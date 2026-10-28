"""
Pruebas de integración del issue "Reserva con datos de pago guardados".

Contrato (decisiones D-02 y D-08):
  Esquema de Credit_Card
    - card_number guarda un TOKEN generado por el servidor (no el número real).
      Se conserva el nombre de la columna para no romper la FK de Reservation.
    - Se elimina la columna cvv. Se agregan last4 CHAR(4) e is_default.
  API (todo requiere sesión; el usuario sale de la sesión)
    - POST   /api/payment          {card_number, name, cvv, expiration_date, make_default?}
                                   -> 200 {"result": true, "card": {...}} ; 400 si datos inválidos
    - GET    /api/payment          -> lista de {"token","last4","name","expiration_date","is_default"}
    - POST   /api/payment/default  {"token"} -> marca esa tarjeta como predeterminada (solo una)
    - DELETE /api/payment?token=   -> 200 ; 404 si el token no es del usuario
    - POST   /api/reservation/create {checkIn, checkOut, rooms, card_token?}
        * sin card_token se usa la tarjeta predeterminada; si no hay ninguna -> 400
        * token de otro usuario -> 403
        * el total se calcula con los precios de la BD, ignorando los del cliente (S3)

Ejecutar desde la raíz:  python -m pytest tests/integration/test_pago_guardado.py -v
"""
from datetime import date, timedelta

import pytest

import db  # noqa: E402
from serve import app  # noqa: E402

CLIENTE_1 = "CPAG1"
CLIENTE_2 = "CPAG2"
SEDE = "TestPago"
HABITACION = 801
COSTO_NOCHE = 100.0
CAMA_EXTRA = 20.0
NUMERO_REAL = "4242424242424242"
CVV = "987"
TOKEN_CLIENTE_2 = "tok_test_cpag02"
BASE = date.today() + timedelta(days=90)


def iso(n):
    return (BASE + timedelta(days=n)).isoformat()


def ejecutar(sql, params=()):
    conexion = db.mysqldb.connection
    cur = conexion.cursor()
    try:
        cur.execute(sql, params)
        filas = cur.fetchall() if cur.with_rows else None
        conexion.commit()
        return filas
    finally:
        cur.close()


def columnas_credit_card():
    filas = ejecutar("""SELECT COLUMN_NAME FROM information_schema.COLUMNS
                        WHERE TABLE_SCHEMA = 'Fancy_Hotel' AND TABLE_NAME = 'Credit_Card'""")
    return {f[0].lower() for f in filas}


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
                    VALUES (%s, 'x', 'Test', 'Pago', %s)""", (usuario, f"{usuario.lower()}@example.com"))
    ejecutar("""INSERT INTO Fancy_Hotel.Room (location, room_number, type, room_cost, capacity, extra_bed_price)
                VALUES (%s, %s, 'Standard', %s, 2, %s)""", (SEDE, HABITACION, COSTO_NOCHE, CAMA_EXTRA))
    # Tarjeta ya guardada de CLIENTE_2, con el esquema nuevo
    if "last4" in columnas_credit_card():
        ejecutar("""INSERT INTO Fancy_Hotel.Credit_Card
                    (card_number, name, expiration_date, username, last4, is_default)
                    VALUES (%s, 'Cliente Dos', %s, %s, '9999', 1)""",
                 (TOKEN_CLIENTE_2, date.today() + timedelta(days=1000), CLIENTE_2))
    yield
    limpiar()


def cliente_con_sesion(usuario):
    app.config["TESTING"] = True
    http = app.test_client()
    with http.session_transaction() as sesion:
        sesion["username"] = usuario
        sesion["role"] = "customer"
    return http


def guardar_tarjeta(http, numero=NUMERO_REAL, cvv=CVV, vence=None, predeterminada=True):
    vence = vence or (date.today() + timedelta(days=800)).isoformat()
    return http.post("/api/payment", json={
        "card_number": numero, "name": "Cliente Uno", "cvv": cvv,
        "expiration_date": vence, "make_default": predeterminada})


def tarjetas(http):
    r = http.get("/api/payment")
    assert r.status_code == 200, r.get_data(as_text=True)
    return r.get_json()


def reservar(http, extra_cama=0, **extra):
    cuerpo = {"checkIn": iso(0), "checkOut": iso(2),
              "rooms": [{"location": SEDE, "room_number": HABITACION,
                         "cost": 1, "extra_bed_price": 0, "extra_bed_or_not": extra_cama}]}
    cuerpo.update(extra)
    return http.post("/api/reservation/create", json=cuerpo)


# --- Almacenamiento seguro (S2) ----------------------------------------------

def test_esquema_sin_cvv_y_con_last4(escenario):
    columnas = columnas_credit_card()
    assert "cvv" not in columnas, "La tabla Credit_Card todavía tiene columna cvv"
    assert {"last4", "is_default"} <= columnas


def test_guardar_tarjeta_no_almacena_numero_ni_cvv(escenario):
    http = cliente_con_sesion(CLIENTE_1)
    r = guardar_tarjeta(http)
    assert r.status_code == 200, r.get_data(as_text=True)
    filas = ejecutar("SELECT * FROM Fancy_Hotel.Credit_Card WHERE username = %s", (CLIENTE_1,))
    assert len(filas) == 1
    valores = [str(v) for v in filas[0]]
    assert NUMERO_REAL not in valores, "Se guardó el número completo de la tarjeta"
    assert CVV not in valores, "Se guardó el CVV"
    assert "4242" in valores, "No se guardaron los últimos 4 dígitos"


def test_api_nunca_devuelve_numero_ni_cvv(escenario):
    http = cliente_con_sesion(CLIENTE_1)
    guardar_tarjeta(http)
    lista = tarjetas(http)
    texto = str(lista)
    assert NUMERO_REAL not in texto
    assert "cvv" not in texto.lower()
    assert lista[0]["last4"] == "4242"
    assert lista[0]["token"]


@pytest.mark.parametrize("numero, cvv, vence", [
    ("1234", CVV, None),                                   # número muy corto
    ("abcdabcdabcdabcd", CVV, None),                       # no numérico
    (NUMERO_REAL, "12", None),                             # cvv inválido
    (NUMERO_REAL, CVV, (date.today() - timedelta(days=30)).isoformat()),  # vencida
], ids=["numero_corto", "no_numerico", "cvv_invalido", "vencida"])
def test_rechaza_tarjetas_invalidas(escenario, numero, cvv, vence):
    http = cliente_con_sesion(CLIENTE_1)
    assert guardar_tarjeta(http, numero, cvv, vence).status_code == 400


# --- Tarjeta predeterminada ---------------------------------------------------

def test_solo_una_tarjeta_predeterminada(escenario):
    http = cliente_con_sesion(CLIENTE_1)
    guardar_tarjeta(http, NUMERO_REAL)
    guardar_tarjeta(http, "5555555555554444", predeterminada=False)
    lista = tarjetas(http)
    otra = next(t for t in lista if t["last4"] == "4444")
    r = http.post("/api/payment/default", json={"token": otra["token"]})
    assert r.status_code == 200, r.get_data(as_text=True)
    predeterminadas = [t["last4"] for t in tarjetas(http) if t["is_default"]]
    assert predeterminadas == ["4444"]


# --- Reserva en un clic ------------------------------------------------------

def test_reserva_sin_token_usa_la_predeterminada(escenario):
    http = cliente_con_sesion(CLIENTE_1)
    guardar_tarjeta(http)
    token = tarjetas(http)[0]["token"]
    r = reservar(http)
    assert r.status_code == 200, r.get_data(as_text=True)
    filas = ejecutar("SELECT card_number FROM Fancy_Hotel.Reservation WHERE username = %s", (CLIENTE_1,))
    assert filas[0][0] == token


def test_reserva_sin_tarjetas_responde_400(escenario):
    http = cliente_con_sesion(CLIENTE_1)
    assert reservar(http).status_code == 400


def test_no_puede_usar_tarjeta_de_otro_usuario(escenario):
    http = cliente_con_sesion(CLIENTE_1)
    r = reservar(http, card_token=TOKEN_CLIENTE_2)
    assert r.status_code == 403, r.get_data(as_text=True)
    filas = ejecutar("SELECT COUNT(*) FROM Fancy_Hotel.Reservation WHERE username = %s", (CLIENTE_1,))
    assert filas[0][0] == 0


# --- Precio calculado en el servidor (S3) ------------------------------------

@pytest.mark.parametrize("cama, esperado", [(0, COSTO_NOCHE * 2), (1, (COSTO_NOCHE + CAMA_EXTRA) * 2)],
                         ids=["sin_cama_extra", "con_cama_extra"])
def test_precio_se_calcula_con_precios_de_la_bd(escenario, cama, esperado):
    http = cliente_con_sesion(CLIENTE_1)
    guardar_tarjeta(http)
    r = reservar(http, extra_cama=cama)  # el cliente envía cost=1: debe ignorarse
    assert r.status_code == 200, r.get_data(as_text=True)
    filas = ejecutar("SELECT total_cost FROM Fancy_Hotel.Reservation WHERE username = %s", (CLIENTE_1,))
    assert float(filas[0][0]) == pytest.approx(esperado)


# --- Eliminar ----------------------------------------------------------------

def test_eliminar_tarjeta_propia(escenario):
    http = cliente_con_sesion(CLIENTE_1)
    guardar_tarjeta(http)
    token = tarjetas(http)[0]["token"]
    assert http.delete("/api/payment", query_string={"token": token}).status_code == 200
    assert tarjetas(http) == []


def test_no_puede_eliminar_tarjeta_de_otro(escenario):
    http = cliente_con_sesion(CLIENTE_1)
    r = http.delete("/api/payment", query_string={"token": TOKEN_CLIENTE_2})
    assert r.status_code == 404
    filas = ejecutar("SELECT COUNT(*) FROM Fancy_Hotel.Credit_Card WHERE card_number = %s", (TOKEN_CLIENTE_2,))
    assert filas[0][0] == 1
