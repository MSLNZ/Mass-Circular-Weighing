from msl.qt import QtWidgets, Button, prompt, application

import sys
from msl.qt import application, QtWidgets, Button, excepthook, Logger
from src.log import log

from src.application import Application

def label(name):
    return QtWidgets.QLabel(name)

class WeighingPanel(QtWidgets.QWidget):

    def __init__(self, scheme_entry, run_id):
        super(WeighingPanel, self).__init__()

        self.scheme_entry = scheme_entry
        self.nominal_mass = '1000'
        self.run_id = run_id
        self.cycle = label('1')
        self.position = label('2')

    def scheme_entry_display(self):
        self.displaySchemeEntry = QtWidgets.QGroupBox()
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(label('Scheme entry:'))
        layout.addWidget(label(self.scheme_entry))
        layout.addWidget(label('Nominal mass:'))
        layout.addWidget(label(self.nominal_mass))
        self.displaySchemeEntry.setLayout(layout)

        return self.displaySchemeEntry

    def status_group(self):
        self.statusGroup = QtWidgets.QGroupBox()
        layout = QtWidgets.QFormLayout()
        layout.addRow(label('Run #'), label(self.run_id))
        layout.addRow(label('Cycle'), self.cycle)
        layout.addRow(label('Position'), self.position)
        self.statusGroup.setLayout(layout)

        return self.statusGroup

    def display_reading(self):

        self.displayReading = QtWidgets.QGroupBox()
        layout = QtWidgets.QFormLayout()
        layout.addRow(label('Reading'), label(self.scheme_entry))
        self.displayReading.setLayout(layout)

        return self.displayReading

    def weighPanel(self):
        self.scheme_entry_display()
        self.status_group()
        self.display_reading()

        self.panel = QtWidgets.QGroupBox()
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.displaySchemeEntry)
        layout.addWidget(self.statusGroup)
        layout.addWidget(self.displayReading)
        self.panel.setLayout(layout)

        return self.panel


se = "1a 1b 1c 1d"
run_id = "run_1"

sys.excepthook = excepthook

gui = application()

w = QtWidgets.QWidget()
w.setWindowTitle('Circular Weighing')

weighing = WeighingPanel(se, run_id)
weighing_panel = weighing.weighPanel()

layout = QtWidgets.QHBoxLayout()
layout.addWidget(weighing_panel)
layout.addWidget(Logger(log))

w.setLayout(layout)

w.show()
gui.exec()