"""
These tests use data from a calibration for Hort. Research in 2000
"""
import os
import numpy as np
import pytest

from msl.io import read, read_table

from mass_circular_weighing.configuration import Configuration
from mass_circular_weighing.constants import MU_STR

from mass_circular_weighing.routine_classes.final_mass_calc_class import FinalMassCalc
from mass_circular_weighing.gui.threads.masscalc_popup import filter_mass_set
from mass_circular_weighing.routine_classes.results_summary_Excel import ExcelSummaryWorkbook


ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
admin_for_test = os.path.join(ROOT_DIR, r'tests\samples\Hort.Res._Admin.xlsx')
input_data_file_for_test = os.path.join(ROOT_DIR, r'tests\samples\final_mass_calc\LeastSquaresInputData_TPAppendixD.xlsx')

# Create the table of input data
data_table = read_table(input_data_file_for_test, sheet='Mass Differences')
collated = np.empty(len(data_table),
                    dtype=[('+ weight group', object), ('- weight group', object),
                           ('mass difference (g)', 'float64'), ('balance uncertainty (' + MU_STR + 'g)', 'float64'),
                           ('residual ('+MU_STR+'g)', 'float64')])
collated['+ weight group'] = data_table[:, 0]
collated['- weight group'] = data_table[:, 1]
for i in range(len(data_table)):
    collated['mass difference (g)'][i] = float(data_table[i,2])
    collated['balance uncertainty (' + MU_STR + 'g)'][i] = float(data_table[i, 3])
    collated['residual ('+MU_STR+'g)'][i] = float(data_table[i, 4])

# Create the data table in "Mass values from least squares solution" which has headers
# ['Nominal (g)', 'Weight ID', 'Set ID', 'Mass value (g)', 'Uncertainty (' + MU_STR + 'g)', '95% CI', 'Cov', "Reference value (g)"]
check_fmc = read_table(input_data_file_for_test, sheet='Output')

cfg = Configuration(admin_for_test)
cfg.init_ref_mass_sets()

# client_wt_ids = cfg.client_wt_IDs
checks = filter_mass_set(cfg.all_checks, collated)

fmc = FinalMassCalc(cfg.folder, cfg.client, cfg.all_client_wts, checks, cfg.all_stds, collated, nbc=True, corr=None)


def test_filter_masses():
    # Here all standards are used so stds should be unchanged
    stds = filter_mass_set(cfg.all_stds, collated)
    for key, value in cfg.all_stds.items():
        if value is None:
            assert stds[key] is None
        elif type(value) is int:
            assert stds[key] == value
        else:
            assert len(stds[key]) == len(value)
            assert stds[key][0] == value[0]
            assert stds[key][-1] == value[-1]

    # Here all client weights are used so also should be unchanged
    stds = filter_mass_set(cfg.all_client_wts, collated)
    for key, value in cfg.all_client_wts.items():
        if value is None:
            assert stds[key] is None
        elif type(value) is int:
            assert stds[key] == value
        else:
            assert len(stds[key]) == len(value)
            assert stds[key][0] == value[0]
            assert stds[key][-1] == value[-1]


def test_file_structure():
    assert 'JSONWriter' in repr(fmc.finalmasscalc)
    assert "Group '/1: Mass Sets'" in repr(fmc.finalmasscalc['1: Mass Sets'])
    assert "<Group '/1: Mass Sets/Client'" in repr(fmc.finalmasscalc['1: Mass Sets']['Client'])
    assert "<Group '/1: Mass Sets/Check'" in repr(fmc.finalmasscalc['1: Mass Sets']['Check'])
    assert "<Group '/1: Mass Sets/Standard'" in repr(fmc.finalmasscalc['1: Mass Sets']['Standard'])


def test_import_mass_lists():
    fmc.import_mass_lists()
    # check client info
    assert fmc.num_client_masses == 9 \
           == fmc.finalmasscalc['1: Mass Sets']['Client'].metadata['Number of masses']
    for i in range(fmc.num_client_masses):
        assert fmc.client_wt_IDs[i] == ['100', '50', '20', '20d', '10', '5', '2', '2d', '1'][i] \
               == fmc.finalmasscalc['1: Mass Sets']['Client'].metadata['Weight ID'][i]

    # check check info
    assert fmc.num_check_masses == 2 \
           == fmc.finalmasscalc['1: Mass Sets']['Check'].metadata['Number of masses']
    for i in range(fmc.num_check_masses):
        assert fmc.check_masses['Weight ID'][i] == ['5w', '1w'][i] \
               == fmc.finalmasscalc['1: Mass Sets']['Check'].metadata['Weight ID'][i]
    assert fmc.finalmasscalc['1: Mass Sets']['Check']['mass values']
    assert "0 groups, 1 datasets, 4 metadata" in repr(fmc.finalmasscalc['1: Mass Sets']['Check'])

    # check std info
    assert fmc.num_stds == 7 \
           == fmc.finalmasscalc['1: Mass Sets']['Standard'].metadata['Number of masses']
    for i in range(fmc.num_stds):
        assert fmc.std_masses['Weight ID'][i] == ['100s', '50s', '20s', '10s', '5s', '2s', '1s'][i] \
               == fmc.finalmasscalc['1: Mass Sets']['Standard'].metadata['Weight ID'][i]

    assert "0 groups, 1 datasets, 4 metadata" in repr(fmc.finalmasscalc['1: Mass Sets']['Standard'])

    # check inputdata
    for i, row in enumerate(collated):
        for j, item in enumerate(row):
            assert item == fmc.inputdata[i][j]

    assert [
        fmc.allmassIDs[i] == [
            '100', '50', '20', '20d', '10', '5', '2', '2d', '1',
            '5w', '1w',
            '100s', '50s', '20s', '10s', '5s', '2s', '1s',
    ][i]
        for i in range(len(fmc.allmassIDs))
    ]

    assert fmc.nbc
    assert fmc.corr is None

    assert fmc.leastsq_meta == {'Number of observations': 25, 'Number of unknowns': 18, 'Degrees of freedom': 7}


def test_parse_inputdata_to_matrices():
    fmc.parse_inputdata_to_matrices()
    assert fmc.check_design_matrix()

    for i in range(len(collated)):
        assert fmc.differences[i] \
               == collated['mass difference (g)'][i]
        assert fmc.uncerts[i] \
               == collated['balance uncertainty (' + MU_STR + 'g)'][i]

    for j in range(fmc.num_stds):
        assert fmc.differences[len(collated) + j] \
               == fmc.finalmasscalc['1: Mass Sets']['Standard']['mass values']['mass values (g)'][j]
        assert fmc.uncerts[len(collated) + j] \
               == fmc.finalmasscalc['1: Mass Sets']['Standard']['mass values']['std uncertainties (' + MU_STR + 'g)'][j]


def test_least_squares():
    fmc.do_least_squares()

    for i in range(fmc.num_unknowns):
        assert fmc.b[i] == pytest.approx(float(check_fmc[i][3]))

    assert fmc.leastsq_meta['Sum of residues squared (' + MU_STR + 'g^2)'] == pytest.approx(244.943467500369)

    for row in range(len(collated)):
        for col in range(5):
            assert fmc.inputdatares[row][col] == \
                   collated[row][col]


def test_check_residuals():
    fmc.check_residuals()
    with pytest.raises(KeyError) as err:
        flag = fmc.leastsq_meta['Residuals greater than 2 balance uncerts']
    assert 'Residuals greater than 2 balance uncerts' in str(err.value)


def test_cal_rel_unc():
    fmc.REL_UNC = 0.1  # override the default 0.03 for this calculation
    fmc.cal_rel_unc()
    assert fmc.leastsq_meta['Relative uncertainty for no buoyancy correction (ppm)'] == 0.1

    for i in range(fmc.num_unknowns):
        assert np.round(fmc.std_uncert_b[i], 3) == float(check_fmc[i][4])


def test_make_summary_table():
    fmc.make_summary_table()
    for i in range(fmc.num_unknowns):
        for j in range(7):
            if j == 1 or j == 2:
                assert fmc.summarytable[i][j] \
                       == check_fmc[i][j]
            else:
                assert float(fmc.summarytable[i][j]) \
                       == pytest.approx(float(check_fmc[i][j]))


def test_add_data_to_root():
    fmc.add_data_to_root()


def test_save_to_json_file():
    test_folder = os.path.join(ROOT_DIR, r'tests\samples\final_mass_calc')
    test_client = 'hortres'
    test_file_path = os.path.join(test_folder, test_client + '_TPAppendixD.json')
    fmc.save_to_json_file(
        filesavepath=test_file_path,
        folder=test_folder,
        client=test_client
    )
    assert os.path.isfile(test_file_path)

    test_read = read(test_file_path)
    assert "7 groups, 4 datasets" in repr(test_read)


def test_save_to_excel():
    cfg.folder = os.path.join(ROOT_DIR, r'tests\samples')
    xl = ExcelSummaryWorkbook(cfg)
    test_folder = os.path.join(ROOT_DIR, r'tests\samples\final_mass_calc')
    test_client = 'hortres'
    test_file_path = os.path.join(test_folder, test_client + '_TPAppendixD.json')
    fmc_root = read(test_file_path)
    xl.add_mls(fmc_root)
    test_folder = os.path.join(ROOT_DIR, r'tests\samples\final_mass_calc')
    test_client = 'hortres'
    xl.save_workbook(test_folder, test_client + '_TPAppendixD.xlsx')


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
    test_save_to_excel()
