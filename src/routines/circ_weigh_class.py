import numpy as np
from numpy.linalg import inv, multi_dot

""" This class uses matrix least squares analysis for circular weighing measurement sequences
For more information, see 'A General Approach to Comparisons in the Presence of Drift' """


class CircWeigh(object):
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
        self._sequences = {2: 5, 3: 4, 4: 3, 5: 3}  # key: number of weight groups in weighing, value: number of cycles
        self.wtgrps = scheme_entry.split()
        self.num_wtgrps = len(self.wtgrps)
        self.num_cycles = (self._sequences[self.num_wtgrps])

    def generate_design_matrices(self, times=[]):
        """Sets up design matrices for linear, quadratic and cubic drift

        Parameters
        ----------
        times : list
            list of times for each measurement.  Ideally these will be equally spaced.
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
        num_readings = self.num_cycles*self.num_wtgrps
        if times == [] or not all(times):  # Fill time as simple ascending array, [0,1,2,3...]
            times = np.arange(num_readings)
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

        self.dm0 = dm0_T.T
        self.dm1 = dm1_T.T
        self.dm2 = dm2_T.T
        self.dm3 = dm3_T.T



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