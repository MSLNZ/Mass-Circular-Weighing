"""
Use Emile's DLL to fetch data from the LabEnviron server.
"""
import os
import re
from textwrap import wrap
from subprocess import check_output
from ctypes import (
    c_char_p,
    c_int16,
    c_int32,
    c_double,
    POINTER,
    create_string_buffer,
)
from datetime import (
    date,
    datetime,
    timedelta,
)

from msl.loadlib import (
    Client64,
    Server32,
    IS_PYTHON_64BIT,
)


if IS_PYTHON_64BIT:
    import numpy as np
    from ..gui.threads.prompt_thread import PromptThread
    from ..constants import FONTSIZE
    from ..log import log
    prompt_thread = PromptThread()


class LabEnviron32(Server32):

    def __init__(self, host, port, quiet, **kwargs):
        """Wrapper around Emile's 32-bit LabVIEW DLL."""
        super(LabEnviron32, self).__init__('LabEnviron_V1.3.dll', 'cdll', host, port, quiet)

        self.server_ip = kwargs['server_ip'].encode()

        self.lib.LabClientDLLGetSize.restype = None
        self.lib.LabClientDLLGetSize.argtypes = [
            c_int32,           # Probe
            c_char_p,          # ServerIP
            c_char_p,          # iTHXName
            POINTER(c_int32),  # Dates
            POINTER(c_int32),  # Size
            c_char_p,          # Error
            POINTER(c_int16),  # Status
            c_int32,           # length of Dates array
            c_int32,           # length of Error string
        ]

        self.lib.LabClientDLL.restype = None
        self.lib.LabClientDLL.argtypes = [
            c_int32,            # Probe
            c_char_p,           # ServerIP
            c_char_p,           # iTHXName
            POINTER(c_int32),   # Dates
            c_int16,            # Coeff
            POINTER(c_double),  # Xdata
            POINTER(c_double),  # Ydata
            c_char_p,           # Error
            POINTER(c_int16),   # Status
            c_int32,            # length of Dates array
            c_int32,            # length of X array
            c_int32,            # length of Y array
            c_int32,            # length of Error string
        ]

    def get_size(self, ithx_name, probe, date_start, date_end):
        """Calls the ``LabClientDLLGetSize`` function.

        See :meth:`LabEnviron64.get_size` for more details.
        """
        dates = (date_start.day, date_start.month, date_start.year,
                 date_end.day, date_end.month, date_end.year)
        dates = (c_int32 * len(dates))(*dates)
        size = c_int32()
        error = create_string_buffer(128)
        status = c_int16()
        self.lib.LabClientDLLGetSize(
            probe, self.server_ip, ithx_name.encode(), dates, size,
            error, status, len(dates), len(error)
        )
        return size.value, status.value, error.value.decode()

    def get_data(self, ithx_name, probe, date_start, date_end, coeff, size):
        """Calls the ``LabClientDLL`` function.

        See :meth:`LabEnviron64.get_data` for more details.
        """
        dates = (date_start.day, date_start.month, date_start.year,
                 date_end.day, date_end.month, date_end.year)
        dates = (c_int32 * len(dates))(*dates)
        x_data = (c_double * size)()
        y_data = (c_double * size)()
        error = create_string_buffer(128)
        status = c_int16()
        self.lib.LabClientDLL(
            probe, self.server_ip, ithx_name.encode(), dates, coeff,
            x_data, y_data, error, status, len(dates), len(x_data), len(y_data), len(error)
        )
        return [x for x in x_data], [y for y in y_data], status.value, error.value.decode()


class LabEnviron64(Client64):

    LABVIEW_SERVER = '131.203.14.103'  #: The default IP address of the LabVIEW server.

    HUMIDITY_1 = '131.203.8.135'
    MASS_1 = '131.203.15.149'
    MASS_2 = '131.203.15.150'
    RADIATION_1 = '131.203.13.96'
    RADIATION_2 = '131.203.8.134'
    TEMPERATURE_1 = '131.203.13.97'
    TEMPERATURE_2 = '131.203.13.96'

    def __init__(self, server_ip=None):
        """Starts :class:`LabEnviron32` in a 32-bit Python interpreter.

        Since Emile's DLL is built using 32-bit LabVIEW it must be loaded
        from 32-bit Python. Creating an instance of this class will allow
        for communicating with the 32-bit DLL from 64-bit Python.

        Parameters
        ----------
        server_ip : :class:`str`, optional
            The IP address of the LabVIEW server. Uses the default
            IP address if not specified.
        """
        head, tail = os.path.split(__file__)
        dll_dir = os.path.join(head, os.pardir, 'resources')
        if server_ip is not None:
            LabEnviron64.LABVIEW_SERVER = server_ip

        super(LabEnviron64, self).__init__(
            tail, append_sys_path=[head, dll_dir], server_ip=LabEnviron64.LABVIEW_SERVER
        )

        # LabVIEW timestamps are relative to 1 Jan 1904
        # Python timestamps are relative to 1 Jan 1970
        self.x0 = datetime(1970, 1, 1) - datetime(1904, 1, 1)

        self.probe_map = {
            0: 'temperature1',
            1: 'humidity1',
            2: 'dewpoint1',
            3: 'temperature2',
            4: 'humidity2',
            5: 'dewpoint2'
        }

    def get_data(self, ithx_name, probe, date_start=None, date_end=None, coeff=True):
        """Calls the ``LabClientDLL`` function in the DLL.

        Parameters
        ----------
        ithx_name : :class:`str`
            The name assigned to the OMEGA iTHX device. For example:

            * 'temperature 1'
            * 'mass 1'
            * 'mass 2'

        probe : :class:`int`
            The sensor probe to query. Allowed values are:

            * 0 – Temperature sensor 1
            * 1 – Humidity sensor 1
            * 2 – Dew point sensor 1
            * 3 – Temperature sensor 2
            * 4 – Humidity sensor 2
            * 5 – Dew point sensor 2

        date_start : optional
            The starting date to request data from. See :meth:`.to_datetime`
            for the supported data types.

        date_end : optional
            The ending date to request data until. See :meth:`.to_datetime`
            for the supported data types.

        coeff : :class:`bool`, optional
            Whether to apply the calibration coefficients to the returned data.

        Returns
        -------
        :class:`numpy.ndarray`
            A structured array consisting of the timestamps and the values.
        :class:`str`
            The error message. An empty string if there was no error.
        """
        if probe < 0 or probe > 5:
            raise ValueError('The probe value must be between 0 and 5 inclusive, got {}'.format(probe))

        start = self.to_datetime(date_start)
        end = self.to_datetime(date_end)
        if end == start and end.hour == 0 and end.minute == 0 and end.second == 0:
            end = datetime(end.year, end.month, end.day, 23, 59, 59)

        # The data from the OMEGA iTHX devices is logged to CSV files.
        # After 1000 logging events a new CSV file is created. When a request
        # is made for historic data using a date range, the LabVIEW server will
        # only return a list files that were created within this date range.
        # Therefore, a file that crosses over multiple days will only be used
        # if the creation date falls inside the request date period. To work
        # around this feature, we subtract 1 day from date_start and add 1 day
        # to date_end to ensure that all data for the specified range is returned.
        start_minus_1 = start - timedelta(days=1)
        end_plus_1 = end + timedelta(days=1)

        dtype = np.dtype([('timestamp', object), (self.probe_map[probe], np.float)])

        size, status, error = self.request32('get_size', ithx_name, probe, start_minus_1, end_plus_1)
        if status:  # then there was an error from the DLL
            if not self.ping(LabEnviron64.LABVIEW_SERVER):
                error = 'The LabVIEW server at {} is unreachable'.format(LabEnviron64.LABVIEW_SERVER)
            else:
                error += ' [iTHX={!r}, start={}, end={}]'.format(ithx_name, start, end)
            log.error(error)
            return np.array([], dtype=dtype), error

        # fetch the data and select only the date range that was specified
        x_data, y_data, status, error = self.request32(
            'get_data', ithx_name, probe, start_minus_1, end_plus_1, int(coeff), size
        )
        timestamps = [datetime.fromtimestamp(x) - self.x0 for x in x_data]
        data = np.asarray([(d, y) for d, y in zip(timestamps, y_data) if start <= d <= end], dtype=dtype)

        # sanity check to let the user know why there might not be data in the specified date range
        if data.size == 0:
            error = 'No Data From Server [iTHX={!r}, start={}, end={}]'.format(ithx_name, start, end)
            if end.date() == date.today():
                name = ithx_name.upper().replace(' ', '_')
                if not self.ping(getattr(LabEnviron64, name)):
                    error += ' The OMEGA device is currently not pingable.' \
                             ' Is it turned on and connected to the network?'
            log.error(error)

        return data, error

    def get_t_rh_now(self, ithx_name, sensor):
        """Gets both temperature and humidity data for the current time (specifically the last recorded values).

        Parameters
        ----------
        ithx_name : :class:`str`
            The name assigned to the OMEGA iTHX device. For example:

            * 'temperature 1'
            * 'mass 1'
            * 'mass 2'

        sensor : :class:`int`
            The OMEGA iTHX sensor to get the data of. Either 1 or 2.

        Returns
        -------
        :class:`datetime.datetime`
            The timestamp of the latest recorded value.
        :class:`float` or :data:`None`
            The temperature value.
        :class:`float` or :data:`None`
            The humidity value.
        """
        temperatures, humidities = self.get_t_rh_during(ithx_name, sensor, date.today())
        return datetime.now(), temperatures[-1], humidities[-1]

    def get_t_rh_during(self, ithx_name, sensor, start):
        """Gets a list of temperature and humidity values since the specified start time.

        Parameters
        ----------
        ithx_name : :class:`str`
            The name assigned to the OMEGA iTHX device. For example:

            * 'temperature 1'
            * 'mass 1'
            * 'mass 2'

        sensor : :class:`int`
            The OMEGA iTHX sensor to get the data of. Either 1 or 2.

        start : optional
            The starting date to request data from. See :meth:`.to_datetime`
            for the supported data types.

        Returns
        -------
        :class:`numpy.ndarray`
            The temperature values.
        :class:`numpy.ndarray`
            The humidity values.
        """
        t_probe = (sensor - 1) * 3  # probe = 0 or 3
        rh_probe = t_probe + 1

        # fetch the temperature values
        temp_data, error = self.get_data(ithx_name, t_probe, date_start=start)
        if error:
            temperatures = np.array([LabEnviron64.prompt(error, 'temperature')])
        else:
            temperatures = temp_data['temperature{}'.format(sensor)]

        # fetch the humidity values
        rh_data, error = self.get_data(ithx_name, rh_probe, date_start=start)
        if error:
            humidities = np.array([LabEnviron64.prompt(error, 'humidity')])
        else:
            humidities = rh_data['humidity{}'.format(sensor)]

        return temperatures, humidities

    @staticmethod
    def to_datetime(obj=None, fmt='%Y-%m-%d'):
        """Convert an object into a :class:`datetime.datetime`.

        Parameters
        ----------
        obj : :class:`str`, :class:`int`, :class:`float` or :class:`datetime.date`, optional
            The object to convert. If :data:`None` then returns the current date and time.
        fmt : :class:`str`, optional
            If `obj` is of type :class:`str` then the format to use to parse
            the text. See :meth:`~datetime.datetime.strptime` for more details.

        Returns
        -------
        :class:`datetime.datetime`
            The `obj` converted to :class:`datetime.datetime`.
        """
        if obj is None:
            return datetime.now().replace(microsecond=0)
        elif isinstance(obj, str):
            return datetime.strptime(obj, fmt)
        elif isinstance(obj, (int, float)):
            return datetime.fromtimestamp(obj)
        elif isinstance(obj, datetime):
            return obj
        elif isinstance(obj, date):
            return datetime(obj.year, month=obj.month, day=obj.day)
        raise TypeError('Cannot convert {} to a date object'.format(type(obj)))

    @staticmethod
    def ping(host, attempts=3, timeout=1.0):
        """Ping a device to see if it is available on the network.

        Parameters
        ----------
        host : :class:`str`
            The IP address or hostname of the device to ping.
        attempts : :class:`int`, optional
            The maximum number of times to ping the device.
        timeout : :class:`int`, optional
            Timeout in seconds to wait for a reply.

        Returns
        -------
        :class:`bool`
            Whether the device is available.
        """
        i = 0
        wait = str(int(timeout*1e3))
        success_regex = re.compile(r'TTL=\d+', flags=re.MULTILINE)
        while i < attempts:
            try:
                out = check_output(['ping', '-n', '1', '-w', wait, host])
                if success_regex.search(out.decode()):
                    return True
            except:
                return False
            i += 1
        return False

    @staticmethod
    def prompt(error, typ):
        """Request for the user to manually enter a value.

        Parameters
        ----------
        error : :class:`str`
            The error message return from :meth:`.get_data`.
        typ : :class:`str`
            The quantity to enter data for, e.g., Temperature.

        Returns
        -------
        :class:`float` or :data:`None`
            The value that was entered or :data:`None` if the user cancelled the request.
        """
        err = '<br>'.join(wrap(error, 40))
        message = '<html><p style="color:red">{}</p><br>Please enter the {}</html>'.format(err, typ)
        prompt_thread.show('double', message, font=FONTSIZE, minimum=0, maximum=100, title='Ambient Monitoring')
        return prompt_thread.wait_for_prompt_reply()
