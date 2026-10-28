def test_index_serves_spa(client):
	response = client.get('/')
	assert response.status_code == 200
	assert b'ng-view' in response.data


def test_login_valid_credentials(client, mysqldb):
	mysqldb.login.return_value = 'customer'
	response = client.post('/api/login', json={'username': 'Cl3a8', 'password': 'cliente123'})
	assert response.status_code == 200
	assert response.get_json()['result'] is True
	mysqldb.login.assert_called_once_with('Cl3a8', 'cliente123')


def test_login_invalid_credentials(client, mysqldb):
	mysqldb.login.return_value = False
	response = client.post('/api/login', json={'username': 'Cl3a8', 'password': 'wrong'})
	assert response.status_code == 401


def test_search_rooms_reads_query_string(client, mysqldb):
	#GET without a JSON body: reqparse must still work on Flask 3
	mysqldb.search_rooms.return_value = {'response': [], 'result': False}
	response = client.get('/api/searchRoom?location=Atlanta&checkIn=2026-11-01&checkOut=2026-11-03')
	assert response.status_code == 200
	mysqldb.search_rooms.assert_called_once_with('Atlanta', '2026-11-01', '2026-11-03')
