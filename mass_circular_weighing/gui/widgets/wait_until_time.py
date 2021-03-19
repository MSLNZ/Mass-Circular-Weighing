from datetime import datetime, timedelta

from msl.qt import QtCore, QtGui, QtWidgets, Button

from ...constants import FONTSIZE


def chop_microseconds(delta):
    return delta - timedelta(microseconds=delta.microseconds)


class WaitUntilTimeDisplay(QtWidgets.QDialog):

    def __init__(self, loop_delay=1000, message=None, title=None, parent=None, font_family='Helvetica'):
        """This widget counts down to a target time, and displays the time remaining until then.

        Parameters
        ----------
        loop_delay : int
            update interval in ms
        message : str, optional
            message to display to explain what will happen when the countdown is reached
        title : str
            title for dialog window
        parent : QtWidget or app ?, optional
        font_family : str, optional
        """
        print("kwargs in display widget", loop_delay, message, title, parent, font_family)
        super().__init__(parent=parent)

        if title is None:
            title = f"Delay Start"
        self.setWindowTitle(title)

        font = QtGui.QFont(font_family, pointSize=FONTSIZE)

        layout = QtWidgets.QVBoxLayout()

        # display a message if one has been passed
        if message is not None:
            print(message)
            msg = QtWidgets.QLabel(message)
            msg.setWordWrap(True)
            msg.setFont(font)
            layout.addWidget(msg)

        # make a date and time edit box for the target time
        self.intro = QtWidgets.QLabel("Waiting until:")
        self.intro.setFont(font)
        layout.addWidget(self.intro)

        self.dte = QtWidgets.QDateTimeEdit()
        self.dte.setFont(font)
        self.dte.setDateTime(QtCore.QDateTime.currentDateTime().addSecs(3600))
        layout.addWidget(self.dte)

        # show how long it will wait for
        self.status = QtWidgets.QLabel()
        self.status.setFont(font)
        self.loop()
        layout.addWidget(self.status)

        # add an override to start the weighing now
        start_now = Button(text="Start now", left_click=self.start_now)
        start_now.setFont(font)
        layout.addWidget(start_now)

        self.setLayout(layout)

        self.go = False

        self._loop_delay = loop_delay
        print(self._loop_delay)
        self._loop_timer = QtCore.QTimer()
        self._loop_timer.timeout.connect(self.loop)
        self._loop_timer.start(self._loop_delay)

        # allow user to change the time?

        self.closeEvent = self._shutdown

    @property
    def target_time(self):
        """Return displayed time as normal datetime type"""
        try:  # PyQt
            dto = self.dte.dateTime().toPyDateTime()
        except:  # PySide
            dto = self.dte.dateTime().toPython()
        return dto

    @property
    def loop_delay(self):
        """:class:`int`: The time delay, in milliseconds, between successive calls to the :meth:`loop`."""
        return self._loop_delay

    @property
    def loop_timer(self):
        """:class:`QtCore.QTimer`: The reference to the :meth:`loop`\'s timer."""
        return self._loop_timer

    def _stop_timers(self):
        """Stop and delete the timers."""
        if self._loop_timer:
            self._loop_timer.stop()
            self._loop_timer = None

    def time_remaining(self):
        """Work out the remaining time"""
        now = datetime.now()
        time_remaining = self.target_time - now

        return time_remaining

    def loop(self):
        """Update the label and determine if the target time has been reached"""
        tr = self.time_remaining()
        self.status.setText(
            f"Time remaining: {chop_microseconds(tr)}\n"
        )
        if tr.total_seconds() < 0:
            self.start_now()

    def start_now(self):
        """Exit out of the dialog, setting the go attribute to True"""
        self.go = True
        self.close()

    def _shutdown(self, event):
        """Abort the loop"""
        self._stop_timers()
        event.accept()
