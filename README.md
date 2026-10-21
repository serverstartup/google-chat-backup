# google-chat-backup

Copia de seguridad casera de los chats de **Google Chat** en los que participas (espacios,
grupos y conversaciones 1 a 1, con sus adjuntos), usando tu propia cuenta. No necesita
permisos de administrador de Google Workspace: cada persona exporta lo que vería en la web.

Pensado para un escenario concreto: una organización que apaga Google Workspace y quieres
conservar, antes del apagón, los chats en los que has trabajado.

**¿Vas a hacer tu copia?** Sigue [CONTRIBUTING.md](CONTRIBUTING.md): desde un equipo vacío hasta
la copia entregada, paso a paso. No necesitas nada de lo que hay más abajo.

**¿Mantienes el proyecto?** El resto de esta página es para ti: preparar Google Cloud una vez,
dar acceso a un compañero, revertir todo al final y no filtrar datos del cliente al repositorio.

| Sección | Estás… |
|:--|:--|
| [Qué hay aquí](#qué-hay-aquí) | buscando dónde está cada cosa |
| [Preparar Google Cloud](#preparar-google-cloud-una-vez) | montando el proyecto por primera vez |
| [Dar acceso a un compañero](#dar-acceso-a-un-compañero) | a punto de pasarle la guía a alguien |
| [Revertir todo](#revertir-todo) | con todas las copias hechas |
| [Quality gate](#quality-gate-no-filtrar-términos-prohibidos) | a punto de hacer commit |
| [Desarrollo](#desarrollo) | cambiando el script |

---

## Qué hay aquí

```
google-chat-backup/
├── CONTRIBUTING.md       Guía para hacer tu copia, paso a paso
├── scripts/
│   ├── gchat_backup.py   El exportador: cada persona lo ejecuta con su cuenta
│   ├── requirements.txt  Sus dos dependencias de Google
│   └── .env.example      Plantilla de configuración (la real, .env, no se sube)
├── terraform/            Habilita las APIs en el proyecto GCP (lo único con API)
├── docs/
│   ├── MANUAL_STEPS.md   Lo que no tiene API y se hace a mano, una vez
│   └── REVERTIR.md       Cómo dejarlo todo como estaba
├── specs/                Especificaciones de Spec Kit (una por funcionalidad)
└── .specify/             Constitución y plantillas de Spec Kit
```

El resultado de una copia es una carpeta por chat con el JSON original de la API y sus
adjuntos; el formato está en [CONTRIBUTING.md](CONTRIBUTING.md#lanza-la-copia).

## Preparar Google Cloud (una vez)

Necesitas Terraform ≥ 1.5, `gcloud auth login` y rol de editor u owner en el proyecto GCP.
Google solo expone API para una parte de la configuración:

| Paso | ¿Automatizable? | Dónde |
|------|-----------------|-------|
| Habilitar Google Chat API (y People API, que el script ya no usa) | Sí | `terraform/` |
| Crear el proyecto GCP | Sí (opcional) | `terraform/` |
| Pantalla de consentimiento OAuth (scopes, usuarios de prueba) | No tiene API | `docs/MANUAL_STEPS.md` |
| Cliente OAuth de **escritorio** | No tiene API ni `gcloud` | `docs/MANUAL_STEPS.md` |
| Pestaña "Configuración" de la Chat app | No tiene API | `docs/MANUAL_STEPS.md` |

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
   Descarga el `client_secret_*.json` a `scripts/` (no se sube al repo).

## Dar acceso a un compañero

El cliente OAuth de escritorio es uno para todo el equipo; quién es cada uno lo decide su
inicio de sesión en el navegador. Para que un compañero pueda seguir
[CONTRIBUTING.md](CONTRIBUTING.md) por su cuenta:

1. **Repositorio:** invítalo con permiso de lectura.
   ```bash
   gh api -X PUT repos/serverstartup/google-chat-backup/collaborators/<su-usuario-github> -f permission=pull
   ```
2. **Usuario de prueba:** añade su email del trabajo en la consola de Google Cloud →
   *Google Auth Platform* → *Público* → *Usuarios de prueba*. Si la aplicación es de tipo
   *Interno*, no hace falta. Sin este paso, su inicio de sesión acaba en "Acceso bloqueado".
3. **`client_secret`:** pásale el fichero `client_secret_….json` por un canal privado. Nunca por
   el repositorio ni por un chat que se vaya a exportar.
4. **Entrega:** acordad dónde te deja su carpeta `gchat-backup/<su-usuario>/` al terminar.

## Revertir todo

Toda la activación es reversible. Cuando las copias estén hechas, sigue
[`docs/REVERTIR.md`](docs/REVERTIR.md): `terraform destroy` deshabilita las APIs
(`disable_on_destroy = true`) y la parte manual (cliente OAuth, consentimiento) se borra
a mano, porque no tiene API.

## 0 credenciales en el repo

El `.gitignore` bloquea `client_secret*.json`, `token.json`, `.env`, los `*.tfvars` (salvo el
`.example`), el estado de Terraform y las carpetas de salida del backup. El secreto de
cliente y el token de sesión viven **solo** en la máquina de cada uno.

## Quality gate (no filtrar términos prohibidos)

El repo trae un hook de `pre-commit` en `.githooks/` que **aborta el commit** si detecta
en el stage credenciales, estado de Terraform o cualquier término de una **denylist local**.

Esa denylist (`denylist.txt`) **no se versiona** (está en `.gitignore`): vive solo en tu
máquina, así el término prohibido —por ejemplo el nombre de un cliente— nunca llega al
repositorio, ni siquiera dentro del propio hook. El hook tampoco imprime el término que
coincide, solo el fichero.

Puesta en marcha en cada clon (el hook no se activa solo):

```bash
git config core.hooksPath .githooks        # activa el hook
cp denylist.example.txt denylist.txt        # y edítalo con tus términos (1 regex por línea)
```

Para un caso legítimo puntual puedes saltarlo con `git commit --no-verify`.

## Desarrollo

Los cambios del script pasan por [Spec Kit](https://github.com/github/spec-kit): la constitución
del proyecto está en `.specify/memory/constitution.md` y cada funcionalidad tiene su carpeta en
`specs/` (especificación, plan, tareas y cómo validarla). Las funcionalidades van en una rama y
llegan a `main` por pull request.

**Rendimiento.** `GCHAT_WORKERS` exporta varios chats a la vez. Medido el 2026-10-21 con 20
espacios y sin adjuntos: 59 s con 1 hilo, 19 s con 4, sin ningún reintento por cuota. Dentro de
un chat los adjuntos se bajan de uno en uno, así que un chat con miles de adjuntos tarda lo mismo
con 1 hilo que con 4. Detalle en `specs/001-parallel-chat-export/research.md`.

**Dropbox "solo en línea".** El script decide si un adjunto ya existe mirando solo su tamaño,
nunca su contenido, así que no obliga a Dropbox a bajar lo que esté "solo en línea". En macOS 15
no hay orden de terminal para marcarlo; se hace desde el Finder.

## Prior art (por qué este script y no un fork)

Antes de escribir esto se evaluaron los repos existentes. El más cercano es
[`pokhiii/gchat-export`](https://github.com/pokhiii/gchat-export) (Apache-2.0, misma auth de
usuario), pero está en Go, exporta **un espacio por ejecución** y su binario de macOS va sin
firmar. Para nuestro caso (todos los espacios de una pasada, Python, que lo ejecuten varios
compañeros) sale mejor este script. De gchat-export tomamos ideas a futuro: token en el
keychain del SO, `--resume` y hashes SHA-256 de adjuntos. Las herramientas comerciales
(SysCloud, Spin, CloudFuze…) y los visores de Takeout no encajan: admin-only o esperan el
formato de Takeout, que no es el que devuelve la API.
