from src.gui.widgets.aw_pos_allocator import AllocatorThread

import sys

from msl.qt import application, excepthook

sys.excepthook = excepthook

gui = application()

num_pos = 5
se = 'A B C'
wtgrps = se.split()

w = AllocatorThread(num_pos, wtgrps)
w.show()
print(w.wait_for_reply())
gui.exec()

