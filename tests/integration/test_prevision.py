"""
Pruebas de integración del issue "Gráficos de previsión de demanda".

Contrato:
  Reservation.created_at
    - DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP (migración idempotente en init_db).
  Reportes existentes (solo manager) con parámetros opcionales from / to (YYYY-MM-DD)
    - Claves de mes con formato "YYYY-MM": {"YYYY-MM": {"Sede": valor}}
    - Excluyen reservas canceladas.
    - /api/reports/revenue suma cada reserva UNA vez aunque tenga varias habitaciones (B8).
    - /api/reports/reservation cuenta reservas, no habitaciones (B9).
  GET /api/reports/forecast?location=X&weeks=8&history_weeks=12   (solo manager)
    - Semanas de lunes a domingo. "week_start" es el lunes (YYYY-MM-DD).
    - Ocupación de una semana = noches-habitación reservadas (no canceladas)
      / (habitaciones de la sede x 7).
    - history: las history_weeks semanas completas anteriores a la semana actual,
      en orden ascendente: [{"week_start", "occupancy"}].
    - forecast: weeks semanas a partir del PRÓXIMO lunes:
      [{"week_start", "occupancy", "booked", "price_change_pct"}]
        booked    = ocupación ya reservada para esa semana
        occupancy = max(promedio de las últimas 4 semanas del historial, booked)
        price_change_pct = +15 si occupancy >= 0.8 ; -10 si occupancy <= 0.3 ; 0 en otro caso
    - "method": texto que explica el cálculo.
    - Sede sin habitaciones o sin historial -> 200 con ocupación 0 (sin errores).
    - Sin location -> 400.

Ejecutar desde la raíz:  python -m pytest tests/integration/test_prevision.py -v
"""
from datetime import date, datetime, timedelta

import pytest

import db  # noqa: E402
from serve import app  # noqa: E402

SEDE = "TestPrev"
SEDE_INGRESOS = "TestRev"
SEDE_VACIA = "TestNada"
CLIENTE = "CPREV"

HOY = date.today()
LUNES_ACTUAL = HOY - timedelta(days=HOY.weekday())
PROXIMO_LUNES = LUNES_ACTUAL + timedelta(days=7)


def lunes(semanas):
    """Lunes de la semana relativa a la actual (-1 = la anterior, +1 = la próxima)."""
    return LUNES_ACTUAL + timedelta(days=7 * semanas)


def ejecutar(sql, params=()):
    conexion = db.mysqldb.connection
    cur = conexion.cursor()
    try:
        cur.execute(sql, params)
        filas = cur.fetchall() if cur.with_rows else None
        conexion.commit()
        return filas, cur.lastrowid
    finally:
        cur.close()


def limpiar():
    for sede in (SEDE, SEDE_INGRESOS, SEDE_VACIA):
        ejecutar("DELETE FROM Fancy_Hotel.Reserves_Extra_Bed WHERE location = %s", (sede,))
        ejecutar("DELETE FROM Fancy_Hotel.Room WHERE location = %s", (sede,))
    ejecutar("DELETE FROM Fancy_Hotel.Reservation WHERE username = %s", (CLIENTE,))
    ejecutar("DELETE FROM Fancy_Hotel.Customer WHERE username = %s", (CLIENTE,))


def reservar(sede, habitaciones, entrada, noches, total=0.0, cancelada=False):
    _, rid = ejecutar(
        """INSERT INTO Fancy_Hotel.Reservation
           (checkin_date, checkout_date, total_cost, username, card_number, cancelled_or_not)
           VALUES (%s, %s, %s, %s, NULL, %s)""",
        (entrada, entrada + timedelta(days=noches), total, CLIENTE, "1" if cancelada else "0"))
    for numero in habitaciones:
        ejecutar("""INSERT INTO Fancy_Hotel.Reserves_Extra_Bed
                    (location, room_number, reservation_id, extra_bed_or_not) VALUES (%s, %s, %s, '0')""",
                 (sede, numero, rid))
    return rid


@pytest.fixture
def base():
    limpiar()
    ejecutar("""INSERT INTO Fancy_Hotel.Customer (username, password, first_name, last_name, email)
                VALUES (%s, 'x', 'Test', 'Prevision', 'cprev@example.com')""", (CLIENTE,))
    for sede in (SEDE, SEDE_INGRESOS):
        for numero in (701, 702):
            ejecutar("""INSERT INTO Fancy_Hotel.Room
                        (location, room_number, type, room_cost, capacity, extra_bed_price)
                        VALUES (%s, %s, 'Standard', 100, 2, 20)""", (sede, numero))
    yield
    limpiar()


@pytest.fixture
def historial(base):
    """
    Sede con 2 habitaciones (capacidad 14 noches-habitación por semana).
      semana -1: 7 noches        -> 0.5
      semana -2: 14 noches       -> 1.0
      semana -3: solo cancelada  -> 0.0
      semana -4: 7 noches        -> 0.5
      promedio últimas 4 = 0.5
      semana +2 (segunda de la previsión): ya reservada completa -> booked 1.0
    """
    reservar(SEDE, [701], lunes(-1), 7)
    reservar(SEDE, [701, 702], lunes(-2), 7)
    reservar(SEDE, [701], lunes(-3), 7, cancelada=True)
    reservar(SEDE, [702], lunes(-4), 7)
    reservar(SEDE, [701, 702], lunes(+2), 7)


def http_con_rol(rol):
    app.config["TESTING"] = True
    http = app.test_client()
    with http.session_transaction() as sesion:
        sesion["username"] = "MPREV" if rol == "manager" else CLIENTE
        sesion["role"] = rol
    return http


def prevision(http=None, **params):
    http = http or http_con_rol("manager")
    consulta = {"location": SEDE, "weeks": 4, "history_weeks": 6}
    consulta.update(params)
    return http.get("/api/reports/forecast", query_string=consulta)


# --- created_at --------------------------------------------------------------

def test_reservation_tiene_created_at_con_valor_por_defecto(base):
    rid = reservar(SEDE, [701], lunes(+5), 2)
    filas, _ = ejecutar("SELECT created_at FROM Fancy_Hotel.Reservation WHERE reservation_id = %s", (rid,))
    assert filas[0][0] is not None
    assert abs(filas[0][0] - datetime.now()) < timedelta(days=1)


# --- Reportes corregidos (B8, B9) --------------------------------------------

def rango_mes_anterior():
    fin = HOY.replace(day=1) - timedelta(days=1)
    inicio = fin.replace(day=1)
    return inicio, fin


def test_ingresos_no_duplican_reservas_de_varias_habitaciones(base):
    inicio, fin = rango_mes_anterior()
    reservar(SEDE_INGRESOS, [701, 702], inicio + timedelta(days=2), 2, total=500.0)
    reservar(SEDE_INGRESOS, [701], inicio + timedelta(days=10), 1, total=300.0, cancelada=True)
    r = http_con_rol("manager").get("/api/reports/revenue",
                                    query_string={"from": inicio.isoformat(), "to": fin.isoformat()})
    assert r.status_code == 200, r.get_data(as_text=True)
    mes = inicio.strftime("%Y-%m")
    assert float(r.get_json()[mes][SEDE_INGRESOS]) == pytest.approx(500.0)


def test_reporte_de_reservas_cuenta_reservas_no_habitaciones(base):
    inicio, fin = rango_mes_anterior()
    reservar(SEDE_INGRESOS, [701, 702], inicio + timedelta(days=2), 2, total=500.0)
    reservar(SEDE_INGRESOS, [701], inicio + timedelta(days=10), 1, total=300.0, cancelada=True)
    r = http_con_rol("manager").get("/api/reports/reservation",
                                    query_string={"from": inicio.isoformat(), "to": fin.isoformat()})
    assert r.status_code == 200, r.get_data(as_text=True)
    assert r.get_json()[inicio.strftime("%Y-%m")][SEDE_INGRESOS] == 1


# --- Previsión ----------------------------------------------------------------

def test_prevision_solo_para_manager(historial):
    assert prevision(http_con_rol("customer")).status_code == 403


def test_prevision_sin_location_responde_400(historial):
    http = http_con_rol("manager")
    assert http.get("/api/reports/forecast").status_code == 400


def test_prevision_estructura(historial):
    r = prevision()
    assert r.status_code == 200, r.get_data(as_text=True)
    datos = r.get_json()
    assert datos["location"] == SEDE
    assert datos["method"]
    assert len(datos["history"]) == 6
    assert len(datos["forecast"]) == 4
    assert datos["history"][-1]["week_start"] == lunes(-1).isoformat()
    assert datos["forecast"][0]["week_start"] == PROXIMO_LUNES.isoformat()


def test_historial_calcula_ocupacion_y_excluye_canceladas(historial):
    historia = prevision().get_json()["history"]
    ultimas4 = [s["occupancy"] for s in historia[-4:]]   # semanas -4, -3, -2, -1
    assert ultimas4 == pytest.approx([0.5, 0.0, 1.0, 0.5], abs=0.01)


def test_prevision_usa_promedio_movil_y_lo_ya_reservado(historial):
    semanas = prevision().get_json()["forecast"]
    # Próxima semana: nada reservado -> promedio 0.5 -> sin cambio de precio
    assert semanas[0]["booked"] == pytest.approx(0.0, abs=0.01)
    assert semanas[0]["occupancy"] == pytest.approx(0.5, abs=0.01)
    assert semanas[0]["price_change_pct"] == 0
    # Segunda semana: ya reservada completa -> 1.0 -> subir precio
    assert semanas[1]["booked"] == pytest.approx(1.0, abs=0.01)
    assert semanas[1]["occupancy"] == pytest.approx(1.0, abs=0.01)
    assert semanas[1]["price_change_pct"] == 15


def test_demanda_baja_sugiere_bajar_precio(base):
    reservar(SEDE, [701], lunes(-1), 1)          # 1/14 en una sola semana
    semanas = prevision().get_json()["forecast"]
    assert semanas[0]["occupancy"] <= 0.3
    assert semanas[0]["price_change_pct"] == -10


def test_sede_sin_historial_no_falla(base):
    r = prevision()
    assert r.status_code == 200, r.get_data(as_text=True)
    assert all(s["occupancy"] == 0 for s in r.get_json()["history"])


def test_sede_sin_habitaciones_no_falla(base):
    r = prevision(location=SEDE_VACIA)
    assert r.status_code == 200, r.get_data(as_text=True)
    assert all(s["occupancy"] == 0 for s in r.get_json()["forecast"])
