"""
A script to run a new weighing without using the gui
"""
from mass_circular_weighing.constants import admin_default
from mass_circular_weighing.configuration import Configuration
from mass_circular_weighing.routines.run_circ_weigh import *
#from mass_circular_weighing.routines.collate_data import collate_a_data_from_json
#from mass_circular_weighing.routines.final_mass_calc import final_mass_calc


def do_new_weighing(config, bal_alias, nominal_mass, scheme_entry, positions=None, cal_pos=1, self_cal=True):
    """Run a circular weighing without using the gui

    Parameters
    ----------
    config : str
        file path to config.xml file
    bal_alias : str
        name of balance to use for weighing
    scheme_entry : str
        weight groups in weighing order, separated by spaces. Group weights in weight group by + sign only.
    nominal_mass : int
        the closest integer to the true mass value of the weight groups

    Returns
    -------
    bool indicating whether the circular weighing met the specified acceptance criteria
    """

    # initialise weighing configuration
    cfg = Configuration(config)
    filename = cfg.client + '_' + str(nominal_mass)

    # get balance instance
    balance, mode = cfg.get_bal_instance(bal_alias)
    balance._positions = positions
    balance.cal_pos = cal_pos
    balance.want_adjust = self_cal
    check_bal_initialised(bal=balance, wtgrps=scheme_entry.split())

    ac = cfg.acceptance_criteria(bal_alias, nominal_mass)

    # collect metadata
    metadata = {
        'Client': cfg.client, 'Balance': bal_alias, 'Bal serial no.': balance.record.serial,
        'Unit': balance.unit, 'Nominal mass (g)': nominal_mass,
    }
    for key, value in ac.items():
        metadata[key] = value

    # get any existing data for scheme_entry
    url = cfg.folder + "\\" + filename + '.json'
    root = check_for_existing_weighdata(cfg.folder, url, scheme_entry)
    run_id = get_next_run_id(root, scheme_entry)

    # do weighing
    weighing_root = do_circ_weighing(balance, scheme_entry, root, url, run_id, **metadata)
    if not weighing_root:
        return False

    # analyse weighing
    weigh_analysis = analyse_weighing(weighing_root, url, scheme_entry, run_id, mode, cfg.timed, cfg.drift)

    return weigh_analysis.metadata.get('Acceptance met?')


if __name__ == "__main__":

    # config = r'I:\MSL\Private\Mass\transfer\Balance Software\Sample Data\LUCY\config.xml' #r'I:\MSL\Private\Mass\transfer\Balance Software\LUCY_BuildUp\config.xml'
    admin = admin_default
    bal_alias = 'XPE505C'  # codename for balance

    scheme_entries = [
        "20KRA 10KMA+10KMB 20KRB 20KRC",
        "20KRB 10KMA+10KMB 20KRC 20KRD",
        "20KRC 10KMA+10KMB 20KRD 20KRA",
        "20KRD 10KMA+10KMB 20KRA 20KRB",
        ]
    # #"500 500MA 500MB" #"3kn10+500mb+50mb+20mb 2ko+2kod 20KRD 10KMA+10KMB 20KRA 20KRB3kn11+500mb+50mb+20mb" #"1a 1b 1c 1d" # "5000 5000MA 5000MB"
    #"2000 2000MA 2000MB"  "1000 1000MA 1000MB"
    # "3kn10+500mb+50mb+20mb 2ko+2kod 3kn11+500mb+50mb+20mb" # pressure calibration example
    # "1 1s 0.5+0.5s" #
    nominal_mass = 100  # nominal mass in g

    scheme_entry = "100 100MA 100MB" #"100kH 50kH+50kHd 100kHdd"
    """The following information is needed for aw mode balances"""
    positions = [2, 3, 4]
    cal_pos = 2

    for i in range(1):
        do_new_weighing(admin, bal_alias, nominal_mass, scheme_entry,
                        positions=positions, cal_pos=cal_pos, self_cal=True)

    # analyse_old_weighing(cfg, filename, scheme_entry, 'run_1')

    # balance, mode = cfg.get_bal_instance(bal_alias)
    #for scheme_entry in scheme_entries:
    # analyse_all_weighings_in_file(cfg, filename, scheme_entries[3])

    #inputdata = collate_a_data_from_json(cfg.folder, filename, scheme_entry)  # gets data in g

    #print(inputdata)


