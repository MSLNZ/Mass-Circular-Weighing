"""
An interactive display of the metadata needed for a mass calibration, as stored in the config.xml file
"""
import os

from msl.qt import QtWidgets, Button, Signal

from ...log import log
from ...constants import config_default, save_folder_default, job_default, client_default, client_wt_IDs_default
from ...configuration import Configuration
from .browse import Browse, label
from ..threads.configedit_thread import ConfigEditorThread
cfe = ConfigEditorThread()


class Housekeeping(QtWidgets.QWidget):

    balance_list = Signal(list)
    scheme_file = Signal(str)

    def __init__(self):
        super(Housekeeping, self).__init__()

        self.config_io = Browse(config_default, QtWidgets.QStyle.SP_DialogOpenButton, find='file', pattern='*.xml')
        self.config_io.textbox.textChanged.connect(self.load_from_config)
        self.edit_config_but = Button(text='Edit config file', left_click=self.edit_config)

        self.folder_io = label(save_folder_default)
        self.job_io = label(job_default)
        self.client_io = label(client_default)
        self.client_masses_io = label(client_wt_IDs_default)
        self.stds = ['None']
        self.checks = ['None']

        self.cb_stds_io = label("")
        self.cb_checks_io = label("")

        self.drift_io = label('auto select')
        self.timed_io = label('NO')
        self.corr_io = label('None')

        self.cfg = None
        self.go = Button(text='Confirm settings', left_click=self.initialise_cfg)

    def arrange_housekeeping_box(self):
        formGroup = QtWidgets.QGroupBox()
        formlayout = QtWidgets.QFormLayout()

        config_box = self.arrange_config_box()
        formlayout.setWidget(0, 2, config_box)
        formlayout.addRow(label('Folder for saving data'), self.folder_io)
        formlayout.addRow(label('Job'), self.job_io)
        formlayout.addRow(label('Client'), self.client_io)
        formlayout.addRow(label('List of client masses'), self.client_masses_io)
        formlayout.addRow(label('Standard mass set'), self.cb_stds_io)
        formlayout.addRow(label('Check mass set'), self.cb_checks_io)
        formGroup.setLayout(formlayout)

        return formGroup

    def arrange_config_box(self):
        configbox = QtWidgets.QGroupBox('Configuration File')
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.config_io)#, 0, 0, 1, 2)
        # layout.addWidget(self.load_from_config_but, 1, 0)
        layout.addWidget(self.edit_config_but)#, 1, 1)
        configbox.setLayout(layout)
        return configbox

    def arrange_options_box(self):
        self.optionsGroup = QtWidgets.QGroupBox('Options for analysis')
        formlayout = QtWidgets.QFormLayout()
        formlayout.addRow(label('Drift correction'), self.drift_io)
        formlayout.addRow(label('Use measurement times?'), self.timed_io)
        formlayout.addRow(label('Correlations between standards'), self.corr_io)
        self.optionsGroup.setLayout(formlayout)

        return self.optionsGroup

    def lhs_panel_group(self):
        formGroup = self.arrange_housekeeping_box()
        self.arrange_options_box()

        lhs_panel_group = QtWidgets.QGroupBox('Housekeeping')
        lhs_panel_layout = QtWidgets.QVBoxLayout()
        lhs_panel_layout.addWidget(formGroup)
        lhs_panel_layout.addWidget(self.optionsGroup)
        lhs_panel_layout.addWidget(self.go)
        lhs_panel_group.setLayout(lhs_panel_layout)

        return lhs_panel_group

    def load_from_config(self):
        if os.path.isfile(self.config_io.textbox.text()):
            self.cfg = Configuration(self.config_io.textbox.text())
            self.folder_io.setText(self.cfg.folder)
            self.job_io.setText(self.cfg.job)
            self.client_io.setText(self.cfg.client)
            self.client_masses_io.setText(self.cfg.client_wt_IDs)

            self.cb_stds_io.setText(self.cfg.std_set)
            self.cb_checks_io.setText(self.cfg.check_set_text)

            self.drift_io.setText(self.cfg.drift_text)
            self.timed_io.setText(self.cfg.timed_text)
            self.corr_io.setText(self.cfg.correlations)

        else:
            log.error('Config file does not exist at {!r}'.format(self.config_io.textbox.text()))

    def edit_config(self):
        cfe.show(self.config_io.textbox.text())
        newconfig = cfe.wait_for_prompt_reply()
        self.config_io.textbox.setText(newconfig)
        self.load_from_config()

    def initialise_cfg(self):
        """Set and log values for configuration variables; initialise next phase of calibration"""
        self.cfg.init_ref_mass_sets()

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
        # NOTE: This script only adds Mettler Toledo or Sartorius balances to the drop-down list
        for alias, equip in self.cfg.equipment.items():
            if "mettler" in equip.manufacturer.lower():
                bal_list.append(alias)
            if "sartorius" in equip.manufacturer.lower():
                bal_list.append(alias)
        self.balance_list.emit(bal_list)

        if os.path.isfile(os.path.join(self.cfg.folder, self.cfg.client + '_Scheme.xls')):
            scheme_path = os.path.join(self.cfg.folder, self.cfg.client + '_Scheme.xls')
            self.scheme_file.emit(scheme_path)
        elif os.path.isfile(os.path.join(self.cfg.folder, self.cfg.client + '_Scheme.xlsx')):
            scheme_path = os.path.join(self.cfg.folder, self.cfg.client + '_Scheme.xlsx')
            self.scheme_file.emit(scheme_path)

        return True
