#!/usr/bin/env python3
"""Route a host worktree's commands through its recorded dev container."""

import argparse
import json
import os
import re
from pathlib import Path
import shlex
import subprocess
import sys


class FlowError(Exception):
    pass


def capture(argv, cwd=None):
    return subprocess.run(argv, cwd=cwd, check=True, text=True,
                          stdout=subprocess.PIPE).stdout.strip()


def context(directory):
    root = Path(capture(["git", "-C", str(directory), "rev-parse", "--show-toplevel"])).resolve()
    common = Path(capture(["git", "-C", str(root), "rev-parse",
                           "--path-format=absolute", "--git-common-dir"])).resolve()
    config = next((root / name for name in (".devcontainer/devcontainer.json", ".devcontainer.json")
                   if (root / name).is_file()), None)
    if config is None:
        raise FlowError("No root devcontainer configuration found; configure this task before starting it.")
    return root, common, config, root / ".dev-flow" / "container.json"


def prepare_records(root, common):
    tracked = capture(["git", "-C", str(root), "ls-files", "--", ".dev-flow"])
    if tracked:
        raise FlowError(".dev-flow contains tracked files; choose a separate location before using this helper.")
    ignored = subprocess.run(["git", "-C", str(root), "check-ignore", "-q", "--",
                              ".dev-flow/container.json"])
    if ignored.returncode == 1:
        exclude = common / "info" / "exclude"
        exclude.parent.mkdir(parents=True, exist_ok=True)
        with exclude.open("a") as stream:
            stream.write("\n/.dev-flow/\n")
    elif ignored.returncode != 0:
        raise FlowError("Could not verify Git exclusions for the task records.")


def up_command(root, common, rebuild=False):
    command = ["devcontainer", "up", "--workspace-folder", str(root)]
    if rebuild:
        command.append("--remove-existing-container")
    # Absolute worktree gitdir links need both the common metadata and host path alias.
    for path in dict.fromkeys((root, common)):
        if any(char in str(path) for char in (",", "\n", "\r")):
            raise FlowError("Container bind paths cannot contain commas or newlines.")
        command += ["--mount", f"type=bind,source={path},target={path}"]
    return command


def inspect_record(root, record):
    if record.get("workspace") != str(root):
        raise FlowError("Recorded workspace does not match this checkout.")
    container_id = record.get("container_id")
    if not isinstance(container_id, str) or not container_id or container_id.startswith("-"):
        raise FlowError("Missing or invalid recorded container ID; run flow-container up.")
    info = json.loads(capture(["docker", "inspect", container_id]))
    if len(info) != 1 or not info[0].get("Id", "").startswith(container_id):
        raise FlowError("Docker returned an unexpected container.")
    mounts = info[0].get("Mounts", [])
    if not any(m.get("Type") == "bind" and m.get("RW") is True
               and m.get("Source") == str(root)
               and m.get("Destination") == str(root) for m in mounts):
        raise FlowError("Container does not mount this worktree at its host path; refusing to use it.")
    return info[0]


def read_record(path):
    if not path.is_file():
        raise FlowError("No container recorded for this worktree. Run flow-container up first.")
    record = json.loads(path.read_text())
    if not isinstance(record, dict):
        raise FlowError("Invalid container record; run flow-container up again.")
    return record


def exec_command(root, record, command):
    return ["devcontainer", "exec", "--workspace-folder", str(root),
            "--container-id", record["container_id"], *command]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, default=Path.cwd())
    parser.add_argument("--dry-run", action="store_true")
    sub = parser.add_subparsers(dest="action", required=True)
    sub.add_parser("up", help="Create/start the task container and record its ID")
    sub.add_parser("rebuild", help="Replace the task container, keeping bind-mounted source but discarding container-only files")
    execute = sub.add_parser("exec", help="Execute a command only in the recorded task container")
    execute.add_argument("command", nargs=argparse.REMAINDER)
    sub.add_parser("status", help="Show the recorded container and whether it is running")
    sub.add_parser("stop", help="Stop only the recorded task container; keep its data")
    args = parser.parse_args(argv)
    try:
        root, common, config, record_path = context(args.workspace)
        if args.action in ("up", "rebuild"):
            if re.search(r"\$\{localWorkspaceFolder\}[/\\]\.\.(?:[/\\\"',]|$)", config.read_text()):
                raise FlowError("Devcontainer reaches a sibling checkout. Isolate writable sibling sources before starting.")
            command = up_command(root, common, rebuild=args.action == "rebuild")
            if args.dry_run:
                print(shlex.join(command))
                return 0
            prepare_records(root, common)
            output = capture(command, cwd=root)
            result = None
            for line in reversed(output.splitlines()):
                try:
                    candidate = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(candidate, dict) and candidate.get("outcome") == "success":
                    result = candidate
                    break
            if result is None or not result.get("containerId"):
                raise FlowError("Dev Container CLI did not report a successful container ID.")
            record = {"workspace": str(root), "container_id": result["containerId"],
                      "container_workspace": result.get("remoteWorkspaceFolder"),
                      "container_user": result.get("remoteUser")}
            inspect_record(root, record)
            record_path.parent.mkdir(parents=True, exist_ok=True)
            temporary = record_path.with_suffix(f".{os.getpid()}.tmp")
            try:
                temporary.write_text(json.dumps(record, indent=2) + "\n")
                temporary.replace(record_path)
            finally:
                temporary.unlink(missing_ok=True)
            print(json.dumps(record, indent=2))
            return 0

        record = read_record(record_path)
        info = inspect_record(root, record)
        running = info.get("State", {}).get("Running", False)
        if args.action == "status":
            print(json.dumps({**record, "running": running}, indent=2))
            return 0
        if args.action == "stop":
            command = ["docker", "stop", record["container_id"]]
        else:
            command_args = args.command
            if command_args and command_args[0] == "--":
                command_args = command_args[1:]
            if not command_args:
                raise FlowError("Provide a command, for example: flow-container exec -- just test")
            if not running:
                raise FlowError("The task container is stopped; run flow-container up first.")
            command = exec_command(root, record, command_args)
        if args.dry_run:
            print(shlex.join(command))
            return 0
        return subprocess.run(command, cwd=root).returncode
    except subprocess.CalledProcessError as error:
        print(f"flow-container: {error.cmd[0]} failed (exit {error.returncode}); no host fallback.", file=sys.stderr)
        return error.returncode if error.returncode > 0 else 1
    except (FlowError, OSError, ValueError, TypeError) as error:
        print(f"flow-container: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
