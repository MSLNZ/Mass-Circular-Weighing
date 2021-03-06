"""
A thread to pop-up a prompt from another window
"""
from msl.qt import Thread, Worker, prompt, Signal, QtCore, QtWidgets


class PromptWorker(Worker):

    def __init__(self, parent, *args, **kwargs):
        super(PromptWorker, self).__init__()
        self.parent = parent
        self.args = args
        self.kwargs = kwargs

    def process(self):
        self.parent.signal_prompt.emit(self.args, self.kwargs)


class PromptThread(Thread):

    signal_prompt = Signal(tuple, dict)
    signal_prompt_done = Signal()

    def __init__(self):
        super(PromptThread, self).__init__(PromptWorker)
        self.reply = None
        self.signal_prompt.connect(self.prompt)

    def prompt(self, args, kwargs):
        """Popup a prompt"""
        self.reply = getattr(prompt, args[0])(args[1], *args[2:], **kwargs)
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
            self.prompt(args, kwargs)
        else:
            self.start(self, *args, **kwargs)


if __name__ == '__main__':
    pt = PromptThread()
    pt.show('integer', 'Please select position', minimum=1, maximum=5,
                       title='Balance Preparation')
    print('Position:', pt.wait_for_prompt_reply())
