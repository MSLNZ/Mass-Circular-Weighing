"""
Class for the AT106 Mettler Toledo balance with computer interface and linear weight changer
Note: all movement commands check first if self.want_abort is True, in which case no movement occurs.
"""
from time import perf_counter

from msl.equipment import MSLTimeoutError
from msl.qt import application

from . import AWBalLinear
from ..log import log


class AT106(AWBalLinear):
    def __init__(self, record, reset=False, ):
        """Initialise AT106 Mettler Toledo Balance,
        # with automatic weight loading in linear configuration,
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
        self.internal_weights = None  # options: 0, 1 or 2; each weight is 10 g
        self.cal_pos = 0

    @property
    def mode(self):
        return 'aw_106'

    def _query(self, command):
        """Some commands complete without returning a response"""
        try:
            self.connection.serial.flush()
            m = self.connection.query(command)
            if 'EL' in m:             # EL if error otherwise nothing is returned
                self._raise_error(m[0] + ' ' + m[1])
            else:
                return m
        except MSLTimeoutError:
            return

    def _write(self, command):
        self.connection.write(command)
        self.wait_for_elapse(2)

    def get_serial(self):
        """Gets serial number of balance. Note that for the AT106, this 'serial number' is a unique seven character
        identification string 'id' stored in the balance by the IDX id command and returned by IDX.

        Returns
        -------
        str
            serial number
        """
        return self._query("IDX")

    def config_bal(self):
        # Configures AT106; no response from balance expected
        self._write("AD 0")  # turns off the automatic door
        self._write("CA 0")  # turns off automatic calibration
        self._write("MZ 0")  # turns off auto zero
        self._write("MI 1")  # sets vibration-free environment
        self._write("ML 2")  # sets universal weighing setting
        # self._write("MS 6")  # sets stability detector; allowed values between 0 and 7
        if self.internal_weights is None:
            self.ask_internal_weights()
        try:
            mass = self.get_mass_instant()
            if not 9 < mass < 11:
                self.add_int_weights(self.internal_weights)
        except ValueError:
            self.add_int_weights(self.internal_weights)

        self.check_fine_range()

    def check_fine_range(self):
        rg = self._query("RG ?")
        if "F" not in rg:
            log.info("Setting fine range")
            self._write("RG F")  # sets fine range (max number of decimal places)
        else:
            log.debug("Fine range already set")

    def ask_internal_weights(self):
        # ask how many 10 g internal weights are needed
        self._pt.show('item', 'Please select internal weights', ['0', '10 g', '20 g'], font=self._fontsize,
                      title='Balance Preparation')
        reply = self._pt.wait_for_prompt_reply()
        if reply is not None:
            self.internal_weights = reply[0]
            log.info(f"Internal weights selected: {self.internal_weights}")
        else:
            return False

    def remove_int_weights(self):
        log.info("(removing any internal weights)")
        self._write("%CMR")  # removes any/all electronic weights
        self.wait_for_elapse(10)

    def add_int_weights(self, num):
        """Adjusts electronic weights. After removing any electronic weights, sequential %CMS commands are used to
        toggle through the electronic weight options (Order: 20 g, 10 g (1), 10 g (2), None) to get to the desired
        loading

        Parameters
        -------
        num : int
            either 0, 1 or 2, of how many 10 g electronic weights are needed
        """
        log.info(f"Adding {num} internal weight(s)")
        self.remove_int_weights()
        if int(num) == 0:
            log.info("Internal weight adjustment complete")
            return

        log.info(f"(adding 2 x 10 g internal weights)")
        self._write("%CMS")  # adds both electronic weights to make 20 g
        if int(num) == 2:
            self.wait_for_elapse(10)
            log.info("Internal weight adjustment complete")
            return

        self.wait_for_elapse(2)
        log.info(f"(removing one to get 10 g internal weight)")
        self._write("%CMS")  # then takes off one electronic weight to get back to 10 g
        self.wait_for_elapse(10)
        log.info("Internal weight adjustment complete")

    def zero_bal(self):
        """Zeroes balance: must ensure no mass on balance"""
        # Not implemented for AT106: instead tare the balance (without confirming correct load)
        self.tare_bal(ask=False)

    def tare_bal(self, ask=True):
        """Tares balance after checking with user that tare load is correct"""
        ok = not ask
        if ask:
            self._pt.show('ok_cancel', 'Check that the balance has correct tare load, then press enter to continue.')
            ok = self._pt.wait_for_prompt_reply()

        if ok:
            r = self._query("T")
            if r:
                self.parse_mass_reading(r)
            log.info('Balance tared')

    def prep_for_scale_adjust(self, cal_pos):
        """Ensures balance is correctly loaded before commencing scale adjustment.

        Parameters
        ----------
        cal_pos : int or None
        """
        if cal_pos is None:
            cal_pos = self.cal_pos

        if not self.hori_pos == str(cal_pos):
            self.move_to(cal_pos)
        if not self.lift_pos == "weighing":
            self.lift_to('weighing', hori_pos=cal_pos)

        self._query("%CMR")        # check no electronic weights are loaded for scale adjustment
        m = self.get_mass_stable("scale adjust prep.")
        log.info("Current mass reading: {}".format(m))
        if type(m) is float:
            if not m < 1:  # checks that the mass reading is sensible - should be around zero
                log.error("Incorrect mass is loaded.")
                self._want_abort = True
                return False

            self.wait_for_elapse(10)
            return True

        return False

    def scale_adjust(self, cal_pos=None):
        """Adjusts scale using internal weights"""
        # At present copied from the Mettler one but I'm guessing there will be more changes needed for the AW_L mode

        if self.want_abort:
            log.warning('Balance self-calibration aborted before commencing')
            return None

        log.info("Preparing for balance self-calibration")
        ok = self.prep_for_scale_adjust(cal_pos)
        if not ok:
            return None

        self.zero_bal()
        self.wait_for_elapse(3)

        m = self._query("CA").split()  # initiates
        if m[1] == 'BEGIN':
            app = application()
            log.info('Balance self-calibration commencing')
            t0 = perf_counter()
            while True:
                app.processEvents()
                try:
                    c = self.connection.read().split()
                    if c[1] == 'END':
                        cal_time = int(perf_counter() - t0)
                        log.info(f'Balance self-calibration completed successfully in {cal_time} seconds')
                        self._is_adjusted = True
                        self.check_fine_range()
                        if self.internal_weights is None:
                            self.ask_internal_weights()
                        self.add_int_weights(self.internal_weights)  # any internal weights were automatically removed
                        return True
                    elif c[1] == 'STOP':
                        log.warning('The calibration was aborted by the operator.')
                        return False
                    elif c[1] == 'ERROR':
                        log.error('The calibration cycle was aborted as result of an error condition.')
                        return False
                except MSLTimeoutError:
                    if perf_counter() - t0 > self.intcaltimeout:
                        raise TimeoutError(f"Internal calibration took longer than {self.intcaltimeout} seconds.")
                    else:
                        log.info('Waiting for internal calibration to complete')

        self._raise_error(m[0] + ' ' + m[1])

    def parse_mass_reading(self, m):
        """Handle any errors or return the mass reading as a float

        Parameters
        ----------
        m : list
            from string returned from balance

        Returns
        -------
        float
            mass in unit of balance
        None
            if serial read error
        error code
            if balance read correctly but error raised
        """
        if self.check_reading(m, index=2):
            if m[0] == 'S':
                return float(m[1])
            elif m[0] == 'SD':
                log.info('Reading is nonstable (dynamic) weight value')
                return float(m[1])
            elif m[0] in ['EL', 'SI', 'SI+', 'SI-']:
                return self._raise_error(m[0])  # expect EL, SI, SI+ or SI- as first
            else:
                return None
        else:
            return None

    def check_loading(self):
        """Tests each position involved in the automatic circular weighing procedure.
        Checks for sensible loading (raises error on overload or underload)
        and times rotation between positions to get self._move_time.
        Customisation for AT106: asks how many electronic weights should be loaded
        """
        if self.internal_weights is None:
            self.ask_internal_weights()

        if self.positions is None:
            log.warning("Weight groups must first be assigned to positions.")
            return False

        if not self.want_abort:
            # load first mass, adjust electronic weight load, then continue to regular check_loading routine
            self.move_to(self.positions[0], wait=False)
            self.lift_to('weighing', hori_pos=self.positions[0], wait=False)
            self.config_bal()
            super().check_loading()
