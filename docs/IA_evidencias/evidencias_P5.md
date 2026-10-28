Estado actual
Rama feature/pago-datos-guardados, con cambios sin commitear en docs/ y tests/integration/ (no los toco).
Pruebas unitarias: 19 de 19 pasan. Integración: 43 pasan y 14 fallan, todas de test_pago_guardado.py.
BD local (MySQL 26.10): hay 4 tarjetas y 1152 reservas que apuntan a ellas. La FK reservation_ibfk_2 está como ON DELETE SET NULL.
Etapa 1: cambios por archivo
fancyhotel/db/mysqldb.py, solo en init_db:

El CREATE TABLE Credit_Card deja de tener cvv y agrega last4 CHAR(4) NOT NULL DEFAULT '' y is_default TINYINT(1) NOT NULL DEFAULT 0. card_number char(16) se queda igual: "tok_" más 12 caracteres hex da exactamente 16.
Justo después agrego la migración. Consulta information_schema.COLUMNS para ver si existe Credit_Card.cvv. Si existe, ejecuta DELETE FROM Fancy_Hotel.Credit_Card y luego un solo ALTER TABLE ... DROP COLUMN cvv, ADD COLUMN last4 ..., ADD COLUMN is_default .... Al ser una sola sentencia, no puede quedar a medias. Si cvv no existe, no hace nada, así que se puede ejecutar en cada arranque.
No cambian ni el nombre de la columna ni la FK de Reservation.

Antes de empezar
La migración borra datos al correr las pruebas. import db ejecuta init_db, así que la primera vez que corra pytest tests/integration se borrarán las 4 tarjetas de la BD local y las 1152 reservas quedarán con card_number = NULL. Es lo que pide el issue, pero se aplica en cuanto ejecute las pruebas.
Durante un rato algunas pruebas fallarán. Mientras la Etapa 2 no esté hecha, get_credit_cards sigue esperando 5 columnas. Por eso, al terminar la Etapa 1 espero que fallen las pruebas de /api/payment en test_seguridad.py, además de las de pago guardado. Prefiero mantener las etapas separadas y no adelantar cambios de la API. Te mostraré la lista exacta de fallos.
seed.py se rompe con el esquema nuevo, porque inserta cvv y números reales. Como esto lo causa este issue, propongo arreglarlo en la Etapa 2. CREDIT_CARDS pasaría a guardar (token fijo, nombre, last4, vencimiento) con tokens como tok_5eed00000001. Los tokens son fijos para que test_seed.py siga pasando sin modificarlo. ¿Lo incluyo o lo dejo como observación?
Hay una inconsistencia en la documentación: docs/decisiones.md tiene dos D-08 (.env y rama de trabajo) y ninguna trata del esquema de pago, aunque el docstring de la prueba cita D-08 como contrato. No toco los docs, solo te lo aviso.
¿Confirmas la Etapa 1 tal como está y me dices qué hago con seed.py (punto 3)?


confirmo y seed.py arreglalo en la etaoa 2, arregla la incosistencia de las decisiones

Etapa 1 lista
La migración ya se aplicó en tu BD local. Las 4 tarjetas se borraron y las 1152 reservas que las usaban quedaron con card_number = NULL. Al arrancar por segunda vez no cambió nada, así que se puede ejecutar en cada arranque.

Diff de fancyhotel/db/mysqldb.py


+			#card_number keeps its name for the Reservation FK, but stores a server token, never the real number (D-02, D-08)
 			cursor.execute(
 				'''CREATE TABLE IF NOT EXISTS Fancy_Hotel.Credit_Card (
 				 	card_number char(16) NOT NULL,
 				 	name varchar(41) NOT NULL,
-				 	cvv char(3) NOT NULL,
 				 	expiration_date date NOT NULL,
 				 	username char(5) NOT NULL,
+				 	last4 CHAR(4) NOT NULL DEFAULT '',
+				 	is_default TINYINT(1) NOT NULL DEFAULT 0,
 				 	...
 			)
+
+			#old schema (real number + cvv): its cards can't become tokens, so they are deleted (Reservation.card_number is SET NULL)
+			#MySQL has no DROP COLUMN IF EXISTS, so check information_schema; without cvv this is a no-op on every start
+			cursor.execute(
+				'''SELECT COUNT(*) FROM information_schema.COLUMNS
+				WHERE TABLE_SCHEMA = 'Fancy_Hotel' AND TABLE_NAME = 'Credit_Card' AND COLUMN_NAME = 'cvv';'''
+			)
+			if cursor.fetchall()[0][0]:
+				cursor.execute('''DELETE FROM Fancy_Hotel.Credit_Card;''')
+				self.connection.commit()
+				cursor.execute(
+					'''ALTER TABLE Fancy_Hotel.Credit_Card
+					DROP COLUMN cvv,
+					ADD COLUMN last4 CHAR(4) NOT NULL DEFAULT '',
+					ADD COLUMN is_default TINYINT(1) NOT NULL DEFAULT 0;'''
+				)
Cambios en docs/decisiones.md

D-08 ahora es "Esquema de Credit_Card para el pago guardado", con el contrato de esta etapa. Así coincide con lo que cita el docstring de test_pago_guardado.py.
Las dos D-08 anteriores pasan al final como D-26 (.env) y D-27 (rama de trabajo), con la nota "(antes D-08)". Nada fuera del archivo citaba esas D-08.
En D-02 reemplacé los dos marcadores [Decidir… tabla Payment] por "No se agrega la tabla Payment (ver D-08)". Lo deduje de que el issue reutiliza Credit_Card; si el equipo no lo decidió así, revísalo.
Pruebas

Unitarias: 19 de 19 pasan.
Integración: 43 pasan y 14 fallan, como esperaba:
test_esquema_sin_cvv_y_con_last4 ya pasa.
Las otras 13 de test_pago_guardado.py fallan con Unknown column 'cvv' o too many values to unpack, porque la API todavía usa el esquema anterior.
test_seguridad.py::test_cliente_ve_sus_propias_tarjetas falla por la misma causa (get_credit_cards). Es la falla que te había anticipado.
Hay otra inconsistencia en las decisiones que no corregí. El código (mysqldb.py:452), D-10, D-16 y evidencias_P3.md citan D-06 como la regla "noche ocupada si no queda ninguna habitación libre". En el archivo, D-06 es "Rama base para la migración a Python 3", y esa regla no está registrada en ninguna parte. Puedo registrarla como decisión nueva y actualizar las referencias si quieres.

Plan de la Etapa 2: API de tarjetas
fancyhotel/api.py

Un helper validate_card(card_number, cvv, expiration_date) que devuelve (None, error) o (datos, None), igual que validate_stay. Valida 16 dígitos, cvv de 3 dígitos y fecha YYYY-MM-DD que no sea anterior a hoy; si algo falla responde 400. Del número solo conserva last4, y no se imprime ni se registra nada.
CreditCardResource:
post acepta make_default opcional (inputs.boolean) y responde {"result": true, "card": {...}}.
get devuelve la lista con token, last4, name, expiration_date e is_default (como bool).
delete recibe ?token=. Responde 404 si el token no es del usuario y mantiene la regla de no borrar tarjetas usadas en reservas futuras.
Un recurso nuevo, CreditCardDefaultResource, con post {"token"}: responde 404 si el token no es del usuario y, si lo es, deja solo esa tarjeta como predeterminada.
fancyhotel/serve.py: registro la ruta /api/payment/default.

fancyhotel/db/mysqldb.py

add_credit_card(username, last4, name, expiration_date, make_default) genera el token ("tok_" + secrets.token_hex(6)). Si la tarjeta es predeterminada, en la misma transacción quita la marca a las demás. Devuelve la tarjeta creada.
get_credit_cards selecciona las columnas por nombre (sin SELECT *) y devuelve el formato nuevo.
Agrego set_default_credit_card(username, token): con un solo UPDATE deja is_default en 1 para esa tarjeta y en 0 para las demás, siempre que el token sea del usuario.
delete_credit_card solo renombra su parámetro a token.
fancyhotel/seed.py: CREDIT_CARDS pasa a (token fijo, nombre, last4, vencimiento) con tokens tok_5eed0000000N, cada uno como predeterminado de su cliente. test_seed.py sigue pasando sin cambios.

Pruebas unitarias: no hace falta ajustar ninguna, porque ninguna prueba toca /api/payment.

Al terminar la Etapa 2 espero que pase test_seguridad.py completo y todo test_pago_guardado.py menos las 5 pruebas de reserva, que son de la Etapa 3.

Una decisión que el issue no define: con este plan, la primera tarjeta que agrega un usuario no queda como predeterminada si no marca la casilla. Me ciño al issue; si prefieres que la primera tarjeta lo sea automáticamente, dímelo.

¿Confirmas la Etapa 2?

confirmo etapa 2 

Etapa 2 lista
Pruebas

Unitarias: 19 de 19 pasan, sin cambios en ninguna prueba.
Integración: 53 pasan y 4 fallan.
Ya pasa todo test_seguridad.py, incluida test_cliente_ve_sus_propias_tarjetas.
Ya pasan las 9 pruebas de tarjetas y la de borrar tarjetas en test_pago_guardado.py.
Siguen fallando 4 pruebas que corresponden a la Etapa 3: reserva_sin_token_usa_la_predeterminada, no_puede_usar_tarjeta_de_otro_usuario y las dos de precio_se_calcula_con_precios_de_la_bd.
Diff
fancyhotel/api.py


+import re
-from flask_restful import Resource, reqparse, abort, request
+from flask_restful import Resource, reqparse, abort, request, inputs
-from datetime import datetime
+from datetime import datetime, date

+def validate_card(card_number, cvv, expiration_date):
+	#returns (last4, None) or (None, error response); the number and cvv are never stored or logged (D-02, D-08)
+	if not re.fullmatch(r'\d{16}', card_number or ''):
+		return None, ({"message": "The card number must have 16 digits", "result": False}, 400)
+	if not re.fullmatch(r'\d{3}', cvv or ''):
+		return None, ({"message": "The security code must have 3 digits", "result": False}, 400)
+	try:
+		expires = datetime.strptime(expiration_date, "%Y-%m-%d").date()
+	except (TypeError, ValueError):
+		return None, ({"message": "The expiration date must use the format YYYY-MM-DD", "result": False}, 400)
+	if expires < date.today():
+		return None, ({"message": "This card has expired", "result": False}, 400)
+	return card_number[-4:], None

 class CreditCardResource(Resource):
-		self.delete_reqparse.add_argument("card_number", ..., location='args')
+		self.delete_reqparse.add_argument("token", ..., location='args')
-		self.create_reqparse.add_argument("cvv", ..., help="Please provide a ccv")
+		self.create_reqparse.add_argument("cvv", ..., help="Please provide a security code")
+		self.create_reqparse.add_argument("make_default", type=inputs.boolean, default=False, location='json')

 	def post(self):
 		args = self.create_reqparse.parse_args()
-		message, status = db.mysqldb.add_credit_card(session['username'], args['card_number'], args['cvv'], ...)
-		if status: ...
+		last4, error = validate_card(args['card_number'], args['cvv'], args['expiration_date'])
+		if error:
+			return error
+		card = db.mysqldb.add_credit_card(session['username'], last4, args['name'], args['expiration_date'], args['make_default'])
+		return {'message': "Credit card successfully created", 'result': True, 'card': card}

 	def delete(self):
 		args = self.delete_reqparse.parse_args()
-		reservations = db.mysqldb.get_reservation_by_card_number(session['username'], args['card_number'])
+		if not db.mysqldb.get_credit_card(session['username'], args['token']):
+			return {'message': "This credit card was not found", 'result': False}, 404
+		reservations = db.mysqldb.get_reservation_by_card_number(session['username'], args['token'])
 		... (future-reservation rule unchanged)
-		message, status = db.mysqldb.delete_credit_card(session['username'], args['card_number'])
+		message, status = db.mysqldb.delete_credit_card(session['username'], args['token'])

+class CreditCardDefaultResource(Resource):
+	method_decorators = [login_required]
+	...
+	def post(self): #leaves this card as the only default one of the user
+		args = self.reqparse.parse_args()
+		if not db.mysqldb.set_default_credit_card(session['username'], args['token']):
+			return {'message': "This credit card was not found", 'result': False}, 404
+		return {'message': "Default credit card updated", 'result': True}
Cambié el texto de ayuda de cvv (antes decía "ccv") para que el mensaje 400 no contenga esa palabra.

fancyhotel/serve.py


+api.add_resource(restapi.CreditCardDefaultResource, '/api/payment/default')
fancyhotel/db/mysqldb.py


+import secrets

-	def add_credit_card(self, username, card_number, cvv, expiration_date, card_name):
+	def add_credit_card(self, username, last4, card_name, expiration_date, make_default):
+		#card_number stores a token generated here; the real number never reaches the database (D-08)
+		token = "tok_" + secrets.token_hex(6)
+		if make_default:  UPDATE ... SET is_default = 0 WHERE username = ...
+		INSERT (card_number, name, expiration_date, username, last4, is_default) VALUES (token, ...)
+		self.connection.commit()   # one commit: unmark the others + insert
+		return {"token", "last4", "name", "expiration_date", "is_default"}

-	def get_credit_cards(self, username):
-		SELECT * ...  -> {"card_number", "name", "cvv", "expiration_date", "username"}
+	def get_credit_cards(self, username, token=None):
+		#with a token, returns at most that card, and only if it belongs to the user
+		SELECT card_number, last4, name, expiration_date, is_default ...
+		WHERE username = %(username)s AND (%(token)s IS NULL OR card_number = %(token)s)
+		-> {"token", "last4", "name", "expiration_date", "is_default": bool}

+	def get_credit_card(self, username, token):        # None if it isn't the user's card
+	def set_default_credit_card(self, username, token):
+		#returns False when the token is not one of the user's cards
+		UPDATE ... SET is_default = (card_number = %(token)s) WHERE username = %(username)s

-	def delete_credit_card(self, username, card_number):
+	def delete_credit_card(self, username, token):     # same query
fancyhotel/seed.py


-#username: (card_number, name, cvv, expiration_date) -- standard test numbers, not real cards
+#username: (token, name, last4, expiration_date) -- fixed tokens so reservations can point to them; each is the user's default (D-08)
-	'Cl3a8': ('4111111111111111', 'Laura Gomez', '123', date(2029, 12, 31)),
+	'Cl3a8': ('tok_5eed00000001', 'Laura Gomez', '1111', date(2029, 12, 31)),
 	... (same for the other 3)
-	INSERT ... (card_number, name, cvv, expiration_date, username) VALUES (%s, %s, %s, %s, %s)
+	INSERT ... (card_number, name, last4, expiration_date, username, is_default) VALUES (%s, %s, %s, %s, %s, 1)
Cosas que difieren del plan

Agregué get_credit_card(username, token), que no estaba en el plan. Para no duplicar SQL reutiliza get_credit_cards con un filtro opcional. La usan el 404 de DELETE y set_default_credit_card, y la usaré en la Etapa 3.
No ejecuté seed.py, porque vacía todas las tablas de tu BD local. test_seed.py pasa. Si quieres volver a tener datos de desarrollo, ejecútalo con python fancyhotel/seed.py.
Plan de la Etapa 3: crear la reserva
fancyhotel/api.py, en CreateReservationResource.post. Las validaciones quedan en este orden:

Las fechas siguen igual (400).
Cada habitación necesita location, room_number y extra_bed_or_not. Quito cost de los campos obligatorios, porque ya no se usa y el frontend dejará de enviarlo (400).
La tarjeta:
Quito card_number como obligatorio y agrego card_token opcional.
Si viene card_token y get_credit_card devuelve None, respondo 403 (también si el token no existe).
Si no viene, uso la tarjeta con is_default de get_credit_cards. Si no tiene ninguna, respondo 400.
La revalidación de disponibilidad sigue igual (409).
El total se calcula con room_cost y extra_bed_price de la BD, ignorando cost y extra_bed_price que envíe el cliente. extra_bed_price NULL cuenta como 0. Si la habitación no existe, respondo 400.
fancyhotel/db/mysqldb.py: agrego get_room_prices(location, room_number), que devuelve (room_cost, extra_bed_price) o None.

tests/unit/test_validaciones.py: el nuevo contrato rompe 1 prueba, así que propongo 2 ajustes:

El helper create() envía card_token: 'tok_5eed00000001' en lugar de card_number. Las pruebas de 400 y 409 no cambian, porque el mock devuelve una tarjeta "válida" por defecto.
En test_create_reservation_valid, el mock devuelve la tarjeta y los precios de la BD (150, 20). Ahora espera el token y un total de 300, no 200. Así la prueba demuestra que se ignora el cost: 100 que envía el cliente.
Observación (fuera del issue, no la implemento): el servidor no comprueba que la tarjeta siga vigente en la fecha de salida; solo el frontend lo hace.

¿Confirmas la Etapa 3?

cofnirmo etapa 3 y 4

Etapas 3 y 4 listas
Todas las pruebas pasan: 19 de 19 unitarias y 57 de 57 de integración. Además recorrí las dos vistas en Chrome con la app real.

Etapa 3: crear la reserva
fancyhotel/api.py, en CreateReservationResource:


-		self.reqparse.add_argument('card_number', type=str, required=True, help="Please provide a card_number")
+		self.reqparse.add_argument('card_token', type=str, location='json') #optional: without it, the user's default card is used
 ...
-		required_keys = ('location', 'room_number', 'cost', 'extra_bed_or_not')
+		required_keys = ('location', 'room_number', 'extra_bed_or_not')
 ...
+		#the card must belong to the session user (S4)
+		if args['card_token']:
+			card = db.mysqldb.get_credit_card(session['username'], args['card_token'])
+			if not card:
+				return {"message": "This credit card does not belong to you", "result": False}, 403
+		else:
+			card = next((c for c in db.mysqldb.get_credit_cards(session['username']) if c['is_default']), None)
+			if not card:
+				return {"message": "You have no default credit card. Please select or add one", "result": False}, 400
 		(revalidación 409 sin cambios)
-		total_cost += room['cost'] ... room['extra_bed_price']
+		#prices come from the Room table; cost and extra_bed_price sent by the client are ignored (S3)
+		prices = db.mysqldb.get_room_prices(room['location'], room['room_number'])
+		if not prices: return {...does not exist...}, 400
+		room_cost, extra_bed_price = prices
+		total_cost += room_cost
+		if room['extra_bed_or_not'] == 1:
+			total_cost += extra_bed_price or 0
-		... insert_reservation(..., args['card_number'], ...)
+		... insert_reservation(..., card['token'], ...)
fancyhotel/db/mysqldb.py: nuevo get_room_prices(location, room_number), que devuelve (room_cost, extra_bed_price) o None.

Cambios en tests/unit/test_validaciones.py, como en el plan:

El helper create() envía card_token: 'tok_5eed00000001' en lugar de card_number, porque el campo cambió de nombre en el contrato.
test_create_reservation_valid: el mock devuelve la tarjeta y el precio de la BD (150, 20), y la prueba espera el token y un total de 300. Antes esperaba 200, que salía del cost: 100 enviado por el cliente. Ahora la prueba demuestra que ese valor se ignora.
Etapa 4: frontend
fancyhotel/static/views/payment.html

Formulario de alta:
El número usa maxlength="16", pattern="[0-9]{16}" y autocomplete="cc-number".
El CVV es type="password" con pattern="[0-9]{3}".
Nueva casilla "Use as my default card".
La sección "Delete card", que mostraba el número completo en un <select>, pasa a ser una tabla "Saved cards". Cada fila muestra •••• 1234, el nombre, el vencimiento, la etiqueta "Default" o el botón "Make default", y el botón "Delete".
fancyhotel/static/views/searchRoom.html

Si el usuario tiene tarjeta predeterminada, aparece el botón "Reservar con tarjeta •••• 4444", que reserva sin pedir datos de pago.
Debajo está el selector "Or pay with another saved card:" con las opciones •••• 1234 (expires …) y el botón "Book with selected card", que envía card_token.
El total ahora se llama "Estimated total cost" y lleva la nota "The final price is calculated by the hotel when you book".
fancyhotel/static/js/controllers.js

paymentFactory: nuevo SetDefaultCreditCard (POST /api/payment/default).
reservationController:
Al cargar las tarjetas identifica defaultCard y preselecciona su token.
bookRooms(cardToken) envía card_token solo si se eligió una tarjeta en el selector.
Las habitaciones se envían como {room_number, location, extra_bed_or_not}, sin precios.
Se mantiene el aviso de tarjeta que vence antes de la salida.
paymentController:
Agregué loadCards(). Antes la lista no se refrescaba al borrar una tarjeta.
Después de guardar una tarjeta, se borran el número y el CVV del formulario.
Agregué setDefaultCard(card). deleteCard(card) ahora pide confirmación y envía ?token=.
Los errores ahora muestran el mensaje del servidor; antes, al fallar el alta, no se mostraba nada.
Saqué errorMessage() de reservationController y la dejé a nivel de archivo, sin cambiar su código, para que también la use paymentController.
Prueba en el navegador
Lancé la app en el puerto 5099 y la manejé con Chrome headless usando un cliente temporal (CFRT1), que borré al terminar:

Pagos: agregué la 4242 como predeterminada y la 4444 sin marcar. El formulario de una tarjeta inválida (1234, cvv 12) lo bloqueó el navegador. Después marqué la 4444 como predeterminada. La BD guarda solo tok_… y last4.
Reserva en un clic: apareció "Reservar con tarjeta •••• 4444". La petición fue {"checkIn":…,"rooms":[{"room_number":101,"location":"Atlanta","extra_bed_or_not":1}]}, sin card_token ni precios. En la BD quedó el token de la 4444 y un total de 240 = (100 + 20) × 2.
Con el selector: elegí la 4242 y la petición incluyó su card_token. En la BD quedó ese token y un total de 300 = 100 × 3.
Capturas: /private/tmp/claude-502/-Users-anaisabelpm-Documents-topicos/280c9a28-15e0-48bc-825a-f11c5070d7af/scratchpad/payment-view.png y /private/tmp/claude-502/-Users-anaisabelpm-Documents-topicos/280c9a28-15e0-48bc-825a-f11c5070d7af/scratchpad/search-view.png.
No probé en el navegador el botón "Delete"; ese caso solo lo cubren las pruebas de integración.
Bugs que encontré y no corregí
Todavía se puede manipular el precio con extra_bed_or_not. Si el cliente envía "1" (texto) en lugar de 1, la reserva se guarda con cama extra pero no se cobra. Esto pertenece a S3, así que podría corregirse en este mismo issue: aceptar solo 0/1 y responder 400 en cualquier otro caso. ¿Lo hago?
La conexión global nunca hace commit después de un SELECT. Con el servidor corriendo, cualquier otro proceso que importe db (como seed.py o un script) se queda bloqueado en el ALTER TABLE ... MODIFY password de init_db. Además, el servidor puede leer datos desactualizados. Me pasó durante la prueba del navegador. Está relacionado con B4.
El servidor no comprueba que la tarjeta siga vigente en la fecha de salida; solo lo comprueba el frontend.
Si se borra la tarjeta predeterminada, el usuario queda sin ninguna y desaparece el botón de reserva en un clic. No se asigna otra automáticamente.
Si se envía la misma habitación dos veces en una reserva, la API responde 500 por IntegrityError (B14).
Otras notas:

El texto "Reservar con tarjeta" está en español porque así lo pide el issue, pero el resto de la interfaz está en inglés.
No hice commit.
Los cambios en tests/integration/test_disponibilidad.py y test_seguridad.py ya estaban antes de empezar; no los toqué.
