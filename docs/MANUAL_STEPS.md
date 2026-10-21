# Manual steps (no API)

These three steps have **no API and no `gcloud` or Terraform support**. Do them once, by hand,
in the Google Cloud console, with the right project selected in the picker at the top.

> Prerequisite: `terraform/` applied (APIs enabled).

## 1. Chat app configuration

`APIs & Services` → `Google Chat API` → **Configuration** tab.

- **App name:** anything (for example `Chat Backup`).
- **Description:** required, any text.
- **HTTP endpoint URL:** `https://localhost` (never used; the form just requires one).
- No need to tick "Join spaces", "App Home", commands or visibility: there is no bot here, only
  reads with each person's own account.

Save. Without this step the API returns an error even though it is enabled.

## 2. OAuth consent screen

`APIs & Services` → **OAuth consent screen** (in the newer console: *Google Auth Platform*).

- **User type:**
  - If the project belongs to the Workspace organization and you can pick **Internal**, that is
    the simplest option (no unverified-app warning, no user limit).
  - Otherwise, **External** in **Testing** mode, and add under *Audience* → *Test users* every
    account that will run the backup.
- **Scopes:** add exactly these three (read-only):
  ```
  https://www.googleapis.com/auth/chat.spaces.readonly
  https://www.googleapis.com/auth/chat.messages.readonly
  https://www.googleapis.com/auth/chat.memberships.readonly
  ```
  No directory scope is needed: messages and members already carry each person's name and email.

## 3. Desktop OAuth client

`APIs & Services` → `Credentials` → **Create credentials** → **OAuth client ID** → type
**Desktop app**.

- Create it and **download the JSON**.
- Save it in the repo's `scripts/` folder under its original name
  (`client_secret_...apps.googleusercontent.com.json`). `.gitignore` already excludes it.

> This client type **cannot be created through an API or `gcloud`**: it is manual by necessity,
> and the main reason this step is not in Terraform.

## Check

From `scripts/`, with `GCHAT_DRY_RUN=true`, the script must list your spaces. If the login shows
"Access blocked by your administrator's policy", the organization blocks OAuth consent for
unapproved apps and this route does not work for that account.
