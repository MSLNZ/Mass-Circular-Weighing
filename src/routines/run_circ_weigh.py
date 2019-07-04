import os
from msl.io import JSONWriter, read
from msl.equipment import Config
from src.equip.mdebalance import Balance
from src.routines.circ_weigh_class import CircWeigh
from time import perf_counter
import numpy as np
from ..log import log


class RunCircWeigh(object):

    def __init__(self, client, balance, folder, filename, scheme_entry, identifier='run1', nominal_mass=None, ):

        self.se = scheme_entry
        self.weighing = CircWeigh(self.se)

        cfg = Config(balance[0])
        alias = balance[1]
        self.bal = Balance(cfg, alias)
        self.metadata = {'Client': client, 'Balance': alias, 'Unit': self.bal.unit, 'Nominal mass': nominal_mass}

        self.folder = folder
        self.run_id = identifier
        self.url = folder+"\\"+filename+'.json'

        self.root = JSONWriter()
        self.schemefolder = self.check_for_existing_weighdata()

    def check_for_existing_weighdata(self):
        if os.path.isfile(self.url):
            existing_root = read(self.url)
            new_index = len(os.listdir(self.folder + "\\backups\\"))
            new_file = str(self.folder + "\\backups\\" + self.run_id + '_backup{}.json'.format(new_index))
            JSONWriter().save(root=existing_root, url=new_file, mode='w')
            existing_root.is_read_only = False
            self.root = existing_root

            schemefolder = self.root['Circular Weighings'][self.se]

        else:
            print('Creating new file for weighing')
            circularweighings = self.root.require_group('Circular Weighings')
            schemefolder = circularweighings.require_group(self.se)

        return schemefolder

    def check_ambient_pre(self):
        # check ambient conditions meet quality criteria for commencing weighing
        ambient_pre = {'T': 20.0, 'RH': 50.0}  # TODO: link this to Omega logger

        if 18.1 < ambient_pre['T'] < 21.9:
            log.info('Ambient temperature OK for weighing')
            self.metadata['T_pre (deg C)'] = ambient_pre['T']  # \xb0 is degree in unicode
        else:
            raise ValueError('Ambient temperature does not meet limits')

        if 33 < ambient_pre['RH'] < 67:
            log.info('Ambient humidity OK for weighing')
            self.metadata['RH_pre (%)'] = ambient_pre['RH']
        else:
            raise ValueError('Ambient humidity does not meet limits')

    def check_ambient_post(self):
        # check ambient conditions meet quality criteria during weighing
        ambient_post = {'T': 20.3, 'RH': 44.9}  # TODO: get from Omega logger
        self.metadata['T_post (deg C)'] = ambient_post['T']
        self.metadata['RH_post (%)'] = ambient_post['RH']

        if (self.metadata['T_pre (deg C)'] - ambient_post['T'])**2 > 0.25:
            self.metadata['Quality'] = 'exclude'
            log.warning('Ambient temperature change during weighing exceeds quality criteria')
        elif (self.metadata['RH_pre (%)'] - ambient_post['RH'])**2 > 225:
            self.metadata['Quality'] = 'exclude'
            log.warning('Ambient humidity change during weighing exceeds quality criteria')
        else:
            log.info('Ambient conditions OK during weighing')
            self.metadata['Quality'] = 'include'

    def do_weighing(self):
        self.check_ambient_pre()

        # collect data and save as measurement dataset in scheme_entry group
        #root = JSONWriter()
        #circularweighings = root.require_group('Circular Weighings')
        #schemefolder = circularweighings.require_group(self.se)

        print("Beginning circular weighing for scheme entry", self.se)

        print('Number of weight groups in weighing =', self.weighing.num_wtgrps)
        print('Number of cycles =', self.weighing.num_cycles)
        print('Weight groups are positioned as follows:')
        for i in range(self.weighing.num_wtgrps):
            print('Position', str(i + 1) + ':', self.weighing.wtgrps[i])
            self.metadata['grp' + str(i + 1)] = self.weighing.wtgrps[i]

        data = np.empty(shape=(self.weighing.num_cycles, self.weighing.num_wtgrps, 2))
        weighdata = self.schemefolder.require_dataset('measurement_' + self.run_id, data=data)
        weighdata.add_metadata(**self.metadata)

        # do circular weighing:
        times = []
        t0 = 0
        for cycle in range(self.weighing.num_cycles):
            for pos in range(self.weighing.num_wtgrps):
                mass = self.weighing.wtgrps[pos]
                self.bal.load_bal(mass)
                reading = self.bal.get_mass_stable()
                if times==[]:
                    time = 0
                    t0 = perf_counter()
                else:
                    time = np.round((perf_counter() - t0) / 60, 6)  # elapsed time in minutes
                times.append(time)
                weighdata[cycle, pos, :] = [time, reading]
                JSONWriter().save(url=self.url, root=self.root, mode='w')
                self.bal.unload_bal(mass)
        weighdata.add_metadata(**{'Timestamps': np.round(times, 4)})
        weighdata.add_metadata(**{'Time unit': 'min'})
        JSONWriter().save(url=self.url, root=self.root, mode='w')

        self.check_ambient_post()
        JSONWriter().save(url=self.url, root=self.root, mode='w')

        print(weighdata[:, :, 1])

    def analyse_weighing(self, timestamp=True, drift=None):
        weighdata = self.schemefolder['measurement_' + self.run_id]

        if timestamp:
            times=np.reshape(weighdata[:, :, 0], self.weighing.num_readings)
            self.weighing.generate_design_matrices(times)
        else:
            self.weighing.generate_design_matrices(times=[])

        d = self.weighing.determine_drift(weighdata[:, :, 1])  # allows program to select optimum drift correction

        if drift==None:
            drift = d

        print()
        print('Residual std dev. for each drift order:')
        print(self.weighing.stdev)

        print()
        print('Selected drift correction is', drift, '(in', self.bal.unit, 'per reading):')
        print(self.weighing.drift_coeffs(drift))

        analysis = self.weighing.item_diff(drift)
        # TODO: add here the balance uncertainty in final column (same for all)
        #  - depends on value of nominal_mass and balance combination as per acceptance criteria
        # TODO: check circular weighing against acceptance criteria for the balance

        print()
        print('Differences (in', self.bal.unit+'):')
        print(self.weighing.grpdiffs)

        # save analysis to json file
        weighanalysis = self.schemefolder.require_dataset('analysis_'+self.run_id,
            data=analysis, shape=(self.weighing.num_wtgrps, 1))

        analysis_meta = {
            'Residual std devs, \u03C3': str(self.weighing.stdev),
            'Selected drift': drift,
            'Mass unit': self.bal.unit,
            'Drift unit': self.bal.unit+' per '+self.weighing.trend,
        }

        for key, value in self.weighing.driftcoeffs.items():
            analysis_meta[key] = value

        weighanalysis.add_metadata(**analysis_meta)

        JSONWriter().save(url=self.url, root=self.root, mode='w')

        print()
        print('Circular weighing complete')
