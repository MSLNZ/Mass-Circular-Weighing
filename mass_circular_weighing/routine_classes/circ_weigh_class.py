"""
This class uses matrix least squares analysis for circular weighing measurement sequences
For more information, see 'A General Approach to Comparisons in the Presence of Drift'

 Some outputs available within this class:
   - The design matrices, expected values, and variance-covariance matrix
   - Estimates of item differences and their standard deviations
   - Drift parameters and their standard deviations
"""
import numpy as np

from ..log import log

class CircWeigh(object):
    _sequences = {1: 10, 2: 5, 3: 4, 4: 3, 5: 3, 6: 3, 7: 3}  # key: number of weight groups in weighing, value: number of cycles
    _driftorder = {'no drift': 0, 'linear drift': 1, 'quadratic drift': 2, 'cubic drift': 3}
    _orderdrift = {0: 'no drift', 1 : 'linear drift', 2 : 'quadratic drift', 3 : 'cubic drift'}

    def __init__(self, scheme_entry):
        """Initialises a circular weighing for a single weighing in the scheme

        Parameters
        ----------
        scheme_entry : str
            the groups of weights to be weighed in order of weighing.
            groups of weights should be separated by a space; weights within a group should be separated by a + sign

        Examples
        ----------
        e.g. scheme_entry = "1a 1b 1c 1d" for four individual weights
        For a 5, 3, 2, 1 sequence, the four scheme entries are:
            scheme_entry1 = "5 5s 3+2"
            scheme_entry2 = "3 2s+1s 2+1"
            scheme_entry3 = "2 2s 1+1s"
            scheme_entry4 = "1 1s 0.5+0.5s"

        """
        self.wtgrps = scheme_entry.split()
        self.num_wtgrps = len(self.wtgrps)  # q in paper
        self.num_cycles = (self._sequences[self.num_wtgrps])
        self.num_readings = self.num_cycles*self.num_wtgrps  # p in paper
        self.matrices = {}
        self.t_matrices = {}
        self.b = {}
        self.residuals = {}
        self.stdev = {}
        self.varcovar = {}
        self.driftcoeffs = {}
        self.grpdiffs = {}

    def generate_design_matrices(self, times):
        """Sets up design matrices for linear, quadratic and cubic drift

        Parameters
        ----------
        times : list
            list of times for each measurement.  Ideally these will be equally spaced in time.
            Could be [0, 1, 2, 3, ...] or could be from 'Timestamps' attr of dataset

        Returns
        -------
        M1 : numpy array
            design matrix for linear drift
        M2 : numpy array
            design matrix for quadratic drift
        M3 : numpy array
            design matrix for cubic drift
        """
        if len(times) < self.num_readings:  # Fill time as simple ascending array, [0,1,2,3...]
            times = np.arange(self.num_readings)
            self.trend = 'reading'
        else:  # Ensure that time is a numpy array object.
            times = np.array(times)
            self.trend = 'minute'

        # Prepare matrices for each order of drift correction
        id = np.identity(self.num_wtgrps)
        dm0_T = id
        for i in range(self.num_cycles - 1):
            dm0_T = np.concatenate([dm0_T, id], axis=1)

        dm1_T = np.vstack((dm0_T, times))
        dm2_T = np.vstack((dm1_T, times**2))
        dm3_T = np.vstack((dm2_T, times**3))

        self.t_matrices = {'no drift': dm0_T, 'linear drift': dm1_T, 'quadratic drift': dm2_T, 'cubic drift': dm3_T}
        self.matrices = {'no drift': dm0_T.T, 'linear drift': dm1_T.T, 'quadratic drift': dm2_T.T, 'cubic drift': dm3_T.T}

        return self.t_matrices, self.matrices

    def determine_drift(self, dataset):
        """This method takes a dataset from a weighing and calculates expected values, residuals, standard deviation,
         and variance-covariance matrices for each of the drift correction options.
         All matrices are stored as instance variables.

        Parameters
        ----------
        dataset : array
            array from dataset object e.g. weighing[:,:]

        Returns
        -------
        h : int
            Order of drift correction which gives the smallest standard deviation

        """
        for drift, xT in self.t_matrices.items():
            self.expected_vals_drift(dataset, drift)

        return min(self.stdev, key=self.stdev.get)

    def expected_vals_drift(self, dataset, drift):
        """This method takes a dataset from a weighing and calculates expected values, residuals, standard deviation,
         and variance-covariance matrices for a given drift correction option.
         All matrices are stored as instance variables.

        Parameters
        ----------
        dataset : array
            array from dataset object e.g. weighing[:,:]
        drift : str
            allowed strings are keys in _driftorder
        """
        # convert data array to 1D list
        y_col = np.reshape(dataset, self.num_readings)
        xT = self.t_matrices[drift]

        # calculate vector of expected values
        xTx_inv = np.linalg.inv(np.dot(xT, self.matrices[drift]))
        log.debug('xTx_inv = ' + str(xTx_inv) + ' for ' + drift)
        self.b[drift] = np.linalg.multi_dot([xTx_inv, xT, y_col])
        log.debug('b = ' + str(self.b) + ' for ' + drift)

        # calculate the residuals, variance and variance-covariance matrix:
        self.residuals[drift] = y_col - np.dot(self.matrices[drift], self.b[drift])
        log.debug('residuals for ' + drift + ' are ' + str(self.residuals[drift]))

        var = np.dot(self.residuals[drift].T, self.residuals[drift]) / (
                    self.num_readings - self.num_wtgrps - self._driftorder[drift])
        log.debug('variance, \u03C3\u00b2, for ' + drift + ' is: ' + str(var.item(0)))
        self.stdev[drift] = np.round(np.sqrt(var.item(0)), 8)
        log.debug('residual standard deviation, \u03C3, for ' + drift + ' is: ' + str(self.stdev[drift]))

        self.varcovar[drift] = np.multiply(var, xTx_inv)
        log.debug('variance-covariance matrix, C = ' + str(self.varcovar[drift]) +
                  ' for ' + str(self.num_wtgrps) + ' items and ' + drift + ' correction')

    def drift_coeffs(self, drift):
        """For non-zero drift correction, this method takes the variance-covariance matrix from determine_drift,
        and outputs a dictionary of matrices of drift coefficients and their standard deviations.

        Parameters
        ----------
        drift : str
            choice of 'no drift', 'linear drift', 'quadratic drift', or 'cubic drift'

        Returns
        -------
        driftcoeffs : dict
            keys are drift orders as strings. Could be 'linear drift', 'quadratic drift', and/or 'cubic drift'
            values are matrices of drift coefficients and their standard deviations up to the maximum drift specified.
        """
        h = self._driftorder[drift]
        if h == 0:
            log.info('Optimal correction is for no drift')
        else:
            driftcoeff = np.zeros((h, 2))
            driftcoeff[:, 0] = self.b[drift][self.num_wtgrps:self.num_wtgrps + self._driftorder[drift]]

            d = np.diagonal(self.varcovar[drift])
            for i in range(h):
                driftcoeff[i, 1] = np.sqrt(d[i + self.num_wtgrps])
                self.driftcoeffs[self._orderdrift[i+1]] = "{0:.5g}".format(driftcoeff[i,0])+' ('+"{0:.3g}".format(driftcoeff[i,1])+')'

            log.debug('Matrix of drift coefficients and their standard deviations:\n'+str(driftcoeff))

        return self.driftcoeffs

    def item_diff(self, drift):
        """Calculates differences between sequential groups of weights in the circular weighing

        Parameters
        ----------
        drift : str
            choice of 'no drift', 'linear drift', 'quadratic drift', or 'cubic drift'

        Returns
        -------
        analysis : dataset
            dataset with headings '+ weight group', '- weight group',  'mass difference', 'residual'
        self.grpdiffs : dict
            keys are weight groups by position e.g. grp1 - grp2; grp2 - grp3 etc
            values are mass differences in set unit, with standard deviation in brackets
        """
        w_T = np.zeros((self.num_wtgrps, self.num_wtgrps + self._driftorder[drift]))
        for pos in range(self.num_wtgrps-1):
            w_T[pos, pos] = 1
            w_T[pos, pos + 1] = -1
        w_T[self.num_wtgrps - 1, self.num_wtgrps - 1] = 1
        w_T[self.num_wtgrps-1, 0] = -1

        w = w_T.T
        diffab = np.dot(w_T, self.b[drift])
        log.debug('Raw differences are\n'+str(diffab))
        vardiffab = np.linalg.multi_dot([w_T, self.varcovar[drift], w])
        stdev_diffab = np.sqrt(np.diag(vardiffab))

        for grp in range(self.num_wtgrps - 1):
            key = 'grp' + str(grp + 1) + ' - grp' + str(grp + 2)
            value = "{0:.5g}".format(diffab[grp]) + ' (' + "{0:.3g}".format(stdev_diffab[grp]) + ')'
            self.grpdiffs[key] = value

        self.grpdiffs['grp'+str(self.num_wtgrps)+' - grp1'] = \
            "{0:.5g}".format(diffab[self.num_wtgrps-1])+' ('+"{0:.3g}".format(stdev_diffab[self.num_wtgrps-1])+')'

        analysis = np.empty((self.num_wtgrps,),
                            dtype =[('+ weight group', object), ('- weight group', object),
                                    ('mass difference', 'float64'), ('residual', 'float64')]
                            )

        analysis['+ weight group'] = self.wtgrps
        analysis['- weight group'] = np.roll(self.wtgrps,-1)
        analysis['mass difference'] = diffab
        analysis['residual'] = stdev_diffab

        return analysis
