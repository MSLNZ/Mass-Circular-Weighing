import os
from msl.io import JSONWriter, read
from msl.equipment import Config
from src.equip.mdebalance import Balance
from src.routines.circ_weigh_class import CircWeigh
from time import perf_counter
import numpy as np

# TODO: obtain this info from user interface
# specify balance to use for weighing, and weights in comparison
cfg = Config(r'C:\Users\r.hawke\PycharmProjects\Mass-Circular-Weighing\config.xml')
alias = 'MDE-demo'
bal = Balance(cfg, alias)
metadata = {'Balance': alias, 'Unit': bal.unit}
scheme_entry = "3kn10+500mb+50mb+20mb 2ko+2kod 3kn11+500mb+50mb+20mb" # pressure calibration example
# "1 1s 0.5+0.5s" # "1a 1b 1c 1d"
nominal_mass = 4000 # nominal mass in g
identifier = 'run1'
new_weighing = False # select true to enter new data into weighing
# specify where to save data
url = r'C:\Users\r.hawke\PycharmProjects\test_json_files\PressureStandards4.json'
new_url = r'C:\Users\r.hawke\PycharmProjects\test_json_files\PressureStandards6.json'


if new_weighing: # check ambient conditions ok for weighing
    ambient_pre = {'T': 20.2, 'RH': 49.5} # TODO: link this to Omega logger
    metadata['T_pre (\xb0C)'] = ambient_pre['T']
    metadata['RH_pre (%)'] = ambient_pre['RH']

writer = JSONWriter()

# set up for weighing:
if os.path.isfile(url):
    root = read(url)
    writer.save(root=root, url=r'C:\Users\r.hawke\PycharmProjects\test_json_files\backup2.json')
    root.is_read_only = False
else:
    root = JSONWriter()

    circularweighings = root.require_group('Circular Weighings')
    schemefolder = circularweighings.require_group(scheme_entry)

print("Beginning circular weighing for scheme entry", scheme_entry)

weighing = CircWeigh(scheme_entry)
print('Number of weight groups in weighing =', weighing.num_wtgrps)
print('Number of cycles =', weighing.num_cycles)
print('Weight groups are positioned as follows:')
for i in range(weighing.num_wtgrps):
            print('Position',str(i+1)+':', weighing.wtgrps[i])
            metadata['grp'+str(i+1)] = weighing.wtgrps[i]

if new_weighing:
    data = np.empty(shape=(weighing.num_cycles, weighing.num_wtgrps, 2))
    weighdata = schemefolder.require_dataset('measurement_' + identifier, data=data)
    weighdata.add_metadata(**metadata)

    # do circular weighing:
    times = []
    for cycle in range(weighing.num_cycles):
        for pos in range(weighing.num_wtgrps):
            mass = weighing.wtgrps[pos]
            bal.load_bal(mass)
            reading = bal.get_mass_stable()
            print(times)
            if times == []:
                time = 0
                t0 = perf_counter()
            else:
                time = np.round((perf_counter() - t0)/60, 6) # elapsed time in minutes
            times.append(time)
            weighdata[cycle, pos, :] = [time, reading]
            writer.save(url=new_url, root=root, mode='w')
            bal.unload_bal(mass)
    weighdata.add_metadata(**{'Timestamps': np.round(times, 4)})
    writer.save(url=new_url, root=root, mode='w')
else:
    weighdata = root['Circular Weighings'][scheme_entry]['measurement_' + identifier]
    times = weighdata.metadata.get('Timestamps')
    print(times)

if new_weighing: # check ambient conditions ok during weighing
    ambient_post = {'T': 20.2, 'RH': 49.5} # TODO: get from Omega logger
    metadata['T_post (\xb0C)'] = ambient_post['T']
    metadata['RH_post (%)'] = ambient_post['RH']
    # TODO: check ambient conditions meet criteria for quality weighing

print(weighdata[:, :, 1])
# analyse circular weighing

weighing.generate_design_matrices(times)
# TODO: allow inclusion of actual times or fabricated times here?
drift = weighing.determine_drift(weighdata[:, :, 1]) # allows program to select optimum drift correction

print()
print('Residual std dev. for each drift order:')
print(weighing.stdev)

print()
print('Optimal drift correction for', drift, '(in', bal.unit, 'per reading):')
print(weighing.drift_coeffs(drift))

analysis = weighing.item_diff(drift)
# TODO: add here the balance uncertainty in final column (same for all)
#  - depends on value of nominal_mass and balance combination as per acceptance criteria
# TODO: check circular weighing against acceptance criteria for the balance

print()
print('Differences (in', bal.unit+'):')
print(weighing.grpdiffs)

# save analysis to json file
schemefolder = root['Circular Weighings'][scheme_entry]
weighanalysis = schemefolder.require_dataset('analysis_'+identifier,
    data=analysis, shape=(weighing.num_wtgrps, 1))

analysis_meta = {
    'Residual std devs, \u03C3': str(weighing.stdev),
    'Optimal drift': drift,
    'Mass unit': bal.unit,
    'Drift unit': bal.unit+' per '+weighing.trend,
}

for key, value in weighing.driftcoeffs.items():
    analysis_meta[key] = value

weighanalysis.add_metadata(**analysis_meta)

writer.save(url=new_url, root=root)

print()
print('Circular weighing complete')
