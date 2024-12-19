"""
Collect ambient information from the server
"""
import re
from datetime import datetime
from subprocess import check_output

import requests
import numpy as np

from ..log import log


# Hardwire the address running the server
host = 'AX1006-NUC'  # '172.16.31.199' is CISS33748 (NUC); '172.16.31.103' is CISS31653 (Laptop)
port = '1875'
server_add = ":".join(['http://' + host, port])


def get(route, params=None):
    return requests.get(server_add + route, params=params, timeout=10)


def handle_exception(e):
    """A helper function to handle when get() fails to communicate with the server.

    Parameters
    ----------
    e : error
        the error message
    """
    log.error(e)
    if not ping(host):
        log.error('The server is currently not pingable at {}. '
                  'Are both computers on the CI network?'.format(host))
    else:
        log.error('The server is pingable but not responding to requests. '
                  'Please check ambient monitoring is running.')


def get_t_rh_now(ithx_name, sensor=""):
    """Gets both temperature and humidity data for the current time (server directly contacts the Omega ithx).

    Parameters
    ----------
    ithx_name : :class:`str`
        The name assigned to the OMEGA iTHX device. For example:

        * 'temperature 1'
        * 'mass 1'
        * 'mass 2'

    sensor : :class:`int` or `str`
        The OMEGA iTHX sensor from which to get the data.
        Either 1 or 2 for a two-probe device, or an empty string if only one probe (not currently implemented).

    Returns
    -------
    :class:`datetime.datetime`
        The timestamp of the latest recorded value.
    :class:`float` or :data:`None`
        The temperature value.
    :class:`float` or :data:`None`
        The humidity value.
    """
    date_now = datetime.now().replace(microsecond=0).isoformat(sep=' ')

    try:
        json = get('/now', params={'alias': ithx_name}).json()
    except Exception as e:
        json = {}
        handle_exception(e)

    if not json:  # i.e. an empty dictionary is returned
        log.error("No Omega device available with that alias!")
        return datetime.now().replace(microsecond=0).isoformat(sep=' '), None, None

    if len(json) > 1:
        log.warning("More than one device with that alias")  # there should only be one...

    for serial, info in json.items():
        if json[serial]['error']:
            log.error(json[serial]['error'])
        if info['alias'] == ithx_name:
            t_now = info['temperature' + str(sensor)]
            rh_now = info['humidity' + str(sensor)]
            return date_now, t_now, rh_now


def get_t_rh_during(ithx_name, sensor="", start=None, end=None):
    """Gets a list of temperature and humidity values since the specified start time.

    Parameters
    ----------
    ithx_name : :class:`str`
        The name assigned to the OMEGA iTHX device. For example:

        * 'temperature 1'
        * 'mass 1'
        * 'mass 2'

    sensor : :class:`int` or `str`
        The OMEGA iTHX sensor from which to get the data.
        Either 1 or 2 for a two-probe device, or an empty string if only one probe.

    start : optional
        Start date and time as an ISO 8601 string (e.g. YYYY-MM-DDThh:mm:ss).
        If not specified, default is earliest record in database.

    end : optional
        End date and time as an ISO 8601 string. Default is now.

    Returns
    -------
    :class:`numpy.ndarray` or :data:`None`
        The temperature values and the humidity values
    """
    try:
        json = get('/fetch',
                   params={'alias': ithx_name, 'start': start, 'end': end}
                   ).json()
    except Exception as e:
        json = {}
        handle_exception(e)

    if not json:  # i.e. an empty dictionary is returned
        log.error("No data available for alias {}".format(ithx_name))
        return None, None

    if len(json) > 1:
        log.warning("More than one device with that alias")  # there should only be one...

    for serial, info in json.items():
        if json[serial]['error']:
            log.error(json[serial]['error'])
        if info['alias'] == ithx_name:
            timed_temperatures = info['temperature' + str(sensor)]
            timed_humidities = info['humidity' + str(sensor)]

            temperatures = np.asarray([a[1] for a in timed_temperatures])
            humidities = np.asarray([a[1] for a in timed_humidities])

            # sanity check to let the user know why there might not be data in the specified date range
            if temperatures.size == 0 and humidities.size == 0:
                error = 'No data in the database for iTHX={!r}, start={}, end={}.'.format(ithx_name, start, end)

                if end is None:
                    log.warning(f'{error} Collecting current ambient conditions instead.')
                    date_now, t_now, rh_now = get_t_rh_now(ithx_name, sensor=sensor)
                    temperatures, humidities = [t_now], [rh_now]

                else:
                    log.warning(error)

            return temperatures, humidities


def get_aliases():
    try:
        json = get('/aliases').json()
    except Exception as e:
        json = {}
        handle_exception(e)

    return json


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
