import os
from msl.qt import QtWidgets, Button, Signal
from src.log import log
import src.cv as cv
from src.configuration import Configuration

from src.gui.widgets.browse import Browse, FileSelect, label


class Housekeeping(QtWidgets.QWidget):

    balance_list = Signal(list)

    def __init__(self):
        super(Housekeeping, self).__init__()

        self.config_io = FileSelect(cv.config.get(), 'shell32|4')
        self.load_from_config_but = Button(text='Load details from config file', left_click=self.load_from_config)
        self.folder_io = Browse(cv.folder.get(), 'shell32|4')
        self.job_io = QtWidgets.QLineEdit(cv.job.get())
        self.client_io = QtWidgets.QLineEdit(cv.client.get())
        self.client_masses_io = QtWidgets.QTextEdit(cv.client_wt_IDs.get())

        self.stds = ['None']
        self.checks = ['None']

        self.cb_stds_io = QtWidgets.QComboBox()
        self.cb_checks_io = QtWidgets.QComboBox()

        self.drift_io = QtWidgets.QComboBox()
        self.drift_io.addItems(['<auto select>', 'no drift', 'linear drift', 'quadratic drift', 'cubic drift'])

        self.timed_io = QtWidgets.QComboBox()
        self.timed_io.addItems(['NO', 'YES'])

        self.corr_io = QtWidgets.QLineEdit('None')

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
            cfg = Configuration(self.config_io.textbox.text())
            self.folder_io.textbox.setText(cfg.cfg.root.find('save_folder').text)
            self.job_io.setText(cfg.cfg.root.find('job').text)
            self.client_io.setText(cfg.cfg.root.find('client').text)
            self.client_masses_io.setText(cfg.cfg.root.find('client_masses').text)

            self.stds = ['None']
            self.checks = ['None']
            for std in cfg.cfg.root.find('standards'):
                self.stds.append(std.tag)
                self.checks.append(std.tag)
            self.cb_stds_io.clear()
            self.cb_checks_io.clear()
            self.cb_stds_io.addItems(self.stds)
            self.cb_checks_io.addItems(self.checks)
            self.cb_stds_io.setCurrentText(cfg.cfg.root.find('std_set').text)
            self.cb_checks_io.setCurrentText(cfg.cfg.root.find('check_set').text)

            self.drift_io.setCurrentText(cfg.cfg.root.find('drift').text)
            self.timed_io.setCurrentText(cfg.cfg.root.find('use_times').text)
            self.corr_io.setText(cfg.cfg.root.find('correlations').text)

        else:
            log.error('Config file does not exist at {!r}'.format(self.config_io.textbox.text()))

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

    def initialise_cfg(self):
        """Set and log values for context variables"""
        cfg = Configuration(self.config_io.textbox.text())
        cfg.init_ref_mass_sets(self.cb_stds_io.currentText(), self.check_set)
        cv.config.set(self.config_io.textbox.text())
        cv.cfg.set(cfg)

        cv.folder.set(self.folder_io.textbox.text())
        cv.job.set(self.job_io.text())
        cv.client.set(self.client_io.text())
        cv.client_wt_IDs.set(self.client_masses_io.toPlainText())

        cv.stds.set(cfg.all_stds)
        cv.checks.set(cfg.all_checks)

        cv.drift.set(self.drift_io.currentText())
        cv.timed.set(self.timed)
        cv.correlations.set(self.corr_io.text())

        log.info('Config file: '+ cv.config.get())
        log.info('Save folder: ' + cv.folder.get())
        log.info('Job: ' + cv.job.get())
        log.info('Client: ' + cv.client.get())
        log.info('Client masses: ' + cv.client_wt_IDs.get())
        log.info('Standard mass set: ' + cv.stds.get().get('Set name'))
        log.info('Check mass set: ' + str(self.check_set))
        log.debug('Drift correction: ' + cv.drift.get())
        log.debug('Use measurement times? ' + str(cv.timed.get()))
        log.debug('Correlations between standards? ' + cv.correlations.get())

        bal_list = []
        for item in cfg.equipment:
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