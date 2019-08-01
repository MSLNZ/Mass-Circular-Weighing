import time

import sys
from msl.qt import application, QtWidgets, Button, excepthook, Logger
from msl.qt.threading import Thread, Worker

from src.constants import MAX_BAD_RUNS
from src.routines.run_circ_weigh import *


def label(name):
    return QtWidgets.QLabel(name)

def do_weighing(bal, se, root, url, run_id, callback1=None, callback2=None, omega=None, **metadata, ):

    metadata['Mmt Timestamp'] = datetime.now().isoformat(sep=' ', timespec='minutes')
    metadata['Time unit'] = 'min'

    weighing = CircWeigh(se)

    ambient_pre = check_ambient_pre(omega)
    if not ambient_pre:
        log.info('Measurement not started due to ambient conditions')
        return False
    for key, value in ambient_pre.items():
        metadata[key] = value

    log.info("Beginning circular weighing for scheme entry " + se + ' ' + run_id)
    log.info('Number of weight groups in weighing = ' + str(weighing.num_wtgrps))
    log.info('Number of cycles = ' + str(weighing.num_cycles))
    log.info('Weight groups are positioned as follows:')

    for i in range(weighing.num_wtgrps):
        log.info('Position ' + str(i + 1) + ': ' + weighing.wtgrps[i])
        metadata['grp' + str(i + 1)] = weighing.wtgrps[i]

    data = np.empty(shape=(weighing.num_cycles, weighing.num_wtgrps, 2))
    weighdata = root['Circular Weighings'][se].require_dataset('measurement_' + run_id, data=data)
    weighdata.add_metadata(**metadata)

    try:
        times = []
        t0 = 0
        for cycle in range(weighing.num_cycles):
            for pos in range(weighing.num_wtgrps):
                if callback1 is not None:
                    callback1(run_id, cycle+1, pos+1, weighing.num_cycles, weighing.num_wtgrps)
                mass = weighing.wtgrps[pos]
                bal.load_bal(mass)                  # add callbacks here?
                reading = bal.get_mass_stable()     # add callbacks here?
                if callback2 is not None:
                    callback2(reading, str(metadata['Unit']))
                if not times:
                    time = 0
                    t0 = perf_counter()
                else:
                    time = np.round((perf_counter() - t0) / 60, 6)  # elapsed time in minutes
                times.append(time)
                weighdata[cycle, pos, :] = [time, reading]
                root.save(url=url, mode='w', ensure_ascii=False)
                bal.unload_bal(mass)                # add callbacks here?

    except (KeyboardInterrupt, SystemExit):
        log.info('Circular weighing sequence aborted')
        metadata['Weighing complete'] = False
        weighdata.add_metadata(**metadata)
        root.save(url=url, mode='w', ensure_ascii=False)

        return None

    ambient_post = check_ambient_post(omega, ambient_pre)
    for key, value in ambient_post.items():
        metadata[key] = value

    metadata['Weighing complete'] = True
    weighdata.add_metadata(metadata)
    root.save(url=url, mode='w', ensure_ascii=False)

    log.debug('weighdata:\n' + str(weighdata[:, :, :]))

    print('Finished weighing ' + se)



class WeighingWorker(Worker):

    def __init__(self, callback, callback2, se_row_data, info):
        super(WeighingWorker, self).__init__()
        self.callback = callback
        self.callback2 = callback2
        self.se_row_data = se_row_data
        self.info = info
        self.good_runs = None

    def process(self):
        se = self.se_row_data[0]
        nom_mass_str = self.se_row_data[1]
        bal_alias = self.se_row_data[2]
        num_runs = self.se_row_data[3]
        client = self.info['Client']
        folder = self.info['Folder']
        omega_alias = self.info['Omega logger']
        timed = self.info['Use measurement times?']
        drift = self.info['Drift correction']
        app = self.info['App']
        bal = app.get_bal_instance(bal_alias)
        mode = app.equipment[bal_alias].user_defined['weighing_mode']
        ac = app.acceptance_criteria(bal_alias, float(nom_mass_str))

        # get OMEGA instance if available
        if omega_alias:
            omega_instance = app.get_omega_instance(omega_alias)
        else:
            omega_instance = None

        # collect metadata
        metadata = {
            'Client': client, 'Balance': bal_alias, 'Unit': bal.unit, 'Nominal mass (g)': float(nom_mass_str),
        }
        for key, value in ac.items():
            metadata[key] = value

        # get any existing data for scheme_entry
        filename = client + '_' + nom_mass_str  # + '_' + run_id
        url = folder + "\\" + filename + '.json'
        root = check_for_existing_weighdata(folder, url, se)
        run_id = get_next_run_id(root, se)

        log.debug(str(self.info))

        bad = 0
        run_no = float(run_id.strip('run_'))
        while run_no < float(num_runs) and bad < MAX_BAD_RUNS:
            print('got to beginning weighing')
            weighing_root = do_weighing(bal, se, root, url, run_id,
                                        callback1=self.callback, callback2=self.callback2, omega=omega_instance,
                                        **metadata,)
            ok = weighing_root #analyse weighing using timed and drift
            if ok:
                print('ok =', ok)
                run_no += 1
            elif mode == 'aw':
                print('allowed')
                run_no += 1
            else:
                print('bad weighing')
                bad += 1

        print('done all weighings for ' + se)

        self.good_runs = run_no




class WeighingThread(Thread):

    def __init__(self):
        super(WeighingThread, self).__init__(WeighingWorker)

        self.window = QtWidgets.QWidget()
        self.window.setWindowTitle('Circular Weighing')
        self.scheme_entry = label('scheme_entry')
        self.nominal_mass = label('nominal')
        self.run_id = label('0')
        self.cycle = label('0')
        self.position = label('0')
        self.reading = label('0')

        layout = QtWidgets.QFormLayout()
        layout.addRow(label('Scheme Entry'), self.scheme_entry)
        layout.addRow(label('Nominal mass (g)'), self.nominal_mass)
        layout.addRow(label('Run'), self.run_id)
        layout.addRow(label('Cycle'), self.cycle)
        layout.addRow(label('Position'), self.position)

        layout.addRow(label('Reading'), self.reading)

        self.window.setLayout(layout)
        self.window.resize(400,400)

    def show(self):
        self.window.show()

    def transfer_info(self, se_row_data):
        scheme_entry = se_row_data[0]
        # should check that all masses are correctly entered
        nom_mass_str = se_row_data[1]
        num_runs = se_row_data[3]
        self.scheme_entry.setText(scheme_entry)
        self.nominal_mass.setText(nom_mass_str)
        self.num_runs = num_runs

    def update_cyc_pos(self, run_id, c, p, num_cyc, num_pos):
        self.run_id.setText('{} of {}'.format(run_id.strip('run_'), self.num_runs))
        self.cycle.setText('{} of {}'.format(c, num_cyc))
        self.position.setText('{} of {}'.format(p, num_pos))

    def update_reading(self, reading, unit):
        self.reading.setText('{} {}'.format(reading, unit))

