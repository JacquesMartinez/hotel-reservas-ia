import logging
import os
import smtplib #used as smtplib.SMTP so the tests can replace it
from email.message import EmailMessage
import db

logger = logging.getLogger(__name__)


def build_confirmation(to_address, from_address, reservation_id, checkin, checkout, rooms, total):
	message = EmailMessage()
	message['Subject'] = "Fancy Hotel: reservation #%s confirmed" % reservation_id
	message['From'] = from_address
	message['To'] = to_address

	lines = []
	for room in rooms:
		extra_bed = " (extra bed)" if room.get('extra_bed_or_not') == 1 else ""
		lines.append("  - %s, room %s%s" % (room['location'], room['room_number'], extra_bed))

	message.set_content(
		"Your reservation is confirmed.\n\n"
		"Reservation number: %s\n"
		"Check-in: %s\n"
		"Check-out: %s\n"
		"Rooms:\n%s\n"
		"Total: $%.2f\n\n"
		"Thank you for choosing Fancy Hotel.\n"
		% (reservation_id, checkin, checkout, "\n".join(lines), total)
	)
	return message


def send_reservation_confirmation(username, reservation_id, checkin, checkout, rooms, total):
	#never raises: a failed email must not fail a reservation that is already saved
	try:
		to_address = db.mysqldb.get_customer_email(username)
		if not to_address:
			raise LookupError("customer %s has no email" % username)

		#read on every send, not on import, so a change in the environment applies without restarting
		mode = (os.environ.get('MAIL_MODE') or 'console').strip().lower()
		from_address = os.environ.get('MAIL_FROM') or 'no-reply@fancyhotel.local'
		message = build_confirmation(to_address, from_address, reservation_id, checkin, checkout, rooms, total)

		if mode == 'console':
			print(message.as_string())
		elif mode == 'smtp':
			host = os.environ.get('MAIL_HOST') or 'localhost'
			port = int(os.environ.get('MAIL_PORT') or '25')
			with smtplib.SMTP(host, port, timeout=10) as server:
				if os.environ.get('MAIL_USER'):
					server.login(os.environ['MAIL_USER'], os.environ.get('MAIL_PASSWORD', ''))
				server.send_message(message)
		else:
			raise ValueError("unknown MAIL_MODE %r, use console or smtp" % mode)
	except Exception as error:
		#only the type and message: no traceback or settings, so the password never reaches the log
		logger.error("Could not send the confirmation of reservation %s: %s: %s", reservation_id, type(error).__name__, error)
