import numpy as np

from src.constants import MU_STR
from msl.qt import QtWidgets, Button, excepthook
from msl.qt.threading import Thread, Worker

from src.log import log


def label(name):
    return QtWidgets.QLabel(name)


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
            if self.cellWidget(i, 6): # if checked
                # get data
                return inputdata


#class FinalMassTable()


class CalcWorker(Worker):

    def __init__(self, table):
        super(CalcWorker, self).__init__()
        self.table = table
        #self.inputdata = np.empty(0,
        #dtype =[('+ weight group', object), ('- weight group', object),
        #       ('mass difference (g)', 'float64'), ('balance uncertainty ('+MU_STR+'g)', 'float64')])


    def process(self):
        # collating and sorting metadata
        print("oh hello, let's do a calculation")
        print(self.table)
        # inputdata = self.table.get_checked_rows()
        # final mass calc takes: filesavepath, client, client_wt_IDs, check_wt_IDs, std_masses, inputdata, nbc=True, corr=None


class MassCalcThread(Thread):

    def __init__(self, ):
        super(MassCalcThread, self).__init__(CalcWorker)
        self.table = None

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

    def show(self, data):
        self.make_window(data)
        self.window.show()
        print('showing')

    def start_finalmasscalc(self, ):
        self.start(self.table)

    def update_weigh_matrix(self, ):
        # make array
        print('looking for more data')


