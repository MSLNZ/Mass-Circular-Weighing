"""
A first attempt at creating services from the functions and methods within mass_circular_weighing
"""
from msl.network import Service

from ..configuration import Configuration
from ..constants import NBC
from other.do_new_weighing import do_new_weighing
from ..routines.run_circ_weigh import analyse_old_weighing, analyse_all_weighings_in_file
from ..routines.collate_data import *
from ..routine_classes.final_mass_calc_class import FinalMassCalc, filter_IDs, filter_stds


class DoWeighing(Service):

    def __init__(self):
        super().__init__(max_clients=1, name='Do circular weighing')

    def do_new_weighing(self, config, bal_alias, scheme_entry, nominal_mass):

        done_ok = do_new_weighing(config, bal_alias, scheme_entry, nominal_mass)

        return done_ok


class AnalyseWeighing(Service):

    def __init__(self, cfg, filename, se):
        super().__init__(name='Analyse circular weighing(s)')
        self.cfg = cfg
        self.fn = filename
        self.scheme_entry = se

    def analyse_one_weighing(self, run_id):
        return analyse_old_weighing(self.cfg, self.fn, self.scheme_entry, run_id)

    def analyse_all_weighings_in_file(self):
        analyse_all_weighings_in_file(self.cfg, self.fn, self.scheme_entry)


class CollateData(Service):

    def __init__(self):
        super().__init__(name='Collate data from circular weighings')

    def collate_a_data_from_json(self, url, scheme_entry):
        collated_data = collate_a_data_from_json(url, scheme_entry)

        if collated_data[1] == True:
            return collated_data[0]
        else:
            log.error('Unacceptable analysis of weighings from '+scheme_entry)
            return None

    def collate_m_data_from_json(self, url, scheme_entry):
        return collate_m_data_from_json(url, scheme_entry)


class FinalMassCalcService(Service):

    def __init__(self):
        super().__init__(max_clients=1, name='Final mass calculation')

    def final_mass_calc(self, config, inputdata,):
        cfg = Configuration(config)
        client_wt_IDs = filter_IDs(cfg.client_wt_IDs.split(), inputdata)
        if cfg.all_checks is not None:
            check_masses = filter_stds(cfg.all_checks, inputdata)
        else:
            check_masses = None
        std_masses = filter_stds(cfg.all_stds, inputdata)
        # send relevant information to matrix least squares mass calculation algorithm
        fmc = FinalMassCalc(
            cfg.folder,
            cfg.client,
            client_wt_IDs,
            check_masses,
            std_masses,
            inputdata,
            NBC,
            cfg.correlations,
        )
        # do calculation
        fmc.add_data_to_root()
        fmc.save_to_json_file()

        return fmc


if __name__ == '__main__':
    s = DoWeighing()
    s.start(host='CISS33745')

