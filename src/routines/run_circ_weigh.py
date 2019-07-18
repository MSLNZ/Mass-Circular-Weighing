import os
from msl.io import JSONWriter, read
from src.routines.circ_weigh_class import CircWeigh
from time import perf_counter
from datetime import datetime
import numpy as np
from ..log import log

MU_STRING = 'µ'

def check_for_existing_weighdata(folder, url, se):

    if os.path.isfile(url):
        existing_root = read(url)
        if not os.path.exists(folder+"\\backups\\"):
            os.makedirs(folder+"\\backups\\")
        new_index = len(os.listdir(folder + "\\backups\\"))
        new_file = str(folder + "\\backups\\" + se + '_backup{}.json'.format(new_index))
        existing_root.is_read_only = False
        log.debug('Existing root is '+repr(existing_root))
        root = JSONWriter()
        root.set_root(existing_root)
        log.debug('Working root is '+repr(root))
        root.save(root=existing_root, url=new_file, mode='w')

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


def do_circ_weighing(bal, se, root, url, run_id, **metadata):

    ambient_pre = check_ambient_pre()
    for key, value in ambient_pre.items():
        metadata[key] = value

    print("Beginning circular weighing for scheme entry", se, run_id)
    weighing = CircWeigh(se)
    print('Number of weight groups in weighing =', weighing.num_wtgrps)
    print('Number of cycles =', weighing.num_cycles)
    print('Weight groups are positioned as follows:')
    for i in range(weighing.num_wtgrps):
        print('Position', str(i + 1) + ':', weighing.wtgrps[i])
        metadata['grp' + str(i + 1)] = weighing.wtgrps[i]

    data = np.empty(shape=(weighing.num_cycles, weighing.num_wtgrps, 2))
    weighdata = root['Circular Weighings'][se].require_dataset('measurement_' + run_id, data=data)
    weighdata.add_metadata(**metadata)

    # do circular weighing:
    times = []
    t0 = 0
    for cycle in range(weighing.num_cycles):
        for pos in range(weighing.num_wtgrps):
            mass = weighing.wtgrps[pos]
            bal.load_bal(mass)
            reading = bal.get_mass_stable()
            if not times:
                time = 0
                t0 = perf_counter()
            else:
                time = np.round((perf_counter() - t0) / 60, 6)  # elapsed time in minutes
            times.append(time)
            weighdata[cycle, pos, :] = [time, reading]
            root.save(url=url, mode='w')
            bal.unload_bal(mass)

    #metadata['Timestamps'] = np.round(times, 3)
    metadata['Time unit'] = 'min'

    metadata['Mmt Timestamp'] = datetime.now().isoformat(sep=' ', timespec='minutes')

    ambient_post = check_ambient_post(ambient_pre)
    for key, value in ambient_post.items():
        metadata[key] = value

    print(metadata)
    weighdata.add_metadata(**metadata)
    root.save(url=url, mode='w')

    print(weighdata[:, :, :])

    return root


def check_ambient_pre():
    # check ambient conditions meet quality criteria for commencing weighing
    ambient_pre = {'T_pre (deg C)': 20.0, 'RH_pre (%)': 50.0}  # \xb0 is degree in unicode
    # TODO: link this to Omega logger

    if 18.1 < ambient_pre['T_pre (deg C)'] < 21.9:
        log.info('Ambient temperature OK for weighing')
    else:
        raise ValueError('Ambient temperature does not meet limits')

    if 33 < ambient_pre['RH_pre (%)'] < 67:
        log.info('Ambient humidity OK for weighing')
    else:
        raise ValueError('Ambient humidity does not meet limits')

    return ambient_pre


def check_ambient_post(ambient_pre):
    # check ambient conditions meet quality criteria during weighing
    ambient_post = {'T_post (deg C)': 20.3, 'RH_post (%)': 44.9}
    # TODO: get from Omega logger

    if (ambient_pre['T_pre (deg C)'] - ambient_post['T_post (deg C)']) ** 2 > 0.25:
        ambient_post['Ambient OK?'] = False
        log.warning('Ambient temperature change during weighing exceeds quality criteria')
    elif (ambient_pre['RH_pre (%)'] - ambient_post['RH_post (%)']) ** 2 > 225:
        ambient_post['Ambient OK?'] = False
        log.warning('Ambient humidity change during weighing exceeds quality criteria')
    else:
        log.info('Ambient conditions OK during weighing')
        ambient_post['Ambient OK?'] = True

    return ambient_post


def analyse_weighing(root, url, se, run_id, timed=True, drift=None):
    schemefolder = root['Circular Weighings'][se]
    weighdata = schemefolder['measurement_' + run_id]

    flag = weighdata.metadata.get('Ambient OK?')
    if not flag:
        log.warning('Change in ambient conditions during weighing exceeded quality criteria')
        return None

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

    suffix = {'ug': 1e-6, 'mg': 1e-3, 'g': 1, 'kg': 1e3}
    max_stdev_circweigh = weighdata.metadata.get('Max stdev from CircWeigh (ug)')
    analysis_meta = {
        'Analysis Timestamp': datetime.now().isoformat(sep=' ', timespec='minutes'),
        'Residual std devs, \u03C3': str(weighing.stdev),  # \u03C3 for sigma sign
        'Selected drift': drift,
        'Mass unit, µ': massunit,
        'Drift unit': massunit + ' per ' + weighing.trend,
        'Acceptance met?': weighing.stdev[drift]*suffix[massunit] < 1.4*max_stdev_circweigh*suffix['ug'],
    }


    for key, value in weighing.driftcoeffs.items():
        analysis_meta[key] = value

    if not sum(analysis['mass difference']) == 0:
        log.warning('Sum of mass differences is not zero. Analysis not accepted')
        analysis_meta['Acceptance met?'] = False

    weighanalysis.add_metadata(**analysis_meta)

    root.save(url=url, mode='w', encoding='utf-8')

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
            print('No more runs to analyse')
            break
