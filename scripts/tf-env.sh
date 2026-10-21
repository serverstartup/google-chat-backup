#!/bin/bash
# tf-use.sh - Minimal wrapper that evaluates tf-env.py output
# Usage: source tf-use.sh [args]
#   . tf-use -e dev
#   . tf-use -e prod

# Get script directory (works with both bash and zsh, even when sourced)
if [ -n "${BASH_SOURCE:-}" ]; then
    _TF_SCRIPT_PATH="${BASH_SOURCE[0]}"
elif [ -n "${ZSH_VERSION:-}" ]; then
    _TF_SCRIPT_PATH="${(%):-%x}"
else
    _TF_SCRIPT_PATH="$0"
fi
_TF_SCRIPT_DIR="$(cd "$(dirname "$_TF_SCRIPT_PATH")" && pwd)"

# Capture BEFORE evaluating, and check the exit code.
#
# `eval "$(tf-env.py ...)"` swallows failure: on a non-zero exit the substitution
# is empty, `eval ""` succeeds, and the PREVIOUS workspace's exports survive. You
# see an error, believe you are on the new environment, and TF_WORKSPACE /
# TF_CLI_ARGS_apply still point at the old one. Same shape as the PowerShell
# sibling (tf-env.ps1), which has always checked $LASTEXITCODE.
_TF_OUTPUT="$(python3 "$_TF_SCRIPT_DIR/tf-env.py" "$@")"
_TF_RC=$?

if [ "$_TF_RC" -ne 0 ]; then
    echo "tf-env: activation failed (exit $_TF_RC) — the PREVIOUS environment is still active:" >&2
    echo "        TF_WORKSPACE=${TF_WORKSPACE:-<unset>}" >&2
    unset _TF_SCRIPT_PATH _TF_SCRIPT_DIR _TF_OUTPUT
    # `return` when sourced (the documented usage); `exit` if someone ran it directly.
    return "$_TF_RC" 2>/dev/null || exit "$_TF_RC"
fi

eval "$_TF_OUTPUT"

# Cleanup temp variables
unset _TF_SCRIPT_PATH _TF_SCRIPT_DIR _TF_OUTPUT _TF_RC
