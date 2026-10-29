def test_mis_reservas_requiere_sesion(client, mysqldb):
	response = client.get('/api/reservations')
	assert response.status_code == 401
	mysqldb.get_reservations.assert_not_called()


def test_mis_reservas_usa_el_usuario_de_la_sesion(client, mysqldb):
	reservas = [{'reservation_id': 7, 'checkin_date': '2026-11-01', 'checkout_date': '2026-11-03', 'total_cost': 200.0,
		'cancelled_or_not': '0', 'card_last4': '1111', 'rooms': []}]
	mysqldb.get_reservations.return_value = reservas
	with client.session_transaction() as sesion:
		sesion['username'] = 'Cl3a8'
		sesion['role'] = 'customer'
	#el username de la petición se ignora (S1)
	response = client.get('/api/reservations?username=Cyp7d')
	assert response.status_code == 200
	assert response.get_json() == reservas
	mysqldb.get_reservations.assert_called_once_with('Cl3a8')
