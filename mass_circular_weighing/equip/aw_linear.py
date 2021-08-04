"""
Class for a Mettler Toledo balance with computer interface and linear weight changer
Note: all movement commands check first if self.want_abort is True, in which case no movement occurs.
"""
from time import sleep

from . import AWBalCarousel
from ..log import log


class AWBalLinear(AWBalCarousel):
    def __init__(self, record, reset=False, ):
        """Initialise Mettler Toledo Balance,
        with automatic weight loading in linear configuration,
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

        # This balance class inherits many class variables from AWBalCarousel,
        # including self.handler, which can be used to store the Arduino info
        self.arduino = None

    @property
    def mode(self):
        return 'aw_l'

    def query_arduino(self, command):
        """Open serial port, query Arduino, then close serial port.

        Parameters
        ----------
        command : str

        Returns
        -------
        str reply to queried command
        """
        self.arduino.serial.flush()
        self.arduino.write(command)
        reply = self.wait_for_reply(cxn=self.arduino)
        return reply

    def parse_reply(self, reply):
        """Get status out of a typical reply from the Arduino, or raise an error

        Parameters
        ----------
        reply : str
            expects string of format "IDLE {horizontal pos}{lift pos}" or an error string

        Returns
        -------
        Bool of whether the status has been updated (and therefore the string was parsed) or not
        """
        status = reply.split()
        log.debug(f"parsing {status}")
        if "idle" in status[0].lower():
            self.hori_pos = status[1][:-1]
            self.lift_pos = status[1][-1]
            return True
        else:
            self.hori_pos = None
            self.lift_pos = None
            for i in range(8):
                log.warning(self.arduino.read())

            raise ValueError("Error at Arduino: {}".format(reply))

    def check_serial(self):
        import serial.tools.list_ports

        for pinfo in serial.tools.list_ports.comports():
            if pinfo.serial_number == self.handler.serial:
                print(pinfo.device)
                return serial.Serial(pinfo.device)
        raise IOError("Could not find an Arduino - is it plugged in?")

    def identify_handler(self):
        """Initialises and identifies the weight changer Arduino

        Returns
        -------
        Bool to indicate ready status of weight changer
        """
        self.arduino = self.handler.connect()
        log.info("Connecting to Arduino.........")
        self.wait_for_elapse(20)  # need to allow time for the Arduino to initialise
        log.debug(self.query_arduino("START"))
        # sleep(1)
        # print(self.arduino.read())
        # sleep(1)
        # print("handler", self.handler.serial)
        # print(self.arduino.serial)

        status = self.query_arduino("STATUS")

        if "ready" in status[:5].lower():
            return True
        else:
            return self.parse_reply(status)
        # if status BAD, set self._want_abort = True (see parent Balance class)
        # TODO: check serial number is correct

    def place_weight(self, mass, pos):
        """Allow a mass to be placed onto the carrier in position pos using the loading height.

        Parameters
        ----------
        mass : str
            string of weight group allocated to the position pos
        pos : int
            integer of position where mass is to be placed
        """
        self.move_to(pos, wait=False)
        self.loading_position(pos)
        message = 'Place mass <b>' + mass + '</b><br><i>(position ' + str(pos) + ')</i>'
        self._pt.show('ok_cancel', message, font=self._fontsize, title='Balance Preparation')
        reply = self._pt.wait_for_prompt_reply()

        return reply

    def prep_for_scale_adjust(self, cal_pos):
        """Ensures balance is unloaded before commencing scale adjustment.

        Parameters
        ----------
        cal_pos : int or None
        """
        self.lift_to('top', hori_pos=cal_pos)
        self.wait_for_elapse(10)

        return True

    def get_status(self):
        """Update current horizontal and lift position of the carrier.
        Expects string reply of format "IDLE {horizontal pos}{lift pos}"
        where horizontal pos is an integer, and lift pos is U or L

        Returns
        -------
        tuple of hori_pos, lift_pos
        """
        status_str = self.query_arduino("STATUS")
        self.parse_reply(status_str)

        return self.hori_pos, self.lift_pos

    def move_to(self, pos, wait=True):
        """Positions the weight at horizontal position pos,
        in the top (unloaded) position above the weighing pan.
        The command performs lift operations if necessary.
        Waits for at least 5 seconds for stability and to let any eddy currents die out.

        Parameters
        ----------
        pos : int
        wait : bool (optional)
        """
        if not 0 <= pos <= self.num_pos:
            self._raise_error_loaded('POS')

        if self.want_abort:
            return False

        log.info("Moving to position " + str(pos))

        move_str = 'MOVE TO '+str(pos)+'U'   # Leaves handler in the unloaded position after move
        self.arduino.write(move_str)
        sleep(1)
        reply = self.wait_for_reply(cxn=self.arduino)
        if self.parse_reply(reply):
            log.info("Handler in position {}, {} position".format(self.hori_pos, self.lift_pos))
            assert self.hori_pos == str(pos)
            if wait:
                self.wait_for_elapse(5)

    def check_pos(self, pos):
        self.get_status()
        if pos is not None:
            if self.hori_pos == str(pos):
                return True
            else:
                log.error("Asked to load mass in position {} but currently at position {}".format(pos, self.hori_pos))
                return False

    def lower_handler(self, pos=None):
        """Lowers the mass onto the pan at the current horizontal position

        Parameters
        ----------
        pos : int, optional
            If not specified, uses the current position
            If specified, checks that the handler is currently at the desired position

        Returns
        -------
        Bool of completion, or raises error
        """
        if self.want_abort:
            return False

        if not self.check_pos(pos):
            return False

        log.info("Sinking mass to weighing position")
        move_str = 'MOVE TO '+str(self.hori_pos)+'W'
        self.arduino.write(move_str)
        sleep(1)
        return self.handle_lift_reply('W')

    def raise_handler(self, pos=None):
        """Raises the mass off the pan at the current position

        Parameters
        ----------
        pos : int, optional
            If not specified, uses the current position

        Returns
        -------
        Bool of completion, or raises error
        """
        if self.want_abort:
            return False

        if not self.check_pos(pos):
            return False

        log.info("Lifting mass")
        move_str = 'MOVE TO ' + str(pos) + 'U'
        self.arduino.write(move_str)
        sleep(1)
        return self.handle_lift_reply('U')

    def loading_position(self, pos=None):
        """Raises or lowers the carriage so that masses can be placed in the centre at the current position.
        Loading position is equivalent to panbraking position.

        Parameters
        ----------
        pos : int, optional
            If not specified, uses the current position

        Returns
        -------
        Bool of completion, or raises error
        """
        if self.want_abort:
            return False

        if not self.check_pos(pos):
            return False

        log.info("Going to loading lift position")
        move_str = 'MOVE TO ' + str(pos) + 'L'
        self.arduino.write(move_str)
        sleep(1)
        return self.handle_lift_reply('L')

    def lift_to(self, lift_position, hori_pos=None, wait=True):
        """Lowers or raises handler to the lift position specified.

        Parameters
        ----------
        lift_position : string
            string for desired lift position. Allowed strings are: top, weighing, loading.
        hori_pos : int, optional
            confirmation of the desired horizontal position
        wait : Bool, optional
            If True, waits for stable wait time after lowering to weighing position
        """
        if hori_pos is None:
            self.get_status()
            hori_pos = self.hori_pos

        if lift_position == 'top':
            return self.raise_handler(pos=hori_pos)

        elif lift_position == 'weighing':
            ok = self.lower_handler(pos=hori_pos)
            if ok:
                if wait:
                    self.wait_for_elapse(self.stable_wait)
                return True

        elif lift_position == 'loading':
            return self.loading_position(pos=hori_pos)

        else:
            log.error("Lift position {} not recognised for this handler".format(lift_position))

        return False

    def handle_lift_reply(self, lift_pos):
        reply = self.wait_for_reply(cxn=self.arduino)
        if self.parse_reply(reply):
            log.info("Handler in position {}, {} position".format(self.hori_pos, self.lift_pos))
            if not self.lift_pos == lift_pos:
                for i in range(8):
                    log.warning(self.arduino.read())
                raise ValueError(f"Failed to get to {lift_pos} lift position")
            return True

    def close_connection(self):
        self.arduino.query("END")
        self.arduino.disconnect()
        self.connection.disconnect()
