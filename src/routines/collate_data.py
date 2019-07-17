# this script will collect data from multiple json files for the same client weighing

import os
from msl.io import read
import numpy as np


def collate_data_from_json(folder, filename, scheme_entry):
    """

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
    structured array of all weighing data for acceptable/included weighings only

    """
    inputdata = np.empty(0,
                         dtype=[('+ weight group', object), ('- weight group', object),
                               ('mass difference (g)', 'float64'), ('balance uncertainty (ug)', 'float64')])

    url = folder + "\\" + filename + '.json'
    if os.path.isfile(url):
        root = read(url)
    else:
        print('No such file exists')  # TODO: could upgrade this to raise error if needed
        return None

    suffix = {'ug': 1e-6, 'mg': 1e-3, 'g': 1, 'kg': 1e3}
    for dataset in root.datasets():
        dname = dataset.name.split('_')  # split('/')[-1].
        ok = dataset.metadata.get('Acceptance met?')
        if dname[0][-8:] == 'analysis' and ok:
            run_id = 'run_' + dname[2]

            meta = root.require_dataset(root['Circular Weighings'][scheme_entry].name + '/measurement_' + run_id)
            stdev = meta.metadata.get('Stdev for balance (ug)')

            bal_unit = dataset.metadata.get('Mass unit')

            i_len = inputdata.shape[0]
            d_len = dataset.shape[0]
            inputdata.resize(i_len + d_len)
            inputdata[i_len:]['+ weight group'] = dataset['+ weight group']
            inputdata[i_len:]['- weight group'] = dataset['- weight group']
            inputdata[i_len:]['mass difference (g)'] = dataset['mass difference']*suffix[bal_unit]
            for row in range(d_len):
                inputdata[i_len+row:]['balance uncertainty (ug)'] = stdev

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
        dtype =[('+ weight group', object), ('- weight group', object), ('mass difference (g)', 'float64'), ('balance uncertainty (ug)', 'float64')])

    for weighing in weighings:
        c_len = collated.shape[0]
        w_len = weighing.shape[0]
        collated.resize(c_len + w_len)
        collated[c_len:] = weighing

    return collated