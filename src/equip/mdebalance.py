'''Generic class for a balance without a computer interface'''

from ..log import log

class Balance(object):
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
        self._suffix = {'ug': 1e-6, 'mg': 1e-3, 'g': 1, 'kg': 1e3}
        self._unit = self.set_unit()

    @property
    def record(self):
        return self._record

    def set_unit(self):
        """Prompts user to select the unit of mass from {mg, g, kg}"""
        while True:
            try:
                unit = input('Please enter unit (ug, mg, g, kg):')
                suffix = self._suffix[unit]
            except:
                print("Invalid entry")
                continue
            else:
                break
        return unit

    def zero_bal(self):
        """Prompts user to zero balance with no mass on balance"""
        input("Zero balance with no load, then press enter to continue.")

    def scale_adjust(self):
        """Prompts user to adjust scale using internal weights"""
        input("Perform internal balance calibration, then press enter to continue.")

    def tare_bal(self):
        """Prompts user to tare balance with correct tare load"""
        input('Check that the balance has correct tare load, then press enter to continue.')
        input("Tare balance, then press enter to continue.")

    def load_bal(self, mass):
        """Prompts user to load balance with specified mass"""
        input('Load balance with mass '+mass+', then press enter to continue.')

    def unload_bal(self, mass):
        """Prompts user to remove specified mass from balance"""
        input('Unload mass '+mass+' from balance, then press enter to continue.')

    def get_mass(self):
        """Asks user to enter mass from balance when reading is stable
        Returns
        -------
        float
            mass (in unit set for balance when initialised)
        """
        while True:
            try:
                reading = float(input("Enter balance reading: "))
                while True:
                    print("Mass reading:", reading, self._unit)
                    check = input('If correct, press any key. If not correct, re-enter balance reading')
                    if len(check) < 2:
                        break
                    reading = float(check)
            except ValueError:
                print("Invalid entry")  # TODO: add here options to pause or abort weighing?
                continue
            else:
                break
        log.info('Mass reading: '+str(reading)+' '+str(self._unit))
        return reading