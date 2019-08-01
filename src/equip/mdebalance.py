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

        self.stable_wait = record.user_defined['stable_wait']
        # wait time in seconds for balance reading to stabilise

        self._want_abort = False


    @property
    def unit(self):
        return str(self._unit)

    @property
    def want_abort(self):
        return self._want_abort

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
            zeroed = prompt.question("Zero balance with no load.")
            if not zeroed:
                self._want_abort = True

    def scale_adjust(self):
        """Prompts user to adjust scale using internal weights"""
        if not self.want_abort:
            adjusted = prompt.question("Perform internal balance calibration.")
            if not adjusted:
                self._want_abort = True

    def tare_bal(self):
        """Prompts user to tare balance with correct tare load"""
        if not self.want_abort:
            tared = prompt.question('Check that the balance has correct tare load, then tare balance.')
            if not tared:
                self._want_abort = True

    def load_bal(self, mass):
        """Prompts user to load balance with specified mass"""
        if not self.want_abort:
            loaded = prompt.question('Load balance with mass '+mass+'.')
            if not loaded:
                self._want_abort = True

    def unload_bal(self, mass):
        """Prompts user to remove specified mass from balance"""
        if not self.want_abort:
            unloaded = prompt.question('Unload mass '+mass+' from balance.')
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
                reading = prompt.double("Enter balance reading: ", precision=1, title='Reading')
                if not reading:
                    self._want_abort = True
                print('abort flag in reading', self.want_abort)
                while not self.want_abort:
                    #print("Mass reading:", reading, self._unit)
                    item = prompt.item("Mass reading: "+str(reading)+' '+self._unit+
                                     '\n \nIs this reading correct?', ['Yes', 'No', 'Abort weighing'])
                    if item == 'Yes':
                        break
                    elif item =='Abort weighing':
                        print('abort flagged in reading', self.want_abort)
                        self._want_abort = True
                        break
                    reading = prompt.double("Enter balance reading: ", precision=1, title='Reading')
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
