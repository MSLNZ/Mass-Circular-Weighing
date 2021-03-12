import numpy as np
from datetime import datetime

from ..log import log
from ..constants import FONTSIZE, IN_DEGREES_C
from ..gui.threads.prompt_thread import PromptThread
pt = PromptThread()

from ..equip import get_t_rh_now, get_t_rh_during


def check_ambient_pre(ambient_instance, ambient_details):
    """Check ambient conditions meet quality criteria (in config.xml file) for commencing weighing

    Parameters
    ----------
    ambient_instance : str "OMEGA" or Vaisala instance
    ambient_details : :class:`dict`
        dict of ambient monitor alias and limits on ambient conditions

    Returns
    -------
    ambient_pre : :class:`dict`
        dict of ambient conditions at start of weighing:
        {'Start time': datetime object, 'T_pre'+IN_DEGREES_C: float and 'RH_pre (%)': float}
    """
    if ambient_details["Type"] == "OMEGA":
        log.info('COLLECTING AMBIENT CONDITIONS from ambient_logger '+ambient_details['Alias'] + ' sensor ' + str(ambient_details['Sensor']))

        date_start, t_start, rh_start = get_t_rh_now(str(ambient_details['Alias']), sensor=ambient_details['Sensor'])

        if t_start is None:
            t_start, rh_start = prompt_t_rh(timepoint=None)

    elif ambient_details["Type"] == "Vaisala":
        log.info('COLLECTING AMBIENT CONDITIONS from ambient_logger ' + ambient_details['Alias'])

        ambient_instance.open_comms()
        date_start, t_start, rh_start, p_start = ambient_instance.get_readings()
        ambient_instance.close_comms()

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
    if ambient_details["Type"] == "Vaisala":
        ambient_pre["P_pre (hPa)"] = p_start

    log.info('Ambient conditions: ' +
             'Temperature'+IN_DEGREES_C+': '+str(ambient_pre['T_pre'+IN_DEGREES_C])+
             '; Humidity (%): '+str(ambient_pre['RH_pre (%)']))

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


def check_ambient_post(ambient_pre, ambient_instance, ambient_details):
    """Check ambient conditions met quality criteria during weighing

    Parameters
    ----------
    ambient_pre : :class:`dict`
        dict of ambient conditions at start of weighing:
        {'Start time': datetime object, 'T_pre'+IN_DEGREES_C: float and 'RH_pre (%)': float}
    ambient_instance : str "OMEGA" or Vaisala instance
    ambient_details : :class:`dict`
        dict of ambient monitor alias and limits on ambient conditions

    Returns
    -------
    ambient_post : :class:`dict`
        dict of ambient conditions at end of weighing, and evaluation of overall conditions during measurement.
        dict has key-value pairs {'T_post'+IN_DEGREES_C: list of floats, 'RH_post (%)': list of floats, 'Ambient OK?': bool}
    """
    if ambient_details["Type"] == "OMEGA":
        log.info('COLLECTING AMBIENT CONDITIONS from ambient_logger '+ambient_details['Alias'] + ' sensor ' + str(ambient_details['Sensor']))

        t_data, rh_data = get_t_rh_during(
            str(ambient_details['Alias']),
            sensor=ambient_details['Sensor'],
            start=ambient_pre['Start time']
        )
        # t_data and rh_data returned as numpy ndarrays

        if t_data is None:
            t_data, rh_data = prompt_t_rh(timepoint=datetime.now().replace(microsecond=0).isoformat(sep=' '))
            t_data = [t_data]
            rh_data = [rh_data]

    elif ambient_details["Type"] == "Vaisala":
        log.info('COLLECTING AMBIENT CONDITIONS from ambient_logger ' + ambient_details['Alias'])

        ambient_instance.open_comms()
        date_post, t, rh, p_post = ambient_instance.get_readings()
        ambient_instance.close_comms()
        t_data = [t]
        rh_data = [rh]

    else:
        log.error("Unrecognised ambient monitoring sensor")
        return False

    ambient_post = {}
    if not t_data[0]:
        ambient_post['T_pre'+IN_DEGREES_C] = ambient_pre['T_pre'+IN_DEGREES_C]
        log.warning('Ambient temperature change during weighing not recorded')
        ambient_post = {'Ambient OK?': None}
    else:
        t_data = np.append(t_data, ambient_pre['T_pre'+IN_DEGREES_C])
        ambient_post['T' + IN_DEGREES_C] = str(round(min(t_data), 3)) + ' to ' + str(round(max(t_data), 3))

    if not rh_data[0]:
        ambient_post['RH_pre (%)'] = ambient_pre['RH_pre (%)']
        log.warning('Ambient humidity change during weighing not recorded')
        ambient_post = {'Ambient OK?': None}
    else:
        rh_data = np.append(rh_data, ambient_pre['RH_pre (%)'])
        ambient_post['RH (%)'] = str(round(min(rh_data), 1)) + ' to ' + str(round(max(rh_data), 1))

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

    if ambient_details["Type"] == "Vaisala":
        try:
            ambient_post["Pressure (hPa)"] = [ambient_pre["P_pre (hPa)"], p_post]
        except KeyError:
            ambient_post["Pressure (hPa)"] = p_post

    log.info('Ambient conditions:\n' + str(ambient_post))

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
