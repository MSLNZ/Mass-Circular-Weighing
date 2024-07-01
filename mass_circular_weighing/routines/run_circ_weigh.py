"""
The main circular weighing routine and associated functions
"""
from time import perf_counter
from datetime import datetime

from .. import __version__
from ..routine_classes.circ_weigh_class import CircWeigh
from ..constants import local_backup
from ..equip import check_ambient_pre, check_ambient_post
from ..log import log

from .json_circweigh_utils import *

tab = '  '


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
                    network_ok = save_data(root, url, run_id, timestamp, local_backup_folder, )
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
        ok = save_data(root, url, run_id, timestamp, local_backup_folder)
        if not ok:
            log.debug('weighdata:\n' + str(weighdata[:, :, :]))

        return root

    log.info('Circular weighing sequence aborted')
    if reading:
        weighdata.add_metadata(**metadata)
        ok = save_data(root, url, run_id, timestamp, local_backup_folder)
        if not ok:
            log.debug('weighdata:\n' + str(weighdata[:, :, :]))

    return None


def elapsed_duration(duration):
    duration_in_s = duration.total_seconds()
    hours = int(divmod(duration_in_s, 3600)[0])  # Seconds in an hour = 3600
    minutes = int(divmod(duration_in_s, 60)[0])  # Seconds in a minute = 60
    seconds = int(divmod(duration_in_s, 60)[1])
    log.info(f"(duration of {hours} hours, {minutes} minutes and {seconds} seconds)")

    return hours, minutes, seconds
