"""
A thread to pop-up the Delay Start Window from the Circular Weighing pop-up window
"""
from msl.qt import (
    Thread,
    Worker,
    Signal,
    QtCore,
    QtWidgets
)

from mass_circular_weighing.gui.widgets.wait_until_time import WaitUntilTimeDisplay


class WaitWorker(Worker):

    def __init__(self, parent, *args, **kwargs):
        super(WaitWorker, self).__init__()
        self.parent = parent
        self.args = args
        self.kwargs = kwargs

    def process(self):
        self.parent.signal_prompt.emit(self.args, self.kwargs)


class WaitThread(Thread):

    signal_prompt = Signal(tuple, dict)
    signal_prompt_done = Signal()

    def __init__(self):
        super(WaitThread, self).__init__(WaitWorker)
        self.reply = None
        self.signal_prompt.connect(self.display)

    def display(self, kwargs):
        """Popup the allocator Dialog widget"""
        print("display", kwargs)
        w = WaitUntilTimeDisplay(**kwargs)
        w.exec()
        self.reply = w.go
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
            self.display(kwargs)
        else:
            self.start(self, *args, **kwargs)


if __name__ == '__main__':
    pt = WaitThread()
    pt.show(message=f"Delayed start for weighing for 100.", loop_delay=1000,)
    print(pt.wait_for_prompt_reply())
