mplementa la historia de seguridad (issue #N). Lee docs/arquitectura.md (S1, S5, S8).

Contraseñas con werkzeug.security (generate_password_hash / check_password_hash) para Customer y Manager. Amplía la columna password a VARCHAR(255).
Al hacer login, guarda username y role en flask.session. Agrega POST /api/logout y GET /api/me.
SECRET_KEY desde .env. Cookie de sesión con HttpOnly y SameSite=Lax.
Crea decoradores login_required y manager_required y aplícalos con method_decorators de Flask-RESTful: reservas, tarjetas y reseñas requieren login; /api/reports/* requiere manager.
En los endpoints protegidos, usa el usuario de la sesión e ignora el username que llegue en la petición.
Respuestas: 401 sin sesión, 403 con rol incorrecto.
Actualiza seed.py para guardar las contraseñas con hash.
No modifiques nada fuera de esta historia. Lista los cambios y espera mi confirmación.


No he modificado nada todavía. Encontré cuatro cosas que bloquean el trabajo y necesito que las decidas antes de empezar. Debajo va la lista de cambios propuesta.

Lo que bloquea
La migración a Python 3 no está hecha. Estás en chore/migracion-python3, pero esa rama no tiene commits nuevos respecto a main. El código sigue siendo Python 2 (print sin paréntesis y el TabError en mysqldb.py:374), así que con el venv (Python 3.12, Flask 3.1, Werkzeug 3.1) no arranca y no podría probar nada. Según D-01, la migración va antes que la seguridad.
seed.py no existe en el repo, y ninguna rama lo tiene.
No hay soporte para .env. python-dotenv no está instalado, no hay requirements.txt y no hay .gitignore en la raíz, así que un .env se subiría al repo.
Número de issue: el texto dice #N. ¿Cuál es el número real?
Cambios propuestos
Nuevo fancyhotel/auth.py

login_required: devuelve 401 si session no tiene username.
manager_required: devuelve 401 si no hay sesión y 403 si role != 'manager'.
fancyhotel/serve.py

Cargar .env y leer SECRET_KEY. Si falta, la app no arranca, para no caer en una clave por defecto.
Configurar SESSION_COOKIE_HTTPONLY=True y SESSION_COOKIE_SAMESITE='Lax'.
Registrar POST /api/logout y GET /api/me.
fancyhotel/api.py

LoginResource: si el login es correcto, limpiar la sesión y guardar username y role (customer o manager). Limpiar primero evita la fijación de sesión.
LogoutResource: borra la sesión.
MeResource: devuelve {username, role}, o 401 si no hay sesión.
method_decorators = [login_required] en todos los recursos de reserva (crear, actualizar, detalle, availability, cancelar, cardNumber), en CreditCardResource y en ReviewResource.
method_decorators = [manager_required] en los tres /api/reports/*.
En esos recursos, quitar username de los reqparse y usar session['username']. Lo que mande el cliente en username se ignora, así que el frontend sigue funcionando sin cambios.
fancyhotel/db/mysqldb.py

password VARCHAR(255) en el CREATE TABLE de Customer y Manager.
Un ALTER TABLE ... MODIFY password VARCHAR(255) NOT NULL en init_db para las bases que ya existen, porque CREATE TABLE IF NOT EXISTS no cambia una tabla ya creada.
register_user: guardar generate_password_hash(password).
login: buscar el hash por username y comprobarlo con check_password_hash, en lugar de comparar en el SQL.
seed.py (nuevo): Customer y Manager de prueba con las contraseñas ya hasheadas.

Archivos de soporte: .env.example con SECRET_KEY=, .gitignore con .env, y python-dotenv en las dependencias.

Puntos que conviene saber
Las contraseñas en texto plano que ya estén en la base dejarán de servir. Hay que volver a cargar el seed o registrar los usuarios de nuevo.
Tal como lo pediste, GET /api/review (leer reseñas) también exigirá login. Si quieres que leer sea público y solo crear requiera sesión, Flask-RESTful permite aplicar el decorador por método.
/api/searchRoom, /api/login y /api/register quedan públicos.
Secure no se activa en la cookie, porque en local se usa http.
El frontend no tendrá botón de cerrar sesión. Lo dejo fuera por tu indicación de no tocar nada fuera de la historia.
No corrijo B12 (un username vacío provoca un error 500 en el login), porque está fuera del alcance.
Necesito que confirmes
Rama base: ¿hago antes la migración a Python 3 en chore/migracion-python3, o ya existe en otra parte y me la pasas? Después crearía feat/seguridad-sesion-roles a partir de ella.
seed.py: ¿lo creo yo? Propongo ponerlo en fancyhotel/seed.py. Dime también qué usuarios de prueba quieres; los nombres deben tener 5 caracteres y empezar por C o M.
.env: ¿agrego python-dotenv, .env.example y .gitignore?
Número de issue.

Abrí el PR de la migración: https://github.com/JacquesMartinez/hotel-reservas-ia/pull/22. Cierra el issue #3. La app corre con Python 3.12 y las 6 pruebas pasan, pero falta ejecutar seed.py contra MySQL: el permiso automático lo bloqueó porque el script vacía las tablas antes de insertar.

Qué incluye el PR

Python 3: corregí los print, el TabError y la consulta a customer en minúscula (B13).
Error que no estaba en el análisis: con Flask 3, todos los GET respondían 415, porque reqparse busca JSON por defecto. Los parámetros de GET y DELETE ahora se leen de la URL. Lo detectó una de las pruebas.
Configuración: python-dotenv, .env.example, .gitignore y requirements.txt con versiones fijas. El usuario y la contraseña de MySQL ya no están en el código. Agregué PORT al .env porque en macOS el puerto 5000 lo ocupa AirPlay.
fancyhotel/seed.py: 30 habitaciones en las 5 sedes del frontend, 1 manager (M2acz / manager123) y 4 clientes (Cl3a8, Cyp7d, C196b, Cm2wd / cliente123), cada cliente con una tarjeta de prueba. También crea reservas de los últimos 12 meses sin solapamientos. Las contraseñas siguen en texto plano; pasarlas a hash es parte del issue #5.
Pruebas y README: pytest con la base de datos simulada, así que no necesita MySQL, y un README con los pasos reales de instalación.
Lo que hice sin que lo pidieras

Quité venv/ del repositorio. Se había subido por error en el commit 87256f7 (97 MB, rutas que solo existen en tu Mac). Tu carpeta local sigue ahí. Cuando tus compañeros actualicen main después del merge, git les borrará su venv/ y tendrán que recrearlo con pip install -r requirements.txt. Lo avisé en el PR.
Creé un .env local con root/password y PORT=5050. No se sube al repositorio.
Registré un usuario de prueba, Csmk1, en la base Fancy_Hotel mientras probaba contra MySQL. Se borra al ejecutar el seed.
Lo que te toca hacer

Ejecutar el seed: python fancyhotel/seed.py. La base Fancy_Hotel no existía antes de esta sesión, así que solo borra el usuario de prueba.
Completar el PR: en "Uso de IA" faltan "Qué modificamos a mano" y "Qué rechazamos", y en "Roles" faltan los nombres.
No incluí tus cambios en docs/decisiones.md ni en docs/IA_evidencias/evidencias_P2; siguen sin commit en tu copia local.

Cuando aprueben el PR #22, sigo con el issue #5 (seguridad) en una rama feat/seguridad-sesion-roles creada desde main, con el plan que ya revisamos.