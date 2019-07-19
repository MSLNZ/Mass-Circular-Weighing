# Generic class for a balance without a computer interface

from ..constants import SUFFIX
from ..log import log
from time import sleep


class Balance(object):
    def __init__(self, record):
        """Initialise a balance which does not have a computer interface

        Parameters
        ----------
        record : equipment record object
            get via Application(config).equipment[alias]
            Requires an MSL.equipment config.xml file
        """
        self.record = record
        self._suffix = SUFFIX

        try:
            self._unit = record.user_defined['unit']
        except:
            self.set_unit()

        self.stable_wait = record.user_defined['stable_wait']
        # wait time in seconds for balance reading to stabilise


    @property
    def unit(self):
        return str(self._unit)

    def set_unit(self):
        """Prompts user to select the unit of mass from {mg, g, kg}"""
        while True:
            try:
                self._unit = input('Please enter unit (µg or ug, mg, g, or kg):')
                suffix = self._suffix[self._unit]
            except:
                print("Invalid entry")
                continue
            else:
                break
        return self._unit

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

    def get_mass_instant(self):
        """Asks user to enter mass from balance
        Returns
        -------
        float
            mass (in unit set for balance when initialised)
        """
        reading = 0
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
                if reading == 'abort' or reading == 'cancel':
                    raise KeyboardInterrupt
                else:
                    print("Invalid entry")
                    continue
            else:
                break
        log.info('Mass reading: '+str(reading)+' '+str(self._unit))
        return reading

    def get_mass_stable(self):
        print('Waiting for stable reading')
        try:
            sleep(self.stable_wait)
            reading = self.get_mass_instant()
            return reading
        except KeyboardInterrupt:
            raise KeyboardInterrupt