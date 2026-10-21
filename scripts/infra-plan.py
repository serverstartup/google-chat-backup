#!/usr/bin/env python3
"""Plans the Terraform in terraform/, classifies the plan and prints the command that applies it.

    python3 scripts/infra-plan.py            # plan
    python3 scripts/infra-plan.py --import   # plan that also adopts APIs already enabled (imports.tf)

Runs Terraform through scripts/tf-env.py, so the project id comes from
terraform/resources/env/.<env>.env (git-ignored). The plan is saved outside the repository,
because it holds variable values. Nothing is applied: the script prints what the plan imports,
creates, changes and deletes, refuses if it deletes or replaces anything, and otherwise prints
the command that applies exactly this plan.
"""

import argparse
import json
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
TERRAFORM_DIR = REPO / "terraform"
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
    """Runs a terraform command through tf-env.py in terraform/; stops on failure."""
    result = subprocess.run([sys.executable, str(TF_ENV), "-e", env, "-r", command], cwd=TERRAFORM_DIR)
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


def main():
    parser = argparse.ArgumentParser(prog="infra-plan.py", description=__doc__.split("\n")[0])
    parser.add_argument("-e", "--env", default="default", help="tf-env environment (default: default)")
    parser.add_argument("--import", dest="do_import", action="store_true",
                        help="adopt the APIs that are already enabled in the project")
    args = parser.parse_args()

    if not TF_ENV.exists():
        fail(f"No {TF_ENV}", "Restore scripts/tf-env.py from the repository with git checkout -- scripts/tf-env.py")
    secrets = TERRAFORM_DIR / "resources" / "env" / f".{args.env}.env"
    if not secrets.exists():
        fail(f"No {secrets}",
             f"Copy terraform/resources/env/template.env to .{args.env}.env and set the GCP project id")

    plan_file = Path(tempfile.gettempdir()) / "google-chat-backup" / f"{args.env}.tfplan"
    plan_file.parent.mkdir(parents=True, exist_ok=True)

    step(1, 3, "Initialising Terraform")
    tf(args.env, "terraform init -input=false")
    step(2, 3, "Planning" + (" with imports" if args.do_import else ""))
    extra = " -var=import_existing_apis=true" if args.do_import else ""
    tf(args.env, f"terraform plan -input=false{extra} -out={plan_file.as_posix()}")
    step(3, 3, "Reading the plan")
    shown = subprocess.run(["terraform", "show", "-json", str(plan_file)], cwd=TERRAFORM_DIR,
                           capture_output=True, text=True)
    if shown.returncode != 0:
        fail(f"terraform show could not read {plan_file}", "Run the same command again to make a new plan")
    counts, destructive, updates = classify(json.loads(shown.stdout))
    say("  " + ", ".join(f"{counts[a]} to {a}" for a in ("import", "create", "update", "replace", "delete"))
        + f"; {counts['output']} output value(s) change")
    for line in updates:
        say(f"  ~ {line}")

    if destructive:
        for address in destructive:
            say(f"  ✗ {address}")
        say(f"\n✗ The plan deletes or replaces {len(destructive)} resource(s); it is not applied")
        say("Hint: Find the change that intends each one before applying anything")
        plan_file.unlink(missing_ok=True)
        return 1
    if not any(counts[a] for a in ("import", "create", "update", "output")):
        say("\n✓ No changes: the infrastructure matches the configuration")
        plan_file.unlink(missing_ok=True)
        return 0

    say(f"\n✓ Plan saved to {plan_file}; apply exactly this plan with:")
    print(f"cd {TERRAFORM_DIR}")
    if sys.platform == "win32":
        print(f".\\..\\scripts\\tf-env.ps1 -e {args.env}")
    else:
        print(f". ../scripts/tf-env.sh -e {args.env}")
    print(f'terraform apply "{plan_file}"')
    say("Hint: Delete the plan file afterwards; it holds the project id")
    return 0


if __name__ == "__main__":
    sys.exit(main())
