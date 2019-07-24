from src.application import Application
from src.routines.run_circ_weigh import *
from src.routines.collate_data import collate_data_from_json
from src.routines.final_mass_calc import final_mass_calc

import numpy as np


config = r'C:\Users\r.hawke\PycharmProjects\Mass-Circular-Weighing\config.xml'
### initialise application
app = Application(config)

client = 'DriftPaper'
folder = r'C:\Users\r.hawke\PycharmProjects\test_json_files\DriftPaper'  # use full path

### specify balance to use for weighing, and weights in comparison
scheme_entry = "1a 1b 1c 1d"
# "2000 2000MA 2000MB"  "1000 1000MA 1000MB"
# "3kn10+500mb+50mb+20mb 2ko+2kod 3kn11+500mb+50mb+20mb" # pressure calibration example
# "1 1s 0.5+0.5s" #
nominal_mass = 1000  # nominal mass in g
alias = 'MDE-demo'  # codename for balance

filename = client + '_' + str(nominal_mass) + '_rawdataonly'

run_id = 'run_1'
weighanalysis = analyse_old_weighing(folder, filename, scheme_entry, run_id, timed=False, drift='quadratic drift')#None)


assert weighanalysis.metadata.get('Residual std devs') == str(
    {'no drift': 4.30300283, 'linear drift': 0.39013124, 'quadratic drift': 0.41644618, 'cubic drift': 0.290016}
)

check_data = np.array([('1a', '1b',  -722.08054435, 0.34277932),
       ('1b', '1c', -2337.70520833, 0.34201342),
       ('1c', '1d',  -924.02987231, 0.34277932),
       ('1d', '1a',  3983.815625  , 0.35750859)],
      dtype=[('+ weight group', 'O'), ('- weight group', 'O'), ('mass difference', '<f8'), ('residual', '<f8')])

for i in range(4):
    for j in range(2):
        assert weighanalysis[i][j] == check_data[i][j]
        assert np.round(weighanalysis[i][j+2], 8) == np.round(check_data[i][j+2], 8)


#inputdata = collate_data_from_json(folder, filename, scheme_entry)  # gets data in g

#print(inputdata)

client_wt_IDs = ['1000']
check_wt_IDs = ['1000MB']
std_wt_IDs = ['1000MA']

check_wts = app.all_checks

i_s = app.all_stds['weight ID'].index('1000.000MA')
i_c = check_wts['weight ID'].index('1000.000MB')

std_masses = np.empty(len(std_wt_IDs), dtype={
    'names': ('std weight ID', 'std mass values (g)', 'std uncertainties (ug)'),
    'formats': (object, np.float, np.float)})

std_masses['std weight ID'] = std_wt_IDs
std_masses['std mass values (g)'] = app.all_stds['mass values (g)'][i_s]
std_masses['std uncertainties (ug)'] = app.all_stds['uncertainties (ug)'][i_s]

# print(std_masses)

filesavepath = 'savefilehere2.json'
# final_mass_calc(filesavepath, client, client_wt_IDs, check_wt_IDs, std_masses, inputdata)

