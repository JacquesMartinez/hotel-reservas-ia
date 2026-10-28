import pytest

#reservation dates and rooms are validated before anything is written (#11)

ROOM = {'location': 'Atlanta', 'room_number': 101, 'cost': 100, 'extra_bed_price': 20, 'extra_bed_or_not': 0}


@pytest.fixture
def client(client):
	#the reservation endpoints require a session; the username now comes from it, not from the request
	with client.session_transaction() as session:
		session['username'] = 'Cl3a8'
		session['role'] = 'customer'
	return client


def create(client, checkIn='2030-01-01', checkOut='2030-01-03', rooms=None):
	return client.post('/api/reservation/create', json={
		'username': 'Cl3a8', 'checkIn': checkIn, 'checkOut': checkOut,
		'card_number': '4111111111111111', 'rooms': [ROOM] if rooms is None else rooms})


@pytest.mark.parametrize('checkIn, checkOut', [
	('01/01/2030', '2030-01-03'),  #wrong format
	('2030-02-30', '2030-03-02'),  #date that does not exist
	('2030-01-01', '2030-01-01'),  #0 nights
	('2030-01-05', '2030-01-01'),  #check-out before check-in
])
def test_create_reservation_rejects_invalid_stay(client, mysqldb, checkIn, checkOut):
	response = create(client, checkIn, checkOut)
	assert response.status_code == 400
	mysqldb.insert_reservation.assert_not_called()


@pytest.mark.parametrize('room', [
	{k: v for k, v in ROOM.items() if k != 'location'},
	dict(ROOM, location=''),
	dict(ROOM, room_number=None),
	'Atlanta101',
])
def test_create_reservation_rejects_incomplete_room(client, mysqldb, room):
	response = create(client, rooms=[room])
	assert response.status_code == 400
	mysqldb.insert_reservation.assert_not_called()


def test_create_reservation_rejects_taken_room(client, mysqldb):
	mysqldb.is_room_free.return_value = False
	response = create(client)
	assert response.status_code == 409
	mysqldb.insert_reservation.assert_not_called()


def test_create_reservation_valid(client, mysqldb):
	mysqldb.is_room_free.return_value = True
	mysqldb.insert_reservation.return_value = (7, 'Successfully created reservation', True)
	response = create(client)
	assert response.status_code == 200
	mysqldb.insert_reservation.assert_called_once_with('Cl3a8', '2030-01-01', '2030-01-03', '4111111111111111', [ROOM], 200)


@pytest.mark.parametrize('checkIn, checkOut', [('2030-01-01', '2030-01-01'), ('2030-13-01', '2030-13-03')])
def test_update_reservation_rejects_invalid_stay(client, mysqldb, checkIn, checkOut):
	response = client.put('/api/reservation', json={
		'reservation_id': '7', 'username': 'Cl3a8', 'checkIn': checkIn, 'checkOut': checkOut})
	assert response.status_code == 400
	mysqldb.update_reservation.assert_not_called()


def test_update_availability_rejects_zero_nights(client, mysqldb):
	response = client.get('/api/reservation/7/availability?username=Cl3a8&checkIn=2030-01-01&checkOut=2030-01-01')
	assert response.status_code == 400
	mysqldb.is_room_free.assert_not_called()
