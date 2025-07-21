# I:\MSL\Private\Mass\Technical procedures\M_009 Calibration of reference masses
# Example in Appendix A
# I:\MSL\Private\Mass\Mass Program (Masscal)\WSexample.xls

import os
import numpy as np
import pytest

from msl.io import read, read_table

from mass_circular_weighing.configuration import Configuration
from mass_circular_weighing.constants import MU_STR

from mass_circular_weighing.routine_classes.final_mass_calc_class import FinalMassCalc
from mass_circular_weighing.gui.threads.masscalc_popup import filter_mass_set


def assert_arrays_are_the_same(array1, array_2):
    for r1, r2 in zip(array1, array_2):
        for i1, i2 in zip(r1, r2):
            assert np.isclose(i1, i2)


ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
admin_for_test = os.path.join(ROOT_DIR, r'tests\samples\admin_TP009.xlsx')
# input_data_file_for_test is in admin_for_test

# test data
data_table = read_table(admin_for_test, sheet='InputData')

collated = np.empty(len(data_table),
                    dtype=[('+ weight group', object), ('- weight group', object),
                           ('mass difference (g)', 'float64'), ('balance uncertainty (' + MU_STR + 'g)', 'float64'),
                           ('air density (kg/m3)', 'float64'), ('uncertainty (kg/m3)', 'float64'),
                           ],
                    )
collated['+ weight group'] = data_table[:, 0]
collated['- weight group'] = data_table[:, 1]
for i in range(len(data_table)):
    collated['mass difference (g)'][i] = float(data_table[i, 2])
    collated['balance uncertainty (' + MU_STR + 'g)'][i] = float(data_table[i, 3])
    collated['air density (kg/m3)'][i] = float(data_table[i, 4])
    collated['uncertainty (kg/m3)'][i] = float(data_table[i, 5])


check_fmc = read(os.path.join(ROOT_DIR, r'tests\samples\final_mass_calc\test_fmcTP009.json'))

cfg = Configuration(admin_for_test)
cfg.init_ref_mass_sets()

client_wts = filter_mass_set(cfg.all_client_wts, collated)
checks = None
stds = filter_mass_set(cfg.all_stds, collated)

fmc = FinalMassCalc(cfg.folder, cfg.client, client_wts, checks, stds, collated, nbc=False, corr=cfg.correlations)


# settings for analysis options
fmc.BUOYANCY_CORR = True
fmc.HEIGHT_CORR = True

fmc.UNC_AIR_DENS = True
fmc.UNC_VOL = True
fmc.UNC_HEIGHT = True

fmc.TRUE_MASS = True


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
    assert fmc.num_client_masses == 2 \
           == fmc.finalmasscalc['1: Mass Sets']['Client'].metadata['Number of masses'] \
           == check_fmc['1: Mass Sets']['Client'].metadata['Number of masses']
    for i in range(fmc.num_client_masses):
        assert fmc.client_wt_IDs[i] == ['500', '500d'][i]

    # check check info
    assert fmc.num_check_masses == 0

    # check std info
    assert fmc.num_stds == 1 \
           == fmc.finalmasscalc['1: Mass Sets']['Standard'].metadata['Number of masses'] \
           == check_fmc['1: Mass Sets']['Standard'].metadata['Number of masses']
    for i in range(fmc.num_stds):
        assert fmc.std_masses['Weight ID'][i] == ['1Kr'][i] \
               == fmc.finalmasscalc['1: Mass Sets']['Standard'].metadata['Weight ID'][i] \
               == check_fmc['1: Mass Sets']['Standard'].metadata['Weight ID'][i]

    for row in range(fmc.num_stds):
        for j, col in enumerate(fmc.finalmasscalc['1: Mass Sets']['Standard']['mass values'][row]):
            assert col == check_fmc['1: Mass Sets']['Standard']['mass values'][row][j]
            assert col == ["1Kr", 1000.0, 999.99995, 20.0][j]

    assert "0 groups, 1 datasets, 4 metadata" in repr(fmc.finalmasscalc['1: Mass Sets']['Standard'])

    # check inputdata
    check_collated = [
        ['1Kr',      '500+500d', 9.403e-02, 20., 1.20, 0.000253],
        ['500+500d', '1Kr',     -9.800e-02, 20., 1.25, 0.000253],
        ['500',      '500d',     1.500e-05, 20., 1.17, 0.000253],
        ['500d',     '500',     -1.000e-06, 20., 1.22, 0.000253]
    ]
    for i, row in enumerate(collated):
        for j, item in enumerate(row):
            assert item == fmc.inputdata[i][j] == check_collated[i][j]

    for i in range(len(fmc.allmassIDs)):
        assert fmc.allmassIDs[i] == ['500', '500d', '1Kr'][i]

    assert not fmc.nbc
    assert_arrays_are_the_same(fmc.corr, np.identity(2))

    assert fmc.leastsq_meta == {'Number of observations': 5, 'Number of unknowns': 3, 'Degrees of freedom': 2}


def test_parse_inputdata_to_matrices():
    fmc.parse_inputdata_to_matrices()
    assert fmc.check_design_matrix()
    for i in range(len(collated)):
        assert fmc.y_meas[i] \
               == collated['mass difference (g)'][i] \
               # but not check_fmc["2: Matrix Least Squares Analysis"]["Input data with least squares residuals"][i][2]
        assert fmc.uncerts[i] \
               == collated['balance uncertainty (' + MU_STR + 'g)'][i] \
               == check_fmc["2: Matrix Least Squares Analysis"]["Input data with least squares residuals"][i][3] \
               == 20.0

    for j in range(fmc.num_stds):
        # standard mass value is already true mass here
        assert fmc.y_meas[len(collated) + j] \
               == fmc.finalmasscalc['1: Mass Sets']['Standard']['mass values']['mass values (g)'][j] \
               == check_fmc["2: Matrix Least Squares Analysis"]["Input data with least squares residuals"][len(collated) + j][2] \
               == 999.99995
        assert fmc.uncerts[len(collated) + j] \
               == fmc.finalmasscalc['1: Mass Sets']['Standard']['mass values']['std uncertainties (' + MU_STR + 'g)'][j] \
               == check_fmc["2: Matrix Least Squares Analysis"]["Input data with least squares residuals"][len(collated) + j][3] \
               == 20.0


def test_buoyancy_corrections():
    for i, entry in enumerate([1., 1., 1., 1., 0.]):
        assert fmc.cnx1[i] == entry
    bc = [-0.0950176, 0.0989767, 0, 0, 0]
    fmc_bc = fmc.calc_buoyancy_corrections(air_densities=collated['air density (kg/m3)'])

    for i, entry in enumerate(bc):
        assert np.isclose(entry, fmc_bc[i], rtol=1e9)

    assert not fmc.y.any()


def test_height_corrections():
    fmc_hc = fmc.calc_height_corrections()[0]
    hc = [-0.009,  0.009,  0.,     0.,     0.]

    for i, entry in enumerate(hc):
        assert np.isclose(entry/1000, fmc_hc[i])

    assert not fmc.y.any()


def test_apply_corrections_to_mass_differences():
    fmc.apply_corrections_to_mass_differences(air_densities=collated['air density (kg/m3)'])

    corrected_values = [-0.0010107, 0.00100035, 1.5e-05, -1e-06, 999.99995]  # in g
    for i in range(len(collated)):
        assert fmc.y[i] \
               == check_fmc["2: Matrix Least Squares Analysis"]["Input data with least squares residuals"][i][2]
        assert np.isclose(corrected_values[i], fmc.y[i])


def test_cal_psi_y():
    fmc.UNC_VOL = True
    assert not fmc.psi_y
    for u in collated['uncertainty (kg/m3)']:
        assert u == 0.000253
    # here the example uses P0 instead of P
    air_densities = np.array([1.2, 1.2, 1.2, 1.2])
    fmc.cal_psi_y(unc_airdens=collated['uncertainty (kg/m3)'], air_densities=air_densities, rv=None)
    psi_y = np.array(
        [[881.14437606, -881.14437606,    0.,            0.,            0.],
        [-881.14437606,  881.14437606,    0.,            0.,            0.],
        [   0.,            0.,          319.82561682, -319.82561682,    0.],
        [   0.,            0.,         -319.82561682,  319.82561682,    0.],
        [   0.,            0.,            0.,            0.,            0.]]
    )
    assert_arrays_are_the_same(psi_y, fmc.psi_y)  # psi_y without psi_y_meas


def test_least_squares():
    fmc.do_least_squares()

    psi_bmeas = np.array(
        [[500.24249822, 240.32968981, 200.],
         [240.32968981, 500.24249822, 200.],
         [200.00000000, 200.00000000, 400.]]
    )
    assert_arrays_are_the_same(psi_bmeas, fmc.psi_bmeas)

    psi_y = np.array(
        [[1281.14437606, -881.14437606,    0.,            0.,            0.],
        [ -881.14437606, 1281.14437606,    0.,            0.,            0.],
        [    0.,            0.,          719.82561682, -319.82561682,    0.],
        [    0.,            0.,         -319.82561682,  719.82561682,    0.],
        [    0.,            0.,            0.,            0.,          400.]]
    )
    assert_arrays_are_the_same(psi_y, fmc.psi_y)  # psi_y with psi_y_meas

    # note that these are true mass values
    b = [500.000481760, 500.000473762, 999.99995]
    for i in range(fmc.num_unknowns):
        assert fmc.b[i] == \
            pytest.approx(check_fmc["2: Matrix Least Squares Analysis"]["Mass values from least squares solution"][i][3])
        # the b values generated by Python agree to 0.1 µg with the TP values
        assert np.isclose(fmc.b[i], b[i], rtol=1e-9)

    assert np.isclose(fmc.leastsq_meta['Sum of residues squared (' + MU_STR + 'g^2)'], 151.4116989)

    for i, val in enumerate([-5.169, -5.169,  6.999,   6.999,  0.]):
        assert np.isclose(val, fmc.inputdatares[i][4])
        assert fmc.inputdatares[i][4] == \
                   check_fmc["2: Matrix Least Squares Analysis"]["Input data with least squares residuals"][i][4]

    for i in range(3):
        assert np.isclose(
            fmc.convert_to_conventional_mass(v=None, b=None)[i],
            np.array([500.000104892,  500.000096892, 1000.094227952])[i],
            rtol=1e-9
        )


def test_check_residuals():
    fmc.check_residuals()
    with pytest.raises(KeyError) as err:
        flag = fmc.leastsq_meta['Residuals greater than 2 balance uncerts']
    assert 'Residuals greater than 2 balance uncerts' in str(err.value)


def test_cal_rel_unc():
    fmc.cal_rel_unc()

    for i, unc in enumerate([22.3661, 22.3661, 20.0]):
        assert np.isclose(np.round(fmc.std_uncert_b[i], 3),
               check_fmc["2: Matrix Least Squares Analysis"]["Mass values from least squares solution"][i][4])
        assert np.isclose(np.round(fmc.std_uncert_b[i], 3), unc)


def test_make_summary_table():
    fmc.make_summary_table()

    for i in range(fmc.num_unknowns):
        for j in range(6):
            if j == 0:
                assert float(fmc.summarytable[i][j]) \
                       == float(check_fmc["2: Matrix Least Squares Analysis"]["Mass values from least squares solution"][i][j])
            else:
                assert fmc.summarytable[i][j] == pytest.approx(
                    check_fmc["2: Matrix Least Squares Analysis"]["Mass values from least squares solution"][i][j],
                    rel=1e-9
                )

    # note that these are true mass values
    summarytable = np.array(
        [['500',  '500',  'Client',  500.00048176,  22.366, 44.732, 2, '',  ''],
         ['500',  '500d', 'Client',  500.000473762, 22.366, 44.732, 2, '',  ''],
         ['1000', '1Kr', 'Standard', 999.99995,     20.0,   40.0,   2, 999.99995, 0.0]]
    )
    for i, row in enumerate(summarytable):
        for j, item in enumerate(row):
            if not item == fmc.summarytable[i, j]:
                assert np.isclose(float(item), fmc.summarytable[i, j], rtol=1e-9)


if __name__ == '__main__':
    test_file_structure()
    test_filter_masses()
    test_import_mass_lists()
    test_parse_inputdata_to_matrices()
    test_buoyancy_corrections()
    test_apply_corrections_to_mass_differences()
    test_least_squares()
    test_check_residuals()
    test_cal_rel_unc()
    test_make_summary_table()
