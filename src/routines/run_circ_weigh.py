import os
from msl.io import JSONWriter, read
from src.routines.circ_weigh_class import CircWeigh
from src.constants import IN_DEGREES_C, MIN_T, MAX_T, MIN_RH, MAX_RH, MAX_T_CHANGE, MAX_RH_CHANGE, \
    SUFFIX, SQRT_F, EXCL, MU_STR
from time import perf_counter
from datetime import datetime
import numpy as np
from src.log import log


def check_for_existing_weighdata(folder, url, se):

    if os.path.isfile(url):
        existing_root = read(url, encoding='utf-8')
        if not os.path.exists(folder+"\\backups\\"):
            os.makedirs(folder+"\\backups\\")
        new_index = len(os.listdir(folder + "\\backups\\"))
        new_file = str(folder + "\\backups\\" + se + '_backup{}.json'.format(new_index))
        existing_root.is_read_only = False
        log.debug('Existing root is '+repr(existing_root))
        root = JSONWriter()
        root.set_root(existing_root)
        log.debug('Working root is '+repr(root))
        root.save(root=existing_root, url=new_file, mode='w', encoding='utf-8', ensure_ascii=False)

    else:
        if not os.path.exists(folder):
            os.makedirs(folder)
        print('Creating new file for weighing')
        root = JSONWriter()
        circularweighings = root.require_group('Circular Weighings')
        circularweighings.require_group(se)

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


def do_circ_weighing(bal, se, root, url, run_id, callback1=None, callback2=None, omega=None, **metadata):

    metadata['Mmt Timestamp'] = datetime.now().isoformat(sep=' ', timespec='minutes')
    metadata['Time unit'] = 'min'

    ambient_pre = check_ambient_pre(omega)
    if not ambient_pre:
        log.info('Measurement not started due to unsuitable ambient conditions')
        return False
    for key, value in ambient_pre.items():
        metadata[key] = value

    weighing = CircWeigh(se)
    positionstr = ''
    for i in range(weighing.num_wtgrps):
        positionstr = positionstr + 'Position '+ str(i + 1) + ': ' + weighing.wtgrps[i] + '\n'
        metadata['grp' + str(i + 1)] = weighing.wtgrps[i]

    log.info("\nBeginning circular weighing for scheme entry "+ se +' '+ run_id +
             '\nNumber of weight groups in weighing = '+ str(weighing.num_wtgrps) +
             '\nNumber of cycles = '+ str(weighing.num_cycles) +
             '\nWeight groups are positioned as follows:' +
             '\n' + positionstr.strip('\n'))

    data = np.empty(shape=(weighing.num_cycles, weighing.num_wtgrps, 2))
    weighdata = root['Circular Weighings'][se].require_dataset('measurement_' + run_id, data=data)
    weighdata.add_metadata(**metadata)

    # do circular weighing, allowing for keyboard interrupt:
    while not bal.want_abort:
        times = []
        t0 = 0
        for cycle in range(weighing.num_cycles):
            for pos in range(weighing.num_wtgrps):
                if callback1 is not None:
                    callback1(cycle+1, pos+1, weighing.num_cycles, weighing.num_wtgrps)
                mass = weighing.wtgrps[pos]
                bal.load_bal(mass, pos)
                reading = bal.get_mass_stable(mass)
                if callback2 is not None:
                    callback2(reading, str(metadata['Unit']))
                if not times:
                    time = 0
                    t0 = perf_counter()
                else:
                    time = np.round((perf_counter() - t0) / 60, 6)  # elapsed time in minutes
                times.append(time)
                weighdata[cycle, pos, :] = [time, reading]
                root.save(url=url, mode='w', ensure_ascii=False)
                bal.unload_bal(mass, pos)
        break

    while not bal.want_abort:
        ambient_post = check_ambient_post(omega, ambient_pre)
        for key, value in ambient_post.items():
            metadata[key] = value

        metadata['Weighing complete'] = True
        weighdata.add_metadata(**metadata)
        root.save(url=url, mode='w', ensure_ascii=False)

        log.debug('weighdata:\n'+str(weighdata[:, :, :]))

        return root

    log.info('Circular weighing sequence aborted')
    metadata['Weighing complete'] = False
    weighdata.add_metadata(**metadata)
    root.save(url=url, mode='w', ensure_ascii=False)

    return None


def check_ambient_pre(omega):
    """Check ambient conditions meet quality criteria for commencing weighing

    Parameters
    ----------
    omega : OMEGA instance

    Returns
    -------
    ambient_pre : dict
        dict of ambient conditions at start of weighing: {'T_pre'+IN_DEGREES_C: float and 'RH_pre (%)': float}
        If OMEGA instance unavailable, returns 20+IN_DEGREES_C and 50%.
    """

    try:
        ambient = omega.get_t_rh()
    except ConnectionAbortedError:
        try:
            ambient = omega.get_t_rh()
        except ConnectionAbortedError:
            log.error('Omega logger is not present or could not be read')
            ambient_pre = {'T_pre' + IN_DEGREES_C: 20.0, 'RH_pre (%)': 50.0}
            return ambient_pre

    ambient_pre = {'T_pre'+IN_DEGREES_C: ambient['T'+IN_DEGREES_C], 'RH_pre (%)': ambient['RH (%)']}
    log.info('Ambient conditions:\n'+
             'Temperature'+IN_DEGREES_C+': '+str(ambient['T'+IN_DEGREES_C])+
             '; Humidity (%): '+str(ambient['RH (%)']))

    if MIN_T < ambient_pre['T_pre'+IN_DEGREES_C] < MAX_T:
        log.info('Ambient temperature OK for weighing')
    else:
        log.warning('Ambient temperature does not meet limits')
        return False

    if MIN_RH < ambient_pre['RH_pre (%)'] < MAX_RH:
        log.info('Ambient humidity OK for weighing')
    else:
        log.warning('Ambient humidity does not meet limits')
        return False

    return ambient_pre


def check_ambient_post(omega, ambient_pre):
    """Check ambient conditions met quality criteria during weighing

    Parameters
    ----------
    omega : OMEGA instance
    ambient_pre : dict
        dict of ambient conditions at start of weighing: {'T_pre'+IN_DEGREES_C: float and 'RH_pre (%)': float}

    Returns
    -------
    ambient_post : dict
        dict of ambient conditions at end of weighing, and evaluation of overall conditions during measurement.
        dict has key-value pairs {'T_post'+IN_DEGREES_C: float, 'RH_post (%)': float, 'Ambient OK?': bool}
    """

    try:
        ambient = omega.get_t_rh()
        ambient_post = {'T_post'+IN_DEGREES_C: ambient['T'+IN_DEGREES_C], 'RH_post (%)': ambient['RH (%)']}
        log.info('Ambient conditions:\n'+str(ambient_post))
    except:
        log.error('Omega logger is not present or could not be read')
        ambient_post = {'T_post'+IN_DEGREES_C: 20.0, 'RH_post (%)': 50.0}



    if (ambient_pre['T_pre'+IN_DEGREES_C] - ambient_post['T_post'+IN_DEGREES_C]) ** 2 > MAX_T_CHANGE**2:
        ambient_post['Ambient OK?'] = False
        log.warning('Ambient temperature change during weighing exceeds quality criteria')
    elif (ambient_pre['RH_pre (%)'] - ambient_post['RH_post (%)']) ** 2 > MAX_RH_CHANGE**2:
        ambient_post['Ambient OK?'] = False
        log.warning('Ambient humidity change during weighing exceeds quality criteria')
    else:
        log.info('Ambient conditions OK during weighing')
        ambient_post['Ambient OK?'] = True

    return ambient_post


def analyse_weighing(root, url, se, run_id, timed=True, drift=None):
    schemefolder = root['Circular Weighings'][se]
    weighdata = schemefolder['measurement_' + run_id]

    weighing = CircWeigh(se)
    if timed:
        times = np.reshape(weighdata[:, :, 0], weighing.num_readings)
        weighing.generate_design_matrices(times)
    else:
        weighing.generate_design_matrices(times=[])

    d = weighing.determine_drift(weighdata[:, :, 1])  # allows program to select optimum drift correction

    if not drift:
        drift = d

    log.info('Residual std dev. for each drift order:\n'
             + str(weighing.stdev))

    massunit = weighdata.metadata.get('Unit')
    log.info('Selected ' + drift + ' correction (in ' + massunit + ' per reading):\n'
             + str(weighing.drift_coeffs(drift)))

    analysis = weighing.item_diff(drift)

    log.info('Differences (in ' + massunit + '):\n'
             + str(weighing.grpdiffs))

    # save analysis to json file
    # (note that any previous analysis for the same run is not saved in the new json file)
    weighanalysis = root.require_dataset(schemefolder.name+'/analysis_'+run_id,
                                                 data=analysis, shape=(weighing.num_wtgrps, 1))

    max_stdev_circweigh = weighdata.metadata.get('Max stdev from CircWeigh ('+MU_STR+'g)')

    analysis_meta = {
        'Analysis Timestamp': datetime.now().isoformat(sep=' ', timespec='minutes'),
        'Residual std devs': str(weighing.stdev),
        'Selected drift': drift,
        'Mass unit': massunit,
        'Drift unit': massunit + ' per ' + weighing.trend,
        'Acceptance met?': weighing.stdev[drift]*SUFFIX[massunit] < SQRT_F*max_stdev_circweigh*SUFFIX['ug'],
        'Exclude?': weighing.stdev[drift]*SUFFIX[massunit] > EXCL*max_stdev_circweigh*SUFFIX['ug']
    }

    for key, value in weighing.driftcoeffs.items():
        analysis_meta[key] = value

    if not sum(analysis['mass difference']) == 0:
        log.warning('Sum of mass differences is not zero. Analysis not accepted')
        analysis_meta['Acceptance met?'] = False

    flag = weighdata.metadata.get('Ambient OK?')
    if not flag:
        log.warning('Change in ambient conditions during weighing exceeded quality criteria')
        analysis_meta['Acceptance met?'] = False

    weighanalysis.add_metadata(**analysis_meta)

    root.save(url=url, mode='w', encoding='utf-8', ensure_ascii=False)

    log.info('Circular weighing complete')

    return weighanalysis


def analyse_old_weighing(folder, filename, se, run_id, timed, drift):

    url = folder+"\\"+filename+'.json'
    root = check_for_existing_weighdata(folder, url, se)
    weighanalysis = analyse_weighing(root, url, se, run_id, timed, drift)

    return weighanalysis


def analyse_all_weighings_in_file(folder, filename, se, timed, drift):

    url = folder + "\\" + filename + '.json'
    root = check_for_existing_weighdata(folder, url, se)
    i = 1
    while True:
        try:
            run_id = 'run_' + str(i)
            analyse_weighing(root, url, se, run_id, timed, drift)
            i += 1
        except KeyError:
            log.info('No more runs to analyse')
            break
