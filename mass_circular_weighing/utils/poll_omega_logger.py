"""
An entry point for testing the connection to Emile's LabVIEW server for ambient monitoring.
Note that calibrated values are returned by default.
"""
import logging

from mass_circular_weighing.constants import IN_DEGREES_C
from mass_circular_weighing.equip import LabEnviron64

logging.basicConfig(level=logging.DEBUG)


def poll_omega_logger(logger):
    """A method to quickly check if an omega logger is online

    Parameters
    ----------
    logger : str
       one of 'mass 1', 'mass 2', 'temperature 1'

    """
    dll = LabEnviron64()

    for sensor in [1, 2]:
        print('Collecting current ambient conditions from {}, sensor {}...'.format(logger, sensor))
        date_start, t_start, rh_start = dll.get_t_rh_now(logger, sensor)
        print("Temperature: {:.2f}{}, Relative humidity: {:.2f} %".format(t_start, IN_DEGREES_C, rh_start))
