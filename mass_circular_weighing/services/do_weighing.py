from msl.qt import prompt
from msl.network import Service

from other.do_new_weighing import do_new_weighing


class DoWeighing(Service):

    def __init__(self):
        super().__init__(max_clients=1, name='Do single circular weighing')

    @staticmethod
    def do_new_weighing(cfg, bal_alias, scheme_entry, nominal_mass):
        done = do_new_weighing(cfg, bal_alias, scheme_entry, nominal_mass,)

        return done


if __name__ == '__main__':
    s = DoWeighing()
    s.start(host='CISS33745')