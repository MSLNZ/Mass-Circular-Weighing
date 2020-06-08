# A repository for constants and symbols used in the mass weighing program

import os

MU_STR = 'u' #'µ'               # ALT+0181 or 'µ'
SIGMA_STR = 'σ'                 # \u03C3 for sigma sign
DELTA_STR = 'Δ'                 # \u0394 for capital delta sign
SQUARED_STR = '²'

SUFFIX = {'ng': 1e-9, 'µg': 1e-6, 'ug': 1e-6, 'mg': 1e-3, 'g': 1, 'kg': 1e3}

DEGREE_SIGN = '°'           # \xb0
IN_DEGREES_C = ' ('+DEGREE_SIGN+'C)'

NBC = True                  #
REL_UNC = 0.03              # relative uncertainty in ppm for no buoyancy correction: typ 0.03 or 0.1

local_backup = r'C:\CircularWeighingData'
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
config_default = os.path.join(ROOT_DIR, r'examples\sample_config.xml')

save_folder_default = r'I:\MSL\Private\Mass\transfer\Balance Software\Sample Data'
sample_data_folder = r'I:\MSL\Private\Mass\transfer\Balance Software\Sample Data'
mass_folder = r'I:\MSL\Private\Mass'
H_drive = r'H:'

job_default = ""
client_default = ""
client_wt_IDs_default = '1 2 5 10 20 50 100 200 500 1000 2000 5000 10000'

MAX_BAD_RUNS = 6

FONTSIZE = 32               # sets size of large pop-ups during circular weighing