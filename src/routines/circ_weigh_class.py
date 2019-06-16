import numpy as np
from numpy.linalg import inv, multi_dot

""" This class uses matrix least squares analysis for circular weighing measurement sequences
For more information, see 'A General Approach to Comparisons in the Presence of Drift' """


class CircWeigh(object):
    _sequences = {2: 5, 3: 4, 4: 3, 5: 3}  # key: number of weight groups in weighing, value: number of cycles
    _driftorder = {'no drift': 0, 'linear drift': 1, 'quadratic drift': 2, 'cubic drift': 3}

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

    def generate_design_matrices(self, times=[]):
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
        if times == [] or not all(times):  # Fill time as simple ascending array, [0,1,2,3...]
            times = np.arange(self.num_readings)
        else:  # Ensure that time is a numpy array object.
            times = np.array(times)

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
            array from h5py dataset object e.g. weighing[:,:]

        Returns
        -------
        h : str
            Order of drift correction which gives the smallest standard deviation

        """
        # convert data array to 1D list
        self.y_col = np.reshape(dataset, self.num_readings)

        # calculate vector of expected values
        for drift, xT in self.t_matrices.items():
            self.xTx_inv = inv(np.dot(xT, self.matrices[drift]))
            # print('xTx_inv = ')
            # print(self.xTx_inv)
            self.b[drift] = multi_dot([self.xTx_inv, xT, self.y_col])
            # print('b = ')
            # print(self.b)

            # calculate the residuals, variance and variance-covariance matrix:
            self.residuals[drift] = self.y_col - np.dot(self.matrices[drift], self.b[drift])
            print('residuals = ')
            print(self.residuals[drift])

            var = np.dot(self.residuals[drift].T, self.residuals[drift]) / (self.num_readings - self.num_wtgrps - self._driftorder[drift])
            print('variance, \u03C3\u00b2 = ',var.item(0))
            self.stdev[drift] = np.sqrt(var.item(0))
            print('standard deviation, \u03C3 = ', self.stdev[drift])

            self.varcovar[drift] = np.multiply(var, self.xTx_inv)
            print('variance-covariance matrix, C = ')
            print(self.varcovar[drift])
            print('for', str(self.num_wtgrps),'item(s), and', drift, 'correction')

        return min(self.stdev, key=self.stdev.get)

''''''



'''   
Required inputs:
    scheme_entry = number of independent items being compared
    h = highest order of drift correction
    y_col = column vector of measured values or comparator readings in order taken
    t1 = row vector of times for each measurement
Function outputs:
    The design matrix 'X', a column vector 'b' of expected values, 
    and its variance-covariance matrix 'C'
    Estimates of item differences and their standard deviations
    Drift parameters and their standard deviations '''