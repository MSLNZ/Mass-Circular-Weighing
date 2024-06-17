import pytest

from mass_circular_weighing.utils.airdens_calculator import AirDens2009


@pytest.mark.parametrize("test_val", [15, 20, 25])
def test_airdens_temp(test_val):
    airdens = AirDens2009(test_val, 1013, 50, 0.004)

    assert 1.17 < airdens < 1.23


@pytest.mark.parametrize("test_val", [1011, 1012, 1013, 1014, 1015])
def test_airdens_press(test_val):
    airdens = AirDens2009(20, test_val, 50, 0.004)

    assert 1.17 < airdens < 1.23


@pytest.mark.parametrize("test_val", [30, 35, 40, 45, 50, 55, 60, 65, 70])
def test_airdens_hum(test_val):
    airdens = AirDens2009(20, 1013, test_val, 0.004)

    assert 1.17 < airdens < 1.23


@pytest.mark.parametrize("test_val", [0.0, 0.001, 0.002, 0.003, 0.004, 0.005, 0.006])
def test_airdens_co2(test_val):
    airdens = AirDens2009(20, 1013, 50, test_val)

    assert 1.17 < airdens < 1.23
