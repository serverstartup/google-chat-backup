# Research: exportación en paralelo y Dropbox "solo en línea"

## 1. Unidad de paralelismo: el chat

- **Decision**: un hilo exporta un chat entero (miembros, mensajes, adjuntos); N hilos a la vez.
- **Rationale**: la cuota por espacio (15 lecturas/s, compartida entre apps) se respeta sola
  porque dentro de un chat las peticiones siguen siendo secuenciales; la que se reparte entre
  hilos es la del proyecto (3000/min por tipo = 50/s), lejos de lo que alcanzan unos pocos
  hilos secuenciales. Además cada chat sigue escribiendo solo en su carpeta.
- **Alternatives considered**: paralelizar adjuntos dentro de un chat (aceleraría los chats
  grandes, pero concentra peticiones en un espacio y choca con las 15/s); procesos en vez de
  hilos (el trabajo es de red, no de CPU; los procesos complican compartir el estado).

## 2. Cliente de la API por hilo

- **Decision**: cada hilo construye su propio `build("chat", "v1", credentials=creds)`;
  las credenciales se comparten.
- **Rationale**: `httplib2`, el transporte de `googleapiclient`, no es seguro entre hilos; un
  cliente por hilo es lo que recomienda la propia librería. `google_auth_httplib2` refresca el
  token por petición cuando caduca; un refresco simultáneo en dos hilos es inocuo.
- **Alternatives considered**: un cliente compartido con candado (serializaría las peticiones y
  anularía el paralelismo).

## 3. Reintentos ante 429 y 5xx

- **Decision**: seguir usando `execute(num_retries=RETRIES)` y `next_chunk(num_retries=...)`,
  con `RETRIES = 6`.
- **Rationale**: verificado en el código instalado (`googleapiclient/http.py`,
  `_should_retry_response` y `_retry_request`): reintenta 5xx, 429 y 403 de tipo
  `rateLimitExceeded`, esperando `rand() * 2**n`. Con 6 reintentos la espera máxima llega a 64 s,
  el techo que recomienda Google en su página de límites.
- **Alternatives considered**: un limitador de peticiones propio (más código para un límite que
  no se alcanza con N ≤ 16).

## 4. Valor de `GCHAT_WORKERS`

- **Decision**: entero, por defecto 1, rango 1–16; recomendado 4 en la documentación.
- **Rationale**: 1 conserva el comportamiento actual (constitución V). El techo de 16 evita que
  un error tipográfico (`40`) dispare cientos de peticiones por segundo.
- **Alternatives considered**: sin techo (riesgo de bloqueo de la cuenta); detectar el número de
  CPUs (irrelevante: el cuello de botella es la red y la cuota).

## 5. Parada común: freno de disco y Ctrl-C

- **Decision**: un `threading.Event` de parada. `check_free_space()` lo activa al saltar el
  freno; Ctrl-C en el hilo principal también. Cada hilo lo consulta antes de empezar un chat y
  antes de cada adjunto, y sale con una excepción propia. El ejecutor se cierra con
  `cancel_futures=True` (Python 3.9+) para no empezar chats pendientes.
- **Rationale**: en Python solo el hilo principal recibe `KeyboardInterrupt`; sin una señal
  común los hilos seguirían descargando tras Ctrl-C o tras el freno.
- **Alternatives considered**: hilos demonio que se matan al salir (dejaría `.part` a medias,
  aceptable, pero también JSON sin escribir y sin índice).

## 6. Carpetas con el mismo nombre en paralelo

- **Decision**: la resolución del nombre de carpeta y su creación (`mkdir`) ocurren dentro de un
  candado; el mapa id → carpeta compartido se actualiza ahí.
- **Rationale**: la comprobación "ya existe esta carpeta" y su creación tienen que ser atómicas,
  o dos hilos con chats homónimos elegirían la misma.

## 7. Dropbox "solo en línea"

- **Decision**: no automatizar el paso a "solo en línea"; documentar el gesto del Finder.
  Mantener la comprobación de existencia de adjuntos en `exists()` + `stat().st_size`.
- **Rationale**: en macOS 15.6, `fileproviderctl help` no ofrece `evict` (medido 2026-10-21),
  y Dropbox no tiene orden de terminal para ello (sus foros y su ayuda solo describen el menú del
  Finder). Consultar metadatos de un fichero sin contenido local no lo descarga; leerlo sí. El
  script nunca lee un adjunto existente.
- **Pendiente de verificar**: hoy no hay ningún fichero "solo en línea" en el Dropbox de Julio
  (0 de 59.893 con la marca `dataless`, medido 2026-10-21), así que la comprobación con un fichero
  real queda en el quickstart.
- **Trade-off aceptado**: al relanzar, el script lee `space.json` de cada carpeta para reconocer
  chats ya exportados y reescribe `messages.json`; esos JSON pequeños vuelven a tener contenido
  local. Los adjuntos, que son el 98 % del tamaño, no.

## 8. Medición (2026-10-21)

- 20 espacios sin adjuntos: 59 s con 1 hilo, 19 s con 4 (×3,1), 0 reintentos.
- 4 espacios con adjuntos, uno dominante (18 adjuntos): 44 s con 1 hilo, 85 s con 4. El tiempo
  lo fija el chat más lento y su latencia de descarga varía entre pasadas; no hubo reintentos.
  El paralelismo no acelera un chat grande por dentro; paralelizar adjuntos dentro de un chat
  queda fuera de esta funcionalidad (choca con las 15 lecturas/s por espacio si se abusa).

## 9. Progreso legible con varios hilos

- **Decision**: `log()` bajo candado; cada línea lleva el contador global `[n/total]` y el
  nombre del chat al empezar y al terminar.
