
from msl.qt import QtWidgets, Button, prompt
from src.log import log


def label(label):
    return QtWidgets.QLabel(label)

class Browse(QtWidgets.QWidget):

    def __init__(self, default, icon):
        super(Browse, self).__init__()

        self.textbox = QtWidgets.QLineEdit(default)
        self.button = Button(icon=icon, left_click=self.display_folder)
        self.button.add_menu_item('Mass drive', triggered=self.mass_drive_selected)
        self.button.add_menu_item('H: drive', triggered=self.hdrive_selected)
        self.button.add_menu_item('Sample data', triggered=self.sampledata_selected)
        #self.button.add_menu_item('open browser', shortcut='CTRL+O')

        hbox = QtWidgets.QHBoxLayout()
        hbox.addWidget(self.textbox)
        hbox.addWidget(self.button)
        self.setLayout(hbox)

    def display_folder(self):
        folder_text = prompt.folder(self.textbox.text())
        self.textbox.setText(folder_text)

    def mass_drive_selected(self):
        #log.debug('Mass drive selected')
        self.textbox.setText(r'I:\MSL\Private\Mass')

    def hdrive_selected(self):
        #log.debug('H: drive selected')
        self.textbox.setText(r'H:')

    def sampledata_selected(self):
        #log.debug('sample data selected')
        self.textbox.setText(r'I:\MSL\Private\Mass\transfer\Balance Software\Sample Data')
