"""
A helper script for the development of the Browse popup window
"""
import sys

from msl.qt import application, QtWidgets, Button, excepthook, Logger

from mass_circular_weighing.gui.widgets.browse import Browse, label
from mass_circular_weighing.constants import config_default, save_folder_default

sys.excepthook = excepthook

gui = application()

config_io = Browse(config_default, 'shell32|4')
folder_io = Browse(save_folder_default, 'shell32|4')

w = QtWidgets.QGroupBox()

# w.formGroup = QtWidgets.QGroupBox()
formlayout = QtWidgets.QFormLayout()

formlayout.addRow(label('Configuration file'), config_io)
formlayout.addRow(label('Folder for saving data'), folder_io)

w.setLayout(formlayout)

w.show()
gui.exec()
