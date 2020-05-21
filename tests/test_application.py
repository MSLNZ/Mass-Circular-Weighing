import pytest
import os

from mass_circular_weighing.configuration import Configuration
from mass_circular_weighing.constants import MU_STR

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
config_for_test = os.path.join(ROOT_DIR, r'tests\samples\config_for_testing.xml')


def test_acceptance_criteria():

    cfg = Configuration(config_for_test)

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


if __name__ == '__main__':
    test_acceptance_criteria()