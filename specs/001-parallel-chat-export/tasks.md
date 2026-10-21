# Tasks: Exportación de chats en paralelo compatible con Dropbox "solo en línea"

**Input**: Design documents from `specs/001-parallel-chat-export/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/env-config.md, quickstart.md

**Tests**: la especificación no pide una suite; la validación son los escenarios de
`quickstart.md`, que aparecen como tareas de verificación al final de cada historia.

Todas las tareas de código tocan el mismo fichero (`scripts/gchat_backup.py`), así que ninguna
es paralelizable entre sí; solo la documentación lo es.

## Phase 1: Setup

- [X] T001 Añadir `import threading` y `from concurrent.futures import ThreadPoolExecutor` en `scripts/gchat_backup.py`
- [X] T002 Subir `RETRIES` de 5 a 6 en `scripts/gchat_backup.py` (espera máxima 64 s, research §3)

---

## Phase 2: Foundational (bloquea todas las historias)

- [X] T003 Leer `GCHAT_WORKERS` en `scripts/gchat_backup.py`: entero, defecto `1`, rango 1–16; si no es válido, salir antes de autenticar con `GCHAT_WORKERS debe ser un entero entre 1 y 16: '<valor>'` (contrato env-config)
- [X] T004 Crear en `scripts/gchat_backup.py` el estado compartido: `STOP = threading.Event()`, `_folders_lock`, `_log_lock`; `log()` escribe bajo `_log_lock`
- [X] T005 Definir en `scripts/gchat_backup.py` la excepción `Stopped` y hacer que `check_free_space()` active `STOP` antes de lanzar `DiskFull`, y que lance `Stopped` si `STOP` ya está activa

---

## Phase 3: User Story 1 — Backup más rápido con paralelismo configurable (P1) MVP

**Goal**: exportar hasta `GCHAT_WORKERS` chats a la vez con el mismo resultado que en serie.

**Independent Test**: quickstart §1 y §2.

- [X] T006 [US1] En `scripts/gchat_backup.py`, hacer que `export_space()` reciba su propio cliente `chat` y lo construya cada hilo con `build("chat", "v1", credentials=creds, cache_discovery=False)` guardado en un `threading.local()` (research §2)
- [X] T007 [US1] En `scripts/gchat_backup.py`, mover la resolución y creación de carpeta (`resolve_space_dir`) bajo `_folders_lock`, creando la carpeta (`mkdir`) dentro del candado para que dos chats homónimos no elijan la misma (FR-009, research §6)
- [X] T008 [US1] En `scripts/gchat_backup.py`, sustituir el bucle de `main()` por un `ThreadPoolExecutor(max_workers=WORKERS)`; cada tarea registra `[n/total] <chat>` al empezar, devuelve su entrada de índice o su fallo HTTP, y el principal junta resultados en el orden original de la API (FR-003, FR-005)
- [X] T009 [US1] En `scripts/gchat_backup.py`, distinguir en el log de cada chat los adjuntos descargados de los que ya existían (`adjuntos D nuevos / E ya estaban / X error / Y en Drive`) y añadir `attachmentsDownloaded` al índice, para poder verificar reanudación y "solo en línea"
- [X] T010 [US1] Añadir `workers` a `manifest.json` → `params` en `scripts/gchat_backup.py` (FR-010)
- [X] T011 [US1] Verificar quickstart §1 (valores `0` y `abc` rechazados sin abrir navegador) y §2 (mismo `index.json` salvo orden, tiempo con 4 hilos ≤ mitad del de 1) contra la API real con carpeta temporal

---

## Phase 4: User Story 2 — Relanzar sobre Dropbox "solo en línea" sin volver a descargar (P1)

**Goal**: un adjunto existente nunca se lee ni se vuelve a descargar.

**Independent Test**: quickstart §5 (manual, requiere marcar una carpeta desde el Finder).

- [X] T012 [US2] Revisar en `scripts/gchat_backup.py` que `download_attachment()` decide solo con `exists()` y `stat().st_size` (sin abrir el fichero) y que un `.part` sobrante no cuenta como existente (FR-006, FR-007); dejar un comentario de una línea con el porqué
- [X] T013 [US2] Verificar quickstart §4 en la carpeta temporal: Ctrl-C a mitad con 4 hilos, relanzar, 0 carpetas duplicadas, 0 `.part`, adjuntos del segundo pase contados como "ya estaban"

---

## Phase 5: User Story 3 — Freno de disco y reanudación con varios chats a la vez (P2)

**Goal**: freno y Ctrl-C paran todos los hilos y dejan índice y resumen coherentes.

**Independent Test**: quickstart §3 y §4.

- [X] T014 [US3] En `scripts/gchat_backup.py`, consultar `STOP` antes de empezar cada chat y antes de cada adjunto (vía `check_free_space()`); al capturar `DiskFull` o `Stopped`, cerrar el ejecutor con `shutdown(wait=True, cancel_futures=True)`, escribir `index.json` y `manifest.json` con `stoppedEarly` (FR-008, research §5)
- [X] T015 [US3] En `scripts/gchat_backup.py`, en `KeyboardInterrupt` del hilo principal activar `STOP`, esperar a los hilos y salir con el mensaje actual (sin dejar hilos descargando)
- [X] T016 [US3] Verificar quickstart §3 con `GCHAT_WORKERS=4 GCHAT_MIN_FREE_GB=100000`: `DETENIDO`, `stoppedEarly`, 0 adjuntos escritos

---

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T017 [P] Documentar `GCHAT_WORKERS` en la cabecera de `scripts/gchat_backup.py` y en `scripts/.env.example` (recomendado 4)
- [X] T018 [P] Añadir al `README.md` una sección corta: cómo elegir hilos y cómo marcar "solo en línea" en Dropbox desde el Finder, indicando que no hay orden de terminal en macOS 15
- [ ] T019 `py_compile`, comprobación de la denylist sobre el historial, commit en la rama `001-parallel-chat-export` y merge a `main` — commit hecho en la rama (`e0feb32`); merge a `main` y push pendientes de que Julio lo pida (regla git.md)
- [X] T020 Relanzar la sincronización real con `GCHAT_WORKERS=4` y re-armar la vigilancia de consumo

---

## Dependencies & Execution Order

- Setup (T001–T002) → Foundational (T003–T005) → US1 (T006–T011) → US2 y US3 → Polish.
- US2 solo depende de T009 (contadores) para su verificación; US3 depende de T004–T005 y T008.
- Todas las tareas de código son secuenciales (mismo fichero). T017 y T018 pueden hacerse en
  paralelo entre sí.

## Parallel Example

```text
T017 (cabecera + .env.example)  ||  T018 (README)
```

## Implementation Strategy

MVP = US1 (paralelismo con resultado idéntico). US2 y US3 son garantías sobre lo que ya existe y
se cierran en la misma rama antes de usar `GCHAT_WORKERS=4` en la sincronización real (T020).
