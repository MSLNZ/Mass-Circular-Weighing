import numpy as np
import pandas as pd


# import lists of masses from scheme info
num_client_masses = 7
scheme_client = {} #np.empty((num_client_masses,), dtype =[('weight ID', 'S10'), ('mass value', 'float64'), ('uncertainty', 'float64'), ('95% CI', 'float64')])
scheme_client['weight ID'] = ['100', '50', '20', '10', '5', '2', '1']
print(scheme_client['weight ID'])

num_stds = 3
scheme_std = {} #np.empty((num_stds,), dtype =[('weight ID', 'S10'), ('mass value', 'float64'), ('uncertainty', 'float64'), ('95% CI', 'float64')])
scheme_std['weight ID'] = ['100s', '50s', '20s', '10s', '5s', '2s', '1s']

num_check_masses = 2
scheme_check = {} #np.empty((num_check_masses,), dtype =[('weight ID', 'S10'), ('mass value', 'float64'), ('uncertainty', 'float64'), ('95% CI', 'float64')])
scheme_check['weight ID'] = ['5w', '1w']

# import data
num_circweighings = 25
#collated_data = np.empty((num_circweighings,), dtype =[('+ weight group', 'S30'), ('- weight group', 'S30'), ('mass difference', 'float64'), ('residual', 'float64'), ('bal uncert', 'float64')])
collated_data = {} #pd.DataFrame.empty((num_circweighings,), dtype =[('+ weight group', 'S30'), ('- weight group', 'S30'), ('mass difference', 'float64'), ('residual', 'float64'), ('bal uncert', 'float64')])
# note that this is a slightly different format to existing circ weighing group data - could add bal uncert there if needed
collated_data['+ weight group'] = ['100', '100s', '50', '50s', '20', '20s', '20d', '10', '10s', '5', '5s', '2', '2s', '2d', '1', '1s', '1', '1s', '100s', '50s', '20s', '10s', '5s', '2s', '1s']
collated_data['- weight group'] = ['100s', '50+50s', '50s' '20+20d+10', '20s', '20d', '10+10s', '10s', '5+5w', '5s', '5w', '2s', '2d', '1+1s', '1s', '1w', '1s', '1w', '', '', '', '', '', '', '', '']
print(collated_data)

# for all datasets in circular weighing group, get the weight groups and mass differences and collate it into collated_data
'''
for dataset in (somehow get a collation of all datasets which begin 'analysis_' but aren't flagged ignore): 
    collated_data['+ weight group'] = somehow add dataset['+ weight group'] - maybe make a list first and then put it into collated_data?
    collated_data['- weight group'] = 
    collated_data['mass difference'] = 
    collated_data['residual'] = 
'''