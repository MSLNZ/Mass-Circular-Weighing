"""
Use a Mettler Toledo balance with weight handler to perform a repeatability check
"""
import sys
import os
from time import sleep, perf_counter_ns
import numpy as np
import pandas as pd

from msl.qt import application, excepthook

from mass_circular_weighing.configuration import Configuration
from mass_circular_weighing.constants import admin_default

sys.excepthook = excepthook
gui = application()

cfg = Configuration(admin_default)

# bal_alias = 'XPE505C'
# bal_alias = 'AX10005'
bal_alias = 'AX1006'
bal, mode = cfg.get_bal_instance(bal_alias)

## Check balance set-up
print(bal.unit)
print(bal.mode)
print('aw' in bal.mode)
print(bal.stable_wait)
bal.identify_handler()
print(bal.get_serial())

bal.get_status()
print("Handler in position {}, {} position".format(bal.hori_pos, bal.lift_pos))


# pos = 2
# bal.move_to(pos)

# sleep(3600)

# bal.zero_bal()
# sleep(3)
# bal.scale_adjust()
# sleep(3)


def do_repeatability_ab(pos_a, pos_b, n_loadings=5):
    a_s = []
    b_s = []
    times = []

    # initial a
    bal.move_to(pos_a)
    print(f'mass a, #0')
    bal.lift_to('weighing', wait=True)
    a = bal.get_mass_stable('mass off')
    a_s.append(a)
    print(a)

    for i in range(n_loadings):
        # weigh b
        bal.move_to(pos_b)
        t0 = perf_counter_ns()
        print(f'mass b, #{i + 1}')
        bal.lift_to('weighing', wait=True)
        b = bal.get_mass_stable(f'mass b, #{i}')
        times.append((perf_counter_ns() - t0)/10**9)
        print(b, times[-1])
        b_s.append(b)

        # weigh a
        bal.move_to(pos_a)
        t0 = perf_counter_ns()
        print(f'mass a, #{i+1}')
        bal.lift_to('weighing', wait=True)
        a = bal.get_mass_stable(f'mass a, #{i}')
        print((perf_counter_ns() - t0)/10**9)
        a_s.append(a)
        print(a)

    # report results
    b_s.append(np.nan)
    times.append(np.nan)

    df = pd.DataFrame({
        "A's": a_s,
        "B's": b_s,
        "Times": times,
    })

    print(df)

    folder = r'I:\MSL\Private\Mass\Commercial Calibrations\2023\AX1006_ABA'  # folder of data
    filename = f'ABA_{pos_a}_{pos_b}.csv'
    save_path = os.path.join(folder, filename)
    df.to_csv(save_path)

    return df


positions = [1, 2, 3, 4]
pairs = [(positions[i], positions[j]) for i in range(4)
         for j in range(i+1, 4)]

for pair in pairs:
    pos_a = pair[1]
    pos_b = pair[0]
    print(pos_a, pos_b)
    do_repeatability_ab(pos_a=pos_a, pos_b=pos_b)

for pair in pairs:
    pos_a = pair[0]
    pos_b = pair[1]
    print(pos_a, pos_b)
    do_repeatability_ab(pos_a=pos_a, pos_b=pos_b)



## Do a practice weighing

# Allocate positions (needed for src.routines.run_circ_weigh do_circ_weighing)
# se = 'A Level'
# weighing = CircWeigh(se)
# print(weighing.wtgrps)
# positions = bal.initialise_balance(weighing.wtgrps, )
# print(positions)
# print(bal.positions)

# se = 'A B'
# nominal_mass = 500
# filename = cfg.client + '_' + str(nominal_mass)
# from other.do_new_weighing import do_new_weighing

# print(do_new_weighing(config, bal_alias, se, nominal_mass))

