# google-chat-backup

Copia de seguridad casera de los espacios de **Google Chat** en los que participas,
usando tu propia cuenta (autenticación de usuario, OAuth). No necesita permisos de
administrador de Google Workspace: solo ves y exportas lo que verías tú en la web.

Pensado para un escenario concreto: una organización que apaga Google Workspace y
quieres conservar, antes del apagón, los espacios en los que has trabajado.

## Qué hay aquí

```
google-chat-backup/
├── terraform/            Habilita en un proyecto GCP las APIs necesarias (lo único automatizable)
├── scripts/
│   └── gchat_backup.py   El exportador: cada persona lo ejecuta con su cuenta
├── docs/
│   └── MANUAL_STEPS.md    Los pasos que NO tienen API y hay que hacer a mano, una vez
└── README.md
```

## Qué se automatiza y qué no

Google solo expone API para una parte de la configuración:

| Paso | ¿Automatizable? | Dónde |
|------|-----------------|-------|
| Habilitar Google Chat API y People API | Sí | `terraform/` |
| Crear el proyecto GCP | Sí (opcional) | `terraform/` |
| Pantalla de consentimiento OAuth (scopes, usuarios de prueba) | No tiene API | `docs/MANUAL_STEPS.md` |
| Cliente OAuth de **escritorio** | No tiene API ni `gcloud` | `docs/MANUAL_STEPS.md` |
| Pestaña "Configuración" de la Chat app | No tiene API | `docs/MANUAL_STEPS.md` |

## 0 credenciales en el repo

El `.gitignore` bloquea `client_secret*.json`, `token.json`, los `*.tfvars` (salvo el
`.example`), el estado de Terraform y las carpetas de salida del backup. El secreto de
cliente y el token de sesión viven **solo** en la máquina de cada uno. Revisa con
`git status` antes del primer commit que no se cuela nada.

## Requisitos

- Terraform >= 1.5 y `gcloud` autenticado (`gcloud auth login`)
- Rol de editor u owner en el proyecto GCP (para habilitar APIs)
- Python 3.9+

## Puesta en marcha (una vez por proyecto)

1. **APIs, con Terraform:**
   ```bash
   cd terraform
   cp terraform.tfvars.example terraform.tfvars   # edita project_id
   terraform init
   terraform apply
   ```

   Si las APIs **ya estaban habilitadas** (a mano o con `gcloud`), no hace falta
   deshabilitarlas: impórtalas al state y el plan sale limpio.
   ```bash
   terraform import 'google_project_service.apis["chat.googleapis.com"]'   "<project_id>/chat.googleapis.com"
   terraform import 'google_project_service.apis["people.googleapis.com"]' "<project_id>/people.googleapis.com"
   terraform apply    # solo fija disable_on_destroy en el state; no llama a GCP
   ```
   Antes de dejar `disable_on_destroy = true`, comprueba en el audit log (Service Usage)
   que fuiste tú quien las habilitó: si ya estaban en uso, pon `false`.

2. **Pasos manuales:** sigue [`docs/MANUAL_STEPS.md`](docs/MANUAL_STEPS.md) para la pantalla
   de consentimiento, el cliente OAuth de escritorio y la config de la Chat app.
   Descarga el `client_secret_*.json` a la carpeta `scripts/` (no se subirá al repo).

## Ejecutar el backup (cada persona, con su cuenta)

```bash
cd scripts
uv venv .venv && uv pip install --python .venv/bin/python google-api-python-client google-auth-oauthlib

cp .env.example .env           # rellena la ruta del client_secret y tu carpeta de salida
.venv/bin/python gchat_backup.py                       # con GCHAT_DRY_RUN=true: solo lista
GCHAT_DRY_RUN=false .venv/bin/python gchat_backup.py   # exportación real
```

Queda así en disco, una carpeta por chat (los hilos van dentro de `messages.json`):

```
scripts/gchat-backup/<usuario>/
  index.json  manifest.json
  2021-03-04_nombre-del-espacio/       fecha del primer mensaje + nombre del chat
    space.json  members.json  messages.json
    attachments/
  2023-06-12_nombre-de-la-persona/     chat 1 a 1
```

### Más rápido: varios chats a la vez

`GCHAT_WORKERS=4` en `scripts/.env` exporta 4 chats a la vez (por defecto, 1). Medido el
2026-10-21 con 20 espacios: 59 s con 1 hilo, 19 s con 4, sin ningún reintento por cuota. Las
cuotas de Google (3000 lecturas por minuto y proyecto) quedan muy lejos; si aun así Google
responde "demasiadas peticiones", el script espera y reintenta solo. Máximo 16.

### Guardarlo en Dropbox sin llenar el disco

Apunta `GCHAT_OUT_DIR` a una carpeta de Dropbox y el backup se sube según se descarga. Para
liberar espacio, en el Finder: clic derecho sobre la carpeta (o sobre un chat ya subido) →
**Hacer disponible solo en línea**. El script sigue funcionando sobre esas carpetas: para saber
si un adjunto ya está solo mira su tamaño, nunca lo abre, así que no obliga a Dropbox a bajarlo.
No hay forma de hacerlo desde la terminal en macOS 15; también lo hace macOS solo cuando falta
disco, con lo que no esté marcado como "disponible sin conexión".

`scripts/.env` está en `.gitignore`: ahí van las rutas y los filtros (que pueden llevar
nombres de espacios). Las variables del entorno real mandan sobre las del fichero.

Todas las variables (filtrar por nombre de espacio, fecha desde, resolver nombres,
descargar adjuntos…) están documentadas en la cabecera de `scripts/gchat_backup.py`.

## Que lo ejecuten tus compañeros

El cliente OAuth de escritorio se puede compartir entre el equipo. Para que tus compañeros
hagan su propio backup:

1. Añádelos como **usuarios de prueba** en la pantalla de consentimiento (paso 2 de
   `docs/MANUAL_STEPS.md`). Si la app está en modo Internal no hace falta.
2. Pásales el `client_secret_*.json` **fuera del repo** (por un canal seguro, no por el
   git). Cada uno lo deja en su `scripts/`.
3. Cada uno ejecuta el script con su cuenta. Genera su propio `token.json` y su carpeta
   `gchat-backup/<usuario>/`. Luego se juntan las tres.

## Revertir todo

Toda la activación es reversible. Cuando los backups estén hechos, sigue
[`docs/REVERTIR.md`](docs/REVERTIR.md): `terraform destroy` deshabilita las APIs
(`disable_on_destroy = true`) y la parte manual (cliente OAuth, consentimiento) se borra
a mano, porque no tiene API.

## Quality gate (no filtrar términos prohibidos)

El repo trae un hook de `pre-commit` en `.githooks/` que **aborta el commit** si detecta
en el stage credenciales, estado de Terraform o cualquier término de una **denylist local**.

Esa denylist (`denylist.txt`) **no se versiona** (está en `.gitignore`): vive solo en tu
máquina, así el término prohibido —por ejemplo el nombre de un cliente— nunca llega al
repositorio, ni siquiera dentro del propio hook. El hook tampoco imprime el término que
coincide, solo el fichero.

Puesta en marcha (el `bootstrap-git.sh` ya lo hace):

```bash
git config core.hooksPath .githooks        # activa el hook
cp denylist.example.txt denylist.txt        # y edítalo con tus términos (1 regex por línea)
```

Para un caso legítimo puntual puedes saltarlo con `git commit --no-verify`.

## Prior art (por qué este script y no un fork)

Antes de escribir esto se evaluaron los repos existentes. El más cercano es
[`pokhiii/gchat-export`](https://github.com/pokhiii/gchat-export) (Apache-2.0, misma auth de
usuario), pero está en Go, exporta **un espacio por ejecución** y su binario de macOS va sin
firmar. Para nuestro caso (todos los espacios de una pasada, Python, que lo ejecuten varios
compañeros) sale mejor este script. De gchat-export tomamos ideas a futuro: token en el
keychain del SO, `--resume` y hashes SHA-256 de adjuntos. Las herramientas comerciales
(SysCloud, Spin, CloudFuze…) y los visores de Takeout no encajan: admin-only o esperan el
formato de Takeout, que no es el que devuelve la API.
