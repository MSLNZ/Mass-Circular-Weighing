'''Class for Mettler Toledo Balance with computer interface and carousel weight changer'''
from time import perf_counter

from msl.equipment import MSLTimeoutError
from msl.qt import prompt, application

from ..log import log
from .mettler import MettlerToledo, ERRORCODES

from ..gui.threads.allocator_thread import AllocatorThread
allocator = AllocatorThread()


class AWBalCarousel(MettlerToledo):
    def __init__(self, record, reset=False, ):
        """Initialise Mettler Toledo Balance,
        with automatic weight loading in carousel configuration,
        via computer interface.

        Parameters
        ----------
        record : equipment record object
            get via Application(config).equipment[alias]
            Requires an MSL.equipment config.xml file
        reset : bool
            True if reset balance desired
        """
        super().__init__(record)

        self.num_pos = record.user_defined['pos']  # num_pos is the total number of available loading positions
        # num_pos should be 4 for the carousel balances
        self._positions = None

        self.lift_pos = None
        self.rot_pos = None

        self.move_time = 0

        self.is_centered = False

        self.handler = None

    def identify_handler(self):
        """Reports handler model and software version.
        (from AX1006 manual)
        string returned of form: H1006, serial number #xxxx, software V x.xx. ready

        Returns
        -------

        """
        h_str = self._query("IDENTIFY")
        # TODO: confirm that the correct handler is connected
        print(h_str)

    @property
    def mode(self):
        return 'aw_c'

    def tare_bal(self):
        """Tares balance with load"""
        self.lift_to('weighing')
        m = self._query("Z").split()
        # TODO: check if MettlerToledo tare_bal using 'T' works instead
        if m[1] == 'S':
            log.info('Balance tared with value '+m[2]+' '+m[3])
            return
        self._raise_error(m[0]+' '+m[1])

    @property
    def positions(self):
        """Returns a list of positions for the weight groups in the order the groups appear in the scheme entry."""
        return self._positions

    def allocate_positions(self, wtgrps, ):
        """Assign weight groups to weighing positions using the AllocatorDialog

        Parameters
        ----------
        wtgrps : list
            list of weight groups as strings

        Returns
        -------
        self.positions : list
            Returns a list of positions for the weight groups in the order the groups appear in the scheme entry.
        """
        if len(wtgrps) > self.num_pos:
            log.error('Too many weight groups for balance')
            return None
        allocator.show(self.num_pos, wtgrps)
        self._positions = allocator.wait_for_prompt_reply()
        if self.positions is None:
            log.error("Position assignment incomplete")
            self._want_abort = True

        return self.positions

    def get_status(self):
        """Update current rotational and lift position of the turntable.
        Possible string replies for AX10005:
        <a> in top position. ready
        <a> in panbraking position. ready
        <a> in weighing position. ready
        <a> in calibration position. ready
        <a> is an integer that represents the turntable position above the weighing pan.
        The AX1006 has only 'top' and 'weighing' positions.

        Returns
        -------
        tuple of rot_pos, lift_pos

        """
        status_str = self._query("STATUS")
        if len(status_str.split()) == 5 and status_str.split()[-1] == "ready":
            self.rot_pos = status_str.split()[0]
            self.lift_pos = status_str.split()[2]
            return self.rot_pos, self.lift_pos

    def move_to(self, pos):
        """Positions the weight at turntable position pos by the quickest route,
        in the top position above the weighing pan.
        The command performs lift operations if necessary.

        Parameters
        ----------
        pos : int
        """
        # takes integer position.
        if not 0 < pos <= self.num_pos:
            self._raise_error('POS')

        if not self.want_abort:
            log.info("Moving to position "+str(pos))
            # display "Handler Turning to Position: " + Weight
            self.connection.write("MOVE" + str(pos))  # Spaces are ignored by the handler

            reply = self.wait_for_reply()  # the message returned is either 'ready' or an error code
            if reply == "ready":
                return
            else:
                self._raise_error(get_key(reply))

    def time_move(self):
        if self.positions is None:
            log.warning("Weight groups must first be assigned to positions.")
            return
        if not self.want_abort:
            times = []
            print("Moving to last position")
            self.move_to(self.positions[-1])
            for pos in self.positions:
                print("Moving to position "+pos)
                t0 = perf_counter()
                self.move_to(pos)
                times.append(perf_counter() - t0)

            print(times, max(times))

            self.move_time = max(times) + 5  # want to add a wee buffer time here, say 5 s

    def lower_handler(self):
        """Lowers the turntable one lift position.
        For the AX1006, this command puts the turntable in the weighing position.
        For the AX10005, the turntable moves downward:
            – From the top to the panbraking position,
            – from the braking to the weighing position,
            – from the weighing to the calibration position.
        """
        if not self.want_abort:
            log.info("Sinking mass")
            # could get handler to display text such as "Sinking position: " + Weight here if desired
            self.connection.write("SINK")

            reply = self.wait_for_reply()

            if reply == "ERROR: In weighing position already. ready":  # AX1006 error
                log.warning(
                    "The turntable is in the weighing position and cannot be lowered further."
                )
                return

            if reply == "ERROR: In calibration position already. ready":  # AX10005 error
                log.warning(
                    "The turntable is in the calibration position and cannot be lowered further."
                )
                return

            elif reply == "ready":
                return

            else:
                self._raise_error(get_key(reply))

    def raise_handler(self):
        """Raises the turntable one lift position.
        For the AX1006, this command puts the turntable in the top position.
        For the AX10005, the turntable moves upward:
            – From the calibration position to the weighing position,
            – from the weighing position to the top position.
        """
        if not self.want_abort:
            log.info("Lifting mass")
            # could get handler to display text such as "Lifting position: " + Weight here if desired
            self.connection.write("LIFT")

            reply = self.wait_for_reply()

            if reply == "ERROR: In top position already. ready":
                log.warning(
                    "The turntable is in the top position and cannot be raised further."
                )
                return

            elif reply == "ready":
                return

            else:
                self._raise_error(get_key(reply))

    def lift_to(self, lift_position):
        """Lowers or raises handler to the lift position specified.

        Parameters
        ----------
        lift_position : string
            string for desired lift position. Allowed strings are: top, panbraking, weighing, calibration
        Returns
        -------
        """
        if self.record.model == "AX10005":
            lower_options = {'top': 0, 'panbraking': 1, 'weighing': 2, 'calibration': 3}
        else:
            lower_options = {'top': 0, 'weighing': 1}
        raise_options = {'top': 2, 'weighing': 1, 'calibration': 0}
        # note: calibration and panbraking positions are not relevant for AX1006
        rot_pos, current = self.get_status()
        lowers = lower_options[lift_position] - lower_options[current]
        if lowers < 0:
            raises = raise_options[lift_position] - raise_options[current]
            for i in range(raises):
                self.raise_handler()
            self.get_status()
        else:
            for i in range(lowers):
                self.lower_handler()
            self.get_status()

        assert self.lift_pos == lift_position

    def load_bal(self, mass, pos):
        while not self.want_abort:
            # start clock
            t0 = perf_counter()

            # do move
            self.move_to(pos)

            # wait for some time to make all moves same - and/or wait until the next 'weighing time'
            wait_for_elapse(self.move_time, start_time=t0)

            self.lift_to('weighing')
            # the lift_to function might be an unnecessary complication, but we'll see...

            # for AX1006, stable wait is 35 s
            # 'brake time' = 35 s

    def unload_bal(self, mass, pos):
        """Unloads mass from pan"""
        if not self.want_abort:
            self.lift_to('top')

    def centering(self, repeats):
        # TODO: add a centering routine - check this with Greg
        """Performs a centering routine

        Parameters
        ----------
        repeats : int
            number of times to raise/lower each weight
        Returns
        -------
        bool to indicate successful completion
        """
        for pos in self.positions:
            self.move_to(pos)
            for i in range(repeats):
                self.lift_to('weighing')
                # may want to add a wait here while it brakes if needed
                self.lift_to('top')

        """VBA routine for AX balances
        Private Sub CommandButton1_Click()
            Dim count As Integer
            Dim IncludedWeight(4) As Boolean
            Dim NoOfSinks As Integer
            Dim start As Boolean
            Dim Weight As Integer
            Const WaitTime As Integer = 15
            
            Call BalanceCheck
        
            IncludedWeight(1) = frmoutput.opt1.value
            IncludedWeight(2) = frmoutput.opt3.value
            IncludedWeight(3) = frmoutput.opt5.value
            IncludedWeight(4) = frmoutput.opt7.value
        
            NoOfSinks = Val(frmoutput.txtnum.value)
            start = True
            
            For Weight = 1 To 4
                If IncludedWeight(Weight) Then
                    If Not start Then
                        Call DoDelay("Waiting to stabilise", WaitTime)
                    Else
                        start = False
                    End If
                    
                    Call RoughTurn(Weight)
                    Call Lower(Weight)
                    Call DoDelay("Braking", WaitTime)
                    Call Raise(Weight)
                End If
            Next Weight
            
            Call DoDelay("Waiting to stabilise", WaitTime)
            
            For Weight = 1 To 4
                If IncludedWeight(Weight) Then
                    Call RoughTurn(Weight)
                    count = 1
                    Do While count <= NoOfSinks
                        Call Lower(Weight)
                        Call DoDelay("Braking", WaitTime)
                        Call Raise(Weight)
                        Call DoDelay("Waiting to Stabilise", WaitTime)
                        count = count + 1
                    Loop
                End If
            Next Weight
            
            RoughTurn (1)
            Lower (1)
            frmoutput.Close_AXCom_Port
            Unload frmoutput
        End Sub"""

        pass

    def wait_for_reply(self):
        """Utility function for movement commands MOVE, SINK and LIFT.
        Waits for string returned by these commands.

        Returns
        -------
        The string from the handler
        """
        app = application()
        t0 = perf_counter()

        while True:  # wait for handler to finish task
            app.processEvents()
            try:
                r = self.connection.read().split()
                if r:
                    print(r)  # for debugging only
                    return r
            except MSLTimeoutError:
                if perf_counter() - t0 > self.intcaltimeout:
                    raise TimeoutError("Movement took longer than expected")
                else:
                    log.info('Waiting for movement to end')


def wait_for_elapse(elapse_time, start_time=perf_counter()):
    """Wait for a specified time while allowing other events to be processed

    Parameters
    ----------
    elapse_time : int
        time to wait in seconds
    start_time : float
        perf_counter value at start time.
        If not specified, the elapsed time begins when the function is called.
    """
    app = application()
    time = perf_counter() - start_time
    while time < elapse_time:
        app.processEvents()
        time = perf_counter() - start_time


def get_key(val):
    """Looks for the error in ERRORCODES, a dictionary of known error codes for Mettler balances"""
    for key, value in ERRORCODES.items():
        if val == value:
            return key

    return None

