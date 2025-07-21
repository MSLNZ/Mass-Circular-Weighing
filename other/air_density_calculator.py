import os

from msl.io import JSONWriter, read
from msl.equipment import Config

from mass_circular_weighing.routines.json_circweigh_utils import add_air_densities
from mass_circular_weighing.routines.analyse_circ_weigh import analyse_weighing_true_mass


cfg = Config(r"C:\MCW_Config\local_config.xml")
folder = r'C:\Users\r.hawke\OneDrive - Callaghan Innovation\Desktop\0003_Pressure'  # folder of data
url = os.path.join(folder, 'PressureStandards_1000.json')

json__root = read(url)
json__root.read_only = False
print(json__root)

new_root = add_air_densities(root=json__root)

# new_root = analyse_weighing_true_mass(
#         cfg, json__root, url, se="20KA 10KAM+10KBM 20KB 20KC", run_id='run_1', bal_mode='mw')
# new_url = r'M:\Recal_2025_buildup\2025_06_09 June 9 Buoyancy\MSL_50000_tm.json'

root = JSONWriter()
root.set_root(new_root)
root.save(file=url, mode='w', encoding='utf-8', ensure_ascii=False)
