"""
Class for a Mettler Toledo balance with computer interface and carousel weight changer
Note: all movement commands check first if self.want_abort is True, in which case no movement occurs.
"""
from time import perf_counter
import numpy as np

from msl.equipment import MSLTimeoutError
from msl.qt import application

from ..log import log
from .mettler import MettlerToledo, ERRORCODES

from ..gui.threads import AllocatorThread


class AWBalCarousel(MettlerToledo):

    allocator = AllocatorThread()

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
        self._weight_groups = None

        self.pos_to_centre = []
        self.repeats = 0

        self.cal_pos = 1

        self.lift_pos = None    # vertical position   (string)
        self.hori_pos = None    # horizontal position (string of integer)

        self._move_time = False
        self.cycle_duration = 0
        self._is_centred = False

        self.handler = None

    @property
    def mode(self):
        return 'aw_c'

    @property
    def weight_groups(self):
        """Returns a list of weight groups in the order the groups appear in the scheme entry."""
        return self._weight_groups

    @property
    def move_time(self):
        """Longest time taken to move between positions in circular weighing. Integer value, in seconds, or None."""
        return self._move_time

    def identify_handler(self):
        """Reports handler model and software version.
        string returned of form: H1006, serial number #xxxx, software V x.xx. ready

        Returns
        -------
        Bool to indicate ready status of handler
        """
        h_str = self._query("IDENTIFY").strip("\r")
        h_list = h_str.split(", ")

        if self.record.model == "AX10005":
            assert h_list[0] == "H10005"
            assert h_list[1] == "serial number #0003"
            assert h_list[-1][-5:] == "ready"
            self.handler = "H10005"
            return True

        elif self.record.model == "AX1006":
            assert h_list[0] == "H1006"
            assert h_list[1] == "serial number #0040"
            assert h_list[-1][-5:] == "ready"
            self.handler = "H1006"
            return True

        log.error("Unknown balance connected; reply received: {}".format(h_str))
        return False

    def initialise_balance(self, wtgrps):
        """Completes any remaining tasks of the following initialisation steps:
        Assigns weight groups to weighing positions using the AllocatorDialog,
        including specifying which of these positions require centring.
        Performs the check_loading routine, then the centring routine and scale adjustment if selected.

        Parameters
        ----------
        wtgrps : list
            list of weight groups as strings (e.g. from string split of scheme entry)

        Returns
        -------
        self.positions : list
            Returns a list of positions for the weight groups in the order the groups appear in the scheme entry.
        """
        # allocate weight groups to positions, and specify which to centre
        if self.positions is None:
            self._positions = self.allocate_positions_and_centrings(wtgrps)
        if self.positions is None:
            log.error("Position assignment was not completed")
            self._want_abort = True
            return None

        if self.want_adjust and not self.is_adjusted:
            # Carousel needs a mass loaded in the calibration position
            if self.mode == "aw_c":
                if self.cal_pos not in self.positions:
                    log.error("No mass in position selected for self calibration")
                    self._want_abort = True
                    return None

        if self.handler is None:
            ok = self.identify_handler()
            if not ok:
                return None

        # check sensible weights loaded
        if not self.move_time:
            self.check_loading()
        if not self.move_time:
            log.error("Loading check was not completed")
            return None

        # centre weights as needed (ok if no weights to centre)
        if self.pos_to_centre and not self._is_centred:
            self.centring(self.pos_to_centre, self.repeats)
            if not self._is_centred:
                log.error("Centring was not completed")
                return None

        # Do a self calibration if needed
        self.adjust_scale_if_needed()

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
        self.allocator.show(self.num_pos, wtgrps)
        self._positions, self.pos_to_centre, repeats, self.cal_pos \
            = self.allocator.wait_for_prompt_reply()
        self.repeats = int(repeats)

        if self.positions is None:
            log.error("Position assignment was not completed")
            self._want_abort = True
            return None, None, None

        message = f'Assigned weight groups {wtgrps} to positions {self.positions} respectively'
        log.info(msg=message)
        log.info(f"Position for self calibration is position {self.cal_pos}")

        return self._positions

    def place_weight(self, mass, pos):
        """Allow a mass to be placed onto the carrier in position pos.

        Parameters
        ----------
        mass : str
            string of weight group allocated to the position pos
        pos : int
            integer of position where mass is to be placed
        """
        self.move_to(pos, wait=False)
        # these balances are loaded in the top position
        message = 'Place mass <b>' + mass + '</b><br><i>(position ' + str(pos) + ')</i>'
        self._pt.show('ok_cancel', message, font=self._fontsize, title='Balance Preparation')
        reply = self._pt.wait_for_prompt_reply()

        return reply

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
        lifting = []
        for pos in np.roll(self.positions, -1):   # puts first position at end
            if self.want_abort:
                return self.move_time
            t0 = perf_counter()
            self.move_to(pos)
            # note that move_to has a buffer time of 5 s by default (unless wait=False)
            times.append(perf_counter() - t0)

            self.lift_to('weighing', hori_pos=pos)
            m = self.get_mass_instant()
            log.info("Mass value: {} {}".format(m, self.unit))
            self.lift_to('top', hori_pos=pos)
            lifting.append(perf_counter() - t0)

        self.cycle_duration = np.ceil(len(self.positions)*max(lifting))
        # here cycle_duration includes waits at top and bottom as well as getting the mass value

        self._move_time = np.ceil(max(times))
        print("Times: "+str(times))
        print("Longest time: "+str(self.move_time))
        log.info("Balance loading check complete")

        return self.move_time

    def centring(self, pos_to_centre=None, repeats=None):
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
        if pos_to_centre is None:
            pos_to_centre = self.pos_to_centre
        if repeats is None:
            repeats = self.repeats

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
                    self.lift_to('weighing', hori_pos=pos)
                    # the lift_to includes appropriate waits
                    self.lift_to('top', hori_pos=pos)

            log.info("Centring complete")
            self._is_centred = True

        return self._is_centred

    def prep_for_scale_adjust(self, cal_pos):
        """Loads appropriate mass for scale adjustment.
        A mass must be loaded in the calibration position when this method is called, otherwise an error will be raised.

        Parameters
        ----------
        cal_pos : int or None
        """
        if self.positions is None:
            log.warning("Weight groups must first be assigned to positions.")
            return False

        if cal_pos is None:
            cal_pos = self.cal_pos
        if not self.hori_pos == str(cal_pos):
            self.move_to(cal_pos)
        if not self.lift_pos == "weighing":
            self.lift_to('weighing', hori_pos=cal_pos)

        log.info("Current mass reading: {}".format(self.get_mass_instant()))
        # double checks that the mass loaded is sensible!
        self.wait_for_elapse(60)

        return True

    def scale_adjust(self, cal_pos=None):
        """Automatically adjust scale using internal 'external' weight.
        A mass must be loaded in the calibration position when this method is called, otherwise an error will be raised.

        Parameters
        ----------
        cal_pos : int, optional
        """
        # When initiated from run_circ_weigh, this method is called from initialise_balance after check_loading
        # and centring via the mdebalance adjust_scale_if_needed method.
        if self.want_abort:
            log.warning('Balance self-calibration aborted before commencing')
            return None

        log.info("Preparing for balance self-calibration")
        ok = self.prep_for_scale_adjust(cal_pos)
        if not ok:
            return None

        self.zero_bal()
        self.wait_for_elapse(3)

        m = self._query("C1").split()
        log.debug(m)

        if m[1] == 'B':
            app = application()
            log.info('Balance self-calibration commencing')
            t0 = perf_counter()
            while True:
                app.processEvents()
                if self.want_abort:
                    log.warning('Balance self-calibration aborted')
                    return None
                try:
                    c = self.connection.read().split()
                    log.debug(c)
                    if c[0] == 'ready':
                        continue
                    elif c[0] == 'ES':
                        continue
                    elif c[0] == "0.00000":
                        log.debug(self.get_status())
                        if self.lift_pos == 'calibration':
                            self.lift_to("weighing", hori_pos=cal_pos)
                        self.connection.write("")
                        continue
                    elif c[0] == "10.00000":
                        self.lower_handler()
                        self.connection.write("")
                        continue
                    elif c[1] == 'A':
                        cal_time = int(perf_counter() - t0) + 1
                        print(f'Balance self-calibration completed successfully in {cal_time} seconds')
                        log.info(f'Balance self-calibration completed successfully in {cal_time} seconds')
                        self._is_adjusted = True
                        self.lift_to("top", hori_pos=cal_pos)
                        return True
                    elif c[1] == 'I':
                        log.error('The calibration was aborted as, e.g. stability not attained or the procedure was aborted with the C key.')
                        return False
                        # self._raise_error_loaded('CAL C')
                    elif c[1] == "0.00000":
                        log.debug(self.get_status())
                        if self.lift_pos == 'calibration':
                            self.lift_to("weighing", hori_pos=cal_pos)
                        self.connection.write("")
                        continue
                    elif c[1] == "10.00000":
                        self.lower_handler()
                        self.connection.write("")
                        continue
                    elif c[2] == "0.00000":
                        log.debug(self.get_status())
                        if self.lift_pos == 'calibration':
                            self.lift_to("weighing", hori_pos=cal_pos)
                        self.connection.write("")
                        continue
                    elif c[2] == "10.00000":
                        self.lower_handler()
                        self.connection.write("")
                        continue
                    else:
                        self.wait_for_elapse(1)
                        continue
                except MSLTimeoutError:
                    if perf_counter() - t0 > self.intcaltimeout:
                        self.raise_handler()
                        self.raise_handler()
                        raise TimeoutError(f"Internal calibration took longer than {self.intcaltimeout} seconds.")
                    else:
                        log.info('Waiting for internal calibration to complete')

        # in the unlikely event something weird happens and the balance returns something unexpected:
        self._raise_error_loaded(m[0] + ' ' + m[1])

    def get_status(self):
        """Update current horizontal and lift position of the turntable.
        Possible string replies for AX10005:
        <a> in top position. ready
        <a> in panbraking position. ready
        <a> in weighing position. ready
        <a> in calibration position. ready
        <a> is an integer that represents the turntable position above the weighing pan.
        The AX1006 has only 'top' and 'weighing' positions.

        Returns
        -------
        tuple of hori_pos, lift_pos
        """
        status_str = self._query("STATUS")

        if len(status_str.split()) == 5 and status_str.split()[-1] == "ready":
            self.hori_pos = status_str.split()[0]
            self.lift_pos = status_str.split()[2]
            # log.debug("Handler in position {}, {} position".format(self.hori_pos, self.lift_pos))
        else:
            print(status_str)  # because something has gone wrong...
            self.lift_pos = None
            self.hori_pos = None

        return self.hori_pos, self.lift_pos

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
        if self.num_pos is None:
            log.error("Number of positions not set for balance!")
            return False
        if not 0 < pos <= self.num_pos:
            self._raise_error_loaded('POS')

        if self.want_abort:
            return False

        log.info("Moving to position "+str(pos))
        self.connection.write("MOVE" + str(pos))  # Spaces are ignored by the handler

        reply = self.wait_for_reply(cxn=self.connection)
        # the message returned is either 'ready' or an error code
        if reply == "ready":
            self.get_status()
            log.info("Handler in position {}, {} position".format(self.hori_pos, self.lift_pos))
            assert self.hori_pos == str(pos)
            if wait:
                self.wait_for_elapse(5)
        else:
            self._raise_error_loaded(self.get_key(reply))

    def lower_handler(self, pos=None):
        """Lowers the turntable one lift position.
        For the AX1006, this command puts the turntable in the weighing position.
        For the AX10005, the turntable moves downward:
            – From the top to the panbraking position,
            – from the braking to the weighing position,
            – from the weighing to the calibration position.

        Parameters
        ----------
        pos : int (optional, not used here)

        Returns
        -------
        Bool of completion, or raises error
        """
        if self.want_abort:
            return False

        log.info("Sinking mass")
        self.connection.write("SINK")

        reply = self.wait_for_reply(cxn=self.connection)

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
            self._raise_error_loaded(self.get_key(reply))

    def raise_handler(self, pos=None):
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

        reply = self.wait_for_reply(cxn=self.connection)

        if reply == "ERROR: In top position already. ready":
            log.warning(
                "The turntable is in the top position and cannot be raised further."
            )
            return True

        elif reply == "ready":
            return True

        else:
            self._raise_error_loaded(self.get_key(reply))

    def lift_to(self, lift_position, hori_pos=None, wait=True):
        """Lowers or raises handler to the lift position specified.
        If lowering to panbraking or weighing positions, waits for self.stable_wait time at each stage.

        Parameters
        ----------
        lift_position : string
            string for desired lift position. Allowed strings are: top, panbraking, weighing, calibration
        hori_pos : int, optional
            confirmation of the desired horizontal position
        wait : Bool, optional
            If True, waits for stable wait time after lowering to panbraking and/or weighing positions
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

        self.get_status()
        if hori_pos:
            if not str(hori_pos) == self.hori_pos:
                log.error("Asked to raise/lower mass in position {} but currently at position {}".format(hori_pos, self.hori_pos))
                return False

        lowers = lower_options[lift_position] - lower_options[self.lift_pos]
        if lowers < 0:
            raises = raise_options[lift_position] - raise_options[self.lift_pos]
            for i in range(raises):
                self.raise_handler()
        else:
            for i in range(lowers):
                self.lower_handler()
                self.get_status()
                if wait:
                    if self.lift_pos == 'panbraking':
                        self.wait_for_elapse(self.stable_wait)
                    elif self.lift_pos == 'weighing':
                        self.wait_for_elapse(self.stable_wait)
                    # at present these waits are the same time, but we can allow different times here.

        self.get_status()
        log.info("Handler in position {}, {} position".format(self.hori_pos, self.lift_pos))
        if not self.lift_pos == lift_position:
            self._raise_error_loaded("LT")

        return True

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
            self.wait_for_elapse(self._move_time, start_time=t0)

            return self.lift_to('weighing', hori_pos=pos)  # this raises an error if it fails to get to the weighing position

    def unload_bal(self, mass, pos):
        """Unloads mass from pan"""
        if not self.want_abort:
            log.info("Unloading {} from balance position {}".format(mass, pos))
            self.lift_to('top', hori_pos=pos)

    def parse_mass_reading(self, m):
        """Checks that the balance has been read correctly.
        Makes sure to unload the balance before raising any error.

        Returns
        -------
        float
            mass in unit of balance
        OR None
            if serial read error
        OR raises an error via customised _raise_error_loaded method
        """
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
        if not self.want_abort:
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
                    if max(readings) - min(readings) > 2.25*self.resolution:
                        log.warning("Readings differ by more than twice the balance resolution")
                        log.info("Readings recorded: {}".format(readings))
                    return sum(readings)/3

                time = perf_counter() - t0

            self._raise_error_loaded('U')

    def wait_for_reply(self, cxn=None):
        """Utility function for movement commands MOVE, SINK and LIFT.
        Waits for string returned by these commands.

        Returns
        -------
        The string from the handler
        """
        if cxn is None:
            cxn = self.connection

        app = application()
        t0 = perf_counter()

        while True:  # wait for handler to finish task
            app.processEvents()
            try:
                r = cxn.read().strip().strip('\r')
                if r:
                    log.debug(r)  # for debugging only
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

    @staticmethod
    def get_key(val):
        """Looks for the error in ERRORCODES, a dictionary of known error codes for Mettler balances"""
        for key, value in ERRORCODES.items():
            if val == value:
                return key

        return None

