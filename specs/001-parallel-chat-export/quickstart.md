# Quickstart: validar la exportación en paralelo

Todas las pruebas usan una carpeta de salida temporal y un filtro de chats, así no tocan el
backup real. Desde `scripts/`, con el venv y `scripts/.env` ya preparados (ver README).

```bash
cd scripts
OUT=$(mktemp -d)
FILTER='<regex que case con 6-10 espacios pequeños>'
```

## 1. Valor no válido (FR-002)

```bash
GCHAT_WORKERS=0  .venv/bin/python gchat_backup.py   # sale con el mensaje del contrato
GCHAT_WORKERS=abc .venv/bin/python gchat_backup.py  # ídem
```

Esperado: código distinto de 0, sin abrir el navegador ni crear carpetas.

## 2. Mismo resultado y menos tiempo (FR-005, SC-001)

```bash
time GCHAT_DRY_RUN=false GCHAT_WORKERS=1 GCHAT_SPACE_FILTER="$FILTER" GCHAT_OUT_DIR=$OUT/w1 .venv/bin/python gchat_backup.py
time GCHAT_DRY_RUN=false GCHAT_WORKERS=4 GCHAT_SPACE_FILTER="$FILTER" GCHAT_OUT_DIR=$OUT/w4 .venv/bin/python gchat_backup.py
```

Esperado: mismas carpetas, mismo número de mensajes y adjuntos por chat (comparar `index.json`
sin el orden de líneas); el segundo tarda como mucho la mitad.

## 3. Freno de disco con hilos (FR-008, SC-004)

```bash
GCHAT_DRY_RUN=false GCHAT_WORKERS=4 GCHAT_MIN_FREE_GB=100000 GCHAT_OUT_DIR=$OUT/brake .venv/bin/python gchat_backup.py
```

Esperado: `DETENIDO`, `manifest.json` con `stoppedEarly`, 0 adjuntos escritos.

## 4. Reanudación sin duplicados (FR-007, SC-005)

Lanzar la prueba 2 con `GCHAT_WORKERS=4` sobre una carpeta nueva, Ctrl-C a mitad, relanzar.
Esperado: nº de carpetas de chat = nº de chats; ningún `.part` tras terminar.

## 5. Dropbox "solo en línea" (FR-006, SC-003) — manual

1. En el Finder, sobre la carpeta `attachments/` de un chat ya exportado en Dropbox:
   clic derecho → **Hacer disponible solo en línea**. Esperar a que el icono cambie.
2. Comprobar que no tiene contenido local: `ls -lO <carpeta>/attachments | grep -c dataless`.
3. Relanzar el backup (con `GCHAT_SPACE_FILTER` que incluya ese chat).
4. Esperado: el log dice `adjuntos N ok` sin descargas nuevas y el paso 2 da el mismo número.
