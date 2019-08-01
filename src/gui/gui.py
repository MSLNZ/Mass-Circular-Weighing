import sys

from msl.qt import application, QtWidgets, Button, excepthook, Logger

from src.log import log
from src.gui.widgets.housekeeping import Housekeeping
from src.gui.widgets.scheme_table import SchemeTable
from src.gui.widgets.mde_popup import WeighingThread



def make_table_panel():
    get_row = Button(text='Do weighing(s) for selected scheme entry', left_click=collect_n_good_runs, )

    central_panel_group = QtWidgets.QGroupBox('Weighing Scheme Details')
    central_panel_layout = QtWidgets.QVBoxLayout()
    central_panel_layout.addWidget(schemetable)
    central_panel_layout.addWidget(get_row)
    central_panel_group.setLayout(central_panel_layout)

    return central_panel_group


def collect_n_good_runs():
    info = housekeeping.info
    row = schemetable.currentRow()
    log.info('Row ' + str(row + 1) + ' selected for weighing')

    schemetable.update_se_status(row, 'Running')
    print('running')

    se_row_data = schemetable.get_row_info(row)
    thread.transfer_info(se_row_data)

    thread.show()

    thread.start(thread.update_cyc_pos, thread.update_reading, se_row_data, info)

    #while not thread.good_runs:
    #    sleep(15)

    #schemetable.update_se_status(row, 'Finished')


sys.excepthook = excepthook

gui = application()

thread = WeighingThread()

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
w.resize(1300, 400)

w.show()
gui.exec()