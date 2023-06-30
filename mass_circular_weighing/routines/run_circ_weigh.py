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
from ..constants import SUFFIX, MU_STR, local_backup
from ..equip import check_ambient_pre, check_ambient_post
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
        back_up_folder = os.path.join(folder, "backups")
        log.debug(back_up_folder)
        if not os.path.exists(back_up_folder):
            os.makedirs(back_up_folder)
        new_index = len(os.listdir(back_up_folder))  # counts number of files in backup folder
        new_file = os.path.join(back_up_folder, se + '_backup{}.json'.format(new_index))
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


# check_bal_initialised is called by the gui's weighing window
def check_bal_initialised(bal, wtgrps):
    if 'aw' in bal.mode:
        # use the class method within the AWBalCarousel and AWBalLinear classes
        # to check that the balance has been initialised correctly
        positions = bal.initialise_balance(wtgrps)
        log.debug(f'Positions in check_bal_initialised are {positions}')
        if positions is None:  # consequence of exit from initialise_balance for any number of reasons
            log.error("Balance initialisation was not completed")
            return None
    else:
        bal._positions = range(1, len(wtgrps) + 1)
        bal.adjust_scale_if_needed()

    return bal.positions


# do_circ_weighing is called by the gui's weighing window
def do_circ_weighing(bal, se, root, url, run_id, callback1=None, callback2=None,
                     local_backup_folder=local_backup, **metadata):
    """Routine to run a circular weighing by collecting data from a balance.
    This routine currently requires a Vaisala or an OMEGA logger to be specified in the registers
    for monitoring of the ambient conditions

    Parameters
    ----------
    bal : :class:`Balance`
        balance instance, initialised using mass_circular_weighing.configuration using a balance alias.
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
    metadata['Program Version'] = __version__
    timestamp = datetime.now()
    metadata['Mmt Timestamp'] = timestamp.strftime('%d-%m-%Y %H:%M:%S')
    metadata['Time unit'] = 'min'
    metadata['Ambient monitoring'] = bal.ambient_details
    metadata['Weighing complete'] = False

    weighing = CircWeigh(se)
    # here we assume that balance initialisation has been completed successfully
    positions = bal.positions

    positionstr = ''
    positiondict = {}
    for i in range(weighing.num_wtgrps):
        positionstr = positionstr + tab + 'Position ' + str(positions[i]) + ': ' + weighing.wtgrps[i] + '\n'
        positiondict['Position ' + str(positions[i])] = weighing.wtgrps[i]
    metadata["Weight group loading order"] = positiondict

    log.info("BEGINNING CIRCULAR WEIGHING for scheme entry "+ se + ' ' + run_id +
             '\nNumber of weight groups in weighing = '+ str(weighing.num_wtgrps) +
             '\nNumber of cycles = '+ str(weighing.num_cycles) +
             '\nWeight groups are positioned as follows:' +
             '\n' + positionstr.strip('\n'))

    log.info(f"Weighing starting at {metadata['Mmt Timestamp']}")

    ambient_pre = check_ambient_pre(bal.ambient_instance, bal.ambient_details, bal.mode)
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
                    network_ok = save_data(root, url, local_backup_folder, run_id, timestamp)
                    if not network_ok:
                        metadata['Network issues'] = True
                bal.unload_bal(mass, positions[i])
        break

    while not bal.want_abort:
        ambient_post = check_ambient_post(ambient_pre, bal.ambient_instance, bal.ambient_details, bal.mode)
        for key, value in ambient_post.items():
            metadata[key] = value

        metadata['Weighing complete'] = True
        end_time = datetime.now()
        metadata['Mmt end time'] = end_time.strftime('%d-%m-%Y %H:%M:%S')
        log.info(f"Weighing completed at {metadata['Mmt end time']}")
        elapsed_duration(end_time - timestamp)  # reports weighing duration to log window

        weighdata.add_metadata(**metadata)
        ok = save_data(root, url, local_backup_folder, run_id, timestamp)
        if not ok:
            log.debug('weighdata:\n' + str(weighdata[:, :, :]))

        return root

    log.info('Circular weighing sequence aborted')
    if reading:
        weighdata.add_metadata(**metadata)
        ok = save_data(root, url, local_backup_folder, run_id, timestamp)
        if not ok:
            log.debug('weighdata:\n' + str(weighdata[:, :, :]))

    return None


def save_data(root, url, local_backup_folder, run_id, timestamp):
    """Saves data to local drive and attempts to also save to network drive"""
    local_folder = os.path.join(local_backup_folder, os.path.split(os.path.dirname(url))[-1])
    # ensure a unique filename in case of intermittent internet
    local_file = os.path.join(
        local_folder,
        os.path.basename(url).strip('.json') + f'_{run_id}_{timestamp.strftime("%Y%m%d_%H%M%S")}.json'
    )
    if not os.path.exists(local_folder):
        os.makedirs(local_folder)
    root.save(file=local_file, mode='w', encoding='utf-8', ensure_ascii=False)
    try:
        root.save(file=url, mode='w', encoding='utf-8', ensure_ascii=False)
        return True
    except FileNotFoundError:
        log.warning(f'Unable to save to {url}. Please check network connection.')
        log.info(f"Data saved to {local_file}")
        return False


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

    log.info(f'CIRCULAR WEIGHING ANALYSIS for scheme entry {se} {run_id}')

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
        'Program Version': __version__,
        'Analysis Timestamp': datetime.now().strftime('%d-%m-%Y %H:%M:%S'),
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

    if not np.isclose(sum(analysis['mass difference']), 0):
        log.warning('Sum of mass differences is not zero. Analysis not accepted')
        analysis_meta['Acceptance met?'] = False

    flag = weighdata.metadata.get('Ambient OK?')
    if not flag:
        if flag is False:
            log.warning('Analysis not accepted due to unsuitable ambient conditions during weighing')
            analysis_meta['Acceptance met?'] = False
        else:  # e.g. flag is None
            log.warning('Ambient conditions unavailable during weighing')

    weighanalysis.add_metadata(**analysis_meta)

    timestamp = datetime.strptime(weighdata.metadata.get('Mmt Timestamp'), '%d-%m-%Y %H:%M:%S')
    save_data(root, url, local_backup_folder, run_id, timestamp)  # save to same file on C: drive as the weighing data

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


def check_existing_runs(root, scheme_entry, display_message=False):
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
        run_id = 'run_' + str(i + 1)
        try:
            existing_mmt = root['Circular Weighings'][scheme_entry]['measurement_' + run_id]
            if existing_mmt.metadata.get('Weighing complete'):
                try:
                    existing_analysis = root['Circular Weighings'][scheme_entry]['analysis_' + run_id]
                    if existing_analysis.metadata.get('Acceptance met?'):
                        if display_message:
                            log.info(f'Weighing {i+1} for {scheme_entry} accepted')
                        good_runs += 1
                    elif not existing_analysis.metadata.get('Exclude'):
                        if display_message:
                            log.info(f'Weighing {i+1} for {scheme_entry} outside acceptance but allowed')
                        good_runs += 1
                    else:
                        if display_message:
                            log.warning(f'Weighing {i+1} for {scheme_entry} outside acceptance')
                except KeyError:
                    if display_message:
                        log.warning(f'Weighing {i+1} for {scheme_entry} missing analysis')
            else:
                if display_message:
                    log.warning(f'Weighing {i+1} for {scheme_entry} incomplete')
        except KeyError:
            break
        i += 1

    run_1_no = int(run_id.strip('run_'))

    return good_runs, run_1_no  # returns integers for each


def elapsed_duration(duration):
    duration_in_s = duration.total_seconds()
    hours = int(divmod(duration_in_s, 3600)[0])  # Seconds in an hour = 3600
    minutes = int(divmod(duration_in_s, 60)[0])  # Seconds in a minute = 60
    seconds = int(divmod(duration_in_s, 60)[1])
    log.info(f"(duration of {hours} hours, {minutes} minutes and {seconds} seconds)")

    return hours, minutes, seconds
