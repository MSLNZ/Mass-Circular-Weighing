""" This module provides functions for calculating air density"""
import math
import numpy as np


# Constant parameters from Picard et al. Metrologia 2008, 45, 149-155.
# Vapour pressure at saturation, Psv
A = 0.000012378847
B = -0.019121316
C = 33.93711047
D = -6343.1645
# Enhancement factor f
Alpha = 1.00062
Beta = 0.0000000314
Gamma = 0.00000056
# Compressibility factor Z
a0 = 0.00000158123
a1 = -0.000000029331
a2 = 0.00000000011043
b0 = 0.000005707
b1 = -0.00000002051
c0 = 0.00019898
c1 = -0.000002376
d0 = 0.0000000000183
e0 = -0.00000000765
#Gas constant R
R = 8.314472
# Leading constant
MaOverR = 0.00348374    #Value of Ma when xCO2=0.0004
Ma1 = 0.02896546
Ma2 = 0.012011
Mv = 0.01801528
NomXco2 = 0.0004


def Psv(Tk: float) -> float:
    """Calculate the saturated vapour pressure Psv from temperature Tk Kelvin"""
    return math.exp(A * Tk * Tk + B * Tk + C + D / Tk)  # Saturated vapour pressure


def Z(Tk: float, Tc: float, Pa: float, Xv: float) -> float:
    """ Calculate the compressibility factor Z of moist air from
        temperature (Tk Kelvin and Tc deg C), pressure (Pa pascal) and
        mole fraction of water vapour Xv.
    """
    Z1 = a0 + a1 * Tc + a2 * Tc * Tc + (b0 + b1 * Tc) * Xv + (c0 + c1 * Tc) * Xv * Xv
    Z2 = (Pa * Pa) * (d0 + e0 * Xv * Xv) / (Tk * Tk)
    Z_val = 1 - (Pa / Tk) * Z1 + Z2
    return Z_val


def AirDens2009(Tc: float, Pmb: float, RhOrDewpoint: float, Xco2: float) -> float:
    """ Calculates air density using the BIPM equation 2007 (Picard, Metrologia 2008, 45, 149-155).
    This is based on the VBA code provided by Fung
    :param Tc:              Temperature in deg C
    :param Pmb:            Pressure in mb (hPa)
    :param RhOrDewpoint:    Relative humidity in percent or dewpoint °C
    :param Xco2:            Molar fraction of carbon dioxide (usually 0.0004)
    :return:                Calculated air density in kg/m3
    """

    Tk = Tc + 273.15  # Absolute temperature
    Pa = Pmb * 100  # Pressure in Pa

    if (RhOrDewpoint < 20):
        Tdew = RhOrDewpoint
        Rhf = Psv(Tdew + 273.15) / Psv(Tk)  # Convert to relative humidity as a fraction
    else:
        Rhf = RhOrDewpoint / 100  # Relative humidity as %

    Ma = Ma1 + Ma2 * (Xco2 - NomXco2)  # Calculate molar mass of dry air in kg/mol
    CalcPsv = Psv(Tk)  # Calculate saturated vapour pressure in Pa
    f = Alpha + Beta * Pa + Gamma * Tc * Tc  # Calculate enhancement factor
    Xv = Rhf * f * CalcPsv / Pa  # Calculate mole fraction of water vapour
    CalcZ = Z(Tk, Tc, Pa, Xv)  # Calculate compressibility factor
    D1 = 1 - Xv * (1 - Mv / Ma)  # Calculate air density

    AirDens2009_val = Pa * Ma * D1 / (CalcZ * R * Tk)
    return AirDens2009_val
