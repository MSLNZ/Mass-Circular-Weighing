"""
A script to collate all weighing data from json files to determine acceptance criteria
"""

import os
from openpyxl import Workbook

from msl.io import read

# from mass_circular_weighing.constants import MU_STR, SUFFIX

folder = r'C:\Users\rebecca.hawke\Desktop\2021' # folder of data

summary = Workbook()                            # create new Excel doc
runs = summary.active                           # get active sheet
runs.title = "Individual Runs"                  # set title
runs.append([
    "File", "Mmt Date", "Nominal (g)", "Run #", 'no drift', 'linear drift', 'quadratic drift', 'cubic drift',
])
collated = summary.create_sheet("Collated")     # make new sheet for collated runs
collated.append([
    "File", "Mmt Date", "Nominal (g)", "Scheme entry", "Run #", "+ weight group", "- weight group",
    "mass difference (g)", "residual (µg)", "balance uncertainty (µg)", "Acceptance met?",
])

for flist in os.walk(folder):                   # traverse all folders and subfolders
    if 'backups' not in flist[0]:               # unless they are called 'backups'
        for fname in flist[2]:                  # iterate through the files
            if '.json' in fname and 'finalmasscalc' not in fname:   # select only json files from weighings
                file_to_read = os.path.join(flist[0], fname)
                # print(f'Reading {file_to_read}')
                jsonroot = read(file_to_read)

                nom = None
                date = None
                for ds in jsonroot.datasets():
                    if 'measurement_run_1' in ds.name:
                        nom = ds.metadata['Nominal mass (g)']
                if 150 < nom < 550:
                    print(nom, file_to_read.strip("C:\\Users\\rebecca.hawke\\Desktop\\2021"))
                    for ds in jsonroot.datasets():
                        if 'measurement_run_1' in ds.name:
                            bal = ds.metadata["Balance"]
                            assert bal == "XPE505C"             # just in case any were on the old Sartorius
                        if 'analysis' in ds.name:
                            mmt = ds.name.replace('analysis', 'measurement')
                            mmt_ds = jsonroot[mmt]
                            date = mmt_ds.metadata["Mmt Timestamp"]
                            run_data = [
                                file_to_read.strip("C:\\Users\\rebecca.hawke\\Desktop\\2021\\"),
                                date,
                                nom,
                                ds.name.split("_")[-1]
                            ]
                            res_dict = eval(ds.metadata["Residual std devs"])
                            for key, value in res_dict.items():
                                run_data.append(value)
                            # print(run_data)
                            runs.append(run_data)
                        if 'Collated' in ds.name:
                            mmt = ds.name.replace('Collated', 'measurement_run_1')
                            mmt_ds = jsonroot[mmt]
                            date = mmt_ds.metadata["Mmt Timestamp"]
                            for r in ds.data:
                                row = [file_to_read.strip("C:\\Users\\rebecca.hawke\\Desktop\\2021\\"), date]
                                for i in r:
                                    row.append(i)
                                collated.append(row)

# add column, and split date and time
runs.insert_cols(3, amount=1)
runs['C1'] = "Mmt Time"
for i in range(2, runs.max_row+1):
    date_time = runs['B'+str(i)].value.split()
    runs['B' + str(i)] = date_time[0].replace("-", "/")
    runs['C' + str(i)] = date_time[1]

collated.insert_cols(3, amount=1)
collated['C1'] = "Mmt Time"
for i in range(2, collated.max_row+1):
    date_time = collated['B'+str(i)].value.split()
    collated['B' + str(i)] = date_time[0].replace("-", "/")
    collated['C' + str(i)] = date_time[1]

# save data to file
summary.save(os.path.join(folder, "summary.xlsx"))
