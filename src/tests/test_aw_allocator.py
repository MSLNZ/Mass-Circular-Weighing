from src.gui.widgets.aw_pos_allocator import AllocatorDialog

import sys

from msl.qt import application, excepthook

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
