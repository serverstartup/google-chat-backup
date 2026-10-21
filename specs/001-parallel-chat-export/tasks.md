# Tasks: Parallel chat export compatible with Dropbox "online-only"

**Input**: Design documents from `specs/001-parallel-chat-export/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/env-config.md, quickstart.md

**Tests**: the specification does not ask for a suite; validation is the `quickstart.md`
scenarios, which appear as verification tasks at the end of each story.

All code tasks touch the same file (`scripts/gchat_backup.py`), so none of them can run in
parallel with another; only the documentation can.

## Phase 1: Setup

- [X] T001 Add `import threading` and `from concurrent.futures import ThreadPoolExecutor` in `scripts/gchat_backup.py`
- [X] T002 Raise `RETRIES` from 5 to 6 in `scripts/gchat_backup.py` (maximum wait 64 s, research §3)

---

## Phase 2: Foundational (blocks all stories)

- [X] T003 Read `GCHAT_WORKERS` in `scripts/gchat_backup.py`: integer, default `1`, range 1–16; if it is not valid, exit before authenticating with `GCHAT_WORKERS must be an integer between 1 and 16: '<value>'` (env-config contract)
- [X] T004 Create the shared state in `scripts/gchat_backup.py`: `STOP = threading.Event()`, `_folders_lock`, `_log_lock`; `log()` writes under `_log_lock`
- [X] T005 Define the `Stopped` exception in `scripts/gchat_backup.py` and make `check_free_space()` set `STOP` before raising `DiskFull`, and raise `Stopped` if `STOP` is already set

---

## Phase 3: User Story 1 — Faster backup with configurable parallelism (P1) MVP

**Goal**: export up to `GCHAT_WORKERS` chats at once with the same result as serially.

**Independent Test**: quickstart §1 and §2.

- [X] T006 [US1] In `scripts/gchat_backup.py`, make `export_space()` receive its own `chat` client, built by each thread with `build("chat", "v1", credentials=creds, cache_discovery=False)` and stored in a `threading.local()` (research §2)
- [X] T007 [US1] In `scripts/gchat_backup.py`, move folder resolution and creation (`resolve_space_dir`) under `_folders_lock`, creating the folder (`mkdir`) inside the lock so that two same-named chats do not pick the same one (FR-009, research §6)
- [X] T008 [US1] In `scripts/gchat_backup.py`, replace the `main()` loop with a `ThreadPoolExecutor(max_workers=WORKERS)`; each task logs `[n/total] <chat>` when starting, returns its index entry or its HTTP failure, and the main thread collects results in the original API order (FR-003, FR-005)
- [X] T009 [US1] In `scripts/gchat_backup.py`, distinguish in each chat's log the attachments downloaded from those that already existed (`attachments {new} new / {had} already present / {err} errors / {drive} in Drive`) and add `attachmentsDownloaded` to the index, so that resumption and "online-only" can be verified
- [X] T010 [US1] Add `workers` to `manifest.json` → `params` in `scripts/gchat_backup.py` (FR-010)
- [X] T011 [US1] Verify quickstart §1 (values `0` and `abc` rejected without opening the browser) and §2 (same `index.json` except for order, time with 4 threads ≤ half of that with 1) against the real API with a temporary folder

---

## Phase 4: User Story 2 — Relaunch over Dropbox "online-only" without downloading again (P1)

**Goal**: an existing attachment is never read nor downloaded again.

**Independent Test**: quickstart §5 (manual, requires marking a folder from the Finder).

- [X] T012 [US2] Review in `scripts/gchat_backup.py` that `download_attachment()` decides only with `exists()` and `stat().st_size` (without opening the file) and that a leftover `.part` does not count as existing (FR-006, FR-007); leave a one-line comment with the reason
- [X] T013 [US2] Verify quickstart §4 in the temporary folder: Ctrl-C midway with 4 threads, relaunch, 0 duplicate folders, 0 `.part`, attachments of the second pass counted as "already present"

---

## Phase 5: User Story 3 — Disk brake and resumption with several chats at once (P2)

**Goal**: brake and Ctrl-C stop all threads and leave a consistent index and summary.

**Independent Test**: quickstart §3 and §4.

- [X] T014 [US3] In `scripts/gchat_backup.py`, check `STOP` before starting each chat and before each attachment (via `check_free_space()`); on catching `DiskFull` or `Stopped`, shut the executor down with `shutdown(wait=True, cancel_futures=True)`, write `index.json` and `manifest.json` with `stoppedEarly` (FR-008, research §5)
- [X] T015 [US3] In `scripts/gchat_backup.py`, on `KeyboardInterrupt` in the main thread set `STOP`, wait for the threads and exit with the current message (without leaving threads downloading)
- [X] T016 [US3] Verify quickstart §3 with `GCHAT_WORKERS=4 GCHAT_MIN_FREE_GB=100000`: `STOPPED: <reason>. Free up space and run it again: …`, `stoppedEarly`, 0 attachments written

---

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T017 [P] Document `GCHAT_WORKERS` in the header of `scripts/gchat_backup.py` and in `scripts/.env.example` (4 recommended)
- [X] T018 [P] Add a short section to `README.md`: how to choose threads and how to mark "online-only" in Dropbox from the Finder, stating that there is no terminal command on macOS 15
- [ ] T019 `py_compile`, denylist check over the history, commit on the `001-parallel-chat-export` branch and merge to `main` — commit done on the branch (`e0feb32`); merge to `main` and push pending until Julio asks for it (git.md rule)
- [X] T020 Relaunch the real sync with `GCHAT_WORKERS=4` and re-arm the consumption monitoring

---

## Dependencies & Execution Order

- Setup (T001–T002) → Foundational (T003–T005) → US1 (T006–T011) → US2 and US3 → Polish.
- US2 depends only on T009 (counters) for its verification; US3 depends on T004–T005 and T008.
- All code tasks are sequential (same file). T017 and T018 can be done in parallel with each
  other.

## Parallel Example

```text
T017 (header + .env.example)  ||  T018 (README)
```

## Implementation Strategy

MVP = US1 (parallelism with an identical result). US2 and US3 are guarantees over what already
exists and are closed on the same branch before using `GCHAT_WORKERS=4` in the real sync (T020).
