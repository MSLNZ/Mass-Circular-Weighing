# Run final mass calculation using collated data from json files, with ability to customise FMC

import sys
import os

from msl.qt import application, excepthook
sys.excepthook = excepthook
gui = application()

import numpy as np
from openpyxl.styles import Font, Alignment

from msl.io import read, read_table

from mass_circular_weighing.configuration import Configuration
from mass_circular_weighing.constants import MU_STR

from mass_circular_weighing.gui.widgets.scheme_table import SchemeTable
from mass_circular_weighing.routines.collate_data import collate_all_weighings

from mass_circular_weighing.routine_classes.final_mass_calc_class import FinalMassCalc, g_to_microg
from mass_circular_weighing.gui.threads.masscalc_popup import filter_mass_set

from mass_circular_weighing.routine_classes.results_summary_Excel import ExcelSummaryWorkbook


ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# admin = r"M:\Recal_2025_buildup\2025_06_09 June 9 Buoyancy\MSL_Admin.xlsx"
admin = r'C:\Users\r.hawke\OneDrive - Callaghan Innovation\Desktop\0003b_Pressure\PressureStandards_Admin.xlsx'

# input_data is in json files

cfg = Configuration(admin)
print(cfg.correlations)
print(cfg.ad_corr)
cfg.init_ref_mass_sets()

print(cfg.all_stds)
print(cfg.all_client_wts)
print(cfg.all_checks)

# Load scheme
schemetable = SchemeTable()
schemetable.update_balance_list(cfg.bal_list)
schemetable.load_scheme(cfg.scheme[0], cfg.scheme[1])
# schemetable.show()
# gui.exec()

# Collate data, including air density information - use add_air_densities(root) if not already in root
collated_data = collate_all_weighings(schemetable, cfg)
# collated_data = np.delete(collated_data, [3, 4, 5])

### for Pressure 0003
# collated_data = collate_all_weighings(schemetable, cfg)[2:]  # first run of 200P3 200MA 200MB was omitted
# collated_data = np.delete(collated_data, [2, 3, 18, 19, 20])  # third run (now second) of 200P3 200MA 200MB was omitted as well as
# # first run of 800B2+200MA 1KMA 800B3+200MA 1KMB


"""We can change the balance uncertainty here if desired"""
# for i in range(24):
#     collated_data['balance uncertainty ('+MU_STR+'g)'][i] = 11000
print('Collated data\n', collated_data)

input_data = np.empty(len(collated_data),
                    dtype=[('+ weight group', object), ('- weight group', object),
                           ('mass difference (g)', 'float64'), ('balance uncertainty (' + MU_STR + 'g)', 'float64')
                           ],
                    )

for key in ['+ weight group', '- weight group', 'mass difference (g)', 'balance uncertainty (' + MU_STR + 'g)']:
    input_data[key] = collated_data[key]

client_wts = filter_mass_set(cfg.all_client_wts, collated_data)
checks = filter_mass_set(cfg.all_checks, collated_data)  # or None
stds = filter_mass_set(cfg.all_stds, collated_data)
old_stds = stds['mass values (g)']

fmc = FinalMassCalc(cfg.folder, cfg.client, client_wts, checks, stds, input_data, nbc=False, corr=cfg.correlations)

# settings for analysis options
fmc.BUOYANCY_CORR = fmc.TRUE_MASS = cfg.ad_corr  # buoyancy corrections means working in true mass

if fmc.TRUE_MASS:  # need to convert standard (and optionally check) mass values to true mass
    fmc.std_masses['mass values (g)'] = fmc.calculate_true_mass(v=stds['Vol (mL)'], b=stds['mass values (g)'])
    if checks:
        fmc.check_masses['mass values (g)'] = fmc.calculate_true_mass(v=checks['Vol (mL)'], b=checks['mass values (g)'])

fmc.UNC_AIR_DENS = cfg.ad_corr   # for heavy mass this is negligible compared to the weighing uncertainty

fmc.UNC_VOL = False
fmc.HEIGHT_CORR = False
fmc.UNC_HEIGHT = False

# do calculation
fmc.import_mass_lists()
fmc.parse_inputdata_to_matrices()

fmc.apply_corrections_to_mass_differences(air_densities=collated_data['Mean air density (kg/m3)'])
fmc.cal_psi_y(
    unc_airdens=collated_data['Stdev air density (kg/m3)'],
    air_densities=collated_data['Mean air density (kg/m3)'],
    rv=None
)

fmc.do_least_squares()
fmc.check_residuals()

fmc.cal_rel_unc()
fmc.make_summary_table()

fmc.add_data_to_root()
fmc.save_to_json_file()

# Export to Excel summary file
xl = ExcelSummaryWorkbook(cfg)
xl.format_scheme_file()
fmc_root = read(fmc.filesavepath)  # the metadata parsing breaks if trying to use fmc.finalmasscalc directly
xl.add_mls(fmc_root)

# add collated_data matrix to inputdata sheet
insheet = xl.wb["MLS Input Data"]
insheet.append(['True mass differences/values'])
insheet.append([])  # Makes a new empty row
insheet.append(["Before buoyancy corrections (conventional mass)"])
insheet.append(['+ weight group', '- weight group', 'mass difference (g)',
                'balance uncertainty (' + MU_STR + 'g)', 'Acceptance met?', 'Stdev of diff (' + MU_STR + 'g)',
                'Mean air density (kg/m3)', "Stdev air density (kg/m3)"])
for row in collated_data:
    insheet.append(list(row)[3:])
for i, id in enumerate(stds['Weight ID']):
    insheet.append([id, "", old_stds[i]])

# add conventional mass values to output data sheet
mls = xl.wb["MLS Output Data"]
mls.append([""])  # Makes a new empty row
mls.append(["Note that the table above contains TRUE MASS VALUES (including the reference values)"])
mls.append([""])  # Makes a new empty row
mls.append(["Below is a table of CONVENTIONAL MASS VALUES (converted from above)"])
b_conv = fmc.convert_to_conventional_mass(v=None, b=None)
for i, b in enumerate(b_conv):
    fmc.summarytable[i, 3] = np.round(b, 12)
for row in fmc.summarytable:
    mls.append(list(row[:7]))

# add covariance matrix info to mls sheet
mls.append([""])  # Makes a new empty row
mls.append(["Covariance matrix in g"])
mls.append([" "]+fmc.all_wts['Weight ID'])
for i, row in enumerate(fmc.covariances):
    mls.append([fmc.all_wts['Weight ID'][i]]+list(row))

xl_output_file = xl.save_workbook(cfg.folder, cfg.client)
# set Excel output to read_only
# os.chmod(xl_output_file, S_IREAD | S_IRGRP | S_IROTH)
