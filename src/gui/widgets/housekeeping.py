import os
from msl.qt import QtWidgets, Button, Signal
from src.log import log
from src.constants import config_default, save_folder_default, client_default, client_masses_default
from src.configuration import Configuration

from src.gui.widgets.browse import Browse, label


class Housekeeping(QtWidgets.QWidget):

    balance_list = Signal(list)

    def __init__(self):
        super(Housekeeping, self).__init__()

        self.config_io = Browse(config_default, 'shell32|4')
        self.load_from_config_but = Button(text='Load details from config file', left_click=self.load_from_config)
        self.folder_io = Browse(save_folder_default, 'shell32|4')
        self.client_io = QtWidgets.QLineEdit(client_default)
        self.client_masses_io = QtWidgets.QTextEdit(client_masses_default)

        self.stds = ['None']
        self.checks = ['None']

        self.cb_stds_io = QtWidgets.QComboBox()
        self.cb_checks_io = QtWidgets.QComboBox()

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
        formlayout.addRow(label(' '), self.load_from_config_but)
        formlayout.addRow(label('Folder for saving data'), self.folder_io)
        formlayout.addRow(label('Client'), self.client_io)
        formlayout.addRow(label('List of client masses'), self.client_masses_io)
        formlayout.addRow(label('Standard mass set'), self.cb_stds_io)
        formlayout.addRow(label('Check mass set'), self.cb_checks_io)
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

    def load_from_config(self):
        if os.path.isfile(self.config):
            self.cfg = Configuration(self.config)

            client = self.cfg.cfg.root.find('client').text
            parent_folder = self.cfg.cfg.root.find('save_folder').text
            folder = os.path.join(parent_folder, client)
            self.folder_io.textbox.setText(folder)
            self.client_io.setText(client)
            self.client_masses_io.setText(self.cfg.cfg.root.find('client_masses').text)

            for std in self.cfg.cfg.root.find('standards'):
                self.stds.append(std.tag)
                self.checks.append(std.tag)
            self.cb_stds_io.clear()
            self.cb_checks_io.clear()
            self.cb_stds_io.addItems(self.stds)
            self.cb_checks_io.addItems(self.checks)
            self.cb_stds_io.setCurrentText(self.cfg.cfg.root.find('std_set').text)
            self.cb_checks_io.setCurrentText(self.cfg.cfg.root.find('check_set').text)

            self.drift_io.setCurrentText(self.cfg.cfg.root.find('drift').text)
            self.timed_io.setCurrentText(self.cfg.cfg.root.find('use_times').text)
            self.corr_io.setText(self.cfg.cfg.root.find('correlations').text)

        else:
            log.error('Config file does not exist at {!r}'.format(self.config))

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
        log.debug('Drift correction: ' + self.drift_io.currentText())
        log.debug('Use measurement times? ' + str(self.timed))
        log.debug('Correlations between standards? ' + self.correlations)

        self.cfg = Configuration(self.config)
        self.cfg.init_ref_mass_sets(self.std_set, self.check_set)

        bal_list = []
        for item in self.cfg.equipment:
            bal_list.append(item)
        self.balance_list.emit(bal_list)

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