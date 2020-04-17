import os

from msl.qt import QtWidgets, Button, Signal, Slot
from msl.equipment import Config, utils

from mass_circular_weighing.log import log
from mass_circular_weighing.constants import IN_DEGREES_C, config_default, save_folder_default, job_default, client_default, client_wt_IDs_default
from mass_circular_weighing.gui.widgets.browse import Browse, FileSelect, label


class ConfigEditor(QtWidgets.QWidget):

    update_ref_mass_sets = Signal(object)

    def __init__(self):
        super(ConfigEditor, self).__init__()

        self.config_io = FileSelect(config_default, QtWidgets.QStyle.SP_DialogOpenButton)
        self.load_from_config_but = Button(text='Load existing config file', left_click=self.load_from_config)

        self.folder_io = Browse(save_folder_default, QtWidgets.QStyle.SP_DialogOpenButton)
        self.job_io = QtWidgets.QLineEdit(job_default)
        self.client_io = QtWidgets.QLineEdit(client_default)
        self.client_masses_io = QtWidgets.QTextEdit(client_wt_IDs_default)

        self.mass_set_table = QtWidgets.QTableWidget()
        self.cb_stds_io = QtWidgets.QComboBox()
        self.cb_checks_io = QtWidgets.QComboBox()

        self.drift_io = QtWidgets.QComboBox()
        self.drift_io.addItems(['auto select', 'no drift', 'linear drift', 'quadratic drift', 'cubic drift'])
        self.timed_io = QtWidgets.QComboBox()
        self.timed_io.addItems(['NO', 'YES'])
        self.corr_io = QtWidgets.QLineEdit('None')

        self.ambient_form = QtWidgets.QFormLayout()

        self.equipment_table = QtWidgets.QTableWidget()

        self.acceptance_form = QtWidgets.QFormLayout()

        self.registers_table = QtWidgets.QTableWidget()

        self.go = Button(text='Save settings', left_click=self.save_cfg)

    def arrange_housekeeping_box(self):
        formGroup = QtWidgets.QGroupBox()
        formlayout = QtWidgets.QFormLayout()

        formlayout.addRow(label('Configuration file'), self.config_io)
        formlayout.setWidget(1, 2, self.load_from_config_but)
        formlayout.addRow(label('Folder for saving data'), self.folder_io)
        formlayout.addRow(label('Job'), self.job_io)
        formlayout.addRow(label('Client'), self.client_io)
        formlayout.addRow(label('List of client masses'), self.client_masses_io)

        formGroup.setLayout(formlayout)

        return formGroup

    def arrange_options_box(self):
        optionsGroup = QtWidgets.QGroupBox('Options for analysis')
        formlayout = QtWidgets.QFormLayout()
        formlayout.addRow(label('Drift correction'), self.drift_io)
        formlayout.addRow(label('Use measurement times?'), self.timed_io)
        formlayout.addRow(label('Correlations between standards'), self.corr_io)
        optionsGroup.setLayout(formlayout)

        return optionsGroup

    def make_mass_set_table(self, root=None):
        headers = ['Tag', 'Path to set file']
        self.mass_set_table.setColumnCount(len(headers))
        self.mass_set_table.setHorizontalHeaderLabels(headers)
        if root:
            numrows=len(root.find('standards'))
        else:
            numrows = 2
        self.mass_set_table.setRowCount(numrows)
        for i in range(numrows):
            self.mass_set_table.setCellWidget(i, 0, QtWidgets.QLineEdit())
            self.mass_set_table.setCellWidget(i, 1, FileSelect("", QtWidgets.QStyle.SP_DialogOpenButton))
            if root:
                self.mass_set_table.cellWidget(i, 0).setText(str(root.find('standards')[i].tag))
                self.mass_set_table.cellWidget(i, 1).textbox.setText(str(root.find('standards')[i].text))
            self.mass_set_table.cellWidget(i, 0).textChanged.connect(self.update_refmasssetselector)
        self.mass_set_table.resizeColumnsToContents()
        header = self.mass_set_table.horizontalHeader()
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)

    @Slot(str)
    def update_refmasssetselector(self):
        std = self.cb_stds_io.currentText()         # the currently selected std set
        check = self.cb_checks_io.currentText()     # the currently selected check set
        stds = ['None']                             # all available std set tags
        checks = ['None']                           # all available check set tags
        for i in range(self.mass_set_table.rowCount()):
            tag = self.mass_set_table.cellWidget(i, 0).text()
            stds.append(tag)
            checks.append(tag)
        self.cb_stds_io.clear()
        self.cb_checks_io.clear()
        self.cb_stds_io.addItems(stds)
        self.cb_checks_io.addItems(checks)
        self.cb_stds_io.setCurrentText(std)
        self.cb_checks_io.setCurrentText(check)

    def arrange_refmasses_box(self):
        ref_masses_box = QtWidgets.QGroupBox("Reference Masses")
        self.make_mass_set_table()
        formlayout = QtWidgets.QFormLayout()
        formlayout.setWidget(0, 2, self.mass_set_table)
        formlayout.addRow(label('Standard mass set'), self.cb_stds_io)
        formlayout.addRow(label('Check mass set'), self.cb_checks_io)

        ref_masses_box.setLayout(formlayout)
        return ref_masses_box

    def arrange_ambient(self):
        ambient = QtWidgets.QGroupBox('Limits on Ambient Conditions')
        self.ambient_form.addRow(label('Min temp {}'.format(IN_DEGREES_C)), QtWidgets.QLineEdit())
        self.ambient_form.addRow(label('Max temp {}'.format(IN_DEGREES_C)), QtWidgets.QLineEdit())
        self.ambient_form.addRow(label('Min RH (%)'), QtWidgets.QLineEdit())
        self.ambient_form.addRow(label('Max RH (%)'), QtWidgets.QLineEdit())
        self.ambient_form.addRow(label('Max temp change {}'.format(IN_DEGREES_C)), QtWidgets.QLineEdit())
        self.ambient_form.addRow(label('Max RH change (%)'), QtWidgets.QLineEdit())
        ambient.setLayout(self.ambient_form)
        return ambient

    def load_equip_registers(self):
        pass

    def make_equipment_table(self, root=None):
        ## this isn't really what I want though - need the entries here to match available balances in equip register!
        headers = ['Alias', 'Manufacturer', 'Model']
        self.equipment_table.setColumnCount(len(headers))
        self.equipment_table.setHorizontalHeaderLabels(headers)
        if root:
            equip = root.findall('equipment')
            numrows=len(equip)
        else:
            numrows = 2
        self.equipment_table.setRowCount(numrows)
        for i in range(numrows):
            for j in range(len(headers)):
                self.equipment_table.setCellWidget(i, j, QtWidgets.QLineEdit())
        # if root:
        #     for i, e in enumerate(root.findall('equipment')):
        #         self.equipment_table.cellWidget(i, 0).setText(e[0])
        #         self.equipment_table.cellWidget(i, 1).textbox.setText(str(root.find('standards')[i].text))

        self.equipment_table.resizeColumnsToContents()
        header = self.equipment_table.horizontalHeader()
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)


    def arrange_widget_layout(self):
        formGroup = self.arrange_housekeeping_box()
        optionsGroup = self.arrange_options_box()
        ref_masses_box = self.arrange_refmasses_box()
        ambient = self.arrange_ambient()
        self.setWindowTitle("Edit Configuration")

        layout = QtWidgets.QGridLayout()
        layout.addWidget(formGroup, 0, 0)
        layout.addWidget(optionsGroup, 1, 0)
        layout.addWidget(ref_masses_box, 0, 1)
        layout.addWidget(ambient, 1, 1)
        layout.addWidget(self.go, 2, 2)
        layout.addWidget(self.equipment_table, 0, 2)

        self.setLayout(layout)

    def load_from_config(self):
        if os.path.isfile(self.config_io.textbox.text()):
            # try:
            root = Config(self.config_io.textbox.text()).root

            self.folder_io.textbox.setText(root.find('save_folder').text)
            self.job_io.setText(root.find('job').text)
            self.client_io.setText(root.find('client').text)
            self.client_masses_io.setText(root.find('client_masses').text)

            self.drift_io.setCurrentText(root.find('drift').text)
            self.timed_io.setCurrentText(root.find('use_times').text)
            self.corr_io.setText(root.find('correlations').text)

            self.make_mass_set_table(root)
            self.update_refmasssetselector()
            self.cb_stds_io.setCurrentText(root.find('std_set').text)
            self.cb_checks_io.setCurrentText(root.find('check_set').text)

            self.ambient_form.itemAt(0, 1).widget().setText(root.find('min_temp').text)
            self.ambient_form.itemAt(1, 1).widget().setText(root.find('max_temp').text)
            self.ambient_form.itemAt(2, 1).widget().setText(root.find('min_rh').text)
            self.ambient_form.itemAt(3, 1).widget().setText(root.find('max_rh').text)
            self.ambient_form.itemAt(4, 1).widget().setText(root.find('max_temp_change').text)
            self.ambient_form.itemAt(5, 1).widget().setText(root.find('max_rh_change').text)

            self.make_equipment_table(root)

            # self.acceptance(
            #     path = root.find('acceptance_criteria/path').text,
            #     sheet = root.find('acceptance_criteria/sheet').text
            # )

            # self.get_registers(root)

        else:
            log.error('Config file does not exist at {!r}'.format(self.config_io.textbox.text()))

    def save_cfg(self):
        """Set values for configuration variables"""
        c = Config(config_default)

        c.find('save_folder').text = self.folder_io.textbox.text()
        c.find('job').text = self.job_io.text()
        c.find('client').text = self.client_io.text()
        c.find('client_masses').text = self.client_masses_io.toPlainText()

        c.find('std_set').text = self.cb_stds_io.currentText()
        c.find('check_set').text = self.cb_checks_io.currentText()
        standards = c.find('standards')
        standards.clear()
        for i in range(self.mass_set_table.rowCount()):
            tag = self.mass_set_table.cellWidget(i, 0).text()
            path = self.mass_set_table.cellWidget(i, 1).textbox.text()
            if tag and path:
                element = utils.xml_element(tag, path)
                standards.append(element)

        c.find('drift').text = self.drift_io.currentText()

        c.find('use_times').text = self.timed_io.currentText()
        c.find('correlations').text = self.corr_io.text()

        c.find('min_temp').text = self.ambient_form.itemAt(0, 1).widget().text()
        c.find('max_temp').text = self.ambient_form.itemAt(1, 1).widget().text()
        c.find('min_rh').text = self.ambient_form.itemAt(2, 1).widget().text()
        c.find('max_rh').text = self.ambient_form.itemAt(3, 1).widget().text()
        c.find('max_temp_change').text = self.ambient_form.itemAt(4, 1).widget().text()
        c.find('max_rh_change').text = self.ambient_form.itemAt(5, 1).widget().text()

        acceptance = c.find('acceptance_criteria')
        acceptance.clear()
        # for i in range(self.mass_set_table.rowCount()):
        #     tag = self.mass_set_table.cellWidget(i, 0).text()
        #     path = self.mass_set_table.cellWidget(i, 1).textbox.text()
        #     if tag and path:
        #         element = utils.xml_element(tag, path)
        #         standards.append(element)

        newconfig = os.path.join(self.folder_io.textbox.text(), self.job_io.text() + '_config.xml')
        with open(newconfig, mode='w', encoding='utf-8') as fp:
            fp.write(utils.convert_to_xml_string(c.root))

        return newconfig


if __name__ == "__main__":
    import sys
    from msl.qt import application, excepthook

    sys.excepthook = excepthook

    gui = application()

    widgey = ConfigEditor()
    widgey.arrange_widget_layout()
    widgey.show()

    gui.exec()