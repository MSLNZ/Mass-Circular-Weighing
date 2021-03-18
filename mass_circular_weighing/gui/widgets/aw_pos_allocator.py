"""
The Allocator window allows the operator to specify positions for each weight group, which positions to centre (if any),
and the position to be used for balance self-calibration (if desired).
"""
import numpy as np

from msl.qt import QtWidgets, Button


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

        self.num_pos = num_pos
        self.wtgrps = wtgrps
        self.positions = []
        self.pos_to_centre = []
        self.cal_pos = 1
        self.want_adjust = True

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

        shuffle = Button(text='Shuffle all weight groups down one position', left_click=self.roll)
        accept = Button(
            text='OK',
            left_click=self.accept_loading_order,
        )

        # centring and self adjustment parameters
        init_params = QtWidgets.QWidget()
        self.num_centrings = QtWidgets.QSpinBox()
        self.num_centrings.setValue(4)
        self.cal_pos_box = QtWidgets.QSpinBox()
        self.cal_pos_box.setRange(1, num_pos)
        self.cal_pos_box.setValue(self.cal_pos)
        self.adjust_ch = QtWidgets.QCheckBox()
        self.adjust_ch.setChecked(self.want_adjust)
        frm = QtWidgets.QFormLayout()
        frm.setWidget(0, 2, QtWidgets.QLabel("Tick checkboxes for weight(s) to be centred."))
        frm.addRow(QtWidgets.QLabel("Number of centrings:"), self.num_centrings)
        frm.setWidget(2, 2, QtWidgets.QLabel(""))
        frm.addRow(QtWidgets.QLabel("Do self calibration?"), self.adjust_ch)
        frm.addRow(QtWidgets.QLabel("Calibration position:"), self.cal_pos_box)
        init_params.setLayout(frm)

        vbox = QtWidgets.QVBoxLayout()
        vbox.addWidget(lists)
        vbox.addWidget(shuffle)
        vbox.addWidget(init_params)
        vbox.addWidget(accept)

        self.setLayout(vbox)

    def get_all_items(self):
        return [self.wtgrp_list.item(i).text() for i in range(self.wtgrp_list.count())]

    def get_centrings(self,):
        pos_to_centre = []
        for i in range(self.num_pos):
            if self.centre_list.itemWidget(self.centre_list.item(i)).checkState():
                pos_str = self.pos_list.item(i).text().strip("Position ")
                pos_to_centre.append(int(pos_str))

        return pos_to_centre

    def roll(self):
        loading = self.get_all_items()
        self.wtgrp_list.clear()
        self.wtgrp_list.addItems(np.roll(loading, 1))

    def accept_loading_order(self,):
        self.centrings = int(self.num_centrings.text())

        self.pos_to_centre = self.get_centrings()

        self.cal_pos = int(self.cal_pos_box.text())
        self.want_adjust = True if self.adjust_ch.checkState() else False

        loading = self.get_all_items()
        for grp in self.wtgrps:
            self.positions.append(loading.index(grp)+1)

        self.close()

