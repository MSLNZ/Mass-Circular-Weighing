from src.hdf5fileIO import HDF5Writer
from msl.equipment import Config
from src.equip.mdebalance import Balance
from src.routines.circ_weigh_class import CircWeigh
from time import perf_counter

# Specify balance to use for weighing, and weights in comparison
cfg = Config(r'C:\Users\r.hawke\PycharmProjects\Mass-Circular-Weighing\config.xml')
alias = 'MDE-demo'
bal = Balance(cfg, alias)
scheme1 = "1a 1b 1c 1d" # "1 1s 0.5+0.5s" #

# Specify where to save data
folder = r'C:\Users\r.hawke\PycharmProjects\Test_h5files'
filename = 'NumericalExample'
extn = '.hdf5'

# check ambient conditions ok for weighing
ambient = {'T': 20.2, 'RH': 49.5}  # TODO: link this to Omega logger
metadata = {'T (\xb0C)': ambient['T'], 'RH (%)': ambient['RH'], 'Balance': alias, 'Unit': bal.unit}

# set up for weighing:
file = HDF5Writer(folder, filename, extn)
group = file.get_item('2: Circular Weighings')  # could add subgroup for balance, and/or for scheme e.g. if re-run
print("Beginning circular weighing for scheme", scheme1)
weighing = CircWeigh(scheme1)
print('Number of weight groups in weighing =', weighing.num_wtgrps)
print('Number of cycles =', weighing.num_cycles)
print('Weight groups are positioned as follows:')
for i in range(weighing.num_wtgrps):
            print('Position',str(i+1)+':', weighing.wtgrps[i])
            metadata['grp'+str(i+1)] = weighing.wtgrps[i]

weighdata = group.require_dataset(scheme1, dtype='f', shape=(weighing.num_cycles, weighing.num_wtgrps))
for key, value in metadata.items():
    weighdata.attrs[key] = value

# do circular weighing:
t0 = perf_counter()
times = []
for cycle in range(weighing.num_cycles):
    for pos in range(weighing.num_wtgrps):
        mass = weighing.wtgrps[pos]
        bal.load_bal(mass)
        reading = bal.get_mass_instant()
        time = perf_counter() - t0
        times.append(time)
        weighdata[cycle,pos] = reading
        bal.unload_bal(mass)

weighdata.attrs['Timestamps'] = times
print(weighdata.attrs['Timestamps'])

# analyse circular weighing
weighing.generate_design_matrices()  # can include times here if evenly spaced