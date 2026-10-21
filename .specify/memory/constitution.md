<!--
Sync Impact Report
- Versión: plantilla → 1.0.0 (primera ratificación)
- Principios añadidos: I Simplicidad, II Reanudable e idempotente, III Datos del cliente fuera del
  repo, IV Reversibilidad, V Respetar cuotas y recursos, VI Verificación con evidencia
- Secciones añadidas: Restricciones de operación, Flujo de trabajo, Gobierno
- Secciones eliminadas: ninguna
- TODO diferidos: ninguno
-->

# google-chat-backup Constitution

## Core Principles

### I. Simplicidad

- Un único script Python (`scripts/gchat_backup.py`), sin servicios, bases de datos ni demonios.
- La salida son carpetas legibles: una por chat, con el JSON original de la API y `attachments/`.
  Nada de formatos propios que haya que convertir para leerlos.
- Toda la configuración entra por variables `GCHAT_*`, también desde `scripts/.env`. Cada
  variable nueva MUST tener un valor por defecto que funcione sin tocarla.
- Una funcionalidad que añada una dependencia, un proceso aparte o un paso manual MUST
  justificar en su plan por qué no basta algo más simple.

Razón: lo ejecutan tres personas una sola vez antes del apagón de Workspace, y el responsable
pidió explícitamente nada complejo.

### II. Reanudable e idempotente

- Relanzar el script MUST NOT repetir descargas completas ni duplicar carpetas de chats.
- Un corte (Ctrl-C, disco lleno, red, cuota) MUST dejar datos coherentes: escritura atómica de
  JSON y adjuntos a `.part` renombrados solo al terminar.
- La identidad de un chat es su id de la API, no su nombre: un cambio de nombre no crea carpeta
  nueva.

Razón: las exportaciones tardan horas y se interrumpen; repetir trabajo cuesta tiempo y cuota.

### III. Datos del cliente fuera del repositorio

- 0 credenciales, 0 nombres de cliente, 0 identificadores de proyecto y 0 datos exportados en git.
- El hook `pre-commit` (`core.hooksPath .githooks`) con la denylist local MUST estar activo.
- La salida del backup vive fuera del repositorio (carpeta de Dropbox); los ficheros locales con
  datos sensibles (`.env`, `terraform.tfvars`, `token.json`, `client_secret_*`) están ignorados.

Razón: el repositorio es compartible y los datos pertenecen a un cliente.

### IV. Reversibilidad

- Todo lo activado en GCP MUST revertirse con `terraform destroy` más los pasos de
  `docs/REVERTIR.md`.
- Terraform gestiona solo lo que tiene API; lo manual está documentado en `docs/MANUAL_STEPS.md`.

Razón: el proyecto GCP es compartido con el cliente y debe quedar como estaba.

### V. Respetar cuotas y recursos

- El script MUST NOT superar las cuotas publicadas de la API de Google Chat: ante un 429 o un
  5xx reintenta con backoff exponencial y nunca lanza más peticiones simultáneas de las que el
  usuario configure.
- El script MUST NOT llenar el disco: se detiene limpio por debajo de `GCHAT_MIN_FREE_GB`.
- Cualquier forma de paralelismo MUST ser configurable, con valor por defecto conservador.

Razón: un bloqueo por cuota o un disco lleno interrumpen el backup y pueden afectar a otras
cargas del proyecto compartido o del equipo.

### VI. Verificación con evidencia

- Cada cambio se prueba contra datos reales o con una prueba que demuestre que el mecanismo
  falla cuando debe (positivo y negativo).
- Los informes dan recuentos y tamaños, nunca contenido de mensajes ni nombres de chats.

Razón: un backup que parece completo y no lo es se descubre cuando ya no hay vuelta atrás.

## Restricciones de operación

- Python 3.9+ y solo las dependencias de Google (`google-api-python-client`,
  `google-auth-oauthlib`); el resto, biblioteca estándar.
- Autenticación de usuario (OAuth de escritorio): solo se exporta lo que ve quien lo ejecuta.
- Documentación y comentarios en castellano; nombres de carpetas de salida en inglés, con fecha
  ISO (`AAAA-MM-DD_<chat>`).

## Flujo de trabajo

- Cambios funcionales del script pasan por Spec Kit (`/speckit-specify` → `/speckit-plan` →
  `/speckit-tasks` → `/speckit-implement`).
- Antes de cada commit: `py_compile` del script, prueba del mecanismo nuevo y comprobación de
  que el historial no contiene términos de la denylist.

## Governance

- Esta constitución prevalece sobre otras prácticas del proyecto. Un plan que la incumpla MUST
  justificarlo en su sección de complejidad o cambiarse.
- Enmiendas: se editan aquí con versión semántica (MAJOR: se elimina o redefine un principio;
  MINOR: principio o sección nuevos; PATCH: redacción).
- El contexto operativo con datos del cliente vive en `CLAUDE.local.md` (no versionado).

**Version**: 1.0.0 | **Ratified**: 2026-10-21 | **Last Amended**: 2026-10-21
