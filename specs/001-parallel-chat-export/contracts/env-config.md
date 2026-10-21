# Contrato: configuración por variables `GCHAT_*`

El script se configura solo por variables de entorno (o `scripts/.env`). Esta funcionalidad
añade una y no cambia el significado de las demás.

| Variable | Tipo | Defecto | Rango | Error si no es válida |
| :--- | :--- | :--- | :--- | :--- |
| `GCHAT_WORKERS` | entero | `1` | 1–16 | `GCHAT_WORKERS debe ser un entero entre 1 y 16: '<valor>'`, sale antes de autenticar |

Sin cambios: `GCHAT_CLIENT_SECRET`, `GCHAT_TOKEN_FILE`, `GCHAT_OUT_DIR`, `GCHAT_SPACE_TYPES`,
`GCHAT_SPACE_FILTER`, `GCHAT_SINCE`, `GCHAT_DOWNLOAD_ATTACHMENTS`, `GCHAT_DRY_RUN`,
`GCHAT_MIN_FREE_GB`.

## Salida

- Estructura de carpetas: la misma (`<OUT_DIR>/<usuario>/<AAAA-MM-DD>_<chat>/`).
- `manifest.json` → `params.workers` con el valor usado.
- `index.json`: mismo contenido para cualquier valor de `GCHAT_WORKERS`, en el orden en que la
  API lista los chats.
- Códigos de salida: 0 al terminar o al detenerse por el freno de disco (con `stoppedEarly`);
  distinto de 0 con valor de configuración no válido o Ctrl-C.
