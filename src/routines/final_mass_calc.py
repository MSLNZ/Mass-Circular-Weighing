from datetime import datetime
import numpy as np
from src.jsonReaderWriter import jsonReaderWriter
import pprint
from src.log import log


# initialisation
finalmasscalc = jsonReaderWriter('finalmasscalcdemo1.json')

metadata = {'Timestamp': datetime.now().isoformat(sep=' ', timespec='minutes'), "Client": 'Hort Research'}
finalmasscalc.add_metadata(metadata)

finalmasscalc.create_subgroup('1: Mass Sets')
finalmasscalc.create_subgroup('Client', finalmasscalc.root['1: Mass Sets'])
finalmasscalc.create_subgroup('Check', finalmasscalc.root['1: Mass Sets'])
finalmasscalc.create_subgroup('Standard', finalmasscalc.root['1: Mass Sets'])

scheme_client = {}
scheme_std = {}
scheme_check = {}
collated_data = {}
final_mass_values = {}

# import lists of masses from scheme info
num_client_masses = 9
scheme_client['Number of masses'] = num_client_masses
scheme_client['client weight ID'] = ['100', '50', '20', '20d', '10', '5', '2', '2d', '1']
log.info('Client masses: '+str(scheme_client))
finalmasscalc.add_metadata(scheme_client, '1: Mass Sets', 'Client')

num_check_masses = 2
scheme_check['Number of masses'] = num_check_masses
scheme_check['check weight ID'] = ['5w', '1w']
log.info('Check masses: '+str(scheme_check))
finalmasscalc.add_metadata(scheme_check, '1: Mass Sets', 'Check')

num_stds = 7
scheme_std['Number of masses'] = num_stds
scheme_std['std weight ID'] = ['100s', '50s', '20s', '10s', '5s', '2s', '1s']
scheme_std['std mass values'] = [
    100.000059108,
    50.000053126,
    19.999998346,
    10.000010291,
    4.999997782,
    1.999996291,
    0.999956601
]
scheme_std['std residuals'] = [
    -2.779,
    3.305,
    -1.368,
    -0.05,
    -0.071,
    -0.33,
    0.575
]
scheme_std['std uncerts'] = [
    4.008,
    2.624,
    2.088,
    1.747,
    1.152,
    0.806,
    0.752
]
# print as nice array?
# scheme_std['std weights'] = [scheme_std['std weight ID'], scheme_std['std mass values'], scheme_std['std residuals'], scheme_std['std uncerts']]

log.info('Standards: '+str(scheme_std))
finalmasscalc.add_metadata(scheme_std, '1: Mass Sets', 'Standard')


num_unknowns = num_client_masses + num_stds + num_check_masses
print('Number of unknowns =', num_unknowns)
allmassIDs = scheme_client['client weight ID']+scheme_check['check weight ID']+scheme_std['std weight ID']
print('List of masses:', allmassIDs)
final_mass_values['All masses'] = allmassIDs

# import data
num_circweighings = 7
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

# initialise design matrix (final mass calculation part)
designmatrix = np.zeros((num_obs,num_unknowns))  # could use sparse matrix but probably not big enough to worry!
differences = np.empty(num_obs - num_stds)
residuals = np.empty(num_obs - num_stds)
uncerts = np.empty(num_obs - num_stds)

# Create design matrix
rowcounter = 0
for weighing in weighings:
    for entry in weighing:
        #log.info(entry)
        grp1 = entry[0].split('+')
        for m in range(len(grp1)):
            #log.debug('mass '+grp1[m]+' is in position '+str(allmassIDs[0].index(grp1[m])))
            designmatrix[rowcounter, allmassIDs.index(grp1[m])] = 1
        grp2 = entry[1].split('+')
        for m in range(len(grp2)):
            #log.debug('mass '+grp2[m]+' is in position '+str(allmassIDs[0].index(grp2[m])))
            designmatrix[rowcounter, allmassIDs.index(grp2[m])] = -1
        differences[rowcounter] = entry[2]
        residuals[rowcounter] = entry[3]
        uncerts[rowcounter] = entry[4]
        rowcounter += 1
for std in scheme_std['std weight ID']:
    designmatrix[rowcounter, allmassIDs.index(std)] = 1
    rowcounter += 1

# Check
print(designmatrix)

differences = np.append(differences, scheme_std['std mass values'])     # corresponds to Y, in g
residuals = np.append(residuals, scheme_std['std residuals'])           # not used for the following calculation
uncerts = np.append(uncerts, scheme_std['std uncerts'])                 # balance uncertainties in ug

print(differences)
print(residuals)
print(uncerts)

# Calculate least squares solution
# Following the mathcad example in Tech proc MSLT.M.001.008

x = designmatrix
xT = designmatrix.T

psi_y = np.diag(uncerts**2) # variance-covariance matrix
# TODO: work out what this is for sure!
psi_y_inv = np.linalg.inv(psi_y)

psi_b_inv = np.linalg.multi_dot([xT, psi_y_inv, x])
psi_b = np.linalg.inv(psi_b_inv)

b = np.linalg.multi_dot([psi_b, xT, psi_y_inv, differences])
log.info('Mass values are: '+str(b))

    # calculate the residuals, variance and variance-covariance matrix:
r0 = (differences - np.dot(x, b))*1e6 # convert from g to ug
log.info('R0 = '+str(r0))

# TODO: do something akin to buoyancy correction...

summarytable = np.empty((num_unknowns, 5), object)
for i in range(num_unknowns):
    summarytable[i, 0] = allmassIDs[i]
    if i < num_client_masses:
        summarytable[i, 1] = 'Client'
    elif i >= num_client_masses + num_check_masses:
        summarytable[i, 1] = 'Standard'
    else:
        summarytable[i, 1] = 'Check'

    summarytable[i, 2] = b[i]
    #summarytable[i, 3] = r0[i] # nope, not the residual

print(summarytable)

final_mass_values['Mass values from least squares solution'] = summarytable.tolist()

finalmasscalc.create_subgroup('2: Least Squares Data')
finalmasscalc.add_dataset(final_mass_values, '2: Least Squares Data')

'''

xTx_inv = np.linalg.inv(np.dot(xT, self.matrices[drift]))





residuals[drift] = self.y_col - np.dot(self.matrices[drift], self.b[drift])


var = np.dot(self.residuals[drift].T, self.residuals[drift]) / (self.num_readings - self.num_wtgrps - self._driftorder[drift])
log.debug('variance, \u03C3\u00b2, for', drift, 'is:',var.item(0))
self.stdev[drift] = "{0:.5g}".format(np.sqrt(var.item(0)))
log.debug('residual standard deviation, \u03C3, for', drift, 'is:', self.stdev[drift])

self.varcovar[drift] = np.multiply(var, xTx_inv)
log.debug('variance-covariance matrix, C =', self.varcovar[drift],
          'for', str(self.num_wtgrps),'item(s), and', drift, 'correction')
          
          
          '''