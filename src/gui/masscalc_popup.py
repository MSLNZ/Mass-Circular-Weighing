import numpy as np

from src.constants import MU_STR

from msl.qt import QtWidgets, Button, excepthook
from msl.qt.threading import Thread, Worker

from src.log import log

from src.routines.final_mass_calc import final_mass_calc

def label(name):
    return QtWidgets.QLabel(name)


def filter_IDs(ID_list, inputdata):
    relevant_IDs = []
    for item in ID_list:
        if item in inputdata['+ weight group']:
            relevant_IDs.append(item)
        elif item in inputdata['- weight group']:
            relevant_IDs.append(item)

    return relevant_IDs


class DiffsTable(QtWidgets.QTableWidget):

    def __init__(self, data):
        super(DiffsTable, self).__init__()
        self.setColumnCount(7)
        self.setHorizontalHeaderLabels(['+ weight group', '- weight group', 'mass difference (g)', 'residual ('+MU_STR+'g)', 'balance uncertainty ('+MU_STR+'g)', 'acceptance met', 'included'])
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
                if j == 3:
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
                inputdata[-1:]['balance uncertainty (' + MU_STR + 'g)'] = self.cellWidget(i, 4).text()

        return inputdata


#class FinalMassTable()


class CalcWorker(Worker):

    def __init__(self, table, fmc_info,):
        super(CalcWorker, self).__init__()
        self.table = table
        self.fmc_info = fmc_info

    def process(self):
        # collating and sorting metadata
        inputdata = self.table.get_checked_rows()
        self.fmc_info['client_wt_IDs'] = filter_IDs(self.fmc_info['client_wt_IDs'].split(), inputdata)
        if self.fmc_info['check_wt_IDs'] is not None:
            self.fmc_info['check_wt_IDs'] = filter_IDs(self.fmc_info['check_wt_IDs'], inputdata)
        final_mass_calc(
            self.fmc_info['url'],
            self.fmc_info['Client'],
            self.fmc_info['client_wt_IDs'],
            self.fmc_info['check_wt_IDs'],
            self.fmc_info['std_masses'],
            inputdata,
            nbc=self.fmc_info['nbc'],
            corr=self.fmc_info['corr'],
        )


class MassCalcThread(Thread):

    def __init__(self, ):
        super(MassCalcThread, self).__init__(CalcWorker)
        self.table = None
        self.fmc_info = None

    def make_window(self, data):
        self.table = DiffsTable(data)
        do_calc = Button(text='Do calculation', left_click=self.start_finalmasscalc)

        self.window = QtWidgets.QWidget()
        self.window.setWindowTitle('Final Mass Calculation')

        status = QtWidgets.QWidget()
        status_layout = QtWidgets.QVBoxLayout()
        status_layout.addWidget(self.table)
        status.setLayout(status_layout)

        panel = QtWidgets.QGridLayout()
        panel.addWidget(status, 0, 0)
        panel.addWidget(do_calc, 1, 1)

        self.window.setLayout(panel)
        rect = QtWidgets.QDesktopWidget()
        #self.window.move(rect.width() * 0.05, rect.height() * 0.55)

    def show(self, data, fmc_info):
        self.make_window(data)
        self.fmc_info = fmc_info
        self.window.show()

    def start_finalmasscalc(self):
        self.start(self.table, self.fmc_info, )

    def update_weigh_matrix(self, ):
        # make array
        print('looking for more data')


