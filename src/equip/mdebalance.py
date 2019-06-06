'''Class for any balance without a computer interface'''

from ..log import log
from time import sleep

class ManualBalance(object):
    def __init__(self, cfg, alias):
        """Initialise a balance which does not have a computer interface

        Parameters
        ----------
        cfg : msl.equipment.config.Config
            Requires an MSL.equipment config.xml file
        alias : str
            Key of balance in config file
        """
        self._record = cfg.database().equipment[alias]
        self._suffix = {'mg': 1e-3, 'g': 1, 'kg': 1e3}

    def zero_bal(self):
        """Prompts user to zero balance with no mass on balance"""

    def scale_adjust(self):
        # TODO: check with Greg that C3 is the correct command to use and that there should be no mass on the balance
        """Prompts user to adjust scale using internal weights"""

    def tare_bal(self):
        """Prompts user to tare balance with correct tare load"""
        # TODO: Refer to equipment record to prompt user to check correct loading

    def get_mass(self):
        """Asks user to enter mass from balance when reading is stable
        # TODO: allow user to select unit
        Returns
        -------
        float
            mass in grams
        """