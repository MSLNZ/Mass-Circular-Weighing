from __future__ import annotations
from typing import TYPE_CHECKING
import os

from datetime import datetime
import numpy as np

from msl.io import JSONWriter, read

from ..constants import IN_DEGREES_C
from ..utils.airdens_calculator import AirDens2009

from ..log import log
from ..constants import local_backup

if TYPE_CHECKING:
    from msl.io import JSONWriter


def check_for_existing_weighdata(folder, url, se):
    """Reads json file, if it exists, and loads as root object.  Saves backup of existing file.
    Creates new file and corresponding empty root object if file doesn't yet exist.

    Parameters
    ----------
    folder : str
    url : path (full) to json file
    se : str

    Returns
    -------
    root : :class:`root`
        msl.io root object with a group for the given scheme entry in the main group 'Circular Weighings'
    """
    if os.path.isfile(url):
        existing_root = read(url)
        back_up_folder = os.path.join(folder, "backups")
        log.debug(back_up_folder)
        if not os.path.exists(back_up_folder):
            os.makedirs(back_up_folder)
        new_index = len(os.listdir(back_up_folder))  # counts number of files in backup folder
        new_file = os.path.join(back_up_folder, se + '_backup{}.json'.format(new_index))
        existing_root.read_only = False
        log.debug('Existing root is ' + repr(existing_root))
        root = JSONWriter()
        root.set_root(existing_root)
        log.debug('Working root is ' + repr(root))
        root.save(root=existing_root, file=new_file, mode='w', encoding='utf-8', ensure_ascii=False)

    else:
        if not os.path.exists(folder):
            os.makedirs(folder)
        log.debug('Creating new file for weighing')
        root = JSONWriter()

    root.require_group('Circular Weighings')
    root['Circular Weighings'].require_group(se)

    return root


def save_data(root: JSONWriter, url: str, run_id: str, timestamp: datetime = datetime.now(),
              local_backup_folder: str = local_backup, ):
    """Saves data to local drive and attempts to also save to network drive"""
    local_folder = os.path.join(local_backup_folder, os.path.split(os.path.dirname(url))[-1])
    # ensure a unique filename in case of intermittent internet
    local_file = os.path.join(
        local_folder,
        os.path.basename(url).strip('.json') + f'_{run_id}_{timestamp.strftime("%Y%m%d_%H%M%S")}.json'
    )
    if not os.path.exists(local_folder):
        os.makedirs(local_folder)
    root.save(file=local_file, mode='w', encoding='utf-8', ensure_ascii=False)
    try:
        root.save(file=url, mode='w', encoding='utf-8', ensure_ascii=False)
        return True
    except FileNotFoundError:
        log.warning(f'Unable to save to {url}. Please check network connection.')
        log.info(f"Data saved to {local_file}")
        return False


def add_air_densities(root):
    "Mean air density (kg/m3)"

    for weighdata in root.datasets():
        print(weighdata.name)
        if 'measurement' in weighdata.name:

            all_temps = weighdata.metadata.get("All Temps" + IN_DEGREES_C)
            mean_temps = sum(all_temps) / len(all_temps)
            temp_range = max(all_temps) - min(all_temps)
            root[weighdata.name].add_metadata(**{"Mean T" + IN_DEGREES_C: str(mean_temps)})
            root[weighdata.name].add_metadata(**{"T range" + IN_DEGREES_C: str(temp_range)})

            p = weighdata.metadata.get("All Pressures (hPa)")
            all_rh = weighdata.metadata.get("All Humidities (%)")
            mean_rhs = sum(all_rh) / len(all_rh)
            root[weighdata.name].add_metadata(**{"Mean RH (%)": str(mean_rhs)})
            mean_P = sum(p) / len(p)
            root[weighdata.name].add_metadata(**{"Pressure (hPa)": str(min(p)) + " to " + str(max(p))})
            root[weighdata.name].add_metadata(**{"Mean Pressure (hPa)": str(mean_P)})

            if len(p) == len(all_rh) == len(all_temps):
                all_airdens = []
                for i, t in enumerate(all_temps):
                    all_airdens.append(AirDens2009(t, p[i], all_rh[i], 0.0004))
                root[weighdata.name].add_metadata(**{"All air density (kg/m3)": str(all_airdens)})
                airdens = sum(all_airdens) / len(all_airdens)
                ad_stdev = np.std(all_airdens, ddof=1)  # ddof=1 for sample standard deviation
                root[weighdata.name].add_metadata(**{"Stdev air density (kg/m3)": str(ad_stdev)})
            else:
                airdens = AirDens2009(mean_temps, mean_P, mean_rhs, 0.0004)

            root[weighdata.name].add_metadata(**{"Mean air density (kg/m3)": str(airdens)})

    return root


