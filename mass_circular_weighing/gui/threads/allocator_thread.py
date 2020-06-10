from msl.qt import Thread, Worker, Signal, QtCore, QtWidgets

from ..widgets.aw_pos_allocator import AllocatorDialog


class AllocatorWorker(Worker):

    def __init__(self, parent, *args, **kwargs):
        super(AllocatorWorker, self).__init__()
        self.parent = parent
        self.args = args
        self.kwargs = kwargs

    def process(self):
        self.parent.signal_prompt.emit(self.args, self.kwargs)


class AllocatorThread(Thread):

    signal_prompt = Signal(tuple, dict)
    signal_prompt_done = Signal()

    def __init__(self):
        super(AllocatorThread, self).__init__(AllocatorWorker)
        self.reply = None
        self.signal_prompt.connect(self.allocator)

    def allocator(self, args, kwargs):
        """Popup the allocator Dialog widget"""
        w = AllocatorDialog(args[0], args[1])
        w.exec()
        self.reply = w.positions, w.pos_to_centre, w.centrings, w.cal_pos, w.want_adjust
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
            self.allocator(args, kwargs)
        else:
            self.start(self, *args, **kwargs)


