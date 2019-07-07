from msl.equipment import Config
from .equip.mdebalance import Balance
from .equip.mettler import MettlerToledo

class Application(object):

    def __init__(self, config):

        self.cfg = Config(config)  # load cfg file
        self.db = self.cfg.database()
        self.equipment = self.db.equipment # loads subset of database with equipment being used

        self.bal_class = {'mde': Balance, 'mw': MettlerToledo}

    def connect_bal(self, alias, strict=True):
        # selects balance class and return balance instance

        mode = self.equipment[alias].user_defined['weighing_mode']
        bal = self.bal_class[mode](self.equipment[alias])

        return bal

    def acceptance_criteria(self, alias, nominal_mass):
        record = self.equipment.get(alias)
        if not record:
            raise ValueError('No equipment record')
        man = record.manufacturer
        model = record.model
        serial = record.serial

        path = self.cfg.root.find('acceptance_criteria/path').text
        sheet = self.cfg.root.find('acceptance_criteria/sheet').text

        # note that this reader works for 2D table with one header line
        header, data = self.db._read_excel(path, sheet, None)

        index_map = {}
        for col_name in {'model', 'manufacturer', 'serial',
                         'load max', 'load min', 'acceptable', 'residuals'}:
            for i, name in enumerate(header):
                if col_name in name.lower():
                    index_map[col_name] = i

        store = []
        for row in data:
            if model == row[index_map['model']] \
                and man == row[index_map['manufacturer']] \
                    and serial == row[index_map['serial']]:
                store.append(row)

        if not store:
            raise ValueError('No acceptance criteria for balance')

        for row in store:
            if float(row[index_map['load min']]) <= nominal_mass <= float(row[index_map['load max']]):
                return {'Max stdev from CircWeigh (ug)': float(row[index_map['acceptable']]),
                        'Upper limit for residuals (ug)': float(row[index_map['residuals']])}

        raise ValueError('Nominal mass out of range of balance')




