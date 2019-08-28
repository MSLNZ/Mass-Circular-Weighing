import sys

from msl.qt import application, QtWidgets, Button, excepthook, Logger

from src.log import log
from src.gui.widgets.housekeeping import Housekeeping
from src.gui.widgets.scheme_table import SchemeTable
from src.gui.widgets.circweigh_popup import WeighingThread
from src.routines.collate_data import collate_all_weighings


def make_table_panel():
    check_ses = Button(text='Check scheme entries', left_click=check_scheme, )
    save_ses = Button(text='Save scheme entries', left_click=save_scheme, )
    run_row = Button(text='Do weighing(s) for selected scheme entry', left_click=collect_n_good_runs, )
    collate_data = Button(text='Display weighing results', left_click=display_results, )

    buttons = QtWidgets.QWidget()
    button_group = QtWidgets.QGridLayout()
    button_group.addWidget(check_ses, 0, 0)
    button_group.addWidget(save_ses, 1, 0)
    button_group.addWidget(run_row, 0, 1)
    button_group.addWidget(collate_data, 1, 1)
    buttons.setLayout(button_group)

    central_panel_group = QtWidgets.QGroupBox('Weighing Scheme Details')
    central_panel_layout = QtWidgets.QVBoxLayout()
    central_panel_layout.addWidget(schemetable)
    central_panel_layout.addWidget(buttons)
    central_panel_group.setLayout(central_panel_layout)

    return central_panel_group


def check_scheme():
    schemetable.check_scheme_entries(housekeeping)

def save_scheme():
    path = housekeeping.folder+'\Scheme.xls'
    schemetable.save_scheme(path)

def collect_n_good_runs():
    info = housekeeping.info
    row = schemetable.currentRow()
    if row == -1:
        log.warn('No row selected')
        return
    log.info('Row ' + str(row + 1) + ' selected for weighing')

    schemetable.update_se_status(row, 'Running')

    se_row_data = schemetable.get_row_info(row)

    weigh_thread.show(se_row_data, info)

    #while not thread.good_runs:
    #    sleep(15)

    #schemetable.update_se_status(row, 'Finished')

def display_results():
    collate_all_weighings(schemetable, housekeeping.folder, housekeeping.client)

def final_mass_calc():
    filesavepath = ''
    client = housekeeping.info.client
    client_wt_IDs = housekeeping.client_masses
    check_wt_IDs = housekeeping.app.all_checks['weight ID']
    std_masses = housekeeping.app.self.all_stds


sys.excepthook = excepthook

gui = application()

weigh_thread = WeighingThread()
fmcalc_thread = ""

w = QtWidgets.QWidget()
w.setFixedSize(1900, 500)
w.setWindowTitle('Mass Calibration: Main Window')

housekeeping = Housekeeping()
lhs_panel_group = housekeeping.lhs_panel_group()

schemetable = SchemeTable()
central_panel_group = make_table_panel()
#central_panel_group.resize(700,600)

layout = QtWidgets.QHBoxLayout()
layout.addWidget(lhs_panel_group, 3)
layout.addWidget(central_panel_group, 4)

layout.addWidget(Logger(log), 4)

w.setLayout(layout)
w.move(10, 10)

w.show()
gui.exec()