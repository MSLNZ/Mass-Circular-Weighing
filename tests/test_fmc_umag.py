import os
import numpy as np
import pytest

from msl.io import read, read_table

from mass_circular_weighing.configuration import Configuration
from mass_circular_weighing.constants import MU_STR

from mass_circular_weighing.routine_classes.final_mass_calc_class import FinalMassCalc
from mass_circular_weighing.gui.threads.masscalc_popup import filter_mass_set


ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
admin_for_test = os.path.join(ROOT_DIR, r'tests\samples\admin_umag.xlsx')
# input_data_file_for_test is in admin_for_test

# test data
data_table = read_table(admin_for_test, sheet='InputData')

collated = np.empty(len(data_table),
                    dtype=[('+ weight group', object), ('- weight group', object),
                           ('mass difference (g)', 'float64'), ('balance uncertainty (' + MU_STR + 'g)', 'float64')])
collated['+ weight group'] = data_table[:, 0]
collated['- weight group'] = data_table[:, 1]
for i in range(len(data_table)):
    collated['mass difference (g)'][i] = float(data_table[i, 2])
    collated['balance uncertainty (' + MU_STR + 'g)'][i] = float(data_table[i, 3])

check_fmc = read(os.path.join(ROOT_DIR, r'tests\samples\final_mass_calc\samplefinalmasscalcumag.json'))

cfg = Configuration(admin_for_test)
cfg.init_ref_mass_sets()

client_wts = filter_mass_set(cfg.all_client_wts, collated)
checks = filter_mass_set(cfg.all_checks, collated)
stds = filter_mass_set(cfg.all_stds, collated)

fmc = FinalMassCalc(cfg.folder, cfg.client, client_wts, checks, stds, collated, nbc=True, corr=None)


def test_filter_masses():
    # Here only one of the three standards is used
    stds = filter_mass_set(cfg.all_stds, collated)
    assert len(cfg.all_stds['Weight ID']) > 1
    assert len(stds['Weight ID']) == 1
    assert 5000 in cfg.all_stds['Nominal (g)']
    assert 5000 not in stds['Nominal (g)']
    print(stds['mass values (g)'])

    # Here all client weights are used so should be unchanged
    client_wts = filter_mass_set(cfg.all_client_wts, collated)
    for key, value in cfg.all_client_wts.items():
        if value is None:
            assert client_wts[key] is None
        elif type(value) is int:
            if key == 'Num weights':
                assert client_wts[key] == 10
        else:
            assert len(client_wts[key]) == len(value)
            assert client_wts[key][0] == value[0]
            assert client_wts[key][-1] == value[-1]


def test_file_structure():
    assert 'JSONWriter' in repr(fmc.finalmasscalc)
    assert "Group '/1: Mass Sets'" in repr(fmc.finalmasscalc['1: Mass Sets'])
    assert "<Group '/1: Mass Sets/Client'" in repr(fmc.finalmasscalc['1: Mass Sets']['Client'])
    assert "<Group '/1: Mass Sets/Check'" in repr(fmc.finalmasscalc['1: Mass Sets']['Check'])
    assert "<Group '/1: Mass Sets/Standard'" in repr(fmc.finalmasscalc['1: Mass Sets']['Standard'])


def test_import_mass_lists():
    fmc.import_mass_lists()
    # check client info
    assert fmc.num_client_masses == 10 \
           == fmc.finalmasscalc['1: Mass Sets']['Client'].metadata['Number of masses'] \
           == check_fmc['1: Mass Sets']['Client'].metadata['Number of masses']
    for i in range(fmc.num_client_masses):
        assert fmc.client_wt_IDs[i] == [
            '10000KE', '10000KF', '10000KG', '10000KH', '10000KI', '10000NE', '10000NF', '10000NG', '10000NH', '10000NI'
        ][i] \
               == fmc.finalmasscalc['1: Mass Sets']['Client'].metadata['Weight ID'][i] \
               == check_fmc['1: Mass Sets']['Client'].metadata['Weight ID'][i]

    # check check info
    assert fmc.num_check_masses == 1 \
           == fmc.finalmasscalc['1: Mass Sets']['Check'].metadata['Number of masses'] \
           == check_fmc['1: Mass Sets']['Check'].metadata['Number of masses']
    for i in range(fmc.num_check_masses):
        assert fmc.check_masses['Weight ID'][i] == ['10KMB'][i] \
               == fmc.finalmasscalc['1: Mass Sets']['Check'].metadata['Weight ID'][i] \
               == check_fmc['1: Mass Sets']['Check'].metadata['Weight ID'][i]

    assert fmc.finalmasscalc['1: Mass Sets']['Check']['mass values']
    for row in range(fmc.num_check_masses):
        for j, col in enumerate(fmc.finalmasscalc['1: Mass Sets']['Check']['mass values'][row]):
            assert col == check_fmc['1: Mass Sets']['Check']['mass values'][row][j]
    assert "0 groups, 1 datasets, 4 metadata" in repr(fmc.finalmasscalc['1: Mass Sets']['Check'])

    # check std info
    assert fmc.num_stds == 1 \
           == fmc.finalmasscalc['1: Mass Sets']['Standard'].metadata['Number of masses'] \
           == check_fmc['1: Mass Sets']['Standard'].metadata['Number of masses']
    for i in range(fmc.num_stds):
        assert fmc.std_masses['Weight ID'][i] == [
            '10KMA',
        ][i] \
               == fmc.finalmasscalc['1: Mass Sets']['Standard'].metadata['Weight ID'][i] \
               == check_fmc['1: Mass Sets']['Standard'].metadata['Weight ID'][i]

    for row in range(fmc.num_stds):
        for j, col in enumerate(fmc.finalmasscalc['1: Mass Sets']['Standard']['mass values'][row]):
            assert True
            assert col == check_fmc['1: Mass Sets']['Standard']['mass values'][row][j]

    assert "0 groups, 1 datasets, 4 metadata" in repr(fmc.finalmasscalc['1: Mass Sets']['Standard'])

    # check inputdata
    for i, row in enumerate(collated):
        for j, item in enumerate(row):
            assert item == fmc.inputdata[i][j]

    assert [
        fmc.allmassIDs[i] == [
            '10000KE', '10000KF', '10000KG', '10000KH', '10000KI',
            '10000NE', '10000NF', '10000NG', '10000NH', '10000NI',
            '10KMB', '10KMA'
        ][i] for i in range(len(fmc.allmassIDs))
    ]

    assert fmc.nbc is True
    assert fmc.corr is None

    assert fmc.leastsq_meta =={'Number of observations': 16, 'Number of unknowns': 12, 'Degrees of freedom': 4}


def test_parse_inputdata_to_matrices():
    fmc.parse_inputdata_to_matrices()
    assert fmc.check_design_matrix()

    for i in range(len(collated)):
        assert fmc.y_meas[i] \
               == collated['mass difference (g)'][i] \
               == check_fmc["2: Matrix Least Squares Analysis"]["Input data with least squares residuals"][i][2]
        assert fmc.uncerts[i] \
               == collated['balance uncertainty (' + MU_STR + 'g)'][i] \
               == check_fmc["2: Matrix Least Squares Analysis"]["Input data with least squares residuals"][i][3]

    for j in range(fmc.num_stds):
        assert fmc.y_meas[len(collated) + j] \
               == fmc.finalmasscalc['1: Mass Sets']['Standard']['mass values']['mass values (g)'][j] \
               == check_fmc["2: Matrix Least Squares Analysis"]["Input data with least squares residuals"][len(collated) + j][2]
        assert fmc.uncerts[len(collated) + j] \
               == fmc.finalmasscalc['1: Mass Sets']['Standard']['mass values']['std uncertainties (' + MU_STR + 'g)'][j] \
               == check_fmc["2: Matrix Least Squares Analysis"]["Input data with least squares residuals"][len(collated) + j][3]


def test_least_squares():
    fmc.do_least_squares()

    for i in range(fmc.num_unknowns):  # check that the mass values are consistent to within a ng
        assert fmc.b[i] == \
               pytest.approx(
                   check_fmc["2: Matrix Least Squares Analysis"]["Mass values from least squares solution"][i][3],
                   abs=1e-9
                )

    assert fmc.leastsq_meta['Sum of residues squared (' + MU_STR + 'g^2)'] == 128.83941

    for row in range(len(collated)):
        for col in range(5):
            assert fmc.inputdatares[row][col] == \
                   check_fmc["2: Matrix Least Squares Analysis"]["Input data with least squares residuals"][row][col]


def test_check_residuals():
    fmc.check_residuals()
    with pytest.raises(KeyError) as err:
        flag = fmc.leastsq_meta['Residuals greater than 2 balance uncerts']
    assert 'Residuals greater than 2 balance uncerts' in str(err.value)


def test_cal_rel_unc():
    fmc.cal_rel_unc()
    assert fmc.leastsq_meta['Relative uncertainty for no buoyancy correction (ppm)'] == 0.03

    for i in range(fmc.num_unknowns):
        assert np.round(fmc.std_uncert_b[i], 3) \
               == pytest.approx(check_fmc["2: Matrix Least Squares Analysis"]["Mass values from least squares solution"][i][4])


def test_make_summary_table():
    fmc.make_summary_table()
    for i in range(fmc.num_unknowns):
        for j in range(6):
            if j == 0:
                assert float(fmc.summarytable[i][j]) \
                       == float(check_fmc["2: Matrix Least Squares Analysis"]["Mass values from least squares solution"][i][j])
            else:
                assert fmc.summarytable[i][j] \
                   == check_fmc["2: Matrix Least Squares Analysis"]["Mass values from least squares solution"][i][j]


def test_add_data_to_root():
    fmc.add_data_to_root()


def test_save_to_json_file():
    test_folder = os.path.join(ROOT_DIR, r'tests\samples\final_mass_calc')
    test_file_path = os.path.join(test_folder, cfg.client + '_finalmasscalc.json')
    fmc.save_to_json_file(
        filesavepath=test_file_path,
    )
    assert os.path.isfile(test_file_path)

    test_read = read(test_file_path)
    assert "7 groups, 4 datasets" in repr(test_read)


if __name__ == '__main__':
    test_file_structure()
    test_filter_masses()
    test_import_mass_lists()
    test_parse_inputdata_to_matrices()
    test_least_squares()
    test_check_residuals()
    test_cal_rel_unc()
    test_make_summary_table()
    test_add_data_to_root()
    test_save_to_json_file()
