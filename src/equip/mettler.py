'''Class for Mettler Toledo Balance'''

from ..log import log

class MettlerToledo(object):
    def __init__(self, cfg, alias, reset=True):
        """Initialise Mettler Toledo Balance

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
        """Zeroes balance"""
        m = self.connection.query("Z").split()
        if m[1] == 'A':
            log.info('Balance zeroed')
            return
        self._raise_error(m[0]+' '+m[1])

    def get_mass(self):
        """Reads mass from balance in grams

        Returns
        -------
        float
            mass in grams
        """
        m = self.connection.query("S").split()
        if m[1] == 'S':
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
    'S I': 'Command not executable (balance is currently executing another command, '
           'e.g. taring, or timeout as stability was not reached).',
    'S +': 'Balance in overload range.',
    'S -': 'Balance in underload range.'
}