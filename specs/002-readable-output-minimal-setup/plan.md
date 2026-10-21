# Implementation Plan: Readable output and minimal setup

**Branch**: `001-parallel-chat-export` | **Date**: 2026-10-21 | **Spec**: [spec.md](spec.md)

## Summary

Replace the timestamped `log()` with a small set of output helpers in `scripts/gchat_backup.py`
(`step()`, `done()`, `failed()`, `warn()`, `fail()`), all writing to stderr except the preview
list, which goes to stdout. Add `--preview`. Silence the two known library warnings. Add a
root `backup.sh` that creates `scripts/.venv` with the system `python3` on first use and runs
the script. Loosen `requirements.txt` to lower bounds so it installs on Python 3.9. Default
`GCHAT_WORKERS` to 4. Rewrite the README setup around these.

## Technical Context

**Language/Version**: Python 3.9+ (system Python on macOS is 3.9.6)
**Primary Dependencies**: `google-api-python-client>=2.100`, `google-auth-oauthlib>=1.2`; stdlib
**Testing**: captured runs (preview, small real run, error paths) checked against FR-001..FR-008;
fresh clone with `/usr/bin/python3` for FR-009/FR-010
**Project Type**: single-file CLI plus one shell launcher

## Constitution Check

| Principle | Complies | How |
| :--- | :--- | :--- |
| I Simplicity | Yes | No new dependency (no `rich`); one launcher replaces three tools |
| II Resumable | Yes | Output only; resume logic untouched |
| III Data outside the repo | Yes | No change |
| IV Reversibility | Yes | No change |
| V Quotas and resources | Yes | Default 4 workers was measured with 0 quota retries; cap stays 16 |
| VI Evidence | Yes | Each FR checked on captured output, including Python 3.9 |

## Project Structure

```text
backup.sh                 # new: launcher (venv on first use + run)
scripts/gchat_backup.py   # output helpers, --preview, warnings filter, default workers 4
scripts/requirements.txt  # lower bounds
scripts/.env.example      # WORKERS default documented
README.md                 # minimal setup
```

## Output design

```text
[1/3] Signing in…
  as someone@example.com
[2/3] Listing chats…
  433 chats visible, 433 selected
[3/3] Backing up 433 chats to /path/to/gchat-backup/someone (4 at a time)…
  ✓ [  1/433] Server Startup S.L.            12,513 messages    687 attachments (0 new)
  ✗ [  2/433] Some space                     HTTP 403
✓ Backed up 432 of 433 chats: 120,034 messages, 9,447 attachments (371 new)
✗ 1 chat failed; run the same command again to retry it
```

Verdict variants: all done (`✓ Backed up N chats: …`), stopped (`⚠ Stopped: <reason>` + hint),
failures (`✗ N chats failed` + hint), interrupted (`⚠ Interrupted` + hint).

## Complexity Tracking

No deviations.
