"""
Class for a Mettler Toledo balance with a computer interface
"""
from time import perf_counter

from msl.equipment import MSLTimeoutError, MSLConnectionError
from msl.qt import application

from ..log import log
from ..constants import SUFFIX
from .mdebalance import Balance


class MettlerToledo(Balance):
    def __init__(self, record, reset=False):
        """Initialise Mettler Toledo Balance via computer interface

        Parameters
        ----------
        record : equipment record object
            get via Application(config).equipment[alias]
            Requires an MSL.equipment config.xml file
        reset : bool
            True if reset balance desired
        """
        super().__init__(record)

        self.connection = None
        self.connect_bal(reset=reset)

        self.intcaltimeout = self.record.connection.properties.get('intcaltimeout', 30)

    @property
    def mode(self):
        return 'mw'

    def _query(self, command):
        self.connection.serial.flush()
        return self.connection.query(command)

    def connect_bal(self, reset=False):
        ok = True
        while ok:
            try:
                self.connection = self.record.connect()
                self.connection.rstrip = True

                if reset:
                    self.reset()
                while True:
                    log.debug("...talking to balance...")
                    r = self._query("X")  # 'X' is not recognised by any of the Mettler balances we have, such that an
                    # error string ES is returned.  Sending an empty string to the AT106 repeats the last valid command.
                    log.debug(f'...received {r}...')
                    if r == "ES":
                        break
                assert str(self.record.serial) == str(self.get_serial()), \
                    "Serial mismatch: expected " + str(self.record.serial) + " but received " + str(self.get_serial())
                # prints error if false
                break

            except MSLConnectionError:
                self._pt.show('ok_cancel', "Please connect balance to continue")
                ok = self._pt.wait_for_prompt_reply()

    def reset(self):
        log.info('Balance reset')
        return self._query("@")[6: -1]

    def get_serial(self):
        """Gets serial number of balance

        Returns
        -------
        str
            serial number
        """
        return self._query("I4")[6: -1]

    def zero_bal(self):
        """Zeroes balance: must ensure no mass on balance"""
        m = self._query("Z").split()
        if m[1] == 'A':
            log.info('Balance zeroed')
            return
        self._raise_error(m[0]+' '+m[1])

    def scale_adjust(self):
        """Adjusts scale using internal weights"""
        m = self._query("C3").split()
        if m[1] == 'B':
            app = application()
            print('Balance self-calibration commencing')
            log.info('Balance self-calibration commencing')
            t0 = perf_counter()
            while True:
                app.processEvents()
                try:
                    c = self.connection.read().split()
                    if c[1] == 'A':
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

        self._raise_error(m[0]+' '+m[1])

    def tare_bal(self):
        """Tares balance after checking with user that tare load is correct"""

        self._pt.show('ok_cancel', 'Check that the balance has correct tare load, then press enter to continue.')
        ok = self._pt.wait_for_prompt_reply()

        if ok:
            m = self._query("T").split()
            if m[1] == 'S':
                log.info('Balance tared with value '+m[2]+' '+m[3])
                return
            self._raise_error(m[0]+' '+m[1])

    def get_mass_instant(self):
        """Reads instantaneous mass from balance. Includes a check that the balance has been read correctly.

        Returns
        -------
        float
            mass in unit of balance
        None
            if serial read error
        error code
            if balance read correctly but error raised
        """
        m = self._query("SI").split()
        return self.parse_mass_reading(m)

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
        if self.check_reading(m):
            if m[1] == 'S':
                return float(m[2])
            elif m[1] == 'D':
                log.info('Reading is nonstable (dynamic) weight value')
                return float(m[2])
            else:
                self._raise_error(m[0]+' '+m[1])
        else:
            return None

    def get_mass_stable(self, mass):
        """Reads mass from balance when reading is stable.  Returns the average of three readings,
        ensuring a maximum deviation between readings of twice the balance resolution.

        Returns
        -------
        float
            mass in unit set for balance
        """
        if not self.want_abort:
            log.info('Waiting for stable reading for '+mass)
            readings = []
            t0 = perf_counter()

            m = self._query("S")
            if m:
                a = self.parse_mass_reading(m.split())  # handles any errors if not a valid mass value
                if type(a) == float:
                    readings.append(a)

            while perf_counter() - t0 < self.stable_wait:
                while len(readings) < 3:
                    b = self.get_mass_instant()
                    if type(b) == float:
                        readings.append(b)
                    elif not b:
                        continue
                    else:
                        return b

                if max(readings) - min(readings) <= 2*self.resolution:
                    return sum(readings)/len(readings)
                else:
                    log.warning(f"First collected readings not self consistent: {readings}")
                    readings = []
                    continue

            self._raise_error('U')

    def check_reading(self, m, index=3):
        """Checks that the reading is a valid mass value by determining the unit returned in position index"""
        try:
            if not m[index] == self.unit:
                if self._suffix[m[index]]:
                    log.warning('Balance unit set to ' + self.unit + ' but received ' + m[index] +
                                '. Unit and resolution are now in ' + m[index]+'.')
                    self._resolution = SUFFIX[self.unit]/SUFFIX[m[index]]*self.resolution
                    self._unit = m[index]
                    return True
                else:
                    log.warning('Serial error when reading balance OR incorrect unit set')
                    return False
            return True
        except IndexError:
            return m

    def _raise_error(self, errorkey):
        if errorkey:
            raise ValueError(ERRORCODES.get(errorkey, 'Unknown serial communication error: {}'.format(errorkey)))

    def close_connection(self):
        self.connection.disconnect()


ERRORCODES = {
    'E L':   'Error received from AT106',
    'Z I':  'Zero setting not performed (balance is currently executing another command, '
            'e.g. taring, or timeout as stability was not reached).',
    'Z +':  'Upper limit of zero setting range exceeded.',
    'Z -':  'Lower limit of zero setting range exceeded',
    'ZI I': 'Zero setting not performed (balance is currently executing another command, '
            'e.g. taring, or timeout as stability was not reached).',
    'ZI +': 'Upper limit of zero setting range exceeded.',
    'ZI -': 'Lower limit of zero setting range exceeded',
    'C3 I': 'A calibration can not be performed at present as another operation is taking place.',
    'C3 L': 'Calibration operation not possible, e.g. as internal weight missing.',
    'CAL C': 'The calibration was aborted as, e.g. stability not attained or the procedure was aborted with the C key.',
    'T I':  'Taring not performed (balance is currently executing another command, '
            'e.g. zero setting, or timeout as stability was not reached).',
    'T +':  'Upper limit of taring range exceeded.',
    'T -':  'Lower limit of taring range exceeded.',
    'S I':  'Command not executable (balance is currently executing another command, '
            'e.g. taring, or timeout as stability was not reached).',
    'S +':  'Balance in overload range.',
    'S -':  'Balance in underload range.',
    'SI':   'No valid result can be transmitted at present',  # specific to AT106
    'SI+':  'Balance in overload range.',
    'SI-':  'Balance in underload range.',
    'U':    'Timed out while trying to obtain three close readings from get_mass_stable ',
    'POS':  'Selected position invalid',
    'ET':   'Error Transmission: At least one character of the command has a parity error. The command will be ignored.',
    'FE 1': 'FATAL ERROR: Top Position, but light barrier (lift) open!',
    'FE 2': 'FATAL ERROR: Light barriers not connected!',
    'LT':   'Error in lift position when raising or lowering weight',
    'UL':   'Incorrect mass loaded: underload error',
    'OL':   'Incorrect mass loaded: overload error',
}