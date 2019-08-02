
from msl.qt import QtWidgets
from PyQt5 import QtCore
from src.log import log
from src.constants import balances


class SchemeTable(QtWidgets.QTableWidget):

    def __init__(self):
        super(SchemeTable, self).__init__()
        self.setColumnCount(5)
        self.setRowCount(10)
        self.setHorizontalHeaderLabels(['Weight Groups', 'Nominal mass (g)', 'Balance alias', '# runs', 'Status'])
        self.resizeColumnsToContents()
        header = self.horizontalHeader()
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)

        for i in range(self.rowCount()):
            self.set_cell_types(i)

        verthead = self.verticalHeader()
        verthead.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        verthead.customContextMenuRequested.connect(self.vert_header_menu)

    def set_cell_types(self, row_no):
        balance_io = QtWidgets.QComboBox()
        balance_io.addItems(balances)
        self.setCellWidget(row_no, 2, balance_io)
        self.setCellWidget(row_no, 3, QtWidgets.QSpinBox())
        self.setCellWidget(row_no, 4, QtWidgets.QLabel())

    def vert_header_menu(self, pos):
        row = self.currentRow()
        if not row == -1:
            menu = QtWidgets.QMenu()
            add_above = menu.addAction("Add row above")
            add_below = menu.addAction("Add row below")
            delete = menu.addAction("Delete row")

            action = menu.exec_(self.verticalHeader().mapToGlobal(pos))

            if action == add_above:
                self.add_row_above(row)
            if action == add_below:
                self.add_row_below(row)
            if action == delete:
                self.delete_row(row)

    def add_row_above(self, row):
        self.insertRow(row)
        self.set_cell_types(row)

    def add_row_below(self, row):
        self.insertRow(row+1)
        self.set_cell_types(row+1)

    def delete_row(self, row):
        self.removeRow(row)

    def get_row_info(self, row):
        try:
            scheme_entry = self.item(row, 0).text()
            nominal = self.item(row, 1).text()
            bal_alias = self.cellWidget(row, 2).currentText()
            num_runs = self.cellWidget(row, 3).text()
            scheme_entry_row = [scheme_entry, nominal, bal_alias, num_runs]

            return scheme_entry_row

        except AttributeError:
            log.error('Incomplete data in selected row')

    def update_se_status(self, row, status):
        self.cellWidget(row, 4).setText(status)

    #TODO: enable drag and drop using self.dropEvent


