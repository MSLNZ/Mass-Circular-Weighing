"""
A pop-up window to begin the Circular Weighing routine and display progress.
It has buttons to tare/zero the balance (if applicable), to initialise the balance's self-calibration program,
and to begin the circular weighing routine.
"""
import os
import winsound
import numpy as np

from msl.qt import QtWidgets, QtGui, Signal, Button, Logger

from ... import __version__
from ...log import log
from ...constants import MAX_BAD_RUNS, FONTSIZE, local_backup

from ...gui.widgets import label
from ...gui.widgets.wait_until_time import WaitUntilTimeDisplay

from ...routines import check_for_existing_weighdata, check_existing_runs, check_bal_initialised, do_circ_weighing, analyse_weighing
from ...routine_classes import CircWeigh
from ...equip import check_ambient_pre


check_box_style = '''
QCheckBox {
    font-size:''' + str(FONTSIZE) + '''px;     /* <--- */
}

QCheckBox::indicator {
    width:  ''' + str(FONTSIZE) + '''px;
    height: ''' + str(FONTSIZE) + '''px;
}
'''


class WeighingWindow(QtWidgets.QWidget):
    weighing_done = Signal(int)

    def __init__(self):
        super().__init__()

        self.se_row_data = None
        self.cfg = None
        self.bal, self.mode = None, None

        f = QtGui.QFont()
        f.setPointSize(FONTSIZE)
        self.setFont(f)
        self.setWindowTitle('Mass Calibration Program (version {}): Circular Weighing Window'.format(__version__))
        self.closeEvent = self.close_comms
        self.logger = Logger(fmt='%(message)s')

        self.scheme_entry = label('scheme_entry')
        self.nominal_mass = label('nominal')
        self.run_id = label('0')
        self.cycle = label('0')
        self.position = label('0')
        self.reading = label('0')
        self.num_runs = 0

        self.hori_pos_options = QtWidgets.QSpinBox()
        self.lift_positions = QtWidgets.QComboBox()

        self.status = self.status_panel()
        self.controls = self.mettler_panel()
        self.initialise_controls = self.initialisation_panel()
        self.adjust_ch = QtWidgets.QCheckBox("Do self calibration?")
        self.adjust_ch.setStyleSheet(check_box_style)
        self.start_panel = self.start_panel()

    def status_panel(self):
        want_stop = Button(text='Request stop', left_click=self.request_stop, )

        status = QtWidgets.QGroupBox()
        status_layout = QtWidgets.QFormLayout()
        status_layout.addRow(label('Scheme Entry'), self.scheme_entry)
        status_layout.addRow(label('Nominal mass (g)'), self.nominal_mass)
        status_layout.addRow(label('Run'), self.run_id)
        status_layout.addRow(label('Cycle'), self.cycle)
        status_layout.addRow(label('Position'), self.position)
        status_layout.addRow(label('Reading'), self.reading)
        status_layout.setWidget(6, 2, want_stop)
        status_layout.setWidget(7, 2, self.logger)
        status.setLayout(status_layout)

        return status

    def mettler_panel(self):
        reset_comms = Button(text='Reconnect balance', left_click=self.reset_balance_comms, )
        zero = Button(text='Zero balance', left_click=self.zero_balance, )
        tare = Button(text='Tare balance', left_click=self.tare, )
        scale = Button(text='Scale adjustment', left_click=self.scale, )

        controls = QtWidgets.QGroupBox()
        controls_layout = QtWidgets.QVBoxLayout()
        controls_layout.addWidget(reset_comms)
        controls_layout.addWidget(zero)
        controls_layout.addWidget(tare)
        controls_layout.addWidget(scale)

        controls.setLayout(controls_layout)

        return controls

    def initialisation_panel(self):

        pos_alloc = Button(text='Allocate weight(s) to positions', left_click=self.alloc_pos, )
        place = Button(text='Place weights in positions', left_click=self.place_weights, )
        check_loading = Button(text='Check loading and centring', left_click=self.check_loading, )
        gotopos_widget = self.go_to_pos_widget()

        controls = QtWidgets.QGroupBox()
        controls_layout = QtWidgets.QVBoxLayout()
        controls_layout.addWidget(pos_alloc)
        controls_layout.addWidget(place)
        controls_layout.addWidget(check_loading)
        controls_layout.addWidget(gotopos_widget)

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

        self.showMaximized()

    def make_labels(self, se_row_data, cfg):
        self.se_row_data = se_row_data
        self.cfg = cfg
        self.bal, self.mode = self.cfg.get_bal_instance(self.se_row_data['bal_alias'])

        self.scheme_entry.setText(self.se_row_data['scheme_entry'])
        self.nominal_mass.setText(se_row_data['nominal'])
        self.num_runs = se_row_data['num_runs']         # target number of acceptable runs

        if "aw" in self.mode:
            self.hori_pos_options.setRange(0, self.bal.num_pos)
            self.hori_pos_options.setValue(1)
            if "l" in self.mode:        # linear weight handler
                self.lift_positions.addItems(["top", "loading", "weighing"])
            elif '106' in self.mode:    # catch for AT106
                self.lift_positions.addItems(["top", "loading", "weighing"])
            else:                       # carousel weight handler
                self.lift_positions.addItems(['top', 'panbraking', 'weighing', 'calibration'])

    def show(self, se_row_data, cfg):
        self.make_labels(se_row_data, cfg)

        self.check_for_existing()
        if not self.bal.want_abort:
            self.adjust_ch.setChecked(self.bal.want_adjust)

            if "mde" in self.mode:
                layout = self.make_layout_mde()
            else:
                layout = self.make_layout()
                if "aw" not in self.mode:
                    self.initialise_controls.hide()
            self.setLayout(layout)
            self.resize(self.minimumSizeHint())

            # do a quick check on the ambient conditions
            check_ambient_pre(self.bal.ambient_instance, self.bal.ambient_details)
            super().show()

    def reset_balance_comms(self):
        self.bal.connection.disconnect()
        log.info("Reconnecting to balance...")
        self.bal.wait_for_elapse(2)
        self.bal.connect_bal()  # could add reset True here if desired
        log.info("Connected to balance")
        self.bal._want_abort = False

    def zero_balance(self):
        self.bal.zero_bal()

    def tare(self):
        self.bal.tare_bal()

    def scale(self):
        self.bal.scale_adjust()

    def alloc_pos(self):
        self.bal.allocate_positions_and_centrings(self.scheme_entry.text().split())
        self.adjust_ch.setChecked(self.bal.want_adjust)

    def go_to_pos_widget(self):

        gotopos_button = Button(text='Go', left_click=self.go_to_pos, )

        go_to_pos_box = QtWidgets.QGroupBox()
        go_to_pos = QtWidgets.QHBoxLayout()
        go_to_pos.addWidget(label("Move to"))
        go_to_pos.addWidget(self.hori_pos_options)
        go_to_pos.addWidget(self.lift_positions)
        go_to_pos.addWidget(gotopos_button)
        go_to_pos_box.setLayout(go_to_pos)

        return go_to_pos_box

    def go_to_pos(self):
        pos = int(self.hori_pos_options.text())
        lift = self.lift_positions.currentText()
        log.info(f"Selected position {pos}, {lift} position")
        hori_pos, lift_pos = self.bal.get_status()
        if not str(pos) == hori_pos:
            self.bal.move_to(pos, wait=False)
        self.bal.lift_to(lift, hori_pos=pos, wait=False)

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

    def request_stop(self):
        self.bal._want_abort = True
        log.warning("Stop requested. Reconnect balance to continue.")
        self.controls.show()
        self.initialise_controls.show()
        self.start_panel.show()

        self.resize(self.minimumSizeHint())

    def start_weighing(self):
        self.bal.want_adjust = True if self.adjust_ch.checkState() else False
        self.change_to_weighing_layout()
        self.check_for_existing()
        self.process()

    def start_weighing_at(self):
        if 'aw' in self.bal.mode:
            self.bal.want_adjust = False  # so that any scale adjustment occurs immediately before weighing
            # check that the balance has been initialised correctly (except for scale adjustment)
            positions = self.bal.initialise_balance(self.scheme_entry.text().split())
            log.debug(str(positions))
            if positions is None:  # consequence of exit from initialise_balance for any number of reasons
                log.error("Balance initialisation was not completed")
                return
        wt = WaitUntilTimeDisplay(message=f"Delayed start for weighing for {self.scheme_entry.text()}.", loop_delay=1000)
        wt.exec()  # rather than show; to make the pop-up blocking
        if wt.go:
            self.start_weighing()

    def check_for_existing(self):
        filename = self.cfg.client + '_' + self.se_row_data['nominal']  # + '_' + run_id
        url = os.path.join(self.cfg.folder, filename + '.json')
        root = check_for_existing_weighdata(self.cfg.folder, url, self.se_row_data['scheme_entry'])
        good_runs, run_no_1 = check_existing_runs(root, self.se_row_data['scheme_entry'])
        self.se_row_data['url'] = url
        self.se_row_data['root'] = root
        self.se_row_data['good runs'] = good_runs
        self.se_row_data['first run no.'] = run_no_1
        self.update_run_no(good_runs, 0, self.num_runs)

    def update_run_no(self, good, bad, tot):
        self.run_id.setText('{} of {} ({} bad)'.format(good+1, tot, bad))

    def update_cyc_pos(self, c, p, num_cyc, num_pos):
        self.cycle.setText('{} of {}'.format(c, num_cyc))
        positions = self.bal.positions
        if type(positions) is range:        # simplify display for non aw balances
            positions = len(positions)
        self.position.setText('{} of {}'.format(p, positions))

    def update_reading(self, reading, unit):
        if reading is None:
            self.reading.setText('None')
        else:
            self.reading.setText('{} {}'.format(np.round(reading, 9), unit))

    def close_comms(self, *args):
        self.bal._want_abort = True
        self.bal.close_connection()
        print("Connection closed")
        logfile = self.cfg.client + '_' + self.se_row_data['nominal'] + '_log.txt'
        log_save_path = os.path.join(self.cfg.folder, logfile)
        try:
            self.logger.save(log_save_path)
        except FileNotFoundError:
            # Saves to local backup folder in case of internet outage"""
            local_folder = os.path.join(local_backup, os.path.split(os.path.dirname(log_save_path))[-1])
            # ensure a unique filename in case of intermittent internet
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M")
            log_save_path = os.path.join(local_folder,
                                      os.path.basename(log_save_path).strip('.txt') + f'_{timestamp}.txt')
            if not os.path.exists(local_folder):
                os.makedirs(local_folder)
            self.logger.save(log_save_path)

        print(f"Log saved to {log_save_path}")

    def process(self):
        # collating and sorting metadata
        se = self.se_row_data['scheme_entry']
        good_runs = self.se_row_data['good runs']  # including from previous weighings
        ac = self.cfg.acceptance_criteria(self.se_row_data['bal_alias'], float(self.se_row_data['nominal']))

        metadata = {
            'Client': self.cfg.client,
            'Balance': self.se_row_data['bal_alias'], 'Bal serial no.': self.bal.record.serial,
            'Unit': self.bal.unit, 'Nominal mass (g)': float(self.se_row_data['nominal']),
        }
        for key, value in ac.items():
            metadata[key] = value

        log.debug(str(self.cfg))

        # insist that the balance is initialised properly before commencing weighing
        weighing = CircWeigh(se)
        positions = check_bal_initialised(bal=self.bal, wtgrps=weighing.wtgrps)
        if positions is None:
            log.error("Balance initialisation not complete")
            return None
        if 'aw' in self.bal.mode:  # balance has been initialised so we know bal.move_time exists
            circweightime = self.bal.cycle_duration * weighing.num_cycles  # total t in s
            circweighmins = int(circweightime / 60) + 1
            log.info(f'Each circular weighing will take approximately {circweighmins} minutes')

        # initialise run numbers
        run = 0
        bad_runs = 0
        while run < float(self.se_row_data['num_runs'])+MAX_BAD_RUNS+1 and bad_runs < MAX_BAD_RUNS:
            # display progress on pop-up window
            self.update_run_no(good_runs, bad_runs, self.se_row_data['num_runs'])
            # determine if enough runs have been completed successfully
            if good_runs > float(self.se_row_data['num_runs']) - 1:  # num_runs = target
                log.info('Finished weighings for ' + se)
                winsound.Beep(880, 200)
                winsound.Beep(784, 200)
                winsound.Beep(740, 200)
                winsound.Beep(659, 200)
                winsound.Beep(587, 300)
                return
            # get next run id
            run_id = 'run_' + str(round(self.se_row_data['first run no.']+run, 0))
            # do a circular weighing, while updating progress on pop-up window
            weighing_root = do_circ_weighing(self.bal, se, self.se_row_data['root'], self.se_row_data['url'], run_id,
                                             callback1=self.update_cyc_pos, callback2=self.update_reading,
                                             **metadata)
            if weighing_root:
                weighanalysis = analyse_weighing(
                    self.se_row_data['root'], self.se_row_data['url'], se, run_id, self.bal.mode, EXCL=self.cfg.EXCL,
                    timed=self.cfg.timed, drift=self.cfg.drift,
                )
                ok = weighanalysis.metadata.get('Acceptance met?')
                if ok:
                    good_runs += 1
                elif 'aw' in self.bal.mode and not weighanalysis.metadata.get('Exclude?'):
                    log.warning('Weighing acceptable as part of set of automatic weighings only')
                    good_runs += 1
                else:
                    bad_runs += 1
            else:
                return

            run += 1

        if bad_runs == MAX_BAD_RUNS:
            log.error('Completed ' + str(good_runs) + ' acceptable weighings of ' + self.se_row_data['num_runs'])
