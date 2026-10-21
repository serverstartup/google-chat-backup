# Implementation Plan: Configurable chat folder layout

**Branch**: `003-folder-template` | **Date**: 2026-10-21 | **Spec**: [spec.md](spec.md)

## Summary

Replace `folder_name()` in `scripts/gchat_backup.py` with a template rendered by Python's own
`string.Formatter`: `GCHAT_FOLDER_TEMPLATE`, default `{last:%Y}/{last:%m}/{name}`. Date
placeholders are a small object whose `__format__` applies strftime codes, so `{last:%Y%m%d}`
needs no parser of ours. Validate the template once, before signing in. Find existing chat
folders by `space.json` at any depth, and move a folder with one `os.rename` when its rendered
path changes, pruning the folders it leaves empty. Record the relative path in `index.json` and
count the moves in the verdict.

## Technical Context

**Language/Version**: Python 3.9+
**Primary Dependencies**: none added (stdlib `string`, `datetime`, `os`)
**Testing**: a scratch harness that imports the module with the output folder pointed at a
temporary directory and drives `resolve_space_dir()` with synthetic chats (move, clash, new
month, unreadable `space.json`); invalid templates through the real entry point (exit 1 before
signing in); one real run over the maintainer's backup, already moved by the one-off script, must
move 0 folders and download 0 attachments.
**Project Type**: single-file CLI

## Constitution Check

| Principle | Complies | How |
| :--- | :--- | :--- |
| I Simplicity | Yes | One setting, stdlib only; the template syntax is Python's own format syntax |
| II Resumable | Yes | Folders are still recognised by `space.json`; a move is one rename; an unreadable `space.json` stops the run instead of risking a duplicate |
| III Data outside the repo | Yes | No change |
| IV Reversibility | Yes | No change to Google Cloud |
| V Quotas and resources | Yes | The last-message date comes with the chat list: no extra API call; moves read no file content, so online-only files stay in the cloud |
| VI Evidence | Yes | Each FR proved by the harness or a captured run, each in both directions |

## Design

- **Fields**: `name` (today's naming), `last` (`lastActiveTime`, else last message read, else
  `createTime`), `first` (first message read, else `createTime`), `type`
  (`space` / `group-chat` / `direct-message`), `id` (short id). A missing date renders `undated`;
  a bare `{last}` renders `%Y%m%d`.
- **Validation** (FR-004): field names must be exactly one of the five (no attribute or index
  access); a sample render must give a relative path with no empty, `.` or `..` level and none of
  `<>:"\|?*`. Failure: `Error: GCHAT_FOLDER_TEMPLATE …` + `Hint:` with the placeholders, exit 1.
- **Discovery** (FR-005, FR-006, FR-007): `rglob("space.json")` under the user's folder, skipping
  anything under `attachments/` or a hidden folder; each read retried briefly (an online-only
  file can read empty while Dropbox fetches it). Any still unreadable: stop before exporting.
- **Move**: under the existing folders lock. Target taken by another chat, or occupied by a
  folder without `space.json`: append `_<id>`. Then `mkdir` the parent, `os.rename`, prune empty
  parents up to the user's folder, count the move.
- **Index** (FR-008): `folder` = path relative to the user's folder, `/`-separated.

## Project Structure

```text
scripts/gchat_backup.py   # template, validation, discovery at any depth, move, index path, verdict
scripts/.env.example      # GCHAT_FOLDER_TEMPLATE documented
README.md                 # settings table; where the backup ends up
```

## Complexity Tracking

No deviations.
