# Data Model

No changes to the output format. This documents the state that parallelism shares.

## Chat (being exported)

| Field | Source | Notes |
| :--- | :--- | :--- |
| `name` (`spaces/<id>`) | API | stable identity |
| folder | `folder_name()` | `<YYYY-MM-DD>_<chat>`, suffix `_<id>` on a clash |
| state | — | pending → in progress → done \| failed (HTTP) \| stopped |

Transitions: a pending chat does not start if the stop is active; one in progress becomes
stopped at the next attachment after the stop is set; failed ones are recorded in
`manifest.json` → `failed`.

## Attachment

| State on disk | How it is recognised (metadata only) | Action on relaunch |
| :--- | :--- | :--- |
| complete | exists and size > 0 | skipped |
| "online-only" | exists and logical size > 0, no local content | skipped, not read |
| half-written | only `<name>.part` exists | downloaded in full |
| absent | does not exist | downloaded |

## State shared between threads

| State | Protection |
| :--- | :--- |
| id → folder map (`known`) | folders lock |
| creation of a new folder | same lock (check and create together) |
| stop signal | `threading.Event` |
| on-screen output | log lock |
| index and failures | each thread returns them; the main thread collects them in order |

## Manifest (added)

`params.workers`: parallelism used.
