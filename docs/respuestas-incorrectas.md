# Respuestas incorrectas de la IA

## RI-00: Título corto
- **Fecha / Issue:**
- **Herramienta:**
- **Qué se pidió:**
- **Qué respondió la IA:** (fragmento o captura)
- **Por qué es incorrecto:**
- **Cómo lo detectamos:** (revisión, prueba fallida, ejecución)
- **Corrección aplicada:**

# Respuestas incorrectas de la IA

## RI-01: Generalización incorrecta sobre la carga de librerías por http://
- **Fecha / Issue:** 2026-10-28 / Análisis de arquitectura (rama `docs/analisis-arquitectura`)
- **Herramienta:** [Herramienta de escritorio usada para el análisis]
- **Qué se pidió:** Analizar el proyecto completo sin modificar código, incluyendo problemas de seguridad.
- **Qué respondió la IA:** En el hallazgo S10 afirmó que las librerías del frontend "se cargan por http:// (contenido mixto) y sin SRI".
- **Por qué es incorrecto:** Solo Bootstrap 3.3.5 se carga por `http://` (maxcdn). jQuery y AngularJS se cargan por `https://` desde ajax.googleapis.com. La IA generalizó un problema de una librería a todas.
- **Cómo lo detectamos:** Revisión manual de las etiquetas `<link>` y `<script>` en `templates/index.html`.
- **Corrección aplicada:** En `arquitectura.md` se documentó que solo Bootstrap usa http. Al actualizar dependencias se cargarán todas por https.

## RI-02: Librería del calendario identificada por el nombre del archivo
- **Fecha / Issue:** 2026-10-28 / HU Calendario dinámico
- **Herramienta:** Claude (asistente de chat, usado para la planificación)
- **Qué se pidió:** Plan de implementación para la historia del calendario de disponibilidad.
- **Qué respondió la IA:** Indicó que el proyecto usa `bootstrap-datepicker` y que se bloquearan fechas con la opción `datesDisabled`. Ese criterio se incluyó en el texto del issue.
- **Por qué es incorrecto:** El archivo se llama `bootstrap-datepicker.js`, pero contiene **Eonasdan bootstrap-datetimepicker v4.15.35**, cuya opción es `disabledDates`. Usar `datesDisabled` no habría tenido efecto.
- **Cómo lo detectamos:** La herramienta de escritorio, al leer el contenido del archivo, identificó la librería correcta. El equipo lo confirmó abriendo el encabezado de `static/libs/bootstrap-datepicker.js`. Las dos IAs se contradecían y la duda se resolvió leyendo el código.
- **Corrección aplicada:** Se actualizó el criterio de aceptación del issue del calendario para usar `disabledDates` (Eonasdan v4).

# Respuestas incorrectas de la IA

## RI-03: El calendario de la Etapa 4 permitía reservas de 0 noches
- **Fecha / Issue:** 2026-10-28 / #4
- **Herramienta:** Claude Code
- **Qué se pidió:** limitar la salida a la primera noche ocupada posterior a la entrada.
- **Qué respondió la IA:** `limitCheckOut` fijaba `minDate(checkIn)`, de modo que la salida podía ser el mismo día que la entrada.
- **Por qué es incorrecto:** permitía reservas de 0 noches, que el sistema trata siempre como libres.
- **Cómo lo detectamos:** revisión. La misma IA lo reportó en sus observaciones finales.
- **Corrección aplicada:** la salida mínima pasó a ser la entrada + 1 día, y además se validó en el servidor (D-13).

## RI-04: La revalidación de la Etapa 3 no controlaba datos inválidos
- **Fecha / Issue:** 2026-10-28 / #4
- **Herramienta:** Claude Code
- **Qué se pidió:** revalidar la disponibilidad antes de insertar y responder 409 si la habitación no está libre.
- **Qué respondió la IA:** un bucle que accede a `room['room_number']` y `room['location']` sin validar los datos.
- **Por qué es incorrecto:** con datos faltantes o fechas mal formadas el endpoint respondía 500 en lugar de un error claro.
- **Cómo lo detectamos:** revisión, reportado por la IA.
- **Corrección aplicada:** validación con 400 para fechas y campos de las habitaciones, y aviso en pantalla (D-17).

## RI-05: El script de prueba en navegador falló en la primera corrida
- **Fecha / Issue:** 2026-10-28 / #4
- **Herramienta:** Claude Code
- **Qué se pidió:** verificar el frontend.
- **Qué respondió la IA:** un script e2e (`scratchpad/e2e/calendar.js`) con dos fallas en la primera ejecución.
- **Por qué es incorrecto:** según la IA, el error estaba en el script y no en la aplicación. Conviene confirmarlo revisando el script.
- **Cómo lo detectamos:** ejecución.
- **Corrección aplicada:** la IA corrigió el script y la segunda corrida pasó en las 4 zonas horarias.

## RI-06: La corrección de 0 noches quedó incompleta
- **Fecha / Issue:** 2026-10-28 / #4
- **Herramienta:** Claude Code
- **Qué se pidió:** "estructura que no se pueda reservar 0 noches".
- **Qué respondió la IA:** validó solo la creación de reservas.
- **Por qué es incorrecto:** modificar una reserva existente todavía permite 0 noches, tanto en el servidor como en su calendario.
- **Cómo lo detectamos:** la IA lo informó como pendiente.
- **Corrección aplicada:** pendiente de decisión.

## RI-07: Afirmó que no podía probar en un navegador
- **Fecha / Issue:** 2026-10-28 / #N
- **Herramienta:** Claude Code
- **Qué se pidió:** plan de verificación de la Etapa 4.
- **Qué respondió la IA:** que la interacción en el navegador le tocaba confirmarla al usuario, porque no podía abrir uno.
- **Por qué es incorrecto:** al implementar la etapa sí probó en Chrome headless con puppeteer-core, como ya había hecho en el issue anterior.
- **Cómo lo detectamos:** revisión, comparando el plan con el reporte de la Etapa 4.
- **Corrección aplicada:** ninguna necesaria. La prueba en navegador se hizo igual.

## RI-08: El ALTER "ejecutable en cada arranque" puede bloquear el arranque
- **Fecha / Issue:** 2026-10-28 / #N
- **Herramienta:** Claude Code
- **Qué se pidió:** un `ALTER TABLE ... MODIFY` en `init_db` que se pueda ejecutar en cada arranque sin error.
- **Qué respondió la IA:** que el ALTER se podía ejecutar en cada arranque y que MySQL no cambia nada ni da error.
- **Por qué es incorrecto:** no da error, pero con la app corriendo otro proceso que importa `db` (las pruebas de integración o `seed.py`) se queda esperando un bloqueo, porque la conexión de la app deja transacciones abiertas (relacionado con B4).
- **Cómo lo detectamos:** ejecución. La IA lo encontró durante las pruebas de la Etapa 4.
- **Corrección aplicada:** pendiente. Mientras tanto, detener la app antes de ejecutar las pruebas de integración o el seed.

## RI-09: Registró en los docs una decisión que el equipo no había tomado
- **Fecha / Issue:** 2026-10-28 / #N
- **Herramienta:** Claude Code
- **Qué se pidió:** corregir la inconsistencia de las D-08 duplicadas.
- **Qué respondió la IA:** además de renumerar, reemplazó en D-02 los marcadores "[Decidir… tabla Payment]" por "No se agrega la tabla Payment (ver D-08)", deducido de que el issue reutiliza Credit_Card.
- **Por qué es incorrecto:** registró como decisión del equipo algo que el equipo no había decidido. La IA misma pidió revisarlo.
- **Cómo lo detectamos:** revisión del reporte de la Etapa 1.
- **Corrección aplicada:** pendiente de confirmar o corregir D-02.

## RI-10: El precio se puede manipular enviando extra_bed_or_not como texto
- **Fecha / Issue:** 2026-10-28 / #N
- **Herramienta:** Claude Code
- **Qué se pidió:** calcular el total con los precios de la BD e ignorar los del cliente (S3).
- **Qué respondió la IA:** cobra la cama extra solo si `room['extra_bed_or_not'] == 1`.
- **Por qué es incorrecto:** si el cliente envía `"1"` (texto), la reserva se guarda con cama extra pero no se cobra. S3 queda abierto.
- **Cómo lo detectamos:** revisión. La IA lo reportó al terminar la Etapa 4.
- **Corrección aplicada:** pendiente. La IA propuso aceptar solo 0/1 y responder 400 en cualquier otro caso.

## RI-11: Agregó una función que no estaba en el plan aprobado
- **Fecha / Issue:** 2026-10-28 / #N
- **Herramienta:** Claude Code
- **Qué se pidió:** implementar la Etapa 2 según el plan aprobado.
- **Qué respondió la IA:** agregó `get_credit_card(username, token)`, que no estaba en el plan.
- **Por qué es incorrecto:** se desvía del plan aprobado, aunque la IA lo informó y la función reutiliza `get_credit_cards`.
- **Cómo lo detectamos:** la IA lo informó en "Cosas que difieren del plan".
- **Corrección aplicada:** ninguna. Se mantuvo porque la usan el 404 de DELETE, la tarjeta predeterminada y la Etapa 3.

## RI-12: El gráfico no siguió el plan para unir historial y previsión
- **Fecha / Issue:** 2026-10-28 / #N
- **Herramienta:** Claude Code
- **Qué se pidió:** implementar el plan aprobado.
- **Qué respondió la IA:** el plan decía que la previsión arrancaría en el último punto del historial para que la línea fuera continua. La implementación deja un hueco en la semana en curso, que no entra ni en el historial ni en la previsión.
- **Por qué es incorrecto:** el comportamiento difiere del plan aprobado, y en el reporte final se presentó como una "precisión" y no como un cambio.
- **Cómo lo detectamos:** revisión, comparando el plan con el reporte final.
- **Corrección aplicada:** ninguna. Falta decidir si se acepta el hueco o se une la línea como estaba en el plan.

## RI-13: La tabla redondea distinto que el backend
- **Fecha / Issue:** 2026-10-28 / #N
- **Herramienta:** Claude Code
- **Qué se pidió:** tabla de semanas previstas con la sugerencia de precio.
- **Qué respondió la IA:** la tabla muestra porcentajes enteros, mientras que el backend compara con 4 decimales.
- **Por qué es incorrecto:** una ocupación de 79,6 % aparece como "80 %" con "No change", lo que parece contradecir el umbral de +15 %.
- **Cómo lo detectamos:** revisión. La IA lo reportó en sus observaciones.
- **Corrección aplicada:** pendiente. Una opción es mostrar un decimal.

## RI-14: Usó una cookie de sesión firmada con la SECRET_KEY local para entrar como manager
- **Fecha / Issue:** 2026-10-28 / #N
- **Herramienta:** Claude Code
- **Qué se pidió:** verificar las vistas del manager.
- **Qué respondió la IA:** como el login de M2acz respondía 401, firmó una cookie de sesión con la `SECRET_KEY` del `.env` para sacar las capturas.
- **Por qué es incorrecto:** saltó la autenticación con la clave secreta sin pedir autorización, aunque lo informó y no cambió credenciales.
- **Cómo lo detectamos:** revisión del reporte final.
- **Corrección aplicada:** ninguna. Lo correcto habría sido avisar del 401 y pedir que se ejecutara `seed.py`.