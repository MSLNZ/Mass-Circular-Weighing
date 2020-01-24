from msl.qt import QtWidgets, Button, prompt


def label(name):
    return QtWidgets.QLabel(name)


class Browse(QtWidgets.QWidget):

    def __init__(self, default, icon):
        super(Browse, self).__init__()

        self.textbox = QtWidgets.QLineEdit(default)
        self.button = Button(icon=icon, left_click=self.display_folder)
        self.button.add_menu_item(text='Mass drive', triggered=self.mass_drive_selected)
        self.button.add_menu_item(text='H: drive', triggered=self.hdrive_selected)
        self.button.add_menu_item(text='Sample data', triggered=self.sampledata_selected)
        #self.button.add_menu_item('open browser', shortcut='CTRL+O')

        hbox = QtWidgets.QHBoxLayout()
        hbox.addWidget(self.textbox)
        hbox.addWidget(self.button)
        self.setLayout(hbox)

    def display_folder(self):
        folder_text = prompt.folder(title=self.textbox.text(), directory=self.textbox.text())
        self.textbox.setText(folder_text)

    def mass_drive_selected(self):
        self.textbox.setText(r'I:\MSL\Private\Mass')

    def hdrive_selected(self):
        self.textbox.setText(r'H:')

    def sampledata_selected(self):
        self.textbox.setText(r'I:\MSL\Private\Mass\transfer\Balance Software\Sample Data')


class FileSelect(QtWidgets.QWidget):

    def __init__(self, default, icon):
        super(FileSelect, self).__init__()

        self.textbox = QtWidgets.QLineEdit(default)
        self.button = Button(icon=icon, left_click=self.display_file)
        self.button.add_menu_item(text='Mass drive', triggered=self.mass_drive_selected)
        self.button.add_menu_item(text='H: drive', triggered=self.hdrive_selected)
        self.button.add_menu_item(text='Sample data', triggered=self.sampledata_selected)
        #self.button.add_menu_item('open browser', shortcut='CTRL+O')

        hbox = QtWidgets.QHBoxLayout()
        hbox.addWidget(self.textbox)
        hbox.addWidget(self.button)
        self.setLayout(hbox)

    def display_file(self):
        folder_text = prompt.filename(title=self.textbox.text(), directory=self.textbox.text())
        self.textbox.setText(folder_text)

    def mass_drive_selected(self):
        self.textbox.setText(r'I:\MSL\Private\Mass')

    def hdrive_selected(self):
        self.textbox.setText(r'H:')

    def sampledata_selected(self):
        self.textbox.setText(r'I:\MSL\Private\Mass\transfer\Balance Software\Sample Data')