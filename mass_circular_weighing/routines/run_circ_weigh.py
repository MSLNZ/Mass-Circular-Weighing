"""
The main circular weighing routine and analysis routines and their associated helper functions
"""
import os
from time import perf_counter
from datetime import datetime
import numpy as np

from msl.io import JSONWriter, read

from .. import __version__
from ..routine_classes.circ_weigh_class import CircWeigh
from ..constants import IN_DEGREES_C, SUFFIX, MU_STR, local_backup
from ..equip import LabEnviron64
from ..log import log


tab = '  '


def check_for_existing_weighdata(folder, url, se):
    """Reads json file, if it exists, and loads as root object.  Saves backup of existing file.
    Creates new file and corresponding empty root object if file doesn't yet exist.
    
    Parameters
    ----------
    folder : str
    url : path (full) to json file
    se : str

    Returns
    -------
    root : :class:`root`
        msl.io root object with a group for the given scheme entry in the main group 'Circular Weighings'
    """
    if os.path.isfile(url):
        existing_root = read(url)
        if not os.path.exists(folder +"\\backups\\"):
            os.makedirs(folder+"\\backups\\")
        new_index = len(os.listdir(folder + "\\backups\\"))  # counts number of files in backup folder
        new_file = str(folder + "\\backups\\" + se + '_backup{}.json'.format(new_index))
        existing_root.is_read_only = False
        log.debug('Existing root is '+repr(existing_root))
        root = JSONWriter()
        root.set_root(existing_root)
        log.debug('Working root is '+repr(root))
        root.save(root=existing_root, file=new_file, mode='w', encoding='utf-8', ensure_ascii=False)

    else:
        if not os.path.exists(folder):
            os.makedirs(folder)
        log.debug('Creating new file for weighing')
        root = JSONWriter()

    root.require_group('Circular Weighings')
    root['Circular Weighings'].require_group(se)

    return root


def get_next_run_id(root, scheme_entry):
    """Cycles through a root object to get the next unique run_id string for a new measurement"""
    i = 1
    while True:
        run_id = 'run_' + str(i)
        try:
            existing_weighing = root['Circular Weighings'][scheme_entry]['measurement_' + run_id]
            i += 1
        except KeyError:
            break

    return run_id


def do_circ_weighing(bal, se, root, url, run_id, callback1=None, callback2=None,
                     local_backup_folder=local_backup, **metadata):
    """Routine to run a circular weighing by collecting data from a balance.
    This routine currently requires a Vaisala or an OMEGA logger to be specified in the registers
    for monitoring of the ambient conditions

    Parameters
    ----------
    bal : :class:`Balance`
        balance instance, initialised using mass_circular_weighing.configuration using a balance alias
        the ambient logger info/instance is contained within the balance instance
    se : str
        scheme entry
    root : :class:`root`
        msl.io root object into which the weighing data is collected
    url : path
        where the msl.io root object is saved (here as a json file)
    run_id : str
    callback1
        used by gui
    callback2
        used by gui
    local_backup_folder : path
    metadata : :class:`dict`

    Returns
    -------
    msl.io root object if weighing was completed, False if weighing was not started, or None if weighing was aborted.
    """
    local_backup_file = os.path.join(local_backup_folder, url.split('\\')[-1])

    metadata['Program Version'] = __version__
    metadata['Mmt Timestamp'] = datetime.now().strftime('%d-%m-%Y %H:%M')
    metadata['Time unit'] = 'min'
    metadata['Ambient monitoring'] = bal.ambient_details
    metadata['Weighing complete'] = False

    weighing = CircWeigh(se)
    # assign positions to weight groups
    if 'aw' in bal.mode:
        if not bal.positions:
            positions = bal.initialise_balance(weighing.wtgrps)
            # pops up a window to allocate positions, then begins the check_loading, centring and scale_adjust routines
            # within the AWBalCarousel and AWBalLinear classes
            log.debug(str(positions))
            if positions is None:
                log.error("Balance initialisation not complete")
                return None
        else:
            positions = bal.positions
    else:
        positions = range(1, weighing.num_wtgrps + 1)

    positionstr = ''
    positiondict = {}
    for i in range(weighing.num_wtgrps):
        positionstr = positionstr + tab + 'Position '+ str(positions[i]) + ': ' + weighing.wtgrps[i] + '\n'
        positiondict['Position ' + str(positions[i])] = weighing.wtgrps[i]
    metadata["Weight group loading order"] = positiondict

    log.info("BEGINNING CIRCULAR WEIGHING for scheme entry "+ se + ' ' + run_id +
             '\nNumber of weight groups in weighing = '+ str(weighing.num_wtgrps) +
             '\nNumber of cycles = '+ str(weighing.num_cycles) +
             '\nWeight groups are positioned as follows:' +
             '\n' + positionstr.strip('\n'))

    ambient_pre = check_ambient_pre(bal.ambient_instance, bal.ambient_details)
    if not ambient_pre:
        log.info('Measurement not started due to unsuitable ambient conditions')
        return False

    data = np.empty(shape=(weighing.num_cycles, weighing.num_wtgrps, 2))
    weighdata = root['Circular Weighings'][se].require_dataset('measurement_' + run_id, data=data)
    weighdata.add_metadata(**metadata)

    # do circular weighing, allowing for user to cancel weighing:
    reading = None
    while not bal.want_abort:
        times = []
        t0 = 0
        for cycle in range(weighing.num_cycles):
            for i in range(weighing.num_wtgrps):
                if callback1 is not None:
                    callback1(cycle+1, positions[i], weighing.num_cycles, weighing.num_wtgrps)
                mass = weighing.wtgrps[i]
                ok = bal.load_bal(mass, positions[i])
                if 'aw' in bal.mode:
                    if not ok:
                        return None
                reading = bal.get_mass_stable(mass)
                if callback2 is not None:
                    callback2(reading, str(metadata['Unit']))
                if not times:
                    time = 0
                    t0 = perf_counter()
                else:
                    time = np.round((perf_counter() - t0) / 60, 6)  # elapsed time in minutes
                times.append(time)
                weighdata[cycle, i, :] = [time, reading]
                if reading is not None:
                    try:
                        root.save(file=url, mode='w', ensure_ascii=False)
                    except OSError:
                        root.save(file=local_backup_file, mode='w', ensure_ascii=False)
                        log.warning('Data saved to local backup at '+local_backup_file)
                bal.unload_bal(mass, positions[i])
        break

    while not bal.want_abort:
        ambient_post = check_ambient_post(ambient_pre, bal.ambient_instance, bal.ambient_details)
        for key, value in ambient_post.items():
            metadata[key] = value

        metadata['Weighing complete'] = True
        weighdata.add_metadata(**metadata)
        try:
            root.save(file=url, mode='w', ensure_ascii=False)
        except:
            log.debug('weighdata:\n' + str(weighdata[:, :, :]))
            root.save(file=local_backup_file, mode='w', ensure_ascii=False)
            log.warning('Data saved to local backup: ' + local_backup_file)

        return root

    log.info('Circular weighing sequence aborted')
    if reading:
        weighdata.add_metadata(**metadata)
        try:
            root.save(file=url, mode='w', ensure_ascii=False)
        except OSError:
            root.save(file=local_backup_file, mode='w', ensure_ascii=False)
            log.warning('Data saved to local backup file: ' + local_backup_file)

    return None


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

        LabView_dll = LabEnviron64()
        date_start, t_start, rh_start = LabView_dll.get_t_rh_now(str(ambient_details['Alias']), ambient_details['Sensor'])
        LabView_dll.shutdown_server32()

    elif ambient_details["Type"] == "Vaisala":
        log.info('COLLECTING AMBIENT CONDITIONS from ambient_logger ' + ambient_details['Alias'])

        ambient_instance.open_comms()
        date_start, t_start, rh_start, p_start = ambient_instance.get_readings()
        ambient_instance.close_comms()

    else:
        log.error("Unrecognised ambient monitoring sensor")
        return False

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

        LabView_dll = LabEnviron64()
        t_data, rh_data = LabView_dll.get_t_rh_during(str(ambient_details['Alias']), ambient_details['Sensor'], ambient_pre['Start time'])
        # methods in labenviron_joe.py return t_data and rh_data as numpy ndarrays
        LabView_dll.shutdown_server32()

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


def analyse_weighing(root, url, se, run_id, bal_mode, timed=False, drift=None, EXCL=3, local_backup_folder=local_backup, **metadata):
    """Analyse a single complete circular weighing measurement using methods in circ_weigh_class

    Parameters
    ----------
    root : :class:`root`
        see msl.io for details
    url : path
        path to json file where analysis will be saved (along with measurement run data)
    se : :class:`str`
        scheme entry
    run_id : :class:`str`
        string in format run_1
    timed : :class:`bool`, optional
        if :data:`True`, uses times from weighings, otherwise assumes equally spaced in time
    drift : :class:`str`, optional
        set desired drift correction, e.g. 'quadratic drift'.  If :data:`None`, routine selects optimal drift correction
    EXCL : :class:`float`, optional
        criterion for excluding a single weighing within an automatic weighing sequence, default set arbitrarily at 3
    local_backup_folder : path
        path to local backup folder

    Returns
    -------
    :class:`root`
        the original root object with new analysis data
    (or None if weighing was not completed)
    """
    schemefolder = root['Circular Weighings'][se]
    weighdata = schemefolder['measurement_' + run_id]

    if not weighdata.metadata.get('Weighing complete'):
        return None

    log.info('CIRCULAR WEIGHING ANALYSIS for scheme entry '+ se + ' ' + run_id)

    weighing = CircWeigh(se)
    if timed:
        times = np.reshape(weighdata[:, :, 0], weighing.num_readings)
    else:
        times = []
    weighing.generate_design_matrices(times)

    if not drift:
        drift = weighing.determine_drift(weighdata[:, :, 1])  # allows program to select optimum drift correction
        log.info('Residual std dev. for each drift order:')
        for key, value in weighing.stdev.items():
            log.info(tab + key + ':\t' + str(value))
    else:
        weighing.determine_drift(weighdata[:, :, 1])
        log.info('Residual std dev. for '+drift+' correction:\n' + tab
                 + str(weighing.stdev[drift]))

    massunit = weighdata.metadata.get('Unit')
    log.info('Selected ' + drift + ' correction (in ' + massunit + ' per ' + weighing.trend + '):\n' + tab
             + str(weighing.drift_coeffs(drift)))

    analysis = weighing.item_diff(drift)

    log.info('Differences (in ' + massunit + '):')
    for key, value in weighing.grpdiffs.items():
        log.info(tab + key + ':\t' + value)

    # print(schemefolder.name + '/analysis_' + run_id)
    a = root.remove(schemefolder.name+'/analysis_'+run_id)

    weighanalysis = root.require_dataset(schemefolder.name+'/analysis_'+run_id,
                                                 data=analysis, shape=(weighing.num_wtgrps, 1))

    max_stdev_circweigh = weighdata.metadata.get('Max stdev from CircWeigh ('+MU_STR+'g)')

    analysis_meta = {
        'Analysis Timestamp': datetime.now().strftime('%d-%m-%Y %H:%M'),
        'Residual std devs': str(weighing.stdev),
        'Selected drift': drift,
        'Uses mmt times': timed,
        'Mass unit': massunit,
        'Drift unit': massunit + ' per ' + weighing.trend,
        'Acceptance met?': weighing.stdev[drift]*SUFFIX[massunit] < max_stdev_circweigh*SUFFIX['ug'],
    }

    if bal_mode == 'aw':
        excl = weighing.stdev[drift]*SUFFIX[massunit] > EXCL*max_stdev_circweigh*SUFFIX['ug']
    else:
        excl = not analysis_meta.get('Acceptance met?')
    analysis_meta['Exclude'] = excl

    for key, value in weighing.driftcoeffs.items():
        analysis_meta[key] = value

    if not sum(analysis['mass difference']) == 0:
        log.warning('Sum of mass differences is not zero. Analysis not accepted')
        analysis_meta['Acceptance met?'] = False

    flag = weighdata.metadata.get('Ambient OK?')
    if not flag:
        log.warning('Analysis not accepted due to ambient conditions during weighing')
        analysis_meta['Acceptance met?'] = False

    weighanalysis.add_metadata(**analysis_meta)

    try:
        root.save(file=url, mode='w', encoding='utf-8', ensure_ascii=False)
    except OSError:
        local_backup_file = os.path.join(local_backup_folder, url.split('\\')[-1])
        root.save(file=local_backup_file, mode='w', ensure_ascii=False)
        log.warning('Data saved to local backup file: ' + local_backup_file)

    log.info('Circular weighing analysis for '+se+', '+run_id+' complete\n')

    return weighanalysis


def analyse_old_weighing(cfg, filename, se, run_id):
    """Analyses a specific weighing run on file, with timed and drift parameters as specified in the configuration"""
    url = cfg.folder+"\\"+filename+'.json'
    root = check_for_existing_weighdata(cfg.folder, url, se)
    weighdata = root['Circular Weighings'][se]['measurement_' + run_id]
    bal_alias = weighdata.metadata.get('Balance')
    bal_mode = cfg.equipment[bal_alias].user_defined['weighing_mode']
    weighanalysis = analyse_weighing(root, url, se, run_id, bal_mode, cfg.timed, cfg.drift)

    return weighanalysis


def analyse_all_weighings_in_file(cfg, filename, se):
    """Analyses all weighings on file for a given scheme entry, with specified timed and drift parameters

    Parameters
    ----------
    cfg : :class:`Configuration`
        configuration instance (see mass_circular_weighing.Configuration)
    filename : :class:`str`
        e.g. client_nominal
    se : :class:`str`
        scheme entry, as per standard format e.g. "1 1s 0.5+0.5s"
    """
    url = cfg.folder + "\\" + filename + '.json'

    i = 1
    while True:
        try:
            run_id = 'run_' + str(i)
            root = check_for_existing_weighdata(cfg.folder, url, se)
            weighdata = root['Circular Weighings'][se]['measurement_' + run_id]
            bal_alias = weighdata.metadata.get('Balance')
            bal_mode = cfg.equipment[bal_alias].user_defined['weighing_mode']
            analyse_weighing(root, url, se, run_id, bal_mode, cfg.timed, cfg.drift)
            i += 1
        except KeyError:
            log.info('No more runs to analyse\n')
            break


def check_existing_runs(root, scheme_entry):
    """Counts the number of runs on file that are acceptable for use in the final mass calculation

    Parameters
    ----------
    root : :class:`root`
        containing the root as read from the relevant json file
    scheme_entry : str

    Returns
    -------
    tuple of integers
        good_runs is the number of acceptable weighings in the file
        run_1_no is the next unique run_id for subsequent circular weighings
    """
    i = 0
    good_runs = 0
    while True:
        run_id = 'run_' + str(i+1)
        try:
            existing_mmt = root['Circular Weighings'][scheme_entry]['measurement_' + run_id]
            # print(run_id, 'complete?', existing_mmt.metadata.get('Weighing complete'))
            if existing_mmt.metadata.get('Weighing complete'):
                try:
                    existing_analysis = root['Circular Weighings'][scheme_entry]['analysis_' + run_id]
                    ok = existing_analysis.metadata.get('Acceptance met?')
                    aw_bad = existing_analysis.metadata.get('Exclude?')
                    if ok:
                        # print('Weighing accepted')
                        good_runs += 1
                    elif not aw_bad:
                        # print('Weighing outside acceptance but allowed')
                        good_runs += 1
                except KeyError:
                    pass
                    # print('Weighing not accepted')
        except KeyError:
            break
        i += 1

    run_1_no = int(run_id.strip('run_'))

    return good_runs, run_1_no # returns integers for each

