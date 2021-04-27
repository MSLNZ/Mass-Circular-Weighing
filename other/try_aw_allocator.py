"""
A helper script for the development of the AllocatorDialog popup window
"""

import sys

from msl.qt import application, excepthook

from mass_circular_weighing.gui.widgets.aw_pos_allocator import AllocatorDialog

sys.excepthook = excepthook

gui = application()

num_pos = 5
se = 'A B C'
wtgrps = se.split()

w = AllocatorDialog(num_pos, wtgrps)
w.show()
gui.exec()
pos = w.positions
print(pos)
if pos:
    print(w.centrings)
    print(w.pos_to_centre)
    print(w.cal_pos, w.want_adjust)
