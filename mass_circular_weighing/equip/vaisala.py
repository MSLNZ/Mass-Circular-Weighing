from datetime import datetime
from time import perf_counter

from msl.equipment import MSLTimeoutError, MSLConnectionError

from ..log import log


class Vaisala(object):

    def __init__(self, record):

        self.record = record
        self.connection = None

    def open_comms(self):
        self.connection = self.record.connect()
        self.connection.write("S")
        self.check_serial()

    def _query(self, command):
        self.connection.serial.flush()
        return self.connection.query(command)

    def check_serial(self):
        assert self.record.serial == self._query("*9900SN")
        return

    def display_info(self):
        self.connection.write("?")
        while True:
            ok = self.connection.read()
            print(ok)
            if not ok:
                break

    def set_format(self):
        # WARNING: This function is upsetting the settings at the moment
        self.connection.write("FORM 4.3 P "" "" 3.3 T "" "" 3.3 RH "" "" SN \r \n \r\n")
        t0 = perf_counter()
        while perf_counter() - t0 < 30:
            ok = self.connection.read()
            if not ok:
                break

        return ok
        #     print(self.connection.read())
        #     return True
        # else:
        #     print(ok)
        #     return False

    def get_readings(self):
        i = 0
        while i < 5:
            reading = self.connection.query("SEND")
            ok = self.check_readings(reading)
            if ok:
                readings = reading.split()
                return datetime.now(), float(readings[1]), float(readings[2]), float(readings[0])
            i += 1
        log.error("Unable to get sensible readings from Vaisala after 5 attempts")
        return datetime.now(), None, None, None

    def check_readings(self, reading):
        """Checks reading for serial read error

        Parameters
        ----------
        reading : str

        Returns
        -------
        Bool of values in string ok or not
        """
        r_list = reading.split()
        if not 400 <= float(r_list[0]) <= 1200:
            log.warning("Pressure reading invalid. Received {}".format(r_list[0]))
            return False
        if not 10 <= float(r_list[1]) <= 30:
            log.warning("Temperature reading invalid. Received {}".format(r_list[1]))
            return False
        if not 0 <= float(r_list[2]) <= 100:
            log.warning("Humidity reading invalid. Received {}".format(r_list[1]))
            return False
        if not r_list[-1] == self.record.serial:
            log.warning("Serial number missing or incorrect in reading string."
                        " Received {}".format(r_list[-1]))
            return False
        return True

    def close_comms(self):
        self.connection.disconnect()

