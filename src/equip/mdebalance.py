# Generic class for a balance without a computer interface

from ..constants import SUFFIX
from ..log import log
from time import sleep
from msl.qt import prompt


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

        try:
            resolution = record.user_defined['resolution'].split()
            self._resolution = float(resolution[0])*SUFFIX[resolution[1]]/SUFFIX[self.unit]
        except:
             self._resolution = 0.000001
        self.dp = self.calc_dp()

        self.stable_wait = record.user_defined['stable_wait']
        # wait time in seconds for balance reading to stabilise

        self._want_abort = False

    @property
    def unit(self):
        return str(self._unit)

    @property
    def resolution(self):
        return self._resolution

    @property
    def want_abort(self):
        return self._want_abort

    def calc_dp(self):
        str = "{:.0e}".format(self.resolution)
        e = float(str.split('e')[1])
        if e < 0:
            return -e
        return 0

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
        if not self.want_abort:
            zeroed = prompt.instruction("Zero balance with no load.")
            if not zeroed:
                self._want_abort = True

    def scale_adjust(self):
        """Prompts user to adjust scale using internal weights"""
        if not self.want_abort:
            adjusted = prompt.instruction("Perform internal balance calibration.")
            if not adjusted:
                self._want_abort = True

    def tare_bal(self):
        """Prompts user to tare balance with correct tare load"""
        if not self.want_abort:
            tared = prompt.instruction('Check that the balance has correct tare load, then tare balance.')
            if not tared:
                self._want_abort = True

    def load_bal(self, mass):
        """Prompts user to load balance with specified mass"""
        if not self.want_abort:
            loaded = prompt.instruction('Load balance with mass '+mass+'.')
            if not loaded:
                self._want_abort = True

    def unload_bal(self, mass):
        """Prompts user to remove specified mass from balance"""
        if not self.want_abort:
            unloaded = prompt.instruction('Unload mass '+mass+' from balance.')
            if not unloaded:
                self._want_abort = True

    def get_mass_instant(self):
        """Asks user to enter mass from balance
        Returns
        -------
        float
            mass (in unit set for balance when initialised)
        """
        reading = 0
        while not self.want_abort:
            try:
                reading = prompt.double("Enter balance reading: ", precision=self.dp, title='Reading')
                if not reading and not reading == 0:
                    self._want_abort = True
                while not self.want_abort:
                    result = prompt.y_n_cancel("Mass reading: "+str(reading)+' '+self._unit+
                                     '\n \nIs this reading correct?')
                    if result == 'Yes':
                        break
                    elif result == 'Cancel':
                        self._want_abort = True
                        break
                    reading = prompt.double("Enter balance reading: ", precision=self.dp, title='Reading')
            except ValueError:
                log.error("Invalid entry")
                continue
            else:
                break
        log.info('Mass reading: '+str(reading)+' '+str(self._unit))
        return reading

    def get_mass_stable(self):
        while not self.want_abort:
            log.info('Waiting for stable reading')
            sleep(self.stable_wait)
            reading = self.get_mass_instant()
            return reading
