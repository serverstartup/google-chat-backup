#!/usr/bin/env python3
"""Runs the Google Chat backup on any system with Python 3.9 or newer.

The first run creates scripts/.venv and installs the dependencies; later runs go straight to
scripts/gchat_backup.py. Arguments pass through, for example: python3 backup.py --preview
"""

import shutil
import subprocess
import sys
import venv
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent / "scripts"
VENV = SCRIPTS / ".venv"
VENV_PYTHON = VENV / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")

for _stream in (sys.stdout, sys.stderr):  # a console without UTF-8 must not crash on "…"
    try:
        _stream.reconfigure(errors="replace")
    except (AttributeError, ValueError):
        pass


def fail(fact, hint):
    print(f"Error: {fact}", file=sys.stderr)
    print(f"Hint: {hint}", file=sys.stderr)
    sys.exit(1)


def prepare_environment():
    print("Preparing the Python environment (first run only)…", file=sys.stderr, flush=True)
    try:
        venv.create(VENV, with_pip=True)
        subprocess.run([str(VENV_PYTHON), "-m", "pip", "install", "--quiet", "--disable-pip-version-check",
                        "-r", str(SCRIPTS / "requirements.txt")], check=True)
    except (OSError, subprocess.CalledProcessError) as e:
        shutil.rmtree(VENV, ignore_errors=True)  # never leave a half-built environment behind
        fail(f"Could not prepare the Python environment in {VENV}: {e}",
             "Check your internet connection (on Debian or Ubuntu, install python3-venv) and run the same command again")


def main():
    if sys.version_info < (3, 9):
        fail(f"Python {sys.version.split()[0]} is too old; this needs 3.9 or newer",
             "Install Python 3.9 or newer from https://www.python.org/downloads/ and run it with that")
    if not VENV_PYTHON.exists():
        prepare_environment()
    process = subprocess.Popen([str(VENV_PYTHON), str(SCRIPTS / "gchat_backup.py"), *sys.argv[1:]])
    while True:
        try:
            return process.wait()
        except KeyboardInterrupt:
            continue  # Ctrl-C also reaches the backup, which stops cleanly; wait for its exit code


if __name__ == "__main__":
    sys.exit(main())
