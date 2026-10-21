# google-chat-backup

<!-- doc-type: layered-how-to -->
<!-- doc-check: timeless -->

Back up every Google Chat conversation you take part in (spaces, group chats and 1:1 messages,
with their attachments) to your own disk, using your own Google account. It needs no admin
rights and no Google Cloud tools: each person exports what they would see in Chat on the web.
Built for one scenario: an organization is shutting down Google Workspace and you want to keep
your chats before it goes.

The project has two phases, done by different people:

| Phase | Who | When | Guide |
|:--|:--|:--|:--|
| **Bootstrap** | the maintainer | once: enable the Google Cloud APIs, register the app, give each teammate access; tear it all down at the end | [docs/how-to/bootstrap.md](docs/how-to/bootstrap.md) |
| **Backup** | anyone with access, with their own account | whenever they want to save their chats | this page |

This page is the backup. It needs no Google Cloud tools and no Terraform: only what the maintainer
hands over. Changing the code is in [CONTRIBUTING.md](CONTRIBUTING.md).

**You need:** Git and [Python](https://www.python.org/downloads/) 3.9 or above (`python3 --version`;
on Windows, `py --version`). The commands below use `python3`; on Windows type `py` instead.

**Ask the project maintainer for** three things before you start (the maintainer's side is
[Give a teammate access](docs/how-to/bootstrap.md#3-give-a-teammate-access)):

1. Read access to the [serverstartup/google-chat-backup](https://github.com/serverstartup/google-chat-backup) repository.
2. To be added as a test user of the app, with your work email. Without it, Google refuses your
   sign-in with "Access blocked".
3. The `client_secret_….apps.googleusercontent.com.json` file. The maintainer creates it once in
   Google Cloud for the whole team and sends it to you over a private channel; it is never in the
   repository. What it is for: [Explanation: who can read what](#explanation-who-can-read-what).

| Section | You are… |
|:--|:--|
| [1. Get the code](#1-get-the-code) | holding the three things above |
| [2. Preview your chats](#2-preview-your-chats) | ready for the first run |
| [3. Run the backup](#3-run-the-backup) | happy with the list of chats |
| [4. Hand over the backup](#4-hand-over-the-backup) | done |
| [Appendix](#appendix) | stuck on an error, or wondering what a setting does |

---

## 1. Get the code

### `TL;DR`

1. Clone the repository and go into it.
   ```bash
   git clone https://github.com/serverstartup/google-chat-backup.git && cd google-chat-backup
   ```
   Expect: you are in the `google-chat-backup` folder.
2. Copy the `client_secret_….json` file the maintainer sent you into the `scripts/` folder, with
   its name unchanged.
   Expect: `scripts/` holds exactly one `client_secret_*.json` file.

---

## 2. Preview your chats

The first run signs you in with Google and lists the chats it would back up, without downloading
anything. Run every command from the `google-chat-backup` folder.

### `TL;DR`

1. Run the preview and sign in with your work account in the browser. → [Sign in with your account](#sign-in-with-your-account)
   ```bash
   python3 backup.py --preview
   ```
   Expect: `as <your work email>`, the number of chats and their list.

### Sign in with your account

Google asks you in the browser who you are and what the script may read:

```bash
python3 backup.py --preview
```

The very first run also prepares a private Python environment in `scripts/.venv`; later runs skip
that.

**Procedure:**

1. A browser opens. Pick your **work** account, the one you use in Google Chat.
2. If you see *"Google hasn't verified this app"*, click **Advanced** → **Go to …**. It is the
   project's own app, in testing mode.
3. Accept the permissions: they are read-only (spaces, members and messages).
4. Close the tab and go back to the terminal.

**Verification:** the line under `[1/2] Signing in…` must show your work email: that is the account
whose chats will be backed up. Your sign-in is saved in `scripts/token.json`, so later runs do not
open the browser. Your backup goes into a folder named after your username (the part of your email
before the `@`).

---

## 3. Run the backup

### `TL;DR`

1. Run the backup. → [Run it](#run-it)
   ```bash
   python3 backup.py
   ```
   Expect: one `✓` line per chat and, last, `✓ Backed up N chats: …`.
2. If it stops, or you stop it with Ctrl-C, run the same command again: it carries on where it
   left off.
   ```bash
   python3 backup.py
   ```
   Expect: chats already backed up show `(0 new)`.

### Run it

Downloads the messages and attachments of all your chats, 4 at a time:

```bash
python3 backup.py
```

Leave it running with the computer plugged in: with hundreds of chats it takes hours, and chats
with thousands of attachments are the slowest. The output looks like this:

```text
[1/3] Signing in…
  as you@example.com

[2/3] Listing chats…
  433 chats visible, 433 selected

[3/3] Backing up 433 chats to /home/you/google-chat-backup/scripts/gchat-backup/you (4 at a time)…
  ✓ [  1/433] Team space                  12,513 messages    687 attachments (12 new)
  ✓ [  2/433] Jane Doe                       81 messages     12 attachments (12 new)

✓ Backed up 433 chats: 120,034 messages, 9,447 attachments (371 new)
```

**Verification:** attachments stored in Google Drive are not downloaded; their link stays in the
JSON. If free disk space drops below 20 GB the backup stops by itself
([Troubleshooting: the backup stops for lack of disk space](#troubleshooting-the-backup-stops-for-lack-of-disk-space)).
The result is one folder per chat, `attachments/` only when it has any:

```text
scripts/gchat-backup/<your-user>/
  index.json  manifest.json
  2021-03-04_team-space/
    space.json  members.json  messages.json
    attachments/
```

---

## 4. Hand over the backup

### `TL;DR`

1. Hand over the `scripts/gchat-backup/<your-user>/` folder to the maintainer, however you agree
   (a shared Dropbox folder, for example). It holds private conversations: never put it anywhere
   public.
2. Delete `scripts/token.json` and the `client_secret_….json` file from `scripts/`.
   Expect: neither file is left in `scripts/`.
3. Optional: remove the app's access from your Google account at
   [myaccount.google.com/connections](https://myaccount.google.com/connections).

---

## Appendix

### Reference: settings

Nothing needs configuring. To change a default, put it in `scripts/.env` (copy
`scripts/.env.example`). Relative paths are resolved from `scripts/`.

| Setting | What it does | Default |
|:--|:--|:--|
| `GCHAT_OUT_DIR` | folder where the backup is stored (a Dropbox folder uploads it as it goes) | `gchat-backup` |
| `GCHAT_WORKERS` | chats backed up at the same time (1-16) | `4` |
| `GCHAT_MIN_FREE_GB` | stop when less free disk space is left, in GB | `20` |
| `GCHAT_DRY_RUN` | `true`: same as `--preview` | `false` |
| `GCHAT_CLIENT_SECRET` | path to the `client_secret` | the only `client_secret_*.json` in `scripts/` |
| `GCHAT_TOKEN_FILE` | where your Google sign-in is saved | `token.json` |
| `GCHAT_SPACE_TYPES` | chat types: `SPACE`, `GROUP_CHAT`, `DIRECT_MESSAGE` | all three |
| `GCHAT_SPACE_FILTER` | regular expression on the space name | all |
| `GCHAT_SINCE` | only messages from this date on (`YYYY-MM-DD`) | all |
| `GCHAT_DOWNLOAD_ATTACHMENTS` | `false`: skip attachments | `true` |

Used by: [Run it](#run-it).

### Explanation: who can read what

Two separate things are involved, and only one of them is personal.

- **The `client_secret` identifies the app, not a person.** It lets this script ask Google for
  permission; on its own it reads nothing. Google treats it as non-confidential for desktop apps
  ("Desktop apps are public clients and cannot keep secrets confidential"), which is why the
  whole team shares one. It still stays out of the repository, so that only people the maintainer
  chose can use the app.
- **Your sign-in decides whose chats are read.** Google gives the script a token only after you
  sign in and accept read-only permissions, and with that token the Chat API acts as you: it
  lists only the spaces you are a member of ("Lists spaces the caller is a member of") and returns
  what you would see in Chat on the web. Nobody can read another person's chats with this script,
  not even the maintainer: it requests no administrator permissions.

What follows from it: in a space you share, the backup includes the other members' messages, just
as Chat shows them to you. And `scripts/token.json` is the key to *your* chats: never share it,
and delete it when you finish ([4. Hand over the backup](#4-hand-over-the-backup)).

Sources (read 2026-10-21): Google, [OAuth 2.0 for iOS & Desktop Apps](https://developers.google.com/identity/protocols/oauth2/native-app);
Google Chat API, [`spaces.list`](https://developers.google.com/workspace/chat/api/reference/rest/v1/spaces/list).

Used by: [Sign in with your account](#sign-in-with-your-account).

### Troubleshooting: "Access blocked" or "access_denied" when signing in

This issue occurs when your email is not registered as a test user of the app, when you pick a
personal account instead of your work one, or when you cancel the permissions screen. To resolve
it, ask the maintainer to add your work email as a test user, delete `scripts/token.json` if it
exists and run the [preview](#2-preview-your-chats) again with your work account.

Used by: [Sign in with your account](#sign-in-with-your-account).

### Troubleshooting: the backup stops for lack of disk space

This issue occurs when free disk space drops below the minimum (`GCHAT_MIN_FREE_GB`, 20 GB by
default): the backup stops cleanly before the disk fills up. To resolve it, free up space (if the
backup is in Dropbox, right-click the folder → **Make online-only** once it has been uploaded) and
run the same command again; nothing is downloaded twice.

Used by: [Run it](#run-it).
