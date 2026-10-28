from functools import wraps
from flask import session
import re
from flask_restful import Resource, reqparse, abort, request, inputs
import db #instantiates the database so we don't have to do that in here
from datetime import datetime, date


def login_required(method):
	#401 without a session; protected methods take the username from the session, never from the request (S1)
	@wraps(method)
	def wrapper(*args, **kwargs):
		if "username" not in session:
			return {"error": "You must be logged in", "result": False}, 401
		return method(*args, **kwargs)
	return wrapper

def manager_required(method):
	#401 without a session, 403 for any role other than manager (S8)
	@wraps(method)
	def wrapper(*args, **kwargs):
		if "username" not in session:
			return {"error": "You must be logged in", "result": False}, 401
		if session.get("role") != "manager":
			return {"error": "Only managers can access this resource", "result": False}, 403
		return method(*args, **kwargs)
	return wrapper


def validate_stay(checkIn, checkOut):
	#returns (nights, None) or (None, error response) for malformed dates or less than one night
	try:
		checkInDate = datetime.strptime(checkIn, "%Y-%m-%d")
		checkOutDate = datetime.strptime(checkOut, "%Y-%m-%d")
	except ValueError:
		return None, ({"message": "Dates must use the format YYYY-MM-DD", "result": False}, 400)
	nights = (checkOutDate - checkInDate).days
	if nights < 1:
		return None, ({"message": "The check-out must be at least one night after the check-in", "result": False}, 400)
	return nights, None

def validate_card(card_number, cvv, expiration_date):
	#returns (last4, None) or (None, error response); the number and cvv are never stored or logged (D-02, D-08)
	if not re.fullmatch(r'\d{16}', card_number or ''):
		return None, ({"message": "The card number must have 16 digits", "result": False}, 400)
	if not re.fullmatch(r'\d{3}', cvv or ''):
		return None, ({"message": "The security code must have 3 digits", "result": False}, 400)
	try:
		expires = datetime.strptime(expiration_date, "%Y-%m-%d").date()
	except (TypeError, ValueError):
		return None, ({"message": "The expiration date must use the format YYYY-MM-DD", "result": False}, 400)
	if expires < date.today():
		return None, ({"message": "This card has expired", "result": False}, 400)
	return card_number[-4:], None

#every method of a class has to have (self)
class NewUserRegistrationResource(Resource):

	def __init__(self): #the constructor
		self.reqparse = reqparse.RequestParser()
		self.reqparse.add_argument('username', type=str, required= True, help="Username is required to register", location='json')
		self.reqparse.add_argument('email', type=str, required= True, help="Email is required to register", location='json')
		self.reqparse.add_argument('password', type=str, required= True, help="Password is required to register", location='json')
		self.reqparse.add_argument('firstName', type=str, required= True, help="First name is required to register", location='json')
		self.reqparse.add_argument('lastName', type=str, required= True, help="Last name is required to register", location='json')
		super(NewUserRegistrationResource, self).__init__() #for flask to finish creating this resource

	def post(self): 
		args = self.reqparse.parse_args()
		username = args['username']
		email = args['email']
		password = args['password']
		firstName = args['firstName']
		lastName = args['lastName']

		if not db.mysqldb.user_exists(username) and  not db.mysqldb.email_exists(email):
			db.mysqldb.register_user(username, email, password, firstName, lastName)
			return {"message": "User successfully created", "result": True}
		else:
			return {"error": "This user already exists", "result": False}, 400

class LoginResource(Resource):
	
	def __init__(self):
		self.reqparse = reqparse.RequestParser()
		self.reqparse.add_argument('username', type=str, required= True, help="Username is required to sign in", location='json')
		self.reqparse.add_argument('password', type=str, required= True, help="Email is required to sign in", location='json')
		super(LoginResource, self).__init__()

	def post(self): #post request, because we are posting information to the database
		args = self.reqparse.parse_args()
		username = args['username']
		password = args['password']

		role = db.mysqldb.login(username, password)
		if role:
			session.clear() #start a fresh session on every login
			session["username"] = username
			session["role"] = role
			return {"message": "You logged in!", "result": True, "role": role}
		else:
			return {"error": "Login information invalid. Check your username or password", "result": False}, 401

class MeResource(Resource):
	def get(self): #the user of the current session, so the front can restore it after a reload
		if "username" not in session:
			return {"error": "Not logged in", "result": False}, 401
		return {"username": session["username"], "role": session["role"]}

class LogoutResource(Resource):
	def post(self):
		session.clear()
		return {"message": "You logged out", "result": True}

class CreateReservationResource(Resource):
	method_decorators = [login_required]

	def __init__(self):
		self.reqparse = reqparse.RequestParser()
		self.reqparse.add_argument('checkIn', type=str, required=True, help="Please provide a checkIn")
		self.reqparse.add_argument('checkOut', type=str, required=True, help="Please provide a checkOut")
		self.reqparse.add_argument('card_token', type=str, location='json') #optional: without it, the user's default card is used
		self.reqparse.add_argument('rooms', type=list, required=True, help="Please provide a list of rooms")
		super(CreateReservationResource, self).__init__()

	def post(self):
		args = self.reqparse.parse_args()
		json_body = request.json

		#reject malformed requests before touching the database
		deltaDays, error = validate_stay(args["checkIn"], args["checkOut"])
		if error:
			return error
		required_keys = ('location', 'room_number', 'extra_bed_or_not')
		for room in json_body['rooms']:
			if not isinstance(room, dict) or any(room.get(key) in (None, '') for key in required_keys):
				return {"message": "Each room needs a location, room_number and extra_bed_or_not", "result": False}, 400

		#the card must belong to the session user (S4)
		if args['card_token']:
			card = db.mysqldb.get_credit_card(session['username'], args['card_token'])
			if not card:
				return {"message": "This credit card does not belong to you", "result": False}, 403
		else:
			card = next((c for c in db.mysqldb.get_credit_cards(session['username']) if c['is_default']), None)
			if not card:
				return {"message": "You have no default credit card. Please select or add one", "result": False}, 400

		#the rooms may have been booked since the search, so check again before inserting anything
		for room in json_body['rooms']:
			if not db.mysqldb.is_room_free(room['room_number'], room['location'], args['checkIn'], args['checkOut'], -1):
				return {"message": "Room %s in %s is no longer available for the selected dates" % (room['room_number'], room['location']), "result": False}, 409

		#prices come from the Room table; cost and extra_bed_price sent by the client are ignored (S3)
		total_cost = 0
		for room in json_body['rooms']:
			prices = db.mysqldb.get_room_prices(room['location'], room['room_number'])
			if not prices:
				return {"message": "Room %s in %s does not exist" % (room['room_number'], room['location']), "result": False}, 400
			room_cost, extra_bed_price = prices
			total_cost += room_cost
			if room['extra_bed_or_not'] == 1:
				total_cost += extra_bed_price or 0
		total_cost *= deltaDays
		id, message, result = db.mysqldb.insert_reservation(session['username'], args['checkIn'], args['checkOut'], card['token'], json_body['rooms'], total_cost)
		
		if not result:
			return {"id": id, "message": message, "result": result}, 400
			
		return {"id": id, "message": message, "result": result}
		
class UpdateReservationResource(Resource):
	method_decorators = [login_required]

	def __init__(self):
		self.reqparse = reqparse.RequestParser()
		self.reqparse.add_argument('reservation_id', type=str, required=True, help="Please provide a reservation_id")
		self.reqparse.add_argument('checkIn', type=str, required=True, help="Please provide a check-in date")
		self.reqparse.add_argument('checkOut', type=str, required=True, help="Please provide a check-out date")
		super(UpdateReservationResource, self).__init__()
	
	def put(self):
		args = self.reqparse.parse_args()
		deltaDays, error = validate_stay(args["checkIn"], args["checkOut"])
		if error:
			return error

		total_cost = 0
		print(deltaDays)
		rooms = db.mysqldb.get_rooms_for_reservation(session['username'], args['reservation_id'])
		for room in rooms:
			if not db.mysqldb.is_room_free(room['room_number'], room['location'], args['checkIn'], args['checkOut'], args['reservation_id']):
				return {"message": "Some rooms in your reservation are not free during the specified times", "result": False}, 400
				
			total_cost += room['cost']
			if room['extra_bed_or_not'] == '1':
				total_cost += room['extra_bed_price']
		#For the rooms in the reservation, check if each room is free during the requested times. If the room is not free, return false.
		print(total_cost)
		total_cost *= deltaDays
		message, status = db.mysqldb.update_reservation(session['username'], args['reservation_id'], args['checkIn'], args['checkOut'], total_cost)
		if status:
			return {"message": message, "result": status}
		else:
			return {"message": message, "result": status}, 400

class ReservationResource(Resource):
	method_decorators = [login_required]

	def __init__(self):
		self.reqparse = reqparse.RequestParser()
		self.reqparse.add_argument('checkIn', type=str, required=True, help="Please provide a check-in date")
		self.reqparse.add_argument('checkOut', type=str, required=True, help="Please provide a check-out date")

		super(ReservationResource, self).__init__()

	def get(self, reservation_id):
		reservation = db.mysqldb.get_reservation(session['username'], reservation_id, False)
		if reservation:
			return {"data": reservation, "result": True}
		else:
			return {"error": "No reservation found", "result": False}, 404

	def put(self, reservation_id): #update the reservation
		args = self.reqparse.parse_args()
		 
		total_cost = 0
		rooms = db.mysqldb.get_rooms_for_reservation(session['username'], reservation_id)
		for room in rooms:
			if not db.mysqldb.is_room_free(room['room_number'], room['location'], args['checkIn'], args['checkOut'], reservation_id):
				return {"message": "Some rooms in your reservation are not free during the specified times", "result": False}, 400
				
			total_cost += room['cost'] * deltaDays
			if room['extra_bed_or_not'] == 1:
				total_cost + room['extra_bed_price'] * deltaDays
		#For the rooms in the reservation, check if each room is free during the requested times. If the room is not free, return false.

		message, status = db.mysqldb.update_reservation(reservation_id, args['checkIn'], args['checkOut'], total_cost)
		if status:
			return {"message": message, "result": status}
		else:
			return {"message": message, "result": status}, 400

class UpdateReservationConfirmResource(Resource):
	method_decorators = [login_required]

	def __init__(self):
		self.reqparse = reqparse.RequestParser()
		self.reqparse.add_argument('checkIn', type=str, required=True, help="Please provide a check-in date", location='args')
		self.reqparse.add_argument('checkOut', type=str, required=True, help="Please provide a check-out date", location='args')
		super(UpdateReservationConfirmResource, self).__init__()

	def get(self, reservation_id):
		args  = self.reqparse.parse_args()
		nights, error = validate_stay(args['checkIn'], args['checkOut'])
		if error:
			return error
		rooms = db.mysqldb.get_rooms_for_reservation(session['username'], reservation_id)
		for room in rooms:
			if not db.mysqldb.is_room_free(room['room_number'], room['location'], args['checkIn'], args['checkOut'], reservation_id):
				return {"message": "Some rooms in your reservation are not free during the specified times", "result": False}, 400
		return {"message": "Rooms are available", "result": True, "rooms": rooms}



class CancelReservationResource(Resource):
	method_decorators = [login_required]

	def get(self, reservation_id):
		message, status = db.mysqldb.cancel_reservation(session['username'], reservation_id)
		if status:
			return {"message": "Cancelled reservation", "result": True}
		else:
			return {"message": message, "result": False}, 400

class SearchRoomsResource(Resource):
	def __init__(self):
		self.reqparse = reqparse.RequestParser()
		self.reqparse.add_argument('location', type=str, required= True, help="Please select a location", location='args')
		self.reqparse.add_argument('checkIn', type=str, required= True, help="Please select a check-in date", location='args')
		self.reqparse.add_argument('checkOut', type=str, required= True, help="Please select a check-out date", location='args')
		super(SearchRoomsResource, self).__init__()

	def get(self): #get request, because we are pulling info from the database
		args = self.reqparse.parse_args()
		location = args['location']
		checkIn = args['checkIn']
		checkOut = args['checkOut']
		print(location)
		return db.mysqldb.search_rooms(location, checkIn, checkOut)

class AvailabilityResource(Resource):
	def __init__(self):
		self.reqparse = reqparse.RequestParser()
		self.reqparse.add_argument('location', type=str, required= True, help="Please select a location", location='args')
		self.reqparse.add_argument('type', type=str, required= True, help="Please select a room type", location='args')
		self.reqparse.add_argument('from', type=str, required= True, help="Please provide a start date", location='args')
		self.reqparse.add_argument('to', type=str, required= True, help="Please provide an end date", location='args')
		super(AvailabilityResource, self).__init__()

	def get(self): #returns the nights (from and to included) with no free room of the type
		args = self.reqparse.parse_args()
		try:
			fromDate = datetime.strptime(args['from'], "%Y-%m-%d").date()
			toDate = datetime.strptime(args['to'], "%Y-%m-%d").date()
		except ValueError:
			return {"message": "Dates must use the format YYYY-MM-DD", "result": False}, 400
		if fromDate > toDate:
			return {"message": "The start date must not be after the end date", "result": False}, 400
		return {"occupied": db.mysqldb.get_occupied_nights(args['location'], args['type'], fromDate, toDate)}

class CreditCardResource(Resource):
	method_decorators = [login_required]

	def __init__(self):
		self.delete_reqparse = reqparse.RequestParser()
		self.delete_reqparse.add_argument("token", type=str, required=True, help="Please provide a card token", location='args')
		
		self.create_reqparse = reqparse.RequestParser()
		self.create_reqparse.add_argument("card_number", type=str, required=True, location='json', help="Please provide a card_number")
		self.create_reqparse.add_argument("name", type=str, required=True, location='json', help="Please provide a name")
		self.create_reqparse.add_argument("cvv", type=str, required=True, location='json', help="Please provide a security code")
		self.create_reqparse.add_argument("expiration_date", type=str, required=True, location='json', help="Please provide a expiration_date")
		self.create_reqparse.add_argument("make_default", type=inputs.boolean, default=False, location='json')
		
		super(CreditCardResource, self).__init__()
		
	def get(self):
		return db.mysqldb.get_credit_cards(session['username'])

	def post(self):
		args = self.create_reqparse.parse_args()
		last4, error = validate_card(args['card_number'], args['cvv'], args['expiration_date'])
		if error:
			return error
		card = db.mysqldb.add_credit_card(session['username'], last4, args['name'], args['expiration_date'], args['make_default'])
		return {'message': "Credit card successfully created", 'result': True, 'card': card}
		
	def delete(self):
		args = self.delete_reqparse.parse_args()
		if not db.mysqldb.get_credit_card(session['username'], args['token']):
			return {'message': "This credit card was not found", 'result': False}, 404
		reservations = db.mysqldb.get_reservation_by_card_number(session['username'], args['token'])

		today = datetime.now()
		for reservation in reservations:
			if (datetime.strptime(reservation['checkout_date'], '%Y-%m-%d') - today).days > 0:
				return {'message': "This card is used in a future reservation!", 'result': False}, 400

		message, status = db.mysqldb.delete_credit_card(session['username'], args['token'])

		if status:
			return {'message': message, 'result': status}
		return {'message': message, 'result': status}, 400

class CreditCardDefaultResource(Resource):
	method_decorators = [login_required]

	def __init__(self):
		self.reqparse = reqparse.RequestParser()
		self.reqparse.add_argument("token", type=str, required=True, location='json', help="Please provide a card token")
		super(CreditCardDefaultResource, self).__init__()

	def post(self): #leaves this card as the only default one of the user
		args = self.reqparse.parse_args()
		if not db.mysqldb.set_default_credit_card(session['username'], args['token']):
			return {'message': "This credit card was not found", 'result': False}, 404
		return {'message': "Default credit card updated", 'result': True}

class ReviewResource(Resource):
	method_decorators = {'post': [login_required]} #reading reviews stays public

	def __init__(self):
		self.reqparse = reqparse.RequestParser()
		self.reqparse.add_argument("location", type=str, required=True, help="Please provide a location", location='args')
		
		self.create_reqparse = reqparse.RequestParser()
		self.create_reqparse.add_argument("comment", type=str, required=True, location='json', help="Please provide a card_number")
		self.create_reqparse.add_argument("rating", type=str, required=True, location='json', help="Please provide a name")
		self.create_reqparse.add_argument("location", type=str, required=True, location='json', help="Please provide a ccv")
		
	def get(self):
		args = self.reqparse.parse_args()
		return db.mysqldb.get_reviews(args['location'])
	
	def post(self):
		args = self.create_reqparse.parse_args()
		message, status = db.mysqldb.add_review(session['username'], args['location'], args['comment'], args['rating'])
		if status:
			return {'message': message, 'result': status}
		return {'message': message, 'result': status}, 400
		
class ReservationReportResource(Resource):
	method_decorators = [manager_required]

	def get(self):
		return db.mysqldb.reservation_report()

class PopularRoomReportResource(Resource):
	method_decorators = [manager_required]

	def get(self):
		return db.mysqldb.room_report()

class RevenueReportResource(Resource):
	method_decorators = [manager_required]

	def get(self):
		return db.mysqldb.revenue_report()

class GetReservationByCardNumberResource(Resource):
	method_decorators = [login_required]

	def __init__(self):
		self.reqparse = reqparse.RequestParser()
		self.reqparse.add_argument("card_number", type=str, required=True, help="Please provide a card number", location='args')

	def get(self):
		args = self.reqparse.parse_args()
		return db.mysqldb.get_reservation_by_card_number(session['username'], args['card_number']) #returns an array of reservations



