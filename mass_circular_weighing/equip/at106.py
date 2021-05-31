"""
Class for the AT106 Mettler Toledo balance with computer interface and linear weight changer
Note: all movement commands check first if self.want_abort is True, in which case no movement occurs.
"""
from time import sleep, perf_counter

from msl.equipment import MSLTimeoutError
from msl.qt import application

from . import AWBalLinear, MettlerToledo
from ..log import log


class AT106(MettlerToledo):  # inherit from AWBalLinear when weight changer is ready
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

    def get_serial(self):
        """Gets serial number of balance. Note that for the AT106, this 'serial number' is a unique seven character
        identification string 'id' stored in the balance by the IDX id command and returned by IDX.

        Returns
        -------
        str
            serial number
        """
        return self._query("IDX")

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
                self._raise_error(r)
            log.info('Balance tared')

    def scale_adjust(self):
        """Adjusts scale using internal weights"""
        # At present copied from the Mettler one but I'm guessing there will be more changes needed for the AW_L mode
        m = self._query("CA").split()
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
                    elif c[1] == 'I':
                        log.error('The calibration was aborted as, e.g. stability not attained or the procedure was aborted with the C key.')
                        return False
                        # self._raise_error('CAL C')
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
            else:
                return self._raise_error(m)  # expect EL, SI, SI+ or SI-
        else:
            self._raise_error(m)

