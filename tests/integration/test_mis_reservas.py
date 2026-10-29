"""
Pruebas de integración de "Mis reservaciones".

Contrato:
  - GET /api/reservations -> 401 sin sesión.
  - Con sesión devuelve solo las reservas del usuario de la sesión, también las
    canceladas, ordenadas por check-in de la más reciente a la más antigua.
  - Cada reserva trae sus habitaciones (location, room_number, room_type,
    extra_bed_or_not) y solo los últimos 4 dígitos de la tarjeta (card_last4).

Ejecutar desde la raíz:  python -m pytest tests/integration/test_mis_reservas.py -v
"""
from datetime import date, timedelta

import pytest

import db  # noqa: E402
from serve import app  # noqa: E402

CLIENTE_1 = "CMRS1"
CLIENTE_2 = "CMRS2"
SEDE = "TestMisRe"
TOKEN = "tok_test_cmrs01"
BASE = date.today() + timedelta(days=60)


def iso(n):
    return (BASE + timedelta(days=n)).isoformat()


def ejecutar(sql, params=()):
    conexion = db.mysqldb.connection
    cur = conexion.cursor()
    try:
        cur.execute(sql, params)
        filas = cur.fetchall() if cur.with_rows else None
        conexion.commit()
        return cur.lastrowid if filas is None else filas
    finally:
        cur.close()


def reservar(usuario, entrada, salida, habitaciones, cancelada="0", tarjeta=None):
    reserva = ejecutar("""INSERT INTO Fancy_Hotel.Reservation
                          (username, checkin_date, checkout_date, card_number, total_cost, cancelled_or_not)
                          VALUES (%s, %s, %s, %s, 100, %s)""", (usuario, entrada, salida, tarjeta, cancelada))
    for numero, cama in habitaciones:
        ejecutar("""INSERT INTO Fancy_Hotel.Reserves_Extra_Bed (location, room_number, reservation_id, extra_bed_or_not)
                    VALUES (%s, %s, %s, %s)""", (SEDE, numero, reserva, cama))
    return reserva


def limpiar():
    clientes = (CLIENTE_1, CLIENTE_2)
    ejecutar("DELETE FROM Fancy_Hotel.Reserves_Extra_Bed WHERE location = %s", (SEDE,))
    ejecutar("DELETE FROM Fancy_Hotel.Reservation WHERE username IN (%s, %s)", clientes)
    ejecutar("DELETE FROM Fancy_Hotel.Credit_Card WHERE username IN (%s, %s)", clientes)
    ejecutar("DELETE FROM Fancy_Hotel.Room WHERE location = %s", (SEDE,))
    ejecutar("DELETE FROM Fancy_Hotel.Customer WHERE username IN (%s, %s)", clientes)


@pytest.fixture
def escenario():
    limpiar()
    for usuario in (CLIENTE_1, CLIENTE_2):
        ejecutar("""INSERT INTO Fancy_Hotel.Customer (username, password, first_name, last_name, email)
                    VALUES (%s, 'x', 'Test', 'Reservas', %s)""", (usuario, f"{usuario.lower()}@example.com"))
    for numero, tipo in ((901, "Standard"), (902, "Suite")):
        ejecutar("""INSERT INTO Fancy_Hotel.Room (location, room_number, type, room_cost, capacity, extra_bed_price)
                    VALUES (%s, %s, %s, 100, 2, 20)""", (SEDE, numero, tipo))
    ejecutar("""INSERT INTO Fancy_Hotel.Credit_Card (card_number, name, expiration_date, username, last4, is_default)
                VALUES (%s, 'Cliente Uno', %s, %s, '4321', 1)""", (TOKEN, date.today() + timedelta(days=1000), CLIENTE_1))
    ids = {
        "proxima": reservar(CLIENTE_1, iso(10), iso(12), [(901, "1"), (902, "0")], tarjeta=TOKEN),
        "cancelada": reservar(CLIENTE_1, iso(0), iso(3), [(901, "0")], cancelada="1"),
        "ajena": reservar(CLIENTE_2, iso(20), iso(21), [(902, "0")]),
    }
    yield ids
    limpiar()


def cliente_con_sesion(usuario):
    app.config["TESTING"] = True
    http = app.test_client()
    with http.session_transaction() as sesion:
        sesion["username"] = usuario
        sesion["role"] = "customer"
    return http


def test_sin_sesion_responde_401(escenario):
    app.config["TESTING"] = True
    assert app.test_client().get("/api/reservations").status_code == 401


def test_solo_las_reservas_propias_ordenadas_por_checkin(escenario):
    r = cliente_con_sesion(CLIENTE_1).get(f"/api/reservations?username={CLIENTE_2}")
    assert r.status_code == 200, r.get_data(as_text=True)
    ids = [reserva["reservation_id"] for reserva in r.get_json()]
    assert ids == [escenario["proxima"], escenario["cancelada"]]


def test_trae_habitaciones_tarjeta_y_cancelacion(escenario):
    reservas = {reserva["reservation_id"]: reserva for reserva in cliente_con_sesion(CLIENTE_1).get("/api/reservations").get_json()}

    proxima = reservas[escenario["proxima"]]
    assert proxima["checkin_date"] == iso(10) and proxima["checkout_date"] == iso(12)
    assert proxima["cancelled_or_not"] == "0"
    assert proxima["card_last4"] == "4321"
    assert proxima["rooms"] == [
        {"location": SEDE, "room_number": 901, "room_type": "Standard", "extra_bed_or_not": "1"},
        {"location": SEDE, "room_number": 902, "room_type": "Suite", "extra_bed_or_not": "0"},
    ]
    assert TOKEN not in str(proxima)  # el token de la tarjeta no sale de la BD

    cancelada = reservas[escenario["cancelada"]]
    assert cancelada["cancelled_or_not"] == "1"
    assert cancelada["card_last4"] is None
    assert len(cancelada["rooms"]) == 1


def test_usuario_sin_reservas_recibe_lista_vacia(escenario):
    limpiar()
    ejecutar("""INSERT INTO Fancy_Hotel.Customer (username, password, first_name, last_name, email)
                VALUES (%s, 'x', 'Test', 'Reservas', 'vacio@example.com')""", (CLIENTE_1,))
    r = cliente_con_sesion(CLIENTE_1).get("/api/reservations")
    assert r.status_code == 200
    assert r.get_json() == []
