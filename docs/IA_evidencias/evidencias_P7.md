Implementa completo el issue #8 "Confirmación de reserva por correo".

CONTEXTO
- Lee el docstring de tests/integration/test_correo.py: define el
  contrato exacto.
- Las pruebas de integración no se modifican y deben pasar todas:
    python -m pytest tests/integration -v
- Las unitarias también deben pasar (puedes ajustarlas explicando por
  qué, sin tocar tests/unit/conftest.py):
    python -m pytest -v
- La sesión y la creación de reservas con card_token ya existen.

CAMBIOS
1. Crea fancyhotel/correo.py con una función que arme y envíe el correo
   de confirmación.
   - Usa "import smtplib" y llama a smtplib.SMTP (no "from smtplib
     import SMTP"), para que las pruebas puedan reemplazarlo.
   - Lee MAIL_MODE, MAIL_HOST, MAIL_PORT, MAIL_FROM, MAIL_USER y
     MAIL_PASSWORD de variables de entorno en el momento del envío, no
     al importar. MAIL_MODE por defecto: "console" (imprime el correo,
     sin conexión SMTP).
   - Si MAIL_USER está definido, hace login antes de enviar.
   - El correo va al email del cliente (tabla Customer) e incluye número
     de reserva, fechas YYYY-MM-DD, sede y número de cada habitación, y
     el total.
   - Cualquier excepción del envío se captura y se registra con logging
     a nivel ERROR, sin incluir contraseñas. Nunca debe hacer fallar la
     reserva.
2. En CreateReservationResource, envía el correo solo después de que la
   reserva se creó correctamente. Si la respuesta es 400, 403 o 409, no
   se envía nada.
3. Agrega las variables MAIL_* a .env.example sin valores reales.
4. Documenta en el README cómo ver los correos en desarrollo con Mailpit:
   docker run -d -p 1025:1025 -p 8025:8025 axllent/mailpit
   con MAIL_MODE=smtp, MAIL_HOST=localhost y MAIL_PORT=1025; la bandeja
   se ve en http://localhost:8025

REGLAS
- No modifiques tests/integration/.
- No corrijas otros bugs fuera de este issue; menciónalos al final.
- Antes de aplicar, lista todos los cambios por archivo y espera mi
  confirmación. Al terminar, ejecuta ambas suites y muéstrame el
  resultado.

  Ya revisé el código y no he cambiado nada todavía. Aquí está el plan; espero tu confirmación antes de aplicarlo.

Punto de partida
Unitarias: pasan las 53.
Integración: pasan 70 y fallan 4, todas en test_correo.py, como era de esperar.
Cambios sin confirmar que no son míos: el árbol de trabajo tiene cambios en api.py, mysqldb.py y controllers.js. Son del registro: límites de longitud, ALTER de la tabla Customer y el re-hash de contraseñas. No pertenecen a este issue y no los voy a tocar. Mis cambios caen en dos de esos archivos, así que conviene que hagas el commit por separado (por ejemplo con git add -p).
Cambios por archivo
1. fancyhotel/correo.py (nuevo)

Usa import smtplib, import os, import logging, EmailMessage e import db.
Tiene una función send_reservation_confirmation(username, reservation_id, checkin, checkout, rooms, total). Todo su cuerpo va dentro de un try/except Exception:
Busca el email con db.mysqldb.get_customer_email(username). Si no lo encuentra, lanza un error, que se registra.
Arma el correo con el número de reserva, las fechas YYYY-MM-DD, una línea por habitación con sede y número (más "extra bed" si aplica) y el total con formato $200.00.
Lee MAIL_* dentro de la función, al momento del envío, nunca al importar.
Con MAIL_MODE=console (el valor por defecto) solo hace print del correo y no abre conexión.
Con smtp abre with smtplib.SMTP(host, port, timeout=10). Hace login solo si MAIL_USER no está vacío, y luego send_message.
Un modo desconocido lanza ValueError, que se registra como error.
Por defecto usa localhost, el puerto 25 y no-reply@fancyhotel.local como remitente.
Los fallos se registran con logger.error(...) con el id de la reserva y el tipo y mensaje de la excepción. No incluyen traceback ni variables, así que la contraseña nunca llega al log.
Los identificadores y comentarios van en inglés y el texto del correo también, para que coincidan con el resto del código y con la interfaz, que está en inglés.
2. fancyhotel/db/mysqldb.py

Agrego un método nuevo, get_customer_email(username), con un SELECT email FROM Fancy_Hotel.Customer. Devuelve el email o None y sigue el estilo de get_room_prices.
3. fancyhotel/api.py

Agrego import correo.
En CreateReservationResource.post llamo a correo.send_reservation_confirmation(...) solo después del if not result: return ... 400, justo antes del return exitoso. Los caminos que devuelven 400, 403 y 409 terminan antes, así que no envían nada.
4. .env.example

Agrego un bloque comentado con MAIL_MODE=console, MAIL_HOST=localhost, MAIL_PORT=1025, MAIL_FROM=reservas@fancyhotel.local y MAIL_USER=/MAIL_PASSWORD= vacíos.
5. README.md

Agrego las filas MAIL_* a la tabla de variables.
Agrego una sección nueva, "Correos en desarrollo (Mailpit)", con el docker run, la configuración MAIL_MODE=smtp, MAIL_HOST=localhost y MAIL_PORT=1025, y la bandeja en http://localhost:8025.
6. tests/unit/test_envio_correo.py (nuevo)

No cambio las pruebas unitarias que ya existen: siguen pasando porque en modo console solo se imprime.
Agrego pruebas sin MySQL:
el modo console no usa SMTP;
con MAIL_USER se llama a login;
un fallo se registra como ERROR y no aparece la contraseña;
el endpoint envía el correo con 200 y no lo envía con 409.
No lo llamo test_correo.py porque ese nombre choca con el de integración si alguien corre pytest tests.
Decisiones que puedes cambiar
El correo se envía de forma síncrona, así que en el peor caso la respuesta tarda hasta 10 s (el timeout).
No hay STARTTLS porque la especificación pide solo login. Mailpit no lo necesita, pero un SMTP real como Gmail en el puerto 587 sí. Se podría agregar después con una variable MAIL_TLS.
¿Lo aplico así?

Se aplica asi

El issue #8 quedó implementado como lo planeamos y las dos suites pasan. No hice commit.

Resultados
Suite	Antes	Ahora
python -m pytest -v (unitarias)	53 pasan	62 pasan
python -m pytest tests/integration -v	70 pasan, 4 fallan	74 pasan, incluidas las 6 de test_correo.py
No toqué tests/integration/ ni las unitarias existentes; las 9 unitarias nuevas están en un archivo aparte.

Qué cambió
correo.py (nuevo):
send_reservation_confirmation(...) busca el email del cliente, arma el correo y lo imprime (modo console) o lo envía con smtplib.SMTP (modo smtp).
Lee las MAIL_* en cada envío.
Solo hace login si MAIL_USER tiene valor.
Cualquier fallo se registra a nivel ERROR con el tipo y el mensaje del error, sin traceback, así que la contraseña no aparece en el log.
mysqldb.py: método nuevo get_customer_email(username).
api.py: el correo se envía justo antes del return exitoso de CreateReservationResource.post. Las respuestas 400, 403 y 409 salen antes y no envían nada.
.env.example: bloque MAIL_* comentado, con MAIL_USER y MAIL_PASSWORD vacíos.
README.md: las MAIL_* en la tabla de variables y una sección nueva, "Correos en desarrollo (Mailpit)".
test_envio_correo.py (nuevo), sin MySQL, cubre:
console por defecto y sin SMTP;
envío sin login, y login cuando hay MAIL_USER;
fallo registrado sin la contraseña;
modo desconocido;
un correo cuando la reserva sale con 200, y ninguno con 403, 409 o 400.
Antes de hacer el commit
api.py, mysqldb.py y controllers.js ya traían cambios sin confirmar del registro (límites de longitud, ALTER de Customer, re-hash de contraseñas). No los toqué, pero en api.py y mysqldb.py están mezclados con los míos. Usa git add -p para que el commit de este issue lleve solo el correo.

Otros bugs que vi y no corregí
ReservationResource.put (api.py:288) tiene tres errores:
usa deltaDays sin definirlo, así que falla con NameError;
total_cost + room[...] no asigna el resultado;
llama a update_reservation sin username.
UpdateReservationResource.put compara extra_bed_or_not == '1' con un string, así que la cama extra nunca se cobra al modificar una reserva. Además le quedan print() de depuración.
insert_reservation: si falla la inserción de una habitación, devuelve el error sin rollback. La fila de Reservation queda en la transacción abierta y el siguiente commit puede guardarla. Además, entre is_room_free y el insert no hay bloqueo, así que dos reservas simultáneas pueden quedarse con la misma habitación.
Mensajes de ayuda equivocados en ReviewResource (el comentario pide un "card_number") y en LoginResource (la contraseña dice "Email is required"). ReviewResource.__init__ tampoco llama a super().
README, sección Pruebas: menciona tests/conftest.py, pero el archivo es tests/unit/conftest.py, y no explica cómo correr las de integración.
Límites conocidos
El envío es síncrono: si el servidor SMTP no responde, la reserva puede tardar hasta 10 s en responder.
No hay STARTTLS. Mailpit funciona así, pero un SMTP real como Gmail en el puerto 587 lo necesita.