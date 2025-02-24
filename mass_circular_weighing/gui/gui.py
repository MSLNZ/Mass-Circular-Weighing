"""
The main gui window and overall interactive program control
"""
import sys
import os
from subprocess import Popen

from msl.qt import application, QtWidgets, Button, excepthook, Logger, Slot
from msl.io import read

sys.excepthook = excepthook

from ..log import log
from .. import __version__
from ..routines.run_circ_weigh import check_existing_runs
from ..routines.analyse_circ_weigh import analyse_all_weighings_in_file
from ..routines.collate_data import collate_all_weighings
from ..gui.widgets.housekeeping import Housekeeping
from ..gui.widgets.scheme_table import SchemeTable
from .threads.masscalc_popup import MassCalcThread

all_weighing_threads = []


class MCWGui(QtWidgets.QWidget):

    def __init__(self):
        """A class for the mass circular weighing main GUI window"""
        super().__init__()

        # rect = QtWidgets.QDesktopWidget()
        # w.setFixedSize(rect.width(), rect.height()*0.45)
        self.setWindowTitle('Mass Calibration Program (version {}): Main Window'.format(__version__))

        self.housekeeping = Housekeeping()
        # self.housekeeping.load_from_admin()
        lhs_panel_group = self.housekeeping.lhs_panel_group()
        self.schemetable = SchemeTable()
        central_panel_group = self.make_table_panel()

        self.housekeeping.balance_list.connect(self.update_balances)
        self.schemetable.check_good_runs_in_file.connect(self.check_good_runs_in_file)
        self.housekeeping.scheme_file.connect(self.schemetable.auto_load_scheme)
        self.housekeeping.scheme_info.connect(self.schemetable.load_scheme)

        self.mass_thread = MassCalcThread()

        layout = QtWidgets.QHBoxLayout()
        layout.addWidget(lhs_panel_group, 2)
        layout.addWidget(central_panel_group, 5)
        layout.addWidget(Logger(fmt='%(message)s'), 3)
        self.setLayout(layout)

    def closeEvent(self, event):
        try:
            self.mass_thread.clean_up()  # closes the final mass calculation window if it's still open
        except AttributeError:
            pass
        super().closeEvent(event)

    def make_table_panel(self, ):
        check_ses = Button(text='Check scheme entries', left_click=self.check_scheme, )
        save_ses = Button(text='Save scheme entries', left_click=self.save_scheme, )
        run_row = Button(text='Do weighing(s) for selected scheme entry', left_click=self.collect_n_good_runs, )
        reanalyse_row = Button(text='Reanalyse weighing(s) for selected scheme entry', left_click=self.reanalyse_weighings, )
        update_status = Button(text='Update status', left_click=self.check_good_run_status, )
        collate_data = Button(text='Display collated results', left_click=self.display_collated)

        buttons = QtWidgets.QWidget()
        button_group = QtWidgets.QGridLayout()
        button_group.addWidget(check_ses, 0, 0)
        button_group.addWidget(save_ses, 1, 0)
        button_group.addWidget(run_row, 0, 1)
        button_group.addWidget(reanalyse_row, 1, 1)
        button_group.addWidget(update_status, 0, 2)
        button_group.addWidget(collate_data, 1, 2)
        buttons.setLayout(button_group)

        central_panel_group = QtWidgets.QGroupBox('Weighing Scheme Details')
        central_panel_layout = QtWidgets.QVBoxLayout()
        central_panel_layout.addWidget(self.schemetable)
        central_panel_layout.addWidget(buttons)
        central_panel_group.setLayout(central_panel_layout)

        return central_panel_group

    @Slot(list)
    def update_balances(self, bal_list):
        self.schemetable.update_balance_list(bal_list)

    @Slot(int)
    def check_good_runs_in_file(self, row):
        nominal = self.schemetable.cellWidget(row, 1).text()
        url = os.path.join(self.housekeeping.cfg.folder, self.housekeeping.cfg.client+'_'+nominal+'.json')
        if os.path.isfile(url):
            scheme_entry = self.schemetable.cellWidget(row, 0).text()
            root = read(url)
            good_runs, run_1_no = check_existing_runs(root, scheme_entry, display_message=True)
            self.schemetable.update_status(row, str(good_runs)+' from '+str(run_1_no-1))
        else:
            self.schemetable.update_status(row, "0")

    def check_good_run_status(self, ):
        for row in range(self.schemetable.rowCount()):
            self.check_good_runs_in_file(row)

    def check_scheme(self, ):
        if not self.housekeeping.cfg.all_stds:
            self.housekeeping.initialise_cfg()
        self.schemetable.check_scheme_entries(self.housekeeping.cfg)

    def save_scheme(self, ):
        folder = self.housekeeping.cfg.folder
        filename = self.housekeeping.cfg.client + '_Admin.xlsx'
        self.schemetable.save_scheme(folder, filename)

    def get_se_row(self, ):
        row = self.schemetable.currentRow()
        if row < 0:
            log.warning('No row selected')
            return None
        log.info('Row ' + str(row + 1) + ' selected for weighing')

        se_row_data = self.schemetable.get_se_row_dict(row)

        return se_row_data

    def collect_n_good_runs(self, ):
        self.save_scheme()

        if not self.housekeeping.cfg.all_stds:
            self.housekeeping.initialise_cfg()

        se_row_data = self.get_se_row()

        if not se_row_data:
            return

        # run circweigh popup as a subprocess that still allows the main gui window to operate
        try:    # running as installed program in Python environment
            Popen(
                ['circweigh-gui', self.housekeeping.cfg.path, str(se_row_data)],
                close_fds=True,
                creationflags=0x00000008  # creates new window as a detached process
            )

        except FileNotFoundError:  # running from exe without Python environment
            Popen(
                [
                    os.path.join(os.getcwd(), 'mass_circular_weighing_standalone.exe'),
                    self.housekeeping.cfg.path,
                    str(se_row_data)
                ],
                close_fds=True,
            )

    def reanalyse_weighings(self, ):
        row = self.schemetable.currentRow()
        if row < 0:
            log.error('Please select a row')
            return

        se = self.schemetable.cellWidget(row, 0).text()
        nom = self.schemetable.cellWidget(row, 1).text()
        filename = self.housekeeping.cfg.client+'_'+nom

        if self.housekeeping.cfg.drift:
            log.info('Beginning weighing analysis using ' + self.housekeeping.cfg.drift + ' correction\n')
        else:
            log.info('Beginning weighing analysis using optimal drift correction\n')

        analyse_all_weighings_in_file(self.housekeeping.cfg, filename, se)
        self.check_good_runs_in_file(row)

    def display_collated(self, ):
        if not self.housekeeping.cfg.all_stds:
            self.housekeeping.initialise_cfg()

        data = collate_all_weighings(self.schemetable, self.housekeeping.cfg)

        self.mass_thread.show(data, self.housekeeping.cfg)


def show_gui():
    gui = application()

    mcw = MCWGui()
    mcw.show()

    gui.exec()


def clean_up_thread(self, thread_instance):
    for i, item in enumerate(all_weighing_threads):
        if thread_instance is item:
            del all_weighing_threads[i]
            break
