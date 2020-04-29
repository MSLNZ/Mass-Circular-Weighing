import winsound
import numpy as np

from msl.qt import QtGui, QtWidgets, Button, excepthook, Logger, Signal, utils
from msl.qt.threading import Thread, Worker

from ...log import log
from ...constants import MAX_BAD_RUNS, FONTSIZE
from ...routines.run_circ_weigh import do_circ_weighing, analyse_weighing, check_for_existing_weighdata, check_existing_runs
from ..widgets.browse import label


class WeighingWorker(Worker):

    def __init__(self, call_run, call_cp, call_read, se_row_data, cfg, bal):
        super(WeighingWorker, self).__init__()
        self.callback_run = call_run        # callback to display status of accumulated runs
        self.callback_cp = call_cp          # callback to display current cycle and position
        self.callback_read = call_read      # callback to display reading
        self.se_row_data = se_row_data
        self.good_runs = self.se_row_data['Good runs']
        self.bal = bal
        self.mode = bal.mode
        self.cfg = cfg

    def process(self):
        # collating and sorting metadata
        se = self.se_row_data['scheme_entry']

        ac = self.cfg.acceptance_criteria(self.se_row_data['bal_alias'], float(self.se_row_data['nominal']))

        # TODO: get OMEGA or Vaisala instance
        # if self.info['Omega logger']:
        #     omega_instance = cfg.get_omega_instance(self.info['Omega logger'])
        # else:
        #     omega_instance = None
        omega_instance = self.cfg.get_omega_instance(self.se_row_data['bal_alias'])

        # collect metadata
        metadata = {
            'Client': self.cfg.client, 'Balance': self.se_row_data['bal_alias'],
            'Unit': self.bal.unit, 'Nominal mass (g)': float(self.se_row_data['nominal']),
        }
        for key, value in ac.items():
            metadata[key] = value

        log.debug(str(self.cfg))

        run = 0
        bad_runs = 0
        while run < float(self.se_row_data['num_runs'])+MAX_BAD_RUNS+1 and bad_runs < MAX_BAD_RUNS:

            self.callback_run(self.good_runs, bad_runs, self.se_row_data['num_runs'])
            if self.good_runs > float(self.se_row_data['num_runs']) - 1:
                log.info('Finished weighings for ' + se)
                winsound.Beep(880, 200)
                winsound.Beep(784, 200)
                winsound.Beep(740, 200)
                winsound.Beep(659, 200)
                winsound.Beep(587, 300)
                return

            run_id = 'run_' + str(round(self.se_row_data['First run no.']+run, 0))

            weighing_root = do_circ_weighing(self.bal, se, self.se_row_data['root'], self.se_row_data['url'], run_id,
                                        callback1=self.callback_cp, callback2=self.callback_read, omega=omega_instance,
                                        **metadata,)
            if weighing_root:
                weighanalysis = analyse_weighing(
                    self.se_row_data['root'], self.se_row_data['url'], se, run_id, self.bal.mode, EXCL=self.cfg.EXCL,
                    timed=self.cfg.timed, drift=self.cfg.drift,
                )
                ok = weighanalysis.metadata.get('Acceptance met?')
                if ok:
                    self.good_runs += 1
                elif self.mode == 'aw' and not weighanalysis.metadata.get['Exclude?']:
                    print('outside acceptance but allowed')
                    self.good_runs += 1
                else:
                    bad_runs += 1
            else:
                return

            run += 1

        if bad_runs == MAX_BAD_RUNS:
            log.error('Completed ' + str(self.good_runs) + ' acceptable weighings of ' + self.se_row_data['num_runs'])


class WeighingThread(Thread):
    weighing_done = Signal(int)

    def __init__(self):
        super(WeighingThread, self).__init__(WeighingWorker)

        self.se_row_data = None
        self.cfg = None
        self.bal, self.mode = None, None

        self.window = QtWidgets.QWidget()
        f = QtGui.QFont()
        f.setPointSize(FONTSIZE)
        self.window.setFont(f)
        self.window.setWindowTitle('Circular Weighing')
        self.window.closeEvent = self.close_comms
        geo = utils.screen_geometry()
        self.window.resize(geo.width() // 2, geo.height())

        self.scheme_entry = label('scheme_entry')
        self.nominal_mass = label('nominal')
        self.run_id = label('0')
        self.cycle = label('0')
        self.position = label('0')
        self.reading = label('0')

        status = QtWidgets.QGroupBox()
        # status = QtWidgets.QWidget()
        status_layout = QtWidgets.QFormLayout()
        status_layout.addRow(label('Scheme Entry'), self.scheme_entry)
        status_layout.addRow(label('Nominal mass (g)'), self.nominal_mass)
        status_layout.addRow(label('Run'), self.run_id)
        status_layout.addRow(label('Cycle'), self.cycle)
        status_layout.addRow(label('Position'), self.position)
        status_layout.addRow(label('Reading'), self.reading)
        status.setLayout(status_layout)

        zero = Button(text='Zero balance', left_click=self.zero_balance, )
        scale = Button(text='Scale adjustment', left_click=self.scale, )
        tare = Button(text='Tare balance', left_click=self.tare, )
        start_weighing = Button(text='START', left_click=self.start_weighing, )

        controls = QtWidgets.QGroupBox()
        controls_layout = QtWidgets.QGridLayout()
        controls_layout.addWidget(zero, 0, 0)
        controls_layout.addWidget(scale, 0, 1)
        controls_layout.addWidget(tare, 1, 0)
        controls_layout.addWidget(start_weighing, 1, 1)
        controls.setLayout(controls_layout)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(status)
        layout.addWidget(controls)
        self.window.setLayout(layout)

        self.finished.connect(self.window.close)

    def show(self, se_row_data, cfg):
        self.se_row_data = se_row_data
        self.cfg = cfg
        self.bal, self.mode = self.cfg.get_bal_instance(self.se_row_data['bal_alias'])

        self.scheme_entry.setText(self.se_row_data['scheme_entry'])
        self.nominal_mass.setText(se_row_data['nominal'])
        self.num_runs = se_row_data['num_runs']

        self.check_for_existing()
        if not self.bal.want_abort:
            self.window.show()

    def zero_balance(self):
        self.bal.zero_bal()

    def scale(self):
        self.bal.scale_adjust()

    def tare(self):
        self.bal.tare_bal()

    def start_weighing(self, ):
        self.check_for_existing()
        self.start(self.update_run_no, self.update_cyc_pos, self.update_reading, self.se_row_data, self.cfg, self.bal)

    def close_comms(self, *args):
        self.bal._want_abort = True
        try:
            self.bal.connection.disconnect()
        except AttributeError:
            pass
        self.weighing_done.emit(self.se_row_data['row'])

    def check_for_existing(self):
        filename = self.cfg.client + '_' + self.se_row_data['nominal']  # + '_' + run_id
        url = self.cfg.folder + "\\" + filename + '.json'
        root = check_for_existing_weighdata(self.cfg.folder, url, self.se_row_data['scheme_entry'])
        good_runs, run_no_1 = check_existing_runs(root, self.se_row_data['scheme_entry'])
        self.se_row_data['url'] = url
        self.se_row_data['root'] = root
        self.se_row_data['Good runs'] = good_runs
        self.se_row_data['First run no.'] = run_no_1
        self.update_run_no(good_runs, 0, self.num_runs)

    def update_run_no(self, good, bad, tot):
        self.run_id.setText('{} of {} ({} bad)'.format(good+1, tot, bad))

    def update_cyc_pos(self, c, p, num_cyc, num_pos):
        self.cycle.setText('{} of {}'.format(c, num_cyc))
        self.position.setText('{} of {}'.format(p, num_pos))

    def update_reading(self, reading, unit):
        if reading is None:
            self.reading.setText('None')
        else:
            self.reading.setText('{} {}'.format(np.round(reading, 9), unit))


