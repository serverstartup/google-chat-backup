#!/usr/bin/env bash
# Deja el repo con su commit inicial, abortando si algo que parezca
# credencial está a punto de entrar en git.
set -euo pipefail
cd "$(dirname "$0")"

if [ -d .git ]; then
  echo "Ya hay un repositorio git aquí. Nada que hacer."
  exit 0
fi

git init -q

# Quality gate: activa el hook de pre-commit versionado en .githooks/
git config core.hooksPath .githooks
chmod +x .githooks/pre-commit 2>/dev/null || true

# denylist local (términos a bloquear). No se sube (.gitignore).
if [ ! -f denylist.txt ]; then
  cp denylist.example.txt denylist.txt
  echo ">> Creado denylist.txt desde el ejemplo. Edítalo con los términos a bloquear"
  echo ">> (nombre de cliente, project_id real) ANTES de hacer commits serios."
fi

git add -A

# Red de seguridad: nada de secretos ni estado en el stage.
if git ls-files --cached | grep -E 'client_secret|token\.json|\.tfvars$|\.tfstate'; then
  echo "!! Hay credenciales o estado de Terraform en el stage. Abortando sin commitear."
  echo "   Revisa el .gitignore y vuelve a intentarlo."
  exit 1
fi

echo "=== Ficheros en el commit inicial ==="
git status --short

git commit -q -F - <<'MSG'
google-chat-backup: backup casero de Google Chat con reversión por Terraform

- Terraform habilita Chat API y People API (disable_on_destroy=true, reversible)
- scripts/gchat_backup.py: exportador por usuario (OAuth de usuario, sin admin)
- docs/: pasos manuales (sin API) y guía de reversión
- 0 credenciales en el repo (.gitignore)

MSG

echo
echo "Commit inicial creado. Revisa con: git log --stat"
echo "Cuando tengas el remoto: git remote add origin <url> && git push -u origin main"
