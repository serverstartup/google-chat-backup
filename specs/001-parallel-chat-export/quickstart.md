# Quickstart: validate the parallel export

All tests use a temporary output folder and a chat filter, so they do not touch the real
backup. From `scripts/`, with the venv and `scripts/.env` already set up (see README).

```bash
cd scripts
OUT=$(mktemp -d)
FILTER='<regex matching 6-10 small spaces>'
```

## 1. Invalid value (FR-002)

```bash
GCHAT_WORKERS=0  .venv/bin/python gchat_backup.py   # exits with the contract's message
GCHAT_WORKERS=abc .venv/bin/python gchat_backup.py  # same
```

Expected: non-zero exit code, without opening the browser or creating folders.

## 2. Same result and less time (FR-005, SC-001)

```bash
time GCHAT_DRY_RUN=false GCHAT_WORKERS=1 GCHAT_SPACE_FILTER="$FILTER" GCHAT_OUT_DIR=$OUT/w1 .venv/bin/python gchat_backup.py
time GCHAT_DRY_RUN=false GCHAT_WORKERS=4 GCHAT_SPACE_FILTER="$FILTER" GCHAT_OUT_DIR=$OUT/w4 .venv/bin/python gchat_backup.py
```

Expected: same folders, same number of messages and attachments per chat (compare `index.json`
ignoring line order); the second takes at most half as long.

## 3. Disk brake with threads (FR-008, SC-004)

```bash
GCHAT_DRY_RUN=false GCHAT_WORKERS=4 GCHAT_MIN_FREE_GB=100000 GCHAT_OUT_DIR=$OUT/brake .venv/bin/python gchat_backup.py
```

Expected: `STOPPED: <reason>. Free up space and run it again: …`, `manifest.json` with
`stoppedEarly`, 0 attachments written.

## 4. Resumption without duplicates (FR-007, SC-005)

Run test 2 with `GCHAT_WORKERS=4` over a new folder, Ctrl-C midway, relaunch.
Expected: no. of chat folders = no. of chats; no `.part` left after finishing.

## 5. Dropbox "online-only" (FR-006, SC-003) — manual

1. In the Finder, on the `attachments/` folder of a chat already exported to Dropbox:
   right-click → **Make online-only**. Wait for the icon to change.
2. Check that it has no local content: `ls -lO <folder>/attachments | grep -c dataless`.
3. Relaunch the backup (with a `GCHAT_SPACE_FILTER` that includes that chat).
4. Expected: the log says `attachments 0 new / N already present / X errors / Y in Drive`, with
   no new downloads, and step 2 gives the same number.
