"""
A thread to pop-up the Config Editor from the main gui window
"""
from msl.qt import Thread, Worker, Signal, QtCore, QtWidgets

from ..widgets.config_editor import ConfigEditor


class ConfigEditorWorker(Worker):

    def __init__(self, parent, *args, **kwargs):
        super(ConfigEditorWorker, self).__init__()
        self.parent = parent
        self.args = args
        self.kwargs = kwargs

    def process(self):
        self.parent.signal_prompt.emit(self.args, self.kwargs)


class ConfigEditorThread(Thread):

    signal_prompt = Signal(tuple, dict)
    signal_prompt_done = Signal()

    def __init__(self):
        super(ConfigEditorThread, self).__init__(ConfigEditorWorker)
        self.reply = None
        self.signal_prompt.connect(self.config_editor)

    def config_editor(self, *args, **kwargs):
        """Popup a prompt"""
        w = ConfigEditor()
        w.config_io.textbox.setText(str(args[0][0]))
        w.exec()
        self.reply = w.new_config
        if QtWidgets.QApplication.instance() is not None:
            self.signal_prompt_done.emit()

    def wait_for_prompt_reply(self):
        """Block loop until the prompt popup window is closed"""
        if QtWidgets.QApplication.instance() is not None:
            loop = QtCore.QEventLoop()
            self.signal_prompt_done.connect(loop.quit)
            loop.exec_()
        return self.reply

    def show(self, *args, **kwargs):
        self.reply = None
        if QtWidgets.QApplication.instance() is None:
            self.config_editor(*args, **kwargs)
        else:
            self.start(self, *args, **kwargs)

