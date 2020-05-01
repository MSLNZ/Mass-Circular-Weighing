import pytest
import numpy as np


def test_rounding():

    a = np.round(45.63214 / 60, 6)
    assert a == 0.760536


def test_array_formation():

    a = np.empty(shape=(3, 4, 2))
    num_reads = 12

    for i in range(3):
        for j in range(4):
            for k in range(2):
                a[i, j][k] = i + j + k

    assert [
        np.reshape(a[:, :, 0], num_reads)[i] == [0., 1., 2., 3., 1., 2., 3., 4., 2., 3., 4., 5.][i]
        for i in range(num_reads)
    ]
    assert type(a) == np.ndarray

    times = np.arange(num_reads)
    assert type(times) == np.ndarray
    assert [
        times[i] == range(num_reads)[i]
        for i in range(num_reads)
    ]

    times2 = np.array([0., 1., 2., 3., 1., 2., 3., 4., 2., 3., 4., 5.])
    assert type(times2) == np.ndarray


def test_ident():
    for n in range(10):
        idmat = np.identity(n)
        for i in range(n):
            for j in range(n):
                if i == j:
                    assert idmat[i, j] == 1
                else:
                    assert idmat[i, j] == 0


def test_matrix_concatenation():
    n = 5
    a = np.identity(n)
    c = np.concatenate([a, a], axis=1)
    for i in range(n):
        for j in range(2*n):
            if i == j:
                assert c[i, j] == 1
            elif j == i + n:
                assert c[i, j] == 1
            else:
                assert c[i, j] == 0

    b = np.identity(n+1)
    with pytest.raises(ValueError) as err:
        np.concatenate([a, b], axis=1)
    assert 'all the input array dimensions for the concatenation axis must match exactly' in str(err.value)


def test_times_vstack():
    n = 10
    times = np.array(range(n))
    a = np.vstack((times, times**2, times**3))

    for i in range(3):
        for j in range(n):
            assert a[i][j] == j**(i+1)

    for j in range(n):
        assert np.sqrt(a[1][j]) == a[0][j]


def test_multiplication():
    a = [
        [1, 2, 3, 4],
        [2, 3, 4, 5],
    ]
    b = [
        [4, 5, 6],
        [3, 4, 5],
        [2, 3, 4],
        [1, 2, 3],
    ]
    c = np.dot(a, b)
    assert np.shape(c) == (2, 3)
    c_t = np.transpose(c)
    for i in range(2):
        for j in range(3):
            assert c[i][j] == c_t[j][i]

    with pytest.raises(ValueError) as err:
        np.linalg.multi_dot([a, b, c])
    assert 'not aligned' in str(err.value)

    d1 = np.dot(c, c_t)
    assert d1[1][0] == d1[0][1]
    d2 = np.linalg.multi_dot([a, b, c_t])
    for i in range(2):
        assert [d1[i][j] == d2[i][j] for j in range(2)]

    e = np.multiply(2, b)
    for i in range(4):
        for j in range(3):
            assert 2*b[i][j] == e[i][j]


def test_inverse():
    a = [
        [1, 2, 3, 4],
        [2, 3, 4, 5],
    ]
    with pytest.raises(np.linalg.LinAlgError) as err:
        np.linalg.inv(a)
    assert 'Last 2 dimensions of the array must be square' in str(err.value)

    b = [
        [2, 3, 4],
        [3, 4, 5],
        [4, 5, 6],
    ]
    with pytest.raises(np.linalg.LinAlgError) as err:
        np.linalg.inv(b)
    assert 'Singular matrix' in str(err.value)

    c = [
        [2, 3, 1],
        [3, 4, 5],
        [4, 5, 6],
    ]

    c_i = (np.linalg.inv(c))

    d = np.dot(c_i, c)
    n = 3
    for i in range(n):
        for j in range(n):
            if i == j:
                assert d[i][j] == pytest.approx(1, rel=1e-15)
            else:
                assert d[i][j] == pytest.approx(0, rel=1e-15)


def test_diagonal():
    c = [
        [2, 3, 1],
        [3, 4, 5],
        [4, 5, 6],
    ]
    d = np.diagonal(c)
    e = np.diag(c)
    n = 3
    for i in range(n):
        for j in range(n):
            if i == j:
                assert d[i] == c[i][j]
                assert e[i] == c[i][j]
            else:
                with pytest.raises(IndexError) as err:
                    print(d[i][j] == 0)
                assert 'invalid index to scalar variable.' in str(err.value)
                with pytest.raises(IndexError) as err:
                    print(e[i][j] == 0)
                assert 'invalid index to scalar variable.' in str(err.value)


def test_roll():
    n = 20

    a = range(n)
    a_roll = np.roll(a, -1)

    d = range(1, n)
    e = np.append(list(d), 0)

    assert [a_roll[i] == e[i] for i in range(n)]


# np.where, np.hstack(uncerts), np.absolute, np.float
# plus longer calculations

