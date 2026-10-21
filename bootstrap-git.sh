#!/usr/bin/env bash
# Leaves the repo with its initial commit, aborting if anything that looks like
# a credential is about to enter git.
set -euo pipefail
cd "$(dirname "$0")"

if [ -d .git ]; then
  echo "There is already a git repository here. Nothing to do."
  exit 0
fi

git init -q

# Quality gate: enables the versioned pre-commit hook in .githooks/
git config core.hooksPath .githooks
chmod +x .githooks/pre-commit 2>/dev/null || true

# local denylist (terms to block). Not pushed (.gitignore).
if [ ! -f denylist.txt ]; then
  cp denylist.example.txt denylist.txt
  echo ">> Created denylist.txt from the example. Edit it with the terms to block"
  echo ">> (client name, real project_id) BEFORE making serious commits."
fi

git add -A

# Safety net: no secrets or state in the stage.
if git ls-files --cached | grep -E 'client_secret|token\.json|\.tfvars$|\.tfstate'; then
  echo "!! There are credentials or Terraform state in the stage. Aborting without committing."
  echo "   Check the .gitignore and try again."
  exit 1
fi

echo "=== Files in the initial commit ==="
git status --short

git commit -q -F - <<'MSG'
google-chat-backup: home-made Google Chat backup, reversible through Terraform

- Terraform enables the Chat API and People API (disable_on_destroy=true, reversible)
- scripts/gchat_backup.py: per-user exporter (user OAuth, no admin)
- docs/: manual steps (no API) and revert guide
- 0 credentials in the repo (.gitignore)

MSG

echo
echo "Initial commit created. Review it with: git log --stat"
echo "When you have the remote: git remote add origin <url> && git push -u origin main"
