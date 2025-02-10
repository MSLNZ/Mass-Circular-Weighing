"""
A repository for constants and symbols used in the mass weighing program
Modify default folder paths as necessary
"""
import os
from datetime import date

MU_STR = 'µ'                    # ALT+0181 or 'µ'. use 'u' if running into issues
SIGMA_STR = 'σ'                 # \u03C3 for sigma sign
DELTA_STR = 'Δ'                 # \u0394 for capital delta sign
SQUARED_STR = '²'

SUFFIX = {'ng': 1e-9, 'µg': 1e-6, 'ug': 1e-6, 'mg': 1e-3, 'g': 1, 'kg': 1e3}

DEGREE_SIGN = '°'           # \xb0
IN_DEGREES_C = ' ('+DEGREE_SIGN+'C)'

NBC = True                  # no buoyancy correction so use REL_UNC
REL_UNC = 0.03              # relative uncertainty in ppm for no buoyancy correction: typically 0.03 or 0.1

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
admin_default = os.path.join(ROOT_DIR, r'utils\default_admin.xlsx')
config_default = os.path.join(ROOT_DIR, r'utils\default_config.xml')

mass_folder = 'M:'

database_dir = r'M:\AirDensityDatabases'

commercial_folder = r'M:\Commercial Calibrations'
year = date.today().strftime("%Y")
commercial_year_folder = os.path.join(commercial_folder, year)
save_folder_default = os.path.join(commercial_year_folder, 'DEFAULT_SAVE_FOLDER')

local_backup = os.path.join(r'C:\CircularWeighingData', year)

job_default = 100000
client_default = "Client"
client_wt_IDs_default = '1 2 5 10 20 50 100 200 500 1000 2000 5000 10000'.split()

MAX_BAD_RUNS = 6            # limit for aborting circular weighing due to multiple bad runs

FONTSIZE = 32               # size of text in large pop-ups
