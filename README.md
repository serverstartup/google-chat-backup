# google-chat-backup

<!-- doc-type: layered-how-to -->
<!-- doc-check: timeless -->

Back up every Google Chat conversation you take part in (spaces, group chats and 1:1 messages,
with their attachments) to your own disk, using your own Google account. It needs no admin
rights and no Google Cloud tools: each person exports what they would see in Chat on the web.
Built for one scenario: an organization is shutting down Google Workspace and you want to keep
your chats before it goes. Tested on macOS.

This page is for the person making a backup. Setting up Google Cloud, giving a teammate access,
reverting everything at the end and changing the code are in [CONTRIBUTING.md](CONTRIBUTING.md).

Before you start, ask the project maintainer for:

1. Access to the [serverstartup/google-chat-backup](https://github.com/serverstartup/google-chat-backup) repository.
2. To be added as a test user of the app, with your work email.
3. The `client_secret_….apps.googleusercontent.com.json` file, over a private channel. It is not in
   the repository and must never be.

| Section | You are… |
|:--|:--|
| [1. Get the code](#1-get-the-code) | starting from scratch |
| [2. Preview your chats](#2-preview-your-chats) | ready for the first run |
| [3. Run the backup](#3-run-the-backup) | happy with the list of chats |
| [4. Hand over the backup](#4-hand-over-the-backup) | done |
| [Appendix](#appendix) | stuck on an error, or wondering what a setting does |

---

## 1. Get the code

### `TL;DR`

1. Install Apple's command line tools: they bring `git` and `python3`, all this needs.
   ```bash
   xcode-select --install
   ```
   Expect: an installer opens, or a note that they are already installed.
2. Clone the repository into your home folder. → [Clone the repository](#clone-the-repository)
   ```bash
   git clone https://github.com/serverstartup/google-chat-backup.git ~/google-chat-backup
   ```
   Expect: the folder `~/google-chat-backup` exists.
3. Move the `client_secret` you were given into `scripts/`.
   ```bash
   mv ~/Downloads/client_secret_*.apps.googleusercontent.com.json ~/google-chat-backup/scripts/
   ```
   Expect: `ls ~/google-chat-backup/scripts/client_secret_*` shows one file.

### Clone the repository

A copy of the code in `~/google-chat-backup`:

```bash
git clone https://github.com/serverstartup/google-chat-backup.git ~/google-chat-backup
```

**If it fails:** the repository is private, so `git` needs your GitHub access. Without it, open the
repository page while signed in to GitHub, click **Code → Download ZIP**, unzip it and rename the
folder to `~/google-chat-backup`. Every command on this page assumes that folder.

---

## 2. Preview your chats

The first run signs you in with Google and lists the chats it would back up, without downloading
anything.

### `TL;DR`

1. Run the preview and sign in with your work account in the browser. → [Sign in with your account](#sign-in-with-your-account)
   ```bash
   ~/google-chat-backup/backup.sh --preview
   ```
   Expect: `as <your work email>`, the number of chats and their list.

### Sign in with your account

Google asks you in the browser who you are and what the script may read:

```bash
~/google-chat-backup/backup.sh --preview
```

The very first run also prepares a private Python environment in `scripts/.venv`; later runs skip
that.

**Procedure:**

1. A browser opens. Pick your **work** account, the one you use in Google Chat.
2. If you see *"Google hasn't verified this app"*, click **Advanced** → **Go to …**. It is the
   project's own app, in testing mode.
3. Accept the permissions: they are read-only (spaces, members and messages).
4. Close the tab and go back to the terminal.

**Verification:** the line under `[1/3] Signing in…` must show your work email. That is how the
script knows who you are: it never sees your password; Google grants it read access for the account
you signed in with, saved in `scripts/token.json`, and the script asks Google whose account that is.
Your backup goes into a folder named after your username (the part of your email before the `@`).
Later runs do not open the browser. Why nothing else is needed:
[Explanation: why signing in is enough](#explanation-why-signing-in-is-enough).

---

## 3. Run the backup

### `TL;DR`

1. Run the backup. → [Run it](#run-it)
   ```bash
   ~/google-chat-backup/backup.sh
   ```
   Expect: one `✓` line per chat and, last, `✓ Backed up N chats: …`.
2. If it stops, or you stop it with Ctrl-C, run the same command again: it carries on where it
   left off.
   ```bash
   ~/google-chat-backup/backup.sh
   ```
   Expect: chats already backed up show `(0 new)`.

### Run it

Downloads the messages and attachments of all your chats, 4 at a time:

```bash
~/google-chat-backup/backup.sh
```

Leave it in an open terminal with the laptop plugged in: with hundreds of chats it takes hours,
and chats with thousands of attachments are the slowest. The output looks like this:

```text
[1/3] Signing in…
  as you@example.com
[2/3] Listing chats…
  433 chats visible, 433 selected
[3/3] Backing up 433 chats to /Users/you/google-chat-backup/scripts/gchat-backup/you (4 at a time)…
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
2. Delete your credentials from the machine.
   ```bash
   rm -f ~/google-chat-backup/scripts/token.json ~/google-chat-backup/scripts/client_secret_*.json
   ```
   Expect: `ls ~/google-chat-backup/scripts/token.json` says it does not exist.
3. Optional: remove the app's access at [myaccount.google.com/connections](https://myaccount.google.com/connections).

---

## Appendix

### Reference: settings

Nothing needs configuring. To change a default, put it in `scripts/.env` (copy
`scripts/.env.example`) or in front of the command (`GCHAT_WORKERS=2 ~/google-chat-backup/backup.sh`).
Relative paths are resolved from `scripts/`.

| Setting | What it does | Default |
|:--|:--|:--|
| `GCHAT_OUT_DIR` | folder where the backup is stored (a Dropbox folder uploads it as it goes) | `gchat-backup` |
| `GCHAT_WORKERS` | chats backed up at the same time (1-16) | `4` |
| `GCHAT_MIN_FREE_GB` | stop when less free disk space is left, in GB | `20` |
| `GCHAT_DRY_RUN` | `true`: same as `--preview` | `false` |
| `GCHAT_CLIENT_SECRET` | path to the `client_secret` | the only `client_secret_*.json` in `scripts/` |
| `GCHAT_TOKEN_FILE` | where Google's access token is saved | `token.json` |
| `GCHAT_SPACE_TYPES` | chat types: `SPACE`, `GROUP_CHAT`, `DIRECT_MESSAGE` | all three |
| `GCHAT_SPACE_FILTER` | regular expression on the space name | all |
| `GCHAT_SINCE` | only messages from this date on (`YYYY-MM-DD`) | all |
| `GCHAT_DOWNLOAD_ATTACHMENTS` | `false`: skip attachments | `true` |

Used by: [Run it](#run-it).

### Explanation: why signing in is enough

The script uses Google's user authentication: it acts as you and only sees what you would see in
Google Chat on the web. That is why it needs no service account, no `gcloud` and no admin rights.
The `client_secret` does not identify anyone: it identifies the app the maintainer registered in
Google Cloud, and it is the same for the whole team. Who you are is decided by the browser sign-in;
that is why each person gets their own `token.json`, which is never shared.

Used by: [Sign in with your account](#sign-in-with-your-account).

### Troubleshooting: "Access blocked" or "access_denied" when signing in

This issue occurs when your email is not registered as a test user of the app, when you pick a
personal account instead of your work one, or when you cancel the permissions screen. To resolve
it, ask the maintainer to add your work email as a test user, delete
`~/google-chat-backup/scripts/token.json` if it exists and run the
[preview](#2-preview-your-chats) again with your work account.

Used by: [Sign in with your account](#sign-in-with-your-account).

### Troubleshooting: the backup stops for lack of disk space

This issue occurs when free disk space drops below the minimum (`GCHAT_MIN_FREE_GB`, 20 GB by
default): the backup stops cleanly before the disk fills up. To resolve it, free up space (if the
backup is in Dropbox, right-click the folder → **Make online-only** once it has been uploaded) and
run the same command again; nothing is downloaded twice.

Used by: [Run it](#run-it).
