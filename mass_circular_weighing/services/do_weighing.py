from msl.qt import prompt
from msl.network import Service

from other.do_new_weighing import do_new_weighing
from mass_circular_weighing.utils.circweigh_subprocess import run_circweigh_popup


class DoWeighing(Service):

    def __init__(self):
        super().__init__(max_clients=1, name='Do single circular weighing')

    @staticmethod
    def do_new_weighing(cfg, bal_alias, scheme_entry, nominal_mass):
        done = do_new_weighing(cfg, bal_alias, scheme_entry, nominal_mass,)

        return done

    @staticmethod
    def run_circweigh_gui(admin=None, se_row_data=None):
        run_circweigh_popup(admin, se_row_data)


if __name__ == '__main__':
    s = DoWeighing()
    s.start(host='CISS33653')