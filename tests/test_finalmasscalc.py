import os
import numpy as np

from msl.io import read_table

from mass_circular_weighing.configuration import Configuration
from mass_circular_weighing.constants import MU_STR, SUFFIX

from mass_circular_weighing.routines.final_mass_calc_class import FinalMassCalc
from mass_circular_weighing.routines.collate_data import collate_data_from_list

from mass_circular_weighing.gui.threads.masscalc_popup import filter_stds

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
config_for_test = os.path.join(ROOT_DIR, r'tests\samples\config_fmc.xml')
input_data_file_for_test = os.path.join(ROOT_DIR, r'tests\samples\final_mass_calc\LeastSquaresInputData_All.xlsx')

cfg = Configuration(config_for_test)

cfg.init_ref_mass_sets()
print(cfg.all_checks)
print(cfg.all_stds)

# test data
data_table = read_table(input_data_file_for_test, sheet='Sheet1')
print(data_table)



collated = np.empty(len(data_table),
                    dtype=[('+ weight group', object), ('- weight group', object),
                           ('mass difference (g)', 'float64'), ('balance uncertainty (' + MU_STR + 'g)', 'float64')])
collated['+ weight group'] = data_table[:,0]
collated['- weight group'] = data_table[:,1]
for i in range(len(data_table)):
    collated['mass difference (g)'][i] = float(data_table[i,2])
    collated['balance uncertainty (' + MU_STR + 'g)'][i] = float(data_table[i, 3])
print(collated)

client_wt_ids = cfg.client_wt_IDs.split()
checks = filter_stds(cfg.all_checks, collated)

print(client_wt_ids)
print(checks)