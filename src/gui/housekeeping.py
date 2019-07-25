from msl.qt import QtWidgets, Button
from src.log import log
from src.constants import config_default, stds

from src.gui.widgets.browse import Browse, label


class Housekeeping(QtWidgets.QWidget):
    def __init__(self):
        super(Housekeeping, self).__init__()

        self.config = Browse(config_default, 'shell32|4')
        self.folder_io = Browse('', 'shell32|4')
        self.client_io = QtWidgets.QLineEdit('Client')
        self.client_masses = QtWidgets.QLineEdit()

        self.cb_stds = QtWidgets.QComboBox()
        self.cb_stds.addItems(stds)
        self.cb_checks = QtWidgets.QComboBox()
        self.cb_checks.addItems(stds)

        self.go = Button(text='Confirm set up', left_click=self.collate_housekeeping)

    def arrange_housekeeping_box(self):
        self.formGroup = QtWidgets.QGroupBox()
        formlayout = QtWidgets.QFormLayout()

        formlayout.addRow(label('Configuration file'), self.config)
        formlayout.addRow(label('Folder for saving data'), self.folder_io)
        formlayout.addRow(QtWidgets.QLabel('Client'), self.client_io)
        formlayout.addRow(QtWidgets.QLabel('List of client masses'), self.client_masses)
        formlayout.addRow(QtWidgets.QLabel('Standard mass set'), self.cb_stds)
        formlayout.addRow(QtWidgets.QLabel('Check mass set'), self.cb_checks)
        self.formGroup.setLayout(formlayout)

        return self.formGroup

    def lhs_panel_group(self):
        self.arrange_housekeeping_box()

        lhs_panel_group = QtWidgets.QGroupBox('Housekeeping')
        lhs_panel_layout = QtWidgets.QVBoxLayout()
        lhs_panel_layout.addWidget(self.formGroup)
        lhs_panel_layout.addWidget(self.go)
        lhs_panel_group.setLayout(lhs_panel_layout)

        return lhs_panel_group

    def collate_housekeeping(self):
        client = self.client_io.text()
        log.info('Client: ' + client)
        folder = self.folder_io.textbox.text()
        log.info('Save folder: ' + folder)
        log.info('Standard mass set: ' + self.cb_stds.currentText())
        log.info('Check mass set: ' + self.cb_checks.currentText())

        metadata = {
            'Client': client,
            'Folder': folder,
            'Standard mass set': self.cb_stds.currentText(),
            'Check mass set': self.cb_checks.currentText(),
        }

        return metadata
