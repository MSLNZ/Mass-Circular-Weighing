import os
from datetime import datetime
import numpy as np

from msl.io import JSONWriter, read

from .. import __version__
from ..log import log
from ..constants import REL_UNC, DELTA_STR, SUFFIX, MU_STR


def g_to_microg(num):
    return round(num*1e6, 3)


def filter_mass_set(masses: dict, inputdata: np.asarray) -> dict:
    """Takes a dictionary of masses and returns a copy with only the masses included in inputdata which will be
    used for the final mass calculation.
    Uses Set type key to determine which other keys are present in the masses dictionary.

    :param masses: mass set as stored in the Configuration class object (from AdminDetails)
    :param inputdata: numpy structured array;
        use format np.asarray(<data>, dtype =[('+ weight group', object), ('- weight group', object),
                                ('mass difference (g)', 'float64'), ('balance uncertainty (ug)', 'float64')])
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
    to_append = ['Shape/Mark', 'Nominal (g)', 'Weight ID',
                 'Expansion coeff (ppm/degC)', 'Vol (mL)', 'Vol unc (mL)',
                 'Density (kg/m3)', 'u_density (kg/m3)',
                 'Centre Height (mm)', 'u_height (mm)']
    if masses['Set type'] == 'Standard' or masses['Set type'] == 'Check':
        to_append += ['mass values (g)', 'uncertainties (' + MU_STR + 'g)', 'u_cal', 'u_drift']
    elif masses['Set type'] == 'Client':
        to_append += ['Container', 'u_mag (mg)']
    else:
        raise ValueError("Mass Set type not recognised: must be 'std' or 'client'")

    for key in to_append:
        masses_new[key] = []
    # add info for included masses only
    for i, item in enumerate(masses['Weight ID']):
        if item in weightgroups:
            for key in to_append:
                masses_new[key].append(masses[key][i])

    return masses_new


class FinalMassCalc(object):
    REL_UNC = REL_UNC       # relative uncertainty for not applying any buoyancy correction
    BUOYANCY_CORR = False   # include buoyancy corrections; requires measured air density and volumes of weights
    UNC_AIR_DENS = False    # include uncertainties in air density measurement
    UNC_VOL = False         # include uncertainties in volume estimation
    HEIGHT_CORR = False     # include corrections for differences in centre height of masses
    UNC_HEIGHT = False      # include uncertainties in centre height measurement
    TRUE_MASS = False       # work in true mass (rather than conventional mass)
    EDIT_CORR_COEFFS = False    # allow manual entry of correlation coefficients

    def __init__(self, folder: str | os.PathLike, client :str, client_masses: dict, check_masses: dict | None,
                 std_masses: dict, inputdata: np.asarray, nbc: bool = True, corr: np.array = np.identity(2)) -> None:
        """Initialises the calculation of mass values using matrix least squares methods. The final calculation is saved
        as a json file containing structured array of weight IDs, mass values, and uncertainties,
        along with a record of the input data and other relevant information

        :param folder: folder in which to save json file with output data; ideally an absolute path
        :param client: name of client
        :param client_masses: dict of client weights in inputdata
            Weight IDs are the strings used in the circular weighing scheme
        :param check_masses: dict of check weights in inputdata, as for std_masses, or None if no check weights are used
        :param std_masses: dict of standard weights in inputdata with keys as specified in admin_details.py.
            keys: 'MASSREF file', 'Sheet name', 'Set name', 'Set type', 'Set identifier', 'Calibrated',
            'Shape/Mark', 'Nominal (g)', 'Weight ID', 'mass values (g)', 'u_cal', 'uncertainties (' + MU_STR + 'g)',
            'u_drift', 'Density (kg/m3)', 'u_density (kg/m3)', 'Expansion coeff (ppm/degC)', 'Num weights', 'Vol (mL)',
            'Centre Height (mm)', 'Std Uncert (mm)'
            Weight ID values must match those used in the circular weighing scheme and inputdata
        :param inputdata: numpy structured array of input data
            use format np.asarray(<data>, dtype =[('+ weight group', object), ('- weight group', object),
            ('mass difference (g)', 'float64'), ('balance uncertainty (ug)', 'float64')])
        :param nbc: bool for whether to apply a default value for no buoyancy correction
        :param corr: 2x2 matrix of correlations between two standards (or the identity matrix for no correlations)
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
        self.all_wts = None
        self.allmassIDs = None

        self.num_obs = None
        self.leastsq_meta = {}

        self.y = np.empty(len(inputdata))       # corrected mass differences
        self.y_meas = np.empty(len(inputdata))  # apparent (measured) mass differences
        self.uncerts = np.empty(len(inputdata))
        self.psi_y = None

        self.designmatrix = None
        self.cmx1 = None
        self.cnx1 = None

        self.inputdatares = None
        self.b = None
        self.psi_bmeas = None
        self.std_uncert_b = None
        self.covariances = None

        self.summarytable = None

    def structure_jsonfile(self):
        """Creates relevant groups in the JSONWriter object"""
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

        # combine relevant parts of weight sets into a mega dictionary
        self.all_wts = ({'Weight ID': self.client_masses['Weight ID'], })
        for k in ['Expansion coeff (ppm/degC)', 'Vol (mL)', 'Vol unc (mL)', 'Nominal (g)', 'Centre Height (mm)', 'u_height (mm)']:
            try:
                self.all_wts[k] = self.client_masses[k]
            except KeyError:
                log.warning(f"{k} key not found in client mass set dictionary")
        for k, v in self.all_wts.items():
            if self.check_masses:
                self.all_wts[k] += self.check_masses[k]
            self.all_wts[k] += self.std_masses[k]

        self.all_wts['Set'] = ['Client']*self.num_client_masses
        if self.check_masses:
            self.all_wts['Set'] += ['Check'] * self.num_check_masses
        self.all_wts['Set'] += ['Standard'] * self.num_stds

        self.allmassIDs = self.all_wts['Weight ID']

        # note that stds are grouped last
        self.num_obs = len(self.inputdata) + self.num_stds
        self.leastsq_meta['Number of observations'] = self.num_obs
        self.leastsq_meta['Number of unknowns'] = self.num_unknowns
        self.leastsq_meta['Degrees of freedom'] = self.num_obs - self.num_unknowns

    def parse_inputdata_to_matrices(self, ):
        if self.all_wts is None:
            self.import_mass_lists()

        # Create design matrix and collect relevant data into differences and uncerts arrays
        designmatrix = np.zeros((self.num_obs, self.num_unknowns))
        rowcounter = 0

        log.debug('Input data: \n+ weight group, - weight group, mass difference (g), balance uncertainty (' + MU_STR + 'g)'
                  '\n' + str(self.inputdata))
        for entry in self.inputdata:
            log.debug("{} {} {} {}".format(entry[0], entry[1], entry[2], entry[3]))
            grp1 = entry[0].split('+')
            for mass in grp1:
                try:
                    i = self.all_wts['Weight ID'].index(mass)
                    log.debug(f'mass {mass} is in position {i}')
                    designmatrix[rowcounter, i] = 1
                except IndexError:
                    log.error("Index error raised at mass {}".format(mass))
            grp2 = entry[1].split('+')
            for mass in grp2:
                try:
                    i = self.all_wts['Weight ID'].index(mass)
                    log.debug(f'mass {mass} is in position {i}')
                    designmatrix[rowcounter, i] = -1
                except IndexError:
                    log.error("Index error raised at mass {}".format(mass))
            self.y_meas[rowcounter] = entry[2]
            self.uncerts[rowcounter] = entry[3]
            rowcounter += 1
        for std in self.std_masses['Weight ID']:
            designmatrix[rowcounter, self.all_wts['Weight ID'].index(std)] = 1
            rowcounter += 1

        self.y_meas = np.append(self.y_meas, self.std_masses['mass values (g)'])  # corresponds to Y, in g
        self.uncerts = np.append(self.uncerts, self.std_masses['uncertainties (' + MU_STR + 'g)'])  # balance uncertainties in ug
        log.debug('differences:\n' + str(self.y_meas))
        log.debug('uncerts:\n' + str(self.uncerts))

        self.designmatrix = designmatrix

        cmx1 = np.ones(self.num_client_masses + self.num_check_masses)  # from above, stds are added last
        self.cmx1 = np.append(cmx1, np.zeros(self.num_stds))  # 1's for unknowns, 0's for reference stds
        self.cnx1 = np.append(np.ones(len(self.inputdata)), np.zeros(self.num_stds))

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
                log.error(f"No comparisons in design matrix for {self.all_wts['Weight ID'][i]}")
                error_tally += 1

        if error_tally > 0:
            return False

        return True

    def calc_buoyancy_corrections(self, air_densities: np.ndarray) -> np.ndarray:
        """Calculate true mass differences by applying buoyancy corrections.
        NOTE: mass volumes are not corrected for temperature during weighing.

        :param air_densities:
        :return: buoyancy correction in g
        """
        # NOTE: volumes are not corrected for temperature during weighing

        a_d = np.append(air_densities, np.zeros(self.num_stds))
        # print('v', self.all_wts['Vol (mL)'])
        # print('xv', np.dot(self.designmatrix, self.all_wts['Vol (mL)']).T)
        # buoyancy correction in mg
        rho_x_v = (np.dot(self.designmatrix, self.all_wts['Vol (mL)']).T * a_d).T
        # print('rho_x_v', rho_x_v)

        tm_conv = - 0.00015*self.cnx1*self.y_meas

        return tm_conv + rho_x_v/1000

    def calc_height_corrections(self):
        """Calculate corrections to mass differences given heights for centres of mass of the weights.

        :return: correction in g, and the corresponding variance-covariance matrix in µg2
        """
        # height corr in mg
        m = np.array(self.all_wts['Nominal (g)'])
        z = np.array(self.all_wts['Centre Height (mm)'])
        x_c = (self.designmatrix.T * self.cnx1).T
        h_c = 0.3 * 1e-6 * np.dot(x_c, m * z)

        u_z = np.array(self.all_wts['u_height (mm)'])
        uuz = np.vstack(u_z) * np.hstack(u_z)
        r_z = np.identity(self.num_unknowns)
        psi_z = uuz * r_z
        # print('\npsi_z', psi_z)

        psi_z_contr = 9e-8 * np.dot(np.dot(x_c, m * psi_z * m.T), x_c.T)  # in µg2
        # print('\npsi_z_contr', psi_z_contr)

        return h_c/1000, psi_z_contr

    def apply_corrections_to_mass_differences(self, air_densities: np.ndarray):
        """Apply corrections to y_meas for buoyancy and COM heights,
           if class variables BUOYANCY_CORR and HEIGHT_CORR are set to True respectively.

        NOTE: call this method before :meth:'do_least_squares'

        :param air_densities: numpy array of measured air densities
        """
        buoy_corr = np.zeros(len(self.y_meas))
        if self.BUOYANCY_CORR:
            buoy_corr = self.calc_buoyancy_corrections(air_densities)

        height_corr = np.zeros(len(self.y_meas))

        if self.HEIGHT_CORR:    # include corrections for differences in centre height of masses
            height_corr = self.calc_height_corrections()[0]

        self.y = self.y_meas + buoy_corr + height_corr

    def cal_psi_y(self, unc_airdens: np.ndarray | None, air_densities: np.ndarray, rv: np.ndarray | None):
        """Calculate optional contributions to variance-covariance matrix from air density, volume, and COM heights.
        Select options by setting class variables UNC_AIR_DENS, UNC_VOL and/or UNC_HEIGHT to True.

        NOTE: call this method before :meth:'do_least_squares'

        :param unc_airdens: numpy array of uncertainties in measured air densities
        :param air_densities: numpy array of measured air densities
        :param rv: square correlation matrix for volumes, of size num_weights. Defaults to identity matrix.

        :return:
        """
        # The 'psi' variables in this method are variance-covariance matrices
        # U's are variances and R's are correlation coefficients
        ad_contr = 0
        vol_contr = 0
        height_contr = 0

        if self.UNC_AIR_DENS:  # include uncertainties in air density measurement
            u_ad = np.append(unc_airdens, np.zeros(self.num_stds))
            uua = np.vstack(u_ad) * np.hstack(u_ad)
            # print('uua', uua)
            ra = np.ones(len(uua))  # the air density measurements are fully correlated
            psi_airdens = uua * ra
            # print('psi_airdens', psi_airdens)
            xv = np.dot(self.designmatrix, self.all_wts['Vol (mL)'])
            # print('xv', xv)

            ad_contr = (xv * psi_airdens).T * xv * 1e6  # factor of 1e6 for µg2
            log.debug(f'Air density contribution to psi_y is {ad_contr}')
            # print('\nvAcomp', ad_contr)  # should be square of size b or num unknowns

        if self.UNC_VOL:   # include uncertainties in volume estimation
            # The uncertainty in the buoyancy correction to a measured mass difference due to an
            # uncertainty uV in the volume of a weight is ρa*uV, where the ambient air density ρa is assumed
            # to be 1.2 kg m-3 for the purposes of the uncertainty calculation. TP9, p7, item 4
            # print('Vol unc (mL)', self.all_wts['Vol unc (mL)'])
            uuv = np.vstack(self.all_wts['Vol unc (mL)']) * np.hstack(self.all_wts['Vol unc (mL)'])
            # print(uuv)

            # Correlations of volume uncertainties are bespoke. They could be uncorrelated,
            # or fully correlated for weights from the same set
            if rv is None:
                rv = np.identity(len(uuv))  # uncorrelated
            # print('set', self.all_wts['Set'])
            # print('rv', rv)
            psi_vol = uuv * rv
            # print('psi_vol', psi_vol)

            # xv = np.dot(self.designmatrix, self.all_wts['Vol (mL)'])
            # print('xv', xv)
            a_d = np.append(air_densities, np.zeros(self.num_stds))
            # print('air density vector', a_d)

            xvxt = np.dot(np.dot(self.designmatrix, psi_vol), self.designmatrix.T)
            vol_contr = (a_d * xvxt).T * a_d * 1e6  # factor of 1e6 for µg2
            # print('\nvVcomp', vol_contr)
            log.debug(f'Volume contribution to psi_y is {vol_contr}')  # should be square of size b or num unknowns

        if self.UNC_HEIGHT:
            height_contr = self.calc_height_corrections()[1]
            log.debug(f'Height contribution to psi_y is {height_contr}')
            # print('\nvZcomp', height_contr)

        self.psi_y = ad_contr + vol_contr + height_contr

    def do_least_squares(self):
        if not self.check_design_matrix():
            log.error("Error in design matrix. Calculation aborted")
            return False

        if not self.y.any():  # no corrections applied
            self.y = self.y_meas

        # Calculate least squares solution, following the mathcad example in Tech proc MSLT.M.001
        x = self.designmatrix
        xT = self.designmatrix.T

        # Hadamard product: element-wise multiplication
        uumeas = np.vstack(self.uncerts) * np.hstack(self.uncerts)    # becomes square matrix dim num_obs
        rmeas = np.identity(self.num_obs)
        # Replace bottom right corner with correlation matrix (which may just be the identity matrix)
        if self.corr is not None:
            rmeas[-2:, -2:] = self.corr
        log.info(f'rmeas matrix with correlations for stds if specified:\n{rmeas}')

        psi_y_hadamard = uumeas * rmeas  # Hadamard product is element-wise multiplication
        # print('covYmeas', psi_y_hadamard)

        if self.psi_y is not None:    # psi_y already includes contributions from buoyancy and volume corrections
            self.psi_y += psi_y_hadamard
        else:             # psi_y not yet defined
            self.psi_y = psi_y_hadamard
        # print('fmc psi_y', self.psi_y)

        psi_y_inv = np.linalg.inv(self.psi_y)

        psi_bmeas_inv = np.linalg.multi_dot([xT, psi_y_inv, x])
        self.psi_bmeas = np.linalg.inv(psi_bmeas_inv)

        self.b = np.linalg.multi_dot([self.psi_bmeas, xT, psi_y_inv, self.y])
        log.info('Mass values:\n'+str(self.b))

        r0 = (self.y - np.dot(x, self.b)) * 1e6               # residuals, converted from g to ug
        sum_residues_squared = np.dot(r0, r0)
        self.leastsq_meta['Sum of residues squared (' + MU_STR + 'g^2)'] = np.round(sum_residues_squared, 6)
        log.info('Residuals:\n'+str(np.round(r0, 4)))       # also save as column with input data for checking

        inputdata = self.inputdata
        inputdatares = np.empty((self.num_obs, 5), dtype=object)
            # dtype =[('+ weight group', object), ('- weight group', object), ('mass difference (g)', object),
            #         ('balance uncertainty (ug)', 'float64'), ('residual (ug)', 'float64')])
        inputdatares[0:len(inputdata), 0] = inputdata['+ weight group']
        inputdatares[len(inputdata):, 0] = self.std_masses['Weight ID']
        inputdatares[0:len(inputdata), 1] = inputdata['- weight group']
        inputdatares[:, 2] = self.y
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

    def cal_rel_unc_nbc(self):
        if self.b is None:
            self.do_least_squares()

        ### Uncertainty due to buoyancy ###
        # uncertainty due to no buoyancy correction
        reluncert = self.REL_UNC  # relative uncertainty in ppm for no buoyancy correction: typ 0.03 or 0.1 (ppm)
        unbc = reluncert * self.b * self.cmx1  # weighing uncertainty in ug as vector of length num_unknowns.
        # Note: TP has * 1e-6 for ppm which would give the uncertainty in g
        uunbc = np.vstack(unbc) * np.hstack(unbc)  # square matrix of dim num_obs
        rnbc = np.identity(self.num_unknowns)
        log.info(f'rnbc matrix (no correlations):\n{rnbc}')

        # Here the Hadamard product is taking the diagonal of the matrix
        psi_buoy = uunbc * rnbc  # psi_nbc_hadamard in TP Mathcad calculation  # square matrix of size num_unknowns

        self.leastsq_meta['Relative uncertainty for no buoyancy correction (ppm)'] = reluncert
        return psi_buoy

    def cal_rel_unc(self):
        if self.nbc:
            # get relative uncertainty due to no buoyancy correction
            psi_buoy = self.cal_rel_unc_nbc()
        else:
            # psi_y already includes other uncertainties if necessary
            psi_buoy = 0

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
        self.std_uncert_b = np.sqrt(np.diag(psi_b))  # variances are in the diagonal components

        # print(psi_b)
        self.covariances = 10**-12*psi_b  # convert from ug to g

        # det_varcovar_bmeas = np.linalg.det(psi_bmeas)
        # det_varcovar_nbc = np.linalg.det(psi_nbc_hadamard)
        # det_varcovar_b = np.linalg.det(psi_b)

    def make_summary_table(self, ):
        if self.std_uncert_b is None:
            self.cal_rel_unc()

        summarytable = np.empty((self.num_unknowns, 9), object)
        cov = 2
        for i in range(self.num_unknowns):
            summarytable[i, 1] = self.all_wts['Weight ID'][i]

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
                summarytable[i, 7] = self.check_masses['mass values (g)'][i - self.num_client_masses]
                delta = self.b[i] - self.check_masses['mass values (g)'][i - self.num_client_masses]
                summarytable[i, 8] = g_to_microg(delta)

            summarytable[i, 3] = np.round(self.b[i], 12)
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
        log.debug('Least squares solution:\nWeight ID, Set ID, Mass value (g), Uncertainty (' + MU_STR + 'g), '
                  '95% CI','Cov', "Reference value (g)", "Shift (" + MU_STR + 'g)\n' + str(summarytable))

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