import os
from msl.io import JSONWriter, read
from src.routines.circ_weigh_class import CircWeigh
from time import perf_counter
from datetime import datetime
import numpy as np
from ..log import log


def check_for_existing_weighdata(folder, filename, se, run_id):

    url = folder+"\\"+filename+'.json'

    if os.path.isfile(url):
        existing_root = read(url)
        if not os.path.exists(folder+"\\backups\\"):
            os.makedirs(folder+"\\backups\\")
        new_index = len(os.listdir(folder + "\\backups\\"))
        new_file = str(folder + "\\backups\\" + se + '_' + run_id + '_backup{}.json'.format(new_index))
        existing_root.is_read_only = False
        print(existing_root)
        root = JSONWriter()
        root.set_root(existing_root)
        print(root)
        root.save(root=existing_root, url=new_file, mode='w')

    else:
        if not os.path.exists(folder):
            os.makedirs(folder)
        print('Creating new file for weighing')
        root = JSONWriter()
        circularweighings = root.require_group('Circular Weighings')
        circularweighings.require_group(se)

    return root  # add here also the max run number


def do_weighing(bal, se, root, url, run_id, **metadata):

    ambient_pre = check_ambient_pre()
    for key, value in ambient_pre.items():
        metadata[key] = value

    print("Beginning circular weighing for scheme entry", se)
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

    return metadata['Ambient OK?']


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


def analyse_weighing(folder, filename, se, run_id, timed=True, drift=None):
    url = folder+"\\"+filename+'.json'
    root = check_for_existing_weighdata(folder, filename, se, run_id)
    schemefolder = root['Circular Weighings'][se]
    weighdata = schemefolder['measurement_' + run_id]

    flag = weighdata.metadata.get('Ambient OK?')
    if not flag:
        log.warning('Change in ambient conditions during weighing exceeded quality criteria')
        return

    weighing = CircWeigh(se)
    if timed:
        times=np.reshape(weighdata[:, :, 0], weighing.num_readings)
        weighing.generate_design_matrices(times)
    else:
        weighing.generate_design_matrices(times=[])

    d = weighing.determine_drift(weighdata[:, :, 1])  # allows program to select optimum drift correction

    if not drift:
        drift = d

    print()
    print('Residual std dev. for each drift order:')
    print(weighing.stdev)

    print()
    massunit = weighdata.metadata.get('Unit')
    print('Selected drift correction is', drift, '(in', massunit, 'per reading):')
    print(weighing.drift_coeffs(drift))

    analysis = weighing.item_diff(drift)

    print()
    print('Differences (in', massunit + '):')
    print(weighing.grpdiffs)

    # save analysis to json file
    # TODO: probably want to overwrite? or save with new identifier if different?
    weighanalysis = schemefolder.require_dataset(schemefolder.name+'/analysis_'+run_id,
                                                 data=analysis, shape=(weighing.num_wtgrps, 1))

    max_stdev_circweigh = weighdata.metadata.get('Max stdev from CircWeigh (ug)')
    analysis_meta = {
        'Analysis Timestamp': datetime.now().isoformat(sep=' ', timespec='minutes'),
        'Residual std devs': str(weighing.stdev),  # \u03C3 for sigma sign
        'Selected drift': drift,
        'Mass unit': massunit,
        'Drift unit': massunit + ' per ' + weighing.trend,
        'Acceptance met?': weighing.stdev[drift] < max_stdev_circweigh,  # TODO - or 1.4 times this?
    }

    for key, value in weighing.driftcoeffs.items():
        analysis_meta[key] = value

    weighanalysis.add_metadata(**analysis_meta)

    root.save(url=url, mode='w')

    print()
    print('Circular weighing complete')

    return weighanalysis
