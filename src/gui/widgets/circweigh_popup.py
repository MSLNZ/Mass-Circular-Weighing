
from msl.qt import QtWidgets, Button, excepthook, Logger
from msl.qt.threading import Thread, Worker

from src.constants import MAX_BAD_RUNS
from src.log import log
from src.routines.run_circ_weigh import *


def label(name):
    return QtWidgets.QLabel(name)


class WeighingWorker(Worker):

    def __init__(self, callback, callback2, se_row_data, info):
        super(WeighingWorker, self).__init__()
        self.callback = callback
        self.callback2 = callback2
        self.se_row_data = se_row_data
        self.info = info
        self.good_runs = 0

    def process(self):
        # collating and sorting metadata
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
        run_id_1 = get_next_run_id(root, se)

        log.debug(str(self.info))

        run = 0
        bad = 0
        run_no_1 = int(run_id_1.strip('run_'))
        while run < float(num_runs)+MAX_BAD_RUNS+1 and bad < MAX_BAD_RUNS:
            run_id = 'run_' + str(round(run_no_1+run, 0))
            weighing_root = do_circ_weighing(bal, se, root, url, run_id,
                                        callback1=self.callback, callback2=self.callback2, omega=omega_instance,
                                        **metadata,)
            ok = weighing_root # here want to analyse weighing using timed and drift
            if ok:
                print('ok =', ok)
                self.good_runs += 1
            elif mode == 'aw':
                print('allowed')
                self.good_runs += 1
            else:
                print('bad weighing')
                bad += 1

            if self.good_runs == float(num_runs):
                break

            run += 1
            bal._want_abort = False


        if bad == MAX_BAD_RUNS:
            log.error('Completed ' + str(self.good_runs) + ' acceptable weighings of ' + num_runs)
            return 'Failed' # check this...

        print('Finished weighings for ' + se)

        return self.good_runs


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

        layout.addWidget(Logger(log))

        self.window.setLayout(layout)
        self.window.resize(400,400)

    def transfer_info(self, se_row_data):
        scheme_entry = se_row_data[0]
        # should check that all masses are correctly entered
        nom_mass_str = se_row_data[1]
        num_runs = se_row_data[3]
        self.scheme_entry.setText(scheme_entry)
        self.nominal_mass.setText(nom_mass_str)
        self.num_runs = num_runs

    def show(self):
        self.window.show()

    def update_cyc_pos(self, run_id, c, p, num_cyc, num_pos):
        self.run_id.setText('{} of {}'.format(run_id.strip('run_'), self.num_runs))
        self.cycle.setText('{} of {}'.format(c, num_cyc))
        self.position.setText('{} of {}'.format(p, num_pos))

    def update_reading(self, reading, unit):
        self.reading.setText('{} {}'.format(reading, unit))

