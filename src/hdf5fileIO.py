import os
import h5py
from .log import log

class HDF5Writer(object):
    def __init__(self, folder, filename, extn='.hdf5'):
        """Initialises an hdf5 writer for a particular file"""
        self.calfile = os.path.join(folder, filename + extn)  # concatenates to form full path
        log.info('Calibration file is saved as '+os.path.join(folder, filename+extn))
        self.cal_log = self.open_file()

    def open_file(self):
        """HDF5 Writer to open or create a file to record results and parameters of a mass calibration

        Parameters
        ----------
        folder : str
            path to folder containing file to open or create
        filename : str
            name of individual file to open or create
        extn : str
            optional, default is .hdf5
        """
        if not os.path.isfile(self.calfile):
            self.cal_log = self.create_h5_file(self.calfile)  # creates file if it does not exist
        else:
            self.cal_log = h5py.File(self.calfile, 'a')  # opens file if it does exist
            # TODO: currently not working if file already exists...

        return self.cal_log

    def create_h5_file(self, filetocreate, mode='a'):
        """Creates an hdf5 file for a given calibration run with pre-existing groups

        Parameters
        ----------
        filetocreate : str
        mode : str
            append 'a' (default) or write 'w'

        Returns
        -------
        h5py file object
            root contains groups Scheme, CircularWeighings, FinalMassCalculation, Equipment, Logging.
            Scheme contains group MassSets.

        """
        self.cal_log = h5py.File(filetocreate, mode=mode)
        self.cal_log.create_group('1: Parameters')
        self.cal_log.create_group('2: Circular Weighings')
        self.cal_log.create_group('3: Final Mass Calculation')

        return self.cal_log

    def get_item(self, item):
        return self.cal_log[item]

    def create_group(self, parentgroup, subgroup):
        """Create group within an existing group

        Parameters
        ----------
        parentgroup : str
            existing group in which new group will be created
        subgroup : str
            name of new group to create

        Returns
        -------
        Group
            newly created group in h5py file object
        """
        obj = self.cal_log[parentgroup]
        obj.create_group(subgroup)

        return self.cal_log[subgroup]

    def save_data(self, dataset, group, data):
        """Saves data as dataset in group

        Parameters
        ----------
        dataset : str
            name of dataset
        group : str
            name of group into which dataset will be saved
        data : array # if this is allowed?
            Array of data e.g. from circular weighing or

        Returns
        -------
        Dataset
            the dataset into which the data was saved
        """
        obj = self.cal_log[group]
        obj.create_dataset(dataset, data)

        return self.cal_log[dataset]

    def add_metadata(self, name, **metadata):
        """Adds metadata to an existing group or dataset in an HDF5 file

        Parameters
        ----------
        name : str
            name of group or dataset
        metadata : dict
            dictionary of key-value pairs to add as attributes

        Returns
        -------
        Group or Dataset
            group or dataset in hdf5 file to which objects were attributed
        """
        obj = self.cal_log[name]
        # TODO: what if this group or dataset does not exist? should be able to use require_group ??
        for key, value in metadata.items():
            obj.attrs[key] = value

        return obj

    #def check_equipment_record(self):
        # TODO: get a list of equipment from cfg, check if new equipment is being used, if so, add to equipment dataset

