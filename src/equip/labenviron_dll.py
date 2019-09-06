import os
from datetime import date, datetime
import ctypes #import byref, c_int32, create_string_buffer, c_int16

from msl.loadlib import Server32, Client64


class Labview32(Server32):
    def __init__(self, host, port, quiet, **kwargs):
        super(Labview32, self).__init__(
            os.path.join(os.path.dirname(__file__),
            r'C:\Users\r.hawke.IRL\PycharmProjects\Mass-Circular-Weighing\resources\LabEnviron_V1.2.dll'),
            'cdll', host, port, quiet)

    def get_size(self, omega_alias, probe, date_start, date_end):
        probe = ctypes.c_int32(probe)
        serverip = ctypes.create_string_buffer(b'131.203.14.103')
        ithxname = ctypes.create_string_buffer(omega_alias.encode('utf-8'))
        if date_start is None:
            date_start = date.today()
        if date_end is None:
            date_end = date.today()
        len1 = ctypes.c_int32(6)    # expected length of date array
        len2 = ctypes.c_int32(128)  # expected length of error string
        dates = (date_start.day, date_start.month, date_start.year, date_end.day, date_end.month, date_end.year)
        dates = (ctypes.c_int32 * len1.value)(*dates)
        size = ctypes.c_int32()
        error = ctypes.create_string_buffer(len2.value)
        status = ctypes.c_int16()
        self.lib.LabClientDLLGetSize(probe, serverip, ithxname, dates, ctypes.byref(size), ctypes.byref(error),
                                     ctypes.byref(status), len1, len2)
        return size.value, status.value, error.value.decode()

    def get_data(self, omega_alias, probe, date_start, date_end, xy_size):
        """returns calibrated value(s) for selected probe and date range

        Parameters
        ----------
        omega_alias : :class:`str`
            omega_alias can be 'temperature 1', 'mass 1' or 'mass 2'
        probe : int
            0 – Temperature sensor 1
            1 – Humidity sensor 1
            2 – Dew point sensor 1
            3 – Temperature sensor 2
            4 – Humidity sensor 2
            5 – Dew point sensor 2
            returns empty array if no second sensor available
        date_start
        date_end
        xy_size

        Returns
        -------
        [x for x in x_data], [y for y in y_data], status.value, error.value.decode()

        """
        # inputs
        #
        probe = ctypes.c_int32(probe)
        serverip = ctypes.create_string_buffer(b'131.203.14.103')
        ithxname = ctypes.create_string_buffer(omega_alias.encode('utf-8'))
        if date_start is None:
            date_start = date.today()
        if date_end is None:
            date_end = date.today()
        len1 = ctypes.c_int32(6)    # expected length of date array
        dates = (date_start.day, date_start.month, date_start.year, date_end.day, date_end.month, date_end.year)
        dates = (ctypes.c_int32 * len1.value)(*dates)
        coeff = ctypes.c_int16(1)   # if not zero, uses calibration coefficients

        len2 = ctypes.c_int32(xy_size)  # expected length of X array
        len3 = ctypes.c_int32(xy_size)  # expected length of Y array
        len4 = ctypes.c_int32(128)  # expected length of error string

        # outputs
        x_data = (ctypes.c_double * len2.value)()  # Can't pickle c_long_Array_3000 or c_double_Array_3000. c_float breaks it properly
        y_data = (ctypes.c_double * len3.value)()
        error = ctypes.create_string_buffer(len4.value)
        status = ctypes.c_int16()

        self.lib.LabClientDLL(probe, serverip, ithxname, dates, coeff,
                              ctypes.byref(x_data), ctypes.byref(y_data),
                              ctypes.byref(error), ctypes.byref(status),
                              len1, len2, len3, len4)
        return [x for x in x_data], [y for y in y_data], status.value, error.value.decode()


class LabEnviron64(Client64):

    def __init__(self):
        super(LabEnviron64, self).__init__(module32='labenviron_dll', append_sys_path=os.path.dirname(__file__))
        self.size = None
        self.date_start = None
        self.date_end = None

    def get_size(self, omega_alias, probe, date_start=None, date_end=None):
        self.date_start = date_start
        self.date_end = date_end
        self.size, status, error = self.request32('get_size', omega_alias, probe, date_start=date_start, date_end=date_end)
        return self.size, status, error

    def get_data(self, omega_alias, probe, date_start=None, date_end=None,):
        x_data, y_data, status, error = self.request32('get_data', omega_alias, probe,
                                                       date_start=date_start, date_end=date_end, xy_size=self.size)
        return x_data, y_data, status, error


if __name__ == '__main__':
    dll = LabEnviron64()
    diff = datetime(1970, 1, 1) - datetime(1904, 1, 1)
    size, status, error = dll.get_size('mass 2', 0, date_start=date(2019, 9, 5), date_end=date(2019, 9, 5))
    #print(size, status, error)
    data = dll.get_data('mass 2', 0,  date_start=date(2019, 9, 5), date_end=date(2019, 9, 5))

    print(datetime.fromtimestamp(data[0][0])-diff, data[1][0])



'''
wnat to record max and min temp during weighing? e.g. check initial is ok, then

def get_t_rh(self):
        connection = self.record.connect()
        t1, rh1 = connection.temperature_humidity(probe=1, nbytes=12)
        t2, rh2 = connection.temperature_humidity(probe=2, nbytes=12)

        ambient = {
            'RH (%)': np.round((rh1 + rh2)/2, 3),
            'T'+IN_DEGREES_C: np.round((t1 + t2)/2, 3),
        }

        return ambient'''