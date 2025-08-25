import numpy as np
from datetime import datetime
from time import sleep

from ..log import log
from ..constants import FONTSIZE, IN_DEGREES_C
from ..gui.threads.prompt_thread import PromptThread
pt = PromptThread()

from ..equip import get_t_rh_now, get_t_rh_during
from .ambient_fromdatabase import (get_cal_temp_now, get_cal_temp_during,
                                   get_rh_p_now, get_rh_p_during, get_p_rh_t_now, get_p_rh_t_during)
from ..utils.airdens_calculator import AirDens2009


def check_ambient_pre(ambient_details, mode):
    """Check ambient conditions meet quality criteria (in config.xml file) for commencing weighing

    Parameters
    ----------
    ambient_details : :class:`dict`
        dict of ambient monitor alias and limits on ambient conditions
    mode : str
        mode for balance (manual or automatic loading) such as mde, mw, aw_l, aw_c etc

    Returns
    -------
    ambient_pre : :class:`dict`
        dict of ambient conditions at start of weighing:
        {'Start time': datetime object, 'T_pre'+IN_DEGREES_C: float and 'RH_pre (%)': float}
    """
    date_start, t_start, rh_start, p_start = None, None, None, None

    if ambient_details["Type"] == "OMEGA":
        log.info(
            f"COLLECTING AMBIENT CONDITIONS from ambient_logger {ambient_details['Alias']} "
            f"sensor {ambient_details['Sensor']}"
        )
        for i in range(10):  # in case the connection gets aborted by the software in the host machine
            date_start, t_start, rh_start = get_t_rh_now(str(ambient_details['Alias']), sensor=ambient_details['Sensor'])
            if t_start is not None:
                break
            else:
                sleep(1)

        if t_start is None:
            if mode[0] == 'm':  # manual weighing, so the operator is present
                t_start, rh_start = prompt_t_rh(timepoint=None)

            else:  # automatic weighing, so no operator is present
                log.critical('Ambient conditions unavailable! Check connection to OMEGA logger')
                ambient_pre = {
                    'Start time': datetime.now().replace(microsecond=0).isoformat(sep=' '),
                    'T_pre' + IN_DEGREES_C: np.nan,
                    'RH_pre (%)': np.nan,
                }
                return ambient_pre

    elif ambient_details["Type"] == "Vaisala & milliK Databases":
        log.info(f"COLLECTING AMBIENT CONDITIONS from databases for ambient_logger {ambient_details['Alias']}")
        channel = int(ambient_details['milliK'][-1])
        date_start, t_start = get_cal_temp_now(channel=channel)
        rh_start, p_start = get_rh_p_now(ambient_details['Vaisala'])

    elif ambient_details["Type"] == "Vaisala Indigo Database":
        log.info(f"COLLECTING AMBIENT CONDITIONS from database for ambient_logger {ambient_details['Alias']}")
        transmitter_sn = ambient_details['transmitter']
        probe_sn = ambient_details['probe']
        date_start, p_start, rh_start, t_start = get_p_rh_t_now(transmitter_sn, probe_sn)

    else:
        log.error("Unrecognised ambient monitoring sensor")
        return False

    # these shouldn't be reached unless the operator intends to cancel the weighing
    if not t_start:
        log.warning('Missing initial ambient temperature value')
        return False
    if not rh_start:
        log.warning('Missing initial ambient humidity value')
        return False

    ambient_pre = {'Start time': date_start, 'T_pre'+IN_DEGREES_C: np.round(t_start, 2), 'RH_pre (%)': np.round(rh_start, 1), }
    if p_start:
        ambient_pre["P_pre (hPa)"] = p_start

    log.info(f"Ambient conditions: Temperature{IN_DEGREES_C}: {ambient_pre['T_pre'+IN_DEGREES_C]}; "
             f"Humidity (%): {ambient_pre['RH_pre (%)']}")

    if ambient_details['MIN_T'] < ambient_pre['T_pre'+IN_DEGREES_C] < ambient_details['MAX_T']:
        log.info('Ambient temperature OK for weighing')
    else:
        log.warning('Ambient temperature does not meet limits')
        return False

    if ambient_details['MIN_RH'] < ambient_pre['RH_pre (%)'] < ambient_details['MAX_RH']:
        log.info('Ambient humidity OK for weighing')
    else:
        log.warning('Ambient humidity does not meet limits')
        return False

    return ambient_pre


def check_ambient_post(ambient_pre, ambient_details, mode):
    """Check ambient conditions met quality criteria during weighing

    Parameters
    ----------
    ambient_pre : :class:`dict`
        dict of ambient conditions at start of weighing:
        {'Start time': datetime object, 'T_pre'+IN_DEGREES_C: float and 'RH_pre (%)': float}
    ambient_details : :class:`dict`
        dict of ambient monitor alias and limits on ambient conditions
    mode : str
        mode for balance (manual or automatic loading) such as mde, mw, aw_l, aw_c etc

    Returns
    -------
    ambient_post : :class:`dict`
        dict of ambient conditions at end of weighing, and evaluation of overall conditions during measurement.
        dict has key-value pairs {'T_post'+IN_DEGREES_C: list of floats, 'RH_post (%)': list of floats, 'Ambient OK?': bool}
    """
    ambient_post = {}
    t_data = None
    rh_data = None
    p_data = None
    if ambient_details["Type"] == "OMEGA":
        log.info(
            f"COLLECTING AMBIENT CONDITIONS from ambient_logger {ambient_details['Alias']} "
            f"sensor {ambient_details['Sensor']}"
        )
        for i in range(10):  # in case the connection gets aborted by the software in the host machine
            t_data, rh_data = get_t_rh_during(
                str(ambient_details['Alias']),
                sensor=ambient_details['Sensor'],
                start=ambient_pre['Start time']
            )
            if t_data is not None:
                break
            else:
                sleep(1)
        # t_data and rh_data returned as numpy ndarrays

        if t_data is None:
            if mode[0] == 'm':  # manual weighing, so the operator is present
                t_data, rh_data = prompt_t_rh(timepoint=datetime.now().replace(microsecond=0).isoformat(sep=' '))
                t_data = [t_data]
                rh_data = [rh_data]

            else:  # automatic weighing, so no operator is present
                log.critical('Ambient conditions unavailable! Check connection to OMEGA logger')

                ambient_post['T_pre' + IN_DEGREES_C] = ambient_pre['T_pre' + IN_DEGREES_C]
                log.warning('Ambient temperature change during weighing not recorded')

                ambient_post['RH_pre (%)'] = ambient_pre['RH_pre (%)']
                log.warning('Ambient humidity change during weighing not recorded')

                ambient_post = {'Ambient OK?': None}

                return ambient_post

    elif ambient_details["Type"] == "Vaisala & milliK Databases":
        log.info(f"COLLECTING AMBIENT CONDITIONS from databases for ambient_logger {ambient_details['Alias']}")
        # convert back to datetime object
        start = datetime.fromisoformat(ambient_pre['Start time'])
        channel = int(ambient_details['milliK'][-1])
        t_data = get_cal_temp_during(channel=channel, start=start)
        rh_data, p_data = get_rh_p_during(ambient_details['Vaisala'], start=start)

    elif ambient_details["Type"] == "Vaisala Indigo Database":
        log.info(f"COLLECTING AMBIENT CONDITIONS from database for ambient_logger {ambient_details['Alias']}")
        # convert back to datetime object
        start = datetime.fromisoformat(ambient_pre['Start time'])
        transmitter_sn = ambient_details['transmitter']
        probe_sn = ambient_details['probe']
        p_data, rh_data, t_data = get_p_rh_t_during(transmitter_sn, probe_sn, start=start)

    else:
        log.error("Unrecognised ambient monitoring sensor")
        return False

    if p_data is not None:
        ambient_post["All Pressures (hPa)"] = p_data
        ambient_post["Pressure (hPa)"] = f'{round(min(p_data), 4)} to {round(max(p_data), 4)}'
        mean_P = sum(p_data) / len(p_data)
        ambient_post["Mean Pressure (hPa)"] = str(mean_P)

    if not t_data[0]:
        ambient_post['T_pre'+IN_DEGREES_C] = ambient_pre['T_pre'+IN_DEGREES_C]
        log.warning('Ambient temperature change during weighing not recorded')
        ambient_post = {'Ambient OK?': None}
    else:
        # t_data = np.append(ambient_pre['T_pre'+IN_DEGREES_C], t_data)
        ambient_post["All Temps"+IN_DEGREES_C] = t_data
        ambient_post['T range' + IN_DEGREES_C] = str(round(min(t_data), 3)) + ' to ' + str(round(max(t_data), 3))
        mean_temps = sum(t_data) / len(t_data)
        ambient_post["Mean T" + IN_DEGREES_C] = mean_temps
        # temp_range = max(t_data) - min(t_data)
        # ambient_post["T range" + IN_DEGREES_C] = temp_range

    if not rh_data[0]:
        ambient_post['RH_pre (%)'] = ambient_pre['RH_pre (%)']
        log.warning('Ambient humidity change during weighing not recorded')
        ambient_post = {'Ambient OK?': None}
    else:
        # rh_data = np.append(ambient_pre['RH_pre (%)'], rh_data)
        ambient_post["All Humidities (%)"] = rh_data
        ambient_post['RH (%)'] = str(round(min(rh_data), 1)) + ' to ' + str(round(max(rh_data), 1))
        mean_rhs = sum(rh_data) / len(rh_data)
        ambient_post["Mean RH (%)"] = str(mean_rhs)

    if t_data[0] and rh_data[0]:
        if (max(t_data) - min(t_data)) ** 2 > ambient_details['MAX_T_CHANGE']**2:
            ambient_post['Ambient OK?'] = False
            log.warning('Ambient temperature change during weighing exceeds quality criteria')
        elif (max(rh_data) - min(rh_data)) ** 2 > ambient_details['MAX_RH_CHANGE']**2:
            ambient_post['Ambient OK?'] = False
            log.warning('Ambient humidity change during weighing exceeds quality criteria')
        else:
            log.info('Ambient conditions OK during weighing')
            ambient_post['Ambient OK?'] = True

        if p_data is not None:
            if len(p_data) == len(rh_data) == len(t_data):
                all_airdens = []
                for i, t in enumerate(t_data):
                    all_airdens.append(AirDens2009(t, p_data[i], rh_data[i], 0.0004))
                ambient_post["All air density (kg/m3)"] = all_airdens
                airdens = sum(all_airdens) / len(all_airdens)
                ad_stdev = np.std(all_airdens, ddof=1)  # ddof=1 for sample standard deviation
                ambient_post["Stdev air density (kg/m3)"] = ad_stdev
            else:
                airdens = AirDens2009(mean_temps, mean_P, mean_rhs, 0.0004)
                max_airdens = AirDens2009(min(t_data), max(p_data), min(rh_data), 0.0004)
                min_airdens = AirDens2009(max(t_data), min(p_data), max(rh_data), 0.0004)
                print(max_airdens, min_airdens)
                ambient_post["Stdev air density (kg/m3)"] = max_airdens - min_airdens

            ambient_post["Mean air density (kg/m3)"] = airdens

    log.info('Ambient conditions during weighing:')
    for key, value in ambient_post.items():
        log.info(f"\t{key}: {value}")

    return ambient_post


def prompt_t_rh(timepoint):
    """Request for the user to manually enter the ambient monitoring values.

    Returns
    -------
    tuple of two :class:`float`s
        The two values that were entered.
    """
    while True:
        try:
            if timepoint is None:
                tp = datetime.now().replace(microsecond=0).isoformat(sep=' ')
            else:
                tp = timepoint

            message = '<html>Please enter the temperature and humidity values<br>as at {}, ' \
                      'separated by a space</html>'.format(tp)
            pt.show('text', message, font=FONTSIZE, title='Ambient Monitoring')
            reply = pt.wait_for_prompt_reply()
            temperature, humidity = reply.split()
            temperature = float(temperature)
            humidity = float(humidity)
            return temperature, humidity
        except ValueError:
            continue
        except AttributeError:
            return None, None
