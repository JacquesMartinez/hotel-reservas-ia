Implementa completo el issue #N "Gráficos de previsión de demanda".

CONTEXTO
- Lee docs/arquitectura.md (B8, B9), docs/decisiones.md (D-09) y
  tests/integration/test_prevision.py. Su docstring define el contrato
  exacto de la API.
- Las pruebas de integración no se modifican y deben pasar todas:
    python -m pytest tests/integration -v
- Las unitarias también deben pasar (puedes ajustarlas explicando por qué,
  sin tocar tests/unit/conftest.py):
    python -m pytest -v
- La sesión y el decorador manager_required ya existen.

CAMBIOS
1. Base de datos
   - Agrega Reservation.created_at DATETIME NOT NULL DEFAULT
     CURRENT_TIMESTAMP. La migración en init_db debe ser idempotente:
     consulta information_schema antes del ALTER (MySQL no soporta
     ADD COLUMN IF NOT EXISTS). Actualiza también el CREATE TABLE.
   - Actualiza seed.py para llenar created_at con fechas realistas:
     entre 1 y 60 días antes del checkin, nunca posterior a hoy.

2. Reportes existentes (/api/reports/revenue y /api/reports/reservation)
   - Parámetros opcionales from y to (YYYY-MM-DD) en lugar de los meses
     fijos de agosto y septiembre.
   - Claves de mes con formato "YYYY-MM".
   - Excluir reservas canceladas.
   - revenue: cada reserva se suma UNA vez aunque tenga varias
     habitaciones (B8). No uses SUM(DISTINCT total_cost): uniría reservas
     distintas que tengan el mismo total.
   - reservation: contar reservas, no habitaciones (B9).
   - Elimina el CREATE OR REPLACE VIEW de room_report (B10) solo si lo
     necesitas modificar; si no, déjalo como está.

3. Nuevo endpoint GET /api/reports/forecast (manager_required)
   - Parámetros: location (obligatorio, 400 si falta), weeks (por defecto
     8), history_weeks (por defecto 12).
   - Semanas de lunes a domingo. Ojo: las funciones WEEK()/YEARWEEK() de
     MySQL empiezan en domingo por defecto; calcula las semanas en Python o
     usa el modo correcto.
   - Una noche d está ocupada por una reserva si checkin <= d < checkout.
     Una reserva que cruza dos semanas aporta sus noches a cada una.
   - Usa una sola consulta para traer las reservas del periodo.
   - Sede sin habitaciones: ocupación 0, sin división por cero.
   - Respuesta, cálculo y umbrales exactamente como en el docstring de las
     pruebas.

4. Frontend
   - Adapta las vistas de reportes existentes a las claves "YYYY-MM" y
     agrega selector de rango de fechas.
   - Nueva vista forecastReport.html, accesible desde el portal del
     manager, con selector de sede y un gráfico de Chart.js:
     historial en línea sólida y previsión en línea punteada (borderDash).
   - Debajo del gráfico, tabla de las semanas previstas con la sugerencia
     de precio (+15 %, -10 % o sin cambio).
   - Carga Chart.js desde un CDN con https y versión fija.
   - Muestra una explicación breve del método (campo "method").

REGLAS
- No modifiques tests/integration/.
- No corrijas otros bugs fuera de este issue; menciónalos al final.
- Antes de aplicar, lista todos los cambios por archivo y espera mi
  confirmación. Al terminar, ejecuta ambas suites de pruebas y muéstrame
  el resultado.


Plan de cambios por archivo
1. fancyhotel/db/mysqldb.py
init_db
Agrego created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP al CREATE TABLE Reservation.
Agrego la migración idempotente después de ese CREATE: consulta information_schema.COLUMNS y ejecuta el ALTER TABLE ... ADD COLUMN solo si la columna no existe. Es el mismo patrón que ya se usa con cvv.
get_reservation y get_reservation_by_card_number: hoy hacen SELECT * y desempaquetan 7 columnas. Con created_at serían 8 y fallarían con ValueError. Las cambio a columnas explícitas. No es otro bug: es necesario para no romper nada con la columna nueva.
reservation_report(from_date, to_date)
COUNT(DISTINCT res.reservation_id) agrupado por YEAR/MONTH de checkin_date y por sede.
Excluye canceladas y filtra checkin_date entre from y to, ambos incluidos (D-09). Si un parámetro falta, ese lado queda sin límite.
La clave "YYYY-MM" se arma en Python. Así evito los % de DATE_FORMAT junto con los parámetros del conector.
revenue_report(from_date, to_date)
Una subconsulta SELECT DISTINCT res.reservation_id, bed.location, res.checkin_date, res.total_cost deja una fila por reserva y sede. Encima se aplica SUM(total_cost). No uso SUM(DISTINCT).
Mismos filtros y mismas claves que reservation_report.
Nuevo get_room_stays(location, from_date, to_date)
Devuelve (número de habitaciones de la sede, [(checkin, checkout), ...]).
Hay una fila por habitación reservada y una sola consulta para todas las reservas no canceladas que se solapan con el periodo.
room_report no se toca (B10 se queda como está).
2. fancyhotel/api.py
Helper parse_date_range(args): valida from y to opcionales con formato YYYY-MM-DD. Responde 400 si el formato es incorrecto o si from > to.
ReservationReportResource y RevenueReportResource: leen from y to con reqparse (location='args') y se los pasan a la base de datos.
Función pura build_forecast(total_rooms, stays, today, weeks, history_weeks)
Semanas de lunes a domingo calculadas en Python (today - weekday()), sin WEEK().
Noches por semana = traslape de [checkin, checkout) con [lunes, lunes+7). Una reserva que cruza dos semanas aporta sus noches a cada una.
Ocupación = noches / (habitaciones × 7). Si la sede no tiene habitaciones, es 0.
Previsión: max(promedio de las últimas 4 semanas del historial, booked).
price_change_pct: +15, −10 o 0.
Redondeo a 4 decimales antes de comparar con los umbrales. Así un 0.30000000000000004 de punto flotante no queda fuera del ≤ 0.3.
Incluye el texto de method.
ForecastReportResource (manager_required)
location obligatorio: reqparse devuelve 400 si falta.
weeks=8 y history_weeks=12 por defecto.
Una sola llamada a get_room_stays para todo el rango, del historial al final de la previsión.
3. fancyhotel/serve.py
Registro /api/reports/forecast.
4. fancyhotel/seed.py
build_reservations agrega created_at = min(checkin − randint(1, 60) días, today).
El INSERT de Reservation incluye created_at.
5. Frontend
templates/index.html: Chart.js 4.4.1 desde cdnjs con https, versión fija y hash SRI (integrity). Va aquí porque las vistas parciales de ng-view no ejecutan <script>.
static/js/controllers.js
reportFactory recibe from/to y una nueva acción Forecast.
reportController
Agrega un rango por defecto: desde el primer día de hace 11 meses hasta hoy.
Agrega loadReports() para volver a consultar con el rango elegido.
Agrega formatMonth("YYYY-MM"), que muestra por ejemplo "October 2026".
Mantengo getMonth, porque el reporte de categoría popular sigue usando números de mes.
Nuevo forecastController
Selector de sede.
Gráfico con dos series: historial en línea sólida y previsión con borderDash. La previsión arranca en el último punto del historial para que la línea sea continua.
Eje Y de 0 a 100 %.
Destruye el gráfico anterior al cambiar de sede y al salir de la vista.
Nueva ruta /forecastReport.
revenueReport.html y reservationReport.html: selector de rango con dos input type="date" y un botón, y las claves "YYYY-MM" mostradas con formatMonth.
Nueva forecastReport.html
Selector de sede con las 5 sedes del front actual, el gráfico y el texto de method.
Debajo, la tabla con semana, ocupación reservada, ocupación prevista y sugerencia de precio ("+15 %", "−10 %" o "No change").
selectionPage.html: enlace "View demand forecast" en el portal del manager.
6. Pruebas unitarias
Las existentes no necesitan cambios: ninguna toca los reportes ni las columnas de Reservation.
Agrego tests/unit/test_seed.py: una prueba de que created_at cae entre 1 y 60 días antes del checkin y nunca después de hoy.
Nuevo tests/unit/test_reports.py (no lo llamo test_prevision.py para no chocar con el módulo de integración del mismo nombre):
build_forecast: reserva que cruza dos semanas, sede sin habitaciones, umbrales exactos 0.8 y 0.3, history_weeks menor que 4.
Respuestas 400 de los endpoints: falta location, fecha mal formada, from > to.
Decisiones que asumo (dímelo si alguna no te sirve)
weeks y history_weeks: deben ser enteros entre 1 y 52; si no, responden 400. El issue no fija límites.
Filtro de los reportes: from/to se aplican a checkin_date, igual que hoy se agrupa por el mes de checkin.
Texto de method y de la vista: en inglés, como el resto de la interfaz.
No toco docs/: si quieres, al final te propongo las entradas D-xx para estas decisiones.
¿Confirmas que aplique estos cambios?


se confirman los cambios


Implementé el issue completo. Pasan las 53 pruebas unitarias y las 68 de integración, incluidas las 11 de previsión, que antes fallaban. No hice commit.

Resultado de las pruebas

python -m pytest -v                    → 53 passed (19 anteriores + 34 nuevas)
python -m pytest tests/integration -v  → 68 passed (57 anteriores + 11 de test_prevision.py)
No modifiqué ninguna prueba unitaria existente; solo agregué pruebas nuevas.

Qué se hizo
Seguí el plan aprobado, con estas precisiones:

Migración de created_at: la probé contra tu MySQL. El ALTER creó la columna (datetime, NOT NULL, CURRENT_TIMESTAMP) y un segundo arranque seguido no da error. También cambié los dos SELECT * de Reservation por columnas explícitas para que no fallaran con la columna nueva.
Respuesta de /api/reports/forecast: devuelve exactamente las claves del docstring, sin campos extra.
Gráfico: historial azul sólido, previsión naranja punteada y un hueco en la semana en curso. Esa semana no entra ni en el historial ni en la previsión, y la vista lo explica. Lo revisé con capturas en Chrome headless, junto con la tabla, el texto del método y el selector de rango de los reportes.
Chart.js 4.4.1: se carga desde cdnjs con https y hash SRI.
Pruebas nuevas:
tests/unit/test_reports.py: semanas de lunes a domingo, una reserva que cruza dos semanas, la noche del checkout, sede sin habitaciones, umbrales de precio, ruido de punto flotante en el promedio y respuestas 400 de los tres endpoints.
tests/unit/test_seed.py: una prueba para created_at.
Bugs y observaciones fuera del issue (no corregidos)
B4 tumba el servidor al abrir un reporte. reportController lanza 3 peticiones a la vez sobre la única conexión MySQL compartida. Repetí la prueba con el código original (HEAD) en un worktree temporal: 3 de 4 veces el proceso murió y la otra perdió la conexión para siempre (todo 500 hasta reiniciar). Ya pasaba antes de estos cambios; la vista de previsión hace una sola petición y no se ve afectada. Para las capturas usé flask run --without-threads.
El seed no crea reservas futuras. En la demo, booked siempre es 0 y todas las sedes quedan cerca del 29 % de ocupación, con sugerencia de −10 %.
created_at de los datos actuales: las reservas que ya existían quedaron con la fecha de la migración. Se corrige ejecutando seed.py, pero ten en cuenta que vacía las tablas.
Penalizaciones de cancelación fuera de los ingresos. Al cancelar, total_cost guarda la penalización y el reporte de ingresos excluye las canceladas, como pide el issue. Por eso ese dinero no aparece en los ingresos.
El reporte de categoría popular sigue igual: solo agosto, claves numéricas, incluye canceladas y conserva el CREATE OR REPLACE VIEW (B10).
El login de M2acz con la clave del seed (manager123) responde 401 en tu base actual. Para las capturas usé una cookie de sesión firmada con tu SECRET_KEY local; no toqué credenciales.
Bootstrap se sigue cargando por http (S10).
Redondeo en la tabla: muestra porcentajes enteros, así que un 79,6 % aparece como "80 %" con "No change". El backend compara con 4 decimales y el resultado es correcto.



