from datetime import datetime
import numpy as np
from msl.io import JSONWriter
from src.log import log


def final_mass_calc(filesavepath, client, client_wt_IDs, check_wt_IDs, std_masses, inputdata):
    '''Calculates mass values using matrix least squares methods

    Parameters
    ----------
    filesavepath : url
        where to save json file with output data; ideally an absolute path
    client : str
        name of client
    client_wt_IDs : list
        list of client wt IDs as str, as used in the circular weighing scheme
    check_wt_IDs : list
        list of check wt IDs as str, as used in the circular weighing scheme
    std_masses : numpy array
        fill array using np.empty(num_stds, dtype={
            'names': ('std weight ID', 'std mass values (g)', 'std uncertainties (ug)'),
            'formats': (object, np.float, np.float)})
    inputdata : numpy structured array
        use format np.asarray(<data>, dtype =[('+ weight group', object), ('- weight group', object),
        ('mass difference', 'float64'), ('bal uncert', 'float64')])

    Returns
    -------
    json file containing structured array of weight IDs, mass values, and uncertainties,
    along with a record of the input data and other relevant information
    '''

    # initialisation
    metadata = {'Timestamp': datetime.now().isoformat(sep=' ', timespec='minutes'), "Client": client}
    finalmasscalc = JSONWriter(filesavepath, metadata=metadata)

    mass_sets = finalmasscalc.create_group('1: Mass Sets')
    scheme_client = mass_sets.create_group('Client')
    scheme_check = mass_sets.create_group('Check')
    scheme_std = mass_sets.create_group('Standard')

    # import lists of masses from supplied info
    num_client_masses = len(client_wt_IDs)
    scheme_client.add_metadata(**{
        'Number of masses': num_client_masses,
        'client weight ID': client_wt_IDs
    })
    log.info('Client masses: '+str(client_wt_IDs))

    num_check_masses = len(check_wt_IDs)
    scheme_check.add_metadata(**{
        'Number of masses': num_check_masses,
        'check weight ID': check_wt_IDs
    })
    log.info('Check masses: '+str(check_wt_IDs))

    num_stds = len(std_masses)
    scheme_std.add_metadata(**{'Number of masses': num_stds})
    scheme_std.create_dataset('std mass values', data=std_masses)
    log.info('Standards:\nstd weight ID, std mass values (g), std uncertainties (ug)\n'+str(std_masses))

    num_unknowns = num_client_masses + num_stds + num_check_masses
    log.info('Number of unknowns = '+str(num_unknowns))
    allmassIDs = np.append(client_wt_IDs + check_wt_IDs, std_masses['std weight ID'])  # note that stds are grouped last
    differences = np.empty(num_unknowns)
    uncerts = np.empty(num_unknowns)

    # Create design matrix and collect relevant data
    num_obs = len(inputdata)+num_stds
    designmatrix = np.zeros((num_obs, num_unknowns))
    rowcounter = 0

    log.info('Input data: \n+ weight group, - weight group, mass difference (g), balance uncertainty (ug)'
             '\n'+str(inputdata))
    for entry in inputdata:
        #log.debug(entry)
        grp1 = entry[0].split('+')
        for m in range(len(grp1)):
            #log.debug('mass '+grp1[m]+' is in position '+str(np.where(allmassIDs == grp1[m])[0][0]))
            designmatrix[rowcounter, np.where(allmassIDs == grp1[m])] = 1
        grp2 = entry[1].split('+')
        for m in range(len(grp2)):
            #log.debug('mass '+grp2[m]+' is in position '+str(np.where(allmassIDs == grp2[m])[0][0]))
            designmatrix[rowcounter, np.where(allmassIDs == grp2[m])] = -1
        differences[rowcounter] = entry[2]
        uncerts[rowcounter] = entry[3]
        rowcounter += 1
    for std in std_masses['std weight ID']:
        designmatrix[rowcounter, np.where(allmassIDs == std)] = 1
        rowcounter += 1

    differences = np.append(differences, std_masses['std mass values (g)'])     # corresponds to Y, in g
    uncerts = np.append(uncerts, std_masses['std uncertainties (ug)'])                 # balance uncertainties in ug

    # Calculate least squares solution, following the mathcad example in Tech proc MSLT.M.001.008
    x = designmatrix
    xT = designmatrix.T

    # Hadamard product: element-wise multiplication
    uumeas = np.vstack(uncerts) * np.hstack(uncerts)    # becomes square matrix dim num_obs
    rmeas = np.identity(num_obs)                        # Add off-diagonal terms for correlations

    psi_y_hadamard = np.zeros((num_obs, num_obs))       # Hadamard product is element-wise multiplication
    for i in range(num_obs):
        for j in range(num_obs):
            psi_y_hadamard[i, j] = uumeas[i, j] * rmeas[i, j]

    psi_y_inv = np.linalg.inv(psi_y_hadamard)

    psi_bmeas_inv = np.linalg.multi_dot([xT, psi_y_inv, x])
    psi_bmeas = np.linalg.inv(psi_bmeas_inv)

    b = np.linalg.multi_dot([psi_bmeas, xT, psi_y_inv, differences])
    #log.info('Mass values are: '+str(b))

    r0 = (differences - np.dot(x, b))*1e6               # residuals, converted from g to ug
    sum_residues_squared = np.dot(r0, r0)
    log.info('Residuals:\n'+str(np.round(r0, 3)))
    #print('residuals = ', residuals)
    #for i in range(num_obs):
    #    print('residuals == r0?', residuals[i], np.round(r0[i],3), residuals[i] == np.round(r0[i],3))

    # uncertainty due to no buoyancy correction
    cmx1 = np.ones(num_client_masses+num_check_masses)  # from above, stds are added last
    cmx1 = np.append(cmx1, np.zeros(num_stds))          # 1's for unknowns, 0's for reference stds

    reluncert = 0.10                                    # relative uncertainty in ppm for no buoyancy correction
    rnbc = np.identity(num_unknowns)                    # Add off-diagonal terms for correlations
    unbc = reluncert * b * cmx1                         # vector of length num_unknowns. TP wrongly has * 1e-6

    uunbc = np.vstack(unbc) * np.hstack(unbc)           # square matrix of dim num_obs

    psi_nbc_hadamard = np.zeros((num_unknowns, num_unknowns))
    for i in range(num_unknowns):                       # Here the Hadamard product is taking the diagonal of the matrix
        for j in range(num_unknowns):
            psi_nbc_hadamard[i, j] = uunbc[i, j] * rnbc[i, j]

    psi_b = psi_bmeas + psi_nbc_hadamard
    std_uncert_b = np.sqrt(np.diag(psi_b))
    det_varcovar = np.linalg.det(psi_b)

    summarytable = np.empty((num_unknowns, 5), object)
    for i in range(num_unknowns):
        summarytable[i, 0] = allmassIDs[i]
        if i < num_client_masses:
            summarytable[i, 1] = 'Client'
        elif i >= num_client_masses + num_check_masses:
            summarytable[i, 1] = 'Standard'
        else:
            summarytable[i, 1] = 'Check'

        summarytable[i, 2] = np.round(b[i], 9)
        summarytable[i, 3] = np.round(std_uncert_b[i], 3)
        summarytable[i, 4] = np.round(2*std_uncert_b[i],3)

    log.info('Least squares solution:\nWeight ID, Set ID, Mass value (g), Uncertainty (ug), 95% CI\n'+str(summarytable))

    leastsq_data = finalmasscalc.create_group('2: Matrix Least Squares Analysis')
    leastsq_data.create_dataset('Input data', data=inputdata)
    leastsq_data.create_dataset('Mass values from least squares solution', data=summarytable)
    leastsq_data.add_metadata(**{
        'Number of observations': num_obs,
        'Number of unknowns': num_unknowns,
        'Degrees of freedom': num_obs - num_unknowns,
        'Determinant of var-covar': det_varcovar,
        '(normalised) variance from analysis': '???',
        'Relative uncertainty for no buoyancy correction (ppm)': reluncert,
        'Sum of residues squared (ug^2)': np.round(sum_residues_squared, 6),
    })

    finalmasscalc.save()
    return


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