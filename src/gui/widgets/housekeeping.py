from msl.qt import QtWidgets, Button
from src.log import log
from src.constants import config_default, save_folder_default, stds, omega_loggers
from src.configuration import Configuration

from src.gui.widgets.browse import Browse, label


class Housekeeping(QtWidgets.QWidget):
    def __init__(self):
        super(Housekeeping, self).__init__()

        self.config_io = Browse(config_default, 'shell32|4')
        self.folder_io = Browse(save_folder_default, 'shell32|4')
        self.client_io = QtWidgets.QLineEdit('AsureQ_Mar')
        self.client_masses_io = QtWidgets.QTextEdit('1 2 5 10 20 50 100 200 200d 500 1000 2000 5000')
        # self.client_masses_io = QtWidgets.QTextEdit('5000MB 10000MB 20000RB 20000RC 20000RD')

        self.cb_stds_io = QtWidgets.QComboBox()
        self.cb_stds_io.addItems(stds)
        self.cb_checks_io = QtWidgets.QComboBox()
        self.cb_checks_io.addItems(stds)
        self.cb_checks_io.setCurrentText('MET19B')

        self.omega_io = QtWidgets.QComboBox()
        self.omega_io.addItems(omega_loggers)

        self.drift_io = QtWidgets.QComboBox()
        self.drift_io.addItems(['<auto select>', 'no drift', 'linear drift', 'quadratic drift', 'cubic drift'])

        self.timed_io = QtWidgets.QComboBox()
        self.timed_io.addItems(['NO', 'YES'])

        self.corr_io = QtWidgets.QLineEdit('None')

        self.cfg = None
        self.go = Button(text='Confirm set up', left_click=self.initialise_cfg)

    def arrange_housekeeping_box(self):
        self.formGroup = QtWidgets.QGroupBox()
        formlayout = QtWidgets.QFormLayout()

        formlayout.addRow(label('Configuration file'), self.config_io)
        formlayout.addRow(label('Folder for saving data'), self.folder_io)
        formlayout.addRow(label('Client'), self.client_io)
        formlayout.addRow(label('List of client masses'), self.client_masses_io)
        formlayout.addRow(label('Standard mass set'), self.cb_stds_io)
        formlayout.addRow(label('Check mass set'), self.cb_checks_io)
        formlayout.addRow(label('Omega logger'), self.omega_io)
        self.formGroup.setLayout(formlayout)

        return self.formGroup

    def arrange_options_box(self):
        self.optionsGroup = QtWidgets.QGroupBox('Options for analysis')
        formlayout = QtWidgets.QFormLayout()
        formlayout.addRow(label('Drift correction'), self.drift_io)
        formlayout.addRow(label('Use measurement times?'), self.timed_io)
        formlayout.addRow(label('Correlations between standards'), self.corr_io)
        self.optionsGroup.setLayout(formlayout)

        return self.optionsGroup

    def lhs_panel_group(self):
        self.arrange_housekeeping_box()
        self.arrange_options_box()

        lhs_panel_group = QtWidgets.QGroupBox('Housekeeping')
        lhs_panel_layout = QtWidgets.QVBoxLayout()
        lhs_panel_layout.addWidget(self.formGroup)
        lhs_panel_layout.addWidget(self.optionsGroup)
        lhs_panel_layout.addWidget(self.go)
        lhs_panel_group.setLayout(lhs_panel_layout)

        return lhs_panel_group

    @property
    def config(self):
        return self.config_io.textbox.text()

    @property
    def folder(self):
        return self.folder_io.textbox.text()

    @property
    def client(self):
        return self.client_io.text()

    @property
    def client_masses(self):
        return self.client_masses_io.toPlainText()

    @property
    def std_set(self):
        return self.cb_stds_io.currentText()

    @property
    def check_set(self):
        if self.cb_checks_io.currentText() == 'None':
            return None
        return self.cb_checks_io.currentText()

    @property
    def omega(self):
        return self.omega_io.currentText()

    @property
    def drift(self):
        if self.drift_io.currentText() == '<auto select>':
            return None
        return self.drift_io.currentText()

    @property
    def timed(self):
        if self.timed_io.currentText() == 'NO':
            return False
        return True

    @property
    def correlations(self):
        return self.corr_io.text()

    def initialise_cfg(self):
        log.info('Config file: '+ self.config)
        log.info('Save folder: ' + self.folder)
        log.info('Client: ' + self.client)
        log.info('Client masses: ' + self.client_masses)
        log.info('Standard mass set: ' + self.std_set)
        log.info('Check mass set: ' + str(self.check_set))
        log.info('Omega logger: ' + self.omega)
        log.info('Drift correction: ' + self.drift_io.currentText())
        log.info('Use measurement times? ' + str(self.timed))
        log.info('Correlations between standards? ' + self.correlations)

        self.cfg = Configuration(self.config, self.std_set, self.check_set)

        return True

    @property
    def info(self):
        info = {
            'CFG': self.cfg,
            'Config file': self.config,
            'Folder': self.folder,
            'Client': self.client,
            'Client masses': self.client_masses,
            'Standard mass set': self.std_set,
            'Check mass set':self.check_set,
            'Omega logger': self.omega,
            'Drift correction': self.drift,
            'Use measurement times?':  str(self.timed),
            'Correlations between standards?': self.correlations,}
        return info


if __name__ == "__main__":
    import sys
    from msl.qt import application, excepthook

    sys.excepthook = excepthook

    gui = application()

    housekeeping = Housekeeping()
    lhs_panel_group = housekeeping.lhs_panel_group()

    w = QtWidgets.QWidget()

    layout = QtWidgets.QHBoxLayout()
    layout.addWidget(lhs_panel_group)

    w.setLayout(layout)

    w.show()
    gui.exec()