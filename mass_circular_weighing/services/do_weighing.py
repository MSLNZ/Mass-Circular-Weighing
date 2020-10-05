from msl.qt import prompt
from msl.network import Service

from other.do_new_weighing import do_new_weighing


class DoWeighing(Service):

    def __init__(self):
        super().__init__(max_clients=1, name='Do single circular weighing')

    def do_new_weighing(self, cfg, client, bal_alias, folder, filename, scheme_entry, nominal_mass,
                        timed=False, drift='quadratic drift'):
        done = do_new_weighing(cfg, client, bal_alias, folder, filename, scheme_entry, nominal_mass,
                               timed, drift)

        return done

    def select_folder(self):
        return prompt.folder()


if __name__ == '__main__':
    s = DoWeighing()
    s.start(host='CISS33745')