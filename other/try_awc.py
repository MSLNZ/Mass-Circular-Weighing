"""
A helper script for testing integration of the Mettler balances with automatic weight changers
"""
import sys

from msl.qt import application, excepthook

from mass_circular_weighing.configuration import Configuration

sys.excepthook = excepthook
gui = application()

config = r"C:\Users\r.hawke\PycharmProjects\Mass-Circular-Weighing\examples\default_config.xml"
# config = r'C:\Users\r.hawke\Documents\20200324 useful files backup\2020python\vaisala_config.xml'  # change this of course!
cfg = Configuration(config)

bal_alias = 'AX10005'
# bal_alias = 'AX1006'
bal, mode = cfg.get_bal_instance(bal_alias)

print(bal.unit)
print('aw' in bal.mode)
print(bal.stable_wait)
bal.identify_handler()

bal.get_status()
print("Handler in position {}, {} position".format(bal.hori_pos, bal.lift_pos))

"""Check Vaisala"""
vai = bal.ambient_instance
vai.open_comms()
print(vai.get_readings())
vai.close_comms()
#
# bal.move_to(1)
# bal.lift_to('top')
# # bal.raise_handler()
#
# bal.move_to(2)
#
#
#
# bal.lift_to('weighing')
# bal.move_to(1)
# # bal.scale_adjust()
#
# #
#
# Test allocation of positions (needed for src.routines.run_circ_weigh do_circ_weighing)
# se = 'CC SR'
# weighing = CircWeigh(se)
# print(weighing.wtgrps)

# positions, pos_to_centre, repeats = bal.allocate_positions_and_centrings(weighing.wtgrps)
# print(positions, pos_to_centre, repeats)

# positions = bal.initialise_balance(weighing.wtgrps, )
# print(bal.positions)

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
