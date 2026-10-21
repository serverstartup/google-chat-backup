# Tasks: Readable output and minimal setup

**Input**: `specs/002-readable-output-minimal-setup/` (spec.md, plan.md)

All code tasks touch `scripts/gchat_backup.py` and run in order.

## Phase 1: User Story 1 — Read the progress at a glance (P1)

- [X] T001 [US1] Add output helpers to `scripts/gchat_backup.py`: `step(k, m, text)` (`[k/m] text…`), `info(text)` (two-space indent), `chat_line(ok, n, total, name, detail)` (aligned, name truncated with `…`), `verdict(mark, text)`, `fail(fact, hint, code=1)` (`Error: …` / `Hint: …`); all to stderr through one locked writer; no timestamps
- [X] T002 [US1] Replace every `log(...)` call in `scripts/gchat_backup.py` with the helpers, following the output design in plan.md; per-chat detail `N messages  N attachments (N new)` plus ` · N in Drive` and ` · N errors` only when non-zero
- [X] T003 [US1] Route user-fixable `sys.exit("…")` messages (client secret, `GCHAT_WORKERS`, `GCHAT_MIN_FREE_GB`, `GCHAT_SINCE`) through `fail()` with a hint in `scripts/gchat_backup.py`
- [X] T004 [US1] Write the verdict last in `scripts/gchat_backup.py`: done, stopped (disk), failures, interrupted — each with its hint when there is something to do
- [X] T005 [US1] Print the preview list on stdout (`<type>  <name>`), everything else on stderr, in `scripts/gchat_backup.py`
- [X] T006 [US1] Filter the Python-EOL `FutureWarning` from `google.*` and urllib3's `NotOpenSSLWarning` in `scripts/gchat_backup.py`, with a comment naming why
- [X] T007 [US1] Add `--preview` (and `-h/--help`) with `argparse` in `scripts/gchat_backup.py`; unknown arguments exit 2

## Phase 2: User Story 2 — Set up with what the machine already has (P1)

- [X] T008 [US2] Create `backup.sh` at the repo root: `cd scripts`, create `.venv` with `python3 -m venv` if missing, `pip install -q -r requirements.txt`, then `exec .venv/bin/python gchat_backup.py "$@"`; on install failure print `Error:` + `Hint:` and exit 1
- [X] T009 [US2] Change `scripts/requirements.txt` to lower bounds that install on Python 3.9
- [X] T010 [US2] Default `GCHAT_WORKERS` to 4 in `scripts/gchat_backup.py` and `scripts/.env.example`; amend 001 (spec FR-001, contract, plan) to record the change
- [X] T011 [US2] Rewrite the README setup and run sections around `backup.sh` and `--preview` (≤3 setup steps); keep `doc-howto-check.py` green

## Phase 3: Verification

- [X] T012 Capture a preview and a real run over 3 chats on `/usr/bin/python3` (3.9) and check FR-001..FR-008 and SC-001/SC-002 on the captured stderr/stdout
- [X] T013 Fresh clone into an empty folder, place the client secret, run `./backup.sh --preview` with only the system `python3` (SC-003)
- [X] T014 Error paths: no client secret, `GCHAT_WORKERS=abc`, unknown flag — check message shape and exit codes 1/1/2

## Phase 4: Amendment — any operating system (2026-10-21)

- [X] T015 [US2] Replace `backup.sh` with `backup.py` at the repo root: checks Python ≥ 3.9, creates `scripts/.venv` with `venv` (Windows `Scripts/python.exe`, else `bin/python`), installs `scripts/requirements.txt`, removes a half-built environment on failure, runs `scripts/gchat_backup.py` passing arguments and Ctrl-C through
- [X] T016 [US1] Reconfigure stdout/stderr with `errors="replace"` in `scripts/gchat_backup.py` and `backup.py` so a non-UTF-8 console never crashes on `✓` or `…`; argparse `prog` becomes `backup.py`
- [X] T017 [US2] README assumes only Git and Python 3.9+ on any OS; says the client secret comes from the maintainer; adds "Explanation: who can read what" with Google's sources
- [X] T018 Verify: fresh clone, `python3 backup.py --preview` and a real run on Python 3.9 and 3.12; a non-UTF-8 stderr (`PYTHONIOENCODING=ascii`) does not crash; Windows and Linux not available here, say so — done 2026-10-21 on macOS with Python 3.9.6 and 3.12.15; ASCII stderr prints `?` instead of `✓` without crashing; Python 3.8 refused with Error + Hint; Windows and Linux not run
