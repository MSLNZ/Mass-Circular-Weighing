"""
This class requires an .xlsx file in the correct template
"""
import os
import string

from openpyxl import load_workbook

from msl.qt import prompt

from .log import log
from .constants import config_default, client_default, job_default, MU_STR


class AdminDetails(object):

    def __init__(self, path):
        """Administrative details for a calibration are read from an .xlsx file.
        Essential details are checked, and default values used if needed.
        Details of client masses and standard mass sets are stored in dictionary objects.

        Parameters
        ----------
        path : path
            an .xlsx file in the correct template. Use examples/Admin.xlsx as the template.
        """
        self.path = path

        self.wb = load_workbook(path, data_only=True)

        self.ds = self.wb["Admin"]  # note that this will raise an error if the sheet Admin doesn't exist

        self.operator = self.ds['B2'].value

        # Client
        try:
            # remove any spaces if present
            self.client = self.ds['B3'].value.replace(" ", "")
        except AttributeError:
            # no spaces present to remove
            self.client = self.ds['B3'].value
        if not self.client:
            self.client = client_default
            self.ds['B3'] = self.client  # update value in memory
            log.warning(f"No client name specified. Defaulting to {self.client}.")

        # Job
        self.job = self.ds['B4'].value
        if not self.job:
            self.job = job_default
            self.ds['B4'] = self.job
            log.warning(f"No job number specified. Defaulting to {self.job}.")

        # Save Folder
        try:
            self.folder = self.ds['B5'].value.encode('unicode-escape').decode()  # convert to raw string
            if not os.path.exists(self.folder):
                os.makedirs(self.folder)
        except AttributeError:  # no folder specified
            # get folder information from where the Admin.xlsx file is coming from
            self.folder = os.path.dirname(self.path)  # save_folder_default
            self.ds['B5'] = self.folder
            log.warning(f"No save folder specified. Defaulting to {self.folder}.")

        # Configuration File
        self.config_xml = self.ds['E11'].value
        if not self.config_xml:
            # look for a config file in the same folder as the Admin.xlsx file
            xml_files = [f for f in os.listdir(self.folder) if f.endswith(".xml")]
            if xml_files:
                config_xml = prompt.item("Select your config.xml file if present", xml_files)
                if config_xml:
                    self.config_xml = os.path.join(self.folder, config_xml)
                    log.warning(f"No config.xml file path specified in {self.path}.")
            if not self.config_xml:
                self.config_xml = config_default  # the example config file in Mass-Circular-Weighing
                log.warning(f"No config.xml file path specified. Defaulting to {self.config_xml}.")
        if not os.path.isfile(self.config_xml):
            raise FileNotFoundError(f"Cannot find the configuration file at {self.config_xml}.")
        self.ds['E11'] = self.config_xml

        # Circular Weighing Analysis Parameters
        self.drift_text = self.ds['E7'].value
        self.timed_text = self.ds['E8'].value
        self.correlations = self.ds['E9'].value

        # Weight Set Information
        self.all_client_wts = self.load_client_set()
        self.client_wt_IDs = self.all_client_wts['Weight ID']

        self.all_stds = None
        self.all_checks = None
        self.massref_path = self.ds['B9'].value
        if not os.path.isfile(self.massref_path):
            # open a browser to find the MASSREF file
            self.massref_path = prompt.filename(
                title="Please select a valid MASSREF file", filters='XLSX files (*.xlsx)', multiple=False
            )
            if not os.path.isfile(self.massref_path):
                raise FileNotFoundError(f"Cannot find the MASSREF file at {self.massref_path}.")
        log.info(f"Found MassRef file at {self.massref_path}")

        self.std_set = self.ds['B10'].value
        if not self.std_set:
            log.error("No reference mass set specified!")
        self.check_set_text = self.ds['B11'].value

        self.scheme = self.load_scheme()

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

    @property
    def check_set(self):
        if self.check_set_text == 'None':
            return None
        return self.check_set_text

    def load_scheme(self):
        """Loads the weighing scheme from the 'Scheme' sheet of an .xlsx file if present"""
        try:
            sheet = self.wb["Scheme"]
        except KeyError:
            log.info('Scheme worksheet does not yet exist in {}'.format(self.path))
            return None

        header = []
        rows = []
        for i, row in enumerate(sheet.values):
            if i == 0:
                header = [item for item in row]
            else:
                rows.append([item for item in row])

        return header, rows

    def load_client_set(self):
        """Collects relevant weight info for all weights in set

        Returns
        -------
        dict
            keys:
                'Set identifier', 'Client', 'Weight ID', 'Nominal (g)', 'Shape/Mark', 'Container',
                'u_mag (mg)', 'Density (kg/m3)', 'u_density (kg/m3)'
        """
        header_row = 14
        wt_dict = {
            'Set identifier': None,   # TODO: alter here if decide to add an identifier to client weights
            'Set type': 'Client',
            'Client': self.client,
        }

        col_name_keys = {
            "weight id": 'Weight ID', "nom": 'Nominal (g)', 'mark': 'Shape/Mark', "container": 'Container',
            'u_mag': 'u_mag (mg)', 'density': 'Density (kg/m3)', 'u_dens': 'u_density (kg/m3)'
        }   # warning: 'u_density' contains 'density' so always use 'u_dens' in xlsx file instead.

        for i in string.ascii_lowercase[:7]:  # go across a row ;)
            key = self.ds[i+str(header_row)].value

            # do a look up to make sure the column name is a valid key
            valid = False
            for code, real_key in col_name_keys.items():
                if code in key.lower():
                    key = real_key
                    valid = True
            if not valid:
                log.warning(f'Error in parsing client weight set: {key} not recognised as a known column header')
            if valid:
                # parse the data in that column
                val = []
                for row in range(header_row + 1, self.ds.max_row):
                    v = self.ds[i + str(row)].value
                    if key == 'Weight ID':
                        if v is None:
                            break
                        else:
                            # ensure all weight IDs are strings
                            val.append(str(v))
                    else:
                        # keep whatever data type makes sense
                        val.append(v)

                wt_dict[key] = val

        if not wt_dict['Weight ID']:
            log.error("No weights in client weight set!")
        else:  # make sure all the lists are the same length as the Weight ID list
            num_weights = len(wt_dict['Weight ID'])
            for key, val in col_name_keys.items():
                wt_dict[val] = wt_dict[val][:num_weights]

        return wt_dict

    def init_ref_mass_sets(self):
        """Collects relevant weight info from MASSREF.xlsx file for all weights in set
        Creates dictionaries for all_stds and all_checks with keys:
            'MASSREF file', 'Sheet name', 'Set name', 'Set type', 'Set identifier', 'Calibrated',
            'Shape/Mark', 'Nominal (g)', 'Weight ID', 'mass values (g)', 'u_cal', 'uncertainties (' + MU_STR + 'g)',
            'u_drift'
        """
        massrefwb = load_workbook(self.massref_path, read_only=True, data_only=True)

        self.all_stds = self.load_set_from_massref(massrefwb, sheet=self.std_set, set_ID="Standard")

        if self.check_set is not None:
            self.all_checks = self.load_set_from_massref(massrefwb, sheet=self.check_set, set_ID='Check')
        else:
            self.all_checks = None

    def load_set_from_massref(self, massrefwb, sheet, set_ID):
        std_sheet = massrefwb[sheet]
        all_stds = {'MASSREF file': self.massref_path, 'Sheet name': sheet, "Set type": set_ID}
        all_stds['Set name'] = std_sheet['B1'].value  # e.g. Mettler 11
        all_stds['Set identifier'] = std_sheet['D1'].value  # e.g. MA
        all_stds['Calibrated'] = str(std_sheet['F1'].value)  # can't serialise/JSONify a datetime object...!

        # use parsing of nominal values to determine last non-empty row
        for key in ['Shape/Mark', 'Nominal (g)', 'Weight ID', 'mass values (g)', 'u_cal', 'uncertainties (' + MU_STR + 'g)',
                    'u_drift']:
            all_stds[key] = []

        start_row = 4
        i = 0
        while True:
            nom = std_sheet[f'B{start_row+i}'].value
            if nom is None:
                break
            if type(nom) is str:
                if nom[-1].lower() == 'k':
                    all_stds['Nominal (g)'].append(int(nom[:-1])*1000)
                else:
                    print(nom)
            else:
                all_stds['Nominal (g)'].append(nom)
            all_stds['Shape/Mark'].append(std_sheet[f'A{start_row + i}'].value)
            wt_id = std_sheet[f'C{start_row + i}'].value
            if wt_id is None:
                wt_id = str(nom).upper() + all_stds['Set identifier']  # here we are forcing k --> K
            all_stds['Weight ID'].append(wt_id)
            mv = std_sheet[f'D{start_row + i}'].value

            all_stds['mass values (g)'].append(mv)
            # all values for uncertainty should be in micrograms
            u_cal = float(std_sheet[f'E{start_row + i}'].value)
            u_drift = float(std_sheet[f'M{start_row + i}'].value)
            u_tot = round((u_cal**2 + u_drift**2)**0.5, 3)
            all_stds['u_cal'].append(u_cal)
            all_stds['u_drift'].append(u_drift)
            all_stds['uncertainties (' + MU_STR + 'g)'].append(u_tot)
            i += 1

        # print(i)  # i now stores the number of non-empty rows
        if i < 1:
            log.error("No weights in standard weight set!")

        return all_stds

    def save_admin(self):
        # triggered by 'Confirm settings' button on main panel of gui
        # update location of new Admin file
        self.path = os.path.join(self.folder, self.client + '_Admin.xlsx')
        # overwrite any previous version of admin details
        self.wb.save(filename=self.path)
        log.info(f'Admin details saved to {self.path}')


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
        keys: 'Set file', 'Set identifier', 'Calibrated', 'Weight ID', 'nominal (g)', 'mass values (g)', 'uncertainties (ug)'
    """

    stds = {'Set file': path}
    for key in {'Weight ID', 'nominal (g)', 'mass values (g)', 'uncertainties ('+MU_STR+'g)'}:
        stds[key] = []

    with open(path, 'r') as fp:
        if "WeightSetFile" in fp.readline():
            set_name = fp.readline().strip('\n').strip('\"').split()
            if set_name[0] == 'Mettler':
                stds['Set identifier'] = 'M'+set_name[1]
            else:
                stds['Set identifier'] = set_name[0]
            log.info(wtset + ' masses use identifier ' + stds['Set identifier'])
            stds['Calibrated'] = set_name[-1]
            log.info(wtset + ' masses were last calibrated in ' + stds['Calibrated'])
            fp.readline()

            headerline = fp.readline().strip('\n')
            if not headerline == '" nominal (g) "," Weight IDentifier "," value(g) "," uncert (ug) ",' \
                                 '"cov factor","density","dens uncert"':
                log.warn('File format has changed; data sorting may be incorrect')
                log.debug(headerline)

            line = fp.readline()
            while line:
                line = line.strip('\n').split(',')
                for i, key in enumerate(['nominal (g)', 'Weight ID', 'mass values (g)', 'uncertainties ('+MU_STR+'g)']):
                    value = line[i].strip()
                    if key == 'Weight ID':
                        id = value.strip('\"')
                        trunc_val = '{:g}'.format((float(stds['nominal (g)'][-1])))
                        if float(trunc_val) > 999:
                            trunc_val = '{:g}'.format(float(trunc_val)/1000) + 'K'
                        if stds['Set identifier'] == 'CUSTOM':
                            stds[key].append(trunc_val + id)
                        else:
                            stds[key].append(trunc_val + id + stds['Set identifier'])
                    elif key == 'uncertainties ('+MU_STR+'g)':
                        stds[key].append(float(value))  # /SUFFIX[MU_STR+'g']
                    else:
                        stds[key].append(float(value))

                line = fp.readline()
        else:
            log.error('Weight set file must begin WeightSetFile')

    fp.close()
    return stds
