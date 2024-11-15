"""
Run the circular weighing program for analysis without the gui
"""
import sys
import os

from msl.qt import application, excepthook
sys.excepthook = excepthook
gui = application()

from mass_circular_weighing.log import log
from mass_circular_weighing.constants import MU_STR

from mass_circular_weighing.configuration import Configuration

from mass_circular_weighing.gui.widgets.scheme_table import SchemeTable
from mass_circular_weighing.routines.collate_data import collate_all_weighings

from mass_circular_weighing.gui.threads.masscalc_popup import *


# Specify admin file location
# admin = r'C:\Users\r.hawke\PycharmProjects\Mass-Circular-Weighing\tests\samples\admin_TP009.xlsx'
# admin = r'I:\MSL\Private\Mass\Recal_2020\D6\D6_python\MassStdsD6_Admin_dens.xlsx'
# admin = r"I:\MSL\Private\Mass\Recal_2020\AX10005\Rebecca's analysis\MassStds_Admin.xlsx"
admin = r"C:\Users\r.hawke\OneDrive - Callaghan Innovation\Desktop\1462_Pressure\PressureStandards_Admin.xlsx"
cfg = Configuration(admin)
print(cfg.correlations)
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

# Collate data
collated_data = collate_all_weighings(schemetable, cfg)
# print(collated_data)
"""We can change the balance uncertainty here if desired"""
# for i in range(60):
#     collated_data['balance uncertainty ('+MU_STR+'g)'][i] = 15000

# Display Final Mass Calculation window with calculation done
fmc = MassCalcThread()
fmc.show(collated_data, cfg)

# set any optional parameters, e.g.
# fmc.BUOYANCY_CORR = True

fmc.start_finalmasscalc()
gui.exec()
