from msl.qt import QtWidgets, Button, prompt

from ...constants import sample_data_folder, mass_folder, H_drive


def label(name):
    lbl = QtWidgets.QLabel(name)
    lbl.setWordWrap(True)
    return lbl


class Browse(QtWidgets.QWidget):

    def __init__(self, default, icon, find='folder'):
        """A browse widget which combines a textbox linked with a file or folder browse pop-up.
        Default is a browser that looks for a folder.

        Parameters
        ----------
        default
        icon
        find : str
            this argument specifies which type of browse is created: file or folder.
        """
        super(Browse, self).__init__()

        self.textbox = QtWidgets.QLineEdit(default)
        if find == 'folder':
            self.button = Button(icon=icon, left_click=self.display_folder)
        elif find == 'file':
            self.button = Button(icon=icon, left_click=self.display_file)
        else:
            self.button = Button(icon=icon)
        self.button.add_menu_item(text='Mass drive', triggered=self.mass_drive_selected)
        self.button.add_menu_item(text='H: drive', triggered=self.hdrive_selected)
        self.button.add_menu_item(text='Sample data', triggered=self.sampledata_selected)

        hbox = QtWidgets.QHBoxLayout()
        hbox.addWidget(self.textbox)
        hbox.addWidget(self.button)
        self.setLayout(hbox)

    def display_folder(self):
        folder_text = prompt.folder(title=self.textbox.text(), directory=self.textbox.text())
        self.textbox.setText(folder_text)

    def display_file(self):
        folder_text = prompt.filename(title=self.textbox.text(), directory=self.textbox.text())
        self.textbox.setText(folder_text)

    def mass_drive_selected(self):
        self.textbox.setText(mass_folder)

    def hdrive_selected(self):
        self.textbox.setText(H_drive)

    def sampledata_selected(self):
        self.textbox.setText(sample_data_folder)
