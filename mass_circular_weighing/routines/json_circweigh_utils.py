from __future__ import annotations
from typing import TYPE_CHECKING
import os

from datetime import datetime
import numpy as np

from msl.io import JSONWriter, read

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
