# Contract: configuration through `GCHAT_*` variables

The script is configured only through environment variables (or `scripts/.env`). This feature
adds one and does not change the meaning of the others.

| Variable | Type | Default | Range | Error if invalid |
| :--- | :--- | :--- | :--- | :--- |
| `GCHAT_WORKERS` | integer | `4` (was `1`; amended by spec 002 FR-011) | 1–16 | `Error: GCHAT_WORKERS must be an integer between 1 and 16: '<value>'` plus a `Hint:` line, exit 1 before authenticating |

Unchanged: `GCHAT_CLIENT_SECRET`, `GCHAT_TOKEN_FILE`, `GCHAT_OUT_DIR`, `GCHAT_SPACE_TYPES`,
`GCHAT_SPACE_FILTER`, `GCHAT_SINCE`, `GCHAT_DOWNLOAD_ATTACHMENTS`, `GCHAT_DRY_RUN`,
`GCHAT_MIN_FREE_GB`.

## Output

- Folder structure: the same (`<OUT_DIR>/<user>/<YYYY-MM-DD>_<chat>/`).
- `manifest.json` → `params.workers` with the value used.
- `index.json`: same content for any value of `GCHAT_WORKERS`, in the order in which the API
  lists the chats.
- Exit codes: 0 on finishing or on stopping due to the disk brake (with `stoppedEarly`);
  non-zero with an invalid configuration value or Ctrl-C.
