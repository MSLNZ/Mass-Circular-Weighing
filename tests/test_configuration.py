import pytest
import os

from mass_circular_weighing.configuration import Configuration
from mass_circular_weighing.constants import MU_STR, config_default, save_folder_default, client_default, job_default

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
admin_for_test = os.path.join(ROOT_DIR, r'tests\samples\admin_for_testing.xlsx')
config_for_test = os.path.join(ROOT_DIR, r'tests\samples\config_for_testing.xml')
config_no_details = os.path.join(ROOT_DIR, r'tests\samples\admin_no_details.xlsx')


def test_no_admin_details():
    # this config has no Client, Job or Folder, and no weights in weight set
    # testing default values are picked up
    cfg = Configuration(config_no_details)

    assert cfg.operator is None
    assert cfg.client == client_default
    assert cfg.job == job_default
    assert cfg.folder == save_folder_default

    assert cfg.config_xml == config_default

    assert cfg.std_set == "CUSTOM"
    assert cfg.check_set is None
    assert not cfg.client_wt_IDs

    # Circular Weighing Analysis Parameters
    assert cfg.drift is None
    assert cfg.timed is False
    assert cfg.correlations is None

    assert cfg.scheme is None


def test_admin_details():

    cfg = Configuration(admin_for_test)

    assert cfg.operator == 'MCW'
    assert cfg.client == '1 kg to 1 g weight set'.replace(" ","")
    assert cfg.job == 'Program Check'

    assert cfg.config_xml in config_for_test

    assert cfg.std_set == "CUSTOM"
    assert cfg.check_set is None
    assert cfg.all_client_wts
    assert len(cfg.client_wt_IDs) == cfg.ds['E13'].value == 13

    # Circular Weighing Analysis Parameters
    assert cfg.drift is None
    assert cfg.timed is False
    assert cfg.correlations is None

    assert cfg.scheme[0] == ['Weight groups', 'Nominal mass (g)', 'Balance alias', '# runs']
    assert cfg.scheme[1] == [
        ['100 100MA 100MB', '100', 'AT106', '5'],
        ['1000 1KMA 1KMB', '1000', 'AX10005', '10'],
        ['5000 5KMA 5KMB', '5000', 'AX10005', '10']
    ]


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

    with pytest.raises(AttributeError) as err:
        cfg.init_ref_mass_sets()
    assert 'NoneType' in str(err.value)


def test_check_scheme():
    pass


if __name__ == '__main__':
    test_acceptance_criteria()