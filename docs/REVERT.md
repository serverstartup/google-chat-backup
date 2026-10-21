# Revert everything

The goal is to leave the project as it was before the backups. There are two parts, because only
one of them has an API.

> Recommended order: **1) everyone finishes their backup → 2) manual revert → 3) `terraform destroy`.**

## 1. APIs — automatic

```bash
cd terraform
terraform destroy
```

With `disable_on_destroy = true` (the default), this **disables** `chat.googleapis.com` and
`people.googleapis.com` in the project.

> ⚠️ **If the project is SHARED** (other teams or workloads use it), disabling an API affects the
> whole project, not just your use. Chat API and People API are very unlikely to be used by
> another workload, but confirm it before destroying.
>
> If you would rather **not touch the APIs** and revert only your own changes, set
> `disable_on_destroy = false` in `terraform.tfvars`, and the revert is just the manual part below.

## 2. What has no API — manual

In the Google Cloud console, with the right project selected:

- **Desktop OAuth client:** `APIs & Services` → `Credentials` → bin icon on the client you created.
- **Consent screen:** remove the test users and the scopes, or leave the app in draft. If it was
  Internal, you can leave it.
- **Chat app configuration** (optional): `Google Chat API` → Configuration; you can clear it.

## 3. Locally (each person)

Delete the credentials and tokens left on disk:

```bash
rm -f scripts/client_secret_*.json scripts/token.json
```

Keep the backup folders (`gchat-backup/<user>/`) or move them wherever the final copy is kept;
they are in `.gitignore` and never go to the repo.
