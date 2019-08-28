import xlrd, xlwt
import os

from msl.qt import QtWidgets, QtCore, io, prompt
from src.log import log
from src.constants import balances


class SchemeTable(QtWidgets.QTableWidget):

    def __init__(self):
        super(SchemeTable, self).__init__()
        self.setAcceptDrops(True)
        self.setColumnCount(5)
        self.make_rows(10)
        self.setHorizontalHeaderLabels(['Weight Groups', 'Nominal mass (g)', 'Balance alias', '# Runs', 'Status'])
        self.resizeColumnsToContents()
        header = self.horizontalHeader()
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)

        verthead = self.verticalHeader()
        verthead.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        verthead.customContextMenuRequested.connect(self.vert_header_menu)

        self.scheme_path = None

    def make_rows(self, numrows):
        self.setRowCount(numrows)
        for i in range(self.rowCount()):
            self.set_cell_types(i)

    def set_cell_types(self, row_no):
        balance_io = QtWidgets.QComboBox()
        balance_io.addItems(balances)
        self.setCellWidget(row_no, 0, QtWidgets.QLineEdit())
        self.setCellWidget(row_no, 1, QtWidgets.QLineEdit())
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
            scheme_entry = self.cellWidget(row, 0).text()
            nominal = self.cellWidget(row, 1).text()
            bal_alias = self.cellWidget(row, 2).currentText()
            num_runs = self.cellWidget(row, 3).text()
            scheme_entry_row = [scheme_entry, nominal, bal_alias, num_runs]

            return scheme_entry_row

        except AttributeError:
            log.error('Incomplete data in selected row')

    def update_se_status(self, row, status):
        self.cellWidget(row, 4).setText(status)

    def dragEnterEvent(self, event):
        paths = io.get_drag_enter_paths(event, pattern='*.xls*')
        if paths:
            self.scheme_path = paths[0]
            if len(paths) > 1:
                self.scheme_path = prompt.item('Please select one file containing the weighing scheme', items=paths)
            event.accept()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        event.accept()

    def dropEvent(self, event):
        header, rows = read_excel_scheme(self.scheme_path)
        self.make_rows(len(rows))

        index_map = {}
        for col_name in {'weight', 'nominal', 'balance', 'runs',}:
            for i, name in enumerate(header):
                if col_name in name.lower():
                    index_map[col_name] = i

        for i, row in enumerate(rows):
            self.cellWidget(i, 0).setText(row[index_map['weight']])
            self.cellWidget(i, 1).setText(row[index_map['nominal']])
            self.cellWidget(i, 2).setCurrentIndex(self.cellWidget(i, 2).findText(row[index_map['balance']]))
            self.cellWidget(i, 3).setValue(float(row[index_map['runs']]))

        log.info('Scheme loaded from ' + str(self.scheme_path))

    def check_scheme_entries(self, housekeeping):
        for i in range(self.rowCount()):
            try:
                scheme_entry = self.cellWidget(i, 0).text()
                for wtgrp in scheme_entry.split():
                    for mass in wtgrp.split('+'):
                        if mass not in housekeeping.client_masses \
                                and mass not in housekeeping.app.all_checks['weight ID'] \
                                and mass not in housekeeping.app.all_stds['weight ID']:
                            log.error(mass + ' is not in any of the specified mass sets.')

            except AttributeError:
                pass

        log.info('Checked all scheme entries')

    def save_scheme(self, folder, filename):
        if not os.path.exists(folder):
            os.makedirs(folder)

        path = folder + "\\" + filename

        workbook = xlwt.Workbook()
        sheet = workbook.add_sheet('Scheme')
        header = ['Weight groups', 'Nominal mass (g)', 'Balance alias', '# runs']
        for j, text in enumerate(header):
            sheet.write(0, j, text)

        for row in range(self.rowCount()):
            # scheme_entry_row = [scheme_entry, nominal, bal_alias, num_runs]
            try:
                sheet.write(row+1, 0, self.cellWidget(row, 0).text())
                sheet.write(row+1, 1, self.cellWidget(row, 1).text())
                sheet.write(row+1, 2, self.cellWidget(row, 2).currentText())
                sheet.write(row+1, 3, self.cellWidget(row, 3).text())

            except AttributeError:
                pass  #  log.error('Incomplete data in selected row')

        workbook.save(path)
        log.info('Scheme saved to ' + str(path))


def read_excel_scheme(path):
    """Read an Excel file containing a weighing scheme"""
    _book = xlrd.open_workbook(path, on_demand=True)

    names = _book.sheet_names()
    if len(names) > 1:
        sheet_name = prompt.item('Please select which Sheet you wish to use:', names)
    else:
        sheet_name = names[0]

    try:
        sheet = _book.sheet_by_name(sheet_name)
    except xlrd.XLRDError:
        sheet = None

    if sheet is None:
        raise IOError('There is no Sheet named {!r} in {}'.format(sheet_name, path))

    header = [val for val in sheet.row_values(0)]
    rows = [[_cell_convert(sheet.cell(r, c)) for c in range(sheet.ncols)] for r in range(1, sheet.nrows)]
    log.debug('Loading Sheet <{}> in {!r}'.format(sheet_name, path))
    return header, rows


def _cell_convert(cell):
    """Convert an Excel cell to the appropriate value and data type"""
    t = cell.ctype
    if t == xlrd.XL_CELL_NUMBER or t == xlrd.XL_CELL_BOOLEAN:
        if int(cell.value) == cell.value:
            return '{}'.format(int(cell.value))
        else:
            return '{}'.format(cell.value)
    elif t == xlrd.XL_CELL_ERROR:
        return xlrd.error_text_from_code[cell.value]
    else:
        return cell.value.strip()



