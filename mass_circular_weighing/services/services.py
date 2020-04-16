from msl.network import Service
#from msl.qt import prompt

from mass_circular_weighing.routines.do_new_weighing import do_new_weighing
from mass_circular_weighing.routines.run_circ_weigh import check_ambient_pre, analyse_old_weighing, analyse_all_weighings_in_file
from mass_circular_weighing.routines.collate_data import *
from mass_circular_weighing.routines.final_mass_calc import final_mass_calc


class CheckAmbient(Service):

    def __init__(self):
        super().__init__(max_clients=1, name='Check ambient conditions')

    def get_ambient_t_rh(self, omega):
        return check_ambient_pre(omega)

    def get_ambient_t_rh_dp(self, omega):
        ambient = omega.get_t_rh_dp()
        log.info('Ambient conditions are:\n'+str(ambient))


class DoWeighing(Service):

    def __init__(self):
        super().__init__(max_clients=1, name='Do circular weighing')

    def do_new_weighing(self, app, client, bal_alias, folder, filename, scheme_entry, nominal_mass,
                   omega_alias=None, timed=False, drift=None):

        done_ok = do_new_weighing(app, client, bal_alias, folder, filename, scheme_entry, nominal_mass,
                    omega_alias=omega_alias, timed=timed, drift=drift)

        return done_ok

    #def select_folder(self):
    #    return prompt.folder()


class AnalyseWeighing(Service):

    def __init__(self):
        super().__init__(name='Analyse circular weighing(s)')

    def analyse_one_weighing(self, folder, filename, se, run_id, timed, drift):
        return analyse_old_weighing(folder, filename, se, run_id, timed, drift)

    def analyse_all_weighings_in_file(self, folder, filename, se, timed, drift):
        analyse_all_weighings_in_file(folder, filename, se, timed, drift)


class CollateData(Service):

    def __init__(self):
        super().__init__(name='Collate data from circular weighings')

    def collate_a_data_from_json(self, folder, filename, scheme_entry):
        collated_data = collate_a_data_from_json(folder, filename, scheme_entry)

        if collated_data[1] == True:
            return collated_data[0]
        else:
            log.error('Unacceptable analysis of weighings from '+scheme_entry)
            return None

    def collate_m_data_from_json(self, folder, filename, scheme_entry):
        return collate_m_data_from_json(folder, filename, scheme_entry)

    def collate_data_from_list(self, weighings):
        return collate_data_from_list(weighings)


class FinalMassCalc(Service):

    def __init__(self):
        super().__init__(max_clients=1, name='Final mass calculation')

    def final_mass_calc(self, filesavepath, client, client_wt_IDs, check_wt_IDs, std_masses,
                        inputdata, nbc=True, corr=None):
            return final_mass_calc(filesavepath, client, client_wt_IDs, check_wt_IDs, std_masses,
                                   inputdata, nbc=nbc, corr=corr)



if __name__ == '__main__':
    s = DoWeighing()
    s.start(host='CISS33745')

