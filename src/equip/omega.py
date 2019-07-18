import numpy as np


class Omega(object):

    def __init__(self, record):
        """Initialise Omega Logger

        Parameters
        ----------
        record : equipment record object
            get via Application(config).equipment[alias]
            Requires an MSL.equipment config.xml file
        """
        self.record = record
        self.connection = self.record.connect()

    def get_ambient(self):
        size = 6

        rh1 = np.float(self.connection.query('*SRH', size=size))
        rh2 = np.float(self.connection.query('*SRH2', size=size))
        t1 = np.float(self.connection.query('*SRTC', size=size))
        t2 = np.float(self.connection.query('*SRTC2', size=size))
        dp1 = np.float(self.connection.query('*SRDC', size=size))
        dp2 = np.float(self.connection.query('*SRDC2', size=size))

        ambient = {
            'RH (%)': np.round((rh1 + rh2)/2, 3),
            'T (°C)': np.round((t1 + t2)/2, 3),
            'DP (°C)': np.round((dp1 + dp2)/2, 3),
        }
        print(ambient)

        return ambient