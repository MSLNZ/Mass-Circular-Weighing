# A repository for constants and symbols used in the mass weighing program

MU_STR = 'u'                # ALT+0181 or 'µ'
SIGMA_STR = 'σ'             # \u03C3 for sigma sign
SQUARED_STR = '²'

SUFFIX = {'µg': 1e-6, 'ug': 1e-6, 'mg': 1e-3, 'g': 1, 'kg': 1e3}

DEGREE_SIGN = '°'           # \xb0
IN_DEGREES_C = ' ('+DEGREE_SIGN+'C)'

MIN_T = 18.1                # temperature limits at beginning of weighing
MAX_T = 21.9

MIN_RH = 33                 # humidity limits at beginning of weighing
MAX_RH = 67

MAX_T_CHANGE = 0.5          # max allowed change in T IN_DEGREES_C over course of weighing
MAX_RH_CHANGE = 15          # max allowed change in RH in % over course of weighing

SQRT_F = 1.4                # criterion for accepting single weighing analysis
EXCL = 3                    # criterion for excluding a single weighing within an automatic weighing sequence.
                            # note that this constant is currently set to a rather arbitrary value...

