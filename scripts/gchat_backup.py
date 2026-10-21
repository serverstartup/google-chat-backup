#!/usr/bin/env python3
"""
gchat_backup.py — Copia local de Google Chat con la cuenta de quien lo ejecuta.

Usa autenticación de USUARIO (OAuth, "iniciar sesión con Google"): solo ve y
exporta los espacios, grupos y chats privados en los que esa persona es miembro.
No necesita permisos de administrador.

Qué guarda (en GCHAT_OUT_DIR/<usuario>/, donde <usuario> es la parte local del email):
  manifest.json                  quién exportó, cuándo, con qué parámetros y resumen
  index.json                     lista de chats exportados (id, carpeta, nombre, tipo, nº mensajes)
  <AAAA-MM-DD>_<chat>/           una carpeta por chat: fecha del primer mensaje + nombre
    space.json                   datos del chat tal como los da la API
    members.json                 miembros (con nombre y email)
    messages.json                mensajes en orden cronológico, JSON original de la API
                                 (autor con nombre y email; los hilos van en el campo thread)
    attachments/                 adjuntos subidos al chat (los de Drive quedan como enlace)

  <chat> es el nombre del espacio; en un chat 1 a 1, el de la otra persona; en un grupo
  sin nombre, el de sus miembros. Si dos chats dan la misma carpeta, se añade el id.

Se puede ejecutar varias veces: reescribe los mensajes y no vuelve a bajar
adjuntos que ya existen. Cada chat conserva su carpeta aunque luego cambie de nombre
(se reconoce por el id guardado en space.json).

Dependencias:
  pip install google-api-python-client google-auth-oauthlib

Variables de entorno (también se leen de scripts/.env, que está en .gitignore;
plantilla en scripts/.env.example):
  GCHAT_CLIENT_SECRET  (obligatoria) ruta al JSON del cliente OAuth "Aplicación de escritorio"
  GCHAT_TOKEN_FILE      ruta donde guardar el token de sesión       [token.json]
  GCHAT_OUT_DIR         carpeta de salida                            [./gchat-backup]
  GCHAT_SPACE_TYPES     tipos a exportar, separados por comas        [SPACE,GROUP_CHAT,DIRECT_MESSAGE]
                        SPACE = espacio con nombre, GROUP_CHAT = grupo sin nombre,
                        DIRECT_MESSAGE = chat 1 a 1
  GCHAT_SPACE_FILTER    expresión regular sobre el nombre del espacio (sin distinguir
                        mayúsculas). Si se define, solo entran espacios con nombre que
                        coincidan; los grupos y chats 1 a 1 (que no tienen nombre) quedan fuera.
  GCHAT_SINCE           exportar solo mensajes desde esta fecha, p. ej. 2024-01-01   [todo]
  GCHAT_DOWNLOAD_ATTACHMENTS  true/false                             [true]
  GCHAT_DRY_RUN         true/false: solo listar qué se exportaría    [false]
  GCHAT_MIN_FREE_GB     espacio libre mínimo en disco, en GB. Por debajo, el backup
                        se detiene limpio (guarda index y manifest) en vez de
                        llenar el disco. Relanzar continúa donde se quedó.  [20]
"""

import io
import json
import os
import re
import shutil
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload


# ---------------------------------------------------------------- configuración

def load_dotenv(path: Path):
    """Carga KEY=valor de un .env local (gitignored). El entorno real manda sobre el fichero."""
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip().removeprefix("export ").strip()
        os.environ.setdefault(key, value.strip().strip("'\""))


load_dotenv(Path(__file__).resolve().parent / ".env")


def env(name, default=None, required=False):
    value = os.environ.get(name, "").strip()
    if not value:
        if required:
            sys.exit(f"Falta la variable de entorno {name}")
        return default
    return value


def env_bool(name, default):
    value = env(name)
    if value is None:
        return default
    return value.lower() in ("1", "true", "yes", "si", "sí", "on")


CLIENT_SECRET = env("GCHAT_CLIENT_SECRET", required=True)
TOKEN_FILE = Path(env("GCHAT_TOKEN_FILE", "token.json"))
OUT_DIR = Path(env("GCHAT_OUT_DIR", "./gchat-backup"))
SPACE_TYPES = {t.strip().upper() for t in env(
    "GCHAT_SPACE_TYPES", "SPACE,GROUP_CHAT,DIRECT_MESSAGE").split(",") if t.strip()}
SPACE_FILTER = env("GCHAT_SPACE_FILTER")
SPACE_FILTER_RE = re.compile(SPACE_FILTER, re.IGNORECASE) if SPACE_FILTER else None
SINCE = env("GCHAT_SINCE")
DOWNLOAD_ATTACHMENTS = env_bool("GCHAT_DOWNLOAD_ATTACHMENTS", True)
DRY_RUN = env_bool("GCHAT_DRY_RUN", False)
try:
    MIN_FREE_GB = float(env("GCHAT_MIN_FREE_GB", "20"))
except ValueError:
    sys.exit(f"GCHAT_MIN_FREE_GB no es un número: {env('GCHAT_MIN_FREE_GB')!r}")

SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/chat.spaces.readonly",
    "https://www.googleapis.com/auth/chat.memberships.readonly",
    "https://www.googleapis.com/auth/chat.messages.readonly",
]

RETRIES = 5  # reintentos automáticos ante 429 (límite de peticiones) y errores 5xx


# ---------------------------------------------------------------- utilidades

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def write_json(path: Path, data):
    """Escritura atómica: primero a .tmp y luego renombrar."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def read_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def safe_name(text, max_len=120):
    text = re.sub(r"[^\w.\- ]+", "_", text or "", flags=re.UNICODE).strip(" ._")
    return (text or "sin_nombre")[:max_len]


def short_id(resource_name):
    """'spaces/AAAA/messages/BBB.CCC' -> 'BBB.CCC'."""
    return resource_name.rsplit("/", 1)[-1]


def paginate(method, items_key, **kwargs):
    page_token = None
    while True:
        if page_token:
            kwargs["pageToken"] = page_token
        resp = method(**kwargs).execute(num_retries=RETRIES)
        yield from resp.get(items_key, [])
        page_token = resp.get("nextPageToken")
        if not page_token:
            break


def since_rfc3339(value):
    try:
        dt = datetime.fromisoformat(value)
    except ValueError:
        sys.exit(f"GCHAT_SINCE no es una fecha válida: {value!r} (usa AAAA-MM-DD)")
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------- autenticación

def get_credentials():
    creds = None
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
        if not creds.has_scopes(SCOPES):
            creds = None  # cambiaron los permisos pedidos: volver a iniciar sesión
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
        except Exception:
            creds = None
    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET, SCOPES)
        creds = flow.run_local_server(port=0, prompt="consent")
    TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")
    try:
        os.chmod(TOKEN_FILE, 0o600)
    except OSError:
        pass
    return creds


# ---------------------------------------------------------------- exportación

def slug(text, max_len=60):
    """'Server Startup S.L.' -> 'server-startup-s-l' (ASCII, minúsculas, guiones)."""
    text = unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode()
    text = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return text[:max_len].rstrip("-")


def other_members(members, exporter_email):
    """Nombres de los miembros que no son quien exporta, ordenados."""
    names = []
    for m in members:
        u = m.get("member") or {}
        if (u.get("email") or "").lower() == exporter_email.lower():
            continue
        names.append(u.get("displayName") or u.get("email") or "")
    return sorted(n for n in names if n)


def chat_label(space, members, exporter_email):
    """Nombre legible del chat: el del espacio o, si no tiene, el de los otros miembros."""
    return space.get("displayName") or ", ".join(other_members(members, exporter_email)) or "(sin nombre)"


def folder_name(space, members, messages, exporter_email):
    """<AAAA-MM-DD>_<chat>: fecha del primer mensaje y nombre del espacio o de las personas."""
    first = (messages[0].get("createTime") if messages else None) or space.get("createTime") or ""
    date = first[:10] if re.match(r"\d{4}-\d{2}-\d{2}", first) else "undated"
    if space.get("displayName"):
        name = slug(space["displayName"])
    else:
        people = other_members(members, exporter_email)
        name = "_".join(slug(n, 30) for n in people[:4]) + ("_and-more" if len(people) > 4 else "")
    return f"{date}_{name or 'unnamed'}"


def existing_folders(user_dir: Path):
    """space name -> carpeta ya creada en una ejecución anterior (por el id de space.json)."""
    found = {}
    for f in user_dir.glob("*/space.json"):
        name = read_json(f, {}).get("name")
        if name:
            found[name] = f.parent
    return found


def wanted(space):
    if space.get("spaceType") not in SPACE_TYPES:
        return False
    if SPACE_FILTER_RE:
        name = space.get("displayName") or ""
        return bool(name) and bool(SPACE_FILTER_RE.search(name))
    return True


class DiskFull(Exception):
    pass


def check_free_space():
    """Corta antes de llenar el disco: se comprueba antes de cada espacio y cada adjunto."""
    free_gb = shutil.disk_usage(OUT_DIR).free / 1024 ** 3
    if free_gb < MIN_FREE_GB:
        raise DiskFull(f"quedan {free_gb:.1f} GB libres en {OUT_DIR.resolve()}, "
                       f"por debajo del mínimo GCHAT_MIN_FREE_GB={MIN_FREE_GB:g}")


def download_attachment(chat, resource_name, dest: Path):
    if dest.exists() and dest.stat().st_size > 0:
        return "ya existía"
    check_free_space()
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    request = chat.media().download_media(resourceName=resource_name)
    with open(tmp, "wb") as fh:
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            _, done = downloader.next_chunk(num_retries=RETRIES)
    tmp.replace(dest)
    return "descargado"


def resolve_space_dir(space, members, messages, user_dir: Path, exporter_email, known):
    if space["name"] in known:
        return known[space["name"]]
    target = user_dir / folder_name(space, members, messages, exporter_email)
    if target.exists():  # la misma carpeta ya la usa otro chat
        target = target.with_name(f"{target.name}_{short_id(space['name'])}")
    legacy = user_dir / "spaces" / short_id(space["name"])  # estructura antigua spaces/<id>/
    if legacy.is_dir():
        legacy.rename(target)
    known[space["name"]] = target
    return target


def export_space(chat, space, user_dir: Path, exporter_email, known):
    space_id = short_id(space["name"])

    members = list(paginate(chat.spaces().members().list, "memberships",
                            parent=space["name"], pageSize=1000))

    msg_kwargs = {"parent": space["name"], "pageSize": 1000, "orderBy": "createTime asc"}
    if SINCE:
        msg_kwargs["filter"] = f'createTime > "{since_rfc3339(SINCE)}"'
    messages = list(paginate(chat.spaces().messages().list, "messages", **msg_kwargs))

    space_dir = resolve_space_dir(space, members, messages, user_dir, exporter_email, known)
    label = chat_label(space, members, exporter_email)

    attachments_ok = attachments_err = drive_links = 0
    if DOWNLOAD_ATTACHMENTS:
        for msg in messages:
            for i, att in enumerate(msg.get("attachment", []) or []):
                ref = (att.get("attachmentDataRef") or {}).get("resourceName")
                if not ref:
                    if att.get("driveDataRef"):
                        drive_links += 1  # está en Drive: queda el enlace en messages.json
                    continue
                fname = f"{safe_name(short_id(msg['name']))}_{i}_{safe_name(att.get('contentName'))}"
                try:
                    download_attachment(chat, ref, space_dir / "attachments" / fname)
                    att["_localFile"] = f"attachments/{fname}"
                    attachments_ok += 1
                except HttpError as e:
                    att["_downloadError"] = f"HTTP {e.resp.status}"
                    attachments_err += 1

    write_json(space_dir / "space.json", space)
    write_json(space_dir / "members.json", members)
    write_json(space_dir / "messages.json", messages)

    log(f"  {label}: {len(messages)} mensajes, {len(members)} miembros, "
        f"adjuntos {attachments_ok} ok / {attachments_err} error / {drive_links} en Drive")

    return {
        "id": space_id,
        "folder": space_dir.name,
        "name": space["name"],
        "displayName": space.get("displayName"),
        "spaceType": space.get("spaceType"),
        "messages": len(messages),
        "members": len(members),
        "attachments": attachments_ok,
        "attachmentErrors": attachments_err,
        "driveLinks": drive_links,
        "firstMessage": messages[0].get("createTime") if messages else None,
        "lastMessage": messages[-1].get("createTime") if messages else None,
    }


def main():
    creds = get_credentials()
    exporter = build("oauth2", "v2", credentials=creds, cache_discovery=False) \
        .userinfo().get().execute(num_retries=RETRIES).get("email")
    chat = build("chat", "v1", credentials=creds, cache_discovery=False)
    user_dir = OUT_DIR / safe_name(exporter.split("@")[0])
    log(f"Exportando como {exporter} a {user_dir.resolve()}")

    all_spaces = list(paginate(chat.spaces().list, "spaces", pageSize=1000))
    spaces = [s for s in all_spaces if wanted(s)]
    log(f"{len(all_spaces)} espacios visibles, {len(spaces)} seleccionados")

    if DRY_RUN:
        for s in spaces:
            print(f"  {s.get('spaceType'):15} {short_id(s['name'])}  {s.get('displayName') or ''}")
        return

    user_dir.mkdir(parents=True, exist_ok=True)
    known = existing_folders(user_dir)
    index, failed = [], []
    stopped = None
    started = datetime.now(timezone.utc).isoformat()

    for n, space in enumerate(spaces, 1):
        log(f"[{n}/{len(spaces)}] {space.get('displayName') or space['name']}")
        try:
            check_free_space()
            index.append(export_space(chat, space, user_dir, exporter, known))
        except DiskFull as e:
            stopped = str(e)
            log(f"DETENIDO: {stopped}. Libera espacio y relanza: continúa sin repetir adjuntos.")
            break
        except HttpError as e:
            log(f"  ERROR HTTP {e.resp.status}: se salta este espacio")
            failed.append({"name": space["name"], "displayName": space.get("displayName"),
                           "error": f"HTTP {e.resp.status}"})

    legacy = user_dir / "spaces"
    if legacy.is_dir() and not any(legacy.iterdir()):
        legacy.rmdir()
    write_json(user_dir / "index.json", index)
    write_json(user_dir / "manifest.json", {
        "exportedBy": exporter,
        "startedAt": started,
        "finishedAt": datetime.now(timezone.utc).isoformat(),
        "params": {
            "spaceTypes": sorted(SPACE_TYPES),
            "spaceFilter": SPACE_FILTER,
            "since": SINCE,
            "downloadAttachments": DOWNLOAD_ATTACHMENTS,
            "minFreeGb": MIN_FREE_GB,
        },
        "spaces": len(index),
        "messages": sum(s["messages"] for s in index),
        "failed": failed,
        "stoppedEarly": stopped,
    })
    log(f"Hecho: {len(index)} espacios, {sum(s['messages'] for s in index)} mensajes, "
        f"{len(failed)} con error")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit("\nInterrumpido. Puedes volver a lanzarlo: los adjuntos ya bajados no se repiten.")
