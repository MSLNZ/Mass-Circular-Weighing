import pytest
import numpy as np
import os

from msl.io import read

from mass_circular_weighing.routines.circ_weigh_class import CircWeigh
from mass_circular_weighing.constants import SUFFIX

# testing repeatability of CircWeigh analysis (and json read)
# using data from an Asure Quality calibration
# undertaken in March 2018 using the VBA automatic weighing procedure on HK1000
# and visually compared with the analysis from the VBA program

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
jsonfile_for_test = os.path.join(ROOT_DIR, r'examples\AsureQ_Mar_1000.json')
root = read(jsonfile_for_test)

for ds in root.datasets():
    if 'measurement_run_3' in str(ds.name):
        dataset = ds
    elif 'analysis_run_3' in str(ds.name):
        check_analysis = ds

se = "1000 1000MA 1000MB"
cw = CircWeigh(se)
checkstdevs = {}

drift_keys = ['no drift', 'linear drift', 'quadratic drift', 'cubic drift']


def test_generate_design_matrices():

    for i, grp in enumerate(["1000", "1000MA", "1000MB"]):
        assert cw.wtgrps[i] == grp
    assert cw.num_wtgrps == 3
    assert cw.num_cycles == 4
    assert cw.num_readings == 12

    cw.generate_design_matrices(times=[])
    assert cw.trend == 'reading'
    id = [
        [1., 0., 0.],
        [0., 1., 0.],
        [0., 0., 1.],
        [1., 0., 0.],
        [0., 1., 0.],
        [0., 0., 1.],
        [1., 0., 0.],
        [0., 1., 0.],
        [0., 0., 1.],
        [1., 0., 0.],
        [0., 1., 0.],
        [0., 0., 1.],
    ]

    for key in drift_keys:
        for i in range(12):
            for j in range(3):
                assert id[i][j] == cw.matrices.get(key)[i][j]
                assert cw.matrices.get(key)[i][j] == cw.t_matrices.get(key)[j][i]

    for i, key in enumerate(drift_keys):
        assert cw._driftorder.get(key) == i

        if i > 0:
            for col in range(i):
                for j in range(12):
                    assert cw.matrices.get(key)[j][3+col] == j**(col+1)


def test_determine_drift():

    assert cw.determine_drift(dataset[:, :, 1]) == 'cubic drift'
    # note that this function calls cw.expected_vals_drift(dataset, drift)
    # because the VBA program only uses linear drift correction we need to do the same here:
    assert check_analysis.metadata["Selected drift"] == 'linear drift'

    # extract string from json file and convert back to dict (duh...)
    temp_list = check_analysis.metadata['Residual std devs'].strip("{").strip("}").split(',')

    for i in temp_list:
        i2 = i.split(": ")
        checkstdevs[i2[0].strip().strip("'")] = float(i2[1])

    for key, val in cw.stdev.items():
        assert val == checkstdevs.get(key)
    # here we assume that the residuals are also correct as they are used to determine the stdev


def test_expected_vals_drift(drift=None):

    unit = dataset.metadata['Unit']
    unit2 = check_analysis.metadata["Mass unit"]
    assert unit == unit2

    if not drift:
        drift = check_analysis.metadata["Selected drift"]
    max_stdev = dataset.metadata["Max stdev from CircWeigh (ug)"]
    check_accept = check_analysis.metadata['Acceptance met?']

    cw.expected_vals_drift(dataset[:, :, 1], drift)

    assert cw.stdev[drift] == checkstdevs[drift]

    accept = cw.stdev[drift]*SUFFIX[unit] < max_stdev*SUFFIX['ug']

    # assert accept == check_accept


def test_drift_coeffs(drift=None):

    if not drift:
        drift = check_analysis.metadata["Selected drift"]
    dc = cw.drift_coeffs(drift)
    try:
        for key in drift_keys[1:]:
            check_dc = check_analysis.metadata[key]
            assert dc[key] == check_dc
    except KeyError:
        pass


def test_item_diff(drift=None):

    if not drift:
        drift = check_analysis.metadata["Selected drift"]

    analysis = cw.item_diff(drift)

    for i in range(cw.num_wtgrps):
        for j in range(4):
            if j < 2:
                assert analysis[i][j] == check_analysis[i][j]
            else:
                assert analysis[i][j] == pytest.approx(check_analysis[i][j])
                # assert analysis[i][j] == pytest.approx(check_analysis[i][j])

    # checkdiffs = {}
    # for grp in range(cw.num_wtgrps - 1):
    #     key = 'grp' + str(grp + 1) + ' - grp' + str(grp + 2)
    #     value = "{0:.5g}".format(check_analysis[2][grp]) \
    #             + ' (' + "{0:.3g}".format(check_analysis[3][grp]) + ')'
    #     checkdiffs[key] = value
    #
    # checkdiffs['grp' + str(cw.num_wtgrps) + ' - grp1'] = \
    #     "{0:.5g}".format(check_analysis[2][-1]) \
    #             + ' (' + "{0:.3g}".format(check_analysis[3][-1]) + ')'
    #
    # for key, val in cw.grpdiffs.items():
    #     print(key, val)
    #     print(checkdiffs[key])
    #     # assert val == checkdiffs[key]



if __name__ == '__main__':

    test_generate_design_matrices()
    test_determine_drift()
    test_expected_vals_drift()
    test_drift_coeffs()
    test_item_diff()