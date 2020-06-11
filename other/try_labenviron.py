import logging
from datetime import datetime

from mass_circular_weighing.equip import LabEnviron64


logging.basicConfig(level=logging.DEBUG)
dll = LabEnviron64()

m1 = 'mass 1'
m2 = 'mass 2'
t1 = 'temperature 1'


for logger in [m1, t1]:
    for sensor in [1, 2]:
        print('Initial ambient conditions: ' + logger + ', sensor '+ str(sensor))
        date_start, t_start, rh_start = dll.get_t_rh_now(logger, sensor)
        # t_start, rh_start = dll.get_t_rh_during(logger, sensor, datetime(2020, 3, 17))
        print(t_start, rh_start)



