#!/usr/bin/env python3
"""
gchat_backup.py — Local copy of Google Chat with the account of whoever runs it.

Uses USER authentication (OAuth, "sign in with Google"): it only sees and
exports the spaces, groups and private chats that person is a member of.
It does not need administrator permissions.

What it saves (in GCHAT_OUT_DIR/<user>/, where <user> is the local part of the email):
  manifest.json                  who exported, when, with which parameters, and a summary
  index.json                     list of exported chats (id, folder, name, type, number of messages)
  <YYYY-MM-DD>_<chat>/           one folder per chat: date of the first message + name
    space.json                   chat data exactly as the API returns it
    members.json                 members (with name and email)
    messages.json                messages in chronological order, original API JSON
                                 (author with name and email; threads go in the thread field)
    attachments/                 attachments uploaded to the chat (Drive ones stay as a link)

  <chat> is the space name; in a 1:1 chat, the other person's name; in a group
  without a name, its members' names. If two chats yield the same folder, the id is appended.

It can be run several times: it rewrites the messages and does not download again
attachments that already exist. Each chat keeps its folder even if it is renamed later
(it is recognised by the id saved in space.json).

Dependencies: scripts/requirements.txt (see CONTRIBUTING.md).

Environment variables (also read from scripts/.env, which is in .gitignore;
template in scripts/.env.example):
  Relative paths are resolved from the scripts/ folder.
  GCHAT_CLIENT_SECRET   path to the JSON of the "Desktop app" OAuth client
                        [the only client_secret_*.json in scripts/]
  GCHAT_TOKEN_FILE      path where the session token is saved       [token.json]
  GCHAT_OUT_DIR         output folder                                [gchat-backup]
  GCHAT_SPACE_TYPES     types to export, comma-separated             [SPACE,GROUP_CHAT,DIRECT_MESSAGE]
                        SPACE = named space, GROUP_CHAT = unnamed group,
                        DIRECT_MESSAGE = 1:1 chat
  GCHAT_SPACE_FILTER    regular expression on the space name (case-insensitive).
                        If set, only named spaces that match are included;
                        groups and 1:1 chats (which have no name) are left out.
  GCHAT_SINCE           export only messages from this date on, e.g. 2024-01-01   [everything]
  GCHAT_DOWNLOAD_ATTACHMENTS  true/false                             [true]
  GCHAT_DRY_RUN         true/false: only list what would be exported, like --preview  [false]
  GCHAT_WORKERS         chats exported at a time, from 1 to 16. Speeds things up when there are
                        many chats; within a chat attachments still go one at a time, so a chat
                        with thousands of attachments takes just as long. Retries on
                        "too many requests" are automatic.  [4]
  GCHAT_MIN_FREE_GB     minimum free disk space, in GB. Below it, the backup
                        stops cleanly (saving index and manifest) instead of
                        filling the disk. Running it again resumes where it left off.  [20]
"""

import argparse
import contextlib
import io
import json
import os
import re
import shutil
import sys
import threading
import unicodedata
import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

# The macOS system Python (3.9, built against LibreSSL) makes the Google libraries warn on every
# run that the Python version is past end of life and that urllib3 wants OpenSSL. Neither affects
# the backup, and both would bury the progress lines, so they are filtered before the imports.
warnings.filterwarnings("ignore", message=r"You are using a Python version .* past its end of life")
warnings.filterwarnings("ignore", message=r"urllib3 v2 only supports OpenSSL")

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload


# ---------------------------------------------------------------- terminal output
# Progress and messages go to stderr; only the preview list goes to stdout, so it can be piped.
# No timestamps: one line per step and per chat, the verdict last, errors as Error: + Hint:.

_log_lock = threading.Lock()


def say(line=""):
    with _log_lock:
        print(line, file=sys.stderr, flush=True)


def step(k, m, text):
    """Numbered step header, `[k/m] Text…`, with a blank line before all but the first."""
    say(f"{'' if k == 1 else chr(10)}[{k}/{m}] {text}…")


def info(text):
    say(f"  {text}")


def verdict(mark, text, hint=None):
    say(f"\n{mark} {text}")
    if hint:
        say(f"Hint: {hint}")


def fail(fact, hint=None, code=1):
    """A failure the user can fix: what happened, then what to do."""
    say(f"Error: {fact}")
    if hint:
        say(f"Hint: {hint}")
    sys.exit(code)


def parse_args():
    parser = argparse.ArgumentParser(
        prog="backup.sh", description="Back up the Google Chat conversations you take part in.")
    parser.add_argument("--preview", action="store_true",
                        help="sign in and list the chats that would be backed up; download nothing")
    return parser.parse_args()


ARGS = parse_args()


# ---------------------------------------------------------------- configuration

def load_dotenv(path: Path):
    """Loads KEY=value from a local .env (gitignored). The real environment wins over the file."""
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip().removeprefix("export ").strip()
        os.environ.setdefault(key, value.strip().strip("'\""))


SCRIPT_DIR = Path(__file__).resolve().parent
load_dotenv(SCRIPT_DIR / ".env")


def env(name, default=None, required=False):
    value = os.environ.get(name, "").strip()
    if not value:
        if required:
            fail(f"Missing environment variable {name}", f"Set {name} in scripts/.env")
        return default
    return value


def env_bool(name, default):
    value = env(name)
    if value is None:
        return default
    return value.lower() in ("1", "true", "yes", "si", "sí", "on")


def local_path(value):
    """Relative paths are resolved from scripts/, wherever the script is launched from."""
    path = Path(value).expanduser()
    return path if path.is_absolute() else SCRIPT_DIR / path


def find_client_secret():
    """GCHAT_CLIENT_SECRET if set; otherwise, the only client_secret_*.json in scripts/."""
    if env("GCHAT_CLIENT_SECRET"):
        return local_path(env("GCHAT_CLIENT_SECRET"))
    found = sorted(SCRIPT_DIR.glob("client_secret_*.json"))
    if len(found) == 1:
        return found[0]
    if not found:
        fail(f"No client_secret_*.json file in {SCRIPT_DIR}",
             "Move the client_secret file the maintainer sent you into that folder")
    fail(f"{len(found)} client_secret_*.json files in {SCRIPT_DIR}",
         "Keep only one of them, or set GCHAT_CLIENT_SECRET to the one to use")


CLIENT_SECRET = find_client_secret()
TOKEN_FILE = local_path(env("GCHAT_TOKEN_FILE", "token.json"))
OUT_DIR = local_path(env("GCHAT_OUT_DIR", "gchat-backup"))
SPACE_TYPES = {t.strip().upper() for t in env(
    "GCHAT_SPACE_TYPES", "SPACE,GROUP_CHAT,DIRECT_MESSAGE").split(",") if t.strip()}
SPACE_FILTER = env("GCHAT_SPACE_FILTER")
SPACE_FILTER_RE = re.compile(SPACE_FILTER, re.IGNORECASE) if SPACE_FILTER else None
SINCE = env("GCHAT_SINCE")
DOWNLOAD_ATTACHMENTS = env_bool("GCHAT_DOWNLOAD_ATTACHMENTS", True)
DRY_RUN = ARGS.preview or env_bool("GCHAT_DRY_RUN", False)
try:
    MIN_FREE_GB = float(env("GCHAT_MIN_FREE_GB", "20"))
except ValueError:
    fail(f"GCHAT_MIN_FREE_GB is not a number: {env('GCHAT_MIN_FREE_GB')!r}",
         "Set GCHAT_MIN_FREE_GB to a number of gigabytes, for example 20")
_workers_raw = env("GCHAT_WORKERS", "4")
if not _workers_raw.isdigit() or not 1 <= int(_workers_raw) <= 16:
    fail(f"GCHAT_WORKERS must be an integer between 1 and 16: {_workers_raw!r}",
         "Set GCHAT_WORKERS to a value from 1 to 16 in scripts/.env, or remove it to use 4")
WORKERS = int(_workers_raw)

SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/chat.spaces.readonly",
    "https://www.googleapis.com/auth/chat.memberships.readonly",
    "https://www.googleapis.com/auth/chat.messages.readonly",
]

RETRIES = 6  # retries on 429 and 5xx, waiting rand()*2^n: up to 64 s, the ceiling Google recommends


# ---------------------------------------------------------------- utilities

# State shared between threads (GCHAT_WORKERS > 1)
STOP = threading.Event()        # disk brake or Ctrl-C: no thread starts anything new
_folders_lock = threading.Lock()  # choosing and creating a chat folder is a single operation
_tls = threading.local()        # one API client per thread: httplib2 is not thread-safe


def write_json(path: Path, data):
    """Atomic write: first to .tmp and then rename."""
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
        fail(f"GCHAT_SINCE is not a valid date: {value!r}", "Set GCHAT_SINCE as YYYY-MM-DD, for example 2024-01-01")
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------- authentication

def get_credentials():
    creds = None
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
        if not creds.has_scopes(SCOPES):
            creds = None  # the requested permissions changed: sign in again
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
        except Exception:
            creds = None
    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRET), SCOPES)
        info("Opening your browser to sign in with your work account")
        # the library prints its own prompt to stdout; keep stdout for the preview list
        with contextlib.redirect_stdout(sys.stderr):
            creds = flow.run_local_server(
                port=0, prompt="consent",
                authorization_prompt_message="  If the browser does not open, visit: {url}",
                success_message="Signed in. You can close this tab and go back to the terminal.")
    TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")
    try:
        os.chmod(TOKEN_FILE, 0o600)
    except OSError:
        pass
    return creds


# ---------------------------------------------------------------- export

def slug(text, max_len=60):
    """'Server Startup S.L.' -> 'server-startup-s-l' (ASCII, lowercase, hyphens)."""
    text = unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode()
    text = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return text[:max_len].rstrip("-")


def other_members(members, exporter_email):
    """Names of the members other than the exporter, sorted."""
    names = []
    for m in members:
        u = m.get("member") or {}
        if (u.get("email") or "").lower() == exporter_email.lower():
            continue
        names.append(u.get("displayName") or u.get("email") or "")
    return sorted(n for n in names if n)


def chat_label(space, members, exporter_email):
    """Readable chat name: the space's or, if it has none, the other members'."""
    return space.get("displayName") or ", ".join(other_members(members, exporter_email)) or "(unnamed)"


def folder_name(space, members, messages, exporter_email):
    """<YYYY-MM-DD>_<chat>: date of the first message and name of the space or of the people."""
    first = (messages[0].get("createTime") if messages else None) or space.get("createTime") or ""
    date = first[:10] if re.match(r"\d{4}-\d{2}-\d{2}", first) else "undated"
    if space.get("displayName"):
        name = slug(space["displayName"])
    else:
        people = other_members(members, exporter_email)
        name = "_".join(slug(n, 30) for n in people[:4]) + ("_and-more" if len(people) > 4 else "")
    return f"{date}_{name or 'unnamed'}"


def existing_folders(user_dir: Path):
    """space name -> folder already created in a previous run (by the id in space.json)."""
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


class Stopped(Exception):
    """Another thread triggered the stop (disk brake or Ctrl-C)."""


def check_free_space():
    """Stops before filling the disk: checked before each space and each attachment."""
    if STOP.is_set():
        raise Stopped()
    free_gb = shutil.disk_usage(OUT_DIR).free / 1024 ** 3
    if free_gb < MIN_FREE_GB:
        STOP.set()
        raise DiskFull(f"{free_gb:.1f} GB free in {OUT_DIR.resolve()}, "
                       f"below the minimum GCHAT_MIN_FREE_GB={MIN_FREE_GB:g}")


def download_attachment(chat, resource_name, dest: Path):
    # Metadata only (stat): a Dropbox "online-only" file is skipped without downloading it.
    # An interruption leaves <name>.part, which is not dest, so anything incomplete is downloaded again.
    if dest.exists() and dest.stat().st_size > 0:
        return "already present"
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
    return "downloaded"


def resolve_space_dir(space, members, messages, user_dir: Path, exporter_email, known):
    with _folders_lock:
        if space["name"] in known:
            return known[space["name"]]
        target = user_dir / folder_name(space, members, messages, exporter_email)
        owner = read_json(target / "space.json", {}).get("name") if target.exists() else None
        if target.exists() and owner and owner != space["name"]:
            # the folder belongs to another chat with the same date and name
            target = target.with_name(f"{target.name}_{short_id(space['name'])}")
        # (if it exists without space.json, it is from an earlier interruption of this same chat: it is reused)
        legacy = user_dir / "spaces" / short_id(space["name"])  # old layout spaces/<id>/
        if legacy.is_dir() and not target.exists():
            legacy.rename(target)
        target.mkdir(parents=True, exist_ok=True)
        # space.json from the start: if interrupted halfway, the next run recognises the folder
        write_json(target / "space.json", space)
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

    attachments_new = attachments_had = attachments_err = drive_links = 0
    if DOWNLOAD_ATTACHMENTS:
        for msg in messages:
            for i, att in enumerate(msg.get("attachment", []) or []):
                ref = (att.get("attachmentDataRef") or {}).get("resourceName")
                if not ref:
                    if att.get("driveDataRef"):
                        drive_links += 1  # it is in Drive: the link stays in messages.json
                    continue
                fname = f"{safe_name(short_id(msg['name']))}_{i}_{safe_name(att.get('contentName'))}"
                try:
                    result = download_attachment(chat, ref, space_dir / "attachments" / fname)
                    att["_localFile"] = f"attachments/{fname}"
                    if result == "downloaded":
                        attachments_new += 1
                    else:
                        attachments_had += 1
                except HttpError as e:
                    att["_downloadError"] = f"HTTP {e.resp.status}"
                    attachments_err += 1

    write_json(space_dir / "space.json", space)
    write_json(space_dir / "members.json", members)
    write_json(space_dir / "messages.json", messages)

    return {
        "label": label,
        "id": space_id,
        "folder": space_dir.name,
        "name": space["name"],
        "displayName": space.get("displayName"),
        "spaceType": space.get("spaceType"),
        "messages": len(messages),
        "members": len(members),
        "attachments": attachments_new + attachments_had,
        "attachmentsDownloaded": attachments_new,
        "attachmentErrors": attachments_err,
        "driveLinks": drive_links,
        "firstMessage": messages[0].get("createTime") if messages else None,
        "lastMessage": messages[-1].get("createTime") if messages else None,
    }


def chat_detail(entry):
    """`12,513 messages    687 attachments (12 new)`, plus Drive links and errors when there are any."""
    text = f"{entry['messages']:>7,} messages  {entry['attachments']:>6,} attachments ({entry['attachmentsDownloaded']:,} new)"
    if entry["driveLinks"]:
        text += f" · {entry['driveLinks']:,} in Drive"
    if entry["attachmentErrors"]:
        text += f" · {entry['attachmentErrors']:,} errors"
    return text


def main():
    steps = 2 if DRY_RUN else 3
    step(1, steps, "Signing in")
    creds = get_credentials()
    exporter = build("oauth2", "v2", credentials=creds, cache_discovery=False) \
        .userinfo().get().execute(num_retries=RETRIES).get("email")
    info(f"as {exporter}")
    chat = build("chat", "v1", credentials=creds, cache_discovery=False)
    user_dir = OUT_DIR / safe_name(exporter.split("@")[0])

    step(2, steps, "Listing chats")
    all_spaces = list(paginate(chat.spaces().list, "spaces", pageSize=1000))
    spaces = [s for s in all_spaces if wanted(s)]
    info(f"{len(all_spaces):,} chats visible, {len(spaces):,} selected")

    if DRY_RUN:
        for s in spaces:
            print(f"{s.get('spaceType')}\t{short_id(s['name'])}\t{s.get('displayName') or ''}", flush=True)
        verdict("✓", f"{len(spaces):,} chats would be backed up to {user_dir.resolve()}",
                "Run the same command without --preview to back them up")
        return 0

    user_dir.mkdir(parents=True, exist_ok=True)
    known = existing_folders(user_dir)
    started = datetime.now(timezone.utc).isoformat()
    total = len(spaces)
    width = len(str(total))
    finished = [0]  # chats finished so far, for the [k/total] counter (completion order)

    def thread_chat():
        if not hasattr(_tls, "chat"):
            _tls.chat = build("chat", "v1", credentials=creds, cache_discovery=False)
        return _tls.chat

    def chat_line(ok, name, detail):
        with _log_lock:
            finished[0] += 1
            name = name if len(name) <= 30 else name[:29] + "…"
            print(f"  {'✓' if ok else '✗'} [{finished[0]:>{width}}/{total}] {name:<30}  {detail}",
                  file=sys.stderr, flush=True)

    def run_one(n, space):
        """Exports one chat in a thread. Returns (status, n, data) and never raises HttpError."""
        if STOP.is_set():
            return "skipped", n, None
        try:
            check_free_space()
            entry = export_space(thread_chat(), space, user_dir, exporter, known)
            chat_line(True, entry["label"], chat_detail(entry))
            return "ok", n, entry
        except DiskFull as e:
            return "stopped", n, str(e)
        except Stopped:
            return "skipped", n, None
        except HttpError as e:
            chat_line(False, space.get("displayName") or space["name"], f"HTTP {e.resp.status}")
            return "failed", n, {"name": space["name"], "displayName": space.get("displayName"),
                                 "error": f"HTTP {e.resp.status}"}

    step(3, steps, f"Backing up {total:,} chats to {user_dir.resolve()} ({WORKERS} at a time)")
    results, stopped, interrupted = {}, None, False
    executor = ThreadPoolExecutor(max_workers=WORKERS)
    try:
        futures = [executor.submit(run_one, n, s) for n, s in enumerate(spaces, 1)]
        for fut in as_completed(futures):
            if fut.cancelled():
                continue
            status, n, data = fut.result()
            results[n] = (status, data)
            if status == "stopped" and stopped is None:
                stopped = data
                executor.shutdown(wait=False, cancel_futures=True)
    except KeyboardInterrupt:
        STOP.set()
        interrupted = True
        say("\n⚠ Stopping: finishing the attachments in progress…")
        executor.shutdown(wait=True, cancel_futures=True)
        for fut in futures:
            if fut.done() and not fut.cancelled():
                status, n, data = fut.result()
                results[n] = (status, data)
        stopped = "interrupted"
    executor.shutdown(wait=True)

    index = [results[n][1] for n in sorted(results) if results[n][0] == "ok"]
    failed = [results[n][1] for n in sorted(results) if results[n][0] == "failed"]
    for entry in index:
        entry.pop("label", None)

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
            "workers": WORKERS,
        },
        "spaces": len(index),
        "messages": sum(s["messages"] for s in index),
        "failed": failed,
        "stoppedEarly": stopped,
    })

    messages = sum(e["messages"] for e in index)
    attachments = sum(e["attachments"] for e in index)
    new = sum(e["attachmentsDownloaded"] for e in index)
    totals = f"{messages:,} messages, {attachments:,} attachments ({new:,} new)"
    again = "Run the same command again: it carries on without downloading anything twice"
    if interrupted:
        verdict("⚠", f"Interrupted after {len(index):,} of {total:,} chats: {totals}", again)
        return 1
    if stopped:
        verdict("⚠", f"Stopped after {len(index):,} of {total:,} chats: {stopped}",
                "Free up disk space, then run the same command again")
        return 0
    if failed:
        verdict("✗", f"Backed up {len(index):,} of {total:,} chats, {len(failed):,} failed: {totals}",
                "Run the same command again to retry the failed chats")
        return 1
    verdict("✓", f"Backed up {total:,} chats: {totals}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        verdict("⚠", "Interrupted before the backup started", "Run the same command again")
        sys.exit(1)
