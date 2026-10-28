# Decisiones tomadas por humanos

## D-00: Título corto
- **Fecha / Issue:**
- **Contexto:** qué problema había
- **Propuesta de la IA:**
- **Decisión del equipo:**
- **Justificación:**
- **Rechazado de la IA (si aplica):**

# Decisiones tomadas por humanos

## D-01: Implementar seguridad (sesión y roles) antes del pago con datos guardados
- **Fecha / Issue:** 2026-10-28 / HU Seguridad de cuenta y HU Reserva con datos guardados
- **Contexto:** El análisis mostró que el servidor no tiene autenticación (S1): cada endpoint confía en el `username` que recibe. Así no se puede cumplir el criterio "un usuario no puede usar la tarjeta guardada de otro".
- **Propuesta de la IA:** El plan inicial ordenaba: calendario → pago guardado → previsión → historias adicionales.
- **Decisión del equipo:** Nuevo orden: tarea técnica (migración) → calendario → **seguridad** → pago guardado → previsión → correo.
- **Justificación:** La historia de pago guardado depende de saber en el servidor quién es el usuario. Implementarla antes obligaría a rehacerla.
- **Rechazado de la IA (si aplica):** Orden original del plan.

## D-02: No almacenar el número completo de tarjeta ni el CVV
- **Fecha / Issue:** 2026-10-28 / HU Reserva con datos guardados
- **Contexto:** La tabla `Credit_Card` guarda el número completo (PAN) y el CVV en texto plano, y la API devuelve el CVV (S2). Guardar el CVV está prohibido por PCI DSS.
- **Propuesta de la IA:** Tokenizar con una pasarela de pago y guardar token, últimos 4 dígitos, marca y vencimiento; agregar una tabla `Payment`.
- **Decisión del equipo:** Guardar solo un **token simulado**, los últimos 4 dígitos y el vencimiento. No integrar una pasarela real. [Decidir si se agrega la tabla `Payment` o se deja fuera de alcance.]
- **Justificación:** Cumple el objetivo de la historia sin manejar datos sensibles. Una pasarela real queda fuera del alcance del proyecto.
- **Rechazado de la IA (si aplica):** Integración con pasarela real. [Completar según lo que se decida sobre la tabla `Payment`.]

## D-03: Historias de usuario adicionales elegidas
- **Fecha / Issue:** 2026-10-28 / Backlog
- **Contexto:** El enunciado pide mínimo 2 historias adicionales. La propuesta inicial (cancelar/modificar reserva) ya existía en el proyecto (ver RI-03).
- **Propuesta de la IA:** Seguridad de cuenta y acceso por rol; confirmación por correo; alternativa: lista de espera.
- **Decisión del equipo:** "Seguridad de cuenta y acceso por rol" y "Confirmación de reserva por correo".
- **Justificación:** La de seguridad corrige los hallazgos más graves (S1, S5, S8) y habilita la historia de pago. La de correo es acotada y fácil de probar automáticamente.
- **Rechazado de la IA (si aplica):** "Cancelar o modificar reserva" (ya existía); "lista de espera" (queda como opcional).

## D-04: Usar el datetimepicker existente en lugar de agregar otra librería de calendario
- **Fecha / Issue:** 2026-10-28 / HU Calendario dinámico
- **Contexto:** El proyecto ya carga Eonasdan bootstrap-datetimepicker v4, que permite bloquear fechas con `disabledDates`.
- **Propuesta de la IA:** El plan inicial mencionaba FullCalendar como posible opción.
- **Decisión del equipo:** Reutilizar el datetimepicker existente con `disabledDates`.
- **Justificación:** Evita dependencias nuevas y cambios grandes en las vistas; cumple el criterio de la historia.
- **Rechazado de la IA (si aplica):** Agregar FullCalendar.

## D-05: Alcance de los bugs encontrados en el análisis
- **Fecha / Issue:** 2026-10-28 / Backlog
- **Contexto:** El análisis encontró 15 bugs (B1–B15).
- **Propuesta de la IA:** Listado de todos los bugs con su ubicación.
- **Decisión del equipo:** Corregir dentro de cada historia los bugs que la afectan (B1 y B2 en calendario; B8 y B9 en previsión; B13 en la migración). Los demás se registran como issues con etiqueta `bug`, sin compromiso de resolverlos.
- **Justificación:** Mantener el foco en las historias de usuario evaluadas, dejando trazabilidad del resto.
- **Rechazado de la IA (si aplica):** —

## D-06: Rama base para la migración a Python 3
- **Fecha / Issue:** 2026-10-28 / #___
- **Contexto:** La rama `feat/seguridad-sesion-roles` necesita partir de una base ya migrada a Python 3, y la migración no existía.
- **Propuesta de la IA:** Hacer primero la migración en `chore/migracion-python3` y crear después `feat/seguridad-sesion-roles` a partir de ella.
- **Decisión del equipo:** Aceptada. Se hace la migración en `chore/migracion-python3` y se abre un PR para su aprobación. El issue de seguridad continúa cuando el PR esté aprobado.
- **Justificación:** Separar la migración de la funcionalidad de seguridad permite revisar cada cambio por separado y evita mezclar problemas de compatibilidad con la lógica nueva.
- **Rechazado de la IA (si aplica):** No aplica.

## D-07: Script de datos de prueba `seed.py`
- **Fecha / Issue:** 2026-10-28 / #___
- **Contexto:** Para probar sesión y roles hacen falta usuarios de prueba, y no había un script que los creara. Los nombres deben tener 5 caracteres y empezar por `C` (cliente) o `M` (manager).
- **Propuesta de la IA:** Crear `fancyhotel/seed.py` con usuarios de prueba para cada rol.
- **Decisión del equipo:** Aceptada. La IA crea `fancyhotel/seed.py` con nombres de usuario aleatorios: clientes `C4Q7X`, `C8N2L`; managers `M3K9T`, `M6W1R`.
- **Justificación:** Tener datos de prueba reproducibles facilita probar los permisos por rol sin crear usuarios a mano.
- **Rechazado de la IA (si aplica):** No aplica.

## D-08: Gestión de configuración con `.env`
- **Fecha / Issue:** 2026-10-28 / #___
- **Contexto:** Las credenciales y la configuración sensible no deben estar en el código ni subirse al repositorio.
- **Propuesta de la IA:** Agregar `python-dotenv`, `.env.example` y un `.gitignore` que excluya `.env`.
- **Decisión del equipo:** Aceptada en su totalidad.
- **Justificación:** Mantiene los secretos fuera del control de versiones y documenta qué variables necesita el proyecto.
- **Rechazado de la IA (si aplica):** No aplica.

# Decisiones tomadas por humanos

## D-08: Rama de trabajo para el issue
- **Fecha / Issue:** 2026-10-28 / #4
- **Contexto:** `main` tenía cambios sin commitear (la reorganización de `tests/` y `pytest.ini`). La rama `feature/calendario-disponibilidad` era anterior a la migración a Python 3.
- **Propuesta de la IA:** trabajar en el árbol actual sin ramas, o recrear la rama desde `main`.
- **Decisión del equipo:** usar `feature/calendario-disponibilidad`, actualizada desde `main`, sin commits.
- **Justificación:** aislar el trabajo del issue. La rama no tenía commits propios ni existía en el remoto.
- **Rechazado de la IA (si aplica):** trabajar directamente en `main`.

## D-09: El parámetro `to` es inclusivo
- **Fecha / Issue:** 2026-10-28 / #4
- **Contexto:** no estaba definido si `to` contaba como la última noche del periodo.
- **Propuesta de la IA:** incluir tanto `from` como `to`.
- **Decisión del equipo:** aceptada.
- **Justificación:** coincide con la forma en que el calendario consulta el periodo.
- **Rechazado de la IA (si aplica):** —

## D-10: Sede sin habitaciones del tipo elegido (decisión inicial, revertida por D-16)
- **Fecha / Issue:** 2026-10-28 / #4
- **Contexto:** si aplicaba D-06 al pie de la letra, una sede sin habitaciones de ese tipo tendría todas las noches ocupadas.
- **Propuesta de la IA:** aplicar D-06 tal cual y marcar todas las noches como ocupadas.
- **Decisión del equipo:** devolver `[]`.
- **Justificación:** [completar]
- **Rechazado de la IA (si aplica):** la recomendación de aplicar D-06 literalmente.

## D-11: No filtrar los resultados de búsqueda por tipo
- **Fecha / Issue:** 2026-10-28 / #4
- **Contexto:** `/api/searchRoom` devuelve todos los tipos, mientras que el calendario se basa en un solo tipo.
- **Propuesta de la IA:** agregar `| filter:{room_type: roomType}:true` al `ng-repeat`, sin aplicarlo por defecto.
- **Decisión del equipo:** no filtrar.
- **Justificación:** está fuera del alcance del issue.
- **Rechazado de la IA (si aplica):** el filtro opcional.

## D-12: No abordar la condición de carrera entre reservas simultáneas
- **Fecha / Issue:** 2026-10-28 / #4
- **Contexto:** la revalidación de la Etapa 3 no usa bloqueo ni transacción.
- **Propuesta de la IA:** dejarlo como observación, ya que se relaciona con B3 y B4.
- **Decisión del equipo:** rechazado, se deja como está.
- **Justificación:** corresponde a B3/B4, fuera del issue.
- **Rechazado de la IA (si aplica):** —

## D-13: Prohibir las reservas de 0 noches
- **Fecha / Issue:** 2026-10-28 / #4
- **Contexto:** el calendario permitía que la salida coincidiera con la entrada y el servidor no validaba las fechas (B5).
- **Propuesta de la IA:** reportado como observación.
- **Decisión del equipo:** aprobado. Se exige al menos una noche, tanto en el servidor como en el calendario.
- **Justificación:** una reserva de 0 noches hace que la habitación aparezca siempre libre.
- **Rechazado de la IA (si aplica):** —

## D-14: Mantener la interacción entre los pickers de entrada y salida
- **Fecha / Issue:** 2026-10-28 / #4
- **Contexto:** para mover la entrada más allá de la salida actual, primero hay que mover la salida (comportamiento del código existente).
- **Propuesta de la IA:** reportado como observación.
- **Decisión del equipo:** rechazado, se deja como está.
- **Justificación:** es comportamiento existente y está fuera del issue.
- **Rechazado de la IA (si aplica):** —

## D-15: No ampliar la ventana de 6 meses
- **Fecha / Issue:** 2026-10-28 / #4
- **Contexto:** después de 6 meses el calendario no bloquea ninguna fecha.
- **Propuesta de la IA:** reportado como observación.
- **Decisión del equipo:** rechazado.
- **Justificación:** el 409 de la Etapa 3 ya frena esas reservas.
- **Rechazado de la IA (si aplica):** —

## D-16: Revertir D-10 y marcar todas las noches como ocupadas
- **Fecha / Issue:** 2026-10-28 / #4
- **Contexto:** con `[]`, el calendario quedaba abierto para un tipo que la sede no tiene.
- **Propuesta de la IA:** la recomendación original de D-10.
- **Decisión del equipo:** corregir. Ahora todas las noches se marcan como ocupadas.
- **Justificación:** el calendario no debe ofrecer fechas imposibles.
- **Rechazado de la IA (si aplica):** —

## D-17: Validar los datos de entrada al crear una reserva
- **Fecha / Issue:** 2026-10-28 / #4
- **Contexto:** `/api/reservation/create` respondía 500 con fechas mal formadas o con habitaciones incompletas.
- **Propuesta de la IA:** reportado como observación.
- **Decisión del equipo:** aprobado. Se responde 400 con un mensaje claro y el frontend muestra el motivo.
- **Justificación:** el usuario debe saber por qué falla la reserva.
- **Rechazado de la IA (si aplica):** —

## D-18: Excepción a la regla para actualizar el docstring de las pruebas
- **Fecha / Issue:** 2026-10-28 / #4
- **Contexto:** el docstring de `test_disponibilidad.py` tenía la ruta vieja, y la regla original prohibía modificar ese archivo.
- **Propuesta de la IA:** reportado como observación.
- **Decisión del equipo:** aprobado, cambiando solo esa línea del docstring.
- **Justificación:** la documentación debe reflejar la ruta actual. No afecta al código de las pruebas.
- **Rechazado de la IA (si aplica):** —