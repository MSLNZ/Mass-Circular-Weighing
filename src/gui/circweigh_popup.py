
from msl.qt import QtGui, QtWidgets, Button, excepthook, Logger
from msl.qt.threading import Thread, Worker

from src.constants import MAX_BAD_RUNS, FONTSIZE
from src.log import log
from src.routines.run_circ_weigh import *


def label(name):
    return QtWidgets.QLabel(name)


class WeighingWorker(Worker):

    def __init__(self, call_run, call_cp, call_read, se_row_data, info):
        super(WeighingWorker, self).__init__()
        self.callback_run = call_run
        self.callback_cp = call_cp
        self.callback_read = call_read
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
        cfg = self.info['CFG']
        bal = cfg.get_bal_instance(bal_alias)
        mode = cfg.equipment[bal_alias].user_defined['weighing_mode']
        ac = cfg.acceptance_criteria(bal_alias, float(nom_mass_str))

        # get OMEGA instance if available
        if omega_alias:
            omega_instance = cfg.get_omega_instance(omega_alias)
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
        bad_runs = 0
        run_no_1 = int(run_id_1.strip('run_'))
        while run < float(num_runs)+MAX_BAD_RUNS+1 and bad_runs < MAX_BAD_RUNS:
            self.callback_run(self.good_runs, bad_runs, num_runs)
            run_id = 'run_' + str(round(run_no_1+run, 0))
            weighing_root = do_circ_weighing(bal, se, root, url, run_id,
                                        callback1=self.callback_cp, callback2=self.callback_read, omega=omega_instance,
                                        **metadata,)
            if weighing_root:
                weighanalysis = analyse_weighing(root, url, se, run_id, timed=timed, drift=drift)
                if weighanalysis.metadata.get['Acceptance met?']:
                    print('good weighing')
                    self.good_runs += 1
                elif mode == 'aw' and not weighanalysis.metadata.get['Exclude?']:
                    print('outside acceptance but allowed')
                    self.good_runs += 1
                else:
                    bad_runs += 1
            else:
                return self.good_runs

            if self.good_runs == float(num_runs):
                break

            run += 1
            bal._want_abort = False

        if bad_runs == MAX_BAD_RUNS:
            log.error('Completed ' + str(self.good_runs) + ' acceptable weighings of ' + num_runs)
            return self.good_runs

        print('Finished weighings for ' + se)
        return self.good_runs


class WeighingThread(Thread):

    def __init__(self):
        super(WeighingThread, self).__init__(WeighingWorker)

        self.se_row_data = None
        self.info = None

        self.window = QtWidgets.QWidget()
        f = QtGui.QFont()
        f.setPointSize(FONTSIZE)
        self.window.setFont(f)
        self.window.setWindowTitle('Circular Weighing')
        self.scheme_entry = label('scheme_entry')
        self.nominal_mass = label('nominal')
        self.run_id = label('0')
        self.cycle = label('0')
        self.position = label('0')
        self.reading = label('0')

        status = QtWidgets.QWidget()
        status_layout = QtWidgets.QFormLayout()
        status_layout.addRow(label('Scheme Entry'), self.scheme_entry)
        status_layout.addRow(label('Nominal mass (g)'), self.nominal_mass)
        status_layout.addRow(label('Run'), self.run_id)
        status_layout.addRow(label('Cycle'), self.cycle)
        status_layout.addRow(label('Position'), self.position)
        status_layout.addRow(label('Reading'), self.reading)
        status.setLayout(status_layout)

        start_weighing = Button(text='Start weighing(s)', left_click=self.start_weighing, )

        panel = QtWidgets.QGridLayout()
        panel.addWidget(status, 0, 0)
        panel.addWidget(start_weighing, 1, 1)

        self.window.setLayout(panel)
        rect = QtWidgets.QDesktopWidget()
        self.window.move(rect.width() * 0.05, rect.height() * 0.55)

    def show(self, se_row_data, info):
        self.se_row_data = se_row_data
        self.info = info

        self.scheme_entry.setText(se_row_data[0])
        self.nominal_mass.setText(se_row_data[1])
        self.num_runs = se_row_data[3]

        self.window.show()

    def start_weighing(self, ):
        self.start(self.update_run_no, self.update_cyc_pos, self.update_reading, self.se_row_data, self.info)

    def update_run_no(self, good, bad, tot):
        self.run_id.setText('{} of {} ({} bad)'.format(good+1, tot, bad))

    def update_cyc_pos(self, c, p, num_cyc, num_pos):
        self.cycle.setText('{} of {}'.format(c, num_cyc))
        self.position.setText('{} of {}'.format(p, num_pos))

    def update_reading(self, reading, unit):
        self.reading.setText('{} {}'.format(reading, unit))

    def update_weigh_matrix(self, c, p, num_cyc, num_pos, reading, ):
        # make array
        print('here but not really!?!')
        pass



