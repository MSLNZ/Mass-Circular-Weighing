from src.application import Application
from src.routines.run_circ_weigh import *
from src.routines.collate_data import collate_a_data_from_json
from src.routines.final_mass_calc import final_mass_calc



import numpy as np


config = r'C:\Users\r.hawke\PycharmProjects\Mass-Circular-Weighing\config.xml'
### initialise application
app = Application(config)

client = 'AsureQ_Mar'
folder = r'C:\Users\r.hawke\PycharmProjects\test_json_files\AsureQ_Mar'  # use full path

### specify balance to use for weighing, and weights in comparison
scheme_entry = "1000 1000MA 1000MB"
# "1000 1000MA 1000MB"
#
# "3kn10+500mb+50mb+20mb 2ko+2kod 3kn11+500mb+50mb+20mb" # pressure calibration example
# "1 1s 0.5+0.5s" # "1a 1b 1c 1d"
nominal_mass = 1000  # nominal mass in g
alias = 'MDE-demo'  # codename for balance


filename = client + '_' + str(nominal_mass) #+ '_' + run_id


#do_new_weighing(client, alias, folder, filename, scheme_entry, nominal_mass,
#        timed=False, drift='linear drift')

#analyse_old_weighing(folder, filename, scheme_entry, 'run_2', timed=False, drift='linear drift')
analyse_all_weighings_in_file(folder, filename, scheme_entry, timed=False, drift='linear drift')#None)

#inputdata, ok = collate_a_data_from_json(folder, filename, scheme_entry)  # gets data in g

#if not ok:
#    print('yelp!')
#    raise ValueError

client_wt_IDs = ['2000']
check_wt_IDs = ['2000MB']
std_wt_IDs = ['2000MA']

check_wts = app.all_checks

i_s = app.all_stds['weight ID'].index('2000.000MA')
i_c = check_wts['weight ID'].index('2000.000MB')

std_masses = np.empty(len(std_wt_IDs), dtype={
    'names': ('std weight ID', 'std mass values (g)', 'std uncertainties (ug)'),
    'formats': (object, np.float, np.float)})

std_masses['std weight ID'] = std_wt_IDs
std_masses['std mass values (g)'] = app.all_stds['mass values (g)'][i_s]
std_masses['std uncertainties (ug)'] = app.all_stds['uncertainties (ug)'][i_s]

filesavepath = 'savefilehere2.json'
#final_mass_calc(filesavepath, client, client_wt_IDs, check_wt_IDs, std_masses, inputdata)