import os
from datetime import (
    date,
    datetime,
)

import pytest
import numpy as np

from mass_circular_weighing.equip import LabEnviron64

has_runtime = os.path.isfile(r'C:\Program Files (x86)\National Instruments\Shared\LabVIEW Run-Time\2010\lvrt.dll')
has_idrive = os.path.isdir('I:\\MSL\\Shared')
has_server = LabEnviron64.ping(LabEnviron64.LABVIEW_SERVER)


def test_to_datetime():
    assert LabEnviron64.to_datetime(None).date() == date.today()
    assert LabEnviron64.to_datetime('2020-6-7') == datetime(2020, month=6, day=7)
    assert LabEnviron64.to_datetime('7/6/20', fmt='%d/%m/%y') == datetime(2020, month=6, day=7)
    now = datetime.now()
    assert LabEnviron64.to_datetime(now) == now
    assert LabEnviron64.to_datetime(now.timestamp()) == now
    with pytest.raises(TypeError):
        assert LabEnviron64.to_datetime(dict())


def test_ping():
    assert LabEnviron64.ping('127.0.0.1')
    assert not LabEnviron64.ping('10.0.0.1')


@pytest.mark.skipif(not has_runtime, reason='requires LabVIEW Run-Time 2010')
def test_invalid_server_ip():
    # cache the default LabEnviron64.LABVIEW_SERVER value since it gets modified for this test
    default_ip = LabEnviron64.LABVIEW_SERVER

    # do the test
    lab = LabEnviron64('10.0.0.1')
    assert LabEnviron64.LABVIEW_SERVER == '10.0.0.1'
    data, error = lab.get_data('mass 1', 0)
    assert data.size == 0
    assert error == 'The LabVIEW server at 10.0.0.1 is unreachable'
    lab.shutdown_server32()

    # reset the default IP address
    LabEnviron64.LABVIEW_SERVER = default_ip


@pytest.mark.skipif(
    not (has_runtime and has_idrive and has_server),
    reason='requires LabVIEW Run-Time 2010, I: drive access and for the LabEnviron server to be reachable'
)
def test_get_data():
    lab = LabEnviron64()

    # invalid probe number
    for probe in [-1, 6, -0.1, 5.1]:
        with pytest.raises(ValueError):
            lab.get_data('does not matter', probe)

    # the Light 1 and Light 2 LabVIEW servers have been shut down
    for ithx in ['invalid', 'light 1', 'light 2']:
        data, error = lab.get_data(ithx, 0)
        assert 0 == data.size
        assert error.startswith('No Data From Server [iTHX={!r}, start='.format(ithx))

    # there is data within the specified date range
    first_record = [datetime(2020, 4, 30, 0, 0, 12), 20.09, 56.37, 11.13, 20.27, 56.42, 11.32]
    last_record = [datetime(2020, 4, 30, 23, 59, 31), 20.13, 55.08, 10.83, 20.31, 55.11, 11.01]
    size = 432+1000+3  # the data for 2020-4-30 is spread across 3 CSV files
    for i in range(6):
        # also tests that date_start == date_end (so date_end becomes 1 second before midnight)
        data, error = lab.get_data('mass 2', i, '2020-4-30', '2020-4-30', coeff=False)
        assert data.size == size
        assert not error
        assert data['timestamp'][0] == first_record[0]
        assert data[0][1] == first_record[i+1]
        assert data['timestamp'][-1] == last_record[0]
        assert data[-1][1] == last_record[i+1]

    # there is no data within the specified date range
    data, error = lab.get_data('mass 2', 0, '2020-5-25', '2020-5-25')
    assert data.size == 0
    assert error == "No Data From Server [iTHX='mass 2', start=2020-05-25 00:00:00, end=2020-05-25 23:59:59]"

    data, error = lab.get_data('mass 2', 0, '2020-5-25', '2020-5-26')
    assert data.size == 0
    assert error == "No Data From Server [iTHX='mass 2', start=2020-05-25 00:00:00, end=2020-05-26 00:00:00]"

    data, error = lab.get_data('mass 2', 0, datetime(2020, 5, 25, 9, 20, 11), datetime(2020, 5, 25, 11, 7, 48))
    assert data.size == 0
    assert error == "No Data From Server [iTHX='mass 2', start=2020-05-25 09:20:11, end=2020-05-25 11:07:48]"

    # fetch data for a narrow time window
    expected = [
        (datetime(2020, 4, 30, 12, 47, 53), 20.36, 20.58, 55.28, 55.11, 11.1, 11.26),
        (datetime(2020, 4, 30, 12, 48, 53), 20.36, 20.58, 55.28, 55.11, 11.1, 11.26),
        (datetime(2020, 4, 30, 12, 49, 54), 20.34, 20.58, 55.28, 55.14, 11.1, 11.25),
        (datetime(2020, 4, 30, 12, 50, 54), 20.34, 20.58, 55.28, 55.17, 11.08, 11.27),
        (datetime(2020, 4, 30, 12, 51, 54), 20.34, 20.58, 55.27, 55.21, 11.08, 11.27),
        (datetime(2020, 4, 30, 12, 52, 54), 20.34, 20.55, 55.27, 55.24, 11.08, 11.26)
    ]

    # fetch temperature data for sensor 1
    data, error = lab.get_data('mass 2', 0, date_start=expected[0][0], date_end=expected[-1][0], coeff=False)
    assert not error
    assert data.size == 6
    assert np.array_equal(data['timestamp'], [expected[i][0] for i in range(6)])
    assert np.array_equal(data['temperature1'], [expected[i][1] for i in range(6)])

    # fetch humidity data for sensor 1
    data, error = lab.get_data('mass 2', 1, date_start=expected[0][0], date_end=expected[-1][0], coeff=False)
    assert not error
    assert data.size == 6
    assert np.array_equal(data['timestamp'], [expected[i][0] for i in range(6)])
    assert np.array_equal(data['humidity1'], [expected[i][3] for i in range(6)])

    # fetch dew point data for sensor 1
    data, error = lab.get_data('mass 2', 2, date_start=expected[0][0], date_end=expected[-1][0], coeff=False)
    assert not error
    assert data.size == 6
    assert np.array_equal(data['timestamp'], [expected[i][0] for i in range(6)])
    assert np.array_equal(data['dewpoint1'], [expected[i][5] for i in range(6)])

    # fetch temperature data for sensor 2
    data, error = lab.get_data('mass 2', 3, date_start=expected[0][0], date_end=expected[-1][0], coeff=False)
    assert not error
    assert data.size == 6
    assert np.array_equal(data['timestamp'], [expected[i][0] for i in range(6)])
    assert np.array_equal(data['temperature2'], [expected[i][2] for i in range(6)])

    # fetch humidity data for sensor 2
    data, error = lab.get_data('mass 2', 4, date_start=expected[0][0], date_end=expected[-1][0], coeff=False)
    assert not error
    assert data.size == 6
    assert np.array_equal(data['timestamp'], [expected[i][0] for i in range(6)])
    assert np.array_equal(data['humidity2'], [expected[i][4] for i in range(6)])

    # fetch dew point data for sensor 2
    data, error = lab.get_data('mass 2', 5, date_start=expected[0][0], date_end=expected[-1][0], coeff=False)
    assert not error
    assert data.size == 6
    assert np.array_equal(data['timestamp'], [expected[i][0] for i in range(6)])
    assert np.array_equal(data['dewpoint2'], [expected[i][6] for i in range(6)])

    # get the calibrated data
    data, error = lab.get_data('mass 2', 0, date_start=expected[0][0], date_end=expected[-1][0])
    assert not error
    assert data.size == 6
    assert np.array_equal(data['timestamp'], [expected[i][0] for i in range(6)])
    assert not np.array_equal(data['temperature1'], [expected[i][1] for i in range(6)])

    # shutdown the 32-bit Python server
    lab.shutdown_server32()
