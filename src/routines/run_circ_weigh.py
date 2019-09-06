import os
from msl.io import JSONWriter, read
from src.routines.circ_weigh_class import CircWeigh
from src.constants import IN_DEGREES_C, SUFFIX, MU_STR
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
    omega : :class:`dict`
        dict of OMEGA instance and limits on ambient conditions

    Returns
    -------
    ambient_pre : :class:`dict`
        dict of ambient conditions at start of weighing: {'T_pre'+IN_DEGREES_C: float and 'RH_pre (%)': float}
        If OMEGA instance unavailable, returns 20+IN_DEGREES_C and 50%.
    """

    try:
        ambient = omega['Inst'].get_t_rh()
    except ConnectionAbortedError:
        try:
            ambient = omega['Inst'].get_t_rh()
        except ConnectionAbortedError:
            log.error('Omega logger is not present or could not be read')
            #ambient_pre = {'T_pre' + IN_DEGREES_C: 20.0, 'RH_pre (%)': 50.0}
            return False

    ambient_pre = {'T_pre'+IN_DEGREES_C: ambient['T'+IN_DEGREES_C], 'RH_pre (%)': ambient['RH (%)']}
    log.info('Ambient conditions:\n'+
             'Temperature'+IN_DEGREES_C+': '+str(ambient['T'+IN_DEGREES_C])+
             '; Humidity (%): '+str(ambient['RH (%)']))

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
        dict of OMEGA instance and limits on ambient conditions
    ambient_pre : :class:`dict`
        dict of ambient conditions at start of weighing: {'T_pre'+IN_DEGREES_C: float and 'RH_pre (%)': float}

    Returns
    -------
    ambient_post : :class:`dict`
        dict of ambient conditions at end of weighing, and evaluation of overall conditions during measurement.
        dict has key-value pairs {'T_post'+IN_DEGREES_C: float, 'RH_post (%)': float, 'Ambient OK?': bool}
    """

    try:
        ambient = omega['Inst'].get_t_rh()
        ambient_post = {'T_post'+IN_DEGREES_C: ambient['T'+IN_DEGREES_C], 'RH_post (%)': ambient['RH (%)']}
        log.info('Ambient conditions:\n'+str(ambient_post))

        if (ambient_pre['T_pre'+IN_DEGREES_C] - ambient_post['T_post'+IN_DEGREES_C]) ** 2 > omega['MAX_T_CHANGE']**2:
            ambient_post['Ambient OK?'] = False
            log.warning('Ambient temperature change during weighing exceeds quality criteria')
        elif (ambient_pre['RH_pre (%)'] - ambient_post['RH_post (%)']) ** 2 > omega['MAX_RH_CHANGE']**2:
            ambient_post['Ambient OK?'] = False
            log.warning('Ambient humidity change during weighing exceeds quality criteria')
        else:
            log.info('Ambient conditions OK during weighing')
            ambient_post['Ambient OK?'] = True
    except:
        log.error('Omega logger is not present or could not be read')
        ambient_post = {'T_post'+IN_DEGREES_C: None, 'RH_post (%)': None, 'Ambient OK?': None}

    return ambient_post


def analyse_weighing(root, url, se, run_id, timed=False, drift=None, SQRT_F=1.4, EXCL=3):
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
    SQRT_F : :class:`float`, optional
        criterion for accepting single weighing analysis, default set to 1.4
    EXCL : :class:`float`, optional
        criterion for excluding a single weighing within an automatic weighing sequence, default set arbitrarily at 3

    Returns
    -------
    :class:`root`
        the original root object with new analysis data
    """
    schemefolder = root['Circular Weighings'][se]
    weighdata = schemefolder['measurement_' + run_id]

    if not weighdata.metadata.get('Weighing complete'):
        return None

    weighing = CircWeigh(se)
    if timed:
        times = np.reshape(weighdata[:, :, 0], weighing.num_readings)
    else:
        times=[]
    weighing.generate_design_matrices(times)

    if not drift:
        drift = weighing.determine_drift(weighdata[:, :, 1])  # allows program to select optimum drift correctiond
        log.info('Residual std dev. for each drift order:\n'
                 + str(weighing.stdev))
    else:
        weighing.expected_vals_drift(weighdata[:, :, 1], drift)
        log.info('Residual std dev. for '+drift+' correction:\n'
                 + str(weighing.stdev))

    massunit = weighdata.metadata.get('Unit')
    log.info('Selected ' + drift + ' correction (in ' + massunit + ' per reading):\n'
             + str(weighing.drift_coeffs(drift)))

    analysis = weighing.item_diff(drift)

    log.info('Differences (in ' + massunit + '):\n'
             + str(weighing.grpdiffs))

    # save new analysis in json file
    print(id(schemefolder), id(root[schemefolder.name]))
    print(root.tree())
    #for k, v in root.items():
    #    print(k, v)
    #print(schemefolder.name+'/analysis_'+run_id)
    a = root.remove(schemefolder.name+'/analysis_'+run_id)
    #schemefolder.remove('analysis_'+run_id)
    print(id(schemefolder), id(root[schemefolder.name]))
    print(root.tree())
    #print('removed', a)
    #for k, v in root.items():
    #    print(k, v)
    print(schemefolder.name+'/analysis_'+run_id)
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
        log.warning('Change in ambient conditions during weighing may have exceeded quality criteria')
        analysis_meta['Acceptance met?'] = False

    weighanalysis.add_metadata(**analysis_meta)

    root.save(url=url, mode='w', encoding='utf-8', ensure_ascii=False)

    log.info('Circular weighing analysis for '+se+', '+run_id+' complete')

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


def check_existing_runs(root, scheme_entry):
    i = 0
    good_runs = 0
    while True:
        run_id = 'run_' + str(i+1)
        try:
            existing_mmt = root['Circular Weighings'][scheme_entry]['measurement_' + run_id]
            print(run_id, 'complete?', existing_mmt.metadata.get('Weighing complete'))
            if existing_mmt.metadata.get('Weighing complete'):
                try:
                    existing_analysis = root['Circular Weighings'][scheme_entry]['analysis_' + run_id]
                    ok = existing_analysis.metadata.get('Acceptance met?')
                    if ok:
                        print('good good')
                        good_runs += 1
                    elif not existing_analysis.metadata.get['Exclude?']:
                        print('outside acceptance but allowed')
                        good_runs += 1
                except:
                    print('Weighing not accepted')
        except KeyError:
            break
        i += 1

    run_1_no = int(run_id.strip('run_'))

    return good_runs, run_1_no # returns integers for each

