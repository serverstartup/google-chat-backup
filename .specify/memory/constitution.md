<!--
- 2.0.1 (PATCH): Principle IV points to docs/how-to/bootstrap.md, which absorbed
  docs/REVERT.md and docs/MANUAL_STEPS.md; Terraform lives in terraform/bootstrap/.
Sync Impact Report
- Version: 1.0.0 → 2.0.0 (MAJOR: a constraint is redefined)
- Modified sections: Operating constraints — documentation, code comments and runtime messages
  are now in English (previously: documentation and comments in Spanish); output folder names
  stay in English with an ISO date prefix (`YYYY-MM-DD_<chat>`)
- Other changes: whole document translated from Spanish to English with no change in meaning;
  Principle IV now points to `docs/REVERT.md` (renamed from `docs/REVERTIR.md`)
- Principles added: none
- Sections added: none
- Sections removed: none
- Dependent artifacts: `specs/001-parallel-chat-export/` translated to English in the same pass
- Deferred TODOs: none
-->

# google-chat-backup Constitution

## Core Principles

### I. Simplicity

- A single Python script (`scripts/gchat_backup.py`), with no services, databases or daemons.
- The output is readable folders: one per chat, with the original API JSON and `attachments/`.
  No custom formats that need converting before they can be read.
- All configuration comes in through `GCHAT_*` variables, also from `scripts/.env`. Every new
  variable MUST have a default value that works without touching it.
- A feature that adds a dependency, a separate process or a manual step MUST justify in its
  plan why something simpler is not enough.

Rationale: three people run it once each before the Workspace shutdown, and the person in
charge explicitly asked for nothing complex.

### II. Resumable and idempotent

- Relaunching the script MUST NOT repeat complete downloads nor duplicate chat folders.
- An interruption (Ctrl-C, full disk, network, quota) MUST leave consistent data: atomic writes
  of JSON and attachments to `.part` files renamed only once finished.
- A chat's identity is its API id, not its name: a rename does not create a new folder.

Rationale: exports take hours and get interrupted; repeating work costs time and quota.

### III. Client data outside the repository

- 0 credentials, 0 client names, 0 project identifiers and 0 exported data in git.
- The `pre-commit` hook (`core.hooksPath .githooks`) with the local denylist MUST be active.
- The backup output lives outside the repository (a Dropbox folder); the local files holding
  sensitive data (`.env`, `terraform.tfvars`, `token.json`, `client_secret_*`) are ignored.

Rationale: the repository is shareable and the data belongs to a client.

### IV. Reversibility

- Everything enabled in GCP MUST be reverted with `terraform destroy` plus the steps in
  `docs/how-to/bootstrap.md` (task 4, teardown).
- Terraform manages only what has an API; the manual part is documented in
  `docs/how-to/bootstrap.md` (task 2).

Rationale: the GCP project is shared with the client and must be left as it was.

### V. Respect quotas and resources

- The script MUST NOT exceed the published Google Chat API quotas: on a 429 or a 5xx it retries
  with exponential backoff and never issues more simultaneous requests than the user
  configures.
- The script MUST NOT fill the disk: it stops cleanly below `GCHAT_MIN_FREE_GB`.
- Any form of parallelism MUST be configurable, with a conservative default value.

Rationale: a quota block or a full disk interrupts the backup and can affect other workloads
of the shared project or of the team.

### VI. Verification with evidence

- Every change is tested against real data or with a test that shows the mechanism fails when
  it should (positive and negative).
- Reports give counts and sizes, never message content nor chat names.

Rationale: a backup that looks complete and is not is discovered when there is no going back.

## Operating constraints

- Python 3.9+ and only the Google dependencies (`google-api-python-client`,
  `google-auth-oauthlib`); everything else, the standard library.
- User authentication (desktop OAuth): only what the person running it can see is exported.
- Documentation, code comments and runtime messages in English; output folder names in
  English, with an ISO date prefix (`YYYY-MM-DD_<chat>`).

## Workflow

- Functional changes to the script go through Spec Kit (`/speckit-specify` → `/speckit-plan` →
  `/speckit-tasks` → `/speckit-implement`).
- Before every commit: `py_compile` of the script, a test of the new mechanism and a check that
  the history contains no denylist terms.

## Governance

- This constitution prevails over other project practices. A plan that breaks it MUST justify
  it in its complexity section or be changed.
- Amendments: edited here with semantic versioning (MAJOR: a principle is removed or redefined;
  MINOR: a new principle or section; PATCH: wording).
- The operating context with client data lives in `CLAUDE.local.md` (not versioned).

**Version**: 2.0.1 | **Ratified**: 2026-10-21 | **Last Amended**: 2026-10-21
