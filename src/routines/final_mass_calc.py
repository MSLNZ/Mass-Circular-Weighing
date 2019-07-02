from datetime import datetime
import numpy as np
from msl.io import JSONWriter
from src.log import log


# initialisation
metadata = {'Timestamp': datetime.now().isoformat(sep=' ', timespec='minutes'), "Client": 'Hort Research'}

finalmasscalc = JSONWriter('finalmasscalc_msl-io1.json', metadata=metadata)

mass_sets = finalmasscalc.create_group('1: Mass Sets')
scheme_client = mass_sets.create_group('Client')
scheme_check = mass_sets.create_group('Check')
scheme_std = mass_sets.create_group('Standard')

collated_data = {}
final_mass_values = {}

# import lists of masses from scheme info
num_client_masses = 9
client_wt_IDs = ['100', '50', '20', '20d', '10', '5', '2', '2d', '1']
scheme_client.add_metadata(**{
    'Number of masses': num_client_masses,
    'client weight ID': client_wt_IDs
})
log.info('Client masses: '+str(client_wt_IDs))


num_check_masses = 2
check_wt_IDs = ['5w', '1w']
scheme_check.add_metadata(**{
    'Number of masses': num_check_masses,
    'check weight ID': check_wt_IDs
})
log.info('Check masses: '+str(check_wt_IDs))


num_stds = 7

std_masses = np.empty(num_stds, dtype={
    'names': ('std weight ID', 'std mass values', 'std residuals', 'std uncerts'),
    'formats': (object, np.float, np.float, np.float)})

std_masses['std weight ID'] = ['100s', '50s', '20s', '10s', '5s', '2s', '1s']
std_masses['std mass values'] = [
    100.000059108,
    50.000053126,
    19.999998346,
    10.000010291,
    4.999997782,
    1.999996291,
    0.999956601
]
std_masses['std residuals'] = [
    -2.779,
    3.305,
    -1.368,
    -0.05,
    -0.071,
    -0.33,
    0.575
]
std_masses['std uncerts'] = [
    4.008,
    2.624,
    2.088,
    1.747,
    1.152,
    0.806,
    0.752
]

scheme_std.add_metadata(**{'Number of masses': num_stds})
scheme_std.create_dataset('std mass values', data=std_masses)
log.info('Standards:\n'+str(std_masses))


num_unknowns = num_client_masses + num_stds + num_check_masses
log.info('Number of unknowns = '+str(num_unknowns))
allmassIDs = np.append(client_wt_IDs + check_wt_IDs, std_masses['std weight ID'])  # note that stds are grouped last
#print('List of masses:', allmassIDs)
final_mass_values['All masses'] = allmassIDs

# import data
#num_circweighings = 7
num_obs = 25 # get this from the circular weighing scheme - here 18 circ weighing entries and 7 standards

# test data
weighing1 = np.asarray(
    [
        ('100', '100s', 0.000640283, 0.0, 8.0),
        ('100s', '50+50s', -0.000192765, 11.071, 8.0)
    ],
    dtype =[('+ weight group', object), ('- weight group', object), ('mass difference', 'float64'), ('residual', 'float64'), ('bal uncert', 'float64')]
)
weighing2 = np.asarray([('50', '50s', 0.00017231, 6.228, 6.0), ('50s', '20+20d+10', -0.000061662, -4.827, 6.0)], dtype =[('+ weight group', object), ('- weight group', object), ('mass difference', 'float64'), ('residual', 'float64'), ('bal uncert', 'float64')])
weighing3 = np.asarray([('20', '20s', -0.000072181, -3.352, 5.0), ('20s', '20d', -0.000037743, 4.489, 5.0), ('20d', '10+10s', -0.000101083, 1.137, 5.0)], dtype =[('+ weight group', object), ('- weight group', object), ('mass difference', 'float64'), ('residual', 'float64'), ('bal uncert', 'float64')])
weighing4 = np.asarray([('10', '10s', 0.000121268, -2.215, 5.0), ('10s', '5+5w', 0.000081936, -0.665, 5.0)], dtype =[('+ weight group', object), ('- weight group', object), ('mass difference', 'float64'), ('residual', 'float64'), ('bal uncert', 'float64')])
weighing5 = np.asarray([('5', '5s', -0.000069925, -0.665, 5.0), ('5s', '5w', -0.000000631, 0.665, 5.0)], dtype =[('+ weight group', object), ('- weight group', object), ('mass difference', 'float64'), ('residual', 'float64'), ('bal uncert', 'float64')])
weighing6 = np.asarray([('2', '2s', -0.00006477, 0.0, 0.5), ('2s', '2d', -0.000041124, 0.127, 0.5), ('2d', '1+1s', 0.000049755, 0.127, 0.5)], dtype =[('+ weight group', object), ('- weight group', object), ('mass difference', 'float64'), ('residual', 'float64'), ('bal uncert', 'float64')])
weighing7 = np.asarray([('1', '1s', 0.00007601, -0.182, 0.5), ('1s', '1w', -0.000057911, 0.343, 0.5), ('1', '1s', 0.000076501, 0.309, 0.5), ('1s', '1w', -0.000058598, -0.344, 0.5)], dtype =[('+ weight group', object), ('- weight group', object), ('mass difference', 'float64'), ('residual', 'float64'), ('bal uncert', 'float64')])
weighings = [weighing1, weighing2, weighing3, weighing4, weighing5, weighing6, weighing7]
inputdata = np.empty(num_obs-num_stds,
    dtype =[('+ weight group', object), ('- weight group', object), ('mass difference', 'float64'), ('residual', 'float64'), ('bal uncert', 'float64')])
i = 0
for weighing in weighings:
    for entry in weighing:
        inputdata[i] = entry
        i+=1

# initialise design matrix (final mass calculation part)
designmatrix = np.zeros((num_obs,num_unknowns))     # could use sparse matrix but probably not big enough to worry!
differences = np.empty(num_unknowns)
#residuals = np.empty(num_unknowns)                 # actually an output of the calculation
uncerts = np.empty(num_unknowns)

# Create design matrix
rowcounter = 0

log.info('Input data: \n+ weight group, - weight group, mass difference, residual, bal uncert\n'+str(inputdata))
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
    #residuals[rowcounter] = entry[3]               # actually an output of the calculation
    uncerts[rowcounter] = entry[4]
    rowcounter += 1
for std in std_masses['std weight ID']:
    designmatrix[rowcounter, np.where(allmassIDs == std)] = 1
    rowcounter += 1



# Check data entered correctly:
#print(designmatrix)

differences = np.append(differences, std_masses['std mass values'])     # corresponds to Y, in g
#residuals = np.append(residuals, std_masses['std residuals'])           # actually an output of the calculation
uncerts = np.append(uncerts, std_masses['std uncerts'])                 # balance uncertainties in ug

#log.info('Differences: '+str(differences))
#print(residuals)
#print(uncerts)

# Calculate least squares solution
# Following the mathcad example in Tech proc MSLT.M.001.008

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
sum_residues_squared = np.dot(r0,r0)
#log.info('R0 = '+str(r0))
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

finalmasscalc.save(url='finalmasscalc_msl-io_final.json')


var = np.dot(r0.T, r0) / (num_obs - num_unknowns)
log.debug('variance, \u03C3\u00b2, is:'+str(var.item(0)))

'''self.stdev[drift] = "{0:.5g}".format(np.sqrt(var.item(0)))
log.debug('residual standard deviation, \u03C3, for', drift, 'is:', self.stdev[drift])

self.varcovar[drift] = np.multiply(var, xTx_inv)
log.debug('variance-covariance matrix, C =', self.varcovar[drift],
          'for', str(self.num_wtgrps),'item(s), and', drift, 'correction')
          
          
          '''