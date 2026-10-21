#!/bin/sh
# Runs the Google Chat backup. The first run creates scripts/.venv with the system python3
# and installs the dependencies; later runs go straight to the script. Arguments pass through
# (for example: ./backup.sh --preview).
set -e
cd "$(dirname "$0")/scripts"

if [ ! -x .venv/bin/python ]; then
  echo "Preparing the Python environment (first run only)…" >&2
  if ! python3 -m venv .venv || ! .venv/bin/pip install --quiet --disable-pip-version-check -r requirements.txt; then
    rm -rf .venv
    echo "Error: Could not prepare the Python environment" >&2
    echo "Hint: Install Apple's command line tools with xcode-select --install, then run ./backup.sh again" >&2
    exit 1
  fi
fi

exec .venv/bin/python gchat_backup.py "$@"
