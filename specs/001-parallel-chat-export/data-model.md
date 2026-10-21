# Data Model

Sin cambios en el formato de salida. Se documenta el estado que el paralelismo comparte.

## Chat (en exportación)

| Campo | Origen | Notas |
| :--- | :--- | :--- |
| `name` (`spaces/<id>`) | API | identidad estable |
| carpeta | `folder_name()` | `<AAAA-MM-DD>_<chat>`, sufijo `_<id>` si choca |
| estado | — | pendiente → en curso → hecho \| fallido (HTTP) \| detenido |

Transiciones: un chat pendiente no empieza si la parada está activa; uno en curso pasa a
detenido en el siguiente adjunto tras activarse la parada; los fallidos se registran en
`manifest.json` → `failed`.

## Adjunto

| Estado en disco | Cómo se reconoce (solo metadatos) | Acción al relanzar |
| :--- | :--- | :--- |
| completo | existe y tamaño > 0 | se salta |
| "solo en línea" | existe y tamaño lógico > 0, sin contenido local | se salta, no se lee |
| a medias | solo existe `<nombre>.part` | se descarga entero |
| ausente | no existe | se descarga |

## Estado compartido entre hilos

| Estado | Protección |
| :--- | :--- |
| mapa id → carpeta (`known`) | candado de carpetas |
| creación de carpeta nueva | mismo candado (comprobar y crear juntos) |
| señal de parada | `threading.Event` |
| salida por pantalla | candado de log |
| índice y fallos | los devuelve cada hilo; el principal los junta en orden |

## Manifest (añadido)

`params.workers`: paralelismo usado.
