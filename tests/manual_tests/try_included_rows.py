import numpy as np
import sys

from msl.qt import application, excepthook

from mass_circular_weighing.configuration import Configuration
from mass_circular_weighing.constants import MU_STR

from mass_circular_weighing.routines.collate_data import collate_a_data_from_json, collate_m_data_from_json
from mass_circular_weighing.gui.threads.masscalc_popup import MassCalcThread

sys.excepthook = excepthook


def collate_weighings(scheme_entries, cfg):
    data = np.empty(0,
                    dtype=[
                        ('Nominal (g)', float), ('Scheme entry', object), ('Run #', object),
                        ('+ weight group', object), ('- weight group', object),
                        ('mass difference (g)', 'float64'), ('balance uncertainty (' + MU_STR + 'g)', 'float64'),
                        ('Acceptance met?', bool), ('residual (' + MU_STR + 'g)', 'float64')
                    ]
                    )

    for se in scheme_entries:
            bal_alias = 'LUCY'
            mode = cfg.equipment[bal_alias].user_defined['weighing_mode']
            if mode == 'aw':
                newdata = collate_a_data_from_json(url, se)
            else:
                newdata = collate_m_data_from_json(url, se)
            dlen = data.shape[0]
            if newdata is not None:
                ndlen = newdata.shape[0]
                data.resize(dlen + ndlen)
                data[-len(newdata):]['Nominal (g)'] = newdata[:]['Nominal (g)']
                data[-len(newdata):]['Scheme entry'] = newdata[:]['Scheme entry']
                data[-len(newdata):]['Run #'] = newdata[:]['Run #']
                data[-len(newdata):]['+ weight group'] = newdata[:]['+ weight group']
                data[-len(newdata):]['- weight group'] = newdata[:]['- weight group']
                data[-len(newdata):]['mass difference (g)'] = newdata[:]['mass difference (g)']
                data[-len(newdata):]['residual (' + MU_STR + 'g)'] = newdata[:]['residual (' + MU_STR + 'g)']
                data[-len(newdata):]['balance uncertainty ('+MU_STR+'g)'] = newdata[:]['balance uncertainty ('+MU_STR+'g)']
                data[-len(newdata):]['Acceptance met?'] = newdata[:]['Acceptance met?']

                print('Collated scheme entry '+se+' from '+url)

    return data

url = r'I:\MSL\Private\Mass\transfer\Balance Software\Sample Data\LUCY\BuildUp_50kg_20000.json'

config = r'I:\MSL\Private\Mass\transfer\Balance Software\Sample Data\LUCY\config.xml'
cfg = Configuration(config)

cfg.init_ref_mass_sets()


scheme_entries = [
    "20KRA 10KMA+10KMB 20KRB 20KRC",
    "20KRB 10KMA+10KMB 20KRC 20KRD",
    "20KRC 10KMA+10KMB 20KRD 20KRA",
    "20KRD 10KMA+10KMB 20KRA 20KRB",
]

data = collate_weighings(scheme_entries, cfg)


gui = application()

mct = MassCalcThread()
mct.show(data, cfg)

gui.exec_()
