"""
An entry point for testing the connection to Emile's LabVIEW server for ambient monitoring.
Note that calibrated values are returned by default.
"""
import logging
from time import sleep

from mass_circular_weighing.constants import IN_DEGREES_C
from mass_circular_weighing.equip import get_t_rh_now, get_aliases

logging.basicConfig(level=logging.DEBUG)


def poll_omega_logger(logger=None):
    """A method to quickly check if an omega logger is online

    Parameters
    ----------
    logger : str
       one of 'mass 1', 'mass 2', 'temperature 1'

    """
    if logger is None:
        omegas = get_aliases()
        aliases = [val for key, val in omegas.items()]
        print("Available omega loggers are: {}".format(", ".join(aliases)))
        logger = input("Enter alias of omega logger to poll: ")

    if logger:
        for sensor in [1, 2]:
            print('Collecting current ambient conditions from {}, sensor {}...'.format(logger, sensor))
            date_start, t_start, rh_start = None, None, None

            for i in range(15):  # in case the connection gets aborted by the software in the host machine
                date_start, t_start, rh_start = get_t_rh_now(logger, sensor=sensor)
                if t_start is not None:
                    print("Temperature: {:.2f}{}, Relative humidity: {:.2f} %".format(t_start, IN_DEGREES_C, rh_start))
                    break
                else:
                    sleep(1)

            if t_start is None:
                print(f"Unable to get ambient conditions from {logger}, sensor {sensor}")
