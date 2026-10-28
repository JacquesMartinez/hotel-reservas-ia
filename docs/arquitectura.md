# Análisis de arquitectura del proyecto base

> Versión validada por el equipo a partir del análisis generado con IA
> (evidencia original: `ia-evidencias/01-analisis-arquitectura.md`).

## 1. Stack

**Backend**
- Código escrito para **Python 2.7** (`print` sin paréntesis en `api.py:98`, `api.py:108`, `api.py:201`, `mysqldb.py:196`).
- **Flask + Flask-RESTful**. No existe `requirements.txt`, por lo que se desconocen las versiones originales.
- **MySQL**: la conexión inicial usa el esquema `sys`; se usa `int(11)` (ancho de visualización obsoleto desde MySQL 8.0.17).
- Entorno local del equipo: Python 3.12 (confirmar versiones exactas con `python --version` y `pip list`).

**Frontend** (sin build ni `package.json`; todo se carga desde `templates/index.html`)
- AngularJS 1.4.6 con ngRoute y ngResource (CDN, https)
- jQuery 1.11.3 (CDN, https)
- Bootstrap 3.3.5 (CDN, **http**)
- Moment.js 2.10.6 (local)
- **Eonasdan bootstrap-datetimepicker v4.15.35** (local). El archivo se llama `bootstrap-datepicker.js`, pero la librería es el *datetimepicker* de Eonasdan; su opción para bloquear fechas es `disabledDates`.

**Estado inicial:** el proyecto no ejecuta con Python 3: `SyntaxError` por los `print` y `TabError` en `mysqldb.py:374` (la línea mezcla un espacio con tabs).

## 2. Estructura de carpetas

```
fancyhotel/
├── serve.py              App Flask: ruta "/" y registro de los recursos REST
├── api.py                Recursos Flask-RESTful: validación (reqparse), cálculo de costos, llamadas a la BD
├── db/__init__.py        Crea un único MysqlManager global compartido por todo el proceso
├── db/mysqldb.py         Capa de datos: crea BD y tablas al arrancar + todas las consultas SQL
├── templates/index.html  Shell de la SPA: carga librerías y monta <div ng-view>
└── static/
    ├── js/controllers.js Toda la app Angular: factories $resource, controllers y rutas
    ├── libs/             moment, datetimepicker (js + css)
    └── views/*.html      13 vistas parciales (login, búsqueda/reserva, modificar, cancelar,
                          pago, reseñas y 3 reportes de manager)
```

## 3. Esquema de base de datos (`Fancy_Hotel`)

Se crea en `mysqldb.py` al arrancar. No hay migraciones ni datos semilla: `Room` y `Manager` quedan vacías.

| Tabla | PK | FK | Campos relevantes |
|---|---|---|---|
| Customer | username CHAR(5) | — | password VARCHAR(16) en texto plano, email UNIQUE |
| Manager | username CHAR(5) | — | password; sin relaciones |
| Credit_Card | card_number CHAR(16) | username → Customer | cvv, expiration_date, name |
| Review | review_id | username → Customer | location (texto libre), rating, comment |
| Reservation | reservation_id | username → Customer; card_number → Credit_Card | checkin_date, checkout_date, total_cost FLOAT, cancelled_or_not |
| Room | (location, room_number) | — | type, room_cost, capacity, extra_bed_price |
| Reserves_Extra_Bed | (location, room_number, reservation_id) | → Room, → Reservation | extra_bed_or_not (es la tabla puente reserva-habitación) |

Observaciones: el rol se deduce del prefijo del username (`C` cliente, `M` manager); no existe tabla de sedes; el dinero se guarda como FLOAT; `Reservation` no tiene `created_at`.

## 4. Endpoints (`serve.py`)

| Método | Ruta | Propósito |
|---|---|---|
| GET | `/` | Sirve la SPA |
| POST | `/api/login` | Valida contra Customer o Manager según el prefijo |
| POST | `/api/register` | Crea un Customer |
| GET | `/api/searchRoom` | Habitaciones libres en una sede y rango de fechas |
| POST | `/api/reservation/create` | Crea la reserva con habitaciones y tarjeta |
| PUT | `/api/reservation` | Cambia fechas y recalcula el costo (el que usa el front) |
| GET / PUT | `/api/reservation/<id>` | Detalle de reserva / actualización duplicada y rota |
| GET | `/api/reservation/<id>/availability` | Verifica disponibilidad para nuevas fechas |
| GET | `/api/reservation/<id>/cancel` | Cancela y aplica penalización (GET que modifica estado) |
| GET | `/api/reservation/cardNumber` | Reservas pagadas con una tarjeta (no usado por el front) |
| GET / POST / DELETE | `/api/payment` | Listar, agregar y borrar tarjetas |
| GET / POST | `/api/review` | Leer y crear reseñas |
| GET | `/api/reports/reservation` | Reservas por mes y sede (solo agosto y septiembre) |
| GET | `/api/reports/popularRoom` | Categoría más reservada por sede |
| GET | `/api/reports/revenue` | Ingresos por mes y sede |

## 5. Flujo de una reserva

1. **Login:** `POST /api/login`. El front guarda el username en `$rootScope`. No hay sesión, token ni cookie en el servidor.
2. **Búsqueda:** `GET /api/searchRoom`; luego `GET /api/payment` para listar las tarjetas guardadas.
3. **Selección:** el total se calcula en el cliente: (Σ precio + cama extra) × noches.
4. **Reserva:** `POST /api/reservation/create`. El backend recalcula el total **con los precios que envía el cliente**, inserta la reserva y sus habitaciones, y no revalida la disponibilidad.
5. **Pago:** no existe cobro real; solo se guarda `card_number` como FK y el `total_cost`.
6. **Después:** modificar (`availability` + `PUT`) o cancelar (penalización: 100% si faltan ≤1 día, 20% si faltan <4, 0 en otro caso).

## 6. Hallazgos

### Seguridad
| # | Problema |
|---|---|
| S1 | Sin autenticación en el servidor: cada endpoint confía en el `username` recibido (IDOR) |
| S2 | Se guardan número completo de tarjeta y CVV en texto plano, y el CVV se devuelve por la API |
| S3 | Manipulación de precio: el total usa precios enviados por el cliente (`api.py:70-74`) |
| S4 | No se verifica que la tarjeta pertenezca al usuario que reserva |
| S5 | Contraseñas en texto plano; VARCHAR(16) no admite un hash |
| S6 | Credenciales `root/password` escritas en el código |
| S7 | `debug=True` escuchando en 0.0.0.0 |
| S8 | Reportes de manager accesibles sin verificar rol |
| S9 | Cancelación por GET (expuesta a CSRF) |
| S10 | Librerías sin soporte (AngularJS 1.4, jQuery 1.11, Bootstrap 3.3, Moment 2.10); Bootstrap por http |

### Bugs principales
| # | Bug |
|---|---|
| B1 | **Overbooking:** la detección de solapamiento solo encuentra reservas contenidas en el rango (`mysqldb.py:212`, `405-406`). Correcto: `res.checkin < salida AND res.checkout > entrada` |
| B2 | No se revalida disponibilidad al crear la reserva |
| B3 | Transacción incompleta: `return` sin `rollback` (`mysqldb.py:333`) |
| B4 | Una sola conexión MySQL global, no thread-safe y sin reconexión |
| B5 | Se permite checkout = checkin (0 noches, $0); fechas sin validar en servidor |
| B6 | `ReservationResource.put` roto (variables no definidas) |
| B7 | El reembolso mostrado en el front no coincide con lo cobrado en el back |
| B8 | `revenue_report` cuenta una reserva una vez por habitación |
| B9 | Reportes con meses fijos e incluyen canceladas |
| B10 | `CREATE OR REPLACE VIEW` en cada consulta de reporte |
| B11 | `bookRooms` alerta pero no detiene el envío si falta tarjeta o habitación |
| B12 | Login sensible a mayúsculas en el prefijo; username vacío da error 500 |
| B13 | `user_exists` consulta `customer` en minúscula: falla en MySQL sobre Linux |
| B14 | `IntegrityError` sin capturar (duplicados terminan en 500) |
| B15 | La vista de cancelación etiqueta la penalización como costo total |

### Deuda técnica
Python 2 sin `requirements.txt`; sin pruebas, migraciones ni datos semilla; SQL mezclado con lógica de negocio; fórmula de costo duplicada en 4 lugares; un solo controller Angular atiende 4 vistas.

## 7. Reutilización para las historias de usuario

- **Calendario:** consulta de ocupación de `search_rooms` / `is_room_free` (tras corregir B1); el datetimepicker v4 ya cargado con `disabledDates`. Falta un endpoint que devuelva los rangos ocupados en un periodo.
- **Pago guardado:** tabla `Credit_Card`, CRUD `/api/payment` y el `<select>` de tarjetas en `searchRoom.html`. Hay que reemplazar el almacenamiento (token + últimos 4 + vencimiento), calcular el precio en el servidor y validar la propiedad de la tarjeta.
- **Previsión de demanda:** consultas y vistas de reportes existentes. Falta parametrizar fechas, corregir B8/B9, agregar `created_at`, una librería de gráficos y datos históricos.

## 8. Validación del análisis de IA

- **Lista de control del equipo:** 12 de 12 hallazgos detectados.
- **Hallazgos adicionales verificados en el código:** TabError (`mysqldb.py:374`), B1, B3, S3, B8 e identidad real del datetimepicker (Eonasdan v4.15.35).
- **Imprecisiones:** ver `respuestas-incorrectas.md` (RI-01). Versiones del entorno pendientes de confirmar con `pip list`.