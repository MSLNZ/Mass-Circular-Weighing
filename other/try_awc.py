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

print(bal.unit)
print('aw' in bal.mode)
print(bal.stable_wait)
bal.identify_handler()

bal.get_status()
print("Handler in position {}, {} position".format(bal.rot_pos, bal.lift_pos))



# bal.move_to(1)
# bal.lift_to('top')
# bal.raise_handler()

# bal.move_to(2)

# bal.move_to(1)

# bal.lift_to('weighing')
# bal.scale_adjust()

#
#
# Test allocation of positions (needed for src.routines.run_circ_weigh do_circ_weighing)
se = '2 2MA 2MB' #['2', "2MA", '2MB']#cfg.client_wt_IDs
weighing = CircWeigh(se)
print(weighing.wtgrps)

# positions, pos_to_centre, repeats = bal.allocate_positions_and_centrings(weighing.wtgrps)
# print(positions, pos_to_centre, repeats)

positions = bal.initialise_balance(weighing.wtgrps, )
print(bal.positions)

#
# print(bal._move_time())
# # testing for with balance:
#
# bal.move_to(2)
#
# print(bal.move_time)
# bal.time_move()
# print(bal.move_time)

bal.connection.disconnect()
