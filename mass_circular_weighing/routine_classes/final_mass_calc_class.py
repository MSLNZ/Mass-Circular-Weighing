import os
from datetime import datetime
import numpy as np

from msl.io import JSONWriter, read

from .. import __version__
from ..log import log
from ..constants import REL_UNC, DELTA_STR, SUFFIX, MU_STR


def num_to_eng_format(num):
    for key, val in SUFFIX.items():
        renum = num/val
        if abs(renum) < 1000:
            eng_num = "{} {}".format(round(renum, 3), key)
            return eng_num


def g_to_microg(num):
    return round(num*1e6, 3)


def filter_mass_set(masses, inputdata):
    """Takes a set of masses and returns a copy with only the masses included in the data which will be
    input into the final mass calculation.
    Uses Set type key to determine which other keys are present in the masses dictionary.

    Parameters
    ----------
    masses : dict
        mass set as stored in the Configuration class object (from AdminDetails)
    inputdata : numpy structured array
        use format np.asarray(<data>, dtype =[('+ weight group', object), ('- weight group', object),
                                ('mass difference (g)', 'float64'), ('balance uncertainty (ug)', 'float64')])
    Returns
    -------
    dict of only the masses which appear in inputdata
    """
    weightgroups = []
    for i in np.append(inputdata['+ weight group'], inputdata['- weight group']):
        if '+' in i:
            for j in i.split('+'):
                weightgroups.append(j)
        else:
            weightgroups.append(i)

    # create copy of masses with empty mass lists
    masses_new = dict()
    for key, val in masses.items():
        masses_new[key] = val
    if masses['Set type'] == 'Standard' or masses['Set type'] == 'Check':
        to_append = ['Shape/Mark', 'Nominal (g)', 'Weight ID', 'mass values (g)', 'u_cal', 'uncertainties (' + MU_STR + 'g)', 'u_drift']
    elif masses['Set type'] == 'Client':
        to_append = ['Weight ID', 'Nominal (g)', 'Shape/Mark', 'Container',
                     'u_mag (mg)', 'Density (kg/m3)', 'u_density (kg/m3)']
    else:
        log.error("Mass Set type not recognised: must be 'std' or 'client'")
        return None

    for key in to_append:
        masses_new[key] = []
    # add info for included masses only
    for i, item in enumerate(masses['Weight ID']):
        if item in weightgroups:
            for key in to_append:
                masses_new[key].append(masses[key][i])

    return masses_new


class FinalMassCalc(object):
    REL_UNC = REL_UNC

    def __init__(self, folder, client, client_masses, check_masses, std_masses, inputdata, nbc=True, corr=None):
        """Initialises the calculation of mass values using matrix least squares methods

        Parameters
        ----------
        folder : url
            folder in which to save json file with output data; ideally an absolute path
        client : str
            name of client
        client_masses : dict
            dict of client weights
            Weight IDs are the strings used in the circular weighing scheme
        check_masses : dict or None
            dict of check weights as for std_masses, or None if no check weights are used
        std_masses : dict
            keys: 'MASSREF file', 'Sheet name', 'Set name', 'Set type', 'Set identifier', 'Calibrated',
            'Shape/Mark', 'Nominal (g)', 'Weight ID', 'mass values (g)', 'u_cal', 'uncertainties (' + MU_STR + 'g)',
            'u_drift'
            Weight ID values must match those used in the circular weighing scheme
        inputdata : numpy structured array
            use format np.asarray(<data>, dtype =[('+ weight group', object), ('- weight group', object),
            ('mass difference (g)', 'float64'), ('balance uncertainty (ug)', 'float64')])

        Returns
        -------
        json file containing structured array of weight IDs, mass values, and uncertainties,
        along with a record of the input data and other relevant information
        """
        self.folder = folder
        self.client = client
        self.filesavepath = os.path.join(folder, client + '_finalmasscalc.json')

        metadata = {
            'Program Version': __version__,
            'Timestamp': datetime.now().isoformat(sep=' ', timespec='minutes'),
            "Client": client
        }

        self.finalmasscalc = JSONWriter(metadata=metadata)
        self.structure_jsonfile()

        self.client_masses = client_masses
        self.client_wt_IDs = client_masses["Weight ID"]
        self.check_masses = check_masses
        self.std_masses = std_masses
        self.inputdata = inputdata
        self.nbc = nbc
        self.corr = corr

        self.num_client_masses = None
        self.num_check_masses = None
        self.num_stds = None
        self.num_unknowns = None
        self.allmassIDs = None

        self.num_obs = None
        self.leastsq_meta = {}

        self.differences = np.empty(len(inputdata))
        self.uncerts = np.empty(len(inputdata))

        self.designmatrix = None

        self.inputdatares = None
        self.b = None
        self.psi_bmeas = None
        self.std_uncert_b = None

        self.summarytable = None

    def structure_jsonfile(self):
        "Creates relevant groups in JSONWriter object"
        mass_sets = self.finalmasscalc.require_group('1: Mass Sets')
        mass_sets.require_group('Client')
        mass_sets.require_group('Check')
        mass_sets.require_group('Standard')

    def import_mass_lists(self, ):
        # import lists of masses from supplied info
        log.info('Beginning mass calculation for the following client masses:\n' + str(self.client_wt_IDs))
        # get client Weight IDs for metadata
        self.num_client_masses = len(self.client_wt_IDs)
        self.finalmasscalc['1: Mass Sets']['Client'].add_metadata(**{
            'Number of masses': self.num_client_masses,
            'Weight ID': self.client_wt_IDs
        })
        # get number of check masses, if used, and save as dataset
        if not self.check_masses:
            self.num_check_masses = 0
            check_wt_IDs = []
            self.finalmasscalc['1: Mass Sets']['Check'].add_metadata(**{
                'Number of masses': self.num_check_masses,
                'Set identifier': 'No check set'})
            log.info('Checks: None')
        else:
            check_wt_IDs = self.check_masses['Weight ID']
            self.num_check_masses = make_stds_dataset('Checks', self.check_masses, self.finalmasscalc['1: Mass Sets']['Check'])

        # get number of standards, and save as dataset
        self.num_stds = make_stds_dataset('Standards', self.std_masses, self.finalmasscalc['1: Mass Sets']['Standard'])

        self.num_unknowns = self.num_client_masses + self.num_check_masses + self.num_stds
        log.info('Number of unknowns = '+str(self.num_unknowns))
        self.allmassIDs = np.append(np.append(self.client_wt_IDs, check_wt_IDs), self.std_masses['Weight ID'])
        # note that stds are grouped last
        self.num_obs = len(self.inputdata) + self.num_stds
        self.leastsq_meta['Number of observations'] = self.num_obs
        self.leastsq_meta['Number of unknowns'] = self.num_unknowns
        self.leastsq_meta['Degrees of freedom'] = self.num_obs - self.num_unknowns

    def parse_inputdata_to_matrices(self, ):
        if self.allmassIDs is None:
            self.import_mass_lists()
        # Create design matrix and collect relevant data into differences and uncerts arrays
        designmatrix = np.zeros((self.num_obs, self.num_unknowns))
        rowcounter = 0

        log.debug('Input data: \n+ weight group, - weight group, mass difference (g), balance uncertainty (' + MU_STR + 'g)'
                  '\n' + str(self.inputdata))
        for entry in self.inputdata:
            log.debug("{} {} {} {}".format(entry[0], entry[1], entry[2], entry[3]))
            grp1 = entry[0].split('+')
            for m in range(len(grp1)):
                try:
                    log.debug('mass ' + grp1[m] + ' is in position ' + str(np.where(self.allmassIDs == grp1[m])[0][0]))
                    designmatrix[rowcounter, np.where(self.allmassIDs == grp1[m])] = 1
                except IndexError:
                    log.error("Index error raised at mass {}".format(grp1[m]))
            grp2 = entry[1].split('+')
            for m in range(len(grp2)):
                log.debug('mass ' + grp2[m] + ' is in position ' + str(np.where(self.allmassIDs == grp2[m])[0][0]))
                designmatrix[rowcounter, np.where(self.allmassIDs == grp2[m])] = -1
            self.differences[rowcounter] = entry[2]
            self.uncerts[rowcounter] = entry[3]
            rowcounter += 1
        for std in self.std_masses['Weight ID']:
            designmatrix[rowcounter, np.where(self.allmassIDs == std)] = 1
            rowcounter += 1

        self.differences = np.append(self.differences, self.std_masses['mass values (g)'])  # corresponds to Y, in g
        self.uncerts = np.append(self.uncerts, self.std_masses['uncertainties (' + MU_STR + 'g)'])  # balance uncertainties in ug
        log.debug('differences:\n' + str(self.differences))
        log.debug('uncerts:\n' + str(self.uncerts))

        self.designmatrix = designmatrix

    def check_design_matrix(self,):
        if self.designmatrix is None:
            self.parse_inputdata_to_matrices()
        # double checks that all columns in the design matrix contain at least one non-zero value
        error_tally = 0
        for i in range(self.num_unknowns):
            sum = 0
            for r in range(self.num_obs):
                sum += self.designmatrix[r, i] ** 2
            if not sum:
                log.error(f"No comparisons in design matrix for {self.allmassIDs[i]}")
                error_tally += 1

        if error_tally > 0:
            return False

        return True

    def do_least_squares(self):
        if not self.check_design_matrix():
            log.error("Error in design matrix. Calculation aborted")
            return False

        # Calculate least squares solution, following the mathcad example in Tech proc MSLT.M.001.008
        x = self.designmatrix
        xT = self.designmatrix.T

        # Hadamard product: element-wise multiplication
        uumeas = np.vstack(self.uncerts) * np.hstack(self.uncerts)    # becomes square matrix dim num_obs

        rmeas = np.identity(self.num_obs)
        if type(self.corr) == np.ndarray:                        # Add off-diagonal terms for correlations
            for mass1 in self.std_masses['Weight ID']:
                i = np.where(self.std_masses['Weight ID'] == mass1)
                for mass2 in self.std_masses['Weight ID']:
                    j = np.where(self.std_masses['Weight ID'] == mass2)
                    rmeas[len(self.inputdata)+i[0], len(self.inputdata)+j[0]] = self.corr[i, j]
            log.debug(f'rmeas matrix includes correlations for stds:\n{rmeas[:, len(self.inputdata)-self.num_obs:]}')

        psi_y_hadamard = np.zeros((self.num_obs, self.num_obs))       # Hadamard product is element-wise multiplication
        for i in range(self.num_obs):
            for j in range(self.num_obs):
                if not rmeas[i, j] == 0:
                    psi_y_hadamard[i, j] = uumeas[i, j] * rmeas[i, j]

        psi_y_inv = np.linalg.inv(psi_y_hadamard)

        psi_bmeas_inv = np.linalg.multi_dot([xT, psi_y_inv, x])
        self.psi_bmeas = np.linalg.inv(psi_bmeas_inv)

        self.b = np.linalg.multi_dot([self.psi_bmeas, xT, psi_y_inv, self.differences])
        log.debug('Mass values before corrections:\n'+str(self.b))

        r0 = (self.differences - np.dot(x, self.b))*1e6               # residuals, converted from g to ug
        sum_residues_squared = np.dot(r0, r0)
        self.leastsq_meta['Sum of residues squared (' + MU_STR + 'g^2)'] = np.round(sum_residues_squared, 6)
        log.debug('Residuals:\n'+str(np.round(r0, 4)))       # also save as column with input data for checking

        inputdata = self.inputdata
        inputdatares = np.empty((self.num_obs, 5), dtype=object)
            # dtype =[('+ weight group', object), ('- weight group', object), ('mass difference (g)', object),
            #         ('balance uncertainty (ug)', 'float64'), ('residual (ug)', 'float64')])
        inputdatares[0:len(inputdata), 0] = inputdata['+ weight group']
        inputdatares[len(inputdata):, 0] = self.std_masses['Weight ID']
        inputdatares[0:len(inputdata), 1] = inputdata['- weight group']
        inputdatares[:, 2] = self.differences
        inputdatares[:, 3] = self.uncerts
        inputdatares[:, 4] = np.round(r0, 3)

        self.inputdatares = inputdatares

    def check_residuals(self):
        if self.inputdatares is None:
            self.do_least_squares()

        # check that the calculated residuals are less than twice the balance uncertainties in ug
        flag = []
        for entry in self.inputdatares:
            if np.absolute(entry[4]) > 2 * entry[3]:
                flag.append(str(entry[0]) + ' - ' + str(entry[1]))
                log.warn(f"A residual for {entry[0]} - {entry[1]} is too large")

        if flag:
            self.leastsq_meta['Residuals greater than 2 balance uncerts'] = flag

    def cal_rel_unc(self, ):
        if self.b is None:
            self.do_least_squares()

        # Note: the 'psi' variables in this method are variance-covariance matrices

        ### Uncertainty due to buoyancy ###
        psi_buoy = np.zeros((self.num_unknowns, self.num_unknowns))
        # uncertainty due to no buoyancy correction
        if self.nbc:
            cmx1 = np.ones(self.num_client_masses + self.num_check_masses)  # from above, stds are added last
            cmx1 = np.append(cmx1, np.zeros(self.num_stds))  # 1's for unknowns, 0's for reference stds

            reluncert = self.REL_UNC  # relative uncertainty in ppm for no buoyancy correction: typ 0.03 or 0.1 (ppm)
            unbc = reluncert * self.b * cmx1  # weighing uncertainty in ug as vector of length num_unknowns.
            # Note: TP has * 1e-6 for ppm which would give the uncertainty in g
            uunbc = np.vstack(unbc) * np.hstack(unbc)  # square matrix of dim num_obs
            rnbc = np.identity(self.num_unknowns)  # TODO: add off-diagonals for any correlations

            # psi_nbc_hadamard = np.zeros((self.num_unknowns, self.num_unknowns))
            for i in range(self.num_unknowns):  # Here the Hadamard product is taking the diagonal of the matrix
                for j in range(self.num_unknowns):
                    if not rnbc[i, j] == 0:
                        psi_buoy[i, j] = uunbc[i, j] * rnbc[i, j]  # psi_nbc_hadamard in TP Mathcad calculation

        # TODO: buoyancy correction (not currently implemented)
        # The uncertainty in the buoyancy correction to a measured mass difference due to an
        # uncertainty uV in the volume of a weight is ρa*uV, where the ambient air density ρa is assumed
        # to be 1.2 kg m-3 for the purposes of the uncertainty calculation. TP9, p7, item 4
        else:
            reluncert = 0

        self.leastsq_meta['Relative uncertainty for no buoyancy correction (ppm)'] = reluncert

        ### Uncertainty due to magnetic effects ###
        # magnetic uncertainty
        psi_mag = np.zeros((self.num_unknowns, self.num_unknowns))
        for i, umag in enumerate(self.client_masses['u_mag (mg)']):
            if umag is not None:
                psi_mag[i, i] = (umag*1000)**2       # convert u_mag from mg to ug
                log.info(f"Uncertainty for {self.client_wt_IDs[i]} includes magnetic uncertainty of {umag} mg")

        ### Total uncertainty ###
        # Add all the squared uncertainty components and square root them to get the final std uncertainty
        psi_b = self.psi_bmeas + psi_buoy + psi_mag
        self.std_uncert_b = np.sqrt(np.diag(psi_b))  # there should only be diagonal components anyway
        # (TODO: check if valid with correlations)

        # det_varcovar_bmeas = np.linalg.det(psi_bmeas)
        # det_varcovar_nbc = np.linalg.det(psi_nbc_hadamard)
        # det_varcovar_b = np.linalg.det(psi_b)

    def make_summary_table(self, ):
        if self.std_uncert_b is None:
            self.cal_rel_unc()

        summarytable = np.empty((self.num_unknowns, 9), object)
        cov = 2
        for i in range(self.num_unknowns):
            summarytable[i, 1] = self.allmassIDs[i]

            if i < self.num_client_masses:
                summarytable[i, 2] = 'Client'
                summarytable[i, 7] = ""
                summarytable[i, 8] = ""
            elif i >= self.num_client_masses + self.num_check_masses:
                summarytable[i, 2] = 'Standard'
                summarytable[i, 7] = self.std_masses['mass values (g)'][i - self.num_client_masses - self.num_check_masses]
                delta = self.b[i] - summarytable[i, 7]
                summarytable[i, 8] = g_to_microg(delta)
            else:
                summarytable[i, 2] = 'Check'
                delta = self.b[i] - self.check_masses['mass values (g)'][i - self.num_client_masses]
                summarytable[i, 7] = self.check_masses['mass values (g)'][i - self.num_client_masses]
                summarytable[i, 8] = g_to_microg(delta)

            summarytable[i, 3] = np.round(self.b[i], 9)
            if self.b[i] >= 1:
                nom = str(int(round(self.b[i], 0)))
            else:
                nom = "{0:.1g}".format(self.b[i])
            if 'e-' in nom:
                nom = 0
            summarytable[i, 0] = nom
            summarytable[i, 4] = np.round(self.std_uncert_b[i], 3)
            summarytable[i, 5] = np.round(cov * self.std_uncert_b[i], 3)
            summarytable[i, 6] = cov

        log.info('Found least squares solution')
        log.debug('Least squares solution:\nWeight ID, Set ID, Mass value (g), Uncertainty (' + MU_STR + 'g), 95% CI\n' + str(
            summarytable))

        self.summarytable = summarytable

    def add_data_to_root(self, ):
        if self.summarytable is None:
            self.make_summary_table()

        leastsq_data = self.finalmasscalc.create_group('2: Matrix Least Squares Analysis', metadata=self.leastsq_meta)
        leastsq_data.create_dataset('Input data with least squares residuals', data=self.inputdatares,
                                    metadata={'headers':
                                                  ['+ weight group', '- weight group', 'mass difference (g)',
                                                   'balance uncertainty (' + MU_STR + 'g)', 'residual (' + MU_STR + 'g)']})
        leastsq_data.create_dataset('Mass values from least squares solution', data=self.summarytable,
                                    metadata={'headers':
                                                  ['Nominal (g)', 'Weight ID', 'Set ID',
                                                   'Mass value (g)', 'Uncertainty (' + MU_STR + 'g)', '95% CI', 'Cov',
                                                   "Reference value (g)", "Shift (" + MU_STR + 'g)'
                                                   ]})

    def save_to_json_file(self, filesavepath=None, folder=None, client=None):
        if not filesavepath:
            filesavepath = self.filesavepath
        if not folder:
            folder = self.folder
        if not client:
            client = self.client

        # make a backup of any previous version, then save root object to json file
        make_backup(folder, client, filesavepath, )

        self.finalmasscalc.save(filesavepath, mode='w')

        log.info('Mass calculation saved to {!r}'.format(filesavepath))


def make_backup(folder, client, filesavepath, ):
    back_up_folder = os.path.join(folder, "backups")
    if os.path.isfile(filesavepath):
        existing_root = read(filesavepath)
        log.debug(back_up_folder)
        if not os.path.exists(back_up_folder):
            os.makedirs(back_up_folder)
        new_index = len(os.listdir(back_up_folder))  # counts number of files in backup folder
        new_file = os.path.join(back_up_folder, client + '_finalmasscalc_backup{}.json'.format(new_index))
        existing_root.read_only = False
        root = JSONWriter()
        root.set_root(existing_root)
        root.save(root=existing_root, file=new_file, mode='w', ensure_ascii=False)
        log.info('Backup of previous Final Mass Calc saved as {}'.format(new_file))


def make_stds_dataset(set_type, masses_dict, scheme):
    num_masses = len(masses_dict['Weight ID'])
    masses_dataarray = np.empty(num_masses, dtype=[
        ('Weight ID', object),
        ('Nominal (g)', float),
        ('mass values (g)', float),
        ('std uncertainties (' + MU_STR + 'g)', float)
    ])
    masses_dataarray['Weight ID'] = masses_dict['Weight ID']
    masses_dataarray['Nominal (g)'] = masses_dict['Nominal (g)']
    masses_dataarray['mass values (g)'] = masses_dict['mass values (g)']
    masses_dataarray['std uncertainties (' + MU_STR + 'g)'] = masses_dict['uncertainties (' + MU_STR + 'g)']

    scheme.add_metadata(**{
        'Number of masses': num_masses,
        'Set identifier': masses_dict['Set identifier'],
        'Calibrated': masses_dict['Calibrated'],
        'Weight ID': masses_dict['Weight ID'],
    })

    scheme.create_dataset('mass values', data=masses_dataarray)

    log.info(f"{set_type}: {masses_dict['Weight ID']}")

    return num_masses


'''Extra bits that aren't used at the moment
var = np.dot(r0.T, r0) / (num_obs - num_unknowns)
log.debug('variance, \u03C3\u00b2, is:'+str(var.item(0)))

stdev = "{0:.5g}".format(np.sqrt(var.item(0)))
log.debug('residual standard deviation, \u03C3, is:'+stdev)

varcovar = np.multiply(var, np.linalg.inv(np.dot(xT, x)))
log.debug('variance-covariance matrix, C ='+str(varcovar))

det_varcovar = np.linalg.det(varcovar)
log.debug('determinant of variance-covariance matrix, det C ='+str(det_varcovar))
'''