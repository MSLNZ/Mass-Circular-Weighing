"""Solve a quadratic equation. Returns both solutions."""

import numpy as np


def solve_quadratic_equation(a: float, b: float, c: float) -> tuple[float, float]:
    """Use quadratic formula to solve for T
    Equation of form a*T**2 + b*T + c = 0

    :param a: coefficient of T**2
    :param b: coefficient of T
    :param c: constant

    :return: temperature, T, in degrees C
    """
    bracket = b**2 - 4*a*c
    T1 = (-b + np.sqrt(bracket))/(2*a)
    T2 = (-b - np.sqrt(bracket))/(2*a)

    return T1, T2
