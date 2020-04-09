from src.routines.final_mass_calc import final_mass_calc
from src.routines.collate_data import collate_data_from_list
import numpy as np

filesavepath = 'savefilehere.json'
client = 'Hort. Research'
client_wt_IDs = ['100', '50', '20', '20d', '10', '5', '2', '2d', '1']
check_wt_IDs = ['5w', '1w']

std_masses = {}
# num_stds = 7
# np.empty(num_stds, dtype={
#     'names': ('std weight ID', 'nominal (g)', 'std mass values (g)', 'std uncertainties (ug)'),
#     'formats': (object, np.float, np.float, np.float)})

std_masses['Set Identifier'] = 'S'
std_masses['Calibrated'] = '2000'
std_masses['weight ID'] = ['100s', '50s', '20s', '10s', '5s', '2s', '1s']
std_masses['nominal (g)'] = [
    100,
    50,
    20,
    10,
    5,
    2,
    1
]
std_masses['mass values (g)'] = [
    100.000059108,
    50.000053126,
    19.999998346,
    10.000010291,
    4.999997782,
    1.999996291,
    0.999956601
]
std_masses['uncertainties (ug)'] = [
    4.008,
    2.624,
    2.088,
    1.747,
    1.152,
    0.806,
    0.752,
]

# test data
weighing1 = np.asarray(
    [
        ('100', '100s', 0.000640283, 8.0),
        ('100s', '50+50s', -0.000192765, 8.0)
    ],
    dtype =[('+ weight group', object), ('- weight group', object), ('mass difference', 'float64'), ('balance uncertainty (ug)', 'float64')]
)
weighing2 = np.asarray(
    [
        ('50', '50s', 0.00017231, 6.0),
        ('50s', '20+20d+10', -0.000061662, 6.0)
    ],
    dtype =[('+ weight group', object), ('- weight group', object), ('mass difference', 'float64'), ('balance uncertainty (ug)', 'float64')]
)
weighing3 = np.asarray(
    [
        ('20', '20s', -0.000072181, 5.0),
        ('20s', '20d', -0.000037743, 5.0),
        ('20d', '10+10s', -0.000101083, 5.0)
    ],
    dtype =[('+ weight group', object), ('- weight group', object), ('mass difference', 'float64'), ('balance uncertainty (ug)', 'float64')]
)
weighing4 = np.asarray(
    [
        ('10', '10s', 0.000121268, 5.0),
        ('10s', '5+5w', 0.000081936, 5.0)
    ],
    dtype =[('+ weight group', object), ('- weight group', object), ('mass difference', 'float64'), ('balance uncertainty (ug)', 'float64')]
)
weighing5 = np.asarray(
    [
        ('5', '5s', -0.000069925, 5.0),
        ('5s', '5w', -0.000000631, 5.0)
    ],
    dtype =[('+ weight group', object), ('- weight group', object), ('mass difference', 'float64'), ('balance uncertainty (ug)', 'float64')]
)
weighing6 = np.asarray(
    [
        ('2', '2s', -0.00006477, 0.5),
        ('2s', '2d', -0.000041124, 0.5),
        ('2d', '1+1s', 0.000049755, 0.5)
    ],
    dtype =[('+ weight group', object), ('- weight group', object), ('mass difference', 'float64'), ('balance uncertainty (ug)', 'float64')]
)
weighing7 = np.asarray(
    [
        ('1', '1s', 0.00007601, 0.5),
        ('1s', '1w', -0.000057911, 0.5),
        ('1', '1s', 0.000076501, 0.5),
        ('1s', '1w', -0.000058598, 0.5)
    ],
    dtype =[('+ weight group', object), ('- weight group', object), ('mass difference', 'float64'), ('balance uncertainty (ug)', 'float64')]
)
weighings = [weighing1, weighing2, weighing3, weighing4, weighing5, weighing6, weighing7]

collated = collate_data_from_list(weighings)

final_mass_calc(filesavepath, client, client_wt_IDs, check_wt_IDs, std_masses, collated)


#     std_masses['std residuals'] = [
#         -2.779,
#         3.305,
#         -1.368,
#         -0.05,
#         -0.071,
#         -0.33,
#         0.575
#     ]