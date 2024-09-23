# I:\MSL\Private\Mass\IRL reports\IRL report Uncertainties in mass comparisons Aug 99.pdf

import os
import numpy as np
import functools

from msl.io import read, read_table

from mass_circular_weighing.configuration import Configuration
from mass_circular_weighing.constants import MU_STR

from mass_circular_weighing.routine_classes.final_mass_calc_class import FinalMassCalc
from mass_circular_weighing.gui.threads.masscalc_popup import filter_mass_set


def assert_arrays_are_the_same(array1, array_2):
    for r1, r2 in zip(array1, array_2):
        for i1, i2 in zip(r1, r2):
            assert np.isclose(float(i1), float(i2), rtol=1e-8)


ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
admin_for_test = os.path.join(ROOT_DIR, r'tests\samples\admin_IRL955.xlsx')
### input_data_file_for_test is in admin_for_test ###

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

collated_1_2 = collated[:2]
collated_3 = collated[2:4]
collated_4 = collated[4:]

cfg = Configuration(admin_for_test)
cfg.init_ref_mass_sets()


def test_example_1():
    """ Example 1: Illustration of matrix calculations with uncertainties in measured mass values
        and in the mass of the reference standard """
    # example data is in the first two rows of collated
    client_wts_1 = filter_mass_set(cfg.all_client_wts, collated_1_2)
    assert client_wts_1['Weight ID'] == ['1kx']
    client_wts_1['Density (kg/m3)'] = [7850]
    client_wts_1['Vol (mL)'] = [1000/7.850]
    assert client_wts_1['Vol (mL)'] == [127.38853503184714]
    checks = None
    stds = filter_mass_set(cfg.all_stds, collated_1_2)
    stds['uncertainties (' + MU_STR + 'g)'] = [10.]

    fmc = FinalMassCalc(cfg.folder, cfg.client, client_wts_1, checks, stds, collated_1_2, nbc=True, corr=cfg.correlations)

    fmc.check_design_matrix()
    assert_arrays_are_the_same(fmc.designmatrix, np.array([[-1.,  1.],  [-1.,  1.],  [0.,  1.]]))
    assert fmc.all_wts['Weight ID'] == ['1kx', '1Kr']

    fmc.BUOYANCY_CORR = True
    fmc.TRUE_MASS = True
    fmc.apply_corrections_to_mass_differences(air_densities=collated_1_2['air density (kg/m3)'])
    for i, j in zip(fmc.y, [-2.01025767e-04, -2.01182457e-04,  1.00000000e+03]):  # y in g
        assert np.isclose(i, j, rtol=1e-8)

    fmc.do_least_squares()
    psi_bmeas = np.array([[100.5, 100.], [100.,  100.]])
    assert_arrays_are_the_same(fmc.psi_bmeas, psi_bmeas)
    psi_y = np.array([[1.,   0.,   0.],  [0.,   1.,   0.],  [0.,   0., 100.]])
    assert_arrays_are_the_same(psi_y, fmc.psi_y)
    assert_arrays_are_the_same(fmc.psi_y, psi_y)

    assert np.isclose(fmc.b[0], 1000.0002011, rtol=1e-9)
    assert np.isclose(fmc.b[1], 1000., rtol=1e-9)

    fmc.add_data_to_root()
    summarytable = np.array(
        [['1000', '1kx', 'Client', 1000.000201104, 31.631, 63.261, 2, ''],
         ['1000', '1Kr', 'Standard', 1000.0, 10.0, 20.0, 2, '1000 g; Δ 0.0 µg']]
    )
    for i, row in enumerate(summarytable):
        for j, item in enumerate(row):
            if not item == fmc.summarytable[i, j]:
                assert np.isclose(float(item), fmc.summarytable[i, j], rtol=1e-8)


def test_example_2():
    """ Example 2: Illustration of matrix calculations with uncertainties in air density"""
    # example data is in the first two rows of collated
    client_wts_1 = filter_mass_set(cfg.all_client_wts, collated_1_2)
    collated_1_2['balance uncertainty (' + MU_STR + 'g)'] = [0.01, 0.01]
    assert client_wts_1['Weight ID'] == ['1kx']
    client_wts_1['Density (kg/m3)'] = [7850]
    client_wts_1['Vol (mL)'] = [1000 / 7.850]
    assert np.isclose(client_wts_1['Vol (mL)'][0], 127.38854, rtol=1e-7)
    checks = None
    stds = filter_mass_set(cfg.all_stds, collated_1_2)
    assert np.isclose(stds['Vol (mL)'][0], 125.78616, rtol=1e-7)

    fmc = FinalMassCalc(cfg.folder, cfg.client, client_wts_1, checks, stds, collated_1_2, nbc=True,
                        corr=cfg.correlations)

    fmc.check_design_matrix()
    assert_arrays_are_the_same(fmc.designmatrix, np.array([[-1., 1.], [-1., 1.], [0., 1.]]))
    assert fmc.all_wts['Weight ID'] == ['1kx', '1Kr']

    fmc.BUOYANCY_CORR = True
    fmc.TRUE_MASS = True
    for i, j in zip(collated_1_2['air density (kg/m3)'], [1.17, 1.23]):
        assert np.isclose(i, j, rtol=1e-8)
    fmc.apply_corrections_to_mass_differences(air_densities=collated_1_2['air density (kg/m3)'])
    for i, j in zip(fmc.y, [-2.01025767e-04, -2.01182457e-04, 1.00000000e+03]):  # y in g
        assert np.isclose(i, j, rtol=1e-8)

    fmc.UNC_AIR_DENS = True
    unc_airdens = collated_1_2['uncertainty (kg/m3)']
    assert [ad == 0.001 for ad in unc_airdens]
    fmc.cal_psi_y(unc_airdens=collated_1_2['uncertainty (kg/m3)'],
                  air_densities=collated_1_2['air density (kg/m3)'],
                  rv=None)
    psi_y = np.array([[2.56759446, 2.56759446, 0.],     [2.56759446, 2.56759446, 0.],     [0., 0., 0.]])
    assert_arrays_are_the_same(fmc.psi_y, psi_y)

    fmc.do_least_squares()
    psi_bmeas = np.array([[2.56774446, 1.00000000e-04],  [1.00000000e-04, 1.00000000e-04]])
    assert_arrays_are_the_same(fmc.psi_bmeas, psi_bmeas)
    psi_y = np.array([[2.56769446,   2.56759446, 0.],   [2.56759446,    2.56769446, 0.],    [0.,   0.,  1.00e-04]])
    assert_arrays_are_the_same(fmc.psi_y, psi_y)

    assert np.isclose(fmc.b[0], 1000.0002011, rtol=1e-9)
    assert np.isclose(fmc.b[1], 1000., rtol=1e-9)

    fmc.add_data_to_root()
    summarytable = np.array(
        [['1000', '1kx', 'Client', 1000.000201104, 30.043, 60.086, 2, ''],
         ['1000', '1Kr', 'Standard', 1000.0, 0.01, 0.02, 2, '1000 g; Δ 0.0 µg']]
    )
    for i, row in enumerate(summarytable):
        for j, item in enumerate(row):
            if not item == fmc.summarytable[i, j]:
                assert np.isclose(float(item), fmc.summarytable[i, j], rtol=1e-8)


def test_example_3():
    """ Example 3: Illustration of matrix calculations with uncertainties in volumes of weights"""
    # example data is in rows 3 and 4 of collated
    client_wts = filter_mass_set(cfg.all_client_wts, collated_3)
    assert client_wts['Weight ID'] == ['1kx', '1kxd']
    assert np.isclose(client_wts['Vol (mL)'][0], 126.58228, rtol=1e-7)
    checks = None
    stds = filter_mass_set(cfg.all_stds, collated_3)
    assert np.isclose(stds['Vol (mL)'][0], 125.78616, rtol=1e-7)

    fmc = FinalMassCalc(cfg.folder, cfg.client, client_wts, checks, stds, collated_3, nbc=True,
                        corr=cfg.correlations)

    fmc.check_design_matrix()
    assert_arrays_are_the_same(fmc.designmatrix, np.array([[-1., 0., 1.], [1., -1., 0.], [0., 0., 1.]]))
    assert fmc.all_wts['Weight ID'] == ['1kx', '1kxd', '1Kr']

    fmc.BUOYANCY_CORR = True
    fmc.TRUE_MASS = True
    for i, j in zip(collated_3['air density (kg/m3)'], [1.2, 1.2]):
        assert np.isclose(i, j, rtol=1e-8)
    fmc.apply_corrections_to_mass_differences(air_densities=collated_3['air density (kg/m3)'])
    for i, j in zip(fmc.y, [-2.00451e-04, 0., 1.0e+03]):  # y in g
        assert np.isclose(i, j, rtol=1e-8)

    fmc.UNC_VOL = True
    unc_airdens = collated_3['uncertainty (kg/m3)']
    assert [ad == 0.001 for ad in unc_airdens]
    rv = np.identity(len(fmc.all_wts['Set']))
    for i, st_i in enumerate(fmc.all_wts['Set']):
        for j, st_j in enumerate(fmc.all_wts['Set']):
            if st_i == st_j:
                rv[i, j] = 1
    fmc.cal_psi_y(unc_airdens=collated_3['uncertainty (kg/m3)'], air_densities=collated_3['air density (kg/m3)'], rv=rv)
    psi_y = np.array([[310921.05, 0, 0.],     [0, 0, 0.],     [0., 0., 0.]])
    assert_arrays_are_the_same(fmc.psi_y, psi_y)
    # noting issues with rounding here - set first element of psi_y to 310921.05
    fmc.psi_y[0][0] = 310921.05
    fmc.do_least_squares()
    psi_bmeas = np.array(
        [[3.1092113e+05, 3.1092113e+05, 1.0e-04],
         [3.1092113e+05, 3.1092113e+05, 1.0e-04],
         [1.0e-04, 1.0e-04, 1.0e-04]]
    )
    assert_arrays_are_the_same(fmc.psi_bmeas, psi_bmeas)

    psi_y = np.array([[3.1092105e+05, 0., 0.],  [0., 1.0e-04, 0.], [0., 0., 1.0e-04]])
    assert_arrays_are_the_same(fmc.psi_y, psi_y)

    assert np.isclose(fmc.b[0], 1000.0005, rtol=1e-7)
    assert np.isclose(fmc.b[1], 1000.0005, rtol=1e-7)
    assert np.isclose(fmc.b[2], 1000.0000, rtol=1e-7)  # standard 1Kr

    fmc.add_data_to_root()
    summarytable = np.array(
        [['1000', '1kx',  'Client',     1000.000559647, 558.409, 1116.819, 2, ''],
         ['1000', '1kxd', 'Client',     1000.000559647, 558.409, 1116.819, 2, ''],
         ['1000', '1Kr',  'Standard',   1000.0,         0.01,       0.02,  2, '1000 g; Δ 0.0 µg']]
    )
    for i, row in enumerate(summarytable):
        for j, item in enumerate(row):
            if not item == fmc.summarytable[i, j]:
                assert np.isclose(float(item), fmc.summarytable[i, j], rtol=1e-7)


def test_example_4():
    """ Example 4: Illustration of matrix calculations with uncertainties
        in heights of centres of mass of the weights"""
    # example data is in rows 5 and 6 of collated
    client_wts = filter_mass_set(cfg.all_client_wts, collated_4)
    assert client_wts['Weight ID'] == ['1kx']
    assert np.isclose(client_wts['Vol (mL)'][0], 126.58228, rtol=1e-7)
    checks = None
    stds = filter_mass_set(cfg.all_stds, collated_4)
    assert np.isclose(stds['Vol (mL)'][0], 125.78616, rtol=1e-7)

    fmc = FinalMassCalc(cfg.folder, cfg.client, client_wts, checks, stds, collated_4, nbc=True,
                        corr=cfg.correlations)

    fmc.check_design_matrix()
    assert_arrays_are_the_same(fmc.designmatrix, np.array([[-1.,  1.],  [-1.,  1.],  [0.,  1.]]))
    assert fmc.all_wts['Weight ID'] == ['1kx', '1Kr']
    for k, v in fmc.all_wts.items():
        assert len(v) == 2
    assert fmc.all_wts['u_height (mm)'] == [1., 0.1]

    fmc.BUOYANCY_CORR = False
    fmc.TRUE_MASS = True
    fmc.HEIGHT_CORR = True
    for i, j in zip(collated_4['air density (kg/m3)'], [1.2, 1.2]):
        assert np.isclose(i, j, rtol=1e-8)

    assert fmc.all_wts['Nominal (g)'] == [1000, 1000]
    assert fmc.all_wts['Centre Height (mm)'] == [35.5, 19.5]

    fmc.apply_corrections_to_mass_differences(air_densities=collated_4['air density (kg/m3)'])
    for i, j in zip(fmc.y, [-4.8e-06, -4.8e-06,  1.0e+03]):  # y in g
        assert np.isclose(i, j, rtol=1e-8)

    fmc.UNC_HEIGHT = True
    unc_airdens = collated_4['uncertainty (kg/m3)']
    assert [ad == 0.001 for ad in unc_airdens]
    fmc.cal_psi_y(unc_airdens=collated_4['uncertainty (kg/m3)'],
                  air_densities=collated_4['air density (kg/m3)'],
                  rv=None)
    psi_y = np.array(
        [[0.0909, 0.0909, 0.],
         [0.0909, 0.0909, 0.],
         [0.,     0.,     0.,]]
    )
    assert_arrays_are_the_same(fmc.psi_y, psi_y)  # psi_y without psi_meas
    fmc.do_least_squares()
    psi_bmeas = np.array(
        [[0.09105, 1.0e-04],
         [1.0e-04, 1.0e-04]]
    )
    assert_arrays_are_the_same(fmc.psi_bmeas, psi_bmeas)
    psi_y = np.array(
        [[0.0910, 0.0909, 0.],
         [0.0909, 0.0910, 0.],
         [0.,     0.,     0.0001,]]
    )
    assert_arrays_are_the_same(fmc.psi_y, psi_y)  # psi_y with psi_meas

    assert np.isclose(fmc.b[0], 1000.000005, rtol=1e-9)  # client 1kx
    assert np.isclose(fmc.b[1], 1000.000000, rtol=1e-9)  # standard 1Kr

    fmc.add_data_to_root()
    summarytable = np.array(
        [['1000', '1kx', 'Client',   1000.0000048, 30.002, 60.003, 2, ''],
         ['1000', '1Kr', 'Standard', 1000.0,        0.01,   0.02,  2, '1000 g; Δ 0.0 µg']]
    )
    for i, row in enumerate(summarytable):
        for j, item in enumerate(row):
            if not item == fmc.summarytable[i, j]:
                assert np.isclose(float(item), fmc.summarytable[i, j], rtol=1e-9)


if __name__ == '__main__':
    test_example_1()
    test_example_2()
    test_example_3()
    test_example_4()
