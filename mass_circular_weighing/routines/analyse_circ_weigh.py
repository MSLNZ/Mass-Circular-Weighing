"""
Functions to analyse circular weighing data
"""
from __future__ import annotations
from typing import TYPE_CHECKING

import numpy as np
from datetime import datetime

from .. import __version__
from ..log import log

from ..routine_classes.circ_weigh_class import CircWeigh
from .json_circweigh_utils import *
from ..constants import SUFFIX, MU_STR, local_backup, IN_DEGREES_C

if TYPE_CHECKING:
    from mass_circular_weighing.configuration import Configuration
    from msl.io import JSONWriter

tab = '  '


def analyse_weighing_true_mass(
        cfg: Configuration, root: JSONWriter, url: str | os.PathLike, se: str, run_id: str, bal_mode: str,
        local_backup_folder=local_backup, **metadata
) -> JSONWriter | None:
    """Analyse a single complete circular weighing measurement using CircWeigh class in circ_weigh_class.py.
    Provides both true mass and basis 8000 mass values (saved into the json root)

    :param cfg: Configuration instance
    :param root: see msl.io for details
    :param url: path to json file where analysis will be saved (along with measurement run data)
    :param se: scheme entry
    :param run_id: string in format run_1
    :param bal_mode: one of 'aw', 'mw', 'mde'
    :param local_backup_folder: path to local backup folder
    :param metadata: optional dictionary of metadata to save
    :return: the original root object with new analysis data
    (or None if weighing was not completed)
    """
    timed = cfg.timed

    schemefolder = root['Circular Weighings'][se]
    weighdata = schemefolder['measurement_' + run_id]

    if not weighdata.metadata.get('Weighing complete'):
        return None

    log.info(f'CIRCULAR WEIGHING ANALYSIS for scheme entry {se} {run_id}')

    weighing = CircWeigh(se)

    # cfg.timed : if `True`, uses times from weighings, otherwise assumes equally spaced in time
    if cfg.timed:
        times = np.reshape(weighdata[:, :, 0], weighing.num_readings)
    else:
        times = []
    weighing.generate_design_matrices(times)

    if not cfg.drift:
        drift = weighing.determine_drift(weighdata[:, :, 1])  # allows program to select optimum drift correction
        log.info('Residual std dev. for each drift order:')
        for key, value in weighing.stdev.items():
            log.info(tab + key + ':\t' + str(value))
    else:
        drift = cfg.drift
        weighing.determine_drift(weighdata[:, :, 1])
        log.info('Residual std dev. for ' + drift + ' correction:\n' + tab
                 + str(weighing.stdev[drift]))

    massunit = weighdata.metadata.get('Unit')
    log.info('Selected ' + drift + ' correction (in ' + massunit + ' per ' + weighing.trend + '):\n' + tab
             + str(weighing.drift_coeffs(drift)))

    analysis = weighing.item_diff(drift)
    log.info('Differences (in ' + massunit + '):')
    for key, value in weighing.grpdiffs.items():
        log.info(tab + key + ':\t' + value)

    #### calculate true mass and conventional mass differences
    w_T = weighing.w_T_drift(drift)
    wt_grp_vols_temp_corr(cfg, root, se, run_id)

    air_dens = float(weighdata.metadata.get("Mean air density (kg/m3)"))
    diffab_true_mass = true_mass_differences(
        weighing.b[drift], w_T, massunit, weighdata.metadata.get("Weight group Tcorrected volumes (mL)"), air_dens
    )

    log.info('True Mass Differences (in mg):')
    analysis_true_mass = prettify_diffs(diffab_true_mass, weighing.wtgrps, stdev_diffab=None)

    log.info('Conventional Mass Differences (in mg):')
    diffab_b8000 = conv_mass(diffab_true_mass, w_T, weighdata.metadata.get("Weight group nominal volumes (mL)"))
    analysis_conv_mass = prettify_diffs(diffab_b8000, weighing.wtgrps, stdev_diffab=None)

    # save all the analysis to the JSONWriter
    # print(schemefolder.name + '/analysis_' + run_id)
    a = root.remove(schemefolder.name + '/analysis_' + run_id)

    weighanalysis = root.require_dataset(schemefolder.name + '/analysis_' + run_id,
                                         data=analysis, shape=(weighing.num_wtgrps, 1))

    max_stdev_circweigh = weighdata.metadata.get('Max stdev from CircWeigh (' + MU_STR + 'g)')

    analysis_meta = {
        'Program Version': __version__,
        'Analysis Timestamp': datetime.now().strftime('%d-%m-%Y %H:%M:%S'),
        'Residual std devs': str(weighing.stdev),
        'Selected drift': drift,
        'Uses mmt times': timed,
        'Mass unit': massunit,
        'Drift unit': massunit + ' per ' + weighing.trend,
        'Expected values': weighing.b,
        'Acceptance met?': weighing.stdev[drift] * SUFFIX[massunit] < max_stdev_circweigh * SUFFIX['ug'],
        'True mass differences (mg)': analysis_true_mass,
        'Basis8000 mass differences (mg)': analysis_conv_mass,
    }

    if bal_mode == 'aw':
        excl = weighing.stdev[drift] * SUFFIX[massunit] > cfg.EXCL * max_stdev_circweigh * SUFFIX['ug']
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

    try:
        timestamp = datetime.strptime(weighdata.metadata.get('Mmt Timestamp'), '%d-%m-%Y %H:%M')
    except ValueError:
        timestamp = datetime.strptime(weighdata.metadata.get('Mmt Timestamp'), '%d-%m-%Y %H:%M:%S')
    save_data(root, url, run_id, timestamp, local_backup_folder)  # save to same file on C: drive as the weighing data

    log.info('Circular weighing analysis for ' + se + ', ' + run_id + ' complete\n')

    return root


def wt_grp_vols_temp_corr(cfg: Configuration, root: JSONWriter, se: str, run_id: str) -> JSONWriter:
    """Returns a list of volumes in mL of each weight group in the scheme entry se, corrected for ambient temperature,
    and also the root object with metadata entries for nominal and corrected weight group volumes."""

    # combine relevant parts of weight sets
    all_wts = {'Weight ID': [], 'Expansion coeff (ppm/degC)': [], 'Vol (mL)': []}
    for k, v in all_wts.items():
        all_wts[k] = cfg.all_client_wts[k] + cfg.all_stds[k]
        if cfg.all_checks:
            all_wts[k] += cfg.all_checks[k]

    # get mean ambient conditions during weighing from weighing metadata
    schemefolder = root['Circular Weighings'][se]
    weighdata = schemefolder['measurement_' + str(run_id)]
    temp = float(weighdata.metadata.get('Mean T' + IN_DEGREES_C))

    # get weight groups
    weighing = CircWeigh(se)
    wt_grps = weighing.wtgrps

    # get volumes of weight groups, both nominal and also corrected for temperature
    wt_grp_vols_20 = np.empty(len(wt_grps), dtype=float)        # nominal at 20 deg C
    wt_grp_vols_Tcorr = np.empty(len(wt_grps), dtype=float)     # corrected for expansion due to ambient temperature
    for g, grp in enumerate(wt_grps):
        grp_vol = 0
        grp_vol_20 = 0
        for wt in grp.split("+"):
            # get index of wt in mass set
            try:
                i = all_wts['Weight ID'].index(wt)
            except ValueError:
                raise ValueError(f"{wt} is not in any of the specified weight sets.")

            nom_vol = all_wts['Vol (mL)'][i]
            grp_vol_20 += nom_vol
            grp_vol += corrected_volume(nom_vol, temp, all_wts['Expansion coeff (ppm/degC)'][i])

        wt_grp_vols_20[g] = grp_vol_20
        wt_grp_vols_Tcorr[g] = grp_vol

    if not all(0.9 < i/wt_grp_vols_Tcorr.max() < 1.1 for i in wt_grp_vols_Tcorr):
        log.warning(f"Volumes of weight groups differ by more than 10%: {wt_grp_vols_Tcorr}")

    weighdata.metadata["Weight group nominal volumes (mL)"] = wt_grp_vols_20
    weighdata.metadata["Weight group Tcorrected volumes (mL)"] = wt_grp_vols_Tcorr

    return root


def true_mass_differences(
        b_vector: np.ndarray, w_T: np.ndarray, massunit: str, vols: np.ndarray, air_dens: float
) -> np.ndarray:
    """Calculates true mass differences in mg between sequential groups of weights in the circular weighing,
    using calculated expected values for m_conv, and the following relation (~A.3 of MSLT.M.009.004):

        * m_conv * (1 - 1.2/8000) = m_true * (1 - rho_a/rho_m)

    where rho_a is measured air density and rho_m is the density of the mass or combination of masses.

    For a measured mass difference dm, this relation becomes

        * dm_true = dm_conv * (1 - 1.2/8000) + dV * rho_a

    noting that the buoyancy correction dV * rho_a is in mg for volumes in mL and air density in kg/m3.

    :param b_vector: expected values for the chosen drift correction
    :param w_T: selector matrix of 1s and -1s to calculate differences
    :param massunit: mass unit for expected values (from weighdata.metadata.get('Unit'))
    :param vols: total volume in mL for each weight group, corrected for expansion due to temperature
    :param air_dens: measured mean air density in kg/m3 during the weighing
    :return: 1-d array of true mass differences in mg
    """
    vols.resize(len(b_vector), refcheck=False)

    # convert b vector to mg
    b_in_mg = SUFFIX[massunit] * b_vector / SUFFIX['mg']

    # difference_in_true_mass = 0.99985 * (b_mass1 - b_mass2) + (vol_1 - vol_2) * air_density
    diffab = 0.99985 * np.dot(w_T, b_in_mg)   # because 0.99985 = 1/(1 + 1.2/8000)
    buoyancy_corr = air_dens * np.dot(w_T, vols)  # in mg
    diffab_true_mass = diffab + buoyancy_corr  # both in mg
    log.debug('True mass differences (in mg) are\n'+str(diffab_true_mass))

    return diffab_true_mass


def conv_mass(diffab_true_mass: np.ndarray, w_T: np.ndarray, vols: np.ndarray) -> np.ndarray:
    """Calculates conventional mass differences in mg, using the relation

        * dm_conv = (dm_true - dV20 * 1.2 ) / (1 - 1.2/8000)

    where true mass differences, dm_true, are in mg and differences in nominal volume (20 degC), dV20, are in mL.

    :param diffab_true_mass: an array of true mass differences in mg
    :param w_T: selector matrix of 1s and -1s to calculate differences
    :param vols: volume in mL, calculated using the nominal mass and measured density
    :return: 1-d array of conventional mass differences
    """
    buoyancy_corr = 1.2 * np.dot(w_T[:, :len(vols)], vols)  # in mg
    diffab_8000 = (diffab_true_mass - buoyancy_corr) / (1 - 1.2/8000)  # all in mg
    log.debug('Conventional mass differences (in mg) are\n' + str(diffab_8000))

    return diffab_8000


def prettify_diffs(diffab: np.array, wtgrps: list[str], stdev_diffab: list | None) -> np.ndarray:
    """Compiles the mass differences into a structured array and prints them nicely to the log.

    :param diffab: mass differences
    :param wtgrps: weight groups in circular weighing
    :param stdev_diffab:
    :return: analysis dataset with headings '+ weight group', '- weight group',  'mass difference', 'residual'
               and grpdiffs_tm dict where the
                    keys are weight groups by position e.g. grp1 - grp2; grp2 - grp3 etc, and
                    values are true mass differences in mg
    """
    num_wtgrps = len(wtgrps)
    grpdiffs = {}
    for grp in range(num_wtgrps - 1):
        key = 'grp' + str(grp + 1) + ' - grp' + str(grp + 2)
        value = "{0:.5g}".format(diffab[grp])
        if stdev_diffab:
            value += ' (' + "{0:.3g}".format(stdev_diffab[grp]) + ')'
        grpdiffs[key] = value

    grpdiffs['grp'+str(num_wtgrps)+' - grp1'] = \
        "{0:.5g}".format(diffab[num_wtgrps-1])  # +' ('+"{0:.3g}".format(stdev_diffab[num_wtgrps-1])+')'

    for key, value in grpdiffs.items():
        log.info(tab + key + ':\t' + value)

    analysis = np.empty((num_wtgrps,),
                        dtype=[('+ weight group', object), ('- weight group', object),
                               ('mass difference', 'float64'), ('residual', 'float64')]
                        )

    analysis['+ weight group'] = wtgrps
    analysis['- weight group'] = np.roll(wtgrps, -1)
    analysis['mass difference'] = diffab
    if stdev_diffab:
        analysis['residual'] = stdev_diffab

    return analysis


def corrected_volume(nom_vol: float, temp: float, exp_coeff: float) -> float:
    """return the volume, in mL, corrected for expansion due to the temperature deviating from 20 deg C

    :param nom_vol: volume in mL, calculated using the nominal mass and measured density
    :param temp: measured temperature in deg C
    :param exp_coeff: expansion coefficient in ppm/degC
    """
    return nom_vol * (1 + exp_coeff * 0.000001 * (temp - 20))


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
    save_data(root, url, run_id, timestamp, local_backup_folder)  # save to same file on C: drive as the weighing data

    log.info('Circular weighing analysis for ' + se + ', ' + run_id + ' complete\n')

    return weighanalysis


def analyse_old_weighing(cfg, filename, se, run_id):
    """Analyses a specific weighing run on file, with timed and drift parameters as specified in the configuration"""
    url = cfg.folder + "\\" + filename + '.json'
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
