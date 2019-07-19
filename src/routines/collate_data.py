# this script will collect data from multiple json files for the same client weighing

import os
from msl.io import read
from ..constants import MU_STR, SUFFIX, SQRT_F
from ..log import log
import numpy as np


def collate_a_data_from_json(folder, filename, scheme_entry):
    """Use this function for an automatic weighing where individual weighings are not likely to meet SQRT_F criterion,
    but the ensemble average is.

    Parameters
    ----------
    folder
    filename
    scheme_entry

    The json file must have analysis datasets with fields and formats as follows:
    dtype = [('+ weight group', 'O'), ('- weight group', 'O'), ('mass difference', '<f8'), ...

    Returns
    -------
    tuple of
    [0] structured array of averaged weighing data in grams, if meets acceptance criteria, else None
    [1] bool indicating whether average data meets acceptance criteria for weighing

    """
    url = folder + "\\" + filename + '.json'
    if not os.path.isfile(url):
        raise IOError('File does not exist {!r}'.format(url))

    root = read(url)
    wt_grps = scheme_entry.split()
    num_wt_grps = len(wt_grps)
    collated = {'Stdev': [], 'Max stdev': []}
    for grp in wt_grps:
        collated[grp] = []

    for dataset in root.datasets():
        dname = dataset.name.split('_')  # split('/')[-1].
        exclude = dataset.metadata.get('Exclude?')

        if dname[0][-8:] == 'analysis' and not exclude:
            run_id = 'run_' + dname[2]

            meta = root.require_dataset(root['Circular Weighings'][scheme_entry].name + '/measurement_' + run_id)
            collated['Stdev'].append(meta.metadata.get('Stdev for balance (' + MU_STR + 'g)'))
            collated['Max stdev'].append(meta.metadata.get('Max stdev from CircWeigh ('+MU_STR+'g)'))

            bal_unit = dataset.metadata.get('Mass unit')
            for i in range(dataset.shape[0]):
                key = dataset['+ weight group'][i]
                collated[key].append(dataset['mass difference'][i]*SUFFIX[bal_unit])

    for key, value in collated.items():
        collated[key] = (np.average(value), np.std(value))

    inputdata = np.empty(num_wt_grps-1,
                         dtype=[('+ weight group', object), ('- weight group', object),
                                ('mass difference (g)', 'float64'),
                                ('balance uncertainty (' + MU_STR + 'g)', 'float64')])

    acceptable = True
    massdiff = np.empty(num_wt_grps)
    stdevs = np.empty(num_wt_grps)
    for i, grp in enumerate(wt_grps):
        massdiff[i] = collated[grp][0]
        stdevs[i] = collated[grp][1]
        if not collated[grp][1] < SQRT_F*collated['Max stdev'][0]*SUFFIX['ug']:
            log.warning('Stdev of differences for + weight group ' + grp + ' falls outside acceptable limits')
            acceptable = False

    if not (np.round(np.sum(massdiff), 12) == 0):
        log.warning('Mass differences for ' + scheme_entry + ' do not sum to zero within reasonable limits')
        acceptable = False

    inputdata[:]['+ weight group'] = wt_grps[:-1]
    inputdata[:]['- weight group'] = np.roll(wt_grps, -1)[:-1]
    inputdata[:]['mass difference (g)'] = massdiff[:-1]
    for row in range(num_wt_grps - 1):
        inputdata[row:]['balance uncertainty ('+MU_STR+'g)'] = collated['Stdev'][0]

    return inputdata, acceptable


def collate_m_data_from_json(folder, filename, scheme_entry):
    """Use this function to collate one or two runs from an mde or mw weighing

    Parameters
    ----------
    folder : path
        path to folder where json file resides
    filename : str
        name of json file (without ending)
    scheme_entry : str
        masses in scheme entry separated by spaces and + only

    The json file must have analysis datasets with fields and formats as follows:
    dtype = [('+ weight group', 'O'), ('- weight group', 'O'), ('mass difference', '<f8'), ...

    Returns
    -------
    structured array of all weighing data in grams for acceptable/included weighings only

    """
    inputdata = np.empty(0,
                         dtype=[('+ weight group', object), ('- weight group', object),
                               ('mass difference (g)', 'float64'), ('balance uncertainty ('+MU_STR+'g)', 'float64')])

    url = folder + "\\" + filename + '.json'
    if os.path.isfile(url):
        root = read(url)
    else:
        print('No such file exists')  # TODO: could upgrade this to raise error if needed
        return None

    for dataset in root.datasets():
        dname = dataset.name.split('_')  # split('/')[-1].

        ok = dataset.metadata.get('Acceptance met?')
        if dname[0][-8:] == 'analysis' and ok:
            run_id = 'run_' + dname[2]

            meta = root.require_dataset(root['Circular Weighings'][scheme_entry].name + '/measurement_' + run_id)
            stdev = meta.metadata.get('Stdev for balance ('+MU_STR+'g)')

            bal_unit = dataset.metadata.get('Mass unit')

            i_len = inputdata.shape[0]
            d_len = dataset.shape[0]
            inputdata.resize(i_len + d_len - 1)
            inputdata[i_len:]['+ weight group'] = dataset['+ weight group'][:-1]
            inputdata[i_len:]['- weight group'] = dataset['- weight group'][:-1]
            inputdata[i_len:]['mass difference (g)'] = dataset['mass difference'][:-1]*SUFFIX[bal_unit]
            for row in range(d_len - 1):
                inputdata[i_len+row:]['balance uncertainty ('+MU_STR+'g)'] = stdev

    return inputdata


def collate_data_from_list(weighings):
    """

    Parameters
    ----------
    weighings : list of structured arrays of weighings
    each weighing must use dtype =[('+ weight group', object), ('- weight group', object),
                                   ('mass difference (g)', 'float64'), ('balance uncertainty (ug)', 'float64')])

    Returns
    -------
    collated data : structured array
    a single array of weighing data which can be input into final_mass_calc

    """
    collated = np.empty(0,
        dtype =[('+ weight group', object), ('- weight group', object),
                ('mass difference (g)', 'float64'), ('balance uncertainty ('+MU_STR+'g)', 'float64')])

    for weighing in weighings:
        c_len = collated.shape[0]
        w_len = weighing.shape[0]
        collated.resize(c_len + w_len)
        collated[c_len:] = weighing

    return collated