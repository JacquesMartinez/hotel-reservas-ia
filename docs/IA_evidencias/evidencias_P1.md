Análisis de hotel-reservas-ia (FancyHotel)

Analiza este proyecto sin modificar ningún archivo. Quiero:

Stack tecnológico exacto (lenguaje y versión, frameworks de backend y frontend con versiones)
Estructura de carpetas y responsabilidad de cada archivo
Esquema de la base de datos: tablas, llaves y relaciones
Lista de todos los endpoints con método HTTP y propósito
Flujo completo de una reserva, desde la búsqueda hasta el pago
Problemas de seguridad, bugs y deuda técnica, indicando archivo y línea
Qué funcionalidad existente podría reutilizarse para: un calendario de disponibilidad, pago con tarjeta guardada y gráficos de previsión de demanda



No modifiqué ningún archivo. Solo hice lecturas y un script de prueba de rutas en el scratchpad. El código viene de un proyecto académico de 2016 (CS 4400, commit 6cab9d9). Lo único tuyo encima es la estructura de docs/ y la plantilla de PR.

1. Stack tecnológico
Backend

Componente	Versión	Evidencia
Lenguaje	Python 2.7, que es para lo que está escrito el código	print x sin paréntesis en api.py:98, api.py:108, api.py:201 y mysqldb.py:196
Entorno local (venv/)	Python 3.12.16, Flask 3.1.3, Flask-RESTful 0.3.10, Werkzeug 3.1.9, Jinja2 3.1.6, mysql-connector-python 26.10.0, pytest 9.2.0	venv/pyvenv.cfg y site-packages
Base de datos	MySQL, sin versión fijada. Usa el esquema sys (5.7+) e int(11) (obsoleto desde 8.0.17)	mysqldb.py:7
⚠️ El código no corre con el venv actual. Bajo Python 3.12, api.py y mysqldb.py dan SyntaxError por los print. Además, mysqldb.py:374 mezcla un espacio con tabs, lo que en Python 3 provoca un TabError. No hay requirements.txt, así que no se conocen las versiones originales de Flask y Flask-RESTful.

Frontend (sin build ni package.json; todo se carga en index.html:24-49)

AngularJS 1.4.6, con ngRoute y ngResource, desde CDN
jQuery 1.11.3 y Bootstrap 3.3.5, desde CDN
Moment.js 2.10.6 (local)
Eonasdan bootstrap-datetimepicker 4.15.35 (local). Ojo: el archivo se llama bootstrap-datepicker.js, pero la librería es el datetimepicker.
2. Estructura de carpetas

hotel-reservas-ia/
├── README.md                  Instrucciones originales (instalar MySQL, `python serve.py`)
├── .github/pull_request_template.md   Plantilla de PR con sección "Uso de IA"
├── docs/                      Bitácoras del curso (AI-LOG, decisiones, respuestas-incorrectas, arquitectura vacía)
└── fancyhotel/
    ├── serve.py               App Flask: ruta "/" y registro de los 14 recursos REST
    ├── api.py                 Recursos Flask-RESTful: validan parámetros (reqparse), calculan costos y llaman a la BD
    ├── db/__init__.py         Crea un único MysqlManager global compartido por todo el proceso
    ├── db/mysqldb.py          Capa de datos: crea BD y tablas al arrancar, y todas las consultas SQL
    ├── templates/index.html   Shell de la SPA: carga librerías y monta <div ng-view>
    └── static/
        ├── js/controllers.js  Toda la app Angular: 5 factories $resource, 6 controllers, rutas
        ├── libs/              moment, datetimepicker (js + css)
        └── views/*.html       13 vistas parciales:
              welcome, login, registerUser, selectionPage (portal según rol)
              searchRoom (búsqueda + reserva + confirmación), updateReservation, cancelReservation
              payment (alta y baja de tarjetas), writeReview, viewFeedback
              reservationReport, popularRoomCatReport, revenueReport (solo manager)
3. Esquema de la base de datos (Fancy_Hotel)
Se crea en mysqldb.py:11-115. No hay migraciones ni datos semilla, así que Room y Manager quedan vacías (ver el comentario en la línea 108).

Tabla	PK	FK	Campos relevantes
Customer	username CHAR(5)	—	password VARCHAR(16) en texto plano, email UNIQUE
Manager	username CHAR(5)	—	password. Tabla aislada, sin relaciones
Credit_Card	card_number CHAR(16)	username → Customer	cvv, expiration_date, name
Review	review_id AUTO_INCREMENT	username → Customer	location (texto libre, sin FK), rating VARCHAR, comment
Reservation	reservation_id AUTO_INCREMENT	username → Customer; card_number → Credit_Card ON DELETE SET NULL	checkin_date, checkout_date, total_cost FLOAT, cancelled_or_not CHAR(1)
Room	(location, room_number)	—	type, room_cost, capacity, extra_bed_price
Reserves_Extra_Bed	(location, room_number, reservation_id)	→ Room, → Reservation	extra_bed_or_not
Relaciones:


Customer 1──N Credit_Card 1──N Reservation N──M Room
    │                              │           (vía Reserves_Extra_Bed,
    ├──1──N Reservation ───────────┘            que en realidad es la tabla
    └──1──N Review                              puente reserva-habitación)
Manager (sin relaciones). El rol se deduce del prefijo del username: 'C' o 'M'.
Observaciones: no existe una tabla Hotel/Location (las sedes están escritas a mano en las vistas). El dinero se guarda como FLOAT. No hay columna created_at en Reservation. cancelled_date está comentada (línea 76).

4. Endpoints
Definidos en serve.py:12-29.

Método	Ruta	Recurso	Propósito
GET	/	index	Sirve la SPA
POST	/api/login	LoginResource	Valida usuario y contraseña contra Customer o Manager según el prefijo
POST	/api/register	NewUserRegistrationResource	Crea un Customer
GET	/api/searchRoom?location&checkIn&checkOut	SearchRoomsResource	Habitaciones libres en una sede
POST	/api/reservation/create	CreateReservationResource	Crea la reserva con sus habitaciones y la tarjeta
PUT	/api/reservation	UpdateReservationResource	Cambia fechas y recalcula el costo. Es el que usa el front en la práctica (ver bug B6)
GET	/api/reservation/<id>?username	ReservationResource.get	Detalle de una reserva no cancelada
PUT	/api/reservation/<id>	ReservationResource.put	Actualización duplicada y rota (ver B6)
GET	/api/reservation/<id>/availability?checkIn&checkOut&username	UpdateReservationConfirmResource	¿Siguen libres las habitaciones de la reserva en las fechas nuevas?
GET	/api/reservation/<id>/cancel?username	CancelReservationResource	Cancela y aplica la penalización (un GET que modifica estado)
GET	/api/reservation/cardNumber?username&card_number	GetReservationByCardNumberResource	Reservas pagadas con una tarjeta. El front no lo usa
GET	/api/payment?username	CreditCardResource	Lista las tarjetas del usuario
POST	/api/payment	CreditCardResource	Agrega una tarjeta
DELETE	/api/payment?username&card_number	CreditCardResource	Borra una tarjeta si no tiene reservas futuras
GET	/api/review?location	ReviewResource	Reseñas de una sede
POST	/api/review	ReviewResource	Crea una reseña
GET	/api/reports/reservation	ReservationReportResource	Reservas por mes y sede (solo agosto y septiembre)
GET	/api/reports/popularRoom	PopularRoomReportResource	Categoría más reservada por sede (solo agosto)
GET	/api/reports/revenue	RevenueReportResource	Ingresos por mes y sede (agosto y septiembre)
/api/reservation/cardNumber también encaja en el patrón /api/reservation/<id>. Comprobé con Werkzeug 3.1.9 que gana la ruta estática, pero el diseño es frágil.

5. Flujo de una reserva, de la búsqueda al pago
Login (controllers.js:180-197): POST /api/login. Si responde OK, el front guarda el username en $rootScope.currentUser. No hay sesión, token ni cookie.
Búsqueda (#/reserve → reservationController.submit, controllers.js:290-320): lee las fechas de los datetimepickers y llama GET /api/searchRoom.
El backend ejecuta search_rooms (mysqldb.py:201-241): Room de la sede, excluyendo las habitaciones con reservas no canceladas contenidas en el rango.
Luego el front pide GET /api/payment para llenar el <select> de tarjetas guardadas.
Selección: casillas por habitación y por cama extra. El botón "Update total cost" (controllers.js:322-350) calcula el total solo en el cliente: (Σ precio + cama extra) × noches.
Reserva (bookRooms, controllers.js:353-435): verifica en el cliente que la tarjeta no venza antes del checkout, arma rooms[] con cost y extra_bed_price tomados del cliente y llama POST /api/reservation/create.
Backend (api.py:61-80): recalcula total_cost con los precios que mandó el cliente. Después insert_reservation (mysqldb.py:309-338) inserta en Reservation (con card_number) y una fila por habitación en Reserves_Extra_Bed, y hace commit. No vuelve a verificar disponibilidad.
Confirmación: la vista muestra el reservation_id.
"Pago": no existe un cobro real. El pago se reduce a guardar el card_number como FK y un total_cost. No hay tabla de pagos, estado de pago ni pasarela.
Después de reservar:
Modificar: GET .../availability y luego PUT /api/reservation. El servidor recalcula el costo con los precios de la BD.
Cancelar: GET .../cancel. Sobrescribe total_cost con la penalización: 100% si faltan ≤1 día, 20% si faltan <4 y 0 en otro caso (mysqldb.py:364-372).
6. Seguridad, bugs y deuda técnica
Seguridad (de mayor a menor gravedad)
#	Problema	Ubicación
S1	No hay autenticación en el servidor. Cada endpoint confía en el username que llega en la petición, así que cualquiera puede leer las tarjetas, reservar, modificar o cancelar a nombre de otro usuario (IDOR)	todo api.py; la sesión vive solo en controllers.js:106
S2	Se guardan el PAN completo y el CVV en texto plano, y el CVV se devuelve en la API (viola PCI-DSS)	mysqldb.py:44-46, mysqldb.py:451-458, api.py:222-224
S3	Manipulación de precio: el total se calcula con cost y extra_bed_price que envía el cliente	api.py:70-74
S4	No se verifica que la tarjeta pertenezca al usuario que reserva; la FK solo exige que la tarjeta exista	api.py:75, mysqldb.py:314-318
S5	Contraseñas en texto plano; VARCHAR(16) ni siquiera admite un hash	mysqldb.py:25, mysqldb.py:157, mysqldb.py:177-180
S6	Credenciales root/password escritas en el código	mysqldb.py:7, mysqldb.py:115
S7	debug=True con escucha en 0.0.0.0 expone el depurador interactivo de Werkzeug	serve.py:8, serve.py:33
S8	Los reportes de manager son públicos; el rol solo se valida en las vistas	api.py:270-280
S9	La cancelación usa GET, lo que la expone a CSRF o a un simple <img src>	serve.py:25, api.py:180
S10	Librerías sin soporte y con CVE conocidos: jQuery 1.11.3, Bootstrap 3.3.5, Moment 2.10.6, AngularJS 1.4 (EOL). Se cargan por http:// (contenido mixto) y sin SRI	index.html:24, index.html:37-47
Bugs
#	Bug	Ubicación
B1	Overbooking. El solapamiento solo detecta reservas contenidas en el rango (checkin >= X AND checkout <= Y), no las parciales ni las que envuelven el rango. Lo correcto es res.checkin < :out AND res.checkout > :in	mysqldb.py:212, mysqldb.py:405-406
B2	Al crear la reserva no se revalida la disponibilidad, lo que deja una condición de carrera entre la búsqueda y la reserva	api.py:61-75
B3	Transacción incompleta: si falla una habitación se hace return sin rollback, y la fila de Reservation queda pendiente y se confirma con el siguiente commit de cualquier petición	mysqldb.py:332-333
B4	Una única conexión MySQL global compartida entre hilos (no es thread-safe) y sin reconexión	db/__init__.py:3, mysqldb.py:115
B5	Se permite checkout igual a checkin, lo que da 0 noches y costo $0. Tampoco hay validación de fechas en el servidor; con un formato inválido strptime produce un 500	controllers.js:237, api.py:66-68, api.py:95-97
B6	ReservationResource.put está roto: deltaDays no está definido, la línea 147 no asigna nada y la 150 llama con un argumento de menos. Funciona "por accidente" porque $resource manda el objeto como body, la URL queda en /api/reservation y la atiende UpdateReservationResource	api.py:145-150, controllers.js:502-508
B7	El reembolso que ve el usuario no coincide con lo que se cobra. El front usa Math.round y el back .days, que trunca y además resta la hora actual. Ejemplo: con un checkin a 2 días, el front muestra 80% de reembolso y el back cobra el 100%	controllers.js:538 vs mysqldb.py:366
B8	revenue_report suma total_cost una vez por habitación, así que una reserva de N habitaciones se cuenta N veces	mysqldb.py:626-631
B9	Los reportes tienen los meses fijos (agosto y septiembre), y reservation_report cuenta habitaciones en lugar de reservas, incluidas las canceladas	mysqldb.py:563, mysqldb.py:588, mysqldb.py:630
B10	room_report ejecuta CREATE OR REPLACE VIEW en cada GET (DDL dentro de una lectura)	mysqldb.py:583
B11	bookRooms muestra una alerta si no hay tarjeta o habitaciones, pero no hace return y envía la reserva igual; además no maneja el error de la respuesta	controllers.js:354-357, controllers.js:415-418, controllers.js:429
B12	El login distingue mayúsculas en el prefijo ('C'/'M') mientras el front acepta c/m; con un username vacío da IndexError (500)	mysqldb.py:172, controllers.js:119-122
B13	user_exists consulta customer en minúsculas y sin esquema, lo que falla en MySQL sobre Linux, donde los nombres de tabla distinguen mayúsculas	mysqldb.py:124
B14	Las IntegrityError no se capturan (tarjeta o usuario duplicados, condición de carrera en el registro) y terminan en un 500; register_user falla en silencio	mysqldb.py:161-162, mysqldb.py:420-427
B15	La vista de cancelación etiqueta la penalización como "Total cost of reservation"	cancelReservation.html:64
Deuda técnica
Código en Python 2 incompatible con el entorno, sin requirements.txt, sin tests (pytest está instalado pero no hay ninguno), sin migraciones ni datos semilla.
SQL y lógica de negocio mezclados. La fórmula de costo está duplicada en 4 sitios: api.py:70-74, api.py:100-109, controllers.js:322-350 y controllers.js:490-499.
extra_bed_or_not se compara a veces con el entero 1 y a veces con el texto '1' (api.py:72 vs api.py:105).
Un único reservationController atiende 4 vistas. Se usa jQuery dentro de los controllers. ng-show="{{...}}" aparece en todas las vistas.
Mensajes de ayuda copiados y equivocados (api.py:38, api.py:255-257). Falta super().__init__() en api.py:248 y api.py:282.
7. Qué se puede reutilizar
Calendario de disponibilidad

Reutilizable: la consulta de ocupación (el join Room ⋈ Reserves_Extra_Bed ⋈ Reservation con cancelled_or_not = 0) de is_room_free y search_rooms (mysqldb.py:393-415), una vez corregido el solapamiento (B1). También UpdateReservationConfirmResource (api.py:156-170) como patrón de endpoint de disponibilidad. En el front ya están cargados moment y el datetimepicker v4, que acepta disabledDates y enabledDates para marcar los días ocupados.
Falta: un endpoint que devuelva en una sola consulta los rangos ocupados por habitación o sede en un periodo (no llamar a is_room_free día por día), y una tabla de sedes.
Pago con tarjeta guardada

Ya existe a medias: la tabla Credit_Card, el CRUD /api/payment, paymentFactory, el <select> de tarjetas en searchRoom.html:78, la FK Reservation.card_number y la regla de no borrar una tarjeta con reservas futuras (api.py:233-246). El flujo de UI y esa regla se pueden conservar.
Hay que reemplazar el almacenamiento: tokenizar con una pasarela y guardar solo token, últimos 4 dígitos, marca y vencimiento (nunca el PAN ni el CVV). Además: una tabla Payment (reserva, monto, estado, referencia del proveedor), validar en el servidor que la tarjeta es del usuario, calcular el precio en el servidor y tener autenticación real (S1–S4).
Gráficos de previsión de demanda

Reutilizable: las tres consultas de reportes (mysqldb.py:555-643), reportFactory y reportController, y las vistas de manager con su control por rol.
Falta:
parametrizar fechas, excluir canceladas y corregir B8 y B9;
una serie temporal de noches-habitación por día o semana;
una librería de gráficos (hoy no hay ninguna);
una columna created_at en Reservation: sin la fecha de creación no se puede calcular la antelación de reserva ni la curva de reservas, que son la base de cualquier pronóstico;
datos históricos, porque hoy la BD arranca vacía.