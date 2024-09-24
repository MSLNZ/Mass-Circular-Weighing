"""
A helper script to extract a table of weighing data from a json-format weighing file.
"""
import os
from msl.io import read
from openpyxl import Workbook


folder = r'I:\MSL\Private\Mass\Commercial Calibrations\2024\1466_ThermoFisher'
json_file = r'ThermoFisherScientificNZLimited_50.json'
wb = Workbook()


for flist in os.walk(folder):                   # traverse all folders and subfolders
    if 'backups' not in flist[0]:               # unless they are called 'backups'
        for fname in flist[2]:                  # iterate through the files
            if 'ThermoFisherScientificNZLimited_50.json' in fname:  # and 'repeatability' not in fname:  # select only json files from weighings
                file_to_read = os.path.join(flist[0], fname)
                print(f'Reading {file_to_read}')
                code=file_to_read.split('_')[2].strip('.json')
                print(f"Code {code}")
                jsonroot = read(file_to_read)

                sheet1 = wb.create_sheet(code)
                sheet1.append(
                    [
                        "Run", "Cycle",
                        "Time 1", "Reading 1",
                        "Time 2", "Reading 2",
                        "Time 3", "Reading 3",
                        "Time 4", "Reading 4",
                    ]
                )

                for data_set in jsonroot.datasets():
                    if 'measurement' in data_set.name:
                        if data_set.metadata.get("Weighing complete"):
                            run_no = data_set.name.split('_')[-1]
                            # print(data_set.name, run_no)
                            for cycle, cyc_val in enumerate(data_set):
                                num_pos = len(cyc_val)
                                sheet1.append(
                                    [
                                        int(run_no), cycle+1,
                                        cyc_val[0][0], cyc_val[0][1],
                                        cyc_val[1][0], cyc_val[1][1],
                                        cyc_val[2][0], cyc_val[2][1],
                                        # cyc_val[3][0], cyc_val[3][1],
                                    ]
                                )


wb.save(os.path.join(folder, "CollatedData_50.xlsx"))
