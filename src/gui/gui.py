import sys
from msl.qt import application, QtWidgets, Button, excepthook, prompt, Logger
from src.log import log

from src.gui.widgets.browse import Browse, label
from src.gui.housekeeping import Housekeeping



def enter_scheme_details():
    scheme_table = QtWidgets.QTableWidget()
    scheme_table.setColumnCount(5)
    scheme_table.setRowCount(2)
    scheme_table.setHorizontalHeaderLabels(['Weight Groups', 'Nominal mass (g)', 'Balance alias', '# runs', 'Status'])
    return scheme_table


def add_row(scheme):
    scheme.insertRow(1)


sys.excepthook = excepthook

app = application()

w = QtWidgets.QWidget()
w.setWindowTitle('Mass Calibration: Main Window')

# config = QtWidgets.QLineEdit(r'C:\Users\r.hawke\PycharmProjects\Mass-Circular-Weighing\config.xml')
# client_io = QtWidgets.QLineEdit('AsureQ')
# folder_io = QtWidgets.QLineEdit()
# get_folder = Button(text='Select folder', left_click=display_folder, icon='shell32|4')


te = QtWidgets.QTextEdit()

sb = QtWidgets.QSpinBox()
# sb.valueChanged.connect(spinbox_changed)

# cb_stds = QtWidgets.QComboBox()
# cb_stds.addItems(['MET16A', 'MET16B', 'WV'])  # options for standards and check masses
# # cb_stds.currentTextChanged.connect(combo_changed)
# cb_checks = QtWidgets.QComboBox()
# cb_checks.addItems(['MET16A', 'MET16B', 'WV'])  # options for standards and check masses
# # cb_checks.currentTextChanged.connect(combo_changed)

#go = Button(text='Confirm set up', left_click=collate_housekeeping)

#folder_box = folder_box()
schemetable = enter_scheme_details()

new_row = Button(text='Add row', left_click=add_row(schemetable), )

# lhs_panel_group = QtWidgets.QGroupBox('Housekeeping')
# lhs_panel_layout = QtWidgets.QVBoxLayout()
# lhs_panel_layout.addWidget(housekeeping())
# lhs_panel_layout.addWidget(go)
# lhs_panel_group.setLayout(lhs_panel_layout)

central_panel_group = QtWidgets.QGroupBox('Weighing Scheme Details')
central_panel_layout = QtWidgets.QVBoxLayout()
central_panel_layout.addWidget(schemetable)
central_panel_layout.addWidget(new_row)
central_panel_group.setLayout(central_panel_layout)

housekeeping = Housekeeping()
lhs_panel_group = housekeeping.lhs_panel_group()

layout = QtWidgets.QHBoxLayout()
layout.addWidget(lhs_panel_group)
layout.addWidget(central_panel_group)
layout.addWidget(Logger(log))

w.setLayout(layout)

w.show()
app.exec()

'''layout = QtWidgets.QGridLayout()
layout.addWidget(cb_checks, 0, 0)
layout.addWidget(client_io, 0, 1)
layout.addWidget(te, 1, 0, 1, 2)
layout.addWidget(cb_stds, 2, 0)
layout.addWidget(sb, 2, 1)
layout.addWidget(go, 3, 3)






def button_clicked():
    print('Button clicked', sb.value(), cb_stds.currentText())


def combo_changed(value):
    print(value)

def spinbox_changed(value):
    print(value)

    '''