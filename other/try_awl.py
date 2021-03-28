import sys

from msl.qt import application, excepthook

from mass_circular_weighing.configuration import Configuration

sys.excepthook = excepthook
gui = application()

config = r'C:\Users\r.hawke\PycharmProjects\Mass-Circular-Weighing\examples\default_config.xml'  # change this of course!
cfg = Configuration(config)

bal_alias = 'XPE505C'
bal, mode = cfg.get_bal_instance(bal_alias)

## Check balance set-up
# print(bal.unit)
# print(bal.mode)
# bal.move_to(1)
# bal.zero_bal()

# Test allocation of positions (needed for src.routines.run_circ_weigh do_circ_weighing)
# se = 'A Level'
# weighing = CircWeigh(se)
# print(weighing.wtgrps)
# positions = bal.initialise_balance(weighing.wtgrps, )
# print(positions)
# print(bal.positions)

# test movement and weighing process
# bal.load_bal('A', 2)
# bal.get_mass_stable('A')
# bal.unload_bal('A', 2)
# bal.load_bal('Level', 3)
# bal.get_mass_stable('Level')
# bal.unload_bal('Level', 3)

# if you want to do a practice weighing
# se = 'A B'
# nominal_mass = 500
# filename = cfg.client + '_' + str(nominal_mass)
# from other.do_new_weighing import do_new_weighing
#
# print(do_new_weighing(config, bal_alias, se, nominal_mass))

