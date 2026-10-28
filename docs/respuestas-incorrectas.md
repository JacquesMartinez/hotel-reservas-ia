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

