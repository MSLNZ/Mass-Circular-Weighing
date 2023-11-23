"""
A helper script to convert a json file from a set of circular weighings
into a LST-style table of weighing data for use in the builddown analysis.
"""
import os
from openpyxl import Workbook

from msl.io import read
from msl.equipment import Config

from mass_circular_weighing.routine_classes.circ_weigh_class import CircWeigh
from mass_circular_weighing.constants import IN_DEGREES_C


folder = r'I:\MSL\Private\Mass\Commercial Calibrations\2023\AX1006PostService'  # folder of data
json_file = r'I:\MSL\Private\Mass\Commercial Calibrations\2023\AX1006PostService\MassStds_1000.json'

jsonroot = read(json_file)
print(jsonroot)

se = "1KSR 1KSS 1KSC 1KCC"
cw_class = CircWeigh(se)
cw_file = json_file
nom = '1000'
cfg = Config(r"C:\MCW_Config\local_config.xml")

wb = Workbook()
sheet1 = wb.active
sheet1.title = "LST file"
header = []
for pos, grp in enumerate(cw_class.wtgrps):
    header.append(grp + '(#' + str(pos+1) + ")")
sheet1.append(header)
sheet1.append(["=F4", cw_class.num_cycles])
sheet1.append([])

for weighdata in jsonroot.datasets():
        if 'measurement' in weighdata.name:
            if weighdata.metadata.get("Weighing complete"):
                run_no = weighdata.name.split('_')[-1]
                if weighdata.metadata.get("Unit") == "g":
                    to_mg = 1000
                elif weighdata.metadata.get("Unit") == "mg":
                    to_mg = 1
                else:
                    print("Unit is ", weighdata.metadata.get("Unit"))
                # print(data_set.name, run_no)
                for cycle, cyc_val in enumerate(weighdata):
                    data_row = []
                    for i in range(cw_class.num_wtgrps):
                        data_row.append(cyc_val[i][1]*to_mg)
                    if cycle == 0:
                        try:
                            # TODO calculate actual mean and save to metadata as part of run_circ_weigh
                            temps = weighdata.metadata.get("T" + IN_DEGREES_C).split(" to ")
                            mean_temp = (float(temps[0]) + float(temps[1])) / 2
                            p = weighdata.metadata.get("Pressure (hPa)").split(" to ")
                            mean_P = (float(p[0]) + float(p[1])) / 2
                            rhs = weighdata.metadata.get("RH (%)").split(" to ")
                            mean_rhs = (float(rhs[0]) + float(rhs[1])) / 2

                            ambient_data = [
                                "",
                                weighdata.metadata.get("Mmt Timestamp"),
                                mean_temp,
                                mean_P,
                                mean_rhs
                            ]
                            data_row += ambient_data
                        except AttributeError:
                            pass
                    bal_alias = weighdata.metadata.get("Balance")
                    db = cfg.database()
                    bal_serial = db.equipment[bal_alias].serial

                    sheet1.append(data_row)

last_row = ['', '', '', '']
last_row += ambient_data
sheet1.append(last_row)

sheet1["F2"] = bal_serial

wb.save(os.path.join(folder, "LST_1000_mg.xlsx"))
