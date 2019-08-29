import sys

from msl.qt import application, QtWidgets, Button, excepthook, Logger

from src.log import log
from src.gui.widgets.housekeeping import Housekeeping
from src.gui.widgets.scheme_table import SchemeTable
from src.gui.circweigh_popup import WeighingThread
from src.routines.collate_data import collate_all_weighings
from src.gui.masscalc_popup import MassCalcThread


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
    folder = housekeeping.folder
    filename = housekeeping.client + '_Scheme.xls'
    schemetable.save_scheme(folder, filename)

def collect_n_good_runs():
    try:
        housekeeping.cfg.bal_class
    except:
        housekeeping.initialise_cfg()

    info = housekeeping.info
    row = schemetable.currentRow()
    if row == -1:
        log.warn('No row selected')
        return
    log.info('Row ' + str(row + 1) + ' selected for weighing')

    #schemetable.update_se_status(row, 'Started')

    se_row_data = schemetable.get_row_info(row)

    weigh_thread.show(se_row_data, info)

    #while not thread.good_runs:
    #    sleep(15)

    #schemetable.update_se_status(row, 'Finished')

def display_results():
    data = collate_all_weighings(schemetable, housekeeping)
    mass_thread.show(data)

def final_mass_calc():
    filesavepath = ''
    client = housekeeping.info.client
    client_wt_IDs = housekeeping.client_masses
    check_wt_IDs = housekeeping.cfg.all_checks['weight ID']
    std_masses = housekeeping.cfg.self.all_stds


sys.excepthook = excepthook

gui = application()

weigh_thread = WeighingThread()
mass_thread = MassCalcThread()

w = QtWidgets.QWidget()
rect = QtWidgets.QDesktopWidget()
w.setFixedSize(rect.width()*0.9, rect.height()*0.45)
w.setWindowTitle('Mass Calibration: Main Window')

housekeeping = Housekeeping()
lhs_panel_group = housekeeping.lhs_panel_group()
schemetable = SchemeTable()
central_panel_group = make_table_panel()

layout = QtWidgets.QHBoxLayout()
layout.addWidget(lhs_panel_group, 3)
layout.addWidget(central_panel_group, 4)
layout.addWidget(Logger(fmt='%(message)s'), 4)
w.setLayout(layout)

w.show()
gui.exec()