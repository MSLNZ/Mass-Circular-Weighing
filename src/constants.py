# A repository for constants and symbols used in the mass weighing program

import os

MU_STR = 'u' #'µ'                # ALT+0181 or 'µ'
SIGMA_STR = 'σ'             # \u03C3 for sigma sign
SQUARED_STR = '²'

SUFFIX = {'µg': 1e-6, 'ug': 1e-6, 'mg': 1e-3, 'g': 1, 'kg': 1e3}

DEGREE_SIGN = '°'           # \xb0
IN_DEGREES_C = ' ('+DEGREE_SIGN+'C)'

local_backup = r'C:\CircularWeighingData'
config_default = os.path.abspath(os.path.join(r'C:\Users\r.hawke\PycharmProjects\Mass-Circular-Weighing', 'config.xml'))
save_folder_default = r'I:\MSL\Private\Mass\transfer\Balance Software\Sample Data'
client_default = ' '
client_masses_default = '1 2 5 10 20 50 100 200 500 1000 2000 5000'

stds = [                    # options for standards and check masses
    'MET19A',
    'MET19B',
    'MET16A',
    'MET16B',
    'WV',
    'None',
]

MAX_BAD_RUNS = 3

FONTSIZE = 32               # sets size of large pop-ups during circular weighing