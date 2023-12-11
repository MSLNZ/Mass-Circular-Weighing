"""
Functions to interrogate an SQLite database and return the appropriate values
"""
import os
from datetime import datetime, timedelta
import numpy as np
import sqlite3

from ..log import log
from ..constants import database_dir
m_database_path = os.path.join(database_dir, 'Temperature_milliK.sqlite3')
v_database_path = os.path.join(database_dir, 'Mass_Lab_Vaisala_PTU300.sqlite3')


def data(path, start=None, end=None, as_datetime=True, select='*'):
    """Fetch all the log records between two dates.

    Parameters
    ----------
    path : :class:`str`
        The path to the SQLite_ database.
    start : :class:`datetime.datetime` or :class:`str`, optional
        Include all records that have a timestamp > `start`. If :class:`str` then in
        ``yyyy-mm-dd`` or ``yyyy-mm-dd HH:MM:SS`` format.
    end : :class:`datetime.datetime` or :class:`str`, optional
        Include all records that have a timestamp < `end`. If :class:`str` then in
        ``yyyy-mm-dd`` or ``yyyy-mm-dd HH:MM:SS`` format.
    as_datetime : :class:`bool`, optional
        Whether to fetch the timestamps from the database as :class:`datetime.datetime` objects.
        If :data:`False` then the timestamps will be of type :class:`str` and this function
        will return much faster if requesting data over a large date range.
    select : :class:`str` or :class:`list` of :class:`str`, optional
        The column(s) in the database to use with the ``SELECT`` SQL command.

    Returns
    -------
    :class:`list` of :class:`tuple`
        A list of ``(timestamp, resistance, ...)`` log records,
        depending on the value of `select`.
    """
    if not os.path.isfile(path):
        raise IOError('Cannot find {}'.format(path))

    detect_types = sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES if as_datetime else 0
    db = sqlite3.connect(path, timeout=10.0, detect_types=detect_types,
                         isolation_level=None)  # Open database in Autocommit mode by setting isolation_level to None
    db.execute(
        'pragma journal_mode=wal')  # Set sqlite to Write-Ahead Log (WAL) journal mode to allow concurrent read and write connection to the database
    cursor = db.cursor()

    if isinstance(start, datetime):
        start = start.isoformat(sep='T')
    if isinstance(end, datetime):
        end = end.isoformat(sep='T')
    if select != '*':
        if isinstance(select, (list, tuple, set)):
            select = ','.join(select)
    base = 'SELECT {} FROM data'.format(select)

    if start is None and end is None:
        cursor.execute(base + ';')
    elif start is not None and end is None:
        cursor.execute(base + ' WHERE datetime > ?;', (start,))
    elif start is None and end is not None:
        cursor.execute(base + ' WHERE datetime < ?;', (end,))
    else:
        cursor.execute(base + ' WHERE datetime BETWEEN ? AND ?;', (start, end))

    data = cursor.fetchall()
    cursor.close()
    db.close()

    return data


def apply_calibration_milliK(resistance):
    """Hard-code calibration information for 2023 build-down

    Correction for resistance on channel 1 of milliK:
    <milliK serial="411776.1" channel="1">  <!--  update to 391119-1 when using mass lab milliK -->
            <report date="2020-02-07" number="Temperature/2020/887a">
                <start_date>2020-02-05</start_date>
                <end_date>2020-02-05</end_date>
                <coverage_factor>2.0</coverage_factor>
                <confidence>95%</confidence>
                <resistance unit="Ohm" min="43" max="347">
                    <!--
                      The 'coefficients' element represents the polynomial coefficients
                      c0, c1, c2, c3... to apply as the calibration equation. You can
                      either separate the coefficients by a comma or a semi-colon.
                      The calibration equation is
                          x_corrected = x + dx
                      where,
                          dx = c0 + c1*x + c2*x^2 + c3*x^3 + ...
                    -->
                    <coefficients>4.315e-4, -1.825e-5, 5.672e-8</coefficients>
                    <expanded_uncertainty>0.00031</expanded_uncertainty>
                </resistance>
            </report>
        </milliK>

    Conversion from resistance to temperature for SILM08_4:
    <PRT serial="SILM08_4" channel="1">
        <report date="2018-06-21" number="Temperature/2018/739">
            <start_date>2018-06-19</start_date>
            <end_date>2018-06-20</end_date>
            <coverage_factor>2.0</coverage_factor>
            <confidence>95%</confidence>
            <temperature unit="C" min="0" max="40">
                <!--
                  The 'coefficients' element represents the polynomial coefficients
                  c0, c1, c2, c3... to apply as the calibration equation. You can
                  either separate the coefficients by a comma or a semi-colon.
                  The calibration equation is
                      R(t)/R0 = 1 + At + Bt**2
                -->
                <coefficients>R0=100.0163, A=3.90991e-3, B=-5.891e-7</coefficients>
                <expanded_uncertainty>0.0029</expanded_uncertainty>
            </temperature>
        </report>
    </PRT>

    Parameters
    ----------
    resistance : :class:`float`
        raw resistance value as read from milliK channel 1

    Returns
    -------
    :class:`float` or None
        Calibrated temperature value, if between 0 and 40 deg C, or None.
    """
    def corrected_resistance(r):
        # min="43" max="347"
        if not 43 <= r <= 347:
            log.error(f"Resistance calibration for {r} Ohms is out of calibration range!")
            return None
        a0 = 4.315e-4  # Ohm
        a1 = -1.825e-5
        a2 = 5.672e-8  # per Ohm
        dr = a0 + a1 * r + a2 * r ** 2
        return r + dr

    R = resistance  # raw reading in Ohms
    corr_R = corrected_resistance(R)
    if not corr_R:
        return None

    # Values for 89/S4 (updated 20/07/2023)
    R0 = 99.983886    # raw reading at 0 deg C, in Ohms
    corr_R0 = corrected_resistance(R0)

    A = 0.00391778  # per degree C
    B = -0.0000007329   # per degree C squared

    def solve_quadratic_equation(a, b, c):
        """Use quadratic formula to solve for T
        Equation of form a*T**2 + b*T + c = 0

        Parameters
        ----------
        a : :class:`float`
            coefficient of T**2
        b : :class:`float`
            coefficient of T
        c : :class:`float`
            constant

        Returns
        -------
        temperature, T, in degrees C
        """
        bracket = b**2 - 4*a*c
        T1 = (-b + np.sqrt(bracket))/(2*a)
        T2 = (-b - np.sqrt(bracket))/(2*a)

        return T1, T2

    T1, T2 = solve_quadratic_equation(B, A, 1-corr_R/corr_R0)
    for T in [T1, T2]:
        if 0 <= T <= 40:  # apply min and max limits of calibration
            return T

    log.error(f"No calibration available for values of {T1} or {T2} deg C")
    return None


def get_cal_temp_now():
    """Query the milliK database file for the latest resistance value from CH1, apply the calibration,
    and return the temperature value. If no data is available, the method returns None and logs a warning.

    Returns
    -------
    :class:`tuple` of datetime and :class:`float` or None
        Calibrated temperature value, if between 0 and 40 deg C, or None.
    """
    start = datetime.now() - timedelta(minutes=1)
    end = datetime.now()
    milliK_data = data(path=m_database_path, select='CH1_Ohm', as_datetime=True, start=start, end=end, )
    try:
        latest = milliK_data[-1][0]
        return end.replace(microsecond=0).isoformat(sep=' '), apply_calibration_milliK(latest)
    except IndexError:
        log.error(
            f"No data available within the last minute. "
            f"Please check the milliK is logging to the database at {m_database_path}."
        )
        return end.replace(microsecond=0).isoformat(sep=' '), None


def get_cal_temp_during(start=None, end=None):
    """Query the milliK database file for the resistance values from CH1 between start and end times, apply the
    calibration to each value, and return the list of temperature values.
    If no data is available, the method returns None and logs a warning.

    Parameters
    ----------
    start : datetime
    end : datetime

    Returns
    -------
    :class:`numpy.ndarray` or :data:`None`
        List of calibrated temperature values, if between 0 and 40 deg C, or None.
    """
    milliK_data = data(path=m_database_path, select='CH1_Ohm', as_datetime=True, start=start, end=end, )
    try:
        last_value = milliK_data[-1][0]
        cal_temps = np.asarray([apply_calibration_milliK(i[0]) for i in milliK_data])
        return cal_temps
    except IndexError:
        log.error(
            f"No data available between {start} and {end}. "
            f"Please check the milliK is logging to the database at {m_database_path}."
        )
        return None


def get_rh_p_now():
    """Query the Vaisala database file for the latest humidity and pressure values.
    Note that these values are corrected before being saved to the database as of 12/12/2023
    If no data is available, the method returns a tuple of Nones and logs a warning.

    Returns
    -------
    :class:`list` of :class:`float` or None
        Tuple of the latest humidity and pressure values, or Nones.
    """
    start = datetime.now() - timedelta(minutes=1)
    end = datetime.now()
    vaisala_data = data(path=v_database_path, select='humidity,pressure', as_datetime=True, start=start, end=end, )
    try:
        return vaisala_data[-1]
    except IndexError:
        log.error(
            f"No data available within the last minute. "
            f"Please check the Vaisala is logging to the database at {v_database_path}."
        )
        return None, None


def get_rh_p_during(start=None, end=None):
    """Query the Vaisala database file for the humidity and pressure values between start and end times.
    Note that these values are corrected before being saved to the database as of 12/12/2023
    If no data is available, the method returns tuple of Nones and logs a warning.

    Parameters
    ----------
    start : datetime
    end : datetime

    Returns
    -------
    tuple of :class:`numpy.ndarray` or :data:`None`
        The humidity and pressure values, or None.
    """
    vaisala_data = data(path=v_database_path, select='humidity,pressure', as_datetime=True, start=start, end=end, )
    try:
        humidities = np.asarray([a[0] for a in vaisala_data])
        pressures = np.asarray([a[1] for a in vaisala_data])
        return humidities, pressures
    except IndexError:
        log.error(
            f"No data available between {start} and {end}. "
            f"Please check the Vaisala is logging to the database at {v_database_path}."
        )
        return None, None
