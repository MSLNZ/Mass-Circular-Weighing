"""
A helper script to convert weighing data from the Excel-with-VBA circular weighing program into json format
for including in the final mass calculation.  Ambient conditions are captured as part of the conversion.
"""
import os
import numpy as np

from msl.io import ExcelReader

from mass_circular_weighing import __version__
from mass_circular_weighing.routines.circ_weigh_class import CircWeigh
from mass_circular_weighing.routines.run_circ_weigh import check_for_existing_weighdata, analyse_weighing
from mass_circular_weighing.configuration import Configuration
from mass_circular_weighing.constants import IN_DEGREES_C

tab = '  '
cols = [
    "A",
    "B",
    "C",
    "D",
    "E",
]


cfg_path = r'I:\MSL\Private\Mass\transfer\Balance Software\Sample Data\Demo_Set\J00712_config.xml'
cfg = Configuration(cfg_path)
bal_alias = "AT106"
omega = cfg.get_ambientlogger_info(bal_alias)

folder = r'I:\MSL\Private\Mass\transfer\Balance Software\Sample Data\Demo_Set\AT106 Weighings'
files = [
    '2020Demo_50a.xls',
    '2020Demo_50b.xls',
    '2020Demo_50c.xls',
    '2020Demo_100a2.xls',
    '2020Demo_100b.xls',
    '2020Demo_100c.xls',
]


temp = [
    "19.01 to 20.05",
    "20.03 to 20.12",
    "20.10 to 20.10",
    "20.17",
    "20.18",
    "20.21",
]
rh = [
    "56.64 to 54.17",
    "54.98 to 54.25",
    "54.75 to 53.97",
    "51.91",
    "51.5",
    "54.63",
]
press = [
    "1013.5 to 1012.4",
    "1012.4 to 1012.8",
    "1012.8 to 1013.3",
    "1013.8 to 1012.9",
    "1012.9",
    "1002.0",
]


for i, file in enumerate(files):
    if i < 3:
        nom = 50
    else:
        nom = 100
    ac = cfg.acceptance_criteria("AT106", nom)

    filename = cfg.client + "_" + str(nom) + ".json"
    url = cfg.folder + "\\" + filename

    temp_i = temp[i]
    rh_i = rh[i]
    press_i = press[i]

    path = os.path.join(folder, file)

    excel = ExcelReader(path)

    header = excel.read(sheet="LST file")[0]
    print(header)
    se = ""
    positions = []
    for h in header:
        se += h.split("(")[0] + " "
        positions.append(int(h.split("#")[1].strip(")")))

    se = se.strip()

    root = check_for_existing_weighdata(folder, url, se)
    print(root)

    weighing = CircWeigh(se)

    positiondict = {}
    positionstr = ""
    for i in range(weighing.num_wtgrps):
        positionstr = positionstr + tab + 'Position ' + str(positions[i]) + ': ' + weighing.wtgrps[i] + '\n'
        positiondict['Position ' + str(positions[i])] = weighing.wtgrps[i]
    print(positionstr)

    timestamp = excel.read(sheet="LST file", cell="A2")

    # collect metadata
    metadata = {
        'Client': cfg.client, 'Balance': "AT106",
        'Unit': 'g', 'Nominal mass (g)': float(nom),
    }
    for key, value in ac.items():
        metadata[key] = value

    metadata['Program Version'] = __version__
    metadata['Mmt Timestamp'] = timestamp.strftime('%d-%m-%Y %H:%M')
    metadata['Time unit'] = 'min'
    metadata['Ambient monitoring'] = omega
    metadata["Weight group loading order"] = positiondict
    metadata['T' + IN_DEGREES_C] = temp_i
    metadata['RH (%)'] = rh_i
    metadata['Pressure (hPa)'] = press_i
    metadata['Ambient OK?'] = True
    metadata['Weighing complete'] = True

    print(metadata)

    for run in range(5):
        run_id = "run_" + str(run + 1)
        # print(run_id)

        # initialise dataset
        data = np.empty(shape=(weighing.num_cycles, weighing.num_wtgrps, 2))
        weighdata = root['Circular Weighings'][se].require_dataset('measurement_' + run_id, data=data)

        # get data and put it into dataset
        col = cols[weighing.num_wtgrps - 1]
        first_row = 4 + run * weighing.num_cycles
        last_row = 3 + weighing.num_cycles + run * weighing.num_cycles
        new_data = excel.read(sheet="LST file", cell="A{}:{}{}".format(first_row, col, last_row))
        print(new_data.shape)
        for i in range(weighing.num_cycles):
            for j in range(weighing.num_wtgrps):
                read_no = i * weighing.num_wtgrps + j
                weighdata[i, j, :] = [read_no, new_data[i][j]]
        # print(weighdata)
        weighdata.add_metadata(**metadata)
        print(weighdata.shape)

        print(root)
        root.save(file=url, mode='w', ensure_ascii=False)

        bal_mode = cfg.equipment[bal_alias].user_defined['weighing_mode']
        analyse_weighing(root, url, se, run_id, bal_mode, cfg.timed, 'linear drift')

    print(root)
    root.save(file=url, mode='w', ensure_ascii=False)

    # save_folder = r"G:\Shared drives\TEST - MSL Shared Drive\Mass"
    # save_here = os.path.join(save_folder, filename)
    # root.save(file=save_here, mode='w', ensure_ascii=False)

