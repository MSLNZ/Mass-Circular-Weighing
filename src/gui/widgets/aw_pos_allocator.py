from msl.qt import QtCore, QtWidgets, Button, Signal, Thread, Worker
import numpy as np


class AllocatorWorker(Worker):

    def __init__(self, parent, *args, **kwargs):
        super(AllocatorWorker, self).__init__()
        self.parent = parent
        self.args = args
        self.kwargs = kwargs

    def process(self):
        self.parent.signal_alloc.emit(self.args)


class AllocatorThread(Thread):
    signal_alloc = Signal(list)
    signal_alloc_done = Signal()

    def __init__(self):
        super(AllocatorThread, self).__init__(AllocatorWorker)

        self.loading = None
        self.signal_alloc.connect(self.accept_loading_order)

    def make_allocator_window(self, args):
        num_pos = args[0]
        wtgrps = args[1]
        self.window = QtWidgets.QWidget()
        self.window.setWindowTitle('Position Allocator')

        self.pos_list = QtWidgets.QListWidget()
        self.wtgrp_list = QtWidgets.QListWidget()

        pos = []
        for i in range(num_pos):
            pos.append('Position '+str(i+1))
        self.pos_list.addItems(pos)

        self.wtgrps = wtgrps
        while len(self.wtgrps) < num_pos:
            self.wtgrps.append('empty')
        self.wtgrp_list.addItems(self.wtgrps)
        self.wtgrp_list.setDragDropMode(self.wtgrp_list.InternalMove)

        lists = QtWidgets.QWidget()
        hbox = QtWidgets.QHBoxLayout()
        hbox.addWidget(self.pos_list, 1)
        hbox.addWidget(self.wtgrp_list, 6)
        lists.setLayout(hbox)

        shuffle = Button(text='Shuffle all down one position', left_click=self.roll)
        accept = Button(text='Accept loading positions', left_click=self.accept_loading_order)

        vbox = QtWidgets.QVBoxLayout()
        vbox.addWidget(lists)
        vbox.addWidget(shuffle)
        vbox.addWidget(accept)
        self.window.setLayout(vbox)

        self.signal_alloc_done.connect(self.window.close)

    def roll(self):
        loading = []
        for i in range(num_pos):
            loading.append(self.wtgrp_list.item(i).text())
        self.wtgrps = np.roll(loading, 1)
        self.wtgrp_list.clear()
        self.wtgrp_list.addItems(self.wtgrps)

    def accept_loading_order(self):
        loading = []
        for i in range(num_pos):
            loading.append(self.wtgrp_list.item(i).text())
        self.loading = loading
        if QtWidgets.QApplication.instance() is not None:
            self.signal_alloc_done.emit()

    def wait_for_reply(self):
        """Block loop until the popup window is closed"""
        if QtWidgets.QApplication.instance() is not None:
            loop = QtCore.QEventLoop()
            self.signal_alloc_done.connect(loop.quit)
            loop.exec_()
        return self.loading

    def show(self, *args, **kwargs):
        if QtWidgets.QApplication.instance() is not None:  # this is opposite to what you have?
            self.make_allocator_window(args)
            self.window.show()
        else:
            self.start(self, *args, **kwargs)


if __name__ == '__main__':
    import sys
    from msl.qt import application, excepthook

    sys.excepthook = excepthook

    gui = application()

    num_pos = 5
    se = 'A B C'
    wtgrps = se.split()

    w = AllocatorThread()
    w.show(num_pos, wtgrps)
    print(w.wait_for_reply())
    gui.exec()

