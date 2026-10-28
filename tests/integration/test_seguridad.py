"""
Pruebas de integración del issue "Seguridad de cuenta y acceso por rol".

Contrato que deben cumplir (ver prompt del issue):
  - Login correcto -> 200 y guarda en flask.session: "username" y "role"
    ("customer" o "manager"). Login incorrecto -> 401.
  - GET  /api/me     -> 200 {"username": ..., "role": ...} con sesión; 401 sin sesión.
  - POST /api/logout -> 200 y borra la sesión.
  - Reservas, tarjetas y reseñas requieren sesión (401 sin ella) y usan el
    usuario de la sesión, ignorando el "username" de la petición.
  - /api/reports/* -> 401 sin sesión, 403 para clientes, 200 para managers.
  - Contraseñas guardadas con hash de werkzeug (columna ampliada).

Contra el código actual estas pruebas FALLAN: el servidor no tiene sesión,
no existen /api/me ni /api/logout, los reportes son públicos y un cliente
puede ver las tarjetas de otro enviando su username (IDOR).
Si la columna password todavía es VARCHAR(16), el fixture guarda la clave
en texto plano para que el login del código actual funcione y las fallas
muestren los problemas reales en lugar de errores de inserción.

Ejecutar desde la raíz:  python -m pytest tests/integration/test_seguridad.py -v
"""
from datetime import date, timedelta

import pytest
from werkzeug.security import check_password_hash, generate_password_hash

import db  # noqa: E402  (conexión real de la app)
from serve import app  # noqa: E402

CLIENTE_1 = "CSEC1"
CLIENTE_2 = "CSEC2"
CLIENTE_NUEVO = "CSEC3"
MANAGER = "MSEC1"
CLAVE = "clave-segura-123"
TARJETA_CLIENTE_2 = "4000000000009902"
REPORTES = ["/api/reports/reservation", "/api/reports/popularRoom", "/api/reports/revenue"]


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


def limpiar():
    clientes = (CLIENTE_1, CLIENTE_2, CLIENTE_NUEVO)
    ejecutar("DELETE FROM Fancy_Hotel.Credit_Card WHERE username IN (%s, %s, %s) OR card_number = %s",
             clientes + (TARJETA_CLIENTE_2,))
    ejecutar("DELETE FROM Fancy_Hotel.Customer WHERE username IN (%s, %s, %s)", clientes)
    ejecutar("DELETE FROM Fancy_Hotel.Manager WHERE username = %s", (MANAGER,))


def clave_para_guardar():
    """Hash si la columna lo admite; texto plano si sigue siendo VARCHAR(16)."""
    filas = ejecutar("""SELECT CHARACTER_MAXIMUM_LENGTH FROM information_schema.COLUMNS
                        WHERE TABLE_SCHEMA = 'Fancy_Hotel' AND TABLE_NAME = 'Customer'
                        AND COLUMN_NAME = 'password'""")
    hash_clave = generate_password_hash(CLAVE)
    return hash_clave if filas and filas[0][0] >= len(hash_clave) else CLAVE


@pytest.fixture
def usuarios():
    limpiar()
    clave = clave_para_guardar()
    for usuario in (CLIENTE_1, CLIENTE_2):
        ejecutar("""INSERT INTO Fancy_Hotel.Customer (username, password, first_name, last_name, email)
                    VALUES (%s, %s, 'Test', 'Seguridad', %s)""",
                 (usuario, clave, f"{usuario.lower()}@example.com"))
    ejecutar("INSERT INTO Fancy_Hotel.Manager (username, password) VALUES (%s, %s)", (MANAGER, clave))
    ejecutar("""INSERT INTO Fancy_Hotel.Credit_Card (card_number, name, cvv, expiration_date, username)
                VALUES (%s, 'Cliente Dos', '123', %s, %s)""",
             (TARJETA_CLIENTE_2, date.today() + timedelta(days=3 * 365), CLIENTE_2))
    yield
    limpiar()


@pytest.fixture
def http():
    app.config["TESTING"] = True
    return app.test_client()


def login(http, usuario, clave=CLAVE):
    return http.post("/api/login", json={"username": usuario, "password": clave})


# --- Contraseñas -----------------------------------------------------------

def test_registro_guarda_la_contrasena_con_hash(usuarios, http):
    r = http.post("/api/register", json={
        "username": CLIENTE_NUEVO, "email": "csec3@example.com", "password": CLAVE,
        "firstName": "Nuevo", "lastName": "Usuario"})
    assert r.status_code == 200, r.get_data(as_text=True)
    filas = ejecutar("SELECT password FROM Fancy_Hotel.Customer WHERE username = %s", (CLIENTE_NUEVO,))
    guardada = filas[0][0]
    assert guardada != CLAVE, "La contraseña se guardó en texto plano"
    assert check_password_hash(guardada, CLAVE), "El hash no es válido o quedó truncado"


# --- Login, sesión y logout -------------------------------------------------

def test_login_correcto(usuarios, http):
    assert login(http, CLIENTE_1).status_code == 200


def test_login_incorrecto(usuarios, http):
    assert login(http, CLIENTE_1, "otra-clave").status_code == 401


def test_me_sin_sesion_responde_401(http):
    assert http.get("/api/me").status_code == 401


def test_me_devuelve_usuario_y_rol_del_cliente(usuarios, http):
    login(http, CLIENTE_1)
    r = http.get("/api/me")
    assert r.status_code == 200, r.get_data(as_text=True)
    assert r.get_json() == {"username": CLIENTE_1, "role": "customer"}


def test_me_devuelve_rol_manager(usuarios, http):
    login(http, MANAGER)
    assert http.get("/api/me").get_json() == {"username": MANAGER, "role": "manager"}


def test_logout_cierra_la_sesion(usuarios, http):
    login(http, CLIENTE_1)
    assert http.post("/api/logout").status_code == 200
    assert http.get("/api/me").status_code == 401
    assert http.get("/api/payment").status_code == 401


# --- Acceso a datos del cliente (S1 / IDOR) ---------------------------------

def test_tarjetas_sin_sesion_responde_401(usuarios, http):
    assert http.get("/api/payment", query_string={"username": CLIENTE_2}).status_code == 401


def test_cliente_no_ve_tarjetas_de_otro(usuarios, http):
    login(http, CLIENTE_1)
    r = http.get("/api/payment", query_string={"username": CLIENTE_2})
    assert r.status_code == 200, r.get_data(as_text=True)
    assert TARJETA_CLIENTE_2 not in r.get_data(as_text=True), \
        "CSEC1 pudo ver la tarjeta de CSEC2 enviando su username (IDOR)"


def test_cliente_ve_sus_propias_tarjetas(usuarios, http):
    login(http, CLIENTE_2)
    r = http.get("/api/payment")
    assert r.status_code == 200, r.get_data(as_text=True)
    assert TARJETA_CLIENTE_2 in r.get_data(as_text=True)


# --- Reportes (S8) ----------------------------------------------------------

@pytest.mark.parametrize("ruta", REPORTES)
def test_reportes_sin_sesion_responden_401(http, ruta):
    assert http.get(ruta).status_code == 401


@pytest.mark.parametrize("ruta", REPORTES)
def test_reportes_para_cliente_responden_403(usuarios, http, ruta):
    login(http, CLIENTE_1)
    assert http.get(ruta).status_code == 403


@pytest.mark.parametrize("ruta", REPORTES)
def test_reportes_para_manager_responden_200(usuarios, http, ruta):
    login(http, MANAGER)
    assert http.get(ruta).status_code == 200


# --- Lo público sigue siendo público -----------------------------------------

def test_busqueda_sigue_siendo_publica(http):
    hoy = date.today()
    r = http.get("/api/searchRoom", query_string={
        "location": "Atlanta",
        "checkIn": (hoy + timedelta(days=200)).isoformat(),
        "checkOut": (hoy + timedelta(days=202)).isoformat()})
    assert r.status_code == 200
