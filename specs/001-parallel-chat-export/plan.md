# Implementation Plan: Exportación de chats en paralelo compatible con Dropbox "solo en línea"

**Branch**: `001-parallel-chat-export` | **Date**: 2026-10-21 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/001-parallel-chat-export/spec.md`

## Summary

Añadir a `scripts/gchat_backup.py` un parámetro `GCHAT_WORKERS` (por defecto 1) que exporta
hasta N chats a la vez con un `ThreadPoolExecutor` de la biblioteca estándar, un cliente de la
API por hilo y un candado para lo compartido (nombres de carpeta, log). El freno de disco y
Ctrl-C pasan a ser una señal de parada común que todos los hilos consultan antes de cada chat y
de cada adjunto. La comprobación de "adjunto ya existe" se queda en metadatos (`stat`), que es
lo que hace falta para no despertar ficheros "solo en línea" de Dropbox.

## Technical Context

**Language/Version**: Python 3.9+ (venv del proyecto en 3.12)

**Primary Dependencies**: `google-api-python-client`, `google-auth-oauthlib` (ya en uso);
`concurrent.futures` y `threading` de la biblioteca estándar

**Storage**: ficheros en disco: carpeta de Dropbox (`GCHAT_OUT_DIR`), un directorio por chat

**Testing**: pruebas de mecanismo con la API real sobre un subconjunto (`GCHAT_SPACE_FILTER`) y
una carpeta de salida temporal; prueba negativa del freno de disco; sin suite de tests (el
proyecto es un script de un solo uso)

**Target Platform**: macOS 15 (portátil de quien exporta), Dropbox sobre File Provider

**Project Type**: CLI de un solo fichero

**Performance Goals**: con 4 hilos, al menos 2× más rápido que con 1 sobre el mismo conjunto
(SC-001)

**Constraints**: cuotas de Google Chat (3000 lecturas/min por proyecto y tipo; 15 lecturas/s
por espacio); 0 chats fallidos por 429; freno de disco intacto

**Scale/Scope**: 433 chats de Julio, del orden de decenas de GB; después Nacho y Dani

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principio | Cumple | Cómo |
| :--- | :--- | :--- |
| I Simplicidad | Sí | Biblioteca estándar, una variable nueva con defecto 1 que reproduce el comportamiento actual |
| II Reanudable | Sí | La escritura atómica no cambia; carpeta reservada bajo candado para no duplicar |
| III Datos fuera del repo | Sí | La salida sigue en Dropbox; nada nuevo se versiona salvo código y specs |
| IV Reversibilidad | Sí | No toca GCP ni Terraform |
| V Cuotas y recursos | Sí | Defecto 1, máximo 16, backoff de la librería hasta 64 s, freno de disco común |
| VI Evidencia | Sí | Quickstart con prueba positiva (tiempos) y negativa (freno, valor inválido) |

Re-check tras el diseño: sin cambios, ninguna desviación que justificar.

## Project Structure

### Documentation (this feature)

```text
specs/001-parallel-chat-export/
├── plan.md              # este fichero
├── research.md          # decisiones de la fase 0
├── data-model.md        # entidades y estados
├── quickstart.md        # cómo validar de punta a punta
├── contracts/
│   └── env-config.md    # contrato de variables GCHAT_*
└── tasks.md             # lo genera /speckit-tasks
```

### Source Code (repository root)

```text
scripts/
├── gchat_backup.py      # único fichero que cambia
└── .env.example         # documenta GCHAT_WORKERS
README.md                # cómo elegir hilos y cómo marcar "solo en línea"
```

**Structure Decision**: proyecto de un solo script; no se añaden módulos ni ficheros de código.

## Complexity Tracking

Sin desviaciones de la constitución.
