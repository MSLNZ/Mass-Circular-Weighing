'''Class for Mettler Toledo Balance with computer interface and carousel weight changer'''
# note: all movement commands check first if self.want_abort is True, in which case no movement occurs.

from time import perf_counter
import numpy as np

from msl.equipment import MSLTimeoutError
from msl.qt import application

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
        super().__init__(record, reset)

        self.num_pos = record.user_defined['pos']  # num_pos is the total number of available loading positions
        # num_pos should be 4 for the carousel balances
        self._positions = None
        self._weight_groups = None

        self.cal_pos = 1
        self.want_adjust = True

        self.lift_pos = None
        self.rot_pos = None

        self._move_time = False
        self._is_centred = False
        self._is_adjusted = False

        self.handler = None

    @property
    def mode(self):
        return 'aw_c'

    def identify_handler(self):
        """Reports handler model and software version.
        string returned of form: H1006, serial number #xxxx, software V x.xx. ready

        Returns
        -------
        string from balance

        """
        h_str = self._query("IDENTIFY")
        if self.record.model == "AX10005":
            assert h_str.strip().strip('\r') == "H10005, serial number #0003, software V 1.03.  ready"
        else:# TODO: confirm that the correct handler is connected for AX1006
            print(h_str)

        return h_str

    @property
    def positions(self):
        """Returns a list of positions for the weight groups in the order the groups appear in the scheme entry."""
        return self._positions

    @property
    def weight_groups(self):
        """Returns a list of weight groups in the order the groups appear in the scheme entry."""
        return self._weight_groups

    def initialise_balance(self, wtgrps):
        """Assigns weight groups to weighing positions using the AllocatorDialog,
        including specifying which of these positions require centring.
        Performs the check_loading routine, then the centring routine, then does a scale adjustment.

        Parameters
        ----------
        wtgrps : list
            list of weight groups as strings

        Returns
        -------
        self.positions : list
            Returns a list of positions for the weight groups in the order the groups appear in the scheme entry.
        """
        # allocate weight groups to positions, and specify which to centre
        self._positions, pos_to_centre, repeats = self.allocate_positions_and_centrings(wtgrps)
        if self.positions is None:
            log.error("Position assignment was not completed")
            self._want_abort = True
            return None

        # check sensible weights loaded
        self.check_loading()
        if not self._move_time:
            log.error("Loading check was not completed")
            return None

        # centre weights as needed (ok if no weights to centre)
        self.centring(pos_to_centre, repeats)
        if not self._is_centred:
            log.error("Centring was not completed")
            return None

        # Do a self calibration using the calibration position
        if self.want_adjust:
            if self.cal_pos not in self.positions:
                log.error("No mass in position selected for self calibration")
                return None
            self.scale_adjust(cal_pos=self.cal_pos)
            if not self._is_adjusted:
                log.error("Balance self-calibration was not successful")
                return None
        else:
            log.info("Balance self-calibration was not selected")

        return self.positions

    def allocate_positions_and_centrings(self, wtgrps):
        """Assigns weight groups to weighing positions using the AllocatorDialog,
        including specifying which of these positions require centring.

        Parameters
        ----------
        wtgrps : list

        Returns
        -------
        Tuple of self._positions, pos_to_centre, repeats or None, None, None if incomplete assignment
        """
        if len(wtgrps) > self.num_pos:
            log.error('Too many weight groups for balance')
            return None

        self._weight_groups = wtgrps

        # allocate weight groups to positions, and specify which to centre
        allocator.show(self.num_pos, wtgrps)
        self._positions, pos_to_centre, repeats, self.cal_pos, self.want_adjust \
            = allocator.wait_for_prompt_reply()

        if self.positions is None:
            log.error("Position assignment was not completed")
            self._want_abort = True
            return None, None, None

        return self._positions, pos_to_centre, int(repeats)

    def check_loading(self):
        """Tests each position involved in the automatic circular weighing procedure.
        Checks for sensible loading (raises error on overload or underload)
        and times rotation between positions to get self._move_time
        """
        if self.positions is None:
            log.warning("Weight groups must first be assigned to positions.")
            return False

        if not self.want_abort:
            log.info("Beginning balance loading check")
            self.move_to(self.positions[0])

        times = []
        for pos in np.roll(self.positions, -1):   # puts first position at end
            if self.want_abort:
                return self._move_time
            t0 = perf_counter()
            self.move_to(pos)
            # note that move_to has a buffer time of 5 s by default (unless wait=False)
            times.append(perf_counter() - t0)

            self.lift_to('weighing')
            self.get_mass_instant()
            self.lift_to('top')

        self._move_time = np.ceil(max(times))
        print("Times: "+str(times))
        print("Longest time: "+str(self._move_time))
        log.info("Balance loading check complete")

        return self._move_time

    def centring(self, pos_to_centre, repeats):
        """Performs a centring routine

        Parameters
        ----------
        pos_to_centre : list
            list of integers for the position numbers to centre
        repeats : int
            number of times to raise/lower each weight
        Returns
        -------
        bool to indicate successful completion
        """
        if not pos_to_centre:
            log.info("No weight groups selected for centring")
            self._is_centred = True
            return True

        if not repeats:
            log.warning("Repeats set to zero for centring")
            return False

        log.info("Commencing centring for {}".format(pos_to_centre))
        if not self.want_abort:
            for pos in pos_to_centre:
                self.move_to(pos)
                for i in range(repeats):
                    log.info("Centring #{} of {} for position {}".format(i + 1, repeats, pos))
                    self.lift_to('weighing')
                    # the lift_to includes appropriate waits
                    self.lift_to('top')

            log.info("Centring complete")
            self._is_centred = True

        return self._is_centred

    def scale_adjust(self, cal_pos=None):
        """Automatically adjust scale using internal 'external' weight.
        A mass must be loaded in the calibration position when this method is called, otherwise an error will be raised."""
        # When initiated from run_circ_weigh, this method is called from initialise_balance after check_loading
        # and centring.  This order of operations ensures a sensible mass is used for the scale_adjust.
        if self.want_abort:
            return None

        if cal_pos is None:
            cal_pos = self.cal_pos

        log.info("Balance self-calibration routine initiated")

        self.move_to(cal_pos)

        self.lift_to('weighing')

        print(self.get_mass_instant())  # double checks that the mass loaded is sensible!

        wait_for_elapse(3)
        self.zero_bal()
        wait_for_elapse(3)

        m = self._query("C1").split()
        log.debug(m)

        if m[1] == 'B':
            app = application()
            print('Balance self-calibration commencing')
            log.info('Balance self-calibration commencing')
            t0 = perf_counter()
            while True:
                app.processEvents()
                if self.want_abort:
                    log.warning('Balance self-calibration aborted')
                    return None
                try:
                    c = self.connection.read().split()
                    print(c)
                    if c[0] == 'ready':
                        continue
                    elif c[0] == 'ES':
                        continue
                    elif c[0] == "0.00000":
                        print(self.get_status())
                        if self.lift_pos == 'calibration':
                            # self.raise_handler()
                            self.lift_to("weighing")
                        self.connection.write("")
                        continue
                    elif c[0] == "10.00000":
                        self.lower_handler()
                        self.connection.write("")
                        continue
                    elif c[1] == 'A':
                        print('Balance self-calibration completed successfully')
                        self._is_adjusted = True
                        log.info('Balance self-calibration completed successfully')
                        self.lift_to("top")
                        return
                    elif c[1] == 'I':
                        self._raise_error_loaded('CAL C')
                    elif c[1] == "0.00000":
                        print(self.get_status())
                        # self.connection.write("")
                        if self.lift_pos == 'calibration':
                            # self.raise_handler()
                            self.lift_to("weighing")
                        self.connection.write("")
                        continue
                    elif c[1] == "10.00000":
                        self.lower_handler()
                        self.connection.write("")
                        continue
                    elif c[2] == "0.00000":
                        print(self.get_status())
                        # self.connection.write("")
                        if self.lift_pos == 'calibration':
                            # self.raise_handler()
                            self.lift_to("weighing")
                        self.connection.write("")
                        continue
                    elif c[2] == "10.00000":
                        self.lower_handler()
                        self.connection.write("")
                        continue
                    else:
                        wait_for_elapse(1)
                        continue
                except MSLTimeoutError:
                    if perf_counter() - t0 > self.intcaltimeout:
                        self.raise_handler()
                        self.raise_handler()
                        raise TimeoutError("Calibration took longer than expected")
                    else:
                        log.info('Waiting for internal calibration to complete')

        self._raise_error_loaded(m[0] + ' ' + m[1])

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
        # while True:
        status_str = self._query("STATUS")
        #     if status_str.strip("\r") == "ready":
        #         continue
        #     else:
        #         break

        if len(status_str.split()) == 5 and status_str.split()[-1] == "ready":
            self.rot_pos = status_str.split()[0]
            self.lift_pos = status_str.split()[2]
            # log.debug("Handler in position {}, {} position".format(self.rot_pos, self.lift_pos))
        else:
            print(status_str)
            self.lift_pos = None
            self.rot_pos = None

        return self.rot_pos, self.lift_pos

    def move_to(self, pos, wait=True):
        """Positions the weight at turntable position pos by the quickest route,
        in the top position above the weighing pan.
        The command performs lift operations if necessary.
        Waits for at least 5 seconds for stability and to let any eddy currents die out.

        Parameters
        ----------
        pos : int
        wait : bool (optional)
        """
        if not 0 < pos <= self.num_pos:
            self._raise_error_loaded('POS')

        if self.want_abort:
            return False

        log.info("Moving to position "+str(pos))
        self.connection.write("MOVE" + str(pos))  # Spaces are ignored by the handler

        reply = self.wait_for_reply()
        # the message returned is either 'ready' or an error code
        if reply == "ready":
            self.get_status()
            log.info("Handler in position {}, {} position".format(self.rot_pos, self.lift_pos))
            if wait:
                wait_for_elapse(5)
        else:
            self._raise_error_loaded(get_key(reply))

    def lower_handler(self):
        """Lowers the turntable one lift position.
        For the AX1006, this command puts the turntable in the weighing position.
        For the AX10005, the turntable moves downward:
            – From the top to the panbraking position,
            – from the braking to the weighing position,
            – from the weighing to the calibration position.
        """
        if self.want_abort:
            return False

        log.info("Sinking mass")
        self.connection.write("SINK")

        reply = self.wait_for_reply()

        if reply == "ERROR: In weighing position already. ready":  # AX1006 error
            log.warning(
                "The turntable is in the weighing position and cannot be lowered further."
            )
            return True

        if reply == "ERROR: In calibration position already. ready":  # AX10005 error
            log.warning(
                "The turntable is in the calibration position and cannot be lowered further."
            )
            return True

        elif reply == "ready":
            return True

        else:
            self._raise_error_loaded(get_key(reply))

    def raise_handler(self):
        """Raises the turntable one lift position.
        For the AX1006, this command puts the turntable in the top position.
        For the AX10005, the turntable moves upward:
            – From the calibration position to the weighing position,
            – from the weighing position to the top position.
        """
        if self.want_abort:
            return False

        log.info("Lifting mass")
        self.connection.write("LIFT")

        reply = self.wait_for_reply()

        if reply == "ERROR: In top position already. ready":
            log.warning(
                "The turntable is in the top position and cannot be raised further."
            )
            return True

        elif reply == "ready":
            return True

        else:
            self._raise_error_loaded(get_key(reply))

    def lift_to(self, lift_position, wait=True):
        """Lowers or raises handler to the lift position specified.
        If lowering to panbraking or weighing positions, waits for self.stable_wait time at each stage.

        Parameters
        ----------
        lift_position : string
            string for desired lift position. Allowed strings are: top, panbraking, weighing, calibration
        """
        if self.record.model == "AX10005":
            lower_options = {'top': 0, 'panbraking': 1, 'weighing': 2, 'calibration': 3}
        else:
            lower_options = {'top': 0, 'weighing': 1}
        raise_options = {'top': 2, 'panbraking': 1, 'weighing': 1, 'calibration': 0}
        # note: calibration and panbraking positions are not relevant for AX1006
        if lift_position not in lower_options:
            log.error("Lift position not recognised")
            return False
        rot_pos, current = self.get_status()
        lowers = lower_options[lift_position] - lower_options[current]
        if lowers < 0:
            raises = raise_options[lift_position] - raise_options[current]
            for i in range(raises):
                print("raises", raises)
                self.raise_handler()
        else:
            for i in range(lowers):
                self.lower_handler()
                self.get_status()
                if wait:
                    if self.lift_pos == 'panbraking':
                        wait_for_elapse(self.stable_wait)
                    elif self.lift_pos == 'weighing':
                        wait_for_elapse(self.stable_wait)
                    # at present these waits are the same time, but we can allow different times here.

        self.get_status()
        log.info("Handler in position {}, {} position".format(self.rot_pos, self.lift_pos))
        if not self.lift_pos == lift_position:
            self._raise_error_loaded("LT")

    def load_bal(self, mass, pos):
        """Load the balance with a specified mass in position pos, including appropriate waits to ensure consistent timing.

        Parameters
        ----------
        mass : str
            string of weight group being loaded
        pos : int
            integer of position of mass to be loaded on balance
        """
        if not self._move_time:
            log.error("Move time not determined. Please run check loading routine")
            return

        if not self.want_abort:
            log.info("Loading balance with {} in position {}".format(mass, pos))
            # start clock
            t0 = perf_counter()

            # do move
            self.move_to(pos, wait=False)

            # wait for some time to make all moves same
            wait_for_elapse(self._move_time + 5, start_time=t0)

            self.lift_to('weighing')  # this raises an error if it fails to get to the weighing position

            return True

    def unload_bal(self, mass, pos):
        """Unloads mass from pan"""
        if not self.want_abort:
            self.lift_to('top')

    def get_mass_instant(self):
        """Reads instantaneous mass from balance.
        Includes a check that the balance has been read correctly.
        Makes sure to unload the balance before raising any error.

        Returns
        -------
        float
            mass in unit of balance
        OR None
            if serial read error
        OR raises an error via customised _raise_error_loaded method
        """
        m = self._query("SI").split()
        if self.check_reading(m):
            if m[1] == 'S':
                return float(m[2])
            elif m[1] == 'D':
                log.info('Reading is nonstable (dynamic) weight value')
                return float(m[2])
            elif m[1] == '-':
                self._raise_error_loaded('UL')
            elif m[1] == '+':
                self._raise_error_loaded('OL')
            else:
                self._raise_error_loaded(m[0]+' '+m[1])
        return None

    def get_mass_stable(self, mass):
        """Reads instantaneous mass values from balance three times, and returns the average.
        Gives a warning if difference between readings is more than twice the balance resolution
        (but allows the reading to be returned).

        Parameters
        ----------
        mass : str
            the name of the weight group being weighed

        Returns
        -------
        float of the average of three instantaneous balance readings
        """
        while not self.want_abort:
            log.info('Reading mass values for '+mass)
            readings = []
            t0 = perf_counter()
            time = perf_counter() - t0
            while time < self.stable_wait:
                b = self.get_mass_instant()
                if type(b) == float:
                    readings.append(b)
                elif b is None:
                    continue
                else:
                    print(b)  # this case shouldn't happen, so it's useful to know why it did!
                    self._raise_error_loaded(b)

                if len(readings) >= 3:
                    if max(readings) - min(readings) > 2*self.resolution:
                        log.warning("Readings differ by more than twice the balance resolution")
                        log.info("Readings recorded: {}".format(readings))
                    return sum(readings)/3

                time = perf_counter() - t0

            self._raise_error_loaded('U')

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
                r = self.connection.read().strip().strip('\r')
                if r:
                    print(r)  # for debugging only
                    return r
            except MSLTimeoutError:
                if perf_counter() - t0 > self.intcaltimeout:
                    self.raise_handler()
                    self.raise_handler()
                    raise TimeoutError("Movement took longer than expected")
                else:
                    log.info('Waiting for movement to end')

    def _raise_error_loaded(self, errorkey):
        self.raise_handler()
        self.raise_handler()
        self._raise_error(errorkey)


def wait_for_elapse(elapse_time, start_time=None):
    """Wait for a specified time while allowing other events to be processed

    Parameters
    ----------
    elapse_time : int
        time to wait in seconds
    start_time : float
        perf_counter value at start time.
        If not specified, the timer begins when the function is called.
    """
    app = application()
    if start_time is None:
        start_time = perf_counter()
        wait_time = elapse_time
    time = perf_counter() - start_time
    wait_time = elapse_time - time
    log.info("Waiting for {} s...".format(round(wait_time, 1)))
    while time < elapse_time:
        app.processEvents()
        time = perf_counter() - start_time
    log.debug('Wait over, ready for next task')


def get_key(val):
    """Looks for the error in ERRORCODES, a dictionary of known error codes for Mettler balances"""
    for key, value in ERRORCODES.items():
        if val == value:
            return key

    return None

