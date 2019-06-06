'''Class for Mettler Toledo Balance with computer interface'''

from ..log import log
from time import sleep

class MettlerToledo(object):
    def __init__(self, cfg, alias, reset=True):
        """Initialise Mettler Toledo Balance via computer interface

        Parameters
        ----------
        cfg : msl.equipment.config.Config
            Requires an MSL.equipment config.xml file
        alias : str
            Key of balance in config file
        reset : bool
            True if reset balance desired
        """
        self._record = cfg.database().equipment[alias]
        self.connection = self._record.connect()
        if reset:
            self.reset()
        assert self._record.serial == self.get_serial(), "Serial mismatch"  # prints error if false
        self._suffix = {'mg': 1e-3, 'g': 1, 'kg': 1e3}

    def reset(self):
        log.info('Balance reset')
        return self.connection.query("@")[6: -2]

    def get_serial(self):
        """Gets serial number of balance

        Returns
        -------
        str
            serial number
        """
        return self.connection.query("I4")[6: -2]

    def zero_bal(self):
        """Zeroes balance: must ensure no mass on balance"""
        m = self.connection.query("Z").split()
        if m[1] == 'A':
            log.info('Balance zeroed')
            return
        self._raise_error(m[0]+' '+m[1])

    def scale_adjust(self):
        # TODO: check with Greg that C3 is the correct command to use and that there should be no mass on the balance
        """Adjusts scale using internal weights"""
        m = self.connection.query("C3").split()
        if m[1] == 'B':
            log.info('Balance self-calibration commencing')
            # TODO: How to wait for the balance to finish self-calibration?
            c = 0
            while c == 0:
                try:
                    sleep(5)
                    c = self.connection.read().split()
                    if c[1] == 'A':
                        log.info('Balance self-calibration completed successfully')
                    self._raise_error('C3 C')
        self._raise_error(m[0]+' '+m[1])

    def tare_bal(self):
        """Tares balance after checking with user that tare load is correct"""
        #TODO: Refer to equipment record to prompt user to check correct loading
        m = self.connection.query("T").split()
        if m[1] == 'S':
            log.info('Balance tared with value '+m[2]+' '+m[3])
            return
        self._raise_error(m[0]+' '+m[1])

    def get_mass_stable(self):
        """Reads mass from balance when reading is stable

        Returns
        -------
        float
            mass in grams
        """
        m = self.connection.query("S").split()
        if m[1] == 'S':
            return float(m[2])*self._suffix[m[3]]
        self._raise_error(m[0]+' '+m[1])

    def get_mass_instant(self):
        """Reads instantaneous mass from balance

        Returns
        -------
        float
            mass in grams
        """
        m = self.connection.query("SI").split()
        if m[1] == 'S':
            return float(m[2])*self._suffix[m[3]]
        elif m[1] == 'D':
            log.info('Reading is nonstable (dynamic) weight value')
            return float(m[2])*self._suffix[m[3]]
        self._raise_error(m[0]+' '+m[1])

    def _raise_error(self, errorkey):
        raise ValueError(ERRORCODES[errorkey])




ERRORCODES = {
    'Z I': 'Zero setting not performed (balance is currently executing another command, '
           'e.g. taring, or timeout as stability was not reached).',
    'Z +': 'Upper limit of zero setting range exceeded.',
    'Z -': 'Lower limit of zero setting range exceeded',
    'ZI I': 'Zero setting not performed (balance is currently executing another command, '
            'e.g. taring, or timeout as stability was not reached).',
    'ZI +': 'Upper limit of zero setting range exceeded.',
    'ZI -': 'Lower limit of zero setting range exceeded',
    'C3 I': 'A calibration can not be performed at present as another operation is taking place.',
    'C3 L': 'Calibration operation not possible, e.g. as internal weight missing.',
    'C3 C': 'The calibration was aborted as, e.g. stability not attained or the procedure was aborted with the C key.',
    'T I': 'Taring not performed (balance is currently executing another command, '
           'e.g. zero setting, or timeout as stability was not reached).',
    'T +': 'Upper limit of taring range exceeded.',
    'T -': 'Lower limit of taring range exceeded.',
    'S I': 'Command not executable (balance is currently executing another command, '
           'e.g. taring, or timeout as stability was not reached).',
    'S +': 'Balance in overload range.',
    'S -': 'Balance in underload range.'
}