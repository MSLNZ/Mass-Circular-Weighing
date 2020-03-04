import os
from msl.qt import QtWidgets, Button, Signal
from src.log import log
from src.constants import config_default, save_folder_default, job_default, client_default, client_wt_IDs_default
from src.configuration import Configuration

from src.gui.widgets.browse import Browse, FileSelect, label


class Housekeeping(QtWidgets.QWidget):

    balance_list = Signal(list)

    def __init__(self):
        super(Housekeeping, self).__init__()

        self.config_io = FileSelect(config_default, 'shell32|4')
        self.load_from_config_but = Button(text='Load details from config file', left_click=self.load_from_config)
        self.folder_io = Browse(save_folder_default, 'shell32|4')
        self.job_io = QtWidgets.QLineEdit(job_default)
        self.client_io = QtWidgets.QLineEdit(client_default)
        self.client_masses_io = QtWidgets.QTextEdit(client_wt_IDs_default)
        self.stds = ['None']
        self.checks = ['None']

        self.cb_stds_io = QtWidgets.QComboBox()
        self.cb_checks_io = QtWidgets.QComboBox()

        self.drift_io = QtWidgets.QComboBox()
        self.drift_io.addItems(['auto select', 'no drift', 'linear drift', 'quadratic drift', 'cubic drift'])

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
        formlayout.addRow(label('Job'), self.job_io)
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
        if os.path.isfile(self.config_io.textbox.text()):
            self.cfg = Configuration(self.config_io.textbox.text())
            self.folder_io.textbox.setText(self.cfg.folder)
            self.job_io.setText(self.cfg.job)
            self.client_io.setText(self.cfg.client)
            self.client_masses_io.setText(self.cfg.client_wt_IDs)

            self.stds = ['None']
            self.checks = ['None']
            for std in self.cfg.cfg.root.find('standards'):
                self.stds.append(std.tag)
                self.checks.append(std.tag)
            self.cb_stds_io.clear()
            self.cb_checks_io.clear()
            self.cb_stds_io.addItems(self.stds)
            self.cb_checks_io.addItems(self.checks)
            self.cb_stds_io.setCurrentText(self.cfg.std_set)
            self.cb_checks_io.setCurrentText(self.cfg.check_set_text)

            self.drift_io.setCurrentText(self.cfg.drift_text)
            self.timed_io.setCurrentText(self.cfg.timed_text)
            self.corr_io.setText(self.cfg.correlations)

        else:
            log.error('Config file does not exist at {!r}'.format(self.config_io.textbox.text()))

    def initialise_cfg(self):
        """Set and log values for configuration variables"""
        if os.path.isfile(self.config_io.textbox.text()):
            self.cfg = Configuration(self.config_io.textbox.text())
        else:
            log.error('Config file does not exist at {!r}'.format(self.config_io.textbox.text()))
        self.cfg.std_set = self.cb_stds_io.currentText()
        self.cfg.check_set_text = self.cb_checks_io.currentText()
        self.cfg.init_ref_mass_sets()

        self.cfg.folder = self.folder_io.textbox.text()
        self.cfg.job = self.job_io.text()
        self.cfg.client = self.client_io.text()
        self.cfg.client_wt_IDs = self.client_masses_io.toPlainText()

        self.cfg.drift_text = self.drift_io.currentText()
        self.cfg.timed_text = self.timed_io.currentText()
        self.cfg.correlations = self.corr_io.text()

        # TODO: amend values and save config file to reflect changes?

        log.info('Config file: '+ self.config_io.textbox.text())
        log.info('Save folder: ' + self.cfg.folder)
        log.info('Job: ' + self.cfg.job)
        log.info('Client: ' + self.cfg.client)
        log.info('Client masses: ' + self.cfg.client_wt_IDs)
        log.info('Standard mass set: ' + self.cfg.std_set)
        log.info('Check mass set: ' + str(self.cfg.check_set))
        log.debug('Drift correction: ' + self.cfg.drift_text)
        log.debug('Use measurement times? ' + str(self.cfg.timed))
        log.debug('Correlations between standards? ' + self.cfg.correlations)

        bal_list = []
        for item in self.cfg.equipment:  # TODO: check that this only adds balances!
            bal_list.append(item)
        self.balance_list.emit(bal_list)

        return True


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