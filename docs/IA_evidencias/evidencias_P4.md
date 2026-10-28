Vas a implementar el issue #N "Seguridad de cuenta y acceso por rol".

CONTEXTO
- Lee docs/arquitectura.md (S1, S5, S8) y tests/integration/test_seguridad.py.
  El docstring de ese archivo define el contrato exacto.
- Las pruebas de integración no se modifican. Deben pasar todas:
    python -m pytest tests/integration -v
- Las pruebas unitarias (tests/unit/) usan un conftest.py que reemplaza db
  por un MagicMock. Si alguna deja de funcionar por el nuevo contrato
  (por ejemplo, porque login ahora debe devolver un rol), puedes ajustarla,
  pero explica cada cambio. No modifiques conftest.py.
    python -m pytest -v

TRABAJA POR ETAPAS. Al terminar cada una, muestra el diff, ejecuta las
pruebas y espera mi confirmación.

ETAPA 1 - Contraseñas con hash (S5)
- Usa werkzeug.security: generate_password_hash al registrar y
  check_password_hash al hacer login, para Customer y Manager.
- Amplía password a VARCHAR(255) en ambas tablas. OJO: init_db usa
  CREATE TABLE IF NOT EXISTS, así que cambiar la definición no altera una
  BD existente. Agrega en init_db un ALTER TABLE ... MODIFY que se pueda
  ejecutar en cada arranque sin error.
- login() debe devolver el rol ("customer" o "manager") o None. Acepta el
  prefijo en mayúscula o minúscula y no falles con username vacío.
- Actualiza seed.py para guardar las contraseñas con hash.

ETAPA 2 - Sesión en el servidor
- SECRET_KEY leída desde .env (agrégala a .env.example sin valor real).
  Si no está definida, la app no debe arrancar con una clave fija.
- Cookie de sesión con SESSION_COOKIE_HTTPONLY=True y
  SESSION_COOKIE_SAMESITE="Lax".
- En login correcto guarda session["username"] y session["role"].
- Nuevos endpoints: GET /api/me -> {"username", "role"} o 401;
  POST /api/logout -> borra la sesión.

ETAPA 3 - Control de acceso (S1, S8)
- Crea decoradores login_required (401) y manager_required (401 sin
  sesión, 403 con rol distinto) y aplícalos con method_decorators de
  Flask-RESTful.
- Requieren login: tarjetas (/api/payment), todas las operaciones de
  reservas (crear, consultar, modificar, verificar disponibilidad,
  cancelar, buscar por tarjeta) y crear reseñas (POST /api/review).
- Requieren manager: /api/reports/*.
- Siguen públicos: login, registro, /api/searchRoom, /api/availability y
  leer reseñas (GET /api/review).
- En todos los endpoints protegidos usa session["username"] e IGNORA el
  username que llegue en la petición. Revisa cada uso de args['username'].

ETAPA 4 - Frontend (mínimo)
- Al cargar la app, llama a /api/me para recuperar el usuario si ya hay
  sesión (hoy se pierde al recargar la página).
- El botón o enlace de salir llama a /api/logout.
- Si una petición responde 401, redirige al login.
- No reescribas el login de Angular; solo lo necesario.

REGLAS
- No modifiques tests/integration/.
- No corrijas otros bugs fuera de este issue. Si ves algo relevante,
  menciónalo al final sin cambiarlo.
- Antes de cada etapa, lista los cambios por archivo y espera mi
  confirmación.

Ya tengo el panorama. Antes de tocar nada, te dejo el estado actual y el plan de la Etapa 1.

Estado actual
Unitarias: pasan las 19.
Integración: fallan 15 de 42.
14 son de test_seguridad.py y fallan por lo que pide el issue.
1 es test_crear_reserva_sobre_fechas_ocupadas_responde_409. Falla con Session backend did not open a session porque la app no tiene SECRET_KEY. Se arreglará sola en la Etapa 2.
Ojo: tests/integration/test_disponibilidad.py tiene cambios tuyos sin commitear (el bloque session_transaction). No lo voy a tocar, solo te aviso que esos cambios están en el árbol de trabajo.
Etapa 1: Contraseñas con hash (S5)
fancyhotel/db/mysqldb.py

Importar generate_password_hash y check_password_hash de werkzeug.security.
En init_db, cambiar password a VARCHAR(255) NOT NULL en los CREATE TABLE de Customer y Manager.
En init_db, justo después de los CREATE TABLE, agregar:

ALTER TABLE Fancy_Hotel.Customer MODIFY password VARCHAR(255) NOT NULL
ALTER TABLE Fancy_Hotel.Manager  MODIFY password VARCHAR(255) NOT NULL
Se puede ejecutar en cada arranque: si la columna ya tiene esa definición, MySQL no cambia nada y no da error.
La primera vez reconstruye la tabla, lo cual es inmediato con tablas tan pequeñas.
En register_user, guardar generate_password_hash(password) en lugar de la clave en texto plano.
Reescribir login:
Toma el prefijo con username[:1].upper(), así un username vacío ya no da IndexError (500).
C busca en Customer y M en Manager. Cualquier otro prefijo devuelve None.
Trae el hash con SELECT password … WHERE username = %(username)s y lo valida con check_password_hash.
Devuelve "customer", "manager" o None.
Los nombres de tabla irán con el esquema Fancy_Hotel. igual que el resto de las consultas. Hoy login es la única que no lo usa.
fancyhotel/seed.py
6. Aplicar generate_password_hash a las contraseñas de CUSTOMERS y MANAGERS al insertarlas. Las constantes siguen en texto plano porque son las claves de desarrollo que se escriben al iniciar sesión.

fancyhotel/api.py: sin cambios en esta etapa. if db.mysqldb.login(...) sigue funcionando porque el rol es un valor verdadero. El rol se guarda en la sesión en la Etapa 2.

Pruebas unitarias: no hace falta cambiar ninguna en esta etapa. Hashear dentro de mysqldb deja intacto el contrato que ve api.py. En la Etapa 2 propondré cambiar mysqldb.login.return_value = True por "customer" en tests/unit/test_app.py, porque ese valor terminará en session["role"].

Efecto que debes saber: los usuarios que ya existen en tu BD local tienen la clave en texto plano y no podrán iniciar sesión, porque check_password_hash devuelve False ante un valor que no es hash. Para arreglarlo hay que volver a ejecutar python fancyhotel/seed.py. No voy a agregar una migración que convierta las claves existentes porque el issue no la pide. Dime si la quieres.

¿Confirmas la Etapa 1 así?

aprobar plan 

Etapa 1 terminada: contraseñas con hash
Arriba está el diff completo de mysqldb.py y seed.py. Hice lo que aprobaste, sin cambios respecto al plan.

Pruebas

Unitarias: pasan las 19 y no tuve que tocar ninguna.
Integración: fallan 14 de 42 (antes fallaban 15).
Ya pasan test_registro_guarda_la_contrasena_con_hash, test_login_correcto, test_login_incorrecto y los reportes con manager.
Las 14 que siguen fallando necesitan sesión o control de acceso, que llegan en las Etapas 2 y 3.
Comprobaciones aparte, contra tu MySQL local

password ya es varchar(255) en Customer y en Manager.

Ejecuté init_db una segunda vez y el ALTER no dio error.

login dio estos resultados:

Entrada	Resultado
CZZZ9 y cZZZ9	"customer"
MZZZ9 y mZZZ9	"manager"
clave incorrecta	None
username "" o None	None (antes daba 500)
prefijo X o usuario inexistente	None
Usé usuarios temporales y los borré al terminar.

Revisé lo que generaría seed sin ejecutarlo, porque vacía tu BD. Las filas salen bien formadas y el hash scrypt mide 162 caracteres, así que cabe en la columna.

Pendiente de tu lado: ejecuta python fancyhotel/seed.py para que los usuarios de desarrollo (Cl3a8, M2acz, …) puedan volver a iniciar sesión. Hoy su clave sigue en texto plano.

Plan de la Etapa 2: sesión en el servidor
fancyhotel/serve.py

Llamar a load_dotenv() de forma explícita. Hoy el .env solo se carga como efecto de importar db, y en las pruebas unitarias db es un mock.
app.secret_key = os.environ.get('SECRET_KEY'). Si falta, lanzar RuntimeError("SECRET_KEY no está definida en .env"), sin ninguna clave de respaldo.
Agregar SESSION_COOKIE_HTTPONLY=True y SESSION_COOKIE_SAMESITE="Lax".
Registrar /api/me y /api/logout.
fancyhotel/api.py
5. En LoginResource, cuando el login es correcto: session.clear() y después guardar session["username"] y session["role"]. Además agrego "role" al JSON de respuesta para usarlo en la Etapa 4.
6. MeResource.get devuelve {"username", "role"}, o 401 si no hay sesión.
7. LogoutResource.post hace session.clear() y devuelve 200.

.env.example
8. Agregar SECRET_KEY= vacía, con un comentario que explique cómo generarla: python -c "import secrets; print(secrets.token_hex(32))".

Tu .env local (no se versiona)
9. No tiene SECRET_KEY. En cuanto aplique la Etapa 2, ni la app ni las pruebas unitarias arrancarán sin ella, porque serve falla al importarse. Propongo agregarte una clave aleatoria con el comando del punto 8. Si prefieres hacerlo tú, me lo dices. No hay CI en .github/, así que esto no rompe ningún pipeline.

tests/unit/test_app.py
10. En test_login_valid_credentials, cambiar mysqldb.login.return_value = True por "customer". Con el contrato nuevo, ese valor va a session["role"], y True ya no es un retorno válido de login.

Efecto esperado: también debería pasar test_crear_reserva_sobre_fechas_ocupadas_responde_409, que hoy falla porque sin secret_key no se puede abrir la sesión de prueba.

Algo a decidir: al aceptar el prefijo en minúscula, quien escriba cl3a8 queda en la sesión como cl3a8 y no como Cl3a8. Las consultas funcionan igual, porque la collation de MySQL no distingue mayúsculas. Lo único que cambia es que el username de las filas nuevas se guarda con lo que escribió el usuario. Lo dejo así, porque login solo debe devolver el rol, salvo que prefieras guardar en la sesión el nombre tal como está en la BD.

¿Confirmas la Etapa 1 y apruebas este plan, incluido el punto 9?

cofnirmado y aprobado 

Etapa 2 terminada: sesión en el servidor
El diff completo está arriba. Hice lo que aprobaste, sin cambios respecto al plan.

Qué quedó

SECRET_KEY obligatoria: sin ella, import serve falla con RuntimeError: SECRET_KEY no está definida en .env. Lo comprobé antes de agregarla a tu .env, tanto con la variable ausente como vacía.
Tu .env: le agregué una SECRET_KEY aleatoria de 64 caracteres hex. No la imprimí y el archivo sigue en .gitignore.
Cookie de sesión: se envía con HttpOnly; Path=/; SameSite=Lax.
Flujo comprobado con un usuario temporal, ya borrado:
el login devuelve 200 y role: "customer"
/api/me devuelve {"username": "CZZZ9", "role": "customer"}
el logout devuelve 200 y borra la cookie
/api/me responde 401 después del logout
Login con username vacío: ahora responde 401 en lugar de 500.
Prueba unitaria modificada: solo test_login_valid_credentials. El mock de login devolvía True y ahora devuelve 'customer', porque ese valor se guarda en session["role"] y el contrato de login es devolver un rol o None.

Pruebas

Unitarias: pasan las 19.
Integración: fallan 10 de 42 (antes 14).
Ya pasa test_crear_reserva_sobre_fechas_ocupadas_responde_409 de disponibilidad.
Las 10 que fallan son tarjetas, reportes y el último assert de logout (/api/payment → 401). Todas dependen del control de acceso de la Etapa 3.
Plan de la Etapa 3: control de acceso (S1, S8)
fancyhotel/api.py: decoradores

login_required: si no hay session["username"], responde {"error": "...", "result": False}, 401.
manager_required: responde 401 sin sesión y 403 si session["role"] != "manager".
Se aplican con method_decorators. Corren antes del método, así que sin sesión se responde 401 antes de validar parámetros y nunca un 400.
Revisión de cada uso de args['username']

En todos los casos quito username del RequestParser, para que lo que mande el cliente se ignore y no sea obligatorio, y en su lugar uso session["username"].

Recurso	Ruta	Decorador	Usos de username que se reemplazan
CreateReservationResource	POST /api/reservation/create	login	insert_reservation
UpdateReservationResource	PUT /api/reservation	login	get_rooms_for_reservation, update_reservation
ReservationResource	GET/PUT /api/reservation/<id>	login	GET: get_reservation. PUT: get_rooms_for_reservation. Sigue roto por B6 y no lo arreglo
UpdateReservationConfirmResource	GET …/<id>/availability	login	get_rooms_for_reservation
CancelReservationResource	GET …/<id>/cancel	login	cancel_reservation. Su parser queda vacío y lo elimino
GetReservationByCardNumberResource	GET /api/reservation/cardNumber	login	get_reservation_by_card_number
CreditCardResource	GET/POST/DELETE /api/payment	login	get_credit_cards, add_credit_card, get_reservation_by_card_number, delete_credit_card. El parser del GET queda vacío y lo elimino
ReviewResource	POST /api/review	login, solo en post ({'post': [...]})	add_review. El GET sigue público
Reservation/PopularRoom/RevenueReportResource	/api/reports/*	manager	(no usan username)
Siguen públicos, sin cambios: login, registro, /api/me, /api/logout, /api/searchRoom y /api/availability.

tests/unit/test_validaciones.py

Todas sus pruebas llaman a endpoints de reservas, que ahora exigen login, así que sin sesión darían 401.
La solución es agregar en ese archivo un fixture que sobrescribe client (def client(client)) y abre sesión como Cl3a8 / customer con session_transaction().
conftest.py no se toca, y las aserciones y los payloads quedan iguales. test_create_reservation_valid sigue esperando 'Cl3a8', que ahora llega desde la sesión.
Frontend: sigue enviando username en las peticiones. Eso no rompe nada porque el servidor lo ignora. Lo limpio en la Etapa 4 solo si hace falta.

Observación, sin cambio: login_required deja pasar a un manager a los endpoints de cliente, porque el issue solo pide exigir sesión. Si un manager intentara reservar o guardar una tarjeta, la FK hacia Customer fallaría con un 500, que ya está registrado como B14.

¿Confirmas la Etapa 2 y apruebas este plan?

Etapa 3 terminada: control de acceso (S1, S8)
Hice lo que aprobaste, sin cambios respecto al plan. El diff completo se ve con git diff fancyhotel/api.py tests/unit/test_validaciones.py.

Cambios en api.py

Agregué login_required y manager_required al principio del archivo, con functools.wraps.
method_decorators = [login_required] en:
CreateReservationResource
UpdateReservationResource
ReservationResource
UpdateReservationConfirmResource
CancelReservationResource
CreditCardResource
GetReservationByCardNumberResource
ReviewResource usa {'post': [login_required]}, así que el GET sigue público.
Los tres reportes usan [manager_required].
Quité username de todos los RequestParser de esos recursos y en todos los casos uso session['username'].
Eliminé los parsers que quedaron vacíos: el de CancelReservationResource, el getreqparse de ReservationResource y el del GET de CreditCardResource.
Con grep comprobé que args['username'] solo queda en registro y login, que es correcto.
Prueba unitaria modificada: en test_validaciones.py agregué un fixture client(client) que sobrescribe al de conftest.py, sin tocarlo, y abre sesión como Cl3a8 / customer. Hacía falta porque todas las pruebas de ese archivo llaman a endpoints de reservas, que sin sesión ahora responden 401. Las aserciones no cambiaron.

Pruebas

Unitarias: pasan las 19.
Integración: pasan las 42.
Comprobación endpoint por endpoint. Usé un mock de la BD y en todas las peticiones envié username=COTRO:

Endpoint	Sin sesión	Con sesión CYO01	Usuario que llega a la BD
POST /reservation/create	401	200	CYO01
PUT /reservation	401	200	CYO01
GET /reservation/7	401	200	CYO01
GET /reservation/7/availability	401	200	CYO01
GET /reservation/7/cancel	401	200	CYO01
GET /reservation/cardNumber	401	200	CYO01
GET, POST y DELETE /payment	401	200	CYO01
POST /review	401	200	CYO01
Sin sesión siguen respondiendo 200 GET /review, /availability, /searchRoom y /register. Además, GET /api/payment sin username en la petición responde 200, porque ese parámetro ya no es obligatorio.

Plan de la Etapa 4: frontend mínimo
Hallazgos en el front:

No existe ningún botón ni enlace para salir.
Cada vista calcula loggedInBool una sola vez, cuando se crea su controlador. Si /api/me responde después de cargar la página, la vista seguiría diciendo "You aren't logged in yet".
fancyhotel/static/js/controllers.js

Restaurar la sesión al recargar: en el .run se inyectan $http, $route y $location, y se llama a GET /api/me.
Si responde 200, se asignan $rootScope.currentUser y $rootScope.userType (este con el role del servidor) y se ejecuta $route.reload(). Así el controlador de la vista actual se vuelve a crear y recalcula loggedInBool.
Si responde 401, no se hace nada y la portada sigue siendo pública.
Salir: $rootScope.logout() hace POST /api/logout, limpia currentUser y userType y redirige a #/.
Redirigir ante 401: un interceptor en .config con $httpProvider.interceptors.
Cuando una respuesta es 401, limpia el usuario y redirige a /login.
No actúa sobre /api/login, donde el 401 significa credenciales incorrectas y ya se muestra la alerta actual, ni sobre /api/me, donde el 401 solo significa que no hay sesión.
Devuelve $q.reject(...) para que los callbacks de error que ya existen sigan funcionando.
fancyhotel/templates/index.html
4. Debajo del título, un enlace "Log out" con ng-show="currentUser" y ng-click="logout()". Lo pongo en el layout para que se vea en todas las vistas, porque no existe ninguno.

Sin cambios

El loginController no se toca.
Las peticiones del front siguen enviando username. El servidor lo ignora, así que quitarlo no es necesario para este issue.
Verificación: no hay pruebas de frontend. Propongo arrancar la app y probar a mano con el test client y peticiones HTTP: que la página sirva el JS sin errores de sintaxis (node --check si tienes Node) y que el flujo login → recarga → /api/me → logout funcione. La interacción en el navegador te tocaría confirmarla a ti, porque no puedo abrir uno desde aquí. Para iniciar sesión con los usuarios de desarrollo primero hay que ejecutar python fancyhotel/seed.py.

¿Confirmas la Etapa 3 y apruebas este plan?

confirmado y procede

Etapa 4 terminada: frontend mínimo
Hice lo que aprobaste, con un solo ajuste. index.html pasa por Jinja (render_template), que se habría comido {{currentUser}} en el servidor, así que el nombre se muestra con ng-bind.

controllers.js

Al cargar la app, el .run llama a GET /api/me. Si hay sesión, restaura currentUser y userType y ejecuta $route.reload().
$rootScope.logout() hace POST /api/logout, limpia el usuario y redirige a #/.
El interceptor authInterceptor manda a #/login ante cualquier 401, salvo los de /api/login y /api/me.
loginController no se tocó.
index.html: debajo del título hay un enlace "Log out", visible solo con sesión.

Pruebas

Unitarias: pasan las 19.
Integración: pasan las 42.
node --check no encuentra errores de sintaxis en el JS.
Prueba en navegador real. Usé Chrome headless con puppeteer-core, instalado en el scratchpad y no en el proyecto, contra la app levantada en el puerto 5099. Ya borré los usuarios temporales y detuve el servidor.

Paso	Resultado
Login de cliente	#/portal, "Hello CZZZ9 !" y "Log out" visible
Recargar #/portal	La sesión se mantiene: "Hello CZZZ9 !" y "You are a customer!"
Borrar la cookie y hacer una petición	401 y redirige a #/login
Pulsar "Log out"	Vuelve a #/ y /api/me responde 401
#/portal después del logout	"You aren't logged in yet"
Login de manager y recargar	Se mantiene, con los 3 enlaces de reportes
El único error en consola fue un 404 de /favicon.ico, que no existe en el proyecto.

Resumen del issue
Toqué 9 archivos: mysqldb.py, seed.py, serve.py, api.py, controllers.js, index.html, .env.example, test_app.py y test_validaciones.py. También agregué SECRET_KEY a tu .env, que no se versiona. No modifiqué tests/integration/ ni conftest.py, y no hice commit.

Pendiente de tu lado: ejecuta python fancyhotel/seed.py. Hasta entonces, los usuarios de desarrollo tienen la clave en texto plano y no pueden iniciar sesión.

Fuera del issue (no lo cambié)
El ALTER de init_db puede bloquear el arranque. Me pasó durante la prueba: con la app corriendo, otro proceso que importa db (pytest de integración o seed.py) se queda esperando un bloqueo. La conexión de la app deja transacciones abiertas después de leer, porque el conector no hace autocommit (relacionado con B4), y esa transacción retiene Customer. Mientras no se corrija, detén la app antes de ejecutar las pruebas de integración o el seed.
La cancelación por GET sigue expuesta a CSRF (S9). Con SameSite=Lax, el navegador envía la cookie cuando el usuario sigue un enlace desde otro sitio. Por eso, ahora que hay sesión, un enlace externo a /api/reservation/<id>/cancel cancelaría la reserva del usuario conectado.
Un manager puede llamar a endpoints de cliente. Al reservar o guardar una tarjeta, la FK hacia Customer falla con un 500 (B14).
El username se guarda tal como se escribe al iniciar sesión. Si alguien entra como cl3a8, las filas nuevas se guardan con ese nombre en lugar de Cl3a8.
Otros pendientes conocidos: ReservationResource.put sigue roto (B6), debug=True sigue escuchando en 0.0.0.0 (S7) y el front todavía envía username aunque el servidor lo ignora.
docs/arquitectura.md quedó desactualizado. Todavía dice VARCHAR(16) en texto plano y "No hay sesión, token ni cookie".
Tu cambio sin commitear en test_disponibilidad.py dice en el docstring "Ejecutar desde fancyhotel/: pytest tests/test_disponibilidad.py". Esa ruta no existe; antes decía python -m pytest tests/integration -v.