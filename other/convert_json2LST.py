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


def to_lst(json_root, save_folder, cfg=None):
    lst_filename = ""
    for grp in jsonroot['Circular Weighings'].groups():
        ambient_data = [""]
        to_mg = 1
        bal_alias = None
        nom = 0

        se = grp.name.split("/")[-1]
        cw_class = CircWeigh(se)

        wb = Workbook()
        sheet1 = wb.active
        sheet1.title = "LST file"
        header = []
        for weighdata in jsonroot.datasets():
            if 'measurement' in weighdata.name:
                positions = weighdata.metadata.get("Weight group loading order")
                for grp in cw_class.wtgrps:
                    for k, v in positions.items():
                        if v == grp:
                            pos = k.strip("Position ")
                    header.append(f'{grp}(#{pos})')
                break
            break
        sheet1.append(header)
        sheet1.append(["=F4", cw_class.num_cycles])  # timestamp needs to appear in cell A2
        sheet1.append([])
        padding = [""]*(5 - cw_class.num_wtgrps)  # customise padding so metadata starts in column F

        for weighdata in jsonroot.datasets():
            if 'measurement' in weighdata.name:
                nom = weighdata.metadata.get("Nominal mass (g)")
                if weighdata.metadata.get("Weighing complete"):
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
                                # could calculate actual mean and save to metadata as part of run_circ_weigh?
                                temps = weighdata.metadata.get("T" + IN_DEGREES_C).split(" to ")
                                mean_temp = (float(temps[0]) + float(temps[1])) / 2
                                p = weighdata.metadata.get("Pressure (hPa)").split(" to ")
                                mean_P = (float(p[0]) + float(p[1])) / 2
                                rhs = weighdata.metadata.get("RH (%)").split(" to ")
                                mean_rhs = (float(rhs[0]) + float(rhs[1])) / 2

                                ambient_data = [
                                    weighdata.metadata.get("Mmt Timestamp"),
                                    float(temps[0]), #mean_temp,
                                    mean_P,
                                    mean_rhs
                                ]
                                # print(ambient_data)
                                data_row += padding  # ambient data must start in column F
                                data_row += ambient_data
                                ambient_data[1] = float(temps[1])
                            except AttributeError:
                                pass
                        bal_alias = weighdata.metadata.get("Balance")

                        sheet1.append(data_row)

                    try:
                        corresponding_analysis_run = weighdata.name.replace("measurement", "analysis")
                        last_row_date = jsonroot[corresponding_analysis_run].metadata.get('Analysis Timestamp')
                    except KeyError:  # this shouldn't happen because we've determined the dataset is complete...
                        print(f"No analysis available for {corresponding_analysis_run}! Moving to next dataset...")

        last_row = ['', '', '', '', '', last_row_date]
        last_row += ambient_data[1:]
        sheet1.append(last_row)

        try:
            bal_serial = cfg.db.equipment[bal_alias].serial
        except AttributeError:
            cfg = Config(r"C:\MCW_Config\local_config.xml")
            db = cfg.database()
            bal_serial = db.equipment[bal_alias].serial
        sheet1["F2"] = bal_serial

        print(ambient_data)
        last_date = ambient_data[0].split()[0]

        lst_filename = os.path.join(save_folder, last_date + "_" +str(nom) + "_" + se + "_LST.xlsx")
        wb.save(lst_filename)

    return lst_filename


if __name__ == "__main__":
    cfg = Config(r"C:\MCW_Config\local_config.xml")
    folder = r'I:\MSL\Private\Mass\Recal_2020\D2\json_files_to_LST'  # folder of data
    json_file = r'I:\MSL\Private\Mass\Recal_2020\D2\json_files_to_LST\MassStdsD2_200(DiscCheck2)_3-4-24.json'
    jsonroot = read(json_file)
    print(jsonroot)

    to_lst(json_root=jsonroot, save_folder=folder, cfg=cfg)

    # for path, directories, files in os.walk(folder):
    #     for f in files:
    #         if ".json" in f:
    #             json_file = os.path.join(path, f)
    #             jsonroot = read(json_file)
    #             print(jsonroot)
    #
    #             to_lst(json_root=jsonroot, save_folder=folder, cfg=cfg)


### extra used for re-correcting previous files:
#from mass_circular_weighing.equip.ambient_fromdatabase import apply_calibration_milliK, corrected_resistance
#
# # Values for 89/S4 (updated 20/07/2023)
# R0 = 99.983886  # raw reading at 0 deg C, in Ohms
# corr_R0 = corrected_resistance(R0)
#
# old_A = 0.00391778
# old_B = -0.0000007329
#
#
# def recorrect_temperature_milliK(old_T):
#     # R(t)/R0 = 1 + At + Bt**2
#     Rt_R0 = 1 + old_A*old_T + old_B*old_T**2
#     Rt = Rt_R0 * corr_R0
#
#     corr_T = apply_calibration_milliK(Rt)  # this uses the correct values now
#
#     return corr_T
