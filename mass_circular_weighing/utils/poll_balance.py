"""
Test communications with a balance listed in default_config.xml
"""
import sys

from ..constants import admin_default
from ..configuration import Configuration


def find_balance(admin=None, bal_alias=None):
    """Gets a balance instance from the list of known balances and checks the connection is valid

    Parameters
    ----------
    admin : path (optional)
       path to the admin.xlsx file
    bal_alias : str (optional)
       alias of balance to connect to, as set in the config.xml file

    Returns
    -------
    balance instance, which can be used for further interactions
    such as loading, unloading, scale adjust, and mass readings
    """
    if admin is None:
        admin = input("Please enter the path to the admin.xlsx file or press enter to use default.")
    if not admin:
        admin = admin_default
    try:
        app = Configuration(admin)
        default = input("Press enter to continue")  # needed in case config pop-up appears
    except IOError as e:
        print(f'{e.__class__.__name__}: {e}', file=sys.stderr)
        return None

    # determine known balances
    bal_list = []
    for alias, equip in app.equipment.items():
        if "mettler" in equip.manufacturer.lower():
            bal_list.append(alias)
        if "sartorius" in equip.manufacturer.lower():
            bal_list.append(alias)

    # allow user input of balance alias
    if bal_alias is None:
        print("Known balances are: {}".format(", ".join(bal_list)))
        bal_alias = input("Enter alias of balance in use: ")

    # connect to known balance and return some diagnostics
    if bal_alias in bal_list:
        bal, mode = app.get_bal_instance(bal_alias)

        print("Balance mode is {}".format(bal.mode))
        print("Balance unit is set to {}".format(bal.unit))

        if 'w' in bal.mode:
            print("Balance serial number is {}".format(bal.get_serial()))

        print("Current mass reading: {}".format(bal.get_mass_instant()))

        return bal

    else:
        print("Balance not recognised")

        return None
