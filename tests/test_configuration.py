import numpy as np
import pytest
import os

from mass_circular_weighing.configuration import Configuration
from mass_circular_weighing.constants import MU_STR, client_default, job_default

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
admin_for_test = os.path.join(ROOT_DIR, r'tests\samples\admin_for_testing.xlsx')
config_for_test = os.path.join(ROOT_DIR, r'tests\samples\config_for_testing.xml')
config_fmc = os.path.join(ROOT_DIR, r'tests\samples\config_fmc.xml')
admin_no_details = os.path.join(ROOT_DIR, r'tests\samples\admin_no_details.xlsx')


def test_no_admin_details():
    # this config has no Client, Job or Folder, and no weights in weight set
    # testing default values are picked up
    cfg = Configuration(admin_no_details)

    assert cfg.operator is None
    assert cfg.client == client_default
    assert cfg.job == job_default
    assert cfg.folder == os.path.join(ROOT_DIR, r'tests\samples')

    assert cfg.config_xml in config_fmc

    assert cfg.std_set == "CUSTOM"
    assert cfg.check_set is None
    assert not cfg.client_wt_IDs

    # Circular Weighing Analysis Parameters
    assert cfg.drift is None
    assert cfg.timed is False
    assert cfg.calc_true_mass is False
    assert cfg.correlations.shape[0] == cfg.correlations.shape[1]
    assert cfg.correlations.all() == np.identity(2).all()

    assert cfg.scheme is None


def test_admin_details():

    cfg = Configuration(admin_for_test)

    assert cfg.operator == 'MCW'
    assert cfg.client == '1 kg to 1 mg weight set'.replace(" ","")
    assert cfg.job == 'Program Check'

    assert cfg.config_xml in config_for_test

    assert cfg.std_set == 'Mettler A'
    assert cfg.check_set == 'Mettler B'
    assert cfg.all_client_wts
    assert len(cfg.client_wt_IDs) == cfg.ds['E13'].value == 25  # added weights to make a full set

    # Circular Weighing Analysis Parameters
    assert cfg.drift == 'linear drift'
    assert cfg.timed is False
    assert cfg.calc_true_mass is True
    assert cfg.correlations.shape[0] == cfg.correlations.shape[1]
    assert cfg.correlations.all() == np.eye(cfg.correlations.shape[0]).all()

    assert cfg.scheme[0] == ['Weight groups', 'Nominal mass (g)', 'Balance alias', '# runs']
    assert cfg.scheme[1] == [
        ['100 100MA 100MB', '100', 'AT106', '5'],
        ['1000 1KMA 1KMB', '1000', 'AX10005', '10'],
        ['5000 5KMA 5KMB', '5000', 'AX10005', '10']
    ]


def test_load_mass_set():
    cfg = Configuration(admin_for_test)     # uses Mettler A and B as for FMC
    cfg.init_ref_mass_sets()

    assert cfg.massref_path == cfg.all_stds['MASSREF file'] == r"tests\samples\MASSREF4tests.xlsx"
    assert cfg.all_stds['Set name'] == 'Mettler 11'
    assert cfg.all_stds['Sheet name'] == 'Mettler A'
    assert cfg.all_stds['Set type'] == 'Standard'
    assert cfg.all_stds['Set identifier'] == 'MA'
    assert cfg.all_stds['Nominal (g)'][0] == 10000
    assert '10KMA' in cfg.all_stds['Weight ID']
    assert len(cfg.all_stds['Weight ID']) == len(cfg.all_stds['Nominal (g)']) \
        == len(cfg.all_stds['mass values (g)']) == len(cfg.all_stds['uncertainties (' + MU_STR + 'g)']) == 22

    assert cfg.all_checks['Set name'] == 'Mettler 11'
    assert cfg.all_checks['Sheet name'] == 'Mettler B'
    assert cfg.all_checks['Set type'] == 'Check'
    assert cfg.all_checks['Set identifier'] == 'MB'
    assert cfg.all_checks['Nominal (g)'][0] == 10000
    assert '10KMB' in cfg.all_checks['Weight ID']
    assert len(cfg.all_checks['Weight ID']) == len(cfg.all_checks['Nominal (g)']) \
        == len(cfg.all_checks['mass values (g)']) == len(cfg.all_checks['uncertainties (' + MU_STR + 'g)']) == 22

    cfg = Configuration(admin_no_details)   # uses Custom and None
    cfg.init_ref_mass_sets()
    assert cfg.massref_path == cfg.all_stds['MASSREF file'] == r"tests\samples\MASSREF4tests.xlsx"
    assert cfg.all_stds['Set identifier'] == "CUSTOM"
    assert cfg.all_stds['Nominal (g)'][0] == 10000
    assert cfg.all_checks is None


def test_acceptance_criteria():

    cfg = Configuration(admin_for_test)

    with pytest.raises(ValueError) as err:
        cfg.acceptance_criteria('MDE-demo', 100000)
    assert 'out of range' in str(err.value)

    with pytest.raises(ValueError) as err:
        cfg.acceptance_criteria('OMEGA', 500)
    assert 'No acceptance' in str(err.value)

    with pytest.raises(ValueError) as err:
        cfg.acceptance_criteria('does not exist', 500)
    assert 'No equipment record' in str(err.value)

    ac = cfg.acceptance_criteria('MDE-demo', 500)
    assert ac['Max stdev from CircWeigh ('+MU_STR+'g)'] == 20.
    assert ac['Stdev for balance ('+MU_STR+'g)'] == 15.
