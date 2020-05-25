import os
import numpy as np

from msl.equipment import Config
from msl import io

from .equip.mdebalance import Balance
from .equip.mettler import MettlerToledo
from .equip.awbalance import AWBal
from .equip.aw_carousel import AWBalCarousel

from .constants import MU_STR, SUFFIX
from .log import log


class Configuration(object):

    def __init__(self, config, ):
        """Initialise the calibration configuration from a config file following msl.equipment rules.
        Assumes specific tags exist in the config file - TODO: make asserts here that the tags exist?

        Parameters
        ----------
        config : path to config.xml file containing relevant parameters
        """

        self.cfg = Config(config)               # loads cfg file
        self.db = self.cfg.database()           # loads database
        self.equipment = self.db.equipment      # loads subset of database with equipment being used

        self.bal_class = {
            'mde': Balance,
            'mw': MettlerToledo,
            'aw': AWBal,
            'aw_c': AWBalCarousel,
        }

        self.EXCL = float(self.cfg.root.find('acceptance_criteria/EXCL').text)

        self.folder = self.cfg.root.find('save_folder').text
        self.job = self.cfg.root.find('job').text
        self.client = self.cfg.root.find('client').text
        self.client_wt_IDs = self.cfg.root.find('client_masses').text

        self.drift_text = self.cfg.root.find('drift').text
        self.timed_text = self.cfg.root.find('use_times').text
        self.correlations = self.cfg.root.find('correlations').text

        self.all_stds = None
        self.all_checks = None
        self.std_set = self.cfg.root.find('std_set').text
        self.check_set_text = self.cfg.root.find('check_set').text

    @property
    def check_set(self):
        if self.check_set_text == 'None':
            return None
        return self.check_set_text

    @property
    def drift(self):
        if self.drift_text == 'auto select':
            return None
        return self.drift_text

    @property
    def timed(self):
        if self.timed_text == 'NO':
            return False
        return True

    def init_ref_mass_sets(self):
        ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        p_std = self.cfg.root.find('standards/'+self.std_set).text
        if os.path.isfile(p_std):
            self.all_stds = load_stds_from_set_file(p_std, 'std')
        elif os.path.isfile(os.path.join(ROOT_DIR,p_std)):
            self.all_stds = load_stds_from_set_file(os.path.join(ROOT_DIR,p_std), 'std')
        else:
            log.error("Standard set file does not exist at specified path: {}".format(p_std))
            return
        self.all_stds['Set name'] = self.std_set

        if self.check_set is not None:
            p_check = self.cfg.root.find('standards/'+self.check_set).text
            if os.path.isfile(p_check):
                self.all_checks = load_stds_from_set_file(p_check, 'check')
            elif os.path.isfile(os.path.join(ROOT_DIR,p_check)):
                self.all_checks = load_stds_from_set_file(os.path.join(ROOT_DIR,p_check), 'check')
            else:
                log.error("Check set file does not exist at specified path: {}".format(p_check))
                return
            self.all_checks['Set name'] = self.check_set
        else:
            self.all_checks = None

    def get_bal_instance(self, alias, strict=True, **kwargs):
        """Selects balance class and returns balance instance

        Parameters
        ----------
        alias : str
            alias for balance in config file
        strict : bool
            not currently used

        Returns
        -------
        Balance instance, mode
        """

        mode = self.equipment[alias].user_defined['weighing_mode']
        bal = self.bal_class[mode](self.equipment[alias], **kwargs)

        return bal, mode

    def get_omega_instance(self, alias):
        """Gets instance of OMEGA logger for ambient measurements

        Parameters
        ----------
        alias : str
            alias for balance in config file where entry is present in Ambient monitoring column in balance register.
            If balance uses an OMEGA logger, entry must be either mass 1, mass 2 or temperature 1

        Returns
        -------
        dict
            dict of ambient logger instance and limits on ambient conditions
        """
        omega_details = self.equipment[alias].user_defined['ambient_monitoring'].split(", sensor ")

        omega = {
            'Inst': omega_details[0],
            'Sensor': int(omega_details[1]),

            'MIN_T': float(self.cfg.root.find('min_temp').text),
            'MAX_T': float(self.cfg.root.find('max_temp').text),
            'MAX_T_CHANGE': float(self.cfg.root.find('max_temp_change').text),

            'MIN_RH': float(self.cfg.root.find('min_rh').text),
            'MAX_RH': float(self.cfg.root.find('max_rh').text),
            'MAX_RH_CHANGE': float(self.cfg.root.find('max_rh_change').text),
        }

        return omega

    def acceptance_criteria(self, alias, nominal_mass):
        """Calculates acceptance criteria for a circular weighing

        Parameters
        ----------
        alias : str
            codename for balance
        nominal_mass : int
            nominal mass of weight group

        Returns
        -------
        dict of {'Max stdev from CircWeigh (ug)': float,
                 'Stdev for balance (ug)': float,
                 }
        """
        record = self.equipment.get(alias)
        if not record:
            raise ValueError('No equipment record')
        man = record.manufacturer
        model = record.model
        serial = record.serial

        path = self.cfg.root.find('acceptance_criteria/path').text
        sheet = self.cfg.root.find('acceptance_criteria/sheet').text

        dataset = io.read_table(path, sheet=sheet)
        header = dataset.metadata.get('header')
        data = dataset.data

        index_map = {}
        for col_name in {'model', 'manufacturer', 'serial',
                         'load max', 'load min', 'acceptable', 'residuals'}:
            for i, name in enumerate(header):
                if col_name in name.lower():
                    index_map[col_name] = i

        store = []
        for row in data:
            if model == row[index_map['model']] \
                and man == row[index_map['manufacturer']] \
                    and float(serial) == row[index_map['serial']]:
                store.append(row)

        if not store:
            raise ValueError('No acceptance criteria for balance')

        for row in store:
            if float(row[index_map['load min']]) <= nominal_mass <= float(row[index_map['load max']]):
                return {
                    'Max stdev from CircWeigh ('+MU_STR+'g)': float(row[index_map['acceptable']]),
                    'Stdev for balance ('+MU_STR+'g)': float(row[index_map['residuals']])/2,
                }

        raise ValueError('Nominal mass out of range of balance')


def load_stds_from_set_file(path, wtset):
    """Collects relevant weight info from SET file for all weights in set

    Parameters
    ----------
    path : path
        location of where to find set file (e.g. cfg.root.find('standards/path').text)
    wtset: str
        specify if std or check weights

    Returns
    -------
    dict
        keys: 'Set Identifier', 'Calibrated', 'weight ID', 'nominal (g)', 'mass values (g)', 'uncertainties (ug)'
    """

    stds = {'Set file': path}
    for key in {'weight ID', 'nominal (g)', 'mass values (g)', 'uncertainties ('+MU_STR+'g)'}:
        stds[key] = []

    with open(path, 'r') as fp:
        if "WeightSetFile" in fp.readline():
            set_name = fp.readline().strip('\n').strip('\"').split()
            if set_name[0] == 'Mettler':
                stds['Set Identifier'] = 'M'+set_name[1]
            else:
                stds['Set Identifier'] = set_name[0]
            log.info(wtset + ' masses use identifier ' + stds['Set Identifier'])
            stds['Calibrated'] = set_name[-1]
            log.info(wtset + ' masses were last calibrated in ' + stds['Calibrated'])
            fp.readline()

            headerline = fp.readline().strip('\n')
            if not headerline == '" nominal (g) "," weight identifier "," value(g) "," uncert (ug) ",' \
                                 '"cov factor","density","dens uncert"':
                log.warn('File format has changed; data sorting may be incorrect')
                log.debug(headerline)

            line = fp.readline()
            while line:
                line = line.strip('\n').split(',')
                for i, key in enumerate(['nominal (g)', 'weight ID', 'mass values (g)', 'uncertainties ('+MU_STR+'g)']):
                    value = line[i].strip()
                    if key == 'weight ID':
                        id = value.strip('\"')
                        trunc_val = '{:g}'.format((float(stds['nominal (g)'][-1])))
                        if float(trunc_val) > 999:
                            trunc_val = '{:g}'.format(float(trunc_val)/1000) + 'K'
                        if stds['Set Identifier'] == 'CUSTOM':
                            stds[key].append(trunc_val + id)
                        else:
                            stds[key].append(trunc_val + id + stds['Set Identifier'])
                    elif key == 'uncertainties ('+MU_STR+'g)':
                        stds[key].append(np.float(value)) # /SUFFIX[MU_STR+'g']
                    else:
                        stds[key].append(np.float(value))

                line = fp.readline()
        else:
            log.error('Weight set file must begin WeightSetFile')

    fp.close()
    return stds

# def get_std_info_excel(path, sheet=None, set_ID=""):
#     std_set_table = read_table_excel(path, sheet=sheet)
#
#     std_set = {'Set file': path}
#     for key in {'weight ID', 'nominal (g)', 'mass values (g)', 'uncertainties (' + MU_STR + 'g)'}:
#         std_set[key] = []
#
#     for r in range(len(std_set_table)):
#         nom = std_set_table[r,0]
#         trunc_val = '{:g}'.format((float(nom)))
#         if float(trunc_val) > 999:
#             trunc_val = '{:g}'.format(float(trunc_val) / 1000) + 'k'
#         if std_set_table[r,1] is
#         std_set['nominal (g)'].append(nom)
#         std_set['weight ID'].append(trunc_val + id + set_ID)
#         std_set['mass values (g)'].append(float(std_set_table[r,2]))
#         std_set['uncertainties (' + MU_STR + 'g)'].append(float(std_set_table[r,2]))
#
#     return std_set


# std_set_path = r'I:\MSL\Private\Mass\transfer\Balance Software\Sample Data\TradingStandards2015\StandardSets.xlsx'
# check_set = get_std_info_excel(std_set_path, sheet='MET13B', set_ID='MB')
# std_set = get_std_info_excel(std_set_path, sheet = 'MET13A', set_ID='MA')

# print(check_set)
# print(std_set)