import os
import mysql.connector
from datetime import datetime, timedelta

class MysqlManager(object):

	def __init__(self):
		self.connection = self.connect('sys')
		self.init_db()

	def connect(self, database):
		#credentials come from the environment (.env), never from the code
		return mysql.connector.connect(
			user=os.environ['DB_USER'],
			password=os.environ['DB_PASSWORD'],
			host=os.environ.get('DB_HOST', '127.0.0.1'),
			port=int(os.environ.get('DB_PORT', '3306')),
			database=database
		)


	def init_db(self):
		cursor = self.connection.cursor()
		try:
			#first need to create a db and populate it with tables
			#this way, it can be run on any machine for local development


			cursor.execute(
				'''CREATE DATABASE IF NOT EXISTS Fancy_Hotel;'''
			)
			
			cursor.execute(
				'''CREATE TABLE IF NOT EXISTS Fancy_Hotel.Customer (
  					username CHAR(5) NOT NULL,
  					password VARCHAR(16) NOT NULL,
  					first_name VARCHAR(20) NOT NULL,
  					last_name VARCHAR(20) NOT NULL,
  					email VARCHAR(30) NOT NULL,
  					PRIMARY KEY (username),
  					UNIQUE(email)
  				);'''
			)

			cursor.execute(
				'''CREATE TABLE IF NOT EXISTS Fancy_Hotel.Manager (
  					username char(5) NOT NULL,
  					password varchar(16) NOT NULL,
 					PRIMARY KEY (username)
 				);'''
			)

			cursor.execute(
				'''CREATE TABLE IF NOT EXISTS Fancy_Hotel.Credit_Card (
				 	card_number char(16) NOT NULL,
				 	name varchar(41) NOT NULL,
				 	cvv char(3) NOT NULL,
				 	expiration_date date NOT NULL,
				 	username char(5) NOT NULL,
				 	PRIMARY KEY (card_number),
				 	FOREIGN KEY (username) REFERENCES Fancy_Hotel.Customer (username)
				);'''
			)

			cursor.execute(
				'''CREATE TABLE IF NOT EXISTS Fancy_Hotel.Review (
				 	review_id INT NOT NULL AUTO_INCREMENT,
				 	location varchar(9) NOT NULL,
				 	comment varchar(1000) DEFAULT NULL,
				 	rating varchar(10) NOT NULL,
				 	username char(5) NOT NULL,
				 	PRIMARY KEY (review_id),
				 	FOREIGN KEY (username) REFERENCES Fancy_Hotel.Customer (username)
				);'''
			)


			cursor.execute(
				'''CREATE TABLE IF NOT EXISTS Fancy_Hotel.Reservation (
				 	reservation_id INT NOT NULL AUTO_INCREMENT,
				 	checkin_date date NOT NULL,
				 	checkout_date date NOT NULL,
				 	total_cost float NOT NULL DEFAULT 0,
			 		username char(5) NOT NULL,
				 	card_number char(16) DEFAULT NULL,
				 	cancelled_or_not char(1) NOT NULL DEFAULT '0',
				 	#cancelled_date date DEFAULT NULL,
				 	PRIMARY KEY (reservation_id),
				 	FOREIGN KEY (username) REFERENCES Fancy_Hotel.Customer (username),
				 	FOREIGN KEY (card_number) REFERENCES Fancy_Hotel.Credit_Card (card_number) ON DELETE SET NULL
				);'''
			)
			

			cursor.execute(
				'''CREATE TABLE IF NOT EXISTS Fancy_Hotel.Room (
				 	location varchar(9) NOT NULL,
				 	room_number int(11) NOT NULL,
				 	type varchar(20) NOT NULL,
				 	room_cost float NOT NULL,
				 	capacity int(11) NOT NULL,
				 	extra_bed_price float DEFAULT NULL,
				 	PRIMARY KEY (location, room_number)
				);'''
			)


			cursor.execute(
				'''CREATE TABLE IF NOT EXISTS Fancy_Hotel.Reserves_Extra_Bed (
					location varchar(9) NOT NULL,
					room_number int(11) NOT NULL,
					reservation_id INT NOT NULL,
					extra_bed_or_not char(1) DEFAULT NULL,
					PRIMARY KEY (location, room_number, reservation_id),
					FOREIGN KEY (location, room_number) REFERENCES Fancy_Hotel.Room (location, room_number),
					FOREIGN KEY (reservation_id) REFERENCES Fancy_Hotel.Reservation (reservation_id)
				);'''
			)		
			#fill db with existing data here: managers, locations, etc


			
		finally:
			cursor.close()
			self.connection.close() #closing the initial sys connection and reconnecting to our new db
			self.connection = self.connect('Fancy_Hotel')



	def user_exists(self, username):
		cursor = self.connection.cursor()
		try:
			cursor.execute(
				'''SELECT username 
					FROM Fancy_Hotel.Customer 
					WHERE username = %(username)s''',
					{'username': username}
			)
			rows = cursor.fetchall() #grabs the rows of our result

			#if user doesn't already exist, there will be no rows, so if rows is 0, then no user exists, and we can create the user
			return len(rows)!=0
		finally:
			cursor.close()


	def email_exists(self, email):
		cursor = self.connection.cursor()
		try:
			cursor.execute(
				'''SELECT email 
					FROM Fancy_Hotel.Customer 
					WHERE email = %(email)s''',
					{'email': email}
			)

			rows = cursor.fetchall()

			return len(rows)!=0
		finally:
			cursor.close()


	def register_user(self, username, email, password, firstName, lastName):
		cursor = self.connection.cursor()
		try:
			cursor.execute(
				'''INSERT INTO Fancy_Hotel.Customer (username, email, password, first_name, last_name)
				VALUES (%(username)s, %(email)s, %(password)s, %(first_name)s, %(last_name)s)''',
				{'username': username, 'email': email, 'password': password, 'first_name': firstName, 'last_name': lastName}
			)
			if cursor.rowcount != 1:
				pass
			else:
				self.connection.commit() #required to write into the database
		finally:
			cursor.close()

	def login(self, username, password):
		cursor = self.connection.cursor()
		try:

			userType = username[0];

			
			if userType == 'C':
				cursor.execute(
					'''SELECT *
					FROM Customer
					WHERE username = %(username)s AND password = %(password)s''',
					{'username': username, 'password':password}
				)
				rows = cursor.fetchall()
				return len(rows)!=0

			elif userType == 'M':
				cursor.execute(
					'''SELECT *
					FROM Manager
					WHERE username = %(username)s AND password = %(password)s''',
					{'username': username, 'password':password}
				)
				rows = cursor.fetchall()
				return len(rows)!=0

			else:
				print("you shouldn't be here. Names should only start with C or M.")
				return False
		finally:
			cursor.close()

	def search_rooms(self, location, checkinDate, checkoutDate):
		cursor = self.connection.cursor()
		try:
			cursor.execute(
				'''SELECT * 
				FROM Fancy_Hotel.Room 
				WHERE (location, room_number) NOT IN (
					SELECT r.location, r.room_number 
					FROM Fancy_Hotel.Room AS r
					JOIN (Fancy_Hotel.Reserves_Extra_Bed AS bed, Fancy_Hotel.Reservation AS res)
					ON bed.location = r.location AND bed.room_number = r.room_number AND res.reservation_id = bed.reservation_id
					WHERE res.checkin_date < %(checkoutDate)s AND res.checkout_date > %(checkinDate)s AND res.cancelled_or_not = 0
				) AND location = %(location)s''',
				{'location': location, 'checkinDate': checkinDate, 'checkoutDate':checkoutDate}
			)

			rows = cursor.fetchall()
			print(len(rows))
			rooms = []
			for (location, room_number, room_type, cost, capacity, extra_bed_price) in rows:
				rooms.append(
					{
						"location" : location, 
						"room_number": room_number, 
						"room_type": room_type, 
						"cost": cost, 
						"capacity": capacity, 
						"extra_bed_price": extra_bed_price
					}
				)
			if(len(rooms)>0):
				return {"response": rooms, "result": True}
			else:
				return {"response": rooms, "result": False}
			
			

			#>= DATE('2015-11-24') (the mock checkin date)
			#DATE('2015-11-29') (the mock checkout date)
		finally:
			cursor.close()

	def get_rooms_for_reservation(self, username, reservation_id):
		cursor = self.connection.cursor()
		try:
			cursor.execute(
				'''SELECT room.location, room.room_number, room.type, room.room_cost, room.capacity, room.extra_bed_price, bed.extra_bed_or_not FROM Fancy_Hotel.Room as room
				JOIN (Fancy_Hotel.Reserves_Extra_Bed AS bed, Fancy_Hotel.Reservation AS res)
				ON room.location = bed.location AND room.room_number = bed.room_number AND res.reservation_id = bed.reservation_id
				WHERE res.reservation_id = %(reservation_id)s AND res.username = %(username)s
				''',
				{'reservation_id': reservation_id, 'username': username}
			)
			rows = cursor.fetchall()
			rooms = []
			for location, room_number, room_type, room_cost, capacity, extra_bed_price, extra_bed_or_not in rows:
				rooms.append({
					"location" : location, 
					"room_number": room_number, 
					"room_type": room_type, 
					"cost": room_cost, 
					"capacity": capacity, 
					"extra_bed_price": extra_bed_price, 
					"extra_bed_or_not": extra_bed_or_not
				})
			return rooms
		finally:
			cursor.close()

	def get_reservation(self, username, reservation_id, include_cancelled):
		cursor = self.connection.cursor()
		try:
			if include_cancelled:
				cursor.execute(
					'''SELECT *
					FROM Fancy_Hotel.Reservation
					WHERE reservation_id = %(reservation_id)s AND username = %(username)s
					''',
					{'reservation_id': reservation_id, "username": username}
				)
			else:
				cursor.execute(
					'''SELECT *
					FROM Fancy_Hotel.Reservation
					WHERE reservation_id = %(reservation_id)s AND username = %(username)s AND cancelled_or_not = 0
					''',
					{'reservation_id': reservation_id, "username": username}
				)

			rows = cursor.fetchall()
			if len(rows) > 0:
				id, checkin_date, checkout_date, total_cost, username, card_number, cancelled_or_not= rows[0] #,cancelled_date
				rooms = self.get_rooms_for_reservation(username, id)
				return {
					"reservation_id": id,
					"checkin_date": str(checkin_date),
					"checkout_date": str(checkout_date),
					"total_cost": total_cost,
					"username": username,
					"card_number": card_number,
					"cancelled_or_not": cancelled_or_not,
					"rooms": rooms
				}
			else:
				return {}
		finally:
			cursor.close()
	
	def insert_reservation(self, username, checkin_date, checkout_date, card_number, rooms, total_cost):
		cursor = self.connection.cursor()
		try:
			cursor.execute(
				'''
				INSERT INTO Fancy_Hotel.Reservation 
				(username, checkin_date, checkout_date, card_number, total_cost)
				VALUES(%(username)s, %(checkin_date)s, %(checkout_date)s, %(card_number)s, %(total_cost)s)
				''',
				{"username": username, "checkin_date": checkin_date, "checkout_date": checkout_date, "card_number": card_number, "total_cost": total_cost}
			)
			
			reservation_id = cursor.lastrowid
			
			for room in rooms:
				cursor.execute(
					'''
					INSERT INTO Fancy_Hotel.Reserves_Extra_Bed
					(location, room_number, reservation_id, extra_bed_or_not )
					VALUES(%(location)s, %(room_number)s, %(reservation_id)s, %(extra_bed_or_not)s)
					''',
					{"location": room['location'], "room_number": room['room_number'], "reservation_id": reservation_id, "extra_bed_or_not": room['extra_bed_or_not']}
				)
				if cursor.rowcount == 0:
					return -1, "Error creating reservaiton", False
				
			self.connection.commit()
			return reservation_id, "Successfully created reservation", True
		finally:
			cursor.close()

	def update_reservation(self, username, reservation_id, checkin_date, checkout_date, total_cost):
		cursor = self.connection.cursor()
		try:
			reservation = self.get_reservation(username, reservation_id, False)
			if reservation:
				cursor.execute(
					'''UPDATE Fancy_Hotel.Reservation
					SET checkin_date = %(checkin_date)s, checkout_date = %(checkout_date)s, total_cost = %(total_cost)s
					WHERE reservation_id = %(reservation_id)s AND username = %(username)s
					''',
					{"reservation_id": reservation_id, "checkin_date":checkin_date, "checkout_date": checkout_date, "username": username, "total_cost": total_cost}
				)
				self.connection.commit()
				return "Reservation updated", True
			else:
				return "This reservation does not exist", False
		finally:
			cursor.close()

	def cancel_reservation(self, username, reservation_id):
		cursor = self.connection.cursor()
		try:
			reservation = self.get_reservation(username, reservation_id, False)
			if reservation:
				total_cost = 0
				checkin_date = datetime.strptime(reservation['checkin_date'], "%Y-%m-%d");
				deltaDays = (checkin_date - datetime.now()).days
				if deltaDays <= 1:
					total_cost = reservation['total_cost']
				elif deltaDays < 4:
					total_cost = reservation['total_cost'] * 0.20
				else:
					total_cost = 0

				cursor.execute(
					'''UPDATE Fancy_Hotel.Reservation
					SET cancelled_or_not = 1, total_cost = %(total_cost)s
					WHERE reservation_id = %(reservation_id)s AND username = %(username)s
						AND cancelled_or_not = 0
					''',
					{'reservation_id': reservation_id, "username": username, "total_cost": total_cost}
				)
				self.connection.commit()

				if cursor.rowcount > 0:
					return "", True
				else:
					return "This reservation has already been cancelled", False
			else:
				return "This reservation does not exist", False
		finally:
			cursor.close()

	def is_room_free(self, room_number, location, checkin_date, checkout_date, exclude_reservation):
		cursor = self.connection.cursor()
		try:
			cursor.execute(
				'''SELECT r.location, r.room_number 
				FROM Fancy_Hotel.Room AS r
				JOIN (Fancy_Hotel.Reserves_Extra_Bed AS bed, Fancy_Hotel.Reservation AS res)
				ON bed.location = r.location 
					AND bed.room_number = r.room_number 
					AND res.reservation_id = bed.reservation_id
				WHERE r.room_number = %(room_number)s 
					AND r.location = %(location)s 
					AND res.checkin_date < %(checkoutDate)s
					AND res.checkout_date > %(checkinDate)s
					AND res.cancelled_or_not = 0 
					AND res.reservation_id != %(exclude_reservation)s 
				''',
				{'room_number': room_number, 'location': location, 'checkinDate': checkin_date, 'checkoutDate': checkout_date, 'exclude_reservation': exclude_reservation}
			)
			rows = cursor.fetchall()
			return len(rows) == 0 #if the room does not occur in our query, then there will be returned an empty table, true
		finally:
			cursor.close()

	def get_occupied_nights(self, location, room_type, from_date, to_date):
		cursor = self.connection.cursor()
		try:
			cursor.execute(
				'''SELECT COUNT(*)
				FROM Fancy_Hotel.Room
				WHERE location = %(location)s AND type = %(type)s
				''',
				{'location': location, 'type': room_type}
			)
			total_rooms = cursor.fetchall()[0][0] #with no room of the type, every night is occupied (D-06)

			#all the reservations of the period in one query; a reservation occupies the nights checkin <= night < checkout
			cursor.execute(
				'''SELECT r.room_number, res.checkin_date, res.checkout_date
				FROM Fancy_Hotel.Room AS r
				JOIN (Fancy_Hotel.Reserves_Extra_Bed AS bed, Fancy_Hotel.Reservation AS res)
				ON bed.location = r.location
					AND bed.room_number = r.room_number
					AND res.reservation_id = bed.reservation_id
				WHERE r.location = %(location)s
					AND r.type = %(type)s
					AND res.checkin_date <= %(toDate)s
					AND res.checkout_date > %(fromDate)s
					AND res.cancelled_or_not = 0
				''',
				{'location': location, 'type': room_type, 'fromDate': from_date, 'toDate': to_date}
			)
			rows = cursor.fetchall()

			#a night is occupied when no room of the type is left free (D-06)
			occupied = []
			night = from_date
			while night <= to_date:
				taken = set(room_number for room_number, checkin, checkout in rows if checkin <= night < checkout)
				if len(taken) >= total_rooms:
					occupied.append(night.isoformat())
				night += timedelta(days=1)
			return occupied
		finally:
			cursor.close()
	
	def add_credit_card(self, username, card_number, cvv, expiration_date, card_name):
		cursor = self.connection.cursor()
		try:
			cursor.execute(
				'''
				INSERT INTO Fancy_Hotel.Credit_Card
				(card_number, name, cvv, expiration_date, username)
				VALUES (%(card_number)s, %(name)s, %(cvv)s, %(expiration_date)s, %(username)s)  
				''',
				{"card_number": card_number, "name": card_name, "cvv": cvv, "expiration_date": expiration_date, "username": username}
			)
			
			
			if cursor.rowcount == 0:
				return "Credit card creation failed", False
			
			self.connection.commit()	
			return "Credit card successfully created", True
			
		finally:
			cursor.close()
			
	def get_credit_cards(self, username):
		cursor = self.connection.cursor()
		try:
			cursor.execute(
				'''
				SELECT * From Fancy_Hotel.Credit_Card
				WHERE username = %(username)s
				''',
				{'username': username}
			)
			rows = cursor.fetchall()
			cards = []
			for card_number, name, cvv, expiration_date, username in rows:
				cards.append(
					{
						"card_number": card_number,
						"name": name,
						"cvv": cvv, 
						"expiration_date": str(expiration_date),
						"username": username
					}
				)
			
			return cards
		finally:
			cursor.close()
	
	def delete_credit_card(self, username, card_number):
		cursor = self.connection.cursor()
		try:
			cursor.execute(
				'''
				DELETE FROM Fancy_Hotel.Credit_Card
				WHERE card_number = %(card_number)s AND username = %(username)s  
				''',
				{"card_number": card_number, "username": username}
			)
			if cursor.rowcount == 0:
				return "This credit card was not found", False
			self.connection.commit()
			return "Credit card deleted", True
		finally:
			cursor.close()
	
	def get_reservation_by_card_number(self, username, card_number):
		cursor = self.connection.cursor()
		try:
			cursor.execute('''
				SELECT *
				FROM Fancy_Hotel.Reservation
				WHERE card_number = %(card_number)s AND username = %(username)s;
				''',
				{"card_number": card_number, "username": username}
			)
			rows = cursor.fetchall()
			reservations = []
			for reservation_id, checkin_date, checkout_date, total_cost, username, card_number, cancelled_or_not in rows:
				reservations.append({
					"reservation_id": reservation_id,
					"checkin_date": str(checkin_date), 
					"checkout_date": str(checkout_date), 
					"total_cost": total_cost, 
					"username": username, 
					"card_number": card_number, 
					"cancelled_or_not": cancelled_or_not
					})
			return reservations
		finally:
			cursor.close()


	def add_review(self, username, location, comment, rating):
		cursor = self.connection.cursor()
		try:
			cursor.execute(
				'''
				INSERT INTO Fancy_Hotel.Review
				(location, comment, rating, username)
				VALUES (%(location)s, %(comment)s, %(rating)s, %(username)s)  
				''',
				{"location": location, "comment": comment, "rating": rating, "username": username}
			)
			if cursor.rowcount == 0:
				return "Could not create review", False
			self.connection.commit()
			return "Review created", True
		finally:
			cursor.close()
			
	def get_reviews(self, location):
		cursor = self.connection.cursor()
		try:
			cursor.execute(
				'''
				SELECT * From Fancy_Hotel.Review
				WHERE location = %(location)s
				''',
				{'location': location}
			)
			rows = cursor.fetchall()
			reviews = []
			for id, location, comment, rating, username in rows:
				reviews.append(
					{
						"review_id": id, 
						"location": location, 
						"comment": comment, 
						"rating": rating,
						"username": username
					}
				)
				
			return reviews
		finally:
			cursor.close()

	def reservation_report(self):
		cursor = self.connection.cursor()
		try:	
			cursor.execute(
				'''SELECT MONTH(checkin_date), bed.location, count(*) 
				FROM Fancy_Hotel.Reservation AS res
				JOIN (Fancy_Hotel.Reserves_Extra_Bed AS bed)
				ON res.reservation_id = bed.reservation_id
				WHERE Month(res.checkin_date) = 8 or Month(res.checkin_date) = 9
				GROUP BY MONTH(checkin_date), bed.location
				'''
			)
			rows = cursor.fetchall()
			report = {}
			for month, location, count in rows:
				if month not in report:
					report[month] = {}
				report[month][location] = count

			return report

		finally:
			cursor.close()

	def room_report(self):
		cursor = self.connection.cursor()
		try:
			cursor.execute(
				'''CREATE OR REPLACE VIEW reservation_by_category 
				AS(SELECT Month(res.checkin_date) as mth, room.type as type, room.location as location, count(room.type) as cnt
					FROM Fancy_Hotel.Room as room
					JOIN (Fancy_Hotel.Reserves_Extra_Bed as bed, Fancy_Hotel.Reservation as res)
					ON room.location = bed.location AND room.room_number = bed.room_number AND res.reservation_id = bed.reservation_id
					WHERE Month(res.checkin_date) = 8 
					GROUP BY Month(res.checkin_date), room.location, room.type);
				'''
			)
			#or Month(res.checkin_date) = 9
			self.connection.commit()

			cursor.execute(
				'''SELECT rbc.mth, rbc.location, rbc.type, rbc.cnt 
				FROM reservation_by_category as rbc
				INNER JOIN
				    (SELECT mth, location, MAX(cnt) AS cnt
				    FROM reservation_by_category
				    GROUP BY mth, location) as groupedrbc 
				ON rbc.mth = groupedrbc.mth AND rbc.location = groupedrbc.location AND rbc.cnt = groupedrbc.cnt;
				'''
			)
			rows = cursor.fetchall()
			report = {}
			for month, location, room_type, count in rows:
				if month not in report:
					report[month] = {}
				if location not in report[month]:
					report[month][location] = []

				report[month][location].append({"type": room_type, "count": count})

			return report

		finally:
			cursor.close()

	def revenue_report(self):
		cursor = self.connection.cursor()
		try:
			cursor.execute(
				'''SELECT Month(res.checkin_date) as month, 
				room.location as location, 
				SUM(res.total_cost)
				FROM Fancy_Hotel.Room as room
				JOIN (Fancy_Hotel.Reserves_Extra_Bed as bed, Fancy_Hotel.Reservation as res)
				ON room.location = bed.location AND room.room_number = bed.room_number AND res.reservation_id = bed.reservation_id
				WHERE Month(res.checkin_date) = 8 or Month(res.checkin_date) = 9
				GROUP BY Month(res.checkin_date), room.location;
				'''
			)
			rows = cursor.fetchall()
			report = {}
			for month, location, cost in rows:
				if month not in report:
					report[month] = {}
				report[month][location] = cost

			return report
		finally:
			cursor.close()

	
