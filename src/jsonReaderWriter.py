#
# FYI, there is already an MSL-IO package that I was writing that helps create files that have
# the HDF5 concept of Metadata, Groups and Datasets but without having to read/write binary
# HDF5 files. I gave a few talks to MSL'ers in the past. I got feedback during the talks but I
# couldn't get anyone to write code. Basically, you can really think of your JSON object in terms
# of a folder and file structure in Windows. Using terms like Folder, Subfolder, File in a Windows
# context map 1-to-1 in the MSL-IO package. It would allow a hierarchy Windows folder structure
# within a single file (a JSON file for example).
#
# Anyways, now for an example using JSON and structured arrays...
#
import json
from pprint import pprint

import numpy as np

class jsonReaderWriter(object):
    def __init__(self, filename):
        # create a empty dictionary (basically an empty JSON object)
        self.root = dict()
        self.f = filename
        self.save_file(self.f)

    def save_file(self):
        with open(self.f, 'w') as outfile:
            json.dump(self.root, outfile, sort_keys=True, indent=4)
        self.save_file(self.f)

    def add_metadata_file(self, metadata):
        # add metadata to the root (think of this as a Windows folder)
        for key, value in metadata:
            self.root[metadata[key]] = value
        self.save_file(self.f)

    def create_subgroup(self, subgroup, jsondict=root):
        # here assuming we only want two levels of groupings?
        if jsondict == root:
            # create a "subfolder" of the "root" folder
            self.root[subgroup] = dict()
        else:
            jsondict[subgroup] = dict()
        self.save_file(self.f)



spaghetti = jsonReaderWriter('spaghetti.json')

spaghetti.add_metadata_file({'date': '2019-06-19'})


# add metadata to the "subfolder"
root['subfolder']['temperature'] = 20.1
root['subfolder']['humidity'] = 47.8

# add a dataset to the "subfolder"
root['subfolder']['dataset1'] = dict()

# add metadata to "dataset1"
root['subfolder']['dataset1']['unit'] = 'g'
root['subfolder']['dataset1']['header'] = data1.dtype.names

# add data1 to "dataset1"
root['subfolder']['dataset1']['data'] = data1.tolist()

# add a dataset to the "root" folder
root['another_dataset'] = dict()
# add metadata to "dataset1"
root['another_dataset']['unit'] = 'g'

# add data2 to "another_dataset"
# Here we specify the header as the first row instead of in the metadata
root['another_dataset']['data'] = [data2.dtype.names] + data2.tolist()

# save the "root" to a JSON file
with open('my_sample_file.json', 'w') as fp:
    json.dump(root, fp, indent=4)

# load the file that was just created
with open('my_sample_file.json', 'r') as fp:
    reloaded = json.load(fp)

# pprint stands for "pretty print", which is self explanatory
pprint(reloaded)

# convert "another_dataset" back into a structured array

# create the dtype
dtype = np.dtype({
    'names': reloaded['another_dataset']['data'][0],  # the header names
    'formats': [object] * len(reloaded['another_dataset']['data'][0])  # you could just make every column an object...
})

# we must convert each row in the 2D list into a Python tuple
data_as_a_list_of_tuples = [tuple(row) for row in reloaded['another_dataset']['data'][1:]]

# finally create the structured array
get_data_back = np.asarray(data_as_a_list_of_tuples, dtype=dtype)
print(get_data_back)
print(get_data_back['integer'])
