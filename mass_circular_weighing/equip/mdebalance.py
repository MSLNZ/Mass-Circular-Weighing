"""
Class for any balance without a computer interface.
Each Balance class instance also holds connection information for the associated ambient monitoring device.
"""
import winsound
from time import perf_counter

from msl.qt import application

from ..constants import SUFFIX, FONTSIZE
from ..log import log

from ..gui.threads.prompt_thread import PromptThread
prompt_thread = PromptThread()


class Balance(object):

    _suffix = SUFFIX

    def __init__(self, record):
        """Initialise a balance which does not have a computer interface

        Parameters
        ----------
        record : equipment record object
            get via Application(config).equipment[alias]
            Requires an MSL.equipment config.xml file
        """
        self.record = record
        self._ambient_instance = None
        self._ambient_details = None
        self._want_abort = False

        self._unit = record.user_defined['unit']
        if not self._unit:
            self.set_unit()

        try:
            resolution = record.user_defined['resolution'].split()
            self._resolution = float(resolution[0])*SUFFIX[resolution[1]]/SUFFIX[self.unit]
        except:
            self._resolution = 0.000001
        self.dp = self.calc_dp()

        self.stable_wait = record.user_defined['stable_wait']
        # wait time in seconds for balance reading to stabilise

    @property
    def mode(self):
        return 'mde'

    @property
    def ambient_instance(self):
        """Connection information for the ambient_instance logging associated with the balance.

        Returns
        -------
        string "OMEGA" or class Vaisala
        """
        return self._ambient_instance

    @property
    def ambient_details(self):
        """Metadata associated with ambient monitoring

        Returns
        -------
        dict of Vaisala or OMEGA alias and limits on ambient conditions
        """
        return self._ambient_details

    @property
    def unit(self):
        return str(self._unit)

    @property
    def resolution(self):
        "Balance resolution in grams"
        return self._resolution

    @property
    def want_abort(self):
        return self._want_abort

    def calc_dp(self):
        """Calculates the number of decimal places displayed on the balance for convenient data entry

        Returns
        -------
        :class:`float`
            The number of decimal places displayed on the balance
        """
        res_string = "{:.0e}".format(self.resolution)
        e = float(res_string.split('e')[1])
        if e < 0:
            return -e
        return 0

    def set_unit(self):
        """Prompts user to select the unit of mass from µg, mg, g, and kg

        Returns
        -------
        :class:`str`
            'µg', 'mg', 'g', or 'kg'
        """
        prompt_thread.show('item', 'Please select unit', ['µg', 'mg', 'g', 'kg'], font=FONTSIZE,
                           title='Balance Preparation')
        self._unit = prompt_thread.wait_for_prompt_reply()
        if not self._unit:
            self._want_abort = True
        return self._unit

    def zero_bal(self):
        """Prompts user to zero balance with no mass on balance"""
        if not self.want_abort:
            prompt_thread.show('ok_cancel', "Zero balance with no load.", font=FONTSIZE,
                               title='Balance Preparation')
            zeroed = prompt_thread.wait_for_prompt_reply()
            if not zeroed:
                self._want_abort = True

    def scale_adjust(self):
        """Prompts user to adjust scale using internal weights"""
        if not self.want_abort:
            prompt_thread.show('ok_cancel', "Perform internal balance calibration.", font=FONTSIZE,
                               title='Balance Preparation')
            adjusted = prompt_thread.wait_for_prompt_reply()
            if not adjusted:
                self._want_abort = True

    def tare_bal(self):
        """Prompts user to tare balance with correct tare load"""
        if not self.want_abort:
            prompt_thread.show('ok_cancel', 'Check that the balance has correct tare load, then tare balance.',
                               font=FONTSIZE, title='Balance Preparation')
            tared = prompt_thread.wait_for_prompt_reply()
            if not tared:
                self._want_abort = True

    def load_bal(self, mass, pos):
        """Prompts user to load balance with specified mass"""
        if not self.want_abort:
            prompt_thread.show('ok_cancel', 'Load mass <b>'+mass+'</b><br><i>(position '+str(pos)+')</i>',
                               font=FONTSIZE, title='Circular Weighing')
            loaded = prompt_thread.wait_for_prompt_reply()
            if not loaded:
                self._want_abort = True
            return loaded
        return False

    def unload_bal(self, mass, pos):
        """Prompts user to remove specified mass from balance"""
        if not self.want_abort:
            winsound.Beep(880, 300)
            print('Unload '+mass+' (position '+str(pos+1)+')')

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
                prompt_thread.show('double', "Enter balance reading: ", font=FONTSIZE, decimals=self.dp,
                                   title='Circular Weighing')
                reading = prompt_thread.wait_for_prompt_reply()
                if not reading and not reading == 0:
                     self._want_abort = True
            except ValueError:
                log.error("Invalid entry")
                continue
            else:
                break
        log.info('Mass reading: '+str(reading)+' '+str(self._unit))
        return reading

    def get_mass_stable(self, mass):
        while not self.want_abort:
            log.info('Waiting for stable reading for '+mass)
            self.wait_for_elapse(self.stable_wait)
            reading = self.get_mass_instant()
            return reading

    def close_connection(self):
        pass

    @staticmethod
    def wait_for_elapse(elapse_time, start_time=None):
        """Wait for a specified time while allowing other events to be processed

        Parameters
        ----------
        elapse_time : int
            time to wait in seconds
        start_time : float
            perf_counter value at start time.
            If not specified, the timer begins when the function is called.
        """
        app = application()
        if start_time is None:
            start_time = perf_counter()
        time = perf_counter() - start_time
        wait_time = elapse_time - time
        log.info("Waiting for {} s...".format(round(wait_time, 1)))
        while time < elapse_time:
            app.processEvents()
            time = perf_counter() - start_time
        log.debug('Wait over, ready for next task')
