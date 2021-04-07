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
        """Administrative details are read from an .xlsx file.
        Essential details are checked, and default values used if needed.
        Client masses are stored as a dictionary which is similar to the standard mass sets in the Configuration class.

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
        self.std_set = self.ds['B10'].value
        if not self.std_set:
            log.error("No reference mass set specified!")
        self.check_set_text = self.ds['B11'].value

        self.scheme = self.load_scheme()

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
            keys: 'Set Identifier', 'weight ID', 'nominal (g)', 'Marking', 'Container', 'u_mag (ug)', 'Density', 'u_density'
        """
        header_row = 14
        wt_dict = {'Set Identifier': None}  # TODO: alter here if decide to add an identifier to client weights

        for i in string.ascii_lowercase[:7]:  # go across a row ;)
            key = self.ds[i+str(header_row)].value

            val = []
            for row in range(header_row + 1, self.ds.max_row):
                v = self.ds[i + str(row)].value
                if v is not None:
                    if key == 'Weight ID':
                        # ensure all weight IDs are strings
                        val.append(str(v))
                    else:
                        # keep whatever data type makes sense
                        val.append(v)

            wt_dict[key] = val

        if not wt_dict['Weight ID']:
            log.error("No weights in client weight set!")

        return wt_dict

    def save_admin(self):
        # triggered by 'Confirm settings' button on main panel of gui
        # update location of new Admin file
        self.path = os.path.join(self.folder, self.client + '_Admin.xlsx')
        # overwrite any previous version of admin details
        self.wb.save(filename=self.path)
        log.info(f'Admin details saved to {self.path}')


if __name__ == "__main__":

    ad = AdminDetails(r"C:\Users\r.hawke\PycharmProjects\Mass-Circular-Weighing\examples\Admin.xlsx")
    print(ad.all_client_wts)
    print(ad.scheme)
    print(ad.folder)
    print(ad.config_xml)
