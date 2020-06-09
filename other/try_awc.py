import sys

from msl.qt import application, excepthook

from mass_circular_weighing.configuration import Configuration
from mass_circular_weighing.routines.circ_weigh_class import CircWeigh


sys.excepthook = excepthook
gui = application()

config = r'C:\Users\r.hawke\PycharmProjects\Mass-Circular-Weighing\config.xml'  # change this of course!
cfg = Configuration(config)

bal_alias = 'AX10005'
# bal_alias = 'AX1006'
bal, mode = cfg.get_bal_instance(bal_alias)
#
print(bal.unit)
print('aw' in bal.mode)
# print(bal.stable_wait)
# bal.identify_handler()

# bal.move_to(1)
# bal.lift_to('top')
# bal.raise_handler()
# bal.get_status()

# bal.move_to(2)

# bal.move_to(1)

# bal.lift_to('weighing')
# bal.scale_adjust()

#
#
# Test allocation of positions (needed for src.routines.run_circ_weigh do_circ_weighing)
se = ['A', "B", 'C']#cfg.client_wt_IDs
# weighing = CircWeigh(se)
# print(weighing.wtgrps)
# positions = bal.allocate_positions(weighing.wtgrps, )
# print(positions)
# print(bal.positions)
#
# bal.time_move()
# # testing for with balance:
#
# bal.move_to(2)
#
# print(bal.move_time)
# bal.time_move()
# print(bal.move_time)

# bal.connection.disconnect()
