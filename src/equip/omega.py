import numpy as np
from src.constants import IN_DEGREES_C


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

    def get_t_rh(self):
        t1, rh1 = self.connection.temperature_humidity(probe=1, nbytes=12)
        t2, rh2 = self.connection.temperature_humidity(probe=2, nbytes=12)

        ambient = {
            'RH (%)': np.round((rh1 + rh2)/2, 3),
            'T'+IN_DEGREES_C: np.round((t1 + t2)/2, 3),
        }

        return ambient

    def get_t_rh_dp(self):
        t1, rh1, dp1 = self.connection.temperature_humidity_dewpoint(probe=1, nbytes=18)
        t2, rh2, dp2 = self.connection.temperature_humidity_dewpoint(probe=2, nbytes=18)

        ambient = {
            'RH (%)': np.round((rh1 + rh2)/2, 3),
            'T'+IN_DEGREES_C: np.round((t1 + t2)/2, 3),
            'DP'+IN_DEGREES_C: np.round((dp1 + dp2)/2, 3),
        }

        return ambient
