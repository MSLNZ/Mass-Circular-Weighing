"""
A helper script for the development of the WaitUntilTime popup window
"""

import sys

from msl.qt import application, excepthook

from mass_circular_weighing.gui.widgets.wait_until_time import WaitUntilTimeDisplay

sys.excepthook = excepthook

gui = application()
#
# target_time = datetime(year=2021, month=3, day=19, hour=17, minute=15, second=0)

w = WaitUntilTimeDisplay(message="Delayed start for weighing for <scheme entry>.")
w.show()
gui.exec()
