from src.hdf5fileIO import HDF5Writer
# TODO: change to using json file structure
from msl.equipment import Config
from src.equip.mdebalance import Balance
from src.routines.circ_weigh_class import CircWeigh
from time import perf_counter

# TODO: obtain this info from user interface
# specify balance to use for weighing, and weights in comparison
cfg = Config(r'C:\Users\r.hawke\PycharmProjects\Mass-Circular-Weighing\config.xml')
alias = 'MDE-demo'
bal = Balance(cfg, alias)
scheme1 = "3kn10+500mb+50mb+20mb 2ko+2kod 3kn11+500mb+50mb+20mb" # pressure calibration example
nominal_mass = 4000 # nominal mass in g
# "1 1s 0.5+0.5s" # "1a 1b 1c 1d"
identifier = 'run1'
new_weighing = False # select true to enter new data into weighing
# specify where to save data
folder = r'C:\Users\r.hawke\PycharmProjects\Test_h5files'
filename = 'PressureStandards1'
extn = '.hdf5'

# TODO: link this to Omega logger - also add check at end
# check ambient conditions ok for weighing
ambient = {'T': 20.2, 'RH': 49.5}
metadata = {'T (\xb0C)': ambient['T'], 'RH (%)': ambient['RH'], 'Balance': alias, 'Unit': bal.unit}

# set up for weighing:
file = HDF5Writer(folder, filename, extn)
group = file.get_item('2: Circular Weighings')
# TODO: work out how to liaise with the various balances to transfer data
scheme1folder = group.require_group(scheme1)

print("Beginning circular weighing for scheme", scheme1)

weighing = CircWeigh(scheme1)
print('Number of weight groups in weighing =', weighing.num_wtgrps)
print('Number of cycles =', weighing.num_cycles)
print('Weight groups are positioned as follows:')
for i in range(weighing.num_wtgrps):
            print('Position',str(i+1)+':', weighing.wtgrps[i])
            metadata['grp'+str(i+1)] = weighing.wtgrps[i]

weighdata = scheme1folder.require_dataset('measurement_'+identifier, dtype='f', shape=(weighing.num_cycles, weighing.num_wtgrps))
for key, value in metadata.items():
    weighdata.attrs[key] = value

# do circular weighing:

if new_weighing == True:
    times = []
    t0 = perf_counter()
    for cycle in range(weighing.num_cycles):
        for pos in range(weighing.num_wtgrps):
            mass = weighing.wtgrps[pos]
            bal.load_bal(mass)
            reading = bal.get_mass_stable()
            time = (perf_counter() - t0)/60  # elapsed time in minutes
            times.append(time)
            weighdata[cycle,pos] = reading
            # TODO: does Greg want the times in this array or are they ok as an attribute?
            bal.unload_bal(mass)

    times -= times[0]  # TODO: check this syntax is ok
    weighdata.attrs['Timestamps'] = times
    # TODO: format times sensibly...
else:
    times = weighdata.attrs['Timestamps']

# analyse circular weighing
weighing.generate_design_matrices(times)
# TODO: check if works when including actual times here
drift = weighing.determine_drift(weighdata[:,:]) # allows program to select optimum drift correction

print()
print('Residual std dev. for each drift order:')
print(weighing.stdev)

print()
print('Optimal drift correction for', drift, '(in', bal.unit, 'per reading):')
print(weighing.drift_coeffs(drift))

analysis = weighing.item_diff(drift)
# TODO: add here the balance uncertainty in final column (same for all) - depends on value of nominal_mass and balance combination as per acceptance criteria
# TODO: check circular weighing against acceptance criteria for the balance

print()
print('Differences (in', bal.unit+'):')
print(weighing.grpdiffs)

# save analysis to h5 dataset
# TODO: change to json
weighanalysis = scheme1folder.require_dataset('analysis_'+identifier,
    data=analysis, shape=(weighing.num_wtgrps, 1),
    dtype=[('+ weight group', object), ('- weight group', object), ('mass difference', 'float64'), ('std deviation', 'float64')])

weighanalysis.attrs['Residual std devs, \u03C3'] = str(weighing.stdev)
weighanalysis.attrs['Optimal drift'] = drift
weighanalysis.attrs['Mass unit'] = bal.unit
weighanalysis.attrs['Drift unit'] = bal.unit+' per '+weighing.trend

for key, value in weighing.driftcoeffs.items():
    weighanalysis.attrs[key] = value

print('Circular weighing complete')
