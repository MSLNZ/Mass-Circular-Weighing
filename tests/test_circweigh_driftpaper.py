import pytest
import numpy as np

from mass_circular_weighing.routine_classes.circ_weigh_class import CircWeigh

# testing CircWeigh class using data from drift paper
se = '1a 1b 1c 1d'
cw = CircWeigh(se)
dataset = [
        [22.1,  743.7,  3080.4, 4003.4],
        [18.3,  739.2,  3075.5, 3998.2],
        [14.2,  734.7,  3071.6, 3994.8],
    ]


def test_generate_design_matrices():

    for i, grp in enumerate(['1a', '1b', '1c', '1d']):
        assert cw.wtgrps[i] == grp
    assert cw.num_wtgrps == 4
    assert cw.num_cycles == 3
    assert cw.num_readings == 12

    cw.generate_design_matrices(times=[])
    assert cw.trend == 'reading'
    id = [[1., 0., 0., 0.],
       [0., 1., 0., 0.],
       [0., 0., 1., 0.],
       [0., 0., 0., 1.],
       [1., 0., 0., 0.],
       [0., 1., 0., 0.],
       [0., 0., 1., 0.],
       [0., 0., 0., 1.],
       [1., 0., 0., 0.],
       [0., 1., 0., 0.],
       [0., 0., 1., 0.],
       [0., 0., 0., 1.]]
    drift_keys = ['no drift', 'linear drift', 'quadratic drift', 'cubic drift']
    for key in drift_keys:
        for i in range(12):
            for j in range(4):
                assert id[i][j] == cw.matrices.get(key)[i][j]
                assert cw.matrices.get(key)[i][j] == cw.t_matrices.get(key)[j][i]

    for i, key in enumerate(drift_keys):
        assert cw._driftorder.get(key) == i

        if i > 0:
            for col in range(i):
                for j in range(12):
                    assert cw.matrices.get(key)[j][4+col] == j**(col+1)


def test_determine_drift():

    cw.determine_drift(dataset)
    # note that this function calls cw.expected_vals_drift(dataset, drift)

    checkstdevs =  {
        'no drift': 4.30300283,
        'linear drift': 0.39013124,
        'quadratic drift': 0.41644618,
        'cubic drift': 0.290016
    }
    for key, val in cw.stdev.items():
        assert val == checkstdevs.get(key)
    # here we assume that the residuals are also correct as they are used to determine the stdev


def test_expected_vals_drift():

    cw.expected_vals_drift(dataset, 'quadratic drift')

    cw_b = cw.b['quadratic drift']
    b = [2.25626344e+01,  7.44643179e+02 , 3.08234839e+03, 4.00637826e+03, -1.11955645e+00,  4.33467742e-03]
    assert [cw_b[i] == pytest.approx(b[i]) for i in range(len(b))]

    cw_res = cw.residuals['quadratic drift']
    check_res = [
        -0.46263441,  0.17204301,  0.2733871,   0.34139785,  0.14623656,  0.04623656,
        -0.28709677, -0.55376344,  0.31639785, -0.21827957,  0.01370968,  0.21236559
    ]
    assert [cw_res[i] == check_res[i] for i in range(12) ]

    assert np.round(cw.stdev['quadratic drift'], 2) == 0.42

    cw_varcovar = cw.varcovar['quadratic drift']
    check_varcovar = [
        [ 1.18881699e-01,   7.10376425e-02,  7.64572494e-02,  7.73313795e-02, - 3.04197288e-02,  2.27273836e-03],
        [ 7.10376425e-02,   1.40691246e-01,  8.96566145e-02,  9.13611682e-02, - 3.46592600e-02,  2.53497740e-03],
        [ 7.64572494e-02,   8.96566145e-02,  1.55595165e-01,  1.00845480e-01, - 3.60141617e-02,  2.53497740e-03],
        [ 7.73313795e-02,   9.13611682e-02,  1.00845480e-01,  1.63593455e-01, - 3.44844339e-02,  2.27273836e-03],
        [-3.04197288e-02,  -3.46592600e-02, -3.60141617e-02, -3.44844339e-02,   1.72203637e-02, -1.44231473e-03],
        [ 2.27273836e-03,   2.53497740e-03,  2.53497740e-03,  2.27273836e-03, - 1.44231473e-03,  1.31119521e-04],
    ]
    np.testing.assert_allclose(cw_varcovar, check_varcovar)


def test_drift_coeffs():

    dc = cw.drift_coeffs('quadratic drift')
    assert dc['linear drift'] == '-1.1196 (0.131)'
    assert dc['quadratic drift'] == '0.0043347 (0.0115)'


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
    test_item_diff()