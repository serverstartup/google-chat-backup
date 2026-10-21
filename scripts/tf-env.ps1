# tf-env.ps1 - Minimal wrapper that evaluates tf-env.py output (PowerShell)
# Usage: .\scripts\tf-env.ps1 -e <env>
#   .\scripts\tf-env.ps1 -e au-dev
#   .\scripts\tf-env.ps1 -e au-prod
#
# No dot-sourcing needed: $env: assignments are process-wide, so the
# variables persist in the current PowerShell session after the script ends.
# Counterpart of tf-env.sh for Windows operators.

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

$Lines = & python "$ScriptDir\tf-env.py" @args
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}
Invoke-Expression ($Lines -join "`n")
