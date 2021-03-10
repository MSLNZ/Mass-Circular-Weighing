"""
Class for a Vaisala device which reads temperature, relative humidity, and pressure
e.g. of type PTU303
"""
from datetime import datetime

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
            if "module 2" in ok.lower():
                break

    def set_format(self):
        """Sets format to 4.3 P " " 3.3 T " " 3.3 RH " " SN " " #r #n
        (same as when reset by Visual Studio program)

        Returns
        -------
        Bool for successful format setting
        """
        self.connection.write('form 4.3 P " " 3.3 T " " 3.3 RH " " SN " " #r #n')

        ok = self.connection.read()

        form = self._query("FORM")
        log.debug("Format of output set to {}".format(form))

        if "ok" in ok.lower():
            return True

        return ok

    def get_readings(self):
        """Read pressure, temperature and humidity from Vaisala.
        With format above, and when reset by Visual Studio program,
        reading appears as 1025.410  19.19  57.83 K1510011 (for example)

        Returns
        -------
        datetime.now(), temp, rh, press or datetime.now(), None, None, None
        """
        i = 0
        while i < 5:
            ok = True
            reading = self.connection.query("SEND")

            r_list = reading.split()
            press = float(r_list[0])
            temp = float(r_list[1])
            rh = float(r_list[2])
            SN = r_list[-1]

            if not 400 <= press <= 1200:
                log.warning("Pressure reading invalid. Received {}".format(press))
                ok = False
            if not 10 <= temp <= 30:
                log.warning("Temperature reading invalid. Received {}".format(temp))
                ok = False
            if not 0 <= rh <= 100:
                log.warning("Humidity reading invalid. Received {}".format(rh))
                ok = False
            if not SN == self.record.serial:
                log.warning("Serial number missing or incorrect in reading string."
                            " Received {}".format(r_list[-1]))
                ok = False
            if ok:
                return datetime.now(), temp, rh, press
            self.set_format()  # try resetting the format to see if that's the problem
            i += 1

        log.error("Unable to get sensible readings from Vaisala after 5 attempts")
        return datetime.now(), None, None, None

    def close_comms(self):
        self.connection.disconnect()

