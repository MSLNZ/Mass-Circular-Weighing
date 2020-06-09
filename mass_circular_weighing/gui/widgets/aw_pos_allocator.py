import numpy as np

from msl.qt import QtWidgets, Button, QtCore

from .browse import label


class AllocatorDialog(QtWidgets.QDialog):

    def __init__(self, num_pos, wtgrps, parent=None):
        """This Dialog widget allows the assignment of weight groups to weighing positions
        for an automatic weight loading balance.

        Parameters
        ----------
        num_pos : int
            number of weighing positions available on the balance
        wtgrps : list
            list of weight groups as strings
        parent
            application instance or parent widget from which the Dialog is opened
        """
        super().__init__(parent=parent)
        self.setWindowTitle('Allocate Weight Groups to Positions')

        self.wtgrps = wtgrps
        self.positions = []
        self.pos_to_centre = []

        self.pos_list = QtWidgets.QListWidget()
        self.pos_list.addItems([f'Position {i+1}' for i in range(num_pos)])
        self.pos_list.setMaximumWidth(1.25*self.pos_list.sizeHintForColumn(0))
        max_list_height = 1.25 * num_pos * self.pos_list.sizeHintForRow(0)
        self.pos_list.setMaximumHeight(max_list_height)

        self.wtgrp_list = QtWidgets.QListWidget()
        self.wtgrp_list.addItems(self.wtgrps)
        while self.wtgrp_list.count() < num_pos:
            self.wtgrp_list.addItem('empty')
        self.wtgrp_list.setDragDropMode(QtWidgets.QListWidget.InternalMove)
        self.wtgrp_list.setMaximumHeight(max_list_height)

        self.centre_list = QtWidgets.QListWidget()
        while self.centre_list.count() < num_pos:
            item = QtWidgets.QListWidgetItem(self.centre_list)
            ch = QtWidgets.QCheckBox()
            self.centre_list.setItemWidget(item, ch)
        self.centre_list.setMaximumWidth(1.5*self.centre_list.sizeHintForColumn(0))
        self.centre_list.setMaximumHeight(max_list_height)

        lists = QtWidgets.QWidget()
        hbox = QtWidgets.QHBoxLayout()
        hbox.addWidget(self.pos_list)
        hbox.addWidget(self.centre_list)
        hbox.addWidget(self.wtgrp_list)

        lists.setLayout(hbox)

        centrings = QtWidgets.QWidget()
        self.num_centrings = QtWidgets.QSpinBox()
        self.num_centrings.setValue(5)
        frm = QtWidgets.QHBoxLayout()
        frm.addWidget(label("Number of centrings:"))
        frm.addWidget(self.num_centrings)
        centrings.setLayout(frm)

        shuffle = Button(text='Shuffle all down one position', left_click=self.roll)
        accept = Button(
            text='Accept loading positions and begin loading check',
            left_click=self.accept_loading_order
        )

        vbox = QtWidgets.QVBoxLayout()
        vbox.addWidget(lists)
        vbox.addWidget(label("Select checkboxes for weight(s) to be centred."))
        vbox.addWidget(centrings)
        vbox.addWidget(shuffle)
        vbox.addWidget(accept)

        self.setLayout(vbox)

    def get_all_items(self):
        return [self.wtgrp_list.item(i).text() for i in range(self.wtgrp_list.count())]

    def get_centrings(self):
        self.centrings = self.num_centrings.text()
        return [
            self.centre_list.itemWidget(self.centre_list.item(i)).checkState()
            for i in range(self.centre_list.count())
        ]

    def roll(self):
        loading = self.get_all_items()
        self.wtgrp_list.clear()
        self.wtgrp_list.addItems(np.roll(loading, 1))

    def accept_loading_order(self):
        self.pos_to_centre = self.get_centrings()

        loading = self.get_all_items()
        for grp in self.wtgrps:
            self.positions.append(loading.index(grp)+1)

        self.close()

