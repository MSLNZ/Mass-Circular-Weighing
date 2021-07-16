"""
A pop-up window to begin the Circular Weighing routine and display progress.
Note: the pop-up runs in a thread so it can be opened from the main gui. It has buttons to tare/zero the balance,
to initialise the balance's self-calibration program, and to begin the circular weighing routine
"""
import sys
import numpy as np
import winsound

from msl.qt import QtGui, QtWidgets, Button, Signal, Logger
from msl.qt.threading import Thread, Worker

from ...log import log
from ...constants import MAX_BAD_RUNS, FONTSIZE
from ...routines.run_circ_weigh import do_circ_weighing, analyse_weighing, check_for_existing_weighdata, check_existing_runs
from ..widgets import label

from .prompt_thread import PromptThread
pt = PromptThread()
from .wait_until_time_thread import WaitThread

check_box_style = '''
QCheckBox {
    font-size:''' + str(FONTSIZE) + '''px;     /* <--- */
}

QCheckBox::indicator {
    width:  ''' + str(FONTSIZE) + '''px;
    height: ''' + str(FONTSIZE) + '''px;
}
'''


class WeighingWorker(Worker):

    def __init__(self, call_run, call_cp, call_read, se_row_data, cfg, bal):
        super(WeighingWorker, self).__init__()
        self.callback_run = call_run        # callback to display status of accumulated runs
        self.callback_cp = call_cp          # callback to display current cycle and position
        self.callback_read = call_read      # callback to display reading
        self.se_row_data = se_row_data
        self.good_runs = self.se_row_data['Good runs']  # target number of acceptable runs
        self.bal = bal                      # balance instance (includes ambient monitoring info)
        self.cfg = cfg                      # Configuration instance

    def process(self):
        # collating and sorting metadata
        se = self.se_row_data['scheme_entry']

        ac = self.cfg.acceptance_criteria(self.se_row_data['bal_alias'], float(self.se_row_data['nominal']))

        metadata = {
            'Client': self.cfg.client, 'Balance': self.se_row_data['bal_alias'],
            'Unit': self.bal.unit, 'Nominal mass (g)': float(self.se_row_data['nominal']),
        }
        for key, value in ac.items():
            metadata[key] = value

        log.debug(str(self.cfg))

        # initialise run numbers
        run = 0
        bad_runs = 0
        while run < float(self.se_row_data['num_runs'])+MAX_BAD_RUNS+1 and bad_runs < MAX_BAD_RUNS:
            # display progress on pop-up window
            self.callback_run(self.good_runs, bad_runs, self.se_row_data['num_runs'])
            # determine if enough runs have been completed successfully
            if self.good_runs > float(self.se_row_data['num_runs']) - 1:
                log.info('Finished weighings for ' + se)
                winsound.Beep(880, 200)
                winsound.Beep(784, 200)
                winsound.Beep(740, 200)
                winsound.Beep(659, 200)
                winsound.Beep(587, 300)
                return
            # get next run id
            run_id = 'run_' + str(round(self.se_row_data['First run no.']+run, 0))
            # do a circular weighing, while updating progress on pop-up window
            weighing_root = do_circ_weighing(self.bal, se, self.se_row_data['root'], self.se_row_data['url'], run_id,
                                             callback1=self.callback_cp, callback2=self.callback_read,
                                             **metadata)
            if weighing_root:
                weighanalysis = analyse_weighing(
                    self.se_row_data['root'], self.se_row_data['url'], se, run_id, self.bal.mode, EXCL=self.cfg.EXCL,
                    timed=self.cfg.timed, drift=self.cfg.drift,
                )
                ok = weighanalysis.metadata.get('Acceptance met?')
                if ok:
                    self.good_runs += 1
                elif 'aw' in self.bal.mode and not weighanalysis.metadata.get('Exclude?'):
                    log.warning('Weighing acceptable as part of set of automatic weighings only')
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

        self.scheme_entry = label('scheme_entry')
        self.nominal_mass = label('nominal')
        self.run_id = label('0')
        self.cycle = label('0')
        self.position = label('0')
        self.reading = label('0')

        self.status = self.status_panel()
        self.controls = self.mettler_panel()
        self.initialise_controls = self.initialisation_panel()
        self.adjust_ch = QtWidgets.QCheckBox("Do self calibration?")
        self.adjust_ch.setStyleSheet(check_box_style)
        self.start_panel = self.start_panel()

        self.finished.connect(self.window.close)

    def status_panel(self):

        status = QtWidgets.QGroupBox()
        status_layout = QtWidgets.QFormLayout()
        status_layout.addRow(label('Scheme Entry'), self.scheme_entry)
        status_layout.addRow(label('Nominal mass (g)'), self.nominal_mass)
        status_layout.addRow(label('Run'), self.run_id)
        status_layout.addRow(label('Cycle'), self.cycle)
        status_layout.addRow(label('Position'), self.position)
        status_layout.addRow(label('Reading'), self.reading)
        status_layout.setWidget(6, 2, Logger(fmt='%(message)s'))
        status.setLayout(status_layout)

        return status

    def mettler_panel(self):
        zero = Button(text='Zero balance', left_click=self.zero_balance, )
        tare = Button(text='Tare balance', left_click=self.tare, )
        scale = Button(text='Scale adjustment', left_click=self.scale, )

        controls = QtWidgets.QGroupBox()
        controls_layout = QtWidgets.QVBoxLayout()
        controls_layout.addWidget(zero)
        controls_layout.addWidget(tare)
        controls_layout.addWidget(scale)

        controls.setLayout(controls_layout)

        return controls

    def initialisation_panel(self):

        pos_alloc = Button(text='Allocate weight(s) to positions', left_click=self.alloc_pos, )
        place = Button(text='Place weights in positions', left_click=self.place_weights, )
        check_loading = Button(text='Check loading and centring', left_click=self.check_loading, )

        controls = QtWidgets.QGroupBox()
        controls_layout = QtWidgets.QVBoxLayout()
        controls_layout.addWidget(pos_alloc)
        controls_layout.addWidget(place)
        controls_layout.addWidget(check_loading)

        controls.setLayout(controls_layout)

        return controls

    def start_panel(self):

        start_weighing = Button(text='START', left_click=self.start_weighing, )
        start_at = Button(text='Start at...', left_click=self.start_weighing_at, )

        start_box = QtWidgets.QGroupBox()
        start_panel = QtWidgets.QVBoxLayout()
        start_panel.addWidget(self.adjust_ch)
        start_panel.addWidget(start_weighing)
        start_panel.addWidget(start_at)
        start_box.setLayout(start_panel)

        return start_box

    def make_layout(self):

        layout = QtWidgets.QGridLayout()
        layout.addWidget(self.status, 0, 0, 3, 1)
        layout.addWidget(self.controls, 0, 1)
        layout.addWidget(self.initialise_controls, 1, 1)
        layout.addWidget(self.start_panel, 2, 1)

        return layout

    def make_layout_mde(self):

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.status)
        layout.addWidget(self.start_panel)

        return layout

    def change_to_weighing_layout(self):
        """Shows only the status of weighing"""
        self.controls.hide()
        self.initialise_controls.hide()
        self.start_panel.hide()

        self.window.resize(self.window.minimumSizeHint())
        # geo = utils.screen_geometry()
        # self.window.resize(geo.width() // 3, geo.height()//2)

    def show(self, se_row_data, cfg):
        self.se_row_data = se_row_data
        self.cfg = cfg
        self.bal, self.mode = self.cfg.get_bal_instance(self.se_row_data['bal_alias'])

        self.scheme_entry.setText(self.se_row_data['scheme_entry'])
        self.nominal_mass.setText(se_row_data['nominal'])
        self.num_runs = se_row_data['num_runs']

        self.check_for_existing()
        if not self.bal.want_abort:
            self.adjust_ch.setChecked(self.bal.want_adjust)

            if "mde" in self.mode:
                layout = self.make_layout_mde()
            else:
                layout = self.make_layout()
                if "aw" not in self.mode:
                    self.initialise_controls.hide()
            self.window.setLayout(layout)
            self.window.resize(self.window.minimumSizeHint())

            self.window.show()

    def zero_balance(self):
        self.bal.zero_bal()

    def tare(self):
        self.bal.tare_bal()

    def scale(self):
        self.bal.scale_adjust()

    def alloc_pos(self):
        self.bal.allocate_positions_and_centrings(self.scheme_entry.text().split())

    def place_weights(self):
        if self.bal.positions is None:
            self.alloc_pos()
        if self.bal.weight_groups is None:
            return

        for mass, pos in zip(self.bal.weight_groups, self.bal.positions):
            ok = self.bal.place_weight(mass, pos)
            if ok is None:
                log.info("Placing aborted")
                return

        log.info("All weights placed")

    def check_loading(self):
        self.bal.check_loading()
        self.bal.centring()

    def start_weighing(self):
        self.bal.want_adjust = True if self.adjust_ch.checkState() else False
        self.change_to_weighing_layout()
        self.check_for_existing()
        self.start(self.update_run_no, self.update_cyc_pos, self.update_reading, self.se_row_data, self.cfg, self.bal)

    def start_weighing_at(self):
        if 'aw' in self.bal.mode:
            self.bal.want_adjust = False    # so that any scale adjustment occurs immediately before weighing
            # check that the balance has been initialised correctly (except for scale adjustment)
            positions = self.bal.initialise_balance(self.scheme_entry.text().split())
            log.debug(str(positions))
            if positions is None:           # consequence of exit from initialise_balance for any number of reasons
                log.error("Balance initialisation was not completed")
                return
        wt = WaitThread()
        wt.show(message=f"Delayed start for weighing for {self.scheme_entry.text()}.", loop_delay=1000,)
        go = wt.wait_for_prompt_reply()
        if go:
            self.start_weighing()

    def close_comms(self, *args):
        self.bal._want_abort = True
        self.bal.close_connection()
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
        self.position.setText('{} of {}'.format(p, self.bal.positions))

    def update_reading(self, reading, unit):
        if reading is None:
            self.reading.setText('None')
        else:
            self.reading.setText('{} {}'.format(np.round(reading, 9), unit))
