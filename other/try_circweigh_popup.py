"""
A helper script for the development of the Circular Weighing control panel popup
"""
import sys

from msl.qt import application, excepthook

from mass_circular_weighing.constants import admin_default
from mass_circular_weighing.configuration import Configuration
from mass_circular_weighing.gui.threads.circweigh_popup import WeighingThread

sys.excepthook = excepthook

gui = application()

cfg = Configuration(admin_default)  # this needs to come after application() in case a prompt is used=

se_row_data = {}
se_row_data['row'] = 1
se_row_data['scheme_entry'] = "100 100A 100B"
se_row_data['nominal'] = "100"
se_row_data['bal_alias'] = "MDE-demo"
se_row_data['num_runs'] = 5


widgey = WeighingThread()
widgey.show(se_row_data, cfg)

gui.exec()


