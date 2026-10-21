# Contributing

How to change the code. Using it is in two other guides: the backup, which anyone runs, in the
[README](README.md); the bootstrap, which the maintainer runs once in Google Cloud, in
[docs/how-to/bootstrap.md](docs/how-to/bootstrap.md).

| Section | You are… |
|:--|:--|
| [What is where](#what-is-where) | looking for a file |
| [Keep client data out of the repository](#keep-client-data-out-of-the-repository) | setting up a clone, or about to commit |
| [Change the code](#change-the-code) | working on the script or the Terraform |
| [Release](#release) | merging into `main` |

---

## What is where

```
google-chat-backup/
├── README.md                Backup phase: how anyone backs up their chats
├── backup.py                Launcher: creates scripts/.venv on first use and runs the backup
├── scripts/
│   ├── gchat_backup.py      The exporter; each person runs it with their own account
│   ├── requirements.txt     Its two Google dependencies
│   ├── .env.example         Optional backup settings (the real .env is never committed)
│   ├── bootstrap-plan.py    Bootstrap phase: plans terraform/bootstrap/ and prints the apply command
│   └── tf-env.py/.sh/.ps1   Terraform environment wrapper
├── terraform/bootstrap/     Bootstrap phase: enables the APIs (local state, never committed)
│   ├── imports.tf           Adopts APIs already enabled (only with bootstrap-plan.py --import)
│   └── resources/env/       template.env, terraform-default.tfvars.json; the real .default.env
│                            holds the project id and is never committed
├── docs/how-to/bootstrap.md Bootstrap phase: Terraform, console steps, access, teardown
├── .githooks/               pre-commit (client data, credentials) and pre-push (no push to main)
├── .gitleaks.toml           gitleaks rules for this repository (the defaults) and its exemptions
├── specs/                   Spec Kit specifications, one folder per feature
└── .specify/                Spec Kit constitution and templates
```

## Keep client data out of the repository

`.gitignore` blocks `client_secret*.json`, `token.json`, `.env`,
`terraform/bootstrap/resources/env/.*.env`, `*.tfvars`, saved plans, the Terraform state and the
backup output folders. The client secret, the session token and the project id live **only** on
each person's machine.

Two hooks in `.githooks/` guard the repository. `pre-commit` **aborts the commit** when the staged
files contain credentials, Terraform state, any term from a **local denylist**, or (with
[gitleaks](https://github.com/gitleaks/gitleaks) installed) a credential recognised by its shape.
`pre-push` **refuses any push to `main`**: changes reach it only through a pull request. GitHub
does not enforce that on this plan, so the hook is the guard. The denylist (`denylist.txt`)
is **not versioned**: it lives only on your machine, so the forbidden term (a client name, for
example) never reaches the repository, not even inside the hook. The hook names the file, never
the term.

Set them up in every clone; they do not activate by themselves:

```bash
git config core.hooksPath .githooks        # activate both hooks
cp denylist.example.txt denylist.txt        # then add your terms (one regex per line)
```

The hooks see staged files only. Before a pull request, scan every ref of the history for
credentials, and check the history and the commit messages for denylist terms:

```bash
gitleaks git --config .gitleaks.toml --log-opts=--all --redact .
T=$(grep -vE '^(#|$)' denylist.txt | paste -sd'|' -)
git grep -i -l -E "$T" $(git rev-list --all); git log --all --format=%B | grep -ciE "$T"
```

Expect `no leaks found`, then no file names and `0`. For a one-off legitimate case, skip a hook with
`git commit --no-verify` or `git push --no-verify`. A false positive from gitleaks is exempted in
`.gitleaks.toml`, with the reason written beside it.

## Change the code

- **Spec Kit:** changes to the script go through [Spec Kit](https://github.com/github/spec-kit).
  The constitution is `.specify/memory/constitution.md`; each feature has its folder in `specs/`
  with the specification, plan, tasks and how to validate it.
- **Before a commit:** `python3 -m py_compile scripts/gchat_backup.py backup.py scripts/bootstrap-plan.py`,
  the validation steps of the feature's `quickstart.md`, and the history check above.
- **Output:** the backup's terminal output follows a few rules: progress on stderr, the preview
  list on stdout, numbered steps, one aligned line per chat, the verdict last, errors as
  `Error: <fact>` plus `Hint: <action>`, no timestamps. Keep new messages in that shape.
- **Terraform:** `terraform fmt -recursive` must change nothing; variables and outputs stay in
  alphabetical order; never apply without a plan from `scripts/bootstrap-plan.py`, which classifies
  it first. The design choices are in
  [docs/how-to/bootstrap.md](docs/how-to/bootstrap.md#explanation-the-choices-behind-the-terraform).
- **Performance:** `GCHAT_WORKERS` backs up several chats at once. Measured 2026-10-21 with 20
  spaces and no attachments: 59 s with 1 worker, 19 s with 4, with no quota retries. Inside a chat
  attachments still download one at a time. Details in `specs/001-parallel-chat-export/research.md`.
- **Dropbox "online-only":** the backup decides whether an attachment already exists from its size
  alone, never its content, so it does not force Dropbox to download online-only files.

## Release

Work on a branch and reach `main` through a pull request. A release is an annotated tag `vX.Y.Z`
on `main` and a GitHub release whose notes come from the commits since the previous tag.

### Prior art (why this script and not a fork)

The closest existing project is [`pokhiii/gchat-export`](https://github.com/pokhiii/gchat-export)
(Apache-2.0, same user authentication), but it is written in Go, exports **one space per run** and
its macOS binary is unsigned. For this case (every space in one pass, Python, several teammates
running it) this script fits better. Ideas taken from it for later: token in the OS keychain,
`--resume` and SHA-256 hashes of attachments. Commercial tools (SysCloud, Spin, CloudFuze…) and
Takeout viewers do not fit: they are admin-only or expect the Takeout format, which is not what the
API returns.
