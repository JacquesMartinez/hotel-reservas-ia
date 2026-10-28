"""
Pruebas de integración del issue "Confirmación de reserva por correo".

Contrato:
  - Configuración leída de variables de entorno EN EL MOMENTO DEL ENVÍO
    (no al importar):
      MAIL_MODE = "console" (por defecto) | "smtp"
      MAIL_HOST, MAIL_PORT, MAIL_FROM, MAIL_USER y MAIL_PASSWORD (opcionales)
  - Modo smtp: usa smtplib.SMTP a través del módulo (import smtplib), para que
    las pruebas puedan reemplazarlo. Modo console: no abre conexiones SMTP.
  - Al crear una reserva con éxito se envía UN correo al email del cliente con:
    número de reserva, fechas (YYYY-MM-DD), sede y número de cada habitación,
    y el total.
  - Si el envío falla, la reserva igual se crea (200) y el error se registra
    con logging a nivel ERROR.
  - Si la reserva no se crea (por ejemplo 409), no se envía correo.

Ejecutar desde la raíz:  python -m pytest tests/integration/test_correo.py -v
"""
import email
import logging
import smtplib
from datetime import date, timedelta
from email import policy

import pytest

import db  # noqa: E402
from serve import app  # noqa: E402

CLIENTE = "CMAIL"
CORREO_CLIENTE = "cmail@example.com"
SEDE = "TestMail"
HABITACION = 601
TOKEN = "tok_test_cmail1"
ENTRADA = date.today() + timedelta(days=120)
SALIDA = ENTRADA + timedelta(days=2)


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
    ejecutar("DELETE FROM Fancy_Hotel.Reserves_Extra_Bed WHERE location = %s", (SEDE,))
    ejecutar("DELETE FROM Fancy_Hotel.Reservation WHERE username = %s", (CLIENTE,))
    ejecutar("DELETE FROM Fancy_Hotel.Credit_Card WHERE username = %s", (CLIENTE,))
    ejecutar("DELETE FROM Fancy_Hotel.Room WHERE location = %s", (SEDE,))
    ejecutar("DELETE FROM Fancy_Hotel.Customer WHERE username = %s", (CLIENTE,))


@pytest.fixture
def escenario():
    limpiar()
    ejecutar("""INSERT INTO Fancy_Hotel.Customer (username, password, first_name, last_name, email)
                VALUES (%s, 'x', 'Test', 'Correo', %s)""", (CLIENTE, CORREO_CLIENTE))
    ejecutar("""INSERT INTO Fancy_Hotel.Room (location, room_number, type, room_cost, capacity, extra_bed_price)
                VALUES (%s, %s, 'Standard', 100, 2, 20)""", (SEDE, HABITACION))
    vence = date.today() + timedelta(days=1000)
    if "last4" in columnas_credit_card():
        ejecutar("""INSERT INTO Fancy_Hotel.Credit_Card
                    (card_number, name, expiration_date, username, last4, is_default)
                    VALUES (%s, 'Test Correo', %s, %s, '1111', 1)""", (TOKEN, vence, CLIENTE))
    else:
        ejecutar("""INSERT INTO Fancy_Hotel.Credit_Card (card_number, name, cvv, expiration_date, username)
                    VALUES (%s, 'Test Correo', '123', %s, %s)""", (TOKEN, vence, CLIENTE))
    yield
    limpiar()


class SMTPFalso:
    """Reemplazo de smtplib.SMTP que guarda los correos en lugar de enviarlos."""
    enviados = []
    conexiones = []
    fallar = False

    def __init__(self, host="", port=0, *args, **kwargs):
        if SMTPFalso.fallar:
            raise smtplib.SMTPConnectError(421, "servidor de prueba caído")
        SMTPFalso.conexiones.append((host, int(port)))

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def ehlo(self, *a, **k): pass
    def starttls(self, *a, **k): pass
    def login(self, *a, **k): pass
    def quit(self): pass
    def close(self): pass

    def send_message(self, mensaje, from_addr=None, to_addrs=None, *a, **k):
        destinatarios = to_addrs or mensaje.get_all("To", [])
        if isinstance(destinatarios, str):
            destinatarios = [destinatarios]
        SMTPFalso._guardar(destinatarios, mensaje)
        return {}

    def sendmail(self, from_addr, to_addrs, mensaje, *a, **k):
        if isinstance(to_addrs, str):
            to_addrs = [to_addrs]
        if isinstance(mensaje, bytes):
            mensaje = mensaje.decode("utf-8", "replace")
        SMTPFalso._guardar(to_addrs, email.message_from_string(mensaje, policy=policy.default))
        return {}

    @staticmethod
    def _guardar(destinatarios, mensaje):
        cuerpo = mensaje.get_body(preferencelist=("plain", "html"))
        texto = cuerpo.get_content() if cuerpo is not None else str(mensaje.get_payload())
        SMTPFalso.enviados.append({"para": [str(d) for d in destinatarios],
                                   "asunto": str(mensaje.get("Subject", "")),
                                   "texto": texto})


@pytest.fixture
def smtp_falso(monkeypatch):
    SMTPFalso.enviados, SMTPFalso.conexiones, SMTPFalso.fallar = [], [], False
    monkeypatch.setattr(smtplib, "SMTP", SMTPFalso)
    monkeypatch.setenv("MAIL_MODE", "smtp")
    monkeypatch.setenv("MAIL_HOST", "smtp.prueba.local")
    monkeypatch.setenv("MAIL_PORT", "2525")
    monkeypatch.setenv("MAIL_FROM", "reservas@fancyhotel.test")
    return SMTPFalso


def reservar(entrada=ENTRADA, salida=SALIDA):
    app.config["TESTING"] = True
    http = app.test_client()
    with http.session_transaction() as sesion:
        sesion["username"] = CLIENTE
        sesion["role"] = "customer"
    return http.post("/api/reservation/create", json={
        "checkIn": entrada.isoformat(), "checkOut": salida.isoformat(),
        "card_token": TOKEN, "card_number": TOKEN,
        "rooms": [{"location": SEDE, "room_number": HABITACION,
                   "cost": 100, "extra_bed_price": 20, "extra_bed_or_not": 0}]})


def test_reserva_envia_un_correo_al_cliente(escenario, smtp_falso):
    r = reservar()
    assert r.status_code == 200, r.get_data(as_text=True)
    assert len(smtp_falso.enviados) == 1
    assert smtp_falso.enviados[0]["para"] == [CORREO_CLIENTE]
    assert smtp_falso.enviados[0]["asunto"]


def test_correo_contiene_los_datos_de_la_reserva(escenario, smtp_falso):
    r = reservar()
    reserva_id = str(r.get_json()["id"])
    texto = smtp_falso.enviados[0]["texto"]
    for dato in (reserva_id, ENTRADA.isoformat(), SALIDA.isoformat(), SEDE, str(HABITACION), "200"):
        assert dato in texto, f"El correo no incluye: {dato}"


def test_usa_la_configuracion_smtp_del_entorno(escenario, smtp_falso):
    reservar()
    assert smtp_falso.conexiones == [("smtp.prueba.local", 2525)]


def test_si_falla_el_envio_la_reserva_igual_se_crea(escenario, smtp_falso, caplog):
    smtp_falso.fallar = True
    with caplog.at_level(logging.ERROR):
        r = reservar()
    assert r.status_code == 200, r.get_data(as_text=True)
    filas = ejecutar("SELECT COUNT(*) FROM Fancy_Hotel.Reservation WHERE username = %s", (CLIENTE,))
    assert filas[0][0] == 1
    assert any(registro.levelno >= logging.ERROR for registro in caplog.records), \
        "El fallo del envío no quedó registrado con logging.ERROR"


def test_modo_consola_no_usa_smtp(escenario, smtp_falso, monkeypatch):
    monkeypatch.setenv("MAIL_MODE", "console")
    r = reservar()
    assert r.status_code == 200, r.get_data(as_text=True)
    assert smtp_falso.conexiones == []


def test_reserva_rechazada_no_envia_correo(escenario, smtp_falso):
    assert reservar().status_code == 200
    smtp_falso.enviados.clear()
    r = reservar()  # mismas fechas: la habitación ya está ocupada
    assert r.status_code == 409, r.get_data(as_text=True)
    assert smtp_falso.enviados == []
