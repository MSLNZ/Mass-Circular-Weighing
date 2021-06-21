"""
Class for the AT106 Mettler Toledo balance with computer interface and linear weight changer
Note: all movement commands check first if self.want_abort is True, in which case no movement occurs.
"""
from time import sleep, perf_counter

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
        self.config_bal()
        self.internal_weights = 1  # options: 1 or 2; each weight is 10 g

    @property
    def mode(self):
        return 'aw_106'

    def _query(self, command):
        """Some commands complete without returning a response"""
        try:
            self.connection.serial.flush()
            m = self.connection.query(command)
            print("Query reply:", m)
            if 'EL' in m:             # EL if error otherwise nothing is returned
                self._raise_error(m[0] + ' ' + m[1])
            else:
                return m
        except MSLTimeoutError:
            return

    def _write(self, command):
        self.connection.write(command)
        sleep(1)

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
        self._write("RG F")  # sets fine range (max number of decimal places)
        self._write("MZ 0")  # turns off auto zero

    def remove_int_weights(self):
        self._write("%CMR")  # removes any/all electronic weights

    def add_int_weights(self, num):

        self.remove_int_weights()

        log.debug(f"Adding {num} internal weights")

        self._write("%CMS")  # adds both electronic weights to make 20 g
        if num == 2:
            return True

        self._write("%CMS")  # then takes off one electronic weight to get back to 10 g
        return True

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
        """Ensures balance is unloaded before commencing scale adjustment.

        Parameters
        ----------
        cal_pos : int or None
        """
        if cal_pos is None:
            cal_pos = self.cal_pos

        # self._query("%CMR")        # check no electronic weights are loaded for scale adjustment

        if not self.hori_pos == str(cal_pos):
            self.move_to(cal_pos)
        if not self.lift_pos == "weighing":
            self.lift_to('weighing', hori_pos=cal_pos)

        m = self.get_mass_instant()
        log.info("Current mass reading: {}".format(m))
        if type(m) is float:
            if not m > 8:  # checks that the mass reading is sensible - should be just over 9 g
                log.error("Incorrect mass is loaded.")
                self._want_abort = True

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
            print('Balance self-calibration commencing')
            log.info('Balance self-calibration commencing')
            t0 = perf_counter()
            while True:
                app.processEvents()
                try:
                    c = self.connection.read().split()
                    if c[1] == 'END':
                        cal_time = int(perf_counter() - t0)
                        print(f'Balance self-calibration completed successfully in {cal_time} seconds')
                        log.info(f'Balance self-calibration completed successfully in {cal_time} seconds')
                        self._is_adjusted = True
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
        """Handle any errors or return the mass reading as a float"""
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
        and times rotation between positions to get self._move_time
        """
        if self.positions is None:
            log.warning("Weight groups must first be assigned to positions.")
            return False

        if not self.want_abort:
            self.move_to(self.positions[0], wait=False)
            self.lift_to('weighing', hori_pos=self.positions[0])

            # determine how many internal weights are needed
            self.remove_int_weights()
            self.internal_weights = 0

            ok = False
            while not ok:
                m = self._query("SI")
                log.info(f"received {m}")
                if "SI-" in m:  # need to make sure that this underload isn't because no masses are loaded!
                    self.add_int_weights(2)
                    self.internal_weights = 2
                elif self.parse_mass_reading(m.split()) > 8:
                    print('accepted internal weight loading;')
                    ok = True
                elif self.parse_mass_reading(m.split()) < 8:
                    self.add_int_weights(1)
                    self.internal_weights = 1
                else:
                    return self._raise_error(m.split()[0])

            print(f"want {self.internal_weights} internal weights")

            super().check_loading()
