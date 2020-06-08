import os
from datetime import datetime
import numpy as np

from msl.io import JSONWriter, read

from .. import __version__
from ..log import log
from ..constants import REL_UNC, DELTA_STR, SUFFIX


def num_to_eng_format(num):
    for key, val in SUFFIX.items():
        renum = num/val
        if abs(renum) < 1000:
            eng_num = "{} {}".format(round(renum, 3), key)
            return eng_num


class FinalMassCalc(object):

    def __init__(self, folder, client, client_wt_IDs, check_masses, std_masses, inputdata, nbc=True, corr=None):
        """Initialises the calculation of mass values using matrix least squares methods

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

        self.client_wt_IDs = client_wt_IDs
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
        # get client weight IDs for metadata
        self.num_client_masses = len(self.client_wt_IDs)
        self.finalmasscalc['1: Mass Sets']['Client'].add_metadata(**{
            'Number of masses': self.num_client_masses,
            'weight ID': self.client_wt_IDs
        })
        # get number of check masses, if used, and save as dataset
        if not self.check_masses:
            self.num_check_masses = 0
            check_wt_IDs = []
            self.finalmasscalc['1: Mass Sets']['Check'].add_metadata(**{
                'Number of masses': self.num_check_masses,
                'Set Identifier': 'No check set'})
            log.info('Checks: None')
        else:
            check_wt_IDs = self.check_masses['weight ID']
            self.num_check_masses = make_stds_dataset('Checks', self.check_masses, self.finalmasscalc['1: Mass Sets']['Check'])

        # get number of standards, and save as dataset
        self.num_stds = make_stds_dataset('Standards', self.std_masses, self.finalmasscalc['1: Mass Sets']['Standard'])

        self.num_unknowns = self.num_client_masses + self.num_check_masses + self.num_stds
        log.info('Number of unknowns = '+str(self.num_unknowns))
        self.allmassIDs = np.append(np.append(self.client_wt_IDs, check_wt_IDs), self.std_masses['weight ID'])
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

        log.debug('Input data: \n+ weight group, - weight group, mass difference (g), balance uncertainty (ug)'
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
        for std in self.std_masses['weight ID']:
            designmatrix[rowcounter, np.where(self.allmassIDs == std)] = 1
            rowcounter += 1

        self.differences = np.append(self.differences, self.std_masses['mass values (g)'])  # corresponds to Y, in g
        self.uncerts = np.append(self.uncerts, self.std_masses['uncertainties (ug)'])  # balance uncertainties in ug
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
                log.error("No comparisons in design matrix for " + self.allmassIDs[i])
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
            for mass1 in self.std_masses['weight ID']:
                i = np.where(self.std_masses['weight ID'] == mass1)
                for mass2 in self.std_masses['weight ID']:
                    j = np.where(self.std_masses['weight ID'] == mass2)
                    rmeas[len(self.inputdata)+i[0], len(self.inputdata)+j[0]] = self.corr[i, j]
            log.debug('rmeas matrix includes correlations for stds:\n'+str(rmeas[:, len(self.inputdata)-self.num_obs:]))

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
        self.leastsq_meta['Sum of residues squared (ug^2)'] = np.round(sum_residues_squared, 6)
        log.debug('Residuals:\n'+str(np.round(r0, 4)))       # also save as column with input data for checking

        inputdata = self.inputdata
        inputdatares = np.empty((self.num_obs, 5), dtype=object)
            # dtype =[('+ weight group', object), ('- weight group', object), ('mass difference (g)', object),
            #         ('balance uncertainty (ug)', 'float64'), ('residual (ug)', 'float64')])
        inputdatares[0:len(inputdata), 0] = inputdata['+ weight group']
        inputdatares[len(inputdata):, 0] = self.std_masses['weight ID']
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
                log.warn("A residual for " + str(entry[0]) + ' - ' + str(entry[1]) + " is too large")

        if flag:
            self.leastsq_meta['Residuals greater than 2 balance uncerts'] = flag

    def cal_rel_unc(self, ):
        if self.b is None:
            self.do_least_squares()

        # uncertainty due to no buoyancy correction
        if self.nbc:
            cmx1 = np.ones(self.num_client_masses + self.num_check_masses)  # from above, stds are added last
            cmx1 = np.append(cmx1, np.zeros(self.num_stds))  # 1's for unknowns, 0's for reference stds

            reluncert = REL_UNC  # relative uncertainty in ppm for no buoyancy correction: typ 0.03 or 0.1
            unbc = reluncert * self.b * cmx1  # vector of length num_unknowns. TP wrongly has * 1e-6
            uunbc = np.vstack(unbc) * np.hstack(unbc)  # square matrix of dim num_obs
            rnbc = np.identity(self.num_unknowns)  # add off-diagonals for any correlations

            psi_nbc_hadamard = np.zeros((self.num_unknowns, self.num_unknowns))
            for i in range(self.num_unknowns):  # Here the Hadamard product is taking the diagonal of the matrix
                for j in range(self.num_unknowns):
                    if not rnbc[i, j] == 0:
                        psi_nbc_hadamard[i, j] = uunbc[i, j] * rnbc[i, j]

            psi_b = self.psi_bmeas + psi_nbc_hadamard

        else:
            psi_b = self.psi_bmeas
            reluncert = 0

        self.leastsq_meta['Relative uncertainty for no buoyancy correction (ppm)'] = reluncert

        self.std_uncert_b = np.sqrt(np.diag(psi_b))
        # det_varcovar_bmeas = np.linalg.det(psi_bmeas)
        # det_varcovar_nbc = np.linalg.det(psi_nbc_hadamard)
        # det_varcovar_b = np.linalg.det(psi_b)


    def make_summary_table(self, ):
        if self.std_uncert_b is None:
            self.cal_rel_unc()

        summarytable = np.empty((self.num_unknowns, 8), object)
        cov = 2
        for i in range(self.num_unknowns):
            summarytable[i, 1] = self.allmassIDs[i]

            if i < self.num_client_masses:
                summarytable[i, 2] = 'Client'
                summarytable[i, 7] = ""
            elif i >= self.num_client_masses + self.num_check_masses:
                summarytable[i, 2] = 'Standard'
                delta = self.std_masses['mass values (g)'][i - self.num_client_masses - self.num_check_masses] - self.b[i]
                summarytable[i, 7] = 'c.f. {} g; {} {}'.format(
                    self.std_masses['mass values (g)'][i - self.num_client_masses - self.num_check_masses],
                    DELTA_STR,
                    num_to_eng_format(delta),
                )
            else:
                summarytable[i, 2] = 'Check'
                delta = self.check_masses['mass values (g)'][i - self.num_client_masses] - self.b[i]
                summarytable[i, 7] = 'c.f. {} g; {} {}'.format(
                    self.check_masses['mass values (g)'][i - self.num_client_masses],
                    DELTA_STR,
                    num_to_eng_format(delta),
                )

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
        log.debug('Least squares solution:\nWeight ID, Set ID, Mass value (g), Uncertainty (ug), 95% CI\n' + str(
            summarytable))

        self.summarytable = summarytable


    def add_data_to_root(self, ):
        if self.summarytable is None:
            self.make_summary_table()

        leastsq_data = self.finalmasscalc.create_group('2: Matrix Least Squares Analysis', metadata=self.leastsq_meta)
        leastsq_data.create_dataset('Input data with least squares residuals', data=self.inputdatares,
                                    metadata={'headers':
                                                  ['+ weight group', '- weight group', 'mass difference (g)',
                                                   'balance uncertainty (ug)', 'residual (ug)']})
        leastsq_data.create_dataset('Mass values from least squares solution', data=self.summarytable,
                                    metadata={'headers':
                                                  ['Nominal (g)', 'Weight ID', 'Set ID',
                                                   'Mass value (g)', 'Uncertainty (ug)', '95% CI', 'Cov',
                                                   "c.f. Reference value (g)",
                                                   ]})

    def save_to_json_file(self, filesavepath=None, folder=None, client=None ):
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