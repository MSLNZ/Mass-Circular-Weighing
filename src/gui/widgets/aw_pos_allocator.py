from msl.qt import QtWidgets, Button, Signal
import numpy as np


class Allocator(QtWidgets.QWidget):
    signal_alloc = Signal(list)

    def __init__(self, num_pos, scheme_entry):
        super(Allocator, self).__init__()
        self.setWindowTitle('Position Allocator')

        pos = []
        for i in range(num_pos):
            pos.append('Position '+str(i+1))
        self.pos_list = QtWidgets.QListWidget()
        self.pos_list.addItems(pos)

        self.wtgrps = scheme_entry.split()
        while len(self.wtgrps) < num_pos:
            self.wtgrps.append('empty')
        self.wtgrp_list = QtWidgets.QListWidget()
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
        self.setLayout(vbox)

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
        print(loading)
        self.close()
        self.signal_alloc.emit(loading)


if __name__ == '__main__':
    import sys
    from msl.qt import application, excepthook

    sys.excepthook = excepthook

    gui = application()

    num_pos = 5
    se = 'A B C'

    w = Allocator(num_pos, se)
    w.show()
    gui.exec()
