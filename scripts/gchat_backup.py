#!/usr/bin/env python3
"""
gchat_backup.py — Copia local de Google Chat con la cuenta de quien lo ejecuta.

Usa autenticación de USUARIO (OAuth, "iniciar sesión con Google"): solo ve y
exporta los espacios, grupos y chats privados en los que esa persona es miembro.
No necesita permisos de administrador.

Qué guarda (en GCHAT_OUT_DIR):
  manifest.json                  quién exportó, cuándo, con qué parámetros y resumen
  index.json                     lista de espacios exportados (id, nombre, tipo, nº mensajes)
  people.json                    caché  users/<id> -> nombre y email (si se pudo resolver)
  spaces/<space_id>/space.json      datos del espacio tal como los da la API
  spaces/<space_id>/members.json    miembros
  spaces/<space_id>/messages.json   mensajes en orden cronológico (JSON original de la API)
  spaces/<space_id>/attachments/    adjuntos subidos al chat (los de Drive quedan como enlace)

Se puede ejecutar varias veces: reescribe los mensajes y no vuelve a bajar
adjuntos que ya existen. La carpeta usa el id del espacio, así que las copias
de varias personas se pueden unir después sin conflictos de nombres.

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
  GCHAT_RESOLVE_NAMES   true/false: traducir users/<id> a nombre y email con la
                        People API (directorio). Si la organización no lo permite,
                        se sigue sin nombres.                        [true]
  GCHAT_DRY_RUN         true/false: solo listar qué se exportaría    [false]
"""

import io
import json
import os
import re
import sys
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
RESOLVE_NAMES = env_bool("GCHAT_RESOLVE_NAMES", True)
DRY_RUN = env_bool("GCHAT_DRY_RUN", False)

SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/chat.spaces.readonly",
    "https://www.googleapis.com/auth/chat.memberships.readonly",
    "https://www.googleapis.com/auth/chat.messages.readonly",
]
if RESOLVE_NAMES:
    SCOPES.append("https://www.googleapis.com/auth/directory.readonly")

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


# ---------------------------------------------------------------- nombres de personas

class PeopleResolver:
    """Traduce 'users/<id>' a nombre y email usando el directorio de la organización."""

    def __init__(self, creds, cache_path: Path):
        self.cache_path = cache_path
        self.cache = read_json(cache_path, {})
        self.enabled = RESOLVE_NAMES
        self.api = build("people", "v1", credentials=creds, cache_discovery=False) if self.enabled else None

    def resolve(self, user_name):
        if not self.enabled or not user_name or not user_name.startswith("users/"):
            return
        if user_name in self.cache:
            return
        person_id = short_id(user_name)
        try:
            p = self.api.people().get(
                resourceName=f"people/{person_id}",
                personFields="names,emailAddresses",
                sources=["READ_SOURCE_TYPE_DIRECTORY", "READ_SOURCE_TYPE_PROFILE"],
            ).execute(num_retries=RETRIES)
            names = p.get("names") or [{}]
            emails = p.get("emailAddresses") or [{}]
            self.cache[user_name] = {
                "displayName": names[0].get("displayName"),
                "email": emails[0].get("value"),
            }
        except HttpError as e:
            if e.resp.status in (401, 403):
                log("Aviso: la organización no permite leer el directorio; se sigue sin nombres.")
                self.enabled = False
            self.cache[user_name] = {"displayName": None, "email": None}

    def save(self):
        write_json(self.cache_path, self.cache)


# ---------------------------------------------------------------- exportación

def wanted(space):
    if space.get("spaceType") not in SPACE_TYPES:
        return False
    if SPACE_FILTER_RE:
        name = space.get("displayName") or ""
        return bool(name) and bool(SPACE_FILTER_RE.search(name))
    return True


def download_attachment(chat, resource_name, dest: Path):
    if dest.exists() and dest.stat().st_size > 0:
        return "ya existía"
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


def export_space(chat, space, people: PeopleResolver):
    space_id = short_id(space["name"])
    space_dir = OUT_DIR / "spaces" / space_id
    label = space.get("displayName") or f"({space.get('spaceType')})"

    members = list(paginate(chat.spaces().members().list, "memberships",
                            parent=space["name"], pageSize=1000))

    msg_kwargs = {"parent": space["name"], "pageSize": 1000, "orderBy": "createTime asc"}
    if SINCE:
        msg_kwargs["filter"] = f'createTime > "{since_rfc3339(SINCE)}"'
    messages = list(paginate(chat.spaces().messages().list, "messages", **msg_kwargs))

    for m in members:
        people.resolve((m.get("member") or {}).get("name"))
    for msg in messages:
        people.resolve((msg.get("sender") or {}).get("name"))

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
    log(f"Exportando como {exporter} a {OUT_DIR.resolve()}")

    all_spaces = list(paginate(chat.spaces().list, "spaces", pageSize=1000))
    spaces = [s for s in all_spaces if wanted(s)]
    log(f"{len(all_spaces)} espacios visibles, {len(spaces)} seleccionados")

    if DRY_RUN:
        for s in spaces:
            print(f"  {s.get('spaceType'):15} {short_id(s['name'])}  {s.get('displayName') or ''}")
        return

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    people = PeopleResolver(creds, OUT_DIR / "people.json")
    index, failed = [], []
    started = datetime.now(timezone.utc).isoformat()

    for n, space in enumerate(spaces, 1):
        log(f"[{n}/{len(spaces)}] {space.get('displayName') or space['name']}")
        try:
            index.append(export_space(chat, space, people))
        except HttpError as e:
            log(f"  ERROR HTTP {e.resp.status}: se salta este espacio")
            failed.append({"name": space["name"], "displayName": space.get("displayName"),
                           "error": f"HTTP {e.resp.status}"})
        people.save()

    write_json(OUT_DIR / "index.json", index)
    write_json(OUT_DIR / "manifest.json", {
        "exportedBy": exporter,
        "startedAt": started,
        "finishedAt": datetime.now(timezone.utc).isoformat(),
        "params": {
            "spaceTypes": sorted(SPACE_TYPES),
            "spaceFilter": SPACE_FILTER,
            "since": SINCE,
            "downloadAttachments": DOWNLOAD_ATTACHMENTS,
            "resolveNames": RESOLVE_NAMES,
        },
        "spaces": len(index),
        "messages": sum(s["messages"] for s in index),
        "failed": failed,
    })
    log(f"Hecho: {len(index)} espacios, {sum(s['messages'] for s in index)} mensajes, "
        f"{len(failed)} con error")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit("\nInterrumpido. Puedes volver a lanzarlo: los adjuntos ya bajados no se repiten.")
