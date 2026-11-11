#!/usr/bin/env python3
"""Create local editor workspaces without changing application repositories."""

import argparse
import json
from pathlib import Path
import re
import subprocess
import sys


DEFAULT_DIRECTORY = Path(__file__).resolve().parents[1] / "workspaces"
HELPER = Path(__file__).resolve().with_name("flow_container.py")


def repository_root(directory):
    result = subprocess.run(
        ["git", "-C", str(directory), "rev-parse", "--show-toplevel"],
        check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return Path(result.stdout.strip()).resolve()


def workspace_config(root):
    variable = "${workspaceFolder:project}"
    tasks = []
    for label, action in (
        ("Flow: Start container", "up"),
        ("Flow: Container status", "status"),
        ("Flow: Rebuild container (replaces container)", "rebuild"),
        ("Flow: Stop container", "stop"),
    ):
        task = {
            "label": label,
            "type": "shell",
            "command": str(HELPER),
            "args": ["--workspace", variable, action],
            "problemMatcher": [],
        }
        if action == "rebuild":
            task["detail"] = ("Replaces this workspace's container. Bind-mounted source stays intact; "
                              "container-only files are discarded.")
        tasks.append(task)
    return {
        "folders": [{"name": "project", "path": str(root)}],
        "tasks": {
            "version": "2.0.0",
            "options": {"cwd": variable, "shell": {"executable": "/bin/zsh", "args": ["-l", "-c"]}},
            "presentation": {"reveal": "always", "panel": "dedicated", "clear": True},
            "tasks": tasks,
        },
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repository", nargs="?", type=Path, default=Path.cwd())
    parser.add_argument("--name", help="Workspace filename without the .code-workspace suffix")
    parser.add_argument("--directory", type=Path, default=DEFAULT_DIRECTORY,
                        help="Where to save local workspace files")
    args = parser.parse_args(argv)
    try:
        root = repository_root(args.repository.expanduser())
        if not any((root / name).is_file() for name in
                   (".devcontainer/devcontainer.json", ".devcontainer.json")):
            raise ValueError("This helper needs a root devcontainer configuration; none was found.")
        name = args.name or root.name
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", name):
            raise ValueError("Use --name with letters, numbers, dots, underscores, or hyphens.")
        destination = args.directory.expanduser().resolve() / f"{name}.code-workspace"
        destination.parent.mkdir(parents=True, exist_ok=True)
        # Exclusive creation preserves user edits and refuses ambiguous name reuse.
        with destination.open("x") as stream:
            json.dump(workspace_config(root), stream, indent=2)
            stream.write("\n")
        print(destination)
        return 0
    except FileExistsError:
        print("flow-workspace: Workspace already exists; open it, or choose another --name. "
              "No file was overwritten.", file=sys.stderr)
    except subprocess.CalledProcessError:
        print("flow-workspace: Could not find the Git repository. Pass an existing checkout or worktree.",
              file=sys.stderr)
    except (OSError, ValueError) as error:
        print(f"flow-workspace: {error}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
