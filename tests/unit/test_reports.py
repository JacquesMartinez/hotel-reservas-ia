from datetime import date, timedelta

import pytest

import api

#manager reports: date ranges and the demand forecast

TODAY = date(2026, 10, 28) #a Wednesday; its week starts on Monday 2026-10-26


@pytest.fixture
def manager(client):
	with client.session_transaction() as session:
		session['username'] = 'M2acz'
		session['role'] = 'manager'
	return client


def forecast(total_rooms, stays, weeks=2, history_weeks=2, today=TODAY):
	return api.build_forecast('Atlanta', total_rooms, stays, today, weeks, history_weeks)


# --- build_forecast -------------------------------------------------------------

def test_weeks_run_from_monday_to_sunday():
	result = forecast(1, [])
	assert [w['week_start'] for w in result['history']] == ['2026-10-12', '2026-10-19']
	assert [w['week_start'] for w in result['forecast']] == ['2026-11-02', '2026-11-09']


@pytest.mark.parametrize('today', [date(2026, 10, 26), date(2026, 11, 1)]) #Monday and Sunday of the same week
def test_first_forecast_week_is_next_monday(today):
	assert forecast(1, [], today=today)['forecast'][0]['week_start'] == '2026-11-02'


def test_stay_across_two_weeks_adds_its_nights_to_each_one():
	#Saturday 17 to Wednesday 21: nights 17 and 18 in one week, 19 and 20 in the next
	result = forecast(1, [(date(2026, 10, 17), date(2026, 10, 21))])
	assert [w['occupancy'] for w in result['history']] == pytest.approx([2 / 7, 2 / 7], abs=0.0001)


def test_checkout_night_is_not_occupied():
	#checkout on Monday 19: the night of the 19th belongs to nobody
	result = forecast(1, [(date(2026, 10, 12), date(2026, 10, 19))])
	assert [w['occupancy'] for w in result['history']] == [1.0, 0]


def test_location_without_rooms_has_zero_occupancy():
	result = forecast(0, [(date(2026, 10, 12), date(2026, 10, 19))])
	assert all(w['occupancy'] == 0 for w in result['history'] + result['forecast'])


def test_average_uses_the_weeks_available_when_history_is_shorter_than_four():
	result = forecast(1, [(date(2026, 10, 19), date(2026, 10, 26))])
	assert result['forecast'][0]['occupancy'] == pytest.approx(0.5)


def test_forecast_never_goes_below_what_is_already_booked():
	result = forecast(1, [(date(2026, 11, 9), date(2026, 11, 16))])
	assert result['forecast'][0]['occupancy'] == 0
	assert result['forecast'][1]['booked'] == 1.0
	assert result['forecast'][1]['occupancy'] == 1.0
	assert result['forecast'][1]['price_change_pct'] == 15


@pytest.mark.parametrize('occupancy, pct', [(1.0, 15), (0.8, 15), (0.7999, 0), (0.5, 0), (0.3001, 0), (0.3, -10), (0, -10)])
def test_price_change_thresholds(occupancy, pct):
	assert api.price_change_pct(occupancy) == pct


def test_float_noise_does_not_cross_a_threshold():
	#weeks at 0.2, 0.4, 0.3, 0.3: in floating point (0.2 + 0.4 + 0.3 + 0.3) / 4 is 0.30000000000000004, not 0.3
	stays = []
	for monday, nights in [(date(2026, 9, 28), 14), (date(2026, 10, 5), 28), (date(2026, 10, 12), 21), (date(2026, 10, 19), 21)]:
		stays += [(monday, monday + timedelta(days=1))] * nights #one-night stays: 10 rooms x 7 = 70 room-nights a week
	result = forecast(10, stays, history_weeks=4)
	assert [w['occupancy'] for w in result['history']] == [0.2, 0.4, 0.3, 0.3]
	assert result['forecast'][0]['occupancy'] == 0.3
	assert result['forecast'][0]['price_change_pct'] == -10


# --- /api/reports/forecast ------------------------------------------------------

def test_forecast_requires_manager(client, mysqldb):
	with client.session_transaction() as session:
		session['username'] = 'Cl3a8'
		session['role'] = 'customer'
	assert client.get('/api/reports/forecast?location=Atlanta').status_code == 403
	mysqldb.get_room_stays.assert_not_called()


@pytest.mark.parametrize('query', ['', '?location=', '?location=Atlanta&weeks=0', '?location=Atlanta&weeks=abc', '?location=Atlanta&history_weeks=53'])
def test_forecast_rejects_invalid_parameters(manager, mysqldb, query):
	assert manager.get('/api/reports/forecast' + query).status_code == 400
	mysqldb.get_room_stays.assert_not_called()


def test_forecast_reads_the_whole_period_in_one_call(manager, mysqldb):
	mysqldb.get_room_stays.return_value = (2, [])
	response = manager.get('/api/reports/forecast?location=Atlanta')
	assert response.status_code == 200
	data = response.get_json()
	assert (len(data['history']), len(data['forecast'])) == (12, 8) #defaults
	monday = date.today() - timedelta(days=date.today().weekday())
	mysqldb.get_room_stays.assert_called_once_with('Atlanta', monday - timedelta(days=7 * 12), monday + timedelta(days=7 * 9))


# --- date range of the existing reports ----------------------------------------

@pytest.mark.parametrize('url', ['/api/reports/revenue', '/api/reports/reservation'])
@pytest.mark.parametrize('query', ['?from=2026-13-01', '?to=01/31/2026', '?from=2026-02-01&to=2026-01-31'])
def test_reports_reject_invalid_ranges(manager, mysqldb, url, query):
	assert manager.get(url + query).status_code == 400
	mysqldb.revenue_report.assert_not_called()
	mysqldb.reservation_report.assert_not_called()


@pytest.mark.parametrize('url, method', [('/api/reports/revenue', 'revenue_report'), ('/api/reports/reservation', 'reservation_report')])
def test_reports_pass_the_range_to_the_database(manager, mysqldb, url, method):
	getattr(mysqldb, method).return_value = {'2026-01': {'Atlanta': 1}}
	response = manager.get(url + '?from=2026-01-01&to=2026-01-31')
	assert response.status_code == 200
	assert response.get_json() == {'2026-01': {'Atlanta': 1}}
	getattr(mysqldb, method).assert_called_once_with(date(2026, 1, 1), date(2026, 1, 31))


@pytest.mark.parametrize('url, method', [('/api/reports/revenue', 'revenue_report'), ('/api/reports/reservation', 'reservation_report')])
def test_reports_without_range_have_no_limits(manager, mysqldb, url, method):
	getattr(mysqldb, method).return_value = {}
	assert manager.get(url).status_code == 200
	getattr(mysqldb, method).assert_called_once_with(None, None)
