"""
A pop-up widget to initialise the Final Mass Calculation and to display the input and output data.
Note: the pop-up window runs in a thread from the main gui window; it includes a button to export the data to MS Excel
"""
import numpy as np

from msl.qt import Qt, QtWidgets, Button, Signal, Slot, utils
from msl.qt.threading import Thread, Worker

from ...constants import SIGMA_STR, MU_STR, NBC
from ...utils import greg_format
from ...routine_classes.final_mass_calc_class import FinalMassCalc, filter_mass_set
from ...routines.report_results import export_results_summary
from .prompt_thread import PromptThread


def label(name):
    return QtWidgets.QLabel(name)


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
                   SIGMA_STR+' of diff ('+MU_STR+'g)', 'CW residual OK?',
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
            self.cellWidget(i, 5).setText(greg_format(data['mass difference (g)'][i]))
            self.cellWidget(i, 5).setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.cellWidget(i, 6).setText(str("{:+.3f}".format(data['residual (' + MU_STR + 'g)'][i])))
            self.cellWidget(i, 6).setAlignment(Qt.AlignRight | Qt.AlignVCenter)
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
                runs = self.cellWidget(i, 2).text().split("+")
                for run in runs:
                    self.included_datasets.add(
                        (self.cellWidget(i, 0).text(), self.cellWidget(i, 1).text(), run)
                    )
                #['+ weight group', '- weight group', 'mass difference (g)', 'residual ('+MU_STR+'g)', 'balance uncertainty ('+MU_STR+'g)', 'acceptance met', 'included'
                dlen = inputdata.shape[0]
                inputdata.resize(dlen + 1)
                inputdata[-1:]['+ weight group'] = self.cellWidget(i, 3).text()
                inputdata[-1:]['- weight group'] = self.cellWidget(i, 4).text()
                inputdata[-1:]['mass difference (g)'] = self.cellWidget(i, 5).text().replace(" ", "")
                inputdata[-1:]['balance uncertainty (' + MU_STR + 'g)'] = self.cellWidget(i, 8).text()

        return inputdata

    @Slot(object, object, name='update_resids')
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
            "Mass value (g)", "Uncertainty (µg)", "95% CI", "Cov", "Reference value (g)", "Shift (" + MU_STR + 'g)'
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

    @Slot(object, object, name='update_mvt')
    def update_table(self, data):
        lend = len(data)
        self.make_rows(lend)
        for i in range(lend):
            for j, item in enumerate(data[i]):
                if j == 3:
                    self.cellWidget(i, j).setText(greg_format(item))
                elif j == 7:
                    self.cellWidget(i, j).setText(greg_format(item))
                else:
                    self.cellWidget(i, j).setText(str(item))
                if j > 2:
                    self.cellWidget(i, j).setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        self.resizeColumnsToContents()


class CalcWorker(Worker):

    pt = PromptThread()

    def __init__(self, parent, table, cfg, mass_vals_table):
        super(CalcWorker, self).__init__()
        self.parent = parent
        self.cw_data_table = table
        self.cfg = cfg
        self.mass_vals_table = mass_vals_table

        self.fmc = None

    def process(self):
        # collate and sort metadata
        inputdata = self.cw_data_table.get_checked_rows()
        if len(inputdata) == 0:
            self.pt.show('warning', "No comparisons selected!\n\n"
                                        "Use checkboxes to select comparisons for calculation")
            self.pt.wait_for_prompt_reply()
            return
        client_masses = filter_mass_set(self.cfg.all_client_wts, inputdata)
        if self.cfg.all_checks is not None:
            check_masses = filter_mass_set(self.cfg.all_checks, inputdata)
        else:
            check_masses = None
        std_masses = filter_mass_set(self.cfg.all_stds, inputdata)
        if len(std_masses['Weight ID']) == 0:
            self.pt.show('warning', "No standard masses included!\n\n"
                                    "Check mass sets are correct.")
            self.pt.wait_for_prompt_reply()
            return
        # send relevant information to matrix least squares mass calculation algorithm
        self.fmc = FinalMassCalc(
            self.cfg.folder,
            self.cfg.client,
            client_masses,
            check_masses,
            std_masses,
            inputdata,
            NBC,
            self.cfg.correlations,
        )
        # do calculation
        self.fmc.add_data_to_root()
        self.fmc.save_to_json_file()
        # update both tables in popup with results
        data = self.fmc.finalmasscalc['2: Matrix Least Squares Analysis']['Mass values from least squares solution']
        self.parent.fmc_result.emit(self.mass_vals_table, data)
        self.parent.fmc_resids.emit(self.cw_data_table, self.fmc.finalmasscalc)


class MassCalcThread(Thread):

    fmc_result = Signal(object, object, name='update_mvt')
    fmc_resids = Signal(object, object, name='update_resids')
    report_summary = Signal(object, name='export_report')

    def __init__(self, ):
        super(MassCalcThread, self).__init__(CalcWorker)
        self.inputdata_table = None
        self.cfg = None
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

        splitter = QtWidgets.QSplitter(orientation=Qt.Horizontal)
        splitter.addWidget(lhpanel)
        splitter.addWidget(rhpanel)
        splitter.setStretchFactor(0, self.inputdata_table.columnCount())
        splitter.setStretchFactor(1, self.mass_vals_table.columnCount())

        window_layout = QtWidgets.QHBoxLayout()
        window_layout.addWidget(splitter)
        self.window.setLayout(window_layout)
        geo = utils.screen_geometry()
        self.window.resize(geo.width(), geo.height() // 2)

    def show(self, data, cfg):
        self.make_window(data)
        self.cfg = cfg
        self.window.show()

    def start_finalmasscalc(self):
        self.start(self, self.inputdata_table, self.cfg, self.mass_vals_table)

    def export_to_report(self):

        inc_datasets = self.inputdata_table.included_datasets

        if self.cfg.all_checks:
            check_set = f"Sheet {self.cfg.all_checks['Sheet name']} in {self.cfg.massref_path}"
        else:
            check_set = None

        export_results_summary(
            self.cfg,
            check_set,
            f"Sheet {self.cfg.all_stds['Sheet name']} in {self.cfg.massref_path}",
            inc_datasets,
        )

    def clean_up(self):
        self.window.close()