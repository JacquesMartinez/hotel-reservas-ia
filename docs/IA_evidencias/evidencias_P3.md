Vas a implementar el issue #N "Calendario dinámico de disponibilidad".

CONTEXTO
- Lee primero docs/arquitectura.md (bugs B1 y B2) y
  tests/integration/test_disponibilidad.py.
- Las pruebas de integración definen el comportamiento esperado.
  Hoy fallan 11 de 22. El objetivo es que pasen las 22 SIN modificar
  el archivo de pruebas.
- Las pruebas unitarias (tests/unit/) usan un conftest.py que reemplaza
  el módulo db por un mock. No lo modifiques.
- Comandos:
    Integración: python -m pytest tests/integration -v
    Unitarias:   python -m pytest -v
- Decisión del equipo (D-06): una noche está ocupada cuando no queda
  ninguna habitación libre del tipo elegido en la sede.

TRABAJA POR ETAPAS. Al terminar cada etapa, detente, muéstrame el diff,
ejecuta las pruebas y espera mi confirmación antes de seguir.

ETAPA 1 - Corregir solapamiento (bug B1)
En db/mysqldb.py, en search_rooms e is_room_free, una reserva se solapa
con el rango [entrada, salida) si:
    res.checkin_date < salida AND res.checkout_date > entrada
Mantén la exclusión de reservas canceladas.
Resultado esperado: pasan los 8 casos de test_is_room_free_detecta_solapamiento
y los 8 de test_busqueda_excluye_habitaciones_ocupadas.

ETAPA 2 - Nuevo endpoint GET /api/availability
- Parámetros por query string (usa location='args' en reqparse):
  location, type, from, to (fechas YYYY-MM-DD).
- Respuesta: {"occupied": ["YYYY-MM-DD", ...]}
- Una noche d está ocupada por una reserva si checkin <= d < checkout.
- Devuelve una noche solo si TODAS las habitaciones de ese tipo en la
  sede están ocupadas esa noche.
- Usa una sola consulta SQL para traer las reservas del periodo; no una
  consulta por día.
- La consulta va en db/mysqldb.py, el recurso en api.py y la ruta en
  serve.py, siguiendo el estilo existente.
Resultado esperado: pasan las 4 pruebas test_availability_*.

ETAPA 3 - Revalidar disponibilidad al crear la reserva (bug B2)
En CreateReservationResource, antes de insertar, verifica con
is_room_free cada habitación (usa -1 como reserva a excluir). Si alguna
no está libre, responde 409 con un mensaje claro y no crees nada.
Resultado esperado: pasan las 22 pruebas de integración y todas las
unitarias.

ETAPA 4 - Frontend (searchRoom.html y controllers.js)
- Agrega un selector de tipo de habitación: Standard, Family, Suite.
- Al cambiar sede o tipo, llama a /api/availability para los próximos
  6 meses.
- El datetimepicker es Eonasdan bootstrap-datetimepicker v4. Usa su
  opción disabledDates en el picker de entrada.
- Al elegir la fecha de entrada, fija maxDate del picker de salida en la
  primera noche ocupada posterior a la entrada. El día de salida SÍ
  puede coincidir con una noche ocupada.
- Las fechas deben coincidir exactamente con las de la BD: cuidado con
  conversiones de zona horaria de moment.
- Usa el mismo estilo de AngularJS 1.4 del archivo; no agregues librerías.

REGLAS
- No modifiques tests/integration/test_disponibilidad.py ni tests/unit/conftest.py.
- No corrijas otros bugs ni cambies nada fuera de este issue, aunque los
  veas. Si encuentras algo relevante, menciónalo al final sin cambiarlo.
- Antes de cada etapa, lista los cambios por archivo y espera mi
  confirmación.

Ya leí todo. Así está el punto de partida:

Integración: fallan 11 y pasan 11, como dijiste. Las 11 que fallan son 6 de B1, las 4 de availability y la del 409.
Unitarias: pasan las 6.
Antes de empezar, un tema de git: estás en main con cambios sin commitear. Son la reorganización de tests/ en unit/ + integration/ y un cambio en pytest.ini. Ya existe una rama local feature/calendario-disponibilidad, pero está desactualizada: apunta al merge #2, antes de la migración a Python 3. Le falta seed.py, requirements.txt, etc. Por ahora voy a trabajar en el árbol actual, sin crear ramas ni hacer commits. Si prefieres otra cosa, dime en qué rama trabajo (por ejemplo, recrear feature/calendario-disponibilidad desde main).

Etapa 1: cambios propuestos (bug B1)
fancyhotel/db/mysqldb.py es el único archivo que cambia:

search_rooms (línea 223): reemplazo la condición de la subconsulta. La exclusión de canceladas y el filtro por sede no cambian.

- WHERE res.checkin_date >= %(checkinDate)s AND res.checkout_date <= %(checkoutDate)s AND res.cancelled_or_not = 0
+ WHERE res.checkin_date < %(checkoutDate)s AND res.checkout_date > %(checkinDate)s AND res.cancelled_or_not = 0
is_room_free (líneas 416-417): el mismo cambio. Se mantienen cancelled_or_not = 0 y reservation_id != exclude_reservation.

- AND res.checkin_date >= %(checkinDate)s
- AND res.checkout_date <= %(checkoutDate)s
+ AND res.checkin_date < %(checkoutDate)s
+ AND res.checkout_date > %(checkinDate)s
No toco nada más: ni los parámetros, ni los print, ni el formato de la respuesta.

Resultado esperado: pasan los 8 casos de test_is_room_free_detecta_solapamiento y los 8 de test_busqueda_excluye_habitaciones_ocupadas. Deberían quedar 5 fallas: las 4 de availability y la del 409. Las unitarias siguen en verde.

¿Confirmas la Etapa 1 (y dónde trabajo en git)?


Etapa 1 completada (bug B1)
Cambié fancyhotel/db/mysqldb.py, que es lo único modificado en fancyhotel/:


@@ search_rooms
-  WHERE res.checkin_date >= %(checkinDate)s AND res.checkout_date <= %(checkoutDate)s AND res.cancelled_or_not = 0
+  WHERE res.checkin_date < %(checkoutDate)s AND res.checkout_date > %(checkinDate)s AND res.cancelled_or_not = 0
@@ is_room_free
-  AND res.checkin_date >= %(checkinDate)s
-  AND res.checkout_date <= %(checkoutDate)s
+  AND res.checkin_date < %(checkoutDate)s
+  AND res.checkout_date > %(checkinDate)s
Pruebas:

Integración: pasan 17 y fallan 5. Pasan los 8 casos de test_is_room_free_detecta_solapamiento, los 8 de test_busqueda_excluye_habitaciones_ocupadas y test_reserva_cancelada_no_ocupa. Siguen fallando, como se esperaba, las 4 de availability y la del 409.
Unitarias: pasan las 6.
Git: cambié a feature/calendario-disponibilidad. Primero la actualicé para que quedara igual que main (691082e). Eso fue seguro porque no tenía commits propios y no existe en el remoto. Tus cambios sin commitear siguen intactos y no hice ningún commit.

Tomé tu "2 procede" como respuesta a la pregunta de git, no como permiso para implementar la Etapa 2. Esta es la lista de cambios propuesta:

Etapa 2: cambios propuestos (GET /api/availability)
fancyhotel/db/mysqldb.py: un método nuevo, get_occupied_nights(self, location, room_type, from_date, to_date).

Hace una consulta para saber cuántas habitaciones del tipo hay en la sede: SELECT COUNT(*) FROM Room WHERE location AND type.
Hace una sola consulta para traer las reservas del periodo. Une Room con Reserves_Extra_Bed y Reservation, filtra por sede y tipo, excluye las canceladas y se queda con las que se solapan con el periodo (checkin_date <= to AND checkout_date > from). Devuelve (room_number, checkin_date, checkout_date).
Luego, en Python, recorre cada noche d del periodo y junta las habitaciones distintas con checkin <= d < checkout. La noche queda ocupada si ese número llega al total de habitaciones (regla D-06).
Devuelve la lista ordenada de fechas en formato YYYY-MM-DD.
fancyhotel/api.py: un recurso nuevo, AvailabilityResource, al estilo de SearchRoomsResource.

Usa reqparse con location, type, from y to, todos required=True y location='args'.
Si alguna fecha no tiene el formato YYYY-MM-DD, o si from > to, responde 400 con {"message": ..., "result": False}.
Si todo está bien, responde {"occupied": [...]}.
fancyhotel/serve.py: una línea nueva, api.add_resource(restapi.AvailabilityResource, '/api/availability').

Son dos consultas en total (el conteo de habitaciones y las reservas), ninguna por día.

Necesito que decidas dos puntos:

¿to cuenta como última noche del periodo? Mi propuesta es que sí: el periodo va de from a to, ambos incluidos.
¿Qué pasa si la sede no tiene habitaciones de ese tipo? Aplicando D-06 al pie de la letra, todas las noches estarían ocupadas, porque no queda ninguna libre. La alternativa es devolver []. Recomiendo aplicar D-06 tal cual, para que el calendario no ofrezca fechas que no se pueden reservar.
Resultado esperado: pasan las 4 pruebas test_availability_*, para un total de 21/22. Las unitarias siguen en verde.

¿Confirmas la Etapa 2 y esos dos puntos?


Etapa 2 completada (GET /api/availability)
Tus dos decisiones quedaron aplicadas: to cuenta como última noche, y si la sede no tiene habitaciones de ese tipo la respuesta es [] (está en una sola línea, if total_rooms == 0: return [], por si después cambian de idea).

Cambios (diff completo arriba):

fancyhotel/db/mysqldb.py: get_occupied_nights() cuenta las habitaciones del tipo, trae las reservas del periodo con una sola consulta (sin las canceladas) y, en Python, marca cada noche en que el número de habitaciones distintas ocupadas llega al total.
fancyhotel/api.py: AvailabilityResource lee location, type, from y to con location='args' y responde 400 si una fecha no tiene el formato correcto o si from > to.
fancyhotel/serve.py: agregué la ruta /api/availability.
Pruebas:

Integración: pasan 21 y falla 1, la del 409, que corresponde a la Etapa 3.
Unitarias: pasan las 6.
Verificación aparte: el escenario de las pruebas tiene una sola habitación, así que no revisa la regla de "todas las habitaciones ocupadas". La probé con un script temporal contra la BD local, con una sede descartable que se borra al final:

Caso	Resultado
2 habitaciones Family: hab. 1 ocupada las noches 1–4, hab. 2 las noches 3–7	["…-03", "…-04"] (solo las noches sin ninguna libre)
to = noche 3	["…-03"] (to cuenta)
Tipo que la sede no tiene	[]
Fecha mal formada, from > to o falta un parámetro	400
Etapa 3: cambios propuestos (bug B2)
fancyhotel/api.py es el único archivo que cambia, en CreateReservationResource.post.

Justo después de parse_args(), antes de calcular el costo e insertar, recorro json_body['rooms'] y llamo a db.mysqldb.is_room_free(room['room_number'], room['location'], args['checkIn'], args['checkOut'], -1) para cada habitación. Si alguna no está libre, respondo:


return {"message": "Room 901 in Testville is no longer available for the selected dates", "result": False}, 409
El mensaje usa el número y la sede de la habitación que falló, y no se inserta nada. El resto del método (cálculo del costo, insert_reservation y respuestas) no cambia.

Resultado esperado: pasan las 22 de integración y las 6 unitarias. En las unitarias, el mock de is_room_free devuelve un MagicMock, que Python toma como verdadero, y ninguna prueba unitaria toca la creación de reservas.

Aviso desde ya: la revalidación cierra el caso del issue, pero no evita una carrera entre dos solicitudes simultáneas. Para eso hace falta bloqueo o transacción, que se relaciona con B3 y B4. No lo voy a tocar y lo anotaré en las observaciones finales.

¿Confirmas la Etapa 3?

Etapa 3 completada (bug B2)
Diff (fancyhotel/api.py, en CreateReservationResource.post):


 		args = self.reqparse.parse_args()
 		json_body = request.json
-		
+
+		#the rooms may have been booked since the search, so check again before inserting anything
+		for room in json_body['rooms']:
+			if not db.mysqldb.is_room_free(room['room_number'], room['location'], args['checkIn'], args['checkOut'], -1):
+				return {"message": "Room %s in %s is no longer available for the selected dates" % (room['room_number'], room['location']), "result": False}, 409
+
 		total_cost = 0
Pruebas:

Integración: pasan las 22.
Unitarias: pasan las 6.
Verificación aparte: la prueba solo mira el código 409, así que revisé con otro script temporal lo que no cubre. Usé una sede descartable que se borra al terminar:

Caso	Resultado	Reservas en BD
Habitación libre	200, result: true	1 (se crea, como antes)
Dos habitaciones, solo la segunda ocupada	409, "Room 1 in Scratchvl is no longer available…"	sigue en 1 (no se insertó nada)
Entrar el mismo día en que sale la reserva anterior	200	2 (la regla [entrada, salida) se respeta)
Etapa 4: cambios propuestos (frontend)
Lo que encontré al revisar el frontend y que condiciona el diseño:

reservationController atiende varias vistas (búsqueda, modificar y cancelar). La carga de disponibilidad solo debe correr si existe #startDatePicker.
En v4, minDate() y maxDate() lanzan una excepción si quedan cruzados. Por eso, al cambiar la entrada, el orden tiene que ser: primero maxDate(false), después el minDate(e.date) que ya existe y al final el maxDate nuevo.
disabledDates() no mueve la fecha ya elegida. Si la entrada seleccionada (hoy, por defecto) queda en una noche ocupada, hay que limpiarla a mano.
Zona horaria: la librería convierte los strings con el formato del picker (YYYY-MM-DD, hora local), así que no se corren de día. El riesgo está en new Date("YYYY-MM-DD") o moment.utc, que interpretan la fecha como UTC y en América la mueven al día anterior. No voy a usar ninguno de los dos: toda fecha se crea con moment(d, 'YYYY-MM-DD') y se compara como string YYYY-MM-DD.
fancyhotel/static/views/searchRoom.html:

Agrego un <select ng-model="roomType" ng-change="loadAvailability()"> con Standard, Family y Suite, después de Location y con el mismo formato.
Agrego ng-change="loadAvailability()" al <select> de Location existente. Es el único cambio a ese elemento.
fancyhotel/static/js/controllers.js:

reservationFactory: una acción nueva, GetAvailability: {method: 'GET', url: '/api/availability'}.
reservationController:
$scope.roomType = "Standard" junto a $scope.location = "Atlanta".
var occupiedNights = [].
$scope.loadAvailability() pide from = hoy y to = hoy + 6 meses, ambos con moment().format('YYYY-MM-DD').
Usa un contador para descartar respuestas viejas si el usuario cambia sede o tipo rápido.
Con la respuesta: aplica disabledDates(...) en #startDatePicker, limpia la entrada si cayó en una noche ocupada y vuelve a calcular el límite de salida.
Si la llamada falla, solo hace console.log, como el resto del archivo. El backend ya responde 409.
Una función auxiliar, limitCheckOut(checkIn):
Hace maxDate(false) y luego minDate(checkIn).
Busca la primera noche ocupada estrictamente posterior a la entrada y la fija como maxDate del picker de salida. Así la salida puede caer ese mismo día, pero no después. Si no hay ninguna, el límite queda abierto.
El handler dp.change de #startDatePicker llama a limitCheckOut(e.date) en vez de minDate(e.date) directamente.
Al final, una llamada inicial a loadAvailability(), protegida con if ($("#startDatePicker").length).
No agrego librerías ni toco las vistas de modificar o cancelar.

Decide un punto antes de que siga: /api/searchRoom devuelve habitaciones de todos los tipos. Con el selector, la tabla de resultados podría mostrar tipos distintos al que guio el calendario. ¿Filtro los resultados por el tipo elegido? Sería agregar | filter:{room_type: roomType}:true al ng-repeat. Por defecto no lo hago, para no cambiar el comportamiento de la búsqueda fuera de lo que pide el issue.

Algo a tener en cuenta: después de 6 meses no se bloquea ninguna fecha, porque el endpoint solo se consulta para ese periodo. Una reserva en esas fechas igual queda protegida por el 409 de la Etapa 3.

¿Confirmas la Etapa 4 y lo del filtro de resultados?

Terminé la Etapa 4, con lo que el issue #4 queda implementado: pasan las 22 pruebas de integración y las 6 unitarias.

Sobre el filtro: no lo pediste, así que no filtré la tabla de resultados por tipo. La búsqueda sigue mostrando todos los tipos.

Etapa 4: frontend
El diff completo está en la salida de arriba. Cambié dos archivos:

fancyhotel/static/views/searchRoom.html: agregué un selector "Room Type" (Standard, Family, Suite). Tanto ese selector como el de sede vuelven a pedir la disponibilidad al cambiar.
fancyhotel/static/js/controllers.js:
Al abrir la búsqueda, y cada vez que cambian sede o tipo, se llama a /api/availability para los próximos 6 meses.
Las noches ocupadas se bloquean en el calendario de entrada con disabledDates.
Al elegir la entrada, la salida queda limitada a la primera noche ocupada posterior. Salir justo ese día sí se permite.
Si la entrada que estaba elegida queda en una noche ocupada, se borra.
Si llegan respuestas viejas porque el usuario cambió la sede rápido, se ignoran.
Las vistas de modificar y cancelar usan el mismo controlador y no hacen esta llamada.
Para evitar desfases de un día por zona horaria, cada fecha se lee con formato explícito (moment(d, 'YYYY-MM-DD')) y se compara como texto.
Prueba en el navegador. Las pruebas de pytest no cubren el frontend, así que levanté la app y la probé en Chromium. Las respuestas de login y de disponibilidad fueron simuladas, así que no escribí nada en tu BD. Corrí la prueba en 4 zonas horarias, de UTC−11 a UTC+14, y pasó en todas:

Se marcan como ocupadas exactamente las noches correctas, sin correrse un día.
El límite de salida queda en la primera noche ocupada y ese día se puede elegir.
Cambiar la entrada hacia atrás no rompe el calendario.
Al pasar a un tipo cuya noche de hoy está ocupada, la entrada se borra.
Se descarta la respuesta vieja cuando se cambia de sede rápido.
Hubo dos fallas en la primera corrida, pero eran del script de prueba, no de la app. El script está en /private/tmp/claude-502/-Users-anaisabelpm-Documents-topicos/ef024018-5cfe-4595-ab87-2ab57f0d5bfd/scratchpad/e2e/calendar.js.

Git: todo está en feature/calendario-disponibilidad, sin commits. docs/respuestas-incorrectas.md aparece modificado, pero no lo toqué yo. Tampoco toqué test_disponibilidad.py ni tests/unit/conftest.py.

Lo que vi y no cambié
Dos reservas al mismo tiempo pueden pasar ambas. La nueva verificación al crear una reserva se hace por separado del guardado, sin bloqueo ni transacción, así que dos pedidos simultáneos por la misma habitación pueden pasar los dos. Se relaciona con B3/B4.
Se pueden crear reservas de 0 noches (B5). El calendario de salida deja elegir el mismo día de la entrada, y el servidor no valida fechas. Con entrada igual a salida, la habitación siempre aparece libre.
Para pasar la entrada a una fecha posterior a la salida actual, primero hay que mover la salida. Cada cambio de la salida fija el límite máximo de la entrada (código existente). Con fechas bloqueadas esto se nota más.
No hay fechas bloqueadas más allá de 6 meses. Una reserva en esas fechas igual la frena el 409.
Con un tipo que la sede no tiene, el calendario queda abierto. Es consecuencia de devolver [], como decidiste.
/api/reservation/create puede devolver un error 500. Pasa si una habitación llega sin location o room_number, o si las fechas vienen mal formadas.
El docstring de test_disponibilidad.py tiene una ruta vieja. Dice que se ejecuta con pytest tests/test_disponibilidad.py; la ruta actual es tests/integration/.


1 - rechazada dejalo asi , rechazada 2 - aprovada , estructura que no se pueda reservar 0 noches  3 dejalo asi rechazada  4 rechazada si ya es frenada 5 corrige para que el calendario funcione correctamente 6 coloca un arreglo para que se indique si hay error al colocar una fecha incorrecta oi que provoque que vaya mal formada, o evitar que llegue sin location 7 actualiza la ruta actual.

Apliqué los cuatro puntos que aprobaste (2, 5, 6 y 7) y dejé el resto como estaba. Pasan las 22 pruebas de integración y las 6 unitarias, y repetí la prueba en el navegador en 4 zonas horarias (de UTC−11 a UTC+14), con 26 casos correctos en cada una.

Punto 2, ya no se puede reservar 0 noches:

Servidor (fancyhotel/api.py): si la salida no es al menos un día después de la entrada, la reserva se rechaza con error 400.
Calendario (fancyhotel/static/js/controllers.js): la salida no puede ser antes del día siguiente a la entrada, y la entrada no puede ser después del día anterior a la salida. Si se borra la entrada, la salida mínima pasa a ser mañana.
Punto 5, calendario cuando la sede no tiene ese tipo de habitación: ahora el servidor marca todas las noches como ocupadas, así que el calendario no ofrece fechas imposibles. Quité el caso especial que devolvía [] (fancyhotel/db/mysqldb.py).

Punto 6, datos incorrectos al reservar:

Fechas: con fechas mal formadas o inexistentes (por ejemplo 2030-02-30), el servidor responde 400 con un mensaje claro en vez de fallar con error 500.
Habitaciones: si a una habitación le falta location, room_number, cost o extra_bed_or_not (o vienen vacíos), también responde 400.
Pantalla: antes, si la reserva fallaba (400 o 409) no se mostraba nada; ahora aparece un aviso con el motivo que da el servidor.
Lo verifiqué con un script temporal contra la BD local, usando una sede descartable que se borra al final. Los 7 casos inválidos responden 400 sin crear ninguna reserva, y la reserva válida se sigue creando.

Punto 7: edité tests/integration/test_disponibilidad.py, que la regla original protegía, porque me lo pediste explícitamente. Solo cambié una línea del docstring y no toqué el código de las pruebas. Ahora dice Ejecutar desde la raíz del repo:   python -m pytest tests/integration -v.

Pendientes:

Modificar una reserva: la validación de 0 noches solo cubre la creación. Modificar una reserva existente todavía permite 0 noches, en el servidor y en su calendario. Si quieres, lo cubro igual.
Aviso al elegir un tipo que la sede no tiene: hoy el calendario se ve completamente bloqueado sin ninguna explicación. Se podría mostrar un mensaje; no lo agregué porque no lo pediste.
Git: todo sigue sin commitear en feature/calendario-disponibilidad. ¿Hago el commit?