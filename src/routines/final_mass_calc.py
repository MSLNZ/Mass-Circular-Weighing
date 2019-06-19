import numpy as np
import json

# initialisation
scheme_client = {}
scheme_std = {}
scheme_check = {}
collated_data = {}

# import lists of masses from scheme info
num_client_masses = 9
scheme_client['client weight ID'] = ['100', '50', '20', '20d', '10', '5', '2', '2d', '1']
print(scheme_client)

num_stds = 7
scheme_std['std weight ID'] = ['100s', '50s', '20s', '10s', '5s', '2s', '1s']
print(scheme_std)

num_check_masses = 2
scheme_check['check weight ID'] = ['5w', '1w']
print(scheme_check)

num_unknowns = num_client_masses + num_stds + num_check_masses
print('Number of unknowns =', num_unknowns)

# import data
num_circweighings = 8  # 25 differences

# test data
weighing1 = np.array([('100', '100s', 0.000640283, 0.0, 8.0), ('100s', '50+50s', -0.000192765, 11.071, 8.0)], dtype =[('+ weight group', 'S256'), ('- weight group', 'S256'), ('mass difference', 'float64'), ('residual', 'float64'), ('bal uncert', 'float64')])
weighing2 = np.array([('50', '50s', 0.000640283, 0.0, 8.0), ('50s', '20+20d+10', -0.000192765, 11.071, 8.0)], dtype =[('+ weight group', 'S256'), ('- weight group', 'S256'), ('mass difference', 'float64'), ('residual', 'float64'), ('bal uncert', 'float64')])
weighing3 = np.array([('20', '20s', 0.000640283, 0.0, 8.0), ('20s', '20d', -0.000192765, 11.071, 8.0), ('20d', '10+10s', -0.000192765, 11.071, 8.0)], dtype =[('+ weight group', 'S256'), ('- weight group', 'S256'), ('mass difference', 'float64'), ('residual', 'float64'), ('bal uncert', 'float64')])
weighing4 = np.array([('10', '10s', 0.000640283, 0.0, 8.0), ('10s', '5+5w', -0.000192765, 11.071, 8.0)], dtype =[('+ weight group', 'S256'), ('- weight group', 'S256'), ('mass difference', 'float64'), ('residual', 'float64'), ('bal uncert', 'float64')])
weighing5 = np.array([('5', '5s', 0.000640283, 0.0, 8.0), ('5s', '5w', -0.000192765, 11.071, 8.0)], dtype =[('+ weight group', 'S256'), ('- weight group', 'S256'), ('mass difference', 'float64'), ('residual', 'float64'), ('bal uncert', 'float64')])
weighing6 = np.array([('2', '2s', 0.000640283, 0.0, 8.0), ('2s', '2d', -0.000192765, 11.071, 8.0), ('2d', '1+1s', -0.000192765, 11.071, 8.0)], dtype =[('+ weight group', 'S256'), ('- weight group', 'S256'), ('mass difference', 'float64'), ('residual', 'float64'), ('bal uncert', 'float64')])
weighing7 = np.array([('1', '1s', 0.000640283, 0.0, 8.0), ('1s', '50+50s', -0.000192765, 11.071, 8.0)], dtype =[('+ weight group', 'S256'), ('- weight group', 'S256'), ('mass difference', 'float64'), ('residual', 'float64'), ('bal uncert', 'float64')])
weighings = [weighing1, weighing2, weighing3, weighing4, weighing5, weighing6, weighing7]

print(weighings)

# check
collated_data['+ weight group'] = ['100', '100s', '50', '50s', '20', '20s', '20d', '10', '10s', '5', '5s', '2', '2s',
                                   '2d', '1', '1s', '1', '1s', '100s', '50s', '20s', '10s', '5s', '2s', '1s']
collated_data['- weight group'] = ['100s', '50+50s', '50s' '20+20d+10', '20s', '20d', '10+10s', '10s', '5+5w', '5s',
                                   '5w', '2s', '2d', '1+1s', '1s', '1w', '1s', '1w', '', '', '', '', '', '', '', '']
print(collated_data)
#collated_data = np.empty((num_circweighings,), dtype =[('+ weight group', 'S30'), ('- weight group', 'S30'), ('mass difference', 'float64'), ('residual', 'float64'), ('bal uncert', 'float64')])
 #pd.DataFrame.empty((num_circweighings,), dtype =[('+ weight group', 'S30'), ('- weight group', 'S30'), ('mass difference', 'float64'), ('residual', 'float64'), ('bal uncert', 'float64')])
# note that this is a slightly different format to existing circ weighing group data - could add bal uncert there if needed


# for all datasets in circular weighing group, get the weight groups and mass differences and collate it into collated_data
'''
for dataset in (somehow get a collation of all datasets which begin 'analysis_' but aren't flagged ignore): 
    collated_data['+ weight group'] = somehow add dataset['+ weight group'] - maybe make a list first and then put it into collated_data?
    collated_data['- weight group'] = 
    collated_data['mass difference'] = 
    collated_data['residual'] = 
'''

