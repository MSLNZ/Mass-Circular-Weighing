import sys

from msl.qt import application, QtWidgets, Button, excepthook, Logger

from src.log import log
from src.gui.widgets.housekeeping import Housekeeping
from src.gui.widgets.scheme_table import SchemeTable
from src.gui.widgets.circweigh_popup import WeighingThread



def make_table_panel():
    check_ses = Button(text='Check scheme entries', left_click=check_scheme_entries, )
    run_row = Button(text='Do weighing(s) for selected scheme entry', left_click=collect_n_good_runs, )

    central_panel_group = QtWidgets.QGroupBox('Weighing Scheme Details')
    central_panel_layout = QtWidgets.QVBoxLayout()
    central_panel_layout.addWidget(schemetable)
    central_panel_layout.addWidget(check_ses)
    central_panel_layout.addWidget(run_row)
    central_panel_group.setLayout(central_panel_layout)

    return central_panel_group


def check_scheme_entries():
    for i in range(schemetable.rowCount()):
        try:
            scheme_entry = schemetable.cellWidget(i, 0).text()
            for wtgrp in scheme_entry.split():
                for mass in wtgrp.split('+'):
                    if mass not in housekeeping.client_masses \
                        and mass not in housekeeping.app.all_checks['weight ID'] \
                            and mass not in housekeeping.app.all_stds['weight ID']:
                        log.error(mass + ' is not in any of the specified mass sets.')

        except AttributeError:
            pass

    log.info('Checked all scheme entries')


def collect_n_good_runs():
    info = housekeeping.info
    row = schemetable.currentRow()
    log.info('Row ' + str(row + 1) + ' selected for weighing')

    schemetable.update_se_status(row, 'Running')

    se_row_data = schemetable.get_row_info(row)

    thread.show(se_row_data, info)

    #while not thread.good_runs:
    #    sleep(15)

    #schemetable.update_se_status(row, 'Finished')

def final_mass_calc():
    filesavepath = ''
    client = housekeeping.info.client
    client_wt_IDs = housekeeping.client_masses
    check_wt_IDs = housekeeping.app.all_checks['weight ID']
    std_masses = housekeeping.app.self.all_stds


sys.excepthook = excepthook

gui = application()

thread = WeighingThread()

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