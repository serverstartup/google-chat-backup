# Tasks: Configurable chat folder layout

**Input**: [spec.md](spec.md), [plan.md](plan.md)

## Phase 1: Foundational

- [X] T001 Add the template setting, the date placeholder object and `render_folder()` with validation before signing in, in `scripts/gchat_backup.py`
- [X] T002 Replace `folder_name()` by the template fields (`name`, `last`, `first`, `type`, `id`) in `scripts/gchat_backup.py`

## Phase 2: User Story 1 + 2 — layout from the template (P1, P2)

- [X] T003 [US1] Render each chat's folder from the template in `resolve_space_dir()` in `scripts/gchat_backup.py`
- [X] T004 [US2] Invalid templates (unknown placeholder, attribute access, absolute, `..`, empty level, forbidden character) stop before signing in, exit 1, in `scripts/gchat_backup.py`

## Phase 3: User Story 3 — existing backups follow by themselves (P1)

- [X] T005 [US3] `existing_folders()` finds `space.json` at any depth, skips `attachments/` and hidden folders, retries a read, and reports the unreadable ones, in `scripts/gchat_backup.py`
- [X] T006 [US3] `main()` stops before exporting when a `space.json` is unreadable, in `scripts/gchat_backup.py`
- [X] T007 [US3] `resolve_space_dir()` moves a known folder to its rendered path with one rename, applies the `_<id>` rule, prunes empty parents and counts the move, in `scripts/gchat_backup.py`
- [X] T008 [US3] `index.json` records the relative path; the verdict and `manifest.json` count folders moved, in `scripts/gchat_backup.py`

## Phase 4: Polish

- [X] T009 [P] Document `GCHAT_FOLDER_TEMPLATE` in the module docstring, `scripts/.env.example` and the README settings table; describe the default layout where the README says where the backup ends up
- [X] T010 Scratch harness: move, clash, new month, second run moves nothing, unreadable `space.json`, each invalid template; each check mutated to red once
- [X] T011 Maintainer's backup (433 chats, already moved by the one-off script): the script's own `existing_folders()` and `folder_path()` over its `space.json` and `members.json` place 433 of 433 where they are, 0 moves. A live run against the API was not done
