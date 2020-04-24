import os
from datetime import datetime
import numpy as np
from msl.io import JSONWriter, read
from .. import __version__
from ..log import log
from ..constants import REL_UNC, DELTA_STR


def final_mass_calc(folder, client, client_wt_IDs, check_masses, std_masses, inputdata, nbc=True, corr=None):
    """Calculates mass values using matrix least squares methods

    Parameters
    ----------
    folder : url
        folder in which to save json file with output data; ideally an absolute path
    client : str
        name of client
    client_wt_IDs : list
        list of client wt IDs as strings, as used in the circular weighing scheme
    check_masses : dict
        list of check wt IDs as str, as used in the circular weighing scheme
        None if no check weights are used
    std_masses : dict
        keys: 'nominal (g)', 'mass values (g)', 'uncertainties (ug)', 'weight ID', 'Set Identifier', 'Calibrated'
    inputdata : numpy structured array
        use format np.asarray(<data>, dtype =[('+ weight group', object), ('- weight group', object),
        ('mass difference (g)', 'float64'), ('balance uncertainty (ug)', 'float64')])

    Returns
    -------
    json file containing structured array of weight IDs, mass values, and uncertainties,
    along with a record of the input data and other relevant information
    """

    # initialisation
    filesavepath = os.path.join(folder, client + '_finalmasscalc.json')
    make_backup(folder, filesavepath, client, )

    metadata = {
        'Program Version': __version__,
        'Timestamp': datetime.now().isoformat(sep=' ', timespec='minutes'),
        "Client": client
    }
    finalmasscalc = JSONWriter(filesavepath, metadata=metadata)

    mass_sets = finalmasscalc.require_group('1: Mass Sets')
    scheme_client = mass_sets.require_group('Client')
    scheme_check = mass_sets.require_group('Check')
    scheme_std = mass_sets.require_group('Standard')

    # import lists of masses from supplied info
    log.info('Beginning mass calculation for the following client masses:\n'+str(client_wt_IDs))
    # get client weight IDs for metadata
    num_client_masses = len(client_wt_IDs)
    scheme_client.add_metadata(**{
        'Number of masses': num_client_masses,
        'weight ID': client_wt_IDs
    })

    # get number of check masses, if used, and save as dataset
    if not check_masses:
        num_check_masses = 0
        check_wt_IDs = []
        scheme_check.add_metadata(**{
            'Number of masses': num_check_masses,
            'Set Identifier': 'No check set'})
        log.info('Checks: None')
    else:
        check_wt_IDs = check_masses['weight ID']
        num_check_masses = make_stds_dataset('Checks', check_masses, scheme_check)

    # get number of standards, and save as dataset
    num_stds = make_stds_dataset('Standards', std_masses, scheme_std)

    num_unknowns = num_client_masses + num_check_masses + num_stds
    log.info('Number of unknowns = '+str(num_unknowns))
    allmassIDs = np.append(np.append(client_wt_IDs, check_wt_IDs), std_masses['weight ID'])
    # note that stds are grouped last

    # Create design matrix and collect relevant data
    num_obs = len(inputdata)+num_stds
    differences = np.empty(len(inputdata))
    uncerts = np.empty(len(inputdata))
    designmatrix = np.zeros((num_obs, num_unknowns))
    rowcounter = 0

    log.debug('Input data: \n+ weight group, - weight group, mass difference (g), balance uncertainty (ug)'
             '\n'+str(inputdata))
    for entry in inputdata:
        # log.debug(str(entry[0])+str(entry[1])+str(entry[2])+str(entry[3]))
        grp1 = entry[0].split('+')
        for m in range(len(grp1)):
            log.debug('mass '+grp1[m]+' is in position '+str(np.where(allmassIDs == grp1[m])[0][0]))
            designmatrix[rowcounter, np.where(allmassIDs == grp1[m])] = 1
        grp2 = entry[1].split('+')
        for m in range(len(grp2)):
            log.debug('mass '+grp2[m]+' is in position '+str(np.where(allmassIDs == grp2[m])[0][0]))
            designmatrix[rowcounter, np.where(allmassIDs == grp2[m])] = -1
        differences[rowcounter] = entry[2]
        uncerts[rowcounter] = entry[3]
        rowcounter += 1
    for std in std_masses['weight ID']:
        designmatrix[rowcounter, np.where(allmassIDs == std)] = 1
        rowcounter += 1

    differences = np.append(differences, std_masses['mass values (g)'])     # corresponds to Y, in g
    uncerts = np.append(uncerts, std_masses['uncertainties (ug)'])          # balance uncertainties in ug

    # Calculate least squares solution, following the mathcad example in Tech proc MSLT.M.001.008
    x = designmatrix
    xT = designmatrix.T
    error_tally = 0

    for i in range(num_unknowns):
        sum = 0
        for r in range(num_obs):
            sum += designmatrix[r, i]**2
        if not sum:
            log.error("No comparisons in design matrix for "+allmassIDs[i])
            error_tally += 1
        # double checks that all columns in the design matrix contain at least one non-zero value
    if error_tally > 0:
        return None
    log.debug('differences:\n' + str(differences))
    log.debug('uncerts:\n' + str(uncerts))

    # Hadamard product: element-wise multiplication
    uumeas = np.vstack(uncerts) * np.hstack(uncerts)    # becomes square matrix dim num_obs

    rmeas = np.identity(num_obs)
    if type(corr) == np.ndarray:                        # Add off-diagonal terms for correlations
        for mass1 in std_masses['weight ID']:
            i = np.where(std_masses['weight ID'] == mass1)
            for mass2 in std_masses['weight ID']:
                j = np.where(std_masses['weight ID'] == mass2)
                rmeas[len(inputdata)+i[0], len(inputdata)+j[0]] = corr[i, j]
        log.debug('rmeas matrix includes correlations for stds:\n'+str(rmeas[:, -num_stds:]))

    psi_y_hadamard = np.zeros((num_obs, num_obs))       # Hadamard product is element-wise multiplication
    for i in range(num_obs):
        for j in range(num_obs):
            if not rmeas[i, j] == 0:
                psi_y_hadamard[i, j] = uumeas[i, j] * rmeas[i, j]

    psi_y_inv = np.linalg.inv(psi_y_hadamard)

    psi_bmeas_inv = np.linalg.multi_dot([xT, psi_y_inv, x])
    psi_bmeas = np.linalg.inv(psi_bmeas_inv)

    b = np.linalg.multi_dot([psi_bmeas, xT, psi_y_inv, differences])
    log.debug('Mass values before corrections:\n'+str(b))

    r0 = (differences - np.dot(x, b))*1e6               # residuals, converted from g to ug
    sum_residues_squared = np.dot(r0, r0)
    log.debug('Residuals:\n'+str(np.round(r0, 4)))       # also save as column with input data for checking

    inputdatares = np.empty((num_obs, 5), dtype=object)
        # dtype =[('+ weight group', object), ('- weight group', object), ('mass difference (g)', object),
        #         ('balance uncertainty (ug)', 'float64'), ('residual (ug)', 'float64')])
    inputdatares[0:len(inputdata), 0] = inputdata['+ weight group']
    inputdatares[len(inputdata):, 0] = std_masses['weight ID']
    inputdatares[0:len(inputdata), 1] = inputdata['- weight group']
    inputdatares[:, 2] = differences
    inputdatares[:, 3] = uncerts
    inputdatares[:, 4] = np.round(r0, 3)

    # check that the calculated residuals are less than twice the balance uncertainties in ug
    flag = []
    for entry in inputdatares:
        if np.absolute(entry[4]) > 2*entry[3]:
            flag.append(str(entry[0]) + ' - ' + str(entry[1]))
            log.warn("A residual for " + str(entry[0]) + ' - ' + str(entry[1]) + " is too large")

    # uncertainty due to no buoyancy correction
    if nbc:
        cmx1 = np.ones(num_client_masses+num_check_masses)  # from above, stds are added last
        cmx1 = np.append(cmx1, np.zeros(num_stds))          # 1's for unknowns, 0's for reference stds

        reluncert = REL_UNC                                 # relative uncertainty in ppm for no buoyancy correction: typ 0.03 or 0.1
        unbc = reluncert * b * cmx1                         # vector of length num_unknowns. TP wrongly has * 1e-6
        uunbc = np.vstack(unbc) * np.hstack(unbc)           # square matrix of dim num_obs
        rnbc = np.identity(num_unknowns)                    # add off-diagonals for any correlations

        psi_nbc_hadamard = np.zeros((num_unknowns, num_unknowns))
        for i in range(num_unknowns):                       # Here the Hadamard product is taking the diagonal of the matrix
            for j in range(num_unknowns):
                if not rnbc[i, j] == 0:
                    psi_nbc_hadamard[i, j] = uunbc[i, j] * rnbc[i, j]

        psi_b = psi_bmeas + psi_nbc_hadamard

    else:
        psi_b = psi_bmeas
        reluncert = 0

    std_uncert_b = np.sqrt(np.diag(psi_b))
    #det_varcovar_bmeas = np.linalg.det(psi_bmeas)
    #det_varcovar_nbc = np.linalg.det(psi_nbc_hadamard)
    #det_varcovar_b = np.linalg.det(psi_b)

    summarytable = np.empty((num_unknowns, 8), object)
    cov = 2
    for i in range(num_unknowns):
        summarytable[i, 1] = allmassIDs[i]

        if i < num_client_masses:
            summarytable[i, 2] = 'Client'
            summarytable[i, 7] = ""
        elif i >= num_client_masses + num_check_masses:
            summarytable[i, 2] = 'Standard'
            summarytable[i, 7] = 'c.f. {} g; {} {} g'.format(
                std_masses['mass values (g)'][i - num_client_masses - num_check_masses],
                DELTA_STR,
                std_masses['mass values (g)'][i - num_client_masses - num_check_masses] - b[i],
            )
        else:
            summarytable[i, 2] = 'Check'
            summarytable[i, 7] = 'c.f. {} g; {} {} g'.format(
                check_masses['mass values (g)'][i-num_client_masses],
                DELTA_STR,
                check_masses['mass values (g)'][i-num_client_masses] - b[i],
            )

        summarytable[i, 3] = np.round(b[i], 9)
        if b[i] >= 1:
            nom = format(int(b[i]), ',')
        else:
            nom = "{0:.1g}".format(b[i])
        if 'e-' in nom:
            nom = 0
        summarytable[i, 0] = nom
        summarytable[i, 4] = np.round(std_uncert_b[i], 3)
        summarytable[i, 5] = np.round(cov*std_uncert_b[i],3)
        summarytable[i, 6] = cov

    log.info('Found least squares solution')
    log.debug('Least squares solution:\nWeight ID, Set ID, Mass value (g), Uncertainty (ug), 95% CI\n'+str(summarytable))

    leastsq_meta = {
        'Number of observations': num_obs,
        'Number of unknowns': num_unknowns,
        'Degrees of freedom': num_obs - num_unknowns,
        #'Determinant of var-covar': [det_varcovar_bmeas, det_varcovar_nbc, det_varcovar_b],
        #'(normalised) variance from analysis': '???',
        'Relative uncertainty for no buoyancy correction (ppm)': reluncert,
        'Sum of residues squared (ug^2)': np.round(sum_residues_squared, 6),
    }
    if flag:
        leastsq_meta['Residuals greater than 2 balance uncerts'] = flag

    leastsq_data = finalmasscalc.create_group('2: Matrix Least Squares Analysis', metadata=leastsq_meta)
    leastsq_data.create_dataset('Input data with least squares residuals', data=inputdatares,
                                metadata={'headers':
                                ['+ weight group', '- weight group', 'mass difference (g)',
                                 'balance uncertainty (ug)', 'residual (ug)']})
    leastsq_data.create_dataset('Mass values from least squares solution', data=summarytable,
                                metadata={'headers':
                                ['Nominal (g)', 'Weight ID', 'Set ID',
                                 'Mass value (g)', 'Uncertainty (ug)', '95% CI', 'Cov', "c.f. Reference value (g)",
                                 ]})

    finalmasscalc.save(mode='w')

    log.info('Mass calculation saved to {!r}'.format(filesavepath))

    return finalmasscalc


def make_backup(folder, filesavepath, client, ):
    if os.path.isfile(filesavepath):
        existing_root = read(filesavepath, encoding='utf-8')
        if not os.path.exists(folder + "\\backups\\"):
            os.makedirs(folder + "\\backups\\")
        new_index = len(os.listdir(folder + "\\backups\\"))
        new_file = str(folder + "\\backups\\" + client + '_finalmasscalc_backup{}.json'.format(new_index))
        existing_root.is_read_only = False
        root = JSONWriter()
        root.set_root(existing_root)
        root.save(root=existing_root, file=new_file, mode='w', encoding='utf-8', ensure_ascii=False)
        log.info('Backup of previous Final Mass Calc saved as {}'.format(new_file))


def make_stds_dataset(type, masses_dict, scheme):
    num_masses = len(masses_dict['weight ID'])
    masses_dataarray = np.empty(num_masses, dtype={
        'names': ('weight ID', 'nominal (g)', 'mass values (g)', 'std uncertainties (ug)'),
        'formats': (object, np.float, np.float, np.float)})
    masses_dataarray['weight ID'] = masses_dict['weight ID']
    masses_dataarray['nominal (g)'] = masses_dict['nominal (g)']
    masses_dataarray['mass values (g)'] = masses_dict['mass values (g)']
    masses_dataarray['std uncertainties (ug)'] = masses_dict['uncertainties (ug)']

    scheme.add_metadata(**{
        'Number of masses': num_masses,
        'Set Identifier': masses_dict['Set Identifier'],
        'Calibrated': masses_dict['Calibrated'],
        'weight ID': masses_dict['weight ID'],
    })

    scheme.create_dataset('mass values', data=masses_dataarray)

    log.info(type + ' '+str(masses_dict['weight ID']))

    return num_masses

'''
var = np.dot(r0.T, r0) / (num_obs - num_unknowns)
log.debug('variance, \u03C3\u00b2, is:'+str(var.item(0)))

stdev = "{0:.5g}".format(np.sqrt(var.item(0)))
log.debug('residual standard deviation, \u03C3, is:'+stdev)

varcovar = np.multiply(var, np.linalg.inv(np.dot(xT, x)))
log.debug('variance-covariance matrix, C ='+str(varcovar))

det_varcovar = np.linalg.det(varcovar)
log.debug('determinant of variance-covariance matrix, det C ='+str(det_varcovar))
'''