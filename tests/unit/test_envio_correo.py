import logging
from unittest.mock import MagicMock

import pytest

import api
import correo

#reservation confirmation email (#8); integration tests with MySQL are in tests/integration/test_correo.py

ROOMS = [{'location': 'Atlanta', 'room_number': 101, 'extra_bed_or_not': 1}]


@pytest.fixture
def smtp(monkeypatch, mysqldb):
	server = MagicMock()
	smtp_class = MagicMock()
	smtp_class.return_value.__enter__.return_value = server
	monkeypatch.setattr(correo.smtplib, 'SMTP', smtp_class)
	monkeypatch.setattr(correo.db, 'mysqldb', mysqldb)
	mysqldb.get_customer_email.return_value = 'cl3a8@example.com'
	for name in ('MAIL_MODE', 'MAIL_HOST', 'MAIL_PORT', 'MAIL_FROM', 'MAIL_USER', 'MAIL_PASSWORD'):
		monkeypatch.delenv(name, raising=False)
	return smtp_class, server


def send():
	correo.send_reservation_confirmation('Cl3a8', 7, '2030-01-01', '2030-01-03', ROOMS, 340)


def test_console_is_the_default_and_does_not_open_smtp(smtp, capsys):
	smtp_class, _ = smtp
	send()
	smtp_class.assert_not_called()
	printed = capsys.readouterr().out
	for text in ('cl3a8@example.com', '7', '2030-01-01', '2030-01-03', 'Atlanta', '101', 'extra bed', '340.00'):
		assert text in printed


def test_smtp_sends_to_the_customer_without_login(smtp, monkeypatch):
	smtp_class, server = smtp
	monkeypatch.setenv('MAIL_MODE', 'smtp')
	monkeypatch.setenv('MAIL_HOST', 'mail.local')
	monkeypatch.setenv('MAIL_PORT', '1025')
	send()
	assert smtp_class.call_args.args == ('mail.local', 1025)
	server.login.assert_not_called()
	message = server.send_message.call_args.args[0]
	assert message['To'] == 'cl3a8@example.com'


def test_smtp_logs_in_when_mail_user_is_set(smtp, monkeypatch):
	_, server = smtp
	monkeypatch.setenv('MAIL_MODE', 'smtp')
	monkeypatch.setenv('MAIL_USER', 'hotel')
	monkeypatch.setenv('MAIL_PASSWORD', 's3cret-pass')
	send()
	server.login.assert_called_once_with('hotel', 's3cret-pass')
	server.send_message.assert_called_once()


def test_failure_is_logged_without_the_password(smtp, monkeypatch, caplog):
	_, server = smtp
	monkeypatch.setenv('MAIL_MODE', 'smtp')
	monkeypatch.setenv('MAIL_USER', 'hotel')
	monkeypatch.setenv('MAIL_PASSWORD', 's3cret-pass')
	server.login.side_effect = OSError('authentication failed')
	with caplog.at_level(logging.ERROR):
		send() #must not raise
	assert any(record.levelno == logging.ERROR for record in caplog.records)
	assert 's3cret-pass' not in caplog.text


def test_unknown_mode_is_logged(smtp, monkeypatch, caplog):
	smtp_class, _ = smtp
	monkeypatch.setenv('MAIL_MODE', 'carrier-pigeon')
	with caplog.at_level(logging.ERROR):
		send()
	smtp_class.assert_not_called()
	assert 'MAIL_MODE' in caplog.text


@pytest.fixture
def session_client(client):
	with client.session_transaction() as session:
		session['username'] = 'Cl3a8'
		session['role'] = 'customer'
	return client


def reserve(client):
	return client.post('/api/reservation/create', json={
		'checkIn': '2030-01-01', 'checkOut': '2030-01-03', 'card_token': 'tok_5eed00000001',
		'rooms': [{'location': 'Atlanta', 'room_number': 101, 'extra_bed_or_not': 0}]})


def test_reservation_created_sends_one_email(session_client, mysqldb, monkeypatch):
	sender = MagicMock()
	monkeypatch.setattr(api.correo, 'send_reservation_confirmation', sender)
	mysqldb.get_credit_card.return_value = {'token': 'tok_5eed00000001'}
	mysqldb.is_room_free.return_value = True
	mysqldb.get_room_prices.return_value = (150, 20)
	mysqldb.insert_reservation.return_value = (7, 'Successfully created reservation', True)
	assert reserve(session_client).status_code == 200
	sender.assert_called_once_with('Cl3a8', 7, '2030-01-01', '2030-01-03',
		[{'location': 'Atlanta', 'room_number': 101, 'extra_bed_or_not': 0}], 300)


@pytest.mark.parametrize('setup, status', [
	(lambda db: setattr(db.get_credit_card, 'return_value', None), 403),
	(lambda db: setattr(db.is_room_free, 'return_value', False), 409),
	(lambda db: setattr(db.insert_reservation, 'return_value', (-1, 'Error creating reservaiton', False)), 400),
], ids=['card_of_another_user', 'room_taken', 'insert_failed'])
def test_rejected_reservation_sends_no_email(session_client, mysqldb, monkeypatch, setup, status):
	sender = MagicMock()
	monkeypatch.setattr(api.correo, 'send_reservation_confirmation', sender)
	mysqldb.get_credit_card.return_value = {'token': 'tok_5eed00000001'}
	mysqldb.is_room_free.return_value = True
	mysqldb.get_room_prices.return_value = (150, 20)
	mysqldb.insert_reservation.return_value = (7, 'Successfully created reservation', True)
	setup(mysqldb)
	assert reserve(session_client).status_code == status
	sender.assert_not_called()
