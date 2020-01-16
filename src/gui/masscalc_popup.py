import numpy as np

from src.constants import MU_STR

from msl.qt import QtWidgets, Button, excepthook, Signal, Slot
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

    def __init__(self, data):
        super(DiffsTable, self).__init__()
        self.setColumnCount(7)
        self.setHorizontalHeaderLabels(
            ['+ weight group', '- weight group', 'mass difference (g)', 'balance uncertainty ('+MU_STR+'g)',
             'acceptance met', 'residual ('+MU_STR+'g)', 'included']
        )
        self.resizeColumnsToContents()

        self.make_rows(len(data))
        self.fill_table(data)

    def make_rows(self, numrows):
        self.setRowCount(numrows)
        for i in range(self.rowCount()):
            for j in range(6):
                self.setCellWidget(i, j, QtWidgets.QLabel())
            self.setCellWidget(i, 6, QtWidgets.QCheckBox())

    def fill_table(self, data):
        for i, entry in enumerate(data):
            for j, item in enumerate(entry):
                if j == 2:
                    item = "{:+.9f}".format(item)
                if j == 5:
                    item = "{:+.3f}".format(item)
                self.cellWidget(i, j).setText(str(item))
            self.cellWidget(i, 6).setChecked(True)
        self.resizeColumnsToContents()

    def get_checked_rows(self, ):
        inputdata = np.empty(0,
                             dtype =[('+ weight group', object), ('- weight group', object),
                                     ('mass difference (g)', 'float64'),
                                     ('balance uncertainty ('+MU_STR+'g)', 'float64')])
        for i in range(self.rowCount()):
            if self.cellWidget(i, 6).isChecked(): # if checked
                #['+ weight group', '- weight group', 'mass difference (g)', 'residual ('+MU_STR+'g)', 'balance uncertainty ('+MU_STR+'g)', 'acceptance met', 'included'
                dlen = inputdata.shape[0]
                inputdata.resize(dlen + 1)
                inputdata[-1:]['+ weight group'] = self.cellWidget(i, 0).text()
                inputdata[-1:]['- weight group'] = self.cellWidget(i, 1).text()
                inputdata[-1:]['mass difference (g)'] = self.cellWidget(i, 2).text()
                inputdata[-1:]['balance uncertainty (' + MU_STR + 'g)'] = self.cellWidget(i, 3).text()

        return inputdata


class MassValuesTable(QtWidgets.QTableWidget):

    def __init__(self):
        super(MassValuesTable, self).__init__()
        self.setColumnCount(5)
        self.setHorizontalHeaderLabels(
            ["Weight ID", "Set ID", "Mass value (g)", "Uncertainty (ug)", "95% CI"]
        )
        self.resizeColumnsToContents()

        self.make_rows(1)
        # self.fill_table(data)

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
        self.table = table
        self.fmc_info = fmc_info
        self.mass_vals_table = mass_vals_table

        self.fmc = None

    def process(self):
        # collating and sorting metadata
        inputdata = self.table.get_checked_rows()
        print(inputdata)
        client_wt_IDs = filter_IDs(self.fmc_info['client_wt_IDs'], inputdata)
        if self.fmc_info['check_wt_IDs'] is not None:
            check_wt_IDs = filter_IDs(self.fmc_info['check_wt_IDs'], inputdata)
        std_masses = filter_stds(self.fmc_info['std_masses'], inputdata)
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
        data = self.fmc['2: Matrix Least Squares Analysis']['Mass values from least squares solution']
        self.parent.fmc_result.emit(self.mass_vals_table, data)
        print('done updating')


class MassCalcThread(Thread):

    fmc_result = Signal(object, object)

    def __init__(self, ):
        super(MassCalcThread, self).__init__(CalcWorker)
        self.inputdata_table = None
        self.fmc_info = None
        self.mass_vals_table = None

        self.fmc_result.connect(MassValuesTable.update_table)

    def make_window(self, data):
        self.inputdata_table = DiffsTable(data)
        do_calc = Button(text='Do calculation', left_click=self.start_finalmasscalc)
        self.mass_vals_table = MassValuesTable()

        self.window = QtWidgets.QWidget()
        self.window.setWindowTitle('Final Mass Calculation')

        window_layout = QtWidgets.QVBoxLayout()
        window_layout.addWidget(self.inputdata_table)
        window_layout.addWidget(do_calc)
        window_layout.addWidget(self.mass_vals_table)
        self.window.setLayout(window_layout)
        rect = QtWidgets.QDesktopWidget()
        #self.window.move(rect.width() * 0.05, rect.height() * 0.55)

    def show(self, data, fmc_info):
        self.make_window(data)
        self.fmc_info = fmc_info
        self.fmc_info['client_wt_IDs'] = self.fmc_info['client_wt_IDs'].split()
        self.window.show()

    def start_finalmasscalc(self):
        self.start(self, self.inputdata_table, self.fmc_info, self.mass_vals_table)






