#!/usr/bin/env python3
import argparse
import json
import os
import shlex
import subprocess
import sys
from pathlib import Path


def find_resources_dir(start_dir):
    """Walk up from start_dir looking for resources/env/ directory."""
    current = start_dir.resolve()
    while current != current.parent:
        candidate = current / "resources" / "env"
        if candidate.is_dir():
            return current
        current = current.parent
    return None


def get_workspace_vars(workspace, base_dir):
    """Reads the JSON variable file for the target workspace."""
    var_file = base_dir / "resources" / "env" / f"terraform-{workspace}.tfvars.json"

    if not var_file.exists():
        print(f"Error: Environment file not found: {var_file}", file=sys.stderr)
        env_dir = base_dir / "resources" / "env"
        if env_dir.exists():
            # `.stem` strips ONE suffix, so `terraform-prd.tfvars.json` would give
            # `terraform-prd.tfvars` and the hint would name an environment `-e` rejects.
            available = [
                f.name.removeprefix("terraform-").removesuffix(".tfvars.json")
                for f in env_dir.glob("terraform-*.tfvars.json")
            ]
            if available:
                print(f"Available environments: {', '.join(sorted(available))}", file=sys.stderr)
        sys.exit(1)

    with open(var_file, "r") as f:
        try:
            return json.load(f), var_file
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON in {var_file}: {e}", file=sys.stderr)
            sys.exit(1)


def load_dotenv(workspace, base_dir):
    """Load secrets from resources/env/.{workspace}.env (dual-file convention).

    Lines are KEY=VALUE pairs. Comments (#) and blank lines are skipped.
    Values are NOT shell-expanded -- raw assignment only.

    A committed template.env is the signal that the project expects secrets;
    without it, a missing .{workspace}.env is a valid no-secrets setup
    (e.g. gcloud user login + service account impersonation) and no warning
    is emitted.
    """
    env_dir = base_dir / "resources" / "env"
    dotenv_file = env_dir / f".{workspace}.env"
    env_vars = {}
    if not dotenv_file.exists():
        if (env_dir / "template.env").exists():
            print(f"Warning: secrets file not found: {dotenv_file}", file=sys.stderr)
            print(
                f"  Create it from template: cp resources/env/template.env resources/env/.{workspace}.env",
                file=sys.stderr,
            )
        return env_vars
    with open(dotenv_file, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, _, value = line.partition("=")
                env_vars[key.strip()] = value.strip()
    return env_vars


# Terraform variables that steer WHERE a run applies and WITH WHAT.
#
# TF_CLI_ARGS is the sharp one: Terraform prepends it to EVERY subcommand.
# Measured against Terraform v1.16.3 -- `TF_CLI_ARGS=-made-up-flag terraform
# fmt -check` makes fmt reject its own arguments, so a value inherited from
# another project's activation reaches this project's plan and apply. The
# legacy setenv.sh cleared it with a bare `export TF_CLI_ARGS=`; nothing
# replaced that when the toolchain took over, and `-r` mode copies os.environ,
# so it leaks there too.
#
# TF_WORKSPACE is absent on purpose: generate_env_vars always defines it, so it
# can never be inherited-and-undefined and a guard for it would never fire.
#
# Also absent, on purpose: TF_LOG*, TF_INPUT, TF_IN_AUTOMATION,
# TF_PLUGIN_CACHE_DIR, TF_CLI_CONFIG_FILE, TF_REGISTRY_*. Those change how a run
# reports or where it caches, never what it touches -- an operator who exported
# TF_LOG=DEBUG for this run means it.
STEERING_VARS = ("TF_CLI_ARGS", "TF_DATA_DIR")
STEERING_PREFIXES = ("TF_CLI_ARGS_", "TF_VAR_")


def find_inherited_steering_vars(env_vars, environ=None):
    """Steering TF_* variables in the environment that this project does not define.

    Sorted, so the report and the emitted `unset` lines are stable.
    """
    environ = os.environ if environ is None else environ
    return sorted(
        name
        for name in environ
        if name not in env_vars and (name in STEERING_VARS or name.startswith(STEERING_PREFIXES))
    )


def is_init(command):
    """True when `command` invokes `terraform init`.

    `terraform init` is the one Terraform command that is workspace-independent:
    it configures the backend and installs providers, and never reads or writes
    workspace state. It is also the one command that REFUSES to run when
    TF_WORKSPACE names a workspace the backend does not have yet:

        Error: Currently selected workspace "uat" does not exist

    Measured against a GCS backend: that refusal only happens on a RE-init, i.e.
    once `.terraform/` exists. The first environment applied from a directory
    therefore works and the second one fails, which reads like a broken runbook
    rather than a missing workspace. Every other command — plan included —
    creates the workspace on demand.

    So the wrapper drops TF_WORKSPACE for init, and the first plan creates it.
    """
    tokens = shlex.split(command)
    for token in tokens[1:]:
        if token.startswith("-"):  # e.g. -chdir=secret-manager
            continue
        return token == "init"
    return False


def generate_env_vars(workspace, vars_data, var_file_path, base_dir):
    """Generates the environment variables needed for Terraform."""

    env_vars = {}

    # 0. Load secrets from .{workspace}.env (dual-file convention)
    env_vars.update(load_dotenv(workspace, base_dir))

    # 1. Base Variables
    env_vars["TF_WORKSPACE"] = workspace
    env_vars["X_TF_CLI_ARGS_VAR_FILE"] = str(var_file_path.absolute())

    # Extract values based on previous setenv.sh mappings
    env_vars["project_id"] = vars_data.get("project_id", "")

    project_ids = vars_data.get("project_ids", {})
    env_vars["project_admin_id"] = project_ids.get("admin", "")
    env_vars["project_staging_id"] = project_ids.get("staging", "")
    env_vars["project_bronze_id"] = project_ids.get("bronze", "")
    env_vars["project_silver_id"] = project_ids.get("silver", "")
    env_vars["project_gold_id"] = project_ids.get("gold", "")
    env_vars["project_valiuz_id"] = project_ids.get("valiuz", "")

    env_vars["bucket_name"] = vars_data.get(
        "backend_bucket", vars_data.get("buckets", {}).get("backend", {}).get("name", "")
    )
    env_vars["location"] = vars_data.get("location", "")

    # 2. Terraform CLI Injections
    #
    # POSIX separators, deliberately, including on Windows. Terraform splits
    # TF_CLI_ARGS_* with a shell-style word parser that treats `\` as an escape
    # character, so a native Windows path arrives stripped of every separator:
    #   -var-file=C:\repo\resources\env\terraform-<env>.tfvars.json
    #     -> "Given variables file C:reporesourcesenvterraform-<env>.tfvars.json
    #         does not exist."
    # Forward slashes survive that parser and Windows accepts them in paths.
    # (The legacy resources/scripts/windows/setenv.ps1 hid this by building the
    # path with doubled backslashes, which the parser halved back to one.)
    tf_args_template = f"-var-file={var_file_path.absolute().as_posix()}"

    env_vars["TF_CLI_ARGS_plan"] = tf_args_template
    env_vars["TF_CLI_ARGS_apply"] = tf_args_template
    env_vars["TF_CLI_ARGS_destroy"] = tf_args_template
    env_vars["TF_CLI_ARGS_import"] = tf_args_template
    if env_vars["bucket_name"]:
        env_vars["TF_CLI_ARGS_init"] = f"-backend-config=bucket={env_vars['bucket_name']}"

    # 3. Handle IDE Support Hack (definitions.bak.tf)
    env_dir = base_dir / "resources" / "env"
    env_dir.mkdir(parents=True, exist_ok=True)

    def_bak_file = env_dir / "definitions.bak.tf"
    variables_tf_file = base_dir / "variables.tf"

    env_vars["X_TF_DEF_VAR_FILE"] = str(def_bak_file.absolute())

    if variables_tf_file.exists():
        with open(def_bak_file, "w") as out_f:
            import datetime

            out_f.write("/*\n * Do NOT edit this file. Changes will be ignored.\n")
            out_f.write(
                f" * This file is just a copy of 'variables.tf' at root directory"
                f" made at '{datetime.datetime.now()}'.\n"
            )
            out_f.write(
                " * It is intended for integrated IDE support for validating '.X_TF_CLI_ARGS_VAR_FILE' files.\n */\n\n"
            )
            with open(variables_tf_file, "r") as in_f:
                out_f.write(in_f.read())

    return env_vars


def main():
    parser = argparse.ArgumentParser(
        description="Terraform Environment Setup Tool",
        epilog="Examples:\n"
        "  tf-env -e dev              # Export env vars for dev\n"
        "  tf-env -e dev -r 'tf plan' # Run terraform plan in dev context\n",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("-e", "--env", default="dev", help="Target environment workspace (default: dev)")
    parser.add_argument(
        "-b",
        "-d",
        "--base-dir",
        default=None,
        help="Root directory containing resources/env/. Auto-detected by walking up from cwd if not specified.",
    )
    parser.add_argument(
        "-r", "--run", type=str, default=None, help="Run a command within the configured environment context"
    )

    args = parser.parse_args()

    # Auto-detect base_dir if not specified
    if args.base_dir:
        base_dir = Path(args.base_dir).resolve()
    else:
        base_dir = find_resources_dir(Path.cwd())
        if base_dir is None:
            print("Error: Could not find resources/env/ directory.", file=sys.stderr)
            print("Searched upward from: " + str(Path.cwd()), file=sys.stderr)
            print("Use --base-dir to specify explicitly.", file=sys.stderr)
            sys.exit(1)

    vars_data, var_file_path = get_workspace_vars(args.env, base_dir)
    env_vars = generate_env_vars(args.env, vars_data, var_file_path, base_dir)

    # Reported on stderr: stdout is eval'd by tf-env.sh / Invoke-Expression'd by
    # tf-env.ps1, so anything informational printed there would be executed.
    inherited = find_inherited_steering_vars(env_vars)
    if inherited:
        print(
            "Dropping inherited Terraform variables this project does not define: " + ", ".join(inherited),
            file=sys.stderr,
        )

    if args.run:
        # --run mode: execute command with env vars injected
        run_env = os.environ.copy()
        for name in inherited:
            run_env.pop(name, None)
        run_env.update(env_vars)

        if is_init(args.run):
            run_env.pop("TF_WORKSPACE", None)
            print(f"Running: {args.run} (init is workspace-independent; TF_WORKSPACE '{args.env}' not passed)")
        else:
            print(f"Running: {args.run} in workspace '{args.env}'")
        try:
            subprocess.run(args.run, shell=True, check=True, env=run_env)
        except subprocess.CalledProcessError as e:
            print(f"Command failed with exit code {e.returncode}", file=sys.stderr)
            sys.exit(e.returncode)
    else:
        # Default: export mode (print statements for eval by tf-env.sh / tf-env.ps1)
        if sys.platform == "win32":
            for name in inherited:
                print(f"Remove-Item Env:\\{name} -ErrorAction SilentlyContinue")
            for k, v in env_vars.items():
                escaped_v = str(v).replace("'", "''")
                print(f"$env:{k} = '{escaped_v}'")
            print(f"Write-Host \"Workspace '{args.env}' environment variables loaded.\"")
        else:
            for name in inherited:
                print(f"unset {name};")
            for k, v in env_vars.items():
                escaped_v = str(v).replace("'", "'\\''")
                print(f"export {k}='{escaped_v}';")
            print(f"echo \"Workspace '{args.env}' environment variables loaded.\";")


if __name__ == "__main__":
    main()
