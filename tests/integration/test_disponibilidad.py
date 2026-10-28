"""
Pruebas del issue "Calendario dinámico de disponibilidad".

Bloque 1 (B1 - solapamiento): prueban is_room_free y /api/searchRoom.
  Contra el código base FALLAN los casos "parcial_al_inicio", "dentro_de_la_reserva"
  y "parcial_al_final": esa es la evidencia del bug de overbooking. El caso
  "envuelve_la_reserva" ya pasa, porque es el único tipo de solapamiento que la
  consulta original detecta. Todos deben pasar tras la corrección.

Bloque 2 (endpoint nuevo): prueban GET /api/availability, que aún no existe.
  Fallan hasta implementarlo (TDD).

Bloque 3 (B2): crear una reserva sobre fechas ocupadas debe responder 409.

Requisitos: MySQL corriendo, BD creada (ejecutar la app una vez) y .env configurado.
Ejecutar desde la raíz del repo:   python -m pytest tests/integration -v

NOTA: cuando se implemente la HU de seguridad, el bloque 3 necesitará iniciar
sesión antes de crear la reserva.
"""
from datetime import date, timedelta

import pytest

import db  # noqa: E402  (crea la conexión global de la app)
from serve import app  # noqa: E402

SEDE = "Testville"
HABITACION = 901
TIPO = "Suite"
CLIENTE = "CTEST"
# Número exclusivo de estas pruebas (no usar 4111..., que es común en pruebas manuales).
TARJETA = "4000000000009901"

# Fechas relativas al futuro para que no choquen con validaciones de "fecha pasada".
BASE = date.today() + timedelta(days=60)


def dia(n):
    return BASE + timedelta(days=n)


def iso(n):
    return dia(n).isoformat()


def ejecutar(sql, params=()):
    # Usa la misma conexión que la app: así la app ve los datos de prueba
    # sin problemas de aislamiento de transacciones.
    conexion = db.mysqldb.connection
    cur = conexion.cursor()
    try:
        cur.execute(sql, params)
        conexion.commit()
        return cur.lastrowid
    finally:
        cur.close()


def limpiar():
    ejecutar("""DELETE b FROM Fancy_Hotel.Reserves_Extra_Bed b
                WHERE b.location = %s""", (SEDE,))
    ejecutar("DELETE FROM Fancy_Hotel.Reservation WHERE username = %s", (CLIENTE,))
    ejecutar("DELETE FROM Fancy_Hotel.Credit_Card WHERE username = %s OR card_number = %s",
             (CLIENTE, TARJETA))
    ejecutar("DELETE FROM Fancy_Hotel.Room WHERE location = %s", (SEDE,))
    ejecutar("DELETE FROM Fancy_Hotel.Customer WHERE username = %s", (CLIENTE,))


def crear_reserva(entrada, salida, cancelada=False):
    rid = ejecutar(
        """INSERT INTO Fancy_Hotel.Reservation
           (checkin_date, checkout_date, total_cost, username, card_number, cancelled_or_not)
           VALUES (%s, %s, %s, %s, NULL, %s)""",
        (dia(entrada), dia(salida), 750.0, CLIENTE, "1" if cancelada else "0"))
    ejecutar(
        """INSERT INTO Fancy_Hotel.Reserves_Extra_Bed
           (location, room_number, reservation_id, extra_bed_or_not)
           VALUES (%s, %s, %s, '0')""",
        (SEDE, HABITACION, rid))
    return rid


@pytest.fixture
def escenario():
    """Una sede de prueba con una sola Suite, reservada del día 10 al 13 (noches 10, 11 y 12)."""
    limpiar()
    ejecutar("""INSERT INTO Fancy_Hotel.Customer (username, password, first_name, last_name, email)
                VALUES (%s, 'test', 'Test', 'Pruebas', 'ctest@example.com')""", (CLIENTE,))
    ejecutar("""INSERT INTO Fancy_Hotel.Room
                (location, room_number, type, room_cost, capacity, extra_bed_price)
                VALUES (%s, %s, %s, 250, 4, 50)""", (SEDE, HABITACION, TIPO))
    ejecutar("""INSERT INTO Fancy_Hotel.Credit_Card (card_number, name, cvv, expiration_date, username)
                VALUES (%s, 'Test Pruebas', '123', %s, %s)""",
             (TARJETA, date.today() + timedelta(days=3 * 365), CLIENTE))
    crear_reserva(10, 13)
    yield
    limpiar()


@pytest.fixture
def cliente_http():
    app.config["TESTING"] = True
    return app.test_client()


# ---------------------------------------------------------------------------
# Bloque 1: detección de solapamiento (B1)
# ---------------------------------------------------------------------------
# (nombre, entrada, salida, ¿debe estar libre?)   Reserva existente: 10 -> 13
CASOS = [
    ("parcial_al_inicio", 8, 11, False),
    ("envuelve_la_reserva", 9, 15, False),
    ("dentro_de_la_reserva", 11, 12, False),
    ("mismo_rango", 10, 13, False),
    ("parcial_al_final", 12, 15, False),
    ("entra_el_dia_del_checkout", 13, 15, True),
    ("sale_el_dia_del_checkin", 8, 10, True),
    ("totalmente_antes", 2, 5, True),
]


@pytest.mark.parametrize("nombre, entrada, salida, libre", CASOS, ids=[c[0] for c in CASOS])
def test_is_room_free_detecta_solapamiento(escenario, nombre, entrada, salida, libre):
    resultado = db.mysqldb.is_room_free(HABITACION, SEDE, iso(entrada), iso(salida), -1)
    assert resultado == libre


@pytest.mark.parametrize("nombre, entrada, salida, libre", CASOS, ids=[c[0] for c in CASOS])
def test_busqueda_excluye_habitaciones_ocupadas(escenario, cliente_http, nombre, entrada, salida, libre):
    r = cliente_http.get("/api/searchRoom", query_string={
        "location": SEDE, "checkIn": iso(entrada), "checkOut": iso(salida)})
    assert r.status_code == 200, r.get_data(as_text=True)
    numeros = [h["room_number"] for h in r.get_json()["response"]]
    assert (HABITACION in numeros) == libre


def test_reserva_cancelada_no_ocupa(escenario):
    limpiar_reservas = "DELETE FROM Fancy_Hotel.Reserves_Extra_Bed WHERE location = %s"
    ejecutar(limpiar_reservas, (SEDE,))
    ejecutar("DELETE FROM Fancy_Hotel.Reservation WHERE username = %s", (CLIENTE,))
    crear_reserva(10, 13, cancelada=True)
    assert db.mysqldb.is_room_free(HABITACION, SEDE, iso(10), iso(13), -1) is True


# ---------------------------------------------------------------------------
# Bloque 2: endpoint nuevo GET /api/availability (falla hasta implementarlo)
# Contrato esperado: {"occupied": ["YYYY-MM-DD", ...]}  -> noches sin habitación libre
# ---------------------------------------------------------------------------
def consultar_disponibilidad(cliente_http, **extra):
    params = {"location": SEDE, "type": TIPO, "from": iso(0), "to": iso(20)}
    params.update(extra)
    return cliente_http.get("/api/availability", query_string=params)


def test_availability_responde_200(escenario, cliente_http):
    r = consultar_disponibilidad(cliente_http)
    assert r.status_code == 200, r.get_data(as_text=True)
    assert "occupied" in r.get_json()


def test_availability_marca_las_noches_ocupadas(escenario, cliente_http):
    ocupadas = set(consultar_disponibilidad(cliente_http).get_json()["occupied"])
    assert {iso(10), iso(11), iso(12)} <= ocupadas


def test_availability_el_dia_de_checkout_queda_libre(escenario, cliente_http):
    ocupadas = set(consultar_disponibilidad(cliente_http).get_json()["occupied"])
    assert iso(13) not in ocupadas
    assert iso(9) not in ocupadas


def test_availability_ignora_canceladas(escenario, cliente_http):
    ejecutar("DELETE FROM Fancy_Hotel.Reserves_Extra_Bed WHERE location = %s", (SEDE,))
    ejecutar("DELETE FROM Fancy_Hotel.Reservation WHERE username = %s", (CLIENTE,))
    crear_reserva(10, 13, cancelada=True)
    assert consultar_disponibilidad(cliente_http).get_json()["occupied"] == []


# ---------------------------------------------------------------------------
# Bloque 3: revalidar disponibilidad al crear la reserva (B2)
# ---------------------------------------------------------------------------
def test_crear_reserva_sobre_fechas_ocupadas_responde_409(escenario, cliente_http):
    r = cliente_http.post("/api/reservation/create", json={
        "username": CLIENTE,
        "checkIn": iso(11),
        "checkOut": iso(14),
        "card_number": TARJETA,
        "rooms": [{"location": SEDE, "room_number": HABITACION, "cost": 250,
                   "extra_bed_price": 50, "extra_bed_or_not": 0}],
    })
    assert r.status_code == 409, r.get_data(as_text=True)