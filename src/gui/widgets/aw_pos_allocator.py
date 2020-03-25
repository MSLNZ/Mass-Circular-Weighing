from msl.qt import Thread, Worker, prompt, Signal, QtCore, QtWidgets, QtGui, utils


def label(name):
    lbl = QtWidgets.QLabel(name)
    lbl.wordWrap = True
    return lbl


def allocator(num_pos, scheme_entry):
    """

    Parameters
    ----------
    num_pos : int
    scheme_entry : str

    Returns
    -------

    """
    window = QtWidgets.QWidget()
    f = QtGui.QFont()
    f.setPointSize(FONTSIZE)
    window.setFont(f)
    window.setWindowTitle('Position Allocator')
    # window.closeEvent =
    geo = utils.screen_geometry()
    window.resize(geo.width() // 2, geo.height())

    for i in range(num_pos):
        print(i)
    wtgrps = scheme_entry.split()
    for wtgrp in wtgrps:
        print(wtgrp)

    return window

    # self.scheme_entry = label('scheme_entry')
    # self.nominal_mass = label('nominal')
    # self.run_id = label('0')
    # self.cycle = label('0')
    # self.position = label('0')
    # self.reading = label('0')



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
    from src.gui.prompt_thread import PromptThread

    prompt_thread = PromptThread()
    from src.constants import FONTSIZE

    num_pos = 5

    def allocate_positions(wtgrps):
        positions = []
        for wtgrp in wtgrps:
            prompt_thread.show('integer', 'Please select position for '+wtgrp, minimum=1, maximum=num_pos, font=FONTSIZE,
                               title='Balance Preparation')
            pos = prompt_thread.wait_for_prompt_reply()
            positions.append(pos)

        # if positions are all unique, accept, otherwise return
        return positions

    se = 'A B C D'
    wtgrps = se.split()

    print(allocate_positions(wtgrps))
