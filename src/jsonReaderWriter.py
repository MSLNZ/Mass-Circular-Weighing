# Link to MSL-IO?
#
import json


class jsonReaderWriter(object):
    def __init__(self, filename):
        # create a empty dictionary (basically an empty JSON object)
        self.root = dict()
        self.f = filename
        self.save_file()

    def save_file(self):
        with open(self.f, 'w') as outfile:
            json.dump(self.root, outfile, indent=4)

    def create_subgroup(self, subgroup, jsondict='root'):
        # adds a new group to a group or to the root if the folder is not specified
        if jsondict == 'root':
            self.root[subgroup] = dict()
        else:
            jsondict[subgroup] = dict()

        self.save_file()

    def add_metadata(self, metadata, level1folder='root', level2folder=None):
        # adds metadata to a folder or to the root if the folder is not specified
        # TODO: check that this works for a level1folder but no level2folder
        if level1folder == 'root':
            try:
                for key, value in metadata.items():
                    self.root['0: '+self.f][key] = value
            except:
                self.root['0: '+self.f] = dict()
                for key, value in metadata.items():
                    self.root['0: '+self.f][key] = value
        else:
            try:
                for key, value in metadata.items():
                    self.root[level1folder][level2folder][key] = value
            except:
                self.root[level1folder][level2folder] = dict()
                for key, value in metadata.items():
                    self.root[level1folder][level2folder][key] = value

        self.save_file()

    def add_dataset(self, dataset, jsondict='root'):
        # adds data to a folder or to a 'Data' folder in the root directory if the folder is not specified
        if jsondict == 'root':
            try:
                for key, value in dataset.items():
                    self.root['Data'][key] = value
            except:
                self.root['Data'] = dict()
                for key, value in dataset.items():
                    self.root['Data'][key] = value
        else:
            try:
                for key, value in dataset.items():
                    self.root[jsondict][key] = value
            except:
                self.root[jsondict] = dict()
                for key, value in dataset.items():
                    self.root[jsondict][key] = value

        self.save_file()


