#!/usr/bin/env python3
"""Plans the bootstrap Terraform, classifies the plan and prints the one command that applies it.

    python3 scripts/bootstrap-plan.py             # plan (enable the APIs, or show drift)
    python3 scripts/bootstrap-plan.py --import    # plan that adopts APIs already enabled (imports.tf)
    python3 scripts/bootstrap-plan.py --destroy   # plan the teardown (disables the APIs)

Runs Terraform in terraform/bootstrap/ through scripts/tf-env.py, so the project id comes from
terraform/bootstrap/resources/env/.<env>.env (git-ignored). The plan is saved outside the repository,
because it holds variable values. Nothing is applied: the script prints what the plan imports,
creates, changes and deletes. A normal plan that deletes or replaces anything is refused; a
--destroy plan lists every deletion instead. Then it prints the one command that applies
exactly this plan.
"""

import argparse
import json
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
BOOTSTRAP_DIR = REPO / "terraform" / "bootstrap"
TF_ENV = REPO / "scripts" / "tf-env.py"


def say(line=""):
    print(line, file=sys.stderr, flush=True)


def step(k, m, text):
    say(f"{'' if k == 1 else chr(10)}[{k}/{m}] {text}…")


def fail(fact, hint):
    say(f"Error: {fact}")
    say(f"Hint: {hint}")
    sys.exit(1)


def tf(env, command):
    """Runs a terraform command through tf-env.py in terraform/bootstrap/; stops on failure."""
    result = subprocess.run([sys.executable, str(TF_ENV), "-e", env, "-r", command], cwd=BOOTSTRAP_DIR)
    if result.returncode != 0:
        fail(f"'{command}' exited with code {result.returncode}",
             "Read the Terraform error above; for credentials run gcloud auth application-default login")


def classify(plan_json):
    """Counts per action, the addresses deleted or replaced, and the attributes each update changes."""
    counts, destructive, updates = Counter(), [], []
    for rc in plan_json.get("resource_changes", []):
        change = rc.get("change", {})
        actions = change.get("actions", [])
        if change.get("importing"):
            counts["import"] += 1
        if actions == ["no-op"] or actions == ["read"]:
            continue
        if "delete" in actions and "create" in actions:
            counts["replace"] += 1
            destructive.append(f"{rc['address']} (replace)")
        elif "delete" in actions:
            counts["delete"] += 1
            destructive.append(f"{rc['address']} (delete)")
        elif "create" in actions:
            counts["create"] += 1
        elif "update" in actions:
            counts["update"] += 1
            before, after = change.get("before") or {}, change.get("after") or {}
            changed = sorted(k for k in set(before) | set(after) if before.get(k) != after.get(k))
            updates.append(f"{rc['address']}: {', '.join(changed) or '(computed attributes)'}")
    for change in plan_json.get("output_changes", {}).values():
        if change.get("actions", ["no-op"]) != ["no-op"]:
            counts["output"] += 1  # changes only the values stored in the state, not infrastructure
    return counts, destructive, updates


def apply_command(env, plan_file):
    """One line that works from any folder and leaves the shell where it was."""
    if sys.platform == "win32":
        return (f'Push-Location "{BOOTSTRAP_DIR}"; .\\..\\..\\scripts\\tf-env.ps1 -e {env}; '
                f'terraform apply "{plan_file}"; Pop-Location; Remove-Item "{plan_file}"')
    # a subshell: the cd and the environment stay inside it, so the next command runs where you were
    return (f'(cd "{BOOTSTRAP_DIR}" && . ../../scripts/tf-env.sh -e {env} && '
            f'terraform apply "{plan_file}") && rm -f "{plan_file}"')


def main():
    parser = argparse.ArgumentParser(prog="bootstrap-plan.py", description=__doc__.split("\n")[0])
    parser.add_argument("-e", "--env", default="default", help="tf-env environment (default: default)")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--import", dest="do_import", action="store_true",
                      help="adopt the APIs that are already enabled in the project")
    mode.add_argument("--destroy", action="store_true", help="plan the teardown: disables the APIs")
    args = parser.parse_args()

    if not TF_ENV.exists():
        fail(f"No {TF_ENV}", "Restore it from the repository with git checkout -- scripts/tf-env.py")
    secrets = BOOTSTRAP_DIR / "resources" / "env" / f".{args.env}.env"
    if not secrets.exists():
        fail(f"No {secrets}",
             f"Copy terraform/bootstrap/resources/env/template.env to .{args.env}.env and set the GCP project id")

    plan_file = Path(tempfile.gettempdir()) / "google-chat-backup" / f"{args.env}.tfplan"
    plan_file.parent.mkdir(parents=True, exist_ok=True)
    plan_file.unlink(missing_ok=True)

    step(1, 3, "Initialising Terraform")
    tf(args.env, "terraform init -input=false")
    label = " with imports" if args.do_import else " the teardown" if args.destroy else ""
    step(2, 3, f"Planning{label}")
    extra = " -var=import_existing_apis=true" if args.do_import else " -destroy" if args.destroy else ""
    tf(args.env, f"terraform plan -input=false{extra} -out={plan_file.as_posix()}")
    step(3, 3, "Reading the plan")
    shown = subprocess.run(["terraform", "show", "-json", str(plan_file)], cwd=BOOTSTRAP_DIR,
                           capture_output=True, text=True)
    if shown.returncode != 0:
        fail(f"terraform show could not read {plan_file}", "Run the same command again to make a new plan")
    counts, destructive, updates = classify(json.loads(shown.stdout))
    say("  " + ", ".join(f"{counts[a]} to {a}" for a in ("import", "create", "update", "replace", "delete"))
        + f"; {counts['output']} output value(s) change")
    for line in updates:
        say(f"  ~ {line}")
    for address in destructive:
        say(f"  {'-' if args.destroy else '✗'} {address}")

    if destructive and not args.destroy:
        say(f"\n✗ The plan deletes or replaces {len(destructive)} resource(s); it is not applied")
        say("Hint: Find the change that intends each one before applying anything")
        plan_file.unlink(missing_ok=True)
        return 1
    if not any(counts[a] for a in ("import", "create", "update", "output", "delete")):
        say("\n✓ No changes: nothing to apply")
        plan_file.unlink(missing_ok=True)
        return 0

    say("\n✓ Plan saved. Apply exactly this plan (and delete it) with this one command:")
    print(apply_command(args.env, plan_file))
    say("Hint: Run it as one line; if the project changes in between, Terraform refuses the stale plan")
    return 0


if __name__ == "__main__":
    sys.exit(main())
