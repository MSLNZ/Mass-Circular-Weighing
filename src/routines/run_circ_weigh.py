import os
from msl.io import JSONWriter, read
from src.routines.circ_weigh_class import CircWeigh
import src.cv as cv
from src.constants import IN_DEGREES_C, SUFFIX, MU_STR, local_backup
from src.equip.labenviron_dll import LabEnviron64
from time import perf_counter
from datetime import datetime
import numpy as np
from src.log import log

dll = LabEnviron64()

tab = '  '

def check_for_existing_weighdata(url, se):

    if os.path.isfile(url):
        existing_root = read(url, encoding='utf-8')
        if not os.path.exists(cv.folder.get()+"\\backups\\"):
            os.makedirs(cv.folder.get()+"\\backups\\")
        new_index = len(os.listdir(cv.folder.get()+ "\\backups\\"))
        new_file = str(cv.folder.get()+ "\\backups\\" + se + '_backup{}.json'.format(new_index))
        existing_root.is_read_only = False
        log.debug('Existing root is '+repr(existing_root))
        root = JSONWriter()
        root.set_root(existing_root)
        log.debug('Working root is '+repr(root))
        root.save(root=existing_root, file=new_file, mode='w', encoding='utf-8', ensure_ascii=False)

    else:
        if not os.path.exists(cv.folder.get()):
            os.makedirs(cv.folder.get())
        print('Creating new file for weighing')
        root = JSONWriter()

    root.require_group('Circular Weighings')
    root['Circular Weighings'].require_group(se)

    return root


def get_next_run_id(root, scheme_entry):
    i = 1
    while True:
        run_id = 'run_' + str(i)
        try:
            existing_weighing = root['Circular Weighings'][scheme_entry]['measurement_' + run_id]
            i += 1
        except KeyError:
            break

    return run_id


def do_circ_weighing(bal, se, root, url, run_id, callback1=None, callback2=None, omega=None,
                     local_backup_folder=local_backup, **metadata):

    local_backup_file = os.path.join(local_backup_folder, url.split('\\')[-1])

    metadata['Mmt Timestamp'] = datetime.now().strftime('%d-%m-%Y %H:%M')
    metadata['Time unit'] = 'min'
    metadata['Ambient monitoring'] = omega

    ambient_pre = check_ambient_pre(omega)
    if not ambient_pre:
        log.info('Measurement not started due to unsuitable ambient conditions')
        return False

    weighing = CircWeigh(se)
    # assign positions to weight groups
    if bal.mode == 'aw':
        print('Please make pop-up to assign positions to weight groups')
        return None
    else:
        positions = range(1, weighing.num_wtgrps + 1, 1)

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
                bal.load_bal(mass, positions[i])
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
        ambient_post = check_ambient_post(omega, ambient_pre)
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
        metadata['Weighing complete'] = False
        weighdata.add_metadata(**metadata)
        try:
            root.save(file=url, mode='w', ensure_ascii=False)
        except OSError:
            root.save(file=local_backup_file, mode='w', ensure_ascii=False)
            log.warning('Data saved to local backup file: ' + local_backup_file)

    return None


def check_ambient_pre(omega):
    """Check ambient conditions meet quality criteria for commencing weighing

    Parameters
    ----------
    omega : :class:`dict`
        dict of OMEGA alias and limits on ambient conditions

    Returns
    -------
    ambient_pre : :class:`dict`
        dict of ambient conditions at start of weighing:
        {'Start time': datetime object, 'T_pre'+IN_DEGREES_C: float and 'RH_pre (%)': float}
    """
    log.info('COLLECTING AMBIENT CONDITIONS from omega '+omega['Inst'] + ' sensor ' + str(omega['Sensor']))

    date_start, t_start, rh_start = dll.get_t_rh_now(str(omega['Inst']), omega['Sensor'])

    if not t_start:
        log.warning('Missing initial ambient temperature value')
        return False
    if not rh_start:
        log.warning('Missing initial ambient humidity value')
        return False

    ambient_pre = {'Start time': date_start, 'T_pre'+IN_DEGREES_C: np.round(t_start, 4), 'RH_pre (%)': np.round(rh_start, 4), }
    log.info('Ambient conditions:' +
             'Temperature'+IN_DEGREES_C+': '+str(ambient_pre['T_pre'+IN_DEGREES_C])+
             '; Humidity (%): '+str(ambient_pre['RH_pre (%)']))

    if omega['MIN_T'] < ambient_pre['T_pre'+IN_DEGREES_C] < omega['MAX_T']:
        log.info('Ambient temperature OK for weighing')
    else:
        log.warning('Ambient temperature does not meet limits')
        return False

    if omega['MIN_RH'] < ambient_pre['RH_pre (%)'] < omega['MAX_RH']:
        log.info('Ambient humidity OK for weighing')
    else:
        log.warning('Ambient humidity does not meet limits')
        return False

    return ambient_pre


def check_ambient_post(omega, ambient_pre):
    """Check ambient conditions met quality criteria during weighing

    Parameters
    ----------
    omega : :class:`dict`
        dict of OMEGA alias and limits on ambient conditions
    ambient_pre : :class:`dict`
        dict of ambient conditions at start of weighing:
        {'Start time': datetime object, 'T_pre'+IN_DEGREES_C: float and 'RH_pre (%)': float}

    Returns
    -------
    ambient_post : :class:`dict`
        dict of ambient conditions at end of weighing, and evaluation of overall conditions during measurement.
        dict has key-value pairs {'T_post'+IN_DEGREES_C: list of floats, 'RH_post (%)': list of floats, 'Ambient OK?': bool}
    """
    log.info('COLLECTING AMBIENT CONDITIONS from omega '+omega['Inst'] + ' sensor ' + str(omega['Sensor']))

    t_data, rh_data = dll.get_t_rh_during(str(omega['Inst']), omega['Sensor'], ambient_pre['Start time'])

    ambient_post = {}
    if not t_data[0]:
        ambient_post['T_pre'+IN_DEGREES_C] = ambient_pre['T_pre'+IN_DEGREES_C]
        log.warning('Ambient temperature change during weighing not recorded')
        ambient_post = {'Ambient OK?': None}
    else:
        t_data.append(ambient_pre['T_pre'+IN_DEGREES_C])
        ambient_post['T' + IN_DEGREES_C] = str(round(min(t_data), 3)) + ' to ' + str(round(max(t_data), 3))

    if not rh_data[0]:
        ambient_post['RH_pre (%)'] = ambient_pre['RH_pre (%)']
        log.warning('Ambient humidity change during weighing not recorded')
        ambient_post = {'Ambient OK?': None}
    else:
        rh_data.append(ambient_pre['RH_pre (%)'])
        ambient_post['RH (%)'] = str(round(min(rh_data), 1)) + ' to ' + str(round(max(rh_data), 1))

    if t_data and rh_data:
        if (max(t_data) - min(t_data)) ** 2 > omega['MAX_T_CHANGE']**2:
            ambient_post['Ambient OK?'] = False
            log.warning('Ambient temperature change during weighing exceeds quality criteria')
        elif (max(rh_data) - min(rh_data)) ** 2 > omega['MAX_RH_CHANGE']**2:
            ambient_post['Ambient OK?'] = False
            log.warning('Ambient humidity change during weighing exceeds quality criteria')
        else:
            log.info('Ambient conditions OK during weighing')
            ambient_post['Ambient OK?'] = True

    log.info('Ambient conditions:\n' + str(ambient_post))

    return ambient_post

def analyse_weighing(root, url, se, run_id, bal_mode, timed=False, drift=None, EXCL=3, local_backup_folder=local_backup, **metadata):
    """Analyse a single circular weighing measurement using methods in circ_weigh_class

    Parameters
    ----------
    root : :class:`root`
        see msl.io for details
    url : path
        path to json file containing raw data
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
        drift = weighing.determine_drift(weighdata[:, :, 1])  # allows program to select optimum drift correctiond
        log.info('Residual std dev. for each drift order:')
        for key, value in weighing.stdev.items():
            log.info(tab + key + ':\t' + str(value))
    else:
        weighing.expected_vals_drift(weighdata[:, :, 1], drift)
        log.info('Residual std dev. for '+drift+' correction:\n' + tab
                 + str(weighing.stdev))

    massunit = weighdata.metadata.get('Unit')
    log.info('Selected ' + drift + ' correction (in ' + massunit + ' per ' + weighing.trend + '):\n' + tab
             + str(weighing.drift_coeffs(drift)))

    analysis = weighing.item_diff(drift)

    log.info('Differences (in ' + massunit + '):')
    for key, value in weighing.grpdiffs.items():
        log.info(tab + key + ':\t' + value)

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
    except:
        local_backup_file = os.path.join(local_backup_folder, url.split('\\')[-1])
        root.save(file=local_backup_file, mode='w', ensure_ascii=False)
        log.warning('Data saved to local backup file: ' + local_backup_file)

    log.info('Circular weighing analysis for '+se+', '+run_id+' complete\n')

    return weighanalysis


def analyse_old_weighing(filename, se, run_id, bal_mode, timed, drift):
    """Analyses a specific weighing run on file, with specified timed and drift parameters

    Parameters
    ----------
    filename
    se
    run_id
    bal_mode : str
    timed
    drift

    Returns
    -------

    """

    url = cv.folder.get()+"\\"+filename+'.json'
    root = check_for_existing_weighdata(url, se)
    weighanalysis = analyse_weighing(root, url, se, run_id, bal_mode, timed, drift)

    return weighanalysis


def analyse_all_weighings_in_file(filename, se, bal_mode, timed, drift):
    """Analyses all weighings on file for a given scheme entry, with specified timed and drift parameters

    Parameters
    ----------
    filename : str
    se : str
    bal_mode : str
    timed : bool
    drift : str or :None:

    Returns
    -------

    """

    url = cv.folder.get()+ "\\" + filename + '.json'
    root = check_for_existing_weighdata(url, se)
    i = 1
    while True:
        try:
            run_id = 'run_' + str(i)
            analyse_weighing(root, url, se, run_id, bal_mode, timed, drift)
            i += 1
        except KeyError:
            log.info('No more runs to analyse')
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
                    aw_ok = existing_analysis.metadata.get('Exclude?')
                    if ok:
                        # print('Weighing accepted')
                        good_runs += 1
                    elif not aw_ok:
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

