import pytest
import numpy as np
import os

from msl.io import read

from mass_circular_weighing.routines.circ_weigh_class import CircWeigh
from mass_circular_weighing.constants import SUFFIX

# testing repeatability of CircWeigh analysis (and json read)
# using data from an Asure Quality calibration
# undertaken in March 2018 using the automatic weighing procedure
# and visually compared with the analysis from the VBA program

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
jsonfile_for_test = os.path.join(ROOT_DIR, r'examples\AsureQ_Mar_1000.json')
root = read(jsonfile_for_test)

for ds in root.datasets():
    if 'measurement_run_3' in str(ds.name):
        dataset = ds
    elif 'analysis_run_3' in str(ds.name):
        analysis = ds

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

    cw.determine_drift(dataset[:, :, 1])
    # note that this function calls cw.expected_vals_drift(dataset, drift)

    # extract string from json file and convert back to dict (duh...)
    temp_list = analysis.metadata['Residual std devs'].strip("{").strip("}").split(',')

    for i in temp_list:
        i2 = i.split(": ")
        checkstdevs[i2[0].strip().strip("'")] = float(i2[1])

    for key, val in cw.stdev.items():
        assert val == checkstdevs.get(key)
    # here we assume that the residuals are also correct as they are used to determine the stdev


def test_expected_vals_drift():

    unit = dataset.metadata['Unit']
    unit2 = analysis.metadata["Mass unit"]
    assert unit == unit2

    drift = analysis.metadata["Selected drift"]
    max_stdev = dataset.metadata["Max stdev from CircWeigh (ug)"]
    check_accept = analysis.metadata['Acceptance met?']

    cw.expected_vals_drift(dataset[:, :, 1], drift)

    assert cw.stdev[drift] == checkstdevs[drift]

    accept = cw.stdev[drift]*SUFFIX[unit] < max_stdev*SUFFIX['ug']
    assert accept == check_accept


def test_drift_coeffs():

    drift = analysis.metadata["Selected drift"]
    dc = cw.drift_coeffs(drift)
    try:
        for key in drift_keys[1:]:
            check_dc = analysis.metadata[key]
            assert dc[key] == check_dc
    except KeyError:
        pass


def test_item_diff():

    analysis = cw.item_diff('quadratic drift')
    checkdata = np.array([('1a', '1b', -722.08054435, 0.34277932),
              ('1b', '1c', -2337.70520833, 0.34201342),
              ('1c', '1d', -924.02987231, 0.34277932),
              ('1d', '1a', 3983.815625, 0.35750859)],
             dtype=[('+ weight group', 'O'), ('- weight group', 'O'), ('mass difference', '<f8'), ('residual', '<f8')])
    for i in range(4):
        for j in range(4):
            if j < 2:
                assert analysis[i][j] == checkdata[i][j]
            else:
                assert analysis[i][j] == pytest.approx(checkdata[i][j])

    checkdiffs = {
        'grp1 - grp2': '-722.08 (0.343)',
        'grp2 - grp3': '-2337.7 (0.342)',
        'grp3 - grp4': '-924.03 (0.343)',
        'grp4 - grp1': '3983.8 (0.358)'
    }
    for key, val in cw.grpdiffs.items():
        assert val == checkdiffs[key]



if __name__ == '__main__':

    test_generate_design_matrices()
    test_determine_drift()
    test_expected_vals_drift()
    test_drift_coeffs()
    # test_item_diff()