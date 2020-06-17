'''Class for Mettler Toledo Balance with computer interface and linear weight changer'''
# note: all movement commands check first if self.want_abort is True, in which case no movement occurs.

from . import AWBalCarousel
from ..log import log

from ..gui.threads.allocator_thread import AllocatorThread
allocator = AllocatorThread()


#TODO: add clean up to close connection to Arduino and leave in Sleep mode
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
        address = record.user_defined['address']
        self.arduino = None
        '''Return when using arduino:
        serial.Serial(port=address, baudrate=115200)
        self.init_arduino()
        '''
        self.identify_handler()

    @property
    def mode(self):
        return 'aw_l'

    def query_arduino(self, command):
        """Open serial port, query Arduino, then close serial port.
        Does any required encoding or decoding...

        Parameters
        ----------
        command : str

        Returns
        -------
        str reply to queried command
        """
        self.arduino = self.handler.connect()
        self.arduino.serial.flush()
        reply = self.arduino.query(command.encode()).decode()
        # TODO: a wait_for_reply equivalent for slow movement (if longer than MSL Timeout
        self.arduino.disconnect()

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
        status, loc = reply.split()
        print(status, loc)
        if "idle" in status.lower():
            self.hori_pos = loc[:-1]
            self.lift_pos = loc[-1]
            return True
        else:
            self.hori_pos = None
            self.lift_pos = None
            print(reply)
            raise ValueError("Error at Arduino: {}".format(reply))

    def identify_handler(self):
        """Initialises and identifies the weight changer Arduino

        Returns
        -------
        Bool to indicate ready status of weight changer
        """
        status = self.query_arduino("START")
        if "ready" in status[:5].lower():
            return True
        else:
            return self.parse_reply(status)
        # if status BAD, set self._want_abort = True (see parent Balance class)
        # TODO: check serial number is correct

    def prep_for_scale_adjust(self, cal_pos):
        """Ensures balance is unloaded before commencing scale adjustment.

        Parameters
        ----------
        cal_pos : int or None
        """
        self.lift_to('top')

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
        if not 0 < pos <= self.num_pos:
            self._raise_error_loaded('POS')

        if self.want_abort:
            return False

        log.info("Moving to position " + str(pos))

        move_str = 'MOVE TO '+str(pos)+'U\n'   # Leaves handler in the unloaded position after move
        print(move_str)
        reply = self.query_arduino(move_str)
        if self.parse_reply(reply):
            log.info("Handler in position {}, {} position".format(self.hori_pos, self.lift_pos))
            assert self.hori_pos == str(pos)
            if wait:
                self.wait_for_elapse(5)

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

        self.get_status()
        if pos:
            if not self.hori_pos == str(pos):
                log.error("Asked to load mass in position {} but currently at position {}".format(pos, self.hori_pos))
                return False

        log.info("Sinking mass")
        lower_str = 'MOVE TO '+str(self.hori_pos)+'L\n'
        reply = self.query_arduino(lower_str)
        if self.parse_reply(reply):
            log.info("Handler in position {}, {} position".format(self.hori_pos, self.lift_pos))
            if not self.lift_pos == "L":
                raise ValueError("Loading failure")
            return True

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

        self.get_status()
        if pos:
            if not self.hori_pos == str(pos):
                log.error("Asked to unload mass from position {} but currently at position {}".format(pos, self.hori_pos))
                return False

        log.info("Lifting mass")
        move_str = 'MOVE TO ' + str(pos) + 'U\n'
        reply = self.query_arduino(move_str)
        if self.parse_reply(reply):
            log.info("Handler in position {}, {} position".format(self.hori_pos, self.lift_pos))
            if not self.lift_pos == "U":
                raise ValueError("Unloading failure")
            return True

    def lift_to(self, lift_position, hori_pos=None, wait=True):
        """Lowers or raises handler to the lift position specified.

        Parameters
        ----------
        lift_position : string
            string for desired lift position. Allowed strings are: top, weighing.
        hori_pos : int, optional
            confirmation of the desired horizontal position
        wait : Bool, optional
            If True, waits for stable wait time after lowering to weighing position
        """
        if lift_position == 'top':
            self.raise_handler(pos=hori_pos)

        elif lift_position == 'weighing':
            self.lower_handler(pos=hori_pos)
            if wait:
                self.wait_for_elapse(self.stable_wait)

        else:
            log.error("Lift position {} not recognised for this handler".format(lift_position))
            return False



