"""
An interactive display of the metadata needed for a mass calibration, as stored in the admin.xlsx and config.xml files
"""
import os

from msl.qt import QtWidgets, Button, Signal

from ...log import log
from ...constants import save_folder_default, job_default, client_default, client_wt_IDs_default
from ...configuration import Configuration
from .browse import Browse, label
# from ..threads.configedit_thread import ConfigEditorThread
# cfe = ConfigEditorThread()


class Housekeeping(QtWidgets.QWidget):

    balance_list = Signal(list)
    scheme_file = Signal(str)
    scheme_info = Signal(list, list)

    def __init__(self):
        super(Housekeeping, self).__init__()

        self.admin_io = Browse("", QtWidgets.QStyle.SP_DialogOpenButton, find='file', pattern='*.xlsx')
        self.admin_io.textbox.textChanged.connect(self.load_from_admin)
        self.config_lbl = label("")
        # self.edit_config_but = Button(text='Edit config file', left_click=self.edit_config)

        self.folder_io = label(save_folder_default)
        self.job_io = label(job_default)
        self.client_io = label(client_default)
        self.client_masses_io = label(', '.join(client_wt_IDs_default))
        self.stds = ['None']
        self.checks = ['None']

        self.cb_stds_io = label("")
        self.cb_checks_io = label("")

        self.drift_io = label('auto select')
        self.timed_io = label('NO')
        self.true_mass_bool = label('False')
        self.corr_io = label('None')

        self.cfg = None
        self.go = Button(text='Confirm settings', left_click=self.initialise_cfg)

    def arrange_housekeeping_box(self):
        formGroup = QtWidgets.QGroupBox()
        formlayout = QtWidgets.QFormLayout()

        # config_box = self.arrange_config_box()
        formlayout.addRow('Admin file (.xlsx)', label(""))
        formlayout.setWidget(1, 2, self.admin_io) #0, 2, config_box)
        formlayout.addRow('Config file', self.config_lbl)
        # could add revised config editor back in here if needed
        formlayout.addRow('Folder for saving data', self.folder_io)
        formlayout.addRow('Job', self.job_io)
        formlayout.addRow(label('Client'), self.client_io)
        formlayout.addRow(label('Client masses'), self.client_masses_io)
        formlayout.addRow(label('Standard mass set'), self.cb_stds_io)
        formlayout.addRow(label('Check mass set'), self.cb_checks_io)
        formGroup.setLayout(formlayout)

        return formGroup

    def arrange_options_box(self):
        self.optionsGroup = QtWidgets.QGroupBox('Options for analysis')
        formlayout = QtWidgets.QFormLayout()
        formlayout.addRow(label('Drift correction'), self.drift_io)
        formlayout.addRow(label('Use measurement times?'), self.timed_io)
        formlayout.addRow(label('Calculate true mass?'), self.true_mass_bool)
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

    def load_from_admin(self):
        filepath = self.admin_io.textbox.text()
        # self.admin_io.path = filepath       # can add if desired but not necessary now
        if os.path.isfile(filepath):
            self.cfg = Configuration(self.admin_io.textbox.text())
            self.config_lbl.setText(self.cfg.config_xml)
            self.folder_io.setText(self.cfg.folder)
            self.job_io.setText(self.cfg.job)
            self.client_io.setText(self.cfg.client)
            self.client_masses_io.setText(', '.join(self.cfg.client_wt_IDs))

            self.cb_stds_io.setText(self.cfg.std_set)
            self.cb_checks_io.setText(self.cfg.check_set_text)

            self.drift_io.setText(self.cfg.drift_text)
            self.timed_io.setText(self.cfg.timed_text)
            self.true_mass_bool.setText(str(self.cfg.calc_true_mass))
            self.corr_io.setText(str(self.cfg.correlations))

        else:
            log.error('File does not exist at {!r}'.format(filepath))

    # def edit_config(self):
    #     cfe.show(self.cfg)
    #     newconfig = cfe.wait_for_prompt_reply()
    #     self.cfg.config_xml = newconfig
    #     self.config_lbl.setText(f'Config file: {self.cfg.config_xml}')

    def initialise_cfg(self):
        """Set and log values for configuration variables; initialise next phase of calibration"""
        self.cfg.init_ref_mass_sets()

        log.info(f'Admin file: {self.cfg.path}')  # self.admin_io.textbox.text()
        log.info(f'Config file: {self.cfg.config_xml}')
        log.info(f'Save folder: {self.cfg.folder}')
        log.info(f'Job: {self.cfg.job}')
        log.info(f'Client: {self.cfg.client}')
        log.info(f'Client masses: {self.cfg.all_client_wts}')
        log.info(f'Standard mass set: {self.cfg.std_set}')
        log.info(f'Standard masses: {self.cfg.all_stds}')
        log.info(f'Check mass set: {self.cfg.check_set}')
        log.info(f'Check masses: {self.cfg.all_checks}')
        log.info(f'Drift correction: {self.cfg.drift_text}')
        log.info(f'Use measurement times? {self.cfg.timed}')
        log.info(f'Correlations between standards? {self.cfg.correlations}')

        # save details to Admin sheet in (client)_admin.xlsx in save folder
        self.cfg.save_admin()

        self.balance_list.emit(self.cfg.bal_list)

        # trigger automatic loading of weighing scheme
        if self.cfg.scheme:
            self.scheme_info.emit(self.cfg.scheme[0], self.cfg.scheme[1])
        else:
            if os.path.isfile(os.path.join(self.cfg.folder, self.cfg.client + '_Scheme.xlsx')):
                scheme_path = os.path.join(self.cfg.folder, self.cfg.client + '_Scheme.xlsx')
                self.scheme_file.emit(scheme_path)
            elif os.path.isfile(os.path.join(self.cfg.folder, self.cfg.client + '_Scheme.xls')):
                scheme_path = os.path.join(self.cfg.folder, self.cfg.client + '_Scheme.xls')
                self.scheme_file.emit(scheme_path)

        return True
