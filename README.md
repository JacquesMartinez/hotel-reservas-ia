Fancy Hotel: sistema de reservas en línea
=========================================

Proyecto base (CS 4400) migrado a Python 3. Backend Flask + Flask-RESTful con MySQL y frontend AngularJS.
Ver `docs/arquitectura.md` para el detalle de la arquitectura.

## Requisitos

- Python 3.12
- MySQL 8 o superior, en ejecución local

## Instalación

```bash
# 1. Entorno virtual y dependencias
python3.12 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 2. Configuración
cp .env.example .env              # completa DB_USER, DB_PASSWORD, etc.

# 3. Datos de prueba (crea la BD Fancy_Hotel si no existe y VACÍA todas sus tablas)
python fancyhotel/seed.py

# 4. Ejecutar
python fancyhotel/serve.py
```

Abre `http://localhost:5000` (o el puerto definido en `PORT`).

> **macOS:** el puerto 5000 lo ocupa *AirPlay Receiver*. Desactívalo en Ajustes del Sistema o usa otro puerto, p. ej. `PORT=5050` en `.env`.

## Variables de entorno (`.env`)

| Variable | Descripción | Por defecto |
|---|---|---|
| `DB_USER` | Usuario de MySQL | (obligatoria) |
| `DB_PASSWORD` | Contraseña de MySQL | (obligatoria) |
| `DB_HOST` | Host de MySQL | `127.0.0.1` |
| `DB_PORT` | Puerto de MySQL | `3306` |
| `PORT` | Puerto de la app Flask | `5000` |
| `MAIL_MODE` | `console` imprime el correo de confirmación en la terminal; `smtp` lo envía | `console` |
| `MAIL_HOST` | Servidor SMTP (solo modo `smtp`) | `localhost` |
| `MAIL_PORT` | Puerto SMTP (solo modo `smtp`) | `25` |
| `MAIL_FROM` | Remitente del correo | `no-reply@fancyhotel.local` |
| `MAIL_USER` | Usuario SMTP; si está vacío no se hace login | (vacía) |
| `MAIL_PASSWORD` | Contraseña SMTP | (vacía) |

`.env` está en `.gitignore`; nunca subas credenciales al repositorio.

## Correos en desarrollo (Mailpit)

Al crear una reserva se envía un correo de confirmación al email del cliente. Si el envío falla, la reserva se crea igual y el error queda en el log.

Por defecto (`MAIL_MODE=console`) el correo solo se imprime en la terminal donde corre `serve.py`. Para verlo como un correo real, usa [Mailpit](https://mailpit.axllent.org/), un servidor SMTP local que no entrega nada hacia afuera:

```bash
docker run -d -p 1025:1025 -p 8025:8025 axllent/mailpit
```

y en `.env`:

```
MAIL_MODE=smtp
MAIL_HOST=localhost
MAIL_PORT=1025
```

Reinicia la app, crea una reserva y abre la bandeja en http://localhost:8025.

## Datos semilla

`fancyhotel/seed.py` carga datos solo para desarrollo:

- 30 habitaciones (Standard, Family, Suite) en 5 sedes: Atlanta, Charlotte, Savannah, Orlando, Miami
- 1 manager y 4 clientes, cada cliente con una tarjeta de prueba
- Reservas históricas de los últimos 12 meses, sin solapamientos

| Rol | Usuario | Contraseña |
|---|---|---|
| Manager | `M2acz` | `manager123` |
| Cliente | `Cl3a8`, `Cyp7d`, `C196b`, `Cm2wd` | `cliente123` |

El rol se deduce de la primera letra del usuario: `C` cliente, `M` manager.

## Pruebas

```bash
pytest
```

Las pruebas no necesitan MySQL: la capa de datos se reemplaza por un mock (`tests/conftest.py`).
