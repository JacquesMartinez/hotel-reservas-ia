"""Loads development data into Fancy_Hotel.

Usage (from the repo root, with the venv active and .env configured):
	python fancyhotel/seed.py

WARNING: it empties every table before inserting. Only for local development.
"""
import random
from datetime import date, timedelta

from werkzeug.security import generate_password_hash

import db #creates the database and tables if they don't exist


LOCATIONS = ['Atlanta', 'Charlotte', 'Savannah', 'Orlando', 'Miami'] #same values as the front-end <select>

#room_number: (type, room_cost, capacity, extra_bed_price)
ROOMS = {
	101: ('Standard', 100, 2, 20),
	102: ('Standard', 100, 2, 20),
	103: ('Standard', 100, 2, 20),
	201: ('Family', 150, 4, 30),
	202: ('Family', 150, 4, 30),
	301: ('Suite', 250, 4, 50),
}

#username: (password, first_name, last_name, email) -- plain text here, stored as a hash
CUSTOMERS = {
	'Cl3a8': ('cliente123', 'Laura', 'Gomez', 'laura.gomez@example.com'),
	'Cyp7d': ('cliente123', 'Pedro', 'Ramirez', 'pedro.ramirez@example.com'),
	'C196b': ('cliente123', 'Sofia', 'Torres', 'sofia.torres@example.com'),
	'Cm2wd': ('cliente123', 'Diego', 'Morales', 'diego.morales@example.com'),
}

MANAGERS = {
	'M2acz': 'manager123',
}

#username: (card_number, name, cvv, expiration_date) -- standard test numbers, not real cards
CREDIT_CARDS = {
	'Cl3a8': ('4111111111111111', 'Laura Gomez', '123', date(2029, 12, 31)),
	'Cyp7d': ('5555555555554444', 'Pedro Ramirez', '456', date(2028, 6, 30)),
	'C196b': ('4012888888881881', 'Sofia Torres', '789', date(2030, 3, 31)),
	'Cm2wd': ('5105105105105100', 'Diego Morales', '321', date(2029, 9, 30)),
}

HISTORY_DAYS = 365
RANDOM_SEED = 2026 #fixed so every run produces the same data


def clear_tables(cursor):
	cursor.execute('SET FOREIGN_KEY_CHECKS = 0')
	for table in ['Reserves_Extra_Bed', 'Reservation', 'Review', 'Credit_Card', 'Room', 'Customer', 'Manager']:
		cursor.execute('TRUNCATE TABLE Fancy_Hotel.' + table)
	cursor.execute('SET FOREIGN_KEY_CHECKS = 1')


def build_reservations(rng, today):
	#walks each room through the last year leaving gaps between stays, so reservations never overlap
	reservations = []
	start = today - timedelta(days=HISTORY_DAYS)
	usernames = sorted(CUSTOMERS)
	for location in LOCATIONS:
		for room_number, (room_type, room_cost, capacity, extra_bed_price) in sorted(ROOMS.items()):
			checkin = start + timedelta(days=rng.randint(0, 10))
			while True:
				nights = rng.randint(1, 5)
				checkout = checkin + timedelta(days=nights)
				if checkout > today:
					break
				username = rng.choice(usernames)
				extra_bed = rng.random() < 0.3
				total_cost = (room_cost + (extra_bed_price if extra_bed else 0)) * nights
				reservations.append({
					'username': username,
					'checkin_date': checkin,
					'checkout_date': checkout,
					'card_number': CREDIT_CARDS[username][0],
					'total_cost': total_cost,
					'location': location,
					'room_number': room_number,
					'extra_bed_or_not': '1' if extra_bed else '0'
				})
				checkin = checkout + timedelta(days=rng.randint(1, 12))
	reservations.sort(key=lambda r: r['checkin_date'])
	return reservations


def seed():
	connection = db.mysqldb.connection
	cursor = connection.cursor()
	try:
		clear_tables(cursor)

		cursor.executemany(
			'''INSERT INTO Fancy_Hotel.Room (location, room_number, type, room_cost, capacity, extra_bed_price)
			VALUES (%s, %s, %s, %s, %s, %s)''',
			[(location, number) + room for location in LOCATIONS for number, room in sorted(ROOMS.items())]
		)

		cursor.executemany(
			'''INSERT INTO Fancy_Hotel.Customer (username, password, first_name, last_name, email)
			VALUES (%s, %s, %s, %s, %s)''',
			[(username, generate_password_hash(data[0])) + data[1:] for username, data in CUSTOMERS.items()]
		)

		cursor.executemany(
			'''INSERT INTO Fancy_Hotel.Manager (username, password) VALUES (%s, %s)''',
			[(username, generate_password_hash(password)) for username, password in MANAGERS.items()]
		)

		cursor.executemany(
			'''INSERT INTO Fancy_Hotel.Credit_Card (card_number, name, cvv, expiration_date, username)
			VALUES (%s, %s, %s, %s, %s)''',
			[card + (username,) for username, card in CREDIT_CARDS.items()]
		)

		reservations = build_reservations(random.Random(RANDOM_SEED), date.today())
		for reservation in reservations:
			cursor.execute(
				'''INSERT INTO Fancy_Hotel.Reservation (username, checkin_date, checkout_date, card_number, total_cost)
				VALUES (%(username)s, %(checkin_date)s, %(checkout_date)s, %(card_number)s, %(total_cost)s)''',
				reservation
			)
			reservation['reservation_id'] = cursor.lastrowid
			cursor.execute(
				'''INSERT INTO Fancy_Hotel.Reserves_Extra_Bed (location, room_number, reservation_id, extra_bed_or_not)
				VALUES (%(location)s, %(room_number)s, %(reservation_id)s, %(extra_bed_or_not)s)''',
				reservation
			)

		connection.commit()
	except Exception:
		connection.rollback()
		raise
	finally:
		cursor.close()

	print('Rooms:        %d in %d locations' % (len(LOCATIONS) * len(ROOMS), len(LOCATIONS)))
	print('Customers:    %s' % ', '.join(sorted(CUSTOMERS)))
	print('Managers:     %s' % ', '.join(sorted(MANAGERS)))
	print('Reservations: %d (%s to %s)' % (len(reservations), reservations[0]['checkin_date'], reservations[-1]['checkout_date']))


if __name__ == '__main__':
	seed()
