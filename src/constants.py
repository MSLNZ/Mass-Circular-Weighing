# A repository for constants and symbols used in the mass weighing program

MU_STR = 'µ'                # ALT+0181 or 'µ'
SIGMA_STR = 'σ'             # \u03C3 for sigma sign
SQUARED_STR = '²'

SUFFIX = {'µg': 1e-6, 'ug': 1e-6, 'mg': 1e-3, 'g': 1, 'kg': 1e3}

DEGREE_SIGN = '°'           # \xb0
IN_DEGREES_C = ' ('+DEGREE_SIGN+'C)'

MIN_T = 18.1                # temperature limits at beginning of weighing
MAX_T = 21.9

MIN_RH = 32                 # humidity limits at beginning of weighing
MAX_RH = 67

MAX_T_CHANGE = 0.5          # max allowed change in T IN_DEGREES_C over course of weighing
MAX_RH_CHANGE = 15          # max allowed change in RH (%) over course of weighing

SQRT_F = 1.4                # criterion for accepting single weighing analysis
EXCL = 3                    # criterion for excluding a single weighing within an automatic weighing sequence
                            # from the final averaging (and from any tally of happy weighings).
                            # Currently set to a rather arbitrary value without any experimental basis...


config_default = r'C:\Users\r.hawke.IRL\PycharmProjects\Mass-Circular-Weighing\config.xml'
stds = [                    # options for standards and check masses
    'MET16A',
    'MET16B',
    'WV',
]
balances = [                # available balances
    "MDE-demo",
    "AX10005",
    "CCE605",
    "AB204-S",
    "AT106",
]
omega_loggers = [           # available Omega Loggers
    "Omega",
]
MAX_BAD_RUNS = 3