import numpy as np

from src.constants import MU_STR

from msl.qt import QtWidgets, Button, excepthook, Signal, Slot, utils
from msl.qt.threading import Thread, Worker

from src.log import log

from src.routines.final_mass_calc import final_mass_calc

def label(name):
    return QtWidgets.QLabel(name)


def filter_IDs(ID_list, inputdata):
    relevant_IDs = []
    for item in ID_list:
        if item in inputdata['+ weight group'] or item in inputdata['- weight group']:
            relevant_IDs.append(item)

    return relevant_IDs


def filter_stds(std_masses, inputdata):
    relevant_IDs = []
    relevant_nominal = []
    relevant_massvals = []
    relevant_uncs = []

    for i, item in enumerate(std_masses['weight ID']):
        if item in inputdata['+ weight group'] or item in inputdata['- weight group']:
            relevant_IDs.append(item)
            relevant_nominal.append(std_masses['nominal (g)'][i])
            relevant_massvals.append(std_masses['mass values (g)'][i])
            relevant_uncs.append(std_masses['uncertainties (ug)'][i])

    std_masses_new = {
        'nominal (g)': relevant_nominal,
        'mass values (g)': relevant_massvals,
        'uncertainties (ug)': relevant_uncs,
        'weight ID': relevant_IDs,
        'Set Identifier': std_masses['Set Identifier'],
        'Calibrated': std_masses['Calibrated'],
    }
    return std_masses_new


class DiffsTable(QtWidgets.QTableWidget):
    """Displays structured data of amss differences obtained from collate_data, provided headings are as in following list:
    ['+ weight group', '- weight group', 'mass difference (g)',
    'balance uncertainty (' + MU_STR + 'g)', 'Acceptance met?', 'residual (' + MU_STR + 'g)']
    """

    def __init__(self, data):
        super(DiffsTable, self).__init__()
        headers = ['+ weight group', '- weight group', 'mass difference (g)',
                   'CW sigma ('+MU_STR+'g)', 'CW residual OK?',
                   'balance uncertainty ('+MU_STR+'g)', 'MLS residual', 'Include?']
        self.setColumnCount(len(headers))
        self.setHorizontalHeaderLabels(headers)
        self.resizeColumnsToContents()

        self.make_rows(len(data))
        self.fill_table(data)

    def make_rows(self, numrows):
        self.setRowCount(numrows)
        for i in range(self.rowCount()):
            for j in range(self.columnCount()-1):
                self.setCellWidget(i, j, QtWidgets.QLabel())
            self.setCellWidget(i, self.columnCount()-1, QtWidgets.QCheckBox())

    def fill_table(self, data):
        for i in range(len(data)):
            self.cellWidget(i, 0).setText(str(data['+ weight group'][i]))
            self.cellWidget(i, 1).setText(str(data['- weight group'][i]))
            self.cellWidget(i, 2).setText(str("{:+.9f}".format(data['mass difference (g)'][i])))
            self.cellWidget(i, 3).setText(str("{:+.3f}".format(data['residual (' + MU_STR + 'g)'][i])))
            self.cellWidget(i, 4).setText(str(data['Acceptance met?'][i]))
            self.cellWidget(i, 5).setText(str(data['balance uncertainty (' + MU_STR + 'g)'][i]))
            if data['Acceptance met?'][i]:
                self.cellWidget(i, self.columnCount()-1).setChecked(True)
        self.resizeColumnsToContents()

    def get_checked_rows(self, ):
        inputdata = np.empty(0,
                             dtype =[('+ weight group', object), ('- weight group', object),
                                     ('mass difference (g)', 'float64'),
                                     ('balance uncertainty ('+MU_STR+'g)', 'float64')])
        for i in range(self.rowCount()):
            if self.cellWidget(i, self.columnCount()-1).isChecked(): # if checked
                #['+ weight group', '- weight group', 'mass difference (g)', 'residual ('+MU_STR+'g)', 'balance uncertainty ('+MU_STR+'g)', 'acceptance met', 'included'
                dlen = inputdata.shape[0]
                inputdata.resize(dlen + 1)
                inputdata[-1:]['+ weight group'] = self.cellWidget(i, 0).text()
                inputdata[-1:]['- weight group'] = self.cellWidget(i, 1).text()
                inputdata[-1:]['mass difference (g)'] = self.cellWidget(i, 2).text()
                inputdata[-1:]['balance uncertainty (' + MU_STR + 'g)'] = self.cellWidget(i, 5).text()

        return inputdata

    @Slot(object, object)
    def update_resids(self, fmc_result):
        resids = fmc_result['2: Matrix Least Squares Analysis']["Input data with least squares residuals"]
        num_stds = fmc_result["1: Mass Sets"]["Standard"].metadata.get("Number of masses")
        i = 0
        while i < len(resids[:, 4]) - num_stds:     # this check is redundant but ok for now
            for row in range(self.rowCount()):
                if self.cellWidget(row, self.columnCount() - 1).isChecked():
                    self.cellWidget(row, 6).setText(str("{:+.3f}".format(resids[i, 4])))
                    i += 1

class MassValuesTable(QtWidgets.QTableWidget):

    def __init__(self):
        super(MassValuesTable, self).__init__()
        header = ["Weight ID", "Set ID", "Mass value (g)", "Uncertainty (ug)", "95% CI"]
        self.setColumnCount(len(header))
        self.setHorizontalHeaderLabels(header)

        self.make_rows(1)

        self.horizontalHeader().setStretchLastSection(True)
        self.horizontalHeader().resizeSections(QtWidgets.QHeaderView.ResizeToContents)
        self.verticalHeader().resizeSections(QtWidgets.QHeaderView.ResizeToContents)

    def make_rows(self, numrows):
        self.setRowCount(numrows)
        for i in range(self.rowCount()):
            for j in range(5):
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
        if self.fmc_info['check_wt_IDs'] is not None:
            check_wt_IDs = filter_IDs(self.fmc_info['check_wt_IDs'], inputdata)
        else:
            check_wt_IDs = None
        std_masses = filter_stds(self.fmc_info['std_masses'], inputdata)
        # send relevant information to matrix least squares mass calculation algorithm
        self.fmc = final_mass_calc(
            self.fmc_info['Folder'],
            self.fmc_info['Client'],
            client_wt_IDs,
            check_wt_IDs,
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
        rhpanel.setLayout(rhpanel_layout)

        splitter = QtWidgets.QSplitter()
        splitter.addWidget(lhpanel)
        splitter.addWidget(rhpanel)
        splitter.setStretchFactor(0, self.inputdata_table.columnCount())
        splitter.setStretchFactor(1, self.mass_vals_table.columnCount())

        window_layout = QtWidgets.QHBoxLayout()
        window_layout.addWidget(splitter)
        # window_layout.addWidget(self.mass_vals_table)
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






