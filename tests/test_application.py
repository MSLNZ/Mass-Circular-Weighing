import pytest
from mass_circular_weighing.configuration import Configuration


def test_acceptance_criteria():

    cfg = Configuration(r'C:\Users\r.hawke\PycharmProjects\Mass-Circular-Weighing\config.xml')

    with pytest.raises(ValueError) as err:
        cfg.acceptance_criteria('MDE-demo', 100000)
    assert 'out of range' in str(err.value)

    with pytest.raises(ValueError) as err:
        cfg.acceptance_criteria('KCC300', 500)
    assert 'No acceptance' in str(err.value)

    with pytest.raises(ValueError) as err:
        cfg.acceptance_criteria('does not exist', 500)
    assert 'No equipment record' in str(err.value)

    ac = cfg.acceptance_criteria('MDE-demo', 500)
    assert ac['Acceptance criteria'] == 20.
    assert ac['Upper limit for residuals'] == 30.