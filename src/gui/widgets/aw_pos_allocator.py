from msl.qt import QtWidgets, Button
import numpy as np


class AllocatorDialog(QtWidgets.QDialog):

    def __init__(self, num_pos, wtgrps, parent=None):
        super().__init__(parent=parent)
        self.setWindowTitle('Position Allocator')

        self.wtgrps = wtgrps
        self.positions = []

        self.pos_list = QtWidgets.QListWidget()
        self.pos_list.addItems([f'Position {i+1}' for i in range(num_pos)])

        self.wtgrp_list = QtWidgets.QListWidget()
        self.wtgrp_list.addItems(self.wtgrps)
        while self.wtgrp_list.count() < num_pos:
            self.wtgrp_list.addItem('empty')
        self.wtgrp_list.setDragDropMode(QtWidgets.QListWidget.InternalMove)

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

    def get_all_items(self):
        return [self.wtgrp_list.item(i).text() for i in range(self.wtgrp_list.count())]

    def roll(self):
        loading = self.get_all_items()
        self.wtgrp_list.clear()
        self.wtgrp_list.addItems(np.roll(loading, 1))

    def accept_loading_order(self):
        loading = self.get_all_items()
        for grp in self.wtgrps:
            self.positions.append(loading.index(grp)+1)
        self.close()

