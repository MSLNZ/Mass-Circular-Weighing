"""
Configure the weighing program according to the admin.xlsx file provided.
This file must include a working link to a configuration file, config.xml.
Configuration loads and stores connection information for all balances in the config.xml file, including weight handlers,
as well as ambient logger details and acceptance criteria for each balance.
"""
import os

from msl.equipment import Config, utils
from msl.io import read_table

from .equip import Balance, MettlerToledo, AWBalCarousel, AWBalLinear
from .equip import Vaisala

from .constants import MU_STR
from .log import log
from .admin_details import AdminDetails


class Configuration(AdminDetails):

    def __init__(self, adminxlsx):
        """Initialise the equipment configuration from an admin.xlsx and a config file following msl.equipment rules.
        Assumes that the admin.xlsx file follows the template, and that specific tags exist in the config.xml file.

        Parameters
        ----------
        adminxlsx : path
            to admin.xlsx file which contains administrative calibration details including path to config.xml file
        """
        super().__init__(adminxlsx)

        self.cfg = Config(self.config_xml)      # loads cfg file

        try:
            self.db = self.cfg.database()       # loads database
        except ValueError as e:                 # can't find the named sheet
            log.debug(e)
            # update root with name of the computer running this Python script
            root = self.cfg.root
            root.find('connections/connection/sheet').text = os.environ['COMPUTERNAME']

            # save config to the folder specified in AdminDetails
            new_config = os.path.join(self.folder, self.job + '_config.xml')
            with open(new_config, mode='w', encoding='utf-8') as fp:
                fp.write(utils.convert_to_xml_string(root))
            self.config_xml = new_config

            self.cfg = Config(self.config_xml)  # reload cfg file
            self.db = self.cfg.database()       # loads database

        self.equipment = self.db.equipment      # loads subset of database with equipment being used

        self.bal_class = {
            'mde': Balance,
            'mw': MettlerToledo,
            'aw_c': AWBalCarousel,
            'aw_l': AWBalLinear,
            'aw_d': Balance,
        }

        self.EXCL = float(self.cfg.root.find('acceptance_criteria/EXCL').text)

    def get_bal_instance(self, alias, strict=True, **kwargs):
        """Selects balance class and returns balance instance.
        Also adds the ambient monitor instance and/or details to the balance instance

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
        log.debug('Connection information for balance:'
                  '\nBalance mode: {} \nEquip record: {} \nBalance instance: {}'.format(mode, self.equipment[alias], bal))

        if mode == "aw_l":
            bal.handler = self.get_handler_record(bal_alias=alias)
            bal.identify_handler()

        bal._ambient_details = self.get_ambientlogger_info(bal_alias=alias)

        if 'vaisala' in bal.ambient_details['Type'].lower():
            vai_record = self.equipment.get(bal.ambient_details['Alias'])
            if not vai_record:
                raise ValueError('No equipment record for {}'.format(bal.ambient_details['Alias']))
            bal._ambient_instance = Vaisala(vai_record)
            bal._ambient_details["Manufacturer"] = vai_record.manufacturer
            bal._ambient_details["Model"] = vai_record.model
            bal._ambient_details["Serial"] = vai_record.serial

        elif "omega" in bal.ambient_details['Type'].lower():
            bal._ambient_instance = "OMEGA"

        return bal, mode

    def get_handler_record(self, bal_alias):
        """Gets the EquipmentRecord for the balance handler (e.g. an Arduino)

        Parameters
        ----------
        bal_alias

        Returns
        -------
        EquipmentRecord
        """

        handler_alias = self.equipment[bal_alias].user_defined['handler']
        record = self.equipment.get(handler_alias)

        return record

    def get_ambientlogger_info(self, bal_alias):
        """Gets information about Vaisala or OMEGA logger for ambient measurements

        Parameters
        ----------
        bal_alias : str
            alias for balance in config.xml file where entry is present in Ambient monitoring column in balance register.
                If balance uses a Vaisala, entry must be the alias for the Vaisala as in the config.xml file
                If balance uses an OMEGA logger, entry must be of format ithx_name, sensor (see LabEnviron64)
                (e.g. 'mass 1, sensor 1' or 'mass 2, sensor 1', or 'temperature 1, sensor 2' etc)

        Returns
        -------
        dict
            dict of ambient logger info and limits on ambient conditions
        """
        ambient_details = {
            'MIN_T': float(self.cfg.root.find('min_temp').text),
            'MAX_T': float(self.cfg.root.find('max_temp').text),
            'MAX_T_CHANGE': float(self.cfg.root.find('max_temp_change').text),

            'MIN_RH': float(self.cfg.root.find('min_rh').text),
            'MAX_RH': float(self.cfg.root.find('max_rh').text),
            'MAX_RH_CHANGE': float(self.cfg.root.find('max_rh_change').text),
        }

        ambient_logger = self.equipment[bal_alias].user_defined['ambient_monitoring']

        if 'vaisala' in ambient_logger.lower():
            ambient_details["Type"] = "Vaisala"
            ambient_details['Alias'] = ambient_logger

        elif 'sensor' in ambient_logger.lower():
            ambient_details["Type"] = "OMEGA"
            omega_details = ambient_logger.split(", sensor ")
            ambient_details['Alias'] = omega_details[0]      # the ithx_name
            ambient_details['Sensor'] = int(omega_details[1])

        else:
            log.error("Ambient monitoring device not recognised")
            return None

        return ambient_details

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

        dataset = read_table(path, sheet=sheet)
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
                    and str(serial) == str(row[index_map['serial']]):
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
