import pytest

from mass_circular_weighing.utils.quadratic_solver import solve_quadratic_equation


def test_solve_quadratic1():
    # a*T**2 + b*T + c = 0
    a = 1
    b = -45
    c = 500

    t1, t2 = solve_quadratic_equation(a, b, c)

    assert 25 in (t1, t2)
    assert 20 in (t1, t2)


def test_solve_quadratic2():
    # a*T**2 + b*T + c = 0
    a = 0.0002471
    b = 1 - 0.00491
    c = -0.097 - 50

    t1, t2 = solve_quadratic_equation(a, b, c)

    assert 49.73007648226519 in (t1, t2)
    assert -4076.8041355676564 in (t1, t2)


if __name__ == '__main__':

    test_solve_quadratic1()
    test_solve_quadratic2()
