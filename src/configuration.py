from msl.equipment import Config
from .equip.mdebalance import Balance
from .equip.mettler import MettlerToledo

from .constants import MU_STR
from .log import log

import numpy as np


class Configuration(object):

    def __init__(self, config, stdset, checkset):

        self.cfg = Config(config)               # loads cfg file
        self.db = self.cfg.database()           # loads database
        self.equipment = self.db.equipment      # loads subset of database with equipment being used

        self.bal_class = {'mde': Balance, 'mw': MettlerToledo, 'aw': Balance}
        # TODO: add aw class for automatic loading balance

        self.all_stds = load_stds_from_set_file(self.cfg.root.find('standards/'+stdset).text, 'std')
        self.all_checks = load_stds_from_set_file(self.cfg.root.find('standards/'+checkset).text, 'check')

        self.SQRT_F = float(self.cfg.root.find('acceptance_criteria/SQRT_F').text)
        self.EXCL = float(self.cfg.root.find('acceptance_criteria/EXCL').text)

    def get_bal_instance(self, alias, strict=True):
        """Selects balance class and returns balance instance

        Parameters
        ----------
        alias : str
            alias for balance in config file
        strict : bool
            not currently used

        Returns
        -------
        Balance instance
        """

        mode = self.equipment[alias].user_defined['weighing_mode']
        bal = self.bal_class[mode](self.equipment[alias])

        return bal

    def get_omega_instance(self, alias):
        """Gets instance of OMEGA logger for ambient measurements

        Parameters
        ----------
        alias : str
            alias for OMEGA logger. Must be either mass 1, mass 2 or temperature 1

        Returns
        -------
        dict
            dict of OMEGA instance and limits on ambient conditions
        """
        omega = {
            'Inst': alias,

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

        # note that this reader works for 2D table with one header line
        header, data = self.db._read_excel(path, sheet, None)

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
                    and serial == row[index_map['serial']]:
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

    stds = {}
    for key in {'weight ID', 'nominal (g)', 'mass values (g)', 'uncertainties ('+MU_STR+'g)'}:
        stds[key] = []

    with open(path, 'r') as fp:
        if "WeightSetFile" in fp.readline():
            set_name = fp.readline().strip('\n').strip('\"').split()
            if set_name[0] == 'Mettler':
                stds['Set Identifier'] = 'M'+set_name[1]
            else:
                stds['Set Identifier'] = set_name[0]
            log.info(wtset + ' weights use identifier ' + stds['Set Identifier'])
            stds['Calibrated'] = set_name[-1]
            log.info(wtset + ' weights were last calibrated in ' + stds['Calibrated'])
            fp.readline()

            headerline = fp.readline().strip('\n')
            if not headerline == '" nominal (g) "," weight identifier "," value(g) "," uncert (g) ",' \
                                 '"cov factor","density","dens uncert"':
                print('File format has changed; data sorting may be incorrect')
                print(headerline)

            line = fp.readline()
            while line:
                line = line.strip('\n').split(', ')
                for i, key in enumerate(['nominal (g)', 'mass values (g)', 'uncertainties ('+MU_STR+'g)']):
                    value = line[i].strip(' ').strip(',\"\"')
                    trunc_val = ('{:g}'.format((float(value))))
                    if i == 0:
                        stds['weight ID'].append(trunc_val + stds['Set Identifier'])  #
                    stds[key].append(np.float(trunc_val))

                line = fp.readline()
        else:
            log.error('Weight set file must begin WeightSetFile')

    fp.close()
    return stds

