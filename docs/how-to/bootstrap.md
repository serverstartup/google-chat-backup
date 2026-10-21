# How to bootstrap the project for the team

<!-- doc-type: layered-how-to -->
<!-- doc-check: timeless -->

The project has two phases. **Bootstrap** is done once, by one person (the maintainer), in the
organization's Google Cloud project: enable the APIs, register the app, give each teammate access,
and tear it all down at the end. **Backup** is done by each person with their own account, and is
in the [README](../../README.md); it needs nothing from this page except what the maintainer hands
over in [3. Give a teammate access](#3-give-a-teammate-access).

| Section | You are… |
|:--|:--|
| [1. Enable the APIs with Terraform](#1-enable-the-apis-with-terraform) | starting the bootstrap |
| [2. Register the app in the Google Cloud console](#2-register-the-app-in-the-google-cloud-console) | done with Terraform |
| [3. Give a teammate access](#3-give-a-teammate-access) | about to send someone the README |
| [4. Tear everything down](#4-tear-everything-down) | done with every backup |
| [Appendix](#appendix) | wondering why, or stuck on an error |

---

## 1. Enable the APIs with Terraform

Terraform enables the Google Chat API and the People API in the project. Its state is local
(`terraform/bootstrap/terraform.tfstate`, never committed), and it always runs through
`scripts/tf-env.py`, which reads the project id from a git-ignored file.

### `TL;DR`

1. Sign in to Google Cloud with an account that is editor or owner of the project. → [Sign in to Google Cloud](#sign-in-to-google-cloud)
   ```bash
   gcloud auth application-default login
   ```
   Expect: the browser confirms the sign-in.
2. From the repository folder, create the environment file and set `TF_VAR_project_id` in it.
   ```bash
   cp terraform/bootstrap/resources/env/template.env terraform/bootstrap/resources/env/.default.env
   ```
   Expect: `.default.env` holds your project id instead of `changeme`.
3. Plan. → [Plan the bootstrap](#plan-the-bootstrap)
   ```bash
   python3 scripts/bootstrap-plan.py
   ```
   Expect: `2 to create` and, last, one command to apply the plan.
4. Run the one command the plan printed.
   Expect: `Apply complete! Resources: 2 added, 0 changed, 0 destroyed.`
5. Plan again to check nothing is left.
   ```bash
   python3 scripts/bootstrap-plan.py
   ```
   Expect: `✓ No changes: nothing to apply`.

### Sign in to Google Cloud

Application Default Credentials for the account Terraform acts as:

```bash
gcloud auth application-default login
```

**Prerequisites:** [Terraform](https://developer.hashicorp.com/terraform/install) 1.7 or above, the
[Google Cloud CLI](https://cloud.google.com/sdk/docs/install), Python 3.9 or above, and the editor
or owner role on the project. If your active `gcloud` account belongs to another organization, sign
in with the right account here; the backup itself never uses these credentials.

### Plan the bootstrap

Init and plan through `tf-env`, then a summary of the plan:

```bash
python3 scripts/bootstrap-plan.py
```

The plan is saved outside the repository, because it holds the project id. The script prints what it
imports, creates, changes (with the attributes of each change) and deletes; it refuses a plan that
deletes or replaces anything; and it prints **one line** that changes to the right folder, loads
the environment, applies exactly that plan and deletes it. Run that line as it is, from any folder.

**If the APIs are already enabled** (by hand, with `gcloud`, or the state was lost), adopt them
instead of creating them: `python3 scripts/bootstrap-plan.py --import`. Expect `2 to import` and
`disable_on_destroy` as the only update: it exists only in the state, so applying makes no call to
Google Cloud. Why it is not the default:
[Explanation: the choices behind the Terraform](#explanation-the-choices-behind-the-terraform).

---

## 2. Register the app in the Google Cloud console

Three settings have no API and no Terraform support, so they are made by hand, once, in the
[Google Cloud console](https://console.cloud.google.com/) with the project selected at the top.

### `TL;DR`

1. Configure the Chat app: *APIs & Services* → *Google Chat API* → **Configuration**. Set any app
   name and description, and `https://localhost` as the HTTP endpoint URL; leave every other
   option unticked.
   Expect: it saves without errors. Why a fake endpoint: [Explanation: what the console steps are for](#explanation-what-the-console-steps-are-for).
2. Choose the consent screen's user type: *Google Auth Platform* (or *OAuth consent screen*) →
   **Internal** if it is offered, otherwise **External** in **Testing** mode.
   Expect: the app is created with that type.
3. Add exactly these three read-only scopes to the consent screen.
   ```text
   https://www.googleapis.com/auth/chat.spaces.readonly
   https://www.googleapis.com/auth/chat.messages.readonly
   https://www.googleapis.com/auth/chat.memberships.readonly
   ```
   Expect: the three scopes are listed, and no other.
4. Create the desktop OAuth client: *APIs & Services* → *Credentials* → **Create credentials** →
   **OAuth client ID** → **Desktop app**, and download its JSON.
   Expect: a `client_secret_….apps.googleusercontent.com.json` file.
5. Put that file in `scripts/` and run the backup preview from the [README](../../README.md#2-preview-your-chats).
   ```bash
   python3 backup.py --preview
   ```
   Expect: your chats are listed. Then give yourself and each teammate access with
   [3. Give a teammate access](#3-give-a-teammate-access).

---

## 3. Give a teammate access

What a teammate needs so they can follow the [README](../../README.md) alone. The OAuth client is one
for the whole team; who each person is comes from their own sign-in.

### `TL;DR`

1. Invite them to the repository with read access.
   ```bash
   gh api -X PUT repos/serverstartup/google-chat-backup/collaborators/<their-github-user> -f permission=pull
   ```
   Expect: GitHub sends them an invitation.
2. Add their work email as a test user: *Google Auth Platform* → *Audience* → *Test users*. Skip it
   if the app type is Internal.
   Expect: their email is in the list. Without it, their sign-in ends in "Access blocked".
3. Send them the `client_secret_….json` file over a private channel: never through the repository,
   nor through a chat that is going to be exported.
4. Agree where they leave their `scripts/gchat-backup/<user>/` folder when they finish.

---

## 4. Tear everything down

When every backup is done, leave the project as it was: first what has no API, then Terraform.

### `TL;DR`

1. In the console, delete the desktop OAuth client: *APIs & Services* → *Credentials* → bin icon.
2. In the console, remove the test users and scopes from the consent screen, or leave the app in
   draft. An Internal app can stay.
3. Optional: clear the Chat app configuration (*Google Chat API* → *Configuration*).
4. Plan the teardown. → [Plan the teardown](#plan-the-teardown)
   ```bash
   python3 scripts/bootstrap-plan.py --destroy
   ```
   Expect: `2 to delete`, both `google_project_service`, and one command to apply the plan.
5. Run the one command the plan printed.
   Expect: `Apply complete! Resources: 0 added, 0 changed, 2 destroyed.`
6. Each person deletes `scripts/token.json` and the `client_secret_….json` file from their copy.

### Plan the teardown

A plan that disables the two APIs:

```bash
python3 scripts/bootstrap-plan.py --destroy
```

**Prerequisites:** the project may be shared with other teams or workloads, and disabling an API
affects the whole project. Confirm nobody else uses the Chat or People API first. To leave the APIs
on, set `"disable_on_destroy": false` in
`terraform/bootstrap/resources/env/terraform-default.tfvars.json`, run `bootstrap-plan.py` and apply
before this step: the teardown then only removes them from the state.

---

## Appendix

### Reference: what is automated and what is not

| Step | Automated? | Where |
|:--|:--|:--|
| Enable the Google Chat API (and People API, which the backup no longer uses) | Yes | `terraform/bootstrap/` |
| Create the GCP project | Yes, optional (`create_project`) | `terraform/bootstrap/` |
| Chat app configuration | No API | [2. Register the app](#2-register-the-app-in-the-google-cloud-console) |
| OAuth consent screen (scopes, test users) | No API | [2. Register the app](#2-register-the-app-in-the-google-cloud-console) |
| Desktop OAuth client | No API, no `gcloud` | [2. Register the app](#2-register-the-app-in-the-google-cloud-console) |

Files under `terraform/bootstrap/resources/env/`: `template.env` (committed template),
`.default.env` (the real project id, git-ignored), `terraform-default.tfvars.json` (public settings,
committed).

Used by: [Plan the bootstrap](#plan-the-bootstrap).

### Explanation: what the console steps are for

- **Chat app configuration.** The Chat API refuses every call, even read-only ones made with a
  person's own account, until the project has a Chat app configured. No bot is ever used, so the
  HTTP endpoint is never called; `https://localhost` only satisfies the form.
- **Internal or External.** Internal (only offered when the project belongs to the Workspace
  organization) has no unverified-app warning and no user limit. External in Testing mode works
  for anyone listed as a test user, which is why each teammate must be added.
- **Three scopes, all read-only.** No directory scope is needed: messages and members already carry
  each person's name and email.
- **The desktop OAuth client is manual.** It cannot be created through an API or `gcloud`, which is
  the main reason the bootstrap is not all Terraform.

Used by: [2. Register the app in the Google Cloud console](#2-register-the-app-in-the-google-cloud-console).

### Explanation: the choices behind the Terraform

- **Local state.** One person bootstraps one project once; a remote backend would be a bucket to
  create and remove for two resources. The cost: the state lives on the maintainer's machine, and if
  it is lost the APIs are adopted again with `--import`.
- **Import off by default.** Importing an API that is not enabled fails, so a first bootstrap in a
  fresh project would break if the import blocks were always on.
- **`disable_on_destroy = true`.** The usual house choice for API enablement is `false`, so a
  teardown never disables an API another workload needs. Here the APIs were enabled for this project
  alone and the teardown must leave the project as it was; check the Service Usage audit log before
  relying on it, and switch to `false` if the APIs were already in use.
- **The project id is not in the repository.** It names the organization, so it lives only in
  `.default.env`, and the saved plan (which holds it) is written outside the repository and deleted
  after the apply.

Used by: [Plan the bootstrap](#plan-the-bootstrap).

### Troubleshooting: "Cannot import non-existent remote object"

This issue occurs when `--import` runs against a project where an API is not enabled. To resolve it,
plan without `--import`: Terraform then enables it.

Used by: [Plan the bootstrap](#plan-the-bootstrap).

### Troubleshooting: "Access blocked by your administrator's policy" at sign-in

This issue occurs when the organization blocks OAuth consent for apps it has not approved. To resolve
it, a Workspace administrator has to allow the app (or the maintainer uses an Internal app inside the
organization); no setting in this project works around it.

Used by: [2. Register the app in the Google Cloud console](#2-register-the-app-in-the-google-cloud-console).
