import pytest

from mass_circular_weighing.equip.ambient_fromwebapp import *

has_server = ping('172.16.31.199')  # not sure how to do this so that it won't break...


def test_ping():
    assert ping('127.0.0.1')
    assert not ping('10.0.0.1')


@pytest.mark.skipif(not has_server, reason='requires access to server running webapp')
def test_get_t_rh_now():
    # invalid alias
    for ithx in ['Mass1', 'mass 1', 'M']:
        timestr, temp, hum = get_t_rh_now(ithx, sensor=1)
        timestamp = datetime.fromisoformat(timestr)
        assert timestamp.date() == datetime.date(datetime.now())
        assert timestamp.hour == datetime.now().hour
        assert datetime.now().minute - 1 <= timestamp.minute <= datetime.now().minute
        assert temp is None
        assert hum is None

    # invalid probe number
    for probe in [-1, 6, -0.1, 5.1]:
        with pytest.raises(KeyError):
            get_t_rh_now('Mass 1', sensor=probe)

    # operational
    ambient = get_t_rh_now('Mass 1', sensor=1)
    assert len(ambient) == 3
    assert isinstance(ambient[0], str)
    timestamp = datetime.fromisoformat(ambient[0])
    assert timestamp.date() == datetime.date(datetime.now())
    assert timestamp.hour == datetime.now().hour
    assert datetime.now().minute - 1 <= timestamp.minute <= datetime.now().minute

    assert isinstance(ambient[1], float) and isinstance(ambient[2], float)
    assert 0 < ambient[1] < 30
    assert 10 < ambient[2] < 100


@pytest.mark.skipif(not has_server, reason='requires access to server running webapp')
def test_get_t_rh_during():
    # there is data within the specified date range
    temperatures = [19.6382 , 19.64808, 19.62832, 19.52952, 19.61844, 19.62832,
       19.6382 , 19.6382 , 19.62832, 19.62832, 19.62832, 19.62832,
       19.62832, 19.6382 , 19.62832, 19.62832, 19.62832, 19.62832,
       19.6382 , 19.64808, 19.6382 , 19.64808, 19.64808, 19.6382 ,
       19.64808, 19.6382 , 19.6382 , 19.64808, 19.64808, 19.6382 ,
       19.65796, 19.64808, 19.64808, 19.6382 , 19.64808, 19.64808,
       19.64808, 19.65796, 19.64808, 19.64808, 19.65796, 19.65796,
       19.6382 , 19.65796, 19.65796, 19.65796, 19.66784, 19.64808,
       19.64808, 19.65796, 19.65796, 19.65796, 19.64808, 19.64808,
       19.66784, 19.65796, 19.65796, 19.64808, 19.66784, 19.65796]

    humidities = [64.38549224, 64.38549224, 64.38549224, 64.7809523 , 64.38549224,
       64.31960783, 64.31960783, 64.28666837, 64.31960783, 64.28666837,
       64.25373074, 64.22079494, 64.25373074, 64.25373074, 64.22079494,
       64.22079494, 64.22079494, 64.22079494, 64.22079494, 64.22079494,
       64.17688338, 64.18786097, 64.18786097, 64.18786097, 64.15492882,
       64.14395185, 64.14395185, 64.15492882, 64.18786097, 64.14395185,
       64.18786097, 64.18786097, 64.15492882, 64.18786097, 64.18786097,
       64.15492882, 64.18786097, 64.15492882, 64.15492882, 64.12199851,
       64.15492882, 64.12199851, 64.11102214, 64.08907002, 64.08907002,
       64.04516821, 64.02321853, 63.9793216 , 63.9793216 , 63.9793216 ,
       63.94640104, 63.94640104, 63.91348231, 63.8805654 , 63.84765033,
       63.8805654 , 63.8805654 , 63.84765033, 63.84765033, 63.84765033]

    temps, hums = get_t_rh_during('Mass 1', sensor=2, start="2021-03-11 13:00", end="2021-03-11 14:00")
    # note that these values are corrected by default
    assert len(temps) == len(temperatures) == len(hums) == len(humidities) == 60

    assert temps[0] == pytest.approx(19.6382)
    assert hums[0] == pytest.approx(64.38549224)
    assert temps[-1] == pytest.approx(19.65796)
    assert hums[-1] == pytest.approx(63.84765033)

    # there is no data within the specified date range
    temps, hums = get_t_rh_during('Mass 1', sensor=1, start="2021-03-01 13:00", end="2021-03-01 13:00")# start='2021-2-27 12:00', end='2021-2-28 12:00')
    assert temps.size == 0
    assert hums.size == 0

    temps, hums = get_t_rh_during('Mass 1', sensor=1, start="2010-03-03 13:00", end="2010-04-04 13:00")# start='2021-2-27 12:00', end='2021-2-28 12:00')
    assert temps.size == 0
    assert hums.size == 0

    # fetch data for a narrow time window
    temps, hums = get_t_rh_during('Mass 1', sensor=1, start="2021-03-01 13:00", end="2021-03-01 13:02")
    temperatures = [20.09202, 20.07244]
    humidities = [65.00239709, 65.00239709]
    for t1, t2 in zip(temps, temperatures):
        assert t1 == pytest.approx(t2)
    for h1, h2 in zip(humidities, hums):
        assert h1 == pytest.approx(h2)
    # note that the uncorrected values are [20.38, 20.36]and [66.58, 66.58] which fails the assertion


if __name__ == "__main__":
    test_ping()
    test_get_t_rh_now()
    test_get_t_rh_during()
