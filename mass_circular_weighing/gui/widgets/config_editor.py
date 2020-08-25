import os

from msl.qt import QtWidgets, Button, Signal, Slot
from msl.equipment import Config, utils

from ...log import log
from ...constants import \
    IN_DEGREES_C, config_default, save_folder_default, job_default, client_default, client_wt_IDs_default
from .browse import Browse, label


class ConfigEditor(QtWidgets.QDialog):

    update_ref_mass_sets = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self.config_io = Browse(
            config_default, QtWidgets.QStyle.SP_DialogOpenButton, find='file', pattern='*.xml'
        )
        self.config_io.textbox.textChanged.connect(self.load_from_config)

        self.folder_io = Browse(
            save_folder_default, QtWidgets.QStyle.SP_DialogOpenButton, find='folder'
        )
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
        self.bal_reg_form = QtWidgets.QFormLayout()
        self.equip_reg_form = QtWidgets.QFormLayout()
        self.connections_form = QtWidgets.QFormLayout()
        self.acceptance_form = QtWidgets.QFormLayout()

        self.go = Button(text='Save settings', left_click=self.save_cfg)

        self.arrange_widget_layout()

    @property
    def new_config(self):
        newconfig = os.path.join(self.folder_io.textbox.text(), self.job_io.text() + '_config.xml')
        return newconfig

    def arrange_housekeeping_box(self):
        formGroup = QtWidgets.QGroupBox()
        formlayout = QtWidgets.QFormLayout()

        formlayout.addRow(label('Configuration file'), self.config_io)
        formlayout.addRow(label('Folder for saving data'), self.folder_io)
        formlayout.addRow(label('Job code'), self.job_io)
        formlayout.addRow(label('Client'), self.client_io)
        formlayout.addRow(label(
            'List of client masses\n'
            '(separate by spaces)'), self.client_masses_io)

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
        headers = ['Set name', 'Path to set file']
        self.mass_set_table.setColumnCount(len(headers))
        self.mass_set_table.setHorizontalHeaderLabels(headers)
        if root:
            numrows=len(root.find('standards'))
        else:
            numrows = 2
        self.mass_set_table.setRowCount(numrows)
        for i in range(numrows):
            self.mass_set_table.setCellWidget(i, 0, QtWidgets.QLineEdit())
            self.mass_set_table.setCellWidget(
                i, 1, Browse("", QtWidgets.QStyle.SP_DialogOpenButton, find='file', pattern='*.set')
            )
            if root:
                self.mass_set_table.cellWidget(i, 0).setText(str(root.find('standards')[i].tag))
                self.mass_set_table.cellWidget(i, 1).textbox.setText(str(root.find('standards')[i].text))
            self.mass_set_table.cellWidget(i, 0).textChanged.connect(self.update_refmasssetselector)
        self.mass_set_table.resizeColumnsToContents()
        self.mass_set_table.resizeRowsToContents()
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

    def extract_equip_registers(self, root):
        regs = root.find('registers').findall('register')

        for reg in regs:
            attr = reg.attrib
            if len(attr.keys()) < 2:
                # type is standard Equipment Register
                for element in reg:
                    if element.tag == 'path':
                        self.equip_reg_form.itemAt(0, 1).widget().textbox.setText(str(element.text))
                    if element.tag == 'sheet':
                        self.equip_reg_form.itemAt(1, 1).widget().setText(str(element.text))
            elif ' weighing_mode' in attr['user_defined'].split(','):
                # type is Balance Register
                for element in reg:
                    if element.tag == 'path':
                        self.bal_reg_form.itemAt(0, 1).widget().textbox.setText(str(element.text))
                    if element.tag == 'sheet':
                        self.bal_reg_form.itemAt(1, 1).widget().setText(str(element.text))
            else:
                print('Unknown register type with attributes {}'.format(attr))

    def make_reg_box(self, form):
        form.removeRow(0)
        form.removeRow(1)
        form.addRow(label('Path'), Browse("", QtWidgets.QStyle.SP_DialogOpenButton, find='file', pattern='*.xls*'))
        form.addRow(label('Sheet'), QtWidgets.QLineEdit())

    def make_acceptance_box(self):
        self.acceptance_form = QtWidgets.QFormLayout()
        self.acceptance_form.addRow(
            label('Path'),
            Browse("", QtWidgets.QStyle.SP_DialogOpenButton, find='file', pattern='*.xls*')
        )
        self.acceptance_form.addRow(label('Sheet'), QtWidgets.QLineEdit())
        self.acceptance_form.addRow(label('Exclusion limit'), QtWidgets.QDoubleSpinBox())

    def get_path_sheet_excl(self, form):
        data = {'path': form.itemAt(0, 1).widget().textbox.text(),
                'sheet': form.itemAt(1, 1).widget().text()}
        try:
            data['EXCL'] = form.itemAt(2, 1).widget().text()
            return data
        except AttributeError:
            return data

    def arrange_registers_box(self):
        registers_box = QtWidgets.QGroupBox("Registers")

        balances = QtWidgets.QGroupBox('Balance Register')
        self.make_reg_box(self.bal_reg_form)
        balances.setLayout(self.bal_reg_form)

        equip = QtWidgets.QGroupBox('Equipment Register (if needed)')
        self.make_reg_box(self.equip_reg_form)
        equip.setLayout(self.equip_reg_form)

        connexions = QtWidgets.QGroupBox('Connections Register')
        self.make_reg_box(self.connections_form)
        connexions.setLayout(self.connections_form)

        ac_box = QtWidgets.QGroupBox('Acceptance Criteria')
        self.make_acceptance_box()
        ac_box.setLayout(self.acceptance_form)

        registers_box_layout = QtWidgets.QVBoxLayout()
        registers_box_layout.addWidget(balances)
        registers_box_layout.addWidget(equip)
        registers_box_layout.addWidget(connexions)
        registers_box_layout.addWidget(ac_box)
        registers_box.setLayout(registers_box_layout)

        return registers_box

    def arrange_widget_layout(self):
        self.setWindowTitle("Edit Configuration File")

        formGroup = self.arrange_housekeeping_box()
        optionsGroup = self.arrange_options_box()
        lhs = QtWidgets.QVBoxLayout()
        lhs.addWidget(formGroup)
        lhs.addWidget(optionsGroup)

        ref_masses_box = self.arrange_refmasses_box()
        ambient = self.arrange_ambient()
        clay = QtWidgets.QVBoxLayout()
        clay.addWidget(ref_masses_box)
        clay.addWidget(ambient)

        registers_box = self.arrange_registers_box()
        rhs = QtWidgets.QVBoxLayout()
        rhs.addWidget(registers_box)
        rhs.addWidget(self.go)

        layout = QtWidgets.QHBoxLayout()
        layout.addLayout(lhs, stretch=2)
        layout.addLayout(clay, stretch=4)
        layout.addLayout(rhs, stretch=1)

        self.setLayout(layout)

        self.load_from_config()

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

            # fill ambient form
            self.ambient_form.itemAt(0, 1).widget().setText(root.find('min_temp').text)
            self.ambient_form.itemAt(1, 1).widget().setText(root.find('max_temp').text)
            self.ambient_form.itemAt(2, 1).widget().setText(root.find('min_rh').text)
            self.ambient_form.itemAt(3, 1).widget().setText(root.find('max_rh').text)
            self.ambient_form.itemAt(4, 1).widget().setText(root.find('max_temp_change').text)
            self.ambient_form.itemAt(5, 1).widget().setText(root.find('max_rh_change').text)

            # fill balance and equipment register boxes
            self.extract_equip_registers(root)

            # fill acceptance_box:
            path = root.find('acceptance_criteria/path').text
            sheet = root.find('acceptance_criteria/sheet').text
            excl = root.find('acceptance_criteria/EXCL').text
            self.acceptance_form.itemAt(0, 1).widget().textbox.setText(path)
            self.acceptance_form.itemAt(1, 1).widget().setText(sheet)
            self.acceptance_form.itemAt(2, 1).widget().setValue(float(excl))

            # fill connections_form box
            self.connections_form.itemAt(0, 1).widget().textbox.setText(root.find('connections/connection/path').text)
            self.connections_form.itemAt(1, 1).widget().setText(root.find('connections/connection/sheet').text)

        else:
            log.error('Config file does not exist at {!r}'.format(self.config_io.textbox.text()))

    def save_cfg(self):
        """Set values for configuration variables"""
        c = Config(self.config_io.textbox.text())

        # update housekeeping
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

        # update ambient
        c.find('min_temp').text = self.ambient_form.itemAt(0, 1).widget().text()
        c.find('max_temp').text = self.ambient_form.itemAt(1, 1).widget().text()
        c.find('min_rh').text = self.ambient_form.itemAt(2, 1).widget().text()
        c.find('max_rh').text = self.ambient_form.itemAt(3, 1).widget().text()
        c.find('max_temp_change').text = self.ambient_form.itemAt(4, 1).widget().text()
        c.find('max_rh_change').text = self.ambient_form.itemAt(5, 1).widget().text()

        # update registers
        regs = c.find('registers')
        regs.clear()

        bal_reg = utils.xml_element(
            'register',
            team="M&amp;P",
            user_defined="unit, ambient_monitoring, weighing_mode, stable_wait, resolution, pos, handler"
        )
        data = self.get_path_sheet_excl(self.bal_reg_form)
        for key, value in data.items():
            e = utils.xml_element(tag=key, text=value)
            bal_reg.append(e)
        regs.append(bal_reg)

        equip_reg = utils.xml_element(
            'register',
            team="M&amp;P"
        )
        data = self.get_path_sheet_excl(self.equip_reg_form)
        for key, value in data.items():
            e = utils.xml_element(tag=key, text=value)
            equip_reg.append(e)
        regs.append(equip_reg)

        acceptance = c.find('acceptance_criteria')
        data = self.get_path_sheet_excl(self.acceptance_form)
        for key, value in data.items():
            acceptance.find(key).text = value

        connections = c.find('connections/connection')
        data = self.get_path_sheet_excl(self.connections_form)
        for key, value in data.items():
            connections.find(key).text = value

        # save file
        with open(self.new_config, mode='w', encoding='utf-8') as fp:
            fp.write(utils.convert_to_xml_string(c.root))

        self.close()



