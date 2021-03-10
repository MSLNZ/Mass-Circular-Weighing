"""
A custom widget for browsing for files and folders
"""
from msl.qt import QtWidgets, Button, prompt, utils

from ...constants import sample_data_folder, mass_folder, mydrive
from ...log import log


def label(name):
    lbl = QtWidgets.QLabel(name)
    lbl.setWordWrap(True)
    return lbl


class Browse(QtWidgets.QWidget):

    def __init__(self, default, icon, find='folder', pattern=None):
        """A browse widget which combines a textbox linked with a file or folder browse pop-up.
        Default is a browser that looks for a folder.

        Parameters
        ----------
        default
        icon
        find : str
            this argument specifies which type of browse widget is created: file or folder.
        pattern : None or str, optional
            restrict the type of file to accept via drag-drop
        """
        super(Browse, self).__init__()
        self.find = find
        self.textbox = QtWidgets.QLineEdit(default)

        self.pattern = pattern
        self.path = None
        self.setAcceptDrops(True)

        self.button = Button(icon=icon, left_click=self.display_browse)

        self.button.add_menu_item(text='Mass drive', triggered=self.mass_drive_selected)
        self.button.add_menu_item(text='G: drive', triggered=self.mydrive_selected)
        self.button.add_menu_item(text='Sample data', triggered=self.sampledata_selected)

        hbox = QtWidgets.QHBoxLayout()
        hbox.addWidget(self.textbox)
        hbox.addWidget(self.button)
        self.setLayout(hbox)

    def display_browse(self):
        if self.find == 'file':
            folder_text = prompt.filename(title=self.textbox.text(), directory=self.textbox.text())
        else:
            folder_text = prompt.folder(title=self.textbox.text(), directory=self.textbox.text())
        if folder_text:
            self.textbox.setText(folder_text)

    def mass_drive_selected(self):
        self.textbox.setText(mass_folder)
        self.display_browse()

    def mydrive_selected(self):
        self.textbox.setText(mydrive)
        self.display_browse()

    def sampledata_selected(self):
        self.textbox.setText(sample_data_folder)
        self.display_browse()

    def dragEnterEvent(self, event):
        paths = utils.drag_drop_paths(event, pattern=self.pattern)
        if paths:
            log.debug("drag enter or drop event from {}".format(paths))
            p = paths[0]
            if len(paths) > 1:
                p = prompt.item('Please select one only:', items=paths)
            event.accept()
            self.path = p
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        event.accept()

    def dropEvent(self, event):
        self.textbox.setText(self.path)
