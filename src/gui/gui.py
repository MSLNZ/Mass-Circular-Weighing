import sys
from msl.qt import application, QtWidgets, Button, excepthook, Logger
from src.log import log
from src.routines.do_new_weighing import do_new_weighing
from src.application import Application
from src.gui.widgets.housekeeping import Housekeeping
from src.gui.widgets.scheme_table import SchemeTable
from src.constants import MAX_BAD_RUNS


def make_table_panel():
    get_row = Button(text='Do weighing(s) for selected scheme entry', left_click=collect_n_good_runs, )

    central_panel_group = QtWidgets.QGroupBox('Weighing Scheme Details')
    central_panel_layout = QtWidgets.QVBoxLayout()
    central_panel_layout.addWidget(schemetable)
    central_panel_layout.addWidget(get_row)
    central_panel_group.setLayout(central_panel_layout)

    return central_panel_group


def do_single_weighing(app, bal_alias, scheme_entry, nom_mass_str, ):

    client = housekeeping.client
    folder = housekeeping.folder
    filename = housekeeping.client + '_' + nom_mass_str
    nominal_mass = float(nom_mass_str)
    omega_alias = housekeeping.omega
    timed = housekeeping.timed
    drift = housekeeping.drift

    ok = do_new_weighing(app, client, bal_alias, folder, filename, scheme_entry, nominal_mass,
                    omega_alias, timed, drift)

    return ok


def collect_n_good_runs():
    app = Application(housekeeping.config)
    row = schemetable.currentRow()
    log.info('Row ' + str(row + 1) + ' selected for weighing')

    se_row_data = schemetable.get_row_info(row)
    scheme_entry = se_row_data[0]
    nom_mass_str = se_row_data[1]
    bal_alias = se_row_data[2]
    num_runs = se_row_data[3]

    mode = app.equipment[bal_alias].user_defined['weighing_mode']

    i = 0
    bad = 0
    while i < float(num_runs) and bad < MAX_BAD_RUNS:
        print('Collected '+ str(i) + ' acceptable weighing(s) of ' + num_runs)
        ok = do_single_weighing(app, bal_alias, scheme_entry, nom_mass_str,)
        if ok:
            i += 1
        elif mode == 'aw':
            i += 1
        else:
            bad += 1

    print('Finished weighing ' + scheme_entry)



sys.excepthook = excepthook

gui = application()


w = QtWidgets.QWidget()
w.setWindowTitle('Mass Calibration: Main Window')


housekeeping = Housekeeping()
lhs_panel_group = housekeeping.lhs_panel_group()



schemetable = SchemeTable()
central_panel_group = make_table_panel()

layout = QtWidgets.QHBoxLayout()
layout.addWidget(lhs_panel_group)
layout.addWidget(central_panel_group)
layout.addWidget(Logger(log))

w.setLayout(layout)

w.show()
gui.exec()