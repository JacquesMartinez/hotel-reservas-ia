import os
from dotenv import load_dotenv
from flask import Flask, render_template
from flask_restful import Api
import api as restapi


load_dotenv() #SECRET_KEY comes from .env, like the DB_* variables

app = Flask(__name__)
app.debug = True
app.secret_key = os.environ.get('SECRET_KEY')
if not app.secret_key:
	raise RuntimeError("SECRET_KEY no está definida en .env") #never fall back to a fixed key
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax")
api = Api(app)


@app.teardown_appcontext
def close_db_connection(exception):
	restapi.db.mysqldb.close_connection() #each request thread opens its own connection; close it when done


@app.route('/')
def index():
	return render_template("index.html")

api.add_resource(restapi.LoginResource, '/api/login')
api.add_resource(restapi.MeResource, '/api/me')
api.add_resource(restapi.LogoutResource, '/api/logout')
api.add_resource(restapi.NewUserRegistrationResource, '/api/register')
api.add_resource(restapi.SearchRoomsResource, '/api/searchRoom')
api.add_resource(restapi.AvailabilityResource, '/api/availability')
api.add_resource(restapi.MyReservationsResource, '/api/reservations')
api.add_resource(restapi.CreateReservationResource, '/api/reservation/create')
api.add_resource(restapi.UpdateReservationResource, '/api/reservation')
api.add_resource(restapi.ReservationResource, '/api/reservation/<string:reservation_id>') #includes update_reservation
api.add_resource(restapi.UpdateReservationConfirmResource, '/api/reservation/<string:reservation_id>/availability')
api.add_resource(restapi.CreditCardResource, '/api/payment')
api.add_resource(restapi.CreditCardDefaultResource, '/api/payment/default')
api.add_resource(restapi.ReviewResource, '/api/review')
api.add_resource(restapi.CancelReservationResource, '/api/reservation/<string:reservation_id>/cancel')
api.add_resource(restapi.ReservationReportResource, '/api/reports/reservation')
api.add_resource(restapi.PopularRoomReportResource, '/api/reports/popularRoom')
api.add_resource(restapi.RevenueReportResource, '/api/reports/revenue')
api.add_resource(restapi.ForecastReportResource, '/api/reports/forecast')
api.add_resource(restapi.GetReservationByCardNumberResource, '/api/reservation/cardNumber')


if __name__ == '__main__':
	app.run('0.0.0.0', int(os.environ.get('PORT', '5000')), debug=True) #PORT from .env (5000 is taken by AirPlay on macOS)


