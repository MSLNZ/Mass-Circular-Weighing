import numpy as np

from ..configuration import Configuration
from .run_circ_weigh import *
#from mass_circular_weighing.routines.collate_data import collate_a_data_from_json
#from mass_circular_weighing.routines.final_mass_calc import final_mass_calc


def do_new_weighing(cfg, client, bal_alias, folder, filename, scheme_entry, nominal_mass, timed=False, drift='quadratic drift'):
    # get balance instance
    balance, mode = cfg.get_bal_instance(bal_alias)
    ac = cfg.acceptance_criteria(bal_alias, nominal_mass)

    # get OMEGA instance for ambient monitoring
    omega_instance = cfg.get_omega_instance(bal_alias)

    # collect metadata
    metadata = {
        'Client': client, 'Balance': bal_alias, 'Unit': balance.unit, 'Nominal mass (g)': nominal_mass,
    }
    for key, value in ac.items():
        metadata[key] = value

    # get any existing data for scheme_entry
    url = folder + "\\" + filename + '.json'
    root = check_for_existing_weighdata(folder, url, scheme_entry)
    run_id = get_next_run_id(root, scheme_entry)

    weighing_root = do_circ_weighing(balance, scheme_entry, root, url, run_id, omega=omega_instance, **metadata)
    if not weighing_root:
        return False

    weigh_analysis = analyse_weighing(weighing_root, url, scheme_entry, run_id, mode, timed, drift)

    return weigh_analysis.metadata.get('Acceptance met?')


if __name__ == "__main__":

    config = r'I:\MSL\Private\Mass\transfer\Balance Software\Sample Data\LUCY\config.xml' #r'I:\MSL\Private\Mass\transfer\Balance Software\LUCY_BuildUp\config.xml'
    ### initialise configuration
    cfg = Configuration(config)

    # cfg.init_ref_mass_sets()

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
    nominal_mass = 20000  # nominal mass in g
    bal_alias = 'LUCY' # codename for balance
    omega_alias = 'Omega'

    # scheme_entry = "100kH 50kH+50kHd 100kHdd"

    filename = cfg.client + '_' + str(nominal_mass) # + '_' + run_id

    # for i in range(1):
    #     do_new_weighing(cfg, cfg.client, bal_alias, cfg.folder, filename, scheme_entry, nominal_mass,
    #                     timed=cfg.timed, drift=cfg.drift)

    # analyse_old_weighing(cfg, filename, scheme_entry, 'run_1')

    # balance, mode = cfg.get_bal_instance(bal_alias)
    #for scheme_entry in scheme_entries:
    analyse_all_weighings_in_file(cfg, filename, scheme_entries[3])

    #inputdata = collate_a_data_from_json(cfg.folder, filename, scheme_entry)  # gets data in g

    #print(inputdata)

    '''
    client_wt_IDs = ['100', '50']
    check_wt_IDs = ['1000MB']
    std_wt_IDs = ['1000MA']

    check_wts = cfg.all_checks

    i_s = cfg.all_stds['weight ID'].index('1000.000MA')
    i_c = check_wts['weight ID'].index('1000.000MB')

    std_masses = np.empty(len(std_wt_IDs), dtype={
        'names': ('std weight ID', 'std mass values (g)', 'std uncertainties (ug)'),
        'formats': (object, np.float, np.float)})

    std_masses['std weight ID'] = std_wt_IDs
    std_masses['std mass values (g)'] = cfg.all_stds['mass values (g)'][i_s]
    std_masses['std uncertainties (ug)'] = cfg.all_stds['uncertainties (ug)'][i_s]

    #print(std_masses)

    filesavepath = 'savefilehere2.json'
    #final_mass_calc(filesavepath, client, client_wt_IDs, check_wt_IDs, std_masses, inputdata)
    '''

