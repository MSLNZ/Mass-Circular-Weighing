"""
A helper script to add missing ambient metadata to a json file for a set of circular weighings
where the ambient metadata is stored in a separate database.
"""
import os
import numpy as np
from datetime import datetime

from msl.io import JSONWriter, read
from msl.equipment import Config

from mass_circular_weighing.routine_classes.circ_weigh_class import CircWeigh
from mass_circular_weighing.constants import IN_DEGREES_C
from mass_circular_weighing.equip.ambient_fromdatabase import data, get_rh_p_during, get_cal_temp_during
from mass_circular_weighing.equip.ambient_fromwebapp import get_t_rh_during
from mass_circular_weighing.utils.airdens_calculator import AirDens2009

#
# v_database_path = os.path.join(database_dir, f'Mass_Lab_Vaisala_{vaisala_sn}.sqlite3')
# vaisala_data = data(path=v_database_path, select='humidity,pressure', as_datetime=True, start=start, end=end, )
p_database_path = os.path.join(r'M:\AirDensityDatabases',
                               'Mass_Lab_Vaisala_K1510011.sqlite3')


def add_ambient_metadata(jsonroot, save_folder, cfg=None):
    root = JSONWriter()
    root.set_root(jsonroot)
    root.read_only = False

    for grp in jsonroot['Circular Weighings'].groups():
        to_mg = 1
        nom = 0

        se = grp.name.split("/")[-1]
        cw_class = CircWeigh(se)

        for weighdata in jsonroot.datasets():
            if se in weighdata.name and 'measurement' in weighdata.name:
                nom = weighdata.metadata.get("Nominal mass (g)")
                ithx = weighdata.metadata.get("Ambient monitoring")['Alias']
                sensor = weighdata.metadata.get("Ambient monitoring")['Sensor']
                if weighdata.metadata.get("Weighing complete"):
                    if weighdata.metadata.get("Unit") == "g":
                        to_mg = 1000
                    elif weighdata.metadata.get("Unit") == "mg":
                        to_mg = 1
                    else:
                        print("Unit is ", weighdata.metadata.get("Unit"))
                    # print(data_set.name, run_no)
                    try:
                        corresponding_analysis_run = weighdata.name.replace("measurement", "analysis")
                        last_row_date = jsonroot[corresponding_analysis_run].metadata.get('Analysis Timestamp')
                        enddatetime = datetime.strptime(last_row_date, "%d-%m-%Y %H:%M:%S")
                    except KeyError:  # this shouldn't happen because we've determined the dataset is complete...
                        print(f"No analysis available for {corresponding_analysis_run}! Moving to next dataset...")

                    for cycle, cyc_val in enumerate(weighdata):
                        data_row = []
                        for i in range(cw_class.num_wtgrps):
                            data_row.append(cyc_val[i][1]*to_mg)
                        if cycle == 0:
                            try:
                                start_time = weighdata.metadata.get("Mmt Timestamp")
                                startdatetime = datetime.strptime(start_time, "%d-%m-%Y %H:%M:%S")

                                print(startdatetime)
                                # print(enddatetime)
                                # get T from milliK database
                                # all_temps = get_cal_temp_during(start=startdatetime, end=enddatetime, channel=2)

                                # """get T from Vaisala database"""
                                # all_temps = np.asarray([a[0] for a in data(p_database_path, start=startdatetime, end=enddatetime, select='Temperature')])
                                #
                                # """get RH from Vaisala database"""
                                # all_rh = np.asarray([a[0] for a in data(p_database_path, start=startdatetime, end=enddatetime, select='Humidity')])

                                # """get mean temperature and humidity during weighing from webapp"""
                                all_temps, all_rh = get_t_rh_during(ithx, sensor=sensor, start=startdatetime, end=enddatetime)
                                root[weighdata.name].add_metadata(**{"All Humidities (%)": all_rh})
                                root[weighdata.name].add_metadata(**{"All Temps" + IN_DEGREES_C: all_temps})
                                print(all_temps)
                                print(all_rh)

                                mean_temps = sum(all_temps) / len(all_temps)
                                temp_range = max(all_temps) - min(all_temps)
                                root[weighdata.name].add_metadata(**{"Mean T" + IN_DEGREES_C: str(mean_temps)})
                                root[weighdata.name].add_metadata(**{"T range" + IN_DEGREES_C: str(temp_range)})
                                mean_rhs = sum(all_rh) / len(all_rh)
                                root[weighdata.name].add_metadata(**{"Mean RH (%)": str(mean_rhs)})

                                """get P from Vaisala database"""
                                all_p = np.asarray([a[0] for a in data(p_database_path, start=startdatetime, end=enddatetime, select='Pressure')])
                                print(all_p)

                                if all_p.any():
                                    mean_P = sum(all_p) / len(all_p)
                                    root[weighdata.name].add_metadata(**{"All Pressures (hPa)": all_p})
                                    root[weighdata.name].add_metadata(**{"Pressure (hPa)": str(min(all_p)) + " to " + str(max(all_p))})
                                    root[weighdata.name].add_metadata(**{"Mean Pressure (hPa)": str(mean_P)})

                                    airdens = AirDens2009(mean_temps, mean_P, mean_rhs, 0.0004)
                                    root[weighdata.name].add_metadata(**{"Air density (kg/m3)": str(airdens)})
                                    print(airdens)
                                else:
                                    print(se)

                            except AttributeError:
                                pass

                            except TypeError:
                                ambient_data = ['04-03-2025 20250304', 0, 0, 0, ]

        last_date = start_time.split()[0]
        new_filename = os.path.join(save_folder, last_date + "_" + str(nom) + "_" + se)

        new_json_name = new_filename + "_airdens.json"
        root.save(root=root, file=new_json_name, mode='w', encoding='utf-8', ensure_ascii=False)


if __name__ == "__main__":
    cfg = Config(r"C:\MCW_Config\local_config.xml")
    folder = r'C:\Users\r.hawke\OneDrive - Callaghan Innovation\Desktop\0003b_Pressure'  # folder of data
    json_file = os.path.join(folder, 'PressureStandards_500.json')
    json__root = read(json_file)
    print(json__root)

    add_ambient_metadata(jsonroot=json__root, save_folder=folder, cfg=cfg)

