"""
Test communications with a aw_l Mettler Toledo balance by performing a repeatability check
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

bal_alias = 'XPE505C'
bal, mode = cfg.get_bal_instance(bal_alias)
bal.stable_wait = 40

## Check balance set-up
print(bal.unit)
print(bal.mode)
print(bal.get_serial())

# pos = 4
# bal.move_to(pos)

pos = 3
bal.move_to(pos)

# bal.zero_bal()
# sleep(3)
# bal.scale_adjust()
# sleep(3)


def do_repeatability_awl(n_loadings=11, stable_wait=40):
    zeroes = []
    masses = []
    times = []
    stability = []

    # initial zero
    bal.zero_bal()
    print(f'mass off, #0')
    z = bal._query("S")  #.get_mass_stable('mass off')
    b = bal.parse_mass_reading(z.split())
    zeroes.append(float(b))

    for i in range(n_loadings):
        # weigh mass
        bal.lift_to('weighing', wait=False)
        t0 = perf_counter_ns()
        print(f'mass on, #{i+1}')
        sleep(stable_wait)
        m = bal._query("SI")
        # m = bal._query("S")
        # m = bal.get_mass_stable(f'mass on, #{i}')
        times.append((perf_counter_ns() - t0)/10**9)
        print(times[-1])
        a = bal.parse_mass_reading(m.split())
        masses.append(float(a))
        stability.append(m.split()[1])
        print(m, stability[-1])

        # get zero
        bal.lift_to('top', wait=False)
        t0 = perf_counter_ns()
        print(f'mass off, #{i+1}')
        sleep(stable_wait)
        z = bal._query("SI")
        # z = bal._query("S")
        # z = bal.get_mass_stable('mass off')
        print(perf_counter_ns() - t0)
        b = bal.parse_mass_reading(z.split())
        zeroes.append(float(b))
        print(z)

    # report results
    print("Masses without zero drift")
    m_no_zero = [m - 0.5 * (zeroes[i] + zeroes[i + 1]) for i, m in enumerate(masses)]
    masses.append(np.nan)
    m_no_zero.append(np.nan)
    times.append(np.nan)
    stability.append(np.nan)

    df = pd.DataFrame({
        "Zeroes": zeroes,
        "Masses": masses,
        "Masses without zero drift": m_no_zero,
        "Times": times,
        "Stability": stability
    })

    print(df)

    folder = r'I:\MSL\Private\Mass\Commercial Calibrations\2023\505C_test'  # folder of data
    filename = f'test_wait_{stable_wait}s_SI.csv'
    save_path = os.path.join(folder, filename)
    df.to_csv(save_path)

    return df


## Do repeatability test
for wait in [30]: #, 40, 25, 35, 45]:  #[35, 80, 15, 90, 25, 75, 10, 65]:
    do_repeatability_awl(n_loadings=11, stable_wait=wait)  # extra loading to exercise the balance


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

