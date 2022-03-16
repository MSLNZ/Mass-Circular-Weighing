import pytest
import os

from msl.io import read

from mass_circular_weighing.routine_classes.circ_weigh_class import CircWeigh
from mass_circular_weighing.constants import SUFFIX

# testing consistency of CircWeigh analysis and json read
# using data from MSLT.M.001.008 Appendix C. Typical Printout for a Circular Weighing
# which used the DOS program for analysis

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
jsonfile_for_test = os.path.join(ROOT_DIR, r'tests\samples\TP_AppendixC_100.json')
root = read(jsonfile_for_test)

se = "100 100s 50+50s"
cw = CircWeigh(se)
checkstdevs = {}

drift_keys = ['no drift', 'linear drift', 'quadratic drift', 'cubic drift']


def do_generate_design_matrices():

    for i, grp in enumerate(se.split()):
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


def do_determine_drift(dataset, check_analysis):

    assert cw.determine_drift(dataset[:, :, 1]) == 'quadratic drift'
    # note that this function calls cw.expected_vals_drift(dataset, drift)
    # the DOS program uses quadratic drift correction so we need to assert that this was used:
    assert check_analysis.metadata["Selected drift"] == 'quadratic drift'

    # extract string from json file and convert back to dict (duh...)
    temp_list = check_analysis.metadata['Residual std devs'].strip("{").strip("}").split(',')

    for i in temp_list:
        i2 = i.split(": ")
        checkstdevs[i2[0].strip().strip("'")] = float(i2[1])

    for key, val in cw.stdev.items():
        assert val == checkstdevs.get(key)
    # here we assume that the residuals are also correct as they are used to determine the stdev

    # TODO
    # assert cw.residuals['quadratic drift'] == 0.000029219  # I don't seem to get this number at all?!


def do_expected_vals_drift(dataset, check_analysis, drift=None):

    unit = dataset.metadata['Unit']
    unit2 = check_analysis.metadata["Mass unit"]
    assert unit == unit2

    if not drift:
        drift = check_analysis.metadata["Selected drift"]
    max_stdev = dataset.metadata["Max stdev from CircWeigh (µg)"]
    check_accept = check_analysis.metadata['Acceptance met?']

    cw.expected_vals_drift(dataset[:, :, 1], drift)

    assert cw.stdev[drift] == checkstdevs[drift]

    accept = cw.stdev[drift]*SUFFIX[unit] < max_stdev*SUFFIX['ug']
    # note that the mde balance class was used to enter the data and thus the acceptance criterion is as used here.
    # In reality, the weighing was on the AT201 for which acceptance criteria no longer exist.
    assert accept == check_accept


def do_drift_coeffs(check_analysis, drift=None):

    if not drift:
        drift = check_analysis.metadata["Selected drift"]
    dc = cw.drift_coeffs(drift)
    try:
        for key in drift_keys[1:]:
            check_dc = check_analysis.metadata[key]
            assert dc[key] == check_dc
    except KeyError:
        pass

    # assert drift coefficients are as per TP to within the final decimal place
    assert float(cw.driftcoeffs['linear drift'].split()[0]) == pytest.approx(0.000003735, abs=1e-9)
    assert float(cw.driftcoeffs['quadratic drift'].split()[0]) == pytest.approx(-0.000000257, abs=1e-9)


def do_item_diff(check_analysis, drift=None):

    if not drift:
        drift = check_analysis.metadata["Selected drift"]

    analysis = cw.item_diff(drift)

    for i in range(cw.num_wtgrps):
        for j in range(4):
            if j < 2:
                assert analysis[i][j] == check_analysis[i][j]
            else:
                assert analysis[i][j] == pytest.approx(check_analysis[i][j])

    checkdiffs = {}

    for grp in range(cw.num_wtgrps - 1):
        key = 'grp' + str(grp + 1) + ' - grp' + str(grp + 2)
        value = "{0:.5g}".format(check_analysis[grp][2]) \
                + ' (' + "{0:.3g}".format(check_analysis[grp][3]) + ')'
        checkdiffs[key] = value

    checkdiffs['grp' + str(cw.num_wtgrps) + ' - grp1'] = \
        "{0:.5g}".format(check_analysis[-1][2]) \
                + ' (' + "{0:.3g}".format(check_analysis[-1][3]) + ')'

    # assert mass differences are as in TP to one d.p.
    # 100-100s       0.000126168
    # 100s-(50+50s) -0.000141846
    # 50+50s-100     0.000015678
    checkvals = {
                    "grp1 - grp2": 0.000126168,
                    "grp2 - grp3": -0.000141846,
                    "grp3 - grp1": 0.000015678,
    }
    for key, val in cw.grpdiffs.items():
        assert val == checkdiffs[key]
        assert float(val.split()[0]) == pytest.approx(checkvals[key], abs=1e-8)


def test_run_analysis():
    for i in range(1, 7):

        # find the appropriate data
        for ds in root.datasets():
            if 'measurement_run_'+str(i) in str(ds.name):
                dataset = ds
            elif 'analysis_run_'+str(i) in str(ds.name):
                check_analysis = ds

        # do the analysis and check that it is consistent with the example json file data
        do_generate_design_matrices()
        do_determine_drift(dataset, check_analysis)
        do_expected_vals_drift(dataset, check_analysis)
        do_drift_coeffs(check_analysis, 'quadratic drift')
        do_item_diff(check_analysis, 'quadratic drift')


if __name__ == '__main__':

    test_run_analysis()