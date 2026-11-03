"""
Configure the weighing program according to the admin.xlsx file provided.
This file must include a working link to a configuration file, config.xml.
Configuration loads and stores connection information for all balances in the config.xml file, including weight handlers,
as well as ambient logger details and acceptance criteria for each balance.
"""
from msl.equipment import Config, Register, Table

from .equip import Balance, MettlerToledo, AWBalCarousel, AWBalLinear, AT106, get_specification

from .constants import MU_STR, EXCL
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
        self.equipment = self.cfg.equipment      # loads subset of database with equipment being used

        self.bal_class = {
            'mde': Balance,
            'mw': MettlerToledo,
            'aw_c': AWBalCarousel,
            'aw_l': AWBalLinear,
            'aw_106': AT106,
            'aw_d': Balance,
        }

        self.bal_list = []
        for equip in self.equipment:
            if "Balance" in equip.keywords:
                self.bal_list.append(equip.alias)

        self.EXCL = float(EXCL)  #TODO # self.cfg.root.find('acceptance_criteria/EXCL').text)
        # criterion for excluding a single weighing within an automatic weighing sequence, default set arbitrarily at 1.5

    def get_bal_instance(self, alias, strict=True, **kwargs):
        """Selects balance class and returns balance instance.
        Also adds the ambient monitor details to the balance instance

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
        mode = get_specification(self.equipment[alias], 'mode')
        bal = self.bal_class[mode](self.equipment[alias], **kwargs)
        log.debug(
            'Connection information for balance:'
            '\nBalance mode: {} \nEquip record: {} \nBalance instance: {}'.format(
               mode, self.equipment[alias], bal)
        )

        if "aw" in mode:
            bal.handler = self.get_handler_record(bal_alias=alias)
            bal.identify_handler()

        bal._ambient_details = self.get_ambientlogger_info(bal_alias=alias)

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

        handler_alias = get_specification(self.equipment[bal_alias], 'handler')
        record = self.equipment[handler_alias]

        return record

    def get_ambientlogger_info(self, bal_alias):
        """Gets information about Vaisala/milliK or OMEGA logger for ambient measurements

        Parameters
        ----------
        bal_alias : str
            alias for balance in config.xml file where entry is present in Ambient monitoring column in balance register.
                If balance uses a Vaisala/milliK, entry must be the alias for the Vaisala as in the config.xml file
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

        ambient_logger = get_specification(self.equipment[bal_alias], 'ambientMonitoring')

        if 'sensor' in ambient_logger.lower():
            ambient_details["Type"] = "OMEGA"
            omega_details = ambient_logger.split(", sensor ")
            ambient_details['Alias'] = omega_details[0]      # the ithx_name
            ambient_details['Sensor'] = int(omega_details[1])

        elif 'ch' in ambient_logger.lower():
            ambient_details["Type"] = "Vaisala & milliK Databases"
            ambient_details['Alias'] = ambient_logger  # e.g. of form 391119.1CH1-M2430306
            serial_numbers = ambient_logger.split("-")
            ambient_details['milliK'] = serial_numbers[0]
            ambient_details['Vaisala'] = serial_numbers[1]

        elif 'w512' in ambient_logger.lower():
            ambient_details["Type"] = "Vaisala Indigo Database"
            ambient_details['Alias'] = ambient_logger  # e.g. of form 391119.1CH1-M2430306
            serial_numbers = ambient_logger.split("-")
            ambient_details['transmitter'] = serial_numbers[0]
            ambient_details['probe'] = serial_numbers[1]

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
        table_element = self.equipment[alias].specified_requirements.find('table')
        if table_element is None:
            raise ValueError(f'{alias} does not have a <table> child element in <specifiedRequirements>')

        accept_table = Table.from_xml(table_element)
        for row in accept_table:
            if float(row['Nom Load min']) <= nominal_mass <= float(row['Nom Load max']):
                return {
                    'Max stdev from CircWeigh ('+MU_STR+'g)': float(row['Max circweigh stdev']),
                    'Stdev for balance ('+MU_STR+'g)': float(row['Bal stdev'])/2,
                }

        raise ValueError('Nominal mass out of range of balance')
