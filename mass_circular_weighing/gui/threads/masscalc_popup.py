import numpy as np
import os

from msl.qt import Qt, QtWidgets, Button, excepthook, Signal, Slot, utils
from msl.qt.threading import Thread, Worker
from msl.io import read

from ...log import log
from ...constants import MU_STR
from ...routines.final_mass_calc import final_mass_calc


def label(name):
    return QtWidgets.QLabel(name)


def filter_IDs(ID_list, inputdata):
    relevant_IDs = []
    for item in ID_list:
        if item in inputdata['+ weight group'] or item in inputdata['- weight group']:
            relevant_IDs.append(item)

    return relevant_IDs


def filter_stds(std_masses, inputdata):
    weightgroups = []
    for i in np.append(inputdata['+ weight group'], inputdata['- weight group']):
        if '+' in i:
            for j in i.split('+'):
                weightgroups.append(j)
        else:
            weightgroups.append(i)

    relevant_IDs = []
    relevant_nominal = []
    relevant_massvals = []
    relevant_uncs = []

    for i, item in enumerate(std_masses['weight ID']):
        if item in weightgroups:
            relevant_IDs.append(item)
            relevant_nominal.append(std_masses['nominal (g)'][i])
            relevant_massvals.append(std_masses['mass values (g)'][i])
            relevant_uncs.append(std_masses['uncertainties (ug)'][i])

    std_masses_new = {
        'Set file': std_masses['Set file'],
        'Set Identifier': std_masses['Set Identifier'],
        'Calibrated': std_masses['Calibrated'],
        'nominal (g)': relevant_nominal,
        'mass values (g)': relevant_massvals,
        'uncertainties (ug)': relevant_uncs,
        'weight ID': relevant_IDs,
    }

    return std_masses_new


class DiffsTable(QtWidgets.QTableWidget):
    """Displays structured data of mass differences obtained from collate_data, provided headings are as in following list:
    ['+ weight group', '- weight group', 'mass difference (g)',
    'balance uncertainty (' + MU_STR + 'g)', 'Acceptance met?', 'residual (' + MU_STR + 'g)']
    """
    tickbox = Signal(int)

    def __init__(self, data):
        super(DiffsTable, self).__init__()
        headers = ['Nominal (g)', 'Scheme entry', 'Run #',
                   '+ weight group', '- weight group', 'mass difference (g)',
                   'CW sigma ('+MU_STR+'g)', 'CW residual OK?',
                   'balance uncertainty ('+MU_STR+'g)', 'MLS residual', 'Include?']
        self.setColumnCount(len(headers))
        self.setHorizontalHeaderLabels(headers)
        self.resizeColumnsToContents()

        self.make_rows(len(data))
        self.fill_table(data)

        self.included_datasets = set()

    def make_rows(self, numrows):
        self.setRowCount(numrows)
        for i in range(self.rowCount()):
            for j in range(self.columnCount()-1):
                self.setCellWidget(i, j, QtWidgets.QLabel())
            self.setCellWidget(i, self.columnCount()-1, QtWidgets.QCheckBox())
            self.cellWidget(i, self.columnCount() - 1).stateChanged.connect(self.update_checkboxes)

    @Slot(int)
    def update_checkboxes(self, state):
        i = self.currentRow()
        try:
            a = (self.cellWidget(i, 0).text(), self.cellWidget(i, 1).text(), self.cellWidget(i, 2).text())
            for j in range(self.rowCount()):
                try:
                    b = (self.cellWidget(j, 0).text(), self.cellWidget(j, 1).text(), self.cellWidget(j, 2).text())
                    if a == b:
                        # finds which other rows are from the same measurement run
                        # and sets them to the same checked or unchecked state
                        self.cellWidget(j, self.columnCount() - 1).setCheckState(state)
                except AttributeError:  # e.g. no data in row yet
                    pass
        except AttributeError:  # e.g. no data in row yet
            pass

    def fill_table(self, data):
        for i in range(len(data)):
            self.cellWidget(i, 0).setText(str(data['Nominal (g)'][i]))
            self.cellWidget(i, 1).setText(data['Scheme entry'][i])
            self.cellWidget(i, 2).setText(str(data['Run #'][i]))
            self.cellWidget(i, 3).setText(str(data['+ weight group'][i]))
            self.cellWidget(i, 4).setText(str(data['- weight group'][i]))
            self.cellWidget(i, 5).setText(str("{:+.9f}".format(data['mass difference (g)'][i])))
            self.cellWidget(i, 6).setText(str("{:+.3f}".format(data['residual (' + MU_STR + 'g)'][i])))
            self.cellWidget(i, 7).setText(str(data['Acceptance met?'][i]))
            self.cellWidget(i, 8).setText(str(data['balance uncertainty (' + MU_STR + 'g)'][i]))
            if data['Acceptance met?'][i]:
                self.cellWidget(i, self.columnCount()-1).setChecked(True)
        self.resizeColumnsToContents()

    def get_checked_rows(self, ):
        self.included_datasets = set()
        inputdata = np.empty(0,
                             dtype =[('+ weight group', object), ('- weight group', object),
                                     ('mass difference (g)', 'float64'),
                                     ('balance uncertainty ('+MU_STR+'g)', 'float64')])
        for i in range(self.rowCount()):
            if self.cellWidget(i, self.columnCount()-1).isChecked():
                # if checked, collate data
                self.included_datasets.add(
                    (self.cellWidget(i, 0).text(), self.cellWidget(i, 1).text(), self.cellWidget(i, 2).text())
                )
                #['+ weight group', '- weight group', 'mass difference (g)', 'residual ('+MU_STR+'g)', 'balance uncertainty ('+MU_STR+'g)', 'acceptance met', 'included'
                dlen = inputdata.shape[0]
                inputdata.resize(dlen + 1)
                inputdata[-1:]['+ weight group'] = self.cellWidget(i, 3).text()
                inputdata[-1:]['- weight group'] = self.cellWidget(i, 4).text()
                inputdata[-1:]['mass difference (g)'] = self.cellWidget(i, 5).text()
                inputdata[-1:]['balance uncertainty (' + MU_STR + 'g)'] = self.cellWidget(i, 8).text()

        return inputdata

    @Slot(object, object)
    def update_resids(self, fmc_result):
        resids = fmc_result['2: Matrix Least Squares Analysis']["Input data with least squares residuals"]
        num_stds = fmc_result["1: Mass Sets"]["Standard"].metadata.get("Number of masses")
        i = 0
        while i < len(resids[:, 4]) - num_stds:     # this check is redundant but ok for now
            for row in range(self.rowCount()):
                if self.cellWidget(row, self.columnCount() - 1).isChecked():
                    self.cellWidget(row, 9).setText(str("{:+.3f}".format(resids[i, 4])))
                    i += 1
                else:
                    self.cellWidget(row, 9).setText("")


class MassValuesTable(QtWidgets.QTableWidget):

    def __init__(self):
        super(MassValuesTable, self).__init__()
        self.header = [
            "Nominal (g)", "Weight ID", "Set ID",
            "Mass value (g)", "Uncertainty (ug)", "95% CI", "Cov", "c.f. Reference value (g)",
        ]
        self.setColumnCount(len(self.header))
        self.setHorizontalHeaderLabels(self.header)

        self.make_rows(1)

        self.horizontalHeader().setStretchLastSection(True)
        self.horizontalHeader().resizeSections(QtWidgets.QHeaderView.ResizeToContents)
        self.verticalHeader().resizeSections(QtWidgets.QHeaderView.ResizeToContents)

    def make_rows(self, numrows):
        self.setRowCount(numrows)
        for i in range(self.rowCount()):
            for j in range(len(self.header)):
                self.setCellWidget(i, j, QtWidgets.QLabel())

    @Slot(object, object)
    def update_table(self, data):
        lend = len(data)
        self.make_rows(lend)
        for i in range(lend):
            for j, item in enumerate(data[i]):
                self.cellWidget(i, j).setText(str(item))
        self.resizeColumnsToContents()


class CalcWorker(Worker):

    def __init__(self, parent, table, fmc_info, mass_vals_table):
        super(CalcWorker, self).__init__()
        self.parent = parent
        self.cw_data_table = table
        self.fmc_info = fmc_info
        self.mass_vals_table = mass_vals_table

        self.fmc = None

    def process(self):
        # collate and sort metadata
        inputdata = self.cw_data_table.get_checked_rows()
        client_wt_IDs = filter_IDs(self.fmc_info['client_wt_IDs'], inputdata)
        if self.fmc_info['check_masses'] is not None:
            check_masses = filter_stds(self.fmc_info['check_masses'], inputdata)
        else:
            check_masses = None
        std_masses = filter_stds(self.fmc_info['std_masses'], inputdata)
        # send relevant information to matrix least squares mass calculation algorithm
        self.fmc = final_mass_calc(
            self.fmc_info['Folder'],
            self.fmc_info['Client'],
            client_wt_IDs,
            check_masses,
            std_masses,
            inputdata,
            nbc=self.fmc_info['nbc'],
            corr=self.fmc_info['corr'],
        )
        # update both tables in popup with results
        data = self.fmc['2: Matrix Least Squares Analysis']['Mass values from least squares solution']
        self.parent.fmc_result.emit(self.mass_vals_table, data)
        self.parent.fmc_resids.emit(self.cw_data_table, self.fmc)


class MassCalcThread(Thread):

    fmc_result = Signal(object, object)
    fmc_resids = Signal(object, object)
    report_summary = Signal(object)

    def __init__(self, ):
        super(MassCalcThread, self).__init__(CalcWorker)
        self.inputdata_table = None
        self.fmc_info = None
        self.mass_vals_table = None

        self.fmc_result.connect(MassValuesTable.update_table)
        self.fmc_resids.connect(DiffsTable.update_resids)

    def make_window(self, data):
        self.inputdata_table = DiffsTable(data)
        do_calc = Button(text='Do calculation', left_click=self.start_finalmasscalc)
        self.mass_vals_table = MassValuesTable()
        report_values = Button(text="Export all values to summary file", left_click=self.export_to_report)

        self.window = QtWidgets.QWidget()
        self.window.setWindowTitle('Final Mass Calculation')

        lhpanel = QtWidgets.QGroupBox('Input data: table of mass differences')
        lhpanel_layout = QtWidgets.QVBoxLayout()
        lhpanel_layout.addWidget(self.inputdata_table)
        lhpanel_layout.addWidget(do_calc)
        lhpanel.setLayout(lhpanel_layout)

        rhpanel = QtWidgets.QGroupBox('Output from Matrix Least Squares Analysis')
        rhpanel_layout = QtWidgets.QVBoxLayout()
        rhpanel_layout.addWidget(self.mass_vals_table)
        rhpanel_layout.addWidget(report_values)
        rhpanel.setLayout(rhpanel_layout)

        splitter = QtWidgets.QSplitter(orientation=Qt.Vertical)
        splitter.addWidget(lhpanel)
        splitter.addWidget(rhpanel)
        splitter.setStretchFactor(0, self.inputdata_table.columnCount())
        splitter.setStretchFactor(1, self.mass_vals_table.columnCount())

        window_layout = QtWidgets.QHBoxLayout()
        window_layout.addWidget(splitter)
        self.window.setLayout(window_layout)
        geo = utils.screen_geometry()
        self.window.resize(geo.width(), geo.height() // 2)

    def show(self, data, fmc_info):
        self.make_window(data)
        self.fmc_info = fmc_info
        self.fmc_info['client_wt_IDs'] = self.fmc_info['client_wt_IDs'].split()
        self.window.show()

    def start_finalmasscalc(self):
        self.start(self, self.inputdata_table, self.fmc_info, self.mass_vals_table)

    def export_to_report(self):
        # results_file_path = os.path.join(self.fmc_info['Folder'], self.fmc_info['Client'] + '_finalmasscalc.json')
        # root = read(results_file_path)
        # print('\ncollated input dataset:')
        # print(root['2: Matrix Least Squares Analysis']["Input data with least squares residuals"])

        inc_datasets = self.inputdata_table.included_datasets
        # for tuple in inc_datasets:
        #     path = os.path.join(self.fmc_info['Folder'], self.fmc_info['Client'] + tuple[0])

        self.report_summary.emit(inc_datasets)






