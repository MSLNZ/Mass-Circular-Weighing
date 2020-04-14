'''Class for Mettler Toledo Balance with computer interface'''
from time import perf_counter

from msl.equipment import MSLTimeoutError
from msl.qt import prompt, application

from src.log import log
from src.constants import SUFFIX
from src.equip.mdebalance import Balance


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
        self.intcaltimeout = self.record.connection.properties.get('intcaltimeout',30)
        self.connection = self.record.connect()
        if reset:
            self.reset()
        assert self.record.serial == self.get_serial(), \
            "Serial mismatch: expected "+str(self.record.serial)+" but received "+str(self.get_serial())
            # prints error if false

    @property
    def mode(self):
        return 'mw'

    def _query(self, command):
        self.connection.serial.flush()
        return self.connection.query(command)

    def reset(self):
        log.info('Balance reset')
        return self._query("@")[6: -2]

    def get_serial(self):
        """Gets serial number of balance

        Returns
        -------
        str
            serial number
        """
        return self._query("I4")[6: -2]

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
                        print('Balance self-calibration completed successfully')
                        log.info('Balance self-calibration completed successfully')
                        return
                    elif c[1] == 'I':
                        self._raise_error('C3 C')
                except MSLTimeoutError:
                    if perf_counter()-t0 > self.intcaltimeout:
                        raise TimeoutError("Calibration took longer than expected")
                    else:
                        print('Waiting for internal calibration to complete')
                        log.info('Waiting for internal calibration to complete')

        self._raise_error(m[0]+' '+m[1])

    def tare_bal(self):
        """Tares balance after checking with user that tare load is correct"""
        prompt.ok_cancel('Check that the balance has correct tare load, then press enter to continue.')
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
        if self.check_reading(m):
            if m[1] == 'S':
                return float(m[2])
            elif m[1] == 'D':
                log.info('Reading is nonstable (dynamic) weight value')
                return float(m[2])
            else:
                return self._raise_error(m[0]+' '+m[1])
        return None

    def get_mass_stable(self, mass):
        """Reads mass from balance when reading is stable.  Returns the average of three readings,
        ensuring a maximum deviation between readings of twice the balance resolution.

        Returns
        -------
        float
            mass in unit set for balance
        """
        while not self.want_abort:
            log.info('Waiting for stable reading for '+mass)
            readings = []

            m = self._query("S").split()
            if self.check_reading(m):
                if m[1] == 'S':
                    a = float(m[2])
                    readings.append(a)
                else:
                    return self._raise_error(m[0] + ' ' + m[1])

            t0 = perf_counter()
            while perf_counter() - t0 < 30:
                while len(readings) < 3:
                    b = self.get_mass_instant()
                    if type(b) == float:
                        readings.append(b)
                    elif not b:
                        continue
                    else:
                        return b

                if max(readings) - min(readings) < 2*self.resolution:
                    return sum(readings)/3

            self._raise_error('U')

    def check_reading(self, m):
        try:
            if not m[3] == self.unit:
                if self._suffix[m[3]]:
                    log.warning('Balance unit set to ' + self.unit + ' but received ' + m[3] +
                                '. Unit and resolution are now in ' + m[3]+'.')
                    self._resolution = SUFFIX[self.unit]/SUFFIX[m[3]]*self.resolution
                    self._unit = m[3]
                    return True
                else:
                    log.warning('Serial error when reading balance OR incorrect unit set')
                    return False
            return True
        except IndexError:
            print(m)

    def _raise_error(self, errorkey):
        raise ValueError(ERRORCODES.get(errorkey,'Unknown serial communication error'))




ERRORCODES = {
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
    'C3 C': 'The calibration was aborted as, e.g. stability not attained or the procedure was aborted with the C key.',
    'T I':  'Taring not performed (balance is currently executing another command, '
            'e.g. zero setting, or timeout as stability was not reached).',
    'T +':  'Upper limit of taring range exceeded.',
    'T -':  'Lower limit of taring range exceeded.',
    'S I':  'Command not executable (balance is currently executing another command, '
            'e.g. taring, or timeout as stability was not reached).',
    'S +':  'Balance in overload range.',
    'S -':  'Balance in underload range.',
    'U':    'Timed out while trying to obtain three close readings from get_mass_stable ',
}