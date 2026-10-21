# Contributing and maintaining

How to set up the Google Cloud side once, give a teammate access, revert everything at the end,
and change the code. Making a backup is in the [README](README.md).

| Section | You are… |
|:--|:--|
| [What is where](#what-is-where) | looking for a file |
| [Set up Google Cloud (once)](#set-up-google-cloud-once) | preparing the project for the first time |
| [Give a teammate access](#give-a-teammate-access) | about to send someone the README |
| [Revert everything](#revert-everything) | done with every backup |
| [Keep client data out of the repository](#keep-client-data-out-of-the-repository) | about to commit |
| [Change the code](#change-the-code) | working on the script |

---

## What is where

```
google-chat-backup/
├── README.md             How to make a backup, step by step
├── backup.py             Launcher: creates scripts/.venv on first use and runs the script
├── scripts/
│   ├── gchat_backup.py   The exporter; each person runs it with their own account
│   ├── requirements.txt  Its two Google dependencies
│   ├── .env.example      Optional settings template (the real .env is never committed)
│   ├── infra-plan.py     Plans terraform/, classifies the plan and prints the apply command
│   └── tf-env.py/.sh/.ps1  Terraform environment wrapper (project id from resources/env/.<env>.env)
├── terraform/            Enables the APIs in the GCP project (the only part with an API)
│   ├── imports.tf        Adopts APIs that are already enabled (off unless planned with --import)
│   └── resources/env/    tf-env settings: terraform-default.tfvars.json, template.env
│                         (the real .default.env holds the project id and is never committed)
├── docs/
│   ├── MANUAL_STEPS.md   What has no API and is done by hand, once
│   └── REVERT.md         How to leave everything as it was
├── specs/                Spec Kit specifications, one folder per feature
└── .specify/             Spec Kit constitution and templates
```

## Set up Google Cloud (once)

You need Terraform ≥ 1.5, `gcloud auth login` and the editor or owner role on the GCP project.
Google exposes an API for only part of the setup:

| Step | Automated? | Where |
|------|------------|-------|
| Enable the Google Chat API (and People API, which the script no longer uses) | Yes | `terraform/` |
| Create the GCP project | Yes (optional) | `terraform/` |
| OAuth consent screen (scopes, test users) | No API | [`docs/MANUAL_STEPS.md`](docs/MANUAL_STEPS.md) |
| **Desktop** OAuth client | No API, no `gcloud` | [`docs/MANUAL_STEPS.md`](docs/MANUAL_STEPS.md) |
| Chat app "Configuration" tab | No API | [`docs/MANUAL_STEPS.md`](docs/MANUAL_STEPS.md) |

1. **APIs, with Terraform.** The state is local (`terraform/terraform.tfstate`, never committed).
   Terraform always runs through `scripts/tf-env.py`, which takes the project id from
   `terraform/resources/env/.default.env`; nothing that names the project is in the repository.
   ```bash
   cp terraform/resources/env/template.env terraform/resources/env/.default.env   # set TF_VAR_project_id
   python3 scripts/infra-plan.py
   ```
   `infra-plan.py` runs `terraform init` and `terraform plan`, saves the plan outside the
   repository, prints what it imports, creates, changes and deletes (with the attributes of each
   change), refuses if it deletes or replaces anything, and prints the three commands that apply
   exactly that plan. Run them, then delete the plan file.

   If the APIs **are already enabled** (by hand, with `gcloud`, or the state was lost), adopt them
   instead of creating them: `python3 scripts/infra-plan.py --import`. Expect `2 to import`, and
   `disable_on_destroy` as the only update: it lives only in the state, so the apply makes no call
   to GCP. Before keeping `disable_on_destroy = true` (in `terraform-default.tfvars.json`), check
   the Service Usage audit log to confirm you enabled them: if they were already in use, set it to
   `false`.

2. **Manual steps:** follow [`docs/MANUAL_STEPS.md`](docs/MANUAL_STEPS.md) for the consent screen,
   the desktop OAuth client and the Chat app configuration. Download the `client_secret_*.json`
   into `scripts/` (it is never committed).

## Give a teammate access

The desktop OAuth client is shared by the whole team; who each person is comes from their own
browser sign-in. For a teammate to follow the [README](README.md) alone:

1. **Repository:** invite them with read access.
   ```bash
   gh api -X PUT repos/serverstartup/google-chat-backup/collaborators/<their-github-user> -f permission=pull
   ```
2. **Test user:** add their work email in the Google Cloud console → *Google Auth Platform* →
   *Audience* → *Test users*. Not needed if the app type is *Internal*. Without it, their sign-in
   ends in "Access blocked".
3. **`client_secret`:** send them the `client_secret_….json` file over a private channel. Never
   through the repository, nor through a chat that is going to be exported.
4. **Hand-over:** agree where they leave their `gchat-backup/<user>/` folder when they finish.

## Revert everything

Everything enabled is reversible. When every backup is done, follow
[`docs/REVERT.md`](docs/REVERT.md): `terraform destroy` disables the APIs
(`disable_on_destroy = true`), and the manual part (OAuth client, consent screen) is removed by
hand because it has no API.

## Keep client data out of the repository

`.gitignore` blocks `client_secret*.json`, `token.json`, `.env`, `terraform/resources/env/.*.env`,
`*.tfvars`, saved plans, the Terraform state and the backup output folders. The client secret and the session
token live **only** on each person's machine.

A `pre-commit` hook in `.githooks/` **aborts the commit** when the staged files contain
credentials, Terraform state or any term from a **local denylist**. The denylist (`denylist.txt`)
is **not versioned**: it lives only on your machine, so the forbidden term (a client name, for
example) never reaches the repository, not even inside the hook. The hook names the file, never
the term.

Set it up in every clone; it does not activate by itself:

```bash
git config core.hooksPath .githooks        # activate the hook
cp denylist.example.txt denylist.txt        # then add your terms (one regex per line)
```

For a one-off legitimate case, skip it with `git commit --no-verify`.

## Change the code

- **Spec Kit:** changes to the script go through [Spec Kit](https://github.com/github/spec-kit).
  The project constitution is `.specify/memory/constitution.md`; each feature has its folder in
  `specs/` with the specification, plan, tasks and how to validate it.
- **Branches:** work on a branch and reach `main` through a pull request merged with
  *Squash and merge*. Releases are annotated tags `vX.Y.Z` on `main` with a GitHub release.
- **Before a commit:** `python3 -m py_compile scripts/gchat_backup.py`, the validation steps of the
  feature's `quickstart.md`, and a check that no commit in the history matches the denylist.
- **Output:** the script's terminal output follows a few rules: progress on stderr, the preview
  list on stdout, numbered steps, one aligned line per chat, the verdict last, errors as
  `Error: <fact>` plus `Hint: <action>`, no timestamps. Keep new messages in that shape.
- **Performance:** `GCHAT_WORKERS` backs up several chats at once. Measured 2026-10-21 with 20
  spaces and no attachments: 59 s with 1 worker, 19 s with 4, with no quota retries. Inside a chat
  attachments still download one at a time, so a chat with thousands of attachments takes as long
  with 1 worker as with 4. Details in `specs/001-parallel-chat-export/research.md`.
- **Dropbox "online-only":** the script decides whether an attachment already exists from its size
  alone, never its content, so it does not force Dropbox to download online-only files. macOS 15
  has no terminal command to mark files online-only; it is done from the Finder.

### Prior art (why this script and not a fork)

The closest existing project is [`pokhiii/gchat-export`](https://github.com/pokhiii/gchat-export)
(Apache-2.0, same user authentication), but it is written in Go, exports **one space per run** and
its macOS binary is unsigned. For this case (every space in one pass, Python, several teammates
running it) this script fits better. Ideas taken from it for later: token in the OS keychain,
`--resume` and SHA-256 hashes of attachments. Commercial tools (SysCloud, Spin, CloudFuze…) and
Takeout viewers do not fit: they are admin-only or expect the Takeout format, which is not what the
API returns.
