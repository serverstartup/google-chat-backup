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

- [ ] T012 Capture a preview and a real run over 3 chats on `/usr/bin/python3` (3.9) and check FR-001..FR-008 and SC-001/SC-002 on the captured stderr/stdout
- [ ] T013 Fresh clone into an empty folder, place the client secret, run `./backup.sh --preview` with only the system `python3` (SC-003)
- [ ] T014 Error paths: no client secret, `GCHAT_WORKERS=abc`, unknown flag — check message shape and exit codes 1/1/2
