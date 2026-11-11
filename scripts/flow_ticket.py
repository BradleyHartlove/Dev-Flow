#!/usr/bin/env python3
"""Manage local ticket worktrees, editor workspaces, and development containers."""

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import filecmp
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parent))
import flow_workspace


DEFAULT_HOME = Path(__file__).resolve().parents[1] / "tickets"
CONTAINER_HELPER = Path(__file__).resolve().with_name("flow_container.py")
SELF = Path(__file__).resolve()


class TicketError(Exception):
    pass


def now():
    return datetime.now(timezone.utc).isoformat()


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], check=True,
                          text=True, stdout=subprocess.PIPE).stdout.strip()


def valid_name(value):
    if (not re.fullmatch(r"[a-z0-9][a-z0-9._-]{0,63}", value)
            or ".." in value or value.endswith((".", ".lock"))):
        raise TicketError("Use a ticket name of 1–64 lowercase letters, numbers, dots, underscores or hyphens.")
    return value


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temporary.open("x") as stream:
            os.chmod(temporary, 0o600)
            json.dump(value, stream, indent=2)
            stream.write("\n")
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def read_json(path):
    if path.is_symlink():
        raise TicketError(f"Refusing symlinked manager file: {path}")
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise TicketError(f"Expected a JSON object in {path}")
    return value


def worktrees(repo):
    output = subprocess.run(["git", "-C", str(repo), "worktree", "list", "--porcelain", "-z"],
                            check=True, stdout=subprocess.PIPE).stdout.decode()
    result, current = [], {}
    for entry in output.split("\0"):
        if not entry:
            if current:
                result.append(current)
                current = {}
        else:
            key, _, value = entry.partition(" ")
            current[key] = value
    return result


def managed_paths(directory, *paths):
    for path in paths:
        try:
            parts = path.relative_to(directory).parts
        except ValueError:
            raise TicketError("Manager path is outside its repository directory.")
        current = directory
        for part in parts:
            current = current / part
            if current.is_symlink():
                raise TicketError(f"Managed paths must not be symlinks: {current}")


def identity(repo, home):
    root = flow_workspace.repository_root(repo.expanduser())
    common = Path(git(root, "rev-parse", "--path-format=absolute", "--git-common-dir")).resolve()
    primary = Path(worktrees(root)[0]["worktree"]).resolve()
    slug = re.sub(r"[^a-zA-Z0-9._-]+", "-", primary.name)
    key = f"{slug}-{hashlib.sha256(str(common).encode()).hexdigest()[:10]}"
    directory = home.expanduser().resolve() / key
    return primary, common, directory


@contextmanager
def locked(directory):
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    if directory.is_symlink():
        raise TicketError("The manager directory must not be a symlink.")
    with (directory / ".lock").open("a") as stream:
        try:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise TicketError("Another ticket lifecycle action is running for this repo. Retry after it finishes.")
        try:
            yield
        finally:
            fcntl.flock(stream, fcntl.LOCK_UN)


def check_config(root):
    configs = [root / ".devcontainer/devcontainer.json", root / ".devcontainer.json"]
    config = next((p for p in configs if p.is_file()), None)
    if config is None:
        raise TicketError("A root .devcontainer/devcontainer.json or .devcontainer.json is required.")
    if re.search(r"\$\{localWorkspaceFolder\}[/\\]\.\.(?:[/\\\"',]|$)", config.read_text()):
        raise TicketError("This configuration reaches a sibling checkout. Configure task-specific sibling isolation before using tickets here.")


def default_base(repo):
    candidate = subprocess.run(["git", "-C", str(repo), "symbolic-ref", "--quiet",
                                "--short", "refs/remotes/origin/HEAD"],
                               text=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    choices = [candidate.stdout.strip(), "origin/main", "origin/master", "main", "master"]
    for ref in filter(None, choices):
        result = subprocess.run(["git", "-C", str(repo), "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}"],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if result.returncode == 0:
            return ref
    raise TicketError("Cannot determine a main branch; supply --base during setup or start.")


def base_commit(repo, base, fetch):
    if not base or base.startswith("-"):
        raise TicketError("Invalid base revision.")
    # Fetch a remote-tracking base when starting a new ticket; never pull/reset another checkout.
    for remote in git(repo, "remote").splitlines():
        if base.startswith(remote + "/") or base.startswith("refs/remotes/" + remote + "/"):
            if fetch:
                subprocess.run(["git", "-C", str(repo), "fetch", remote], check=True)
            if base.startswith(remote + "/"):
                base = "refs/remotes/" + base
            break
    return git(repo, "rev-parse", "--verify", "--end-of-options", f"{base}^{{commit}}")


def task_config(root, directory, ticket=None):
    config = flow_workspace.workspace_config(root)
    arguments = ["--repo", str(read_json(directory / "repo.json")["repo"]),
                 "--home", str(directory.parent)]
    def task(label, action, name=None, open_editor=False):
        args = [*arguments, action]
        if name is not None:
            args.append(name)
        if open_editor:
            args.append("--open")
        return {"label": label, "type": "shell", "command": str(SELF),
                "args": args, "problemMatcher": []}
    choices = [task("Ticket: Start", "start", "${input:ticketName}", True),
               task("Ticket: Resume", "resume", ticket or "${input:ticketName}", True),
               task("Ticket: Finish", "finish", ticket or "${input:ticketName}", True),
               task("Ticket: List", "list")]
    for entry in choices:
        entry["options"] = {"cwd": arguments[1], "shell": {"executable": "/bin/zsh", "args": ["-l", "-c"]}}
    # The permanent repo workspace is a control panel, not a second task container.
    config["tasks"]["tasks"] = choices + (config["tasks"]["tasks"] if ticket else [])
    for entry in config["tasks"]["tasks"]:
        entry["command"] = {"value": entry["command"], "quoting": "strong"}
        entry["args"] = [{"value": value, "quoting": "strong"} for value in entry["args"]]
    config["tasks"]["inputs"] = [{"id": "ticketName", "type": "promptString",
                                  "description": "Ticket name (lowercase, e.g. media-t5)"}]
    return config


def ensure_workspace(path, config):
    if path.exists() or path.is_symlink():
        old = read_json(path)
        if old.get("folders") != config["folders"]:
            raise TicketError(f"Existing workspace points elsewhere; left unchanged: {path}")
        return
    write_json(path, config)


def setup(repo, common, directory, base=None):
    path = directory / "repo.json"
    if path.exists():
        profile = read_json(path)
        if profile.get("repo") != str(repo) or profile.get("common") != str(common):
            raise TicketError("Repository identity does not match its saved profile.")
        if base is not None:
            base_commit(repo, base, fetch=False)
            profile["base"] = base
            write_json(path, profile)
    else:
        check_config(repo)
        profile = {"schema": 1, "repo": str(repo), "common": str(common),
                   "base": base or default_base(repo)}
        base_commit(repo, profile["base"], fetch=False)
        write_json(path, profile)
    ensure_workspace(directory / "repo.code-workspace", task_config(repo, directory))
    return profile


def paths(directory, name):
    valid_name(name)
    record = directory / "records" / name
    result = record / "state.json", directory / "worktrees" / name, record / "ticket.code-workspace"
    managed_paths(directory, *result)
    return result


def load_ticket(directory, profile, name):
    state_path, root, workspace = paths(directory, name)
    if not state_path.exists():
        raise TicketError(f"Unknown ticket {name}; use start first.")
    state = read_json(state_path)
    expected = {"schema": 1, "ticket": name, "repo": profile["repo"],
                "common": profile["common"], "worktree": str(root),
                "workspace": str(workspace), "branch": f"flow/{name}"}
    if any(state.get(k) != v for k, v in expected.items()):
        raise TicketError("Ticket identity/path mismatch; refusing to change anything.")
    if root.is_symlink() or root.parent.is_symlink() or state_path.parent.is_symlink():
        raise TicketError("Managed checkout/record paths must not be symlinks.")
    return state_path, state


def save_state(path, state, stage=None):
    if stage:
        state["stage"] = stage
    state["updated_at"] = now()
    write_json(path, state)


def workflow_status(state_path, state):
    path = state_path.parent / "pipeline" / "STATUS.json"
    if not path.exists():
        return {"stage": "not-started"}
    workflow = read_json(path)
    if workflow.get("workspace") != state["worktree"]:
        raise TicketError("Pipeline record belongs to another checkout.")
    return {"stage": "complete" if state.get("stage") == "finished" else workflow["stage"],
            "summary": workflow.get("summary", ""),
            "record_directory": str(path.parent), "updated_at": workflow.get("updated_at")}


def verify_checkout(state):
    root = Path(state["worktree"])
    if root.is_symlink():
        raise TicketError("Refusing a symlinked checkout.")
    if Path(git(root, "rev-parse", "--show-toplevel")).resolve() != root:
        raise TicketError("Checkout root changed; refusing to use it.")
    common = git(root, "rev-parse", "--path-format=absolute", "--git-common-dir")
    branch = git(root, "symbolic-ref", "--quiet", "--short", "HEAD")
    if Path(common).resolve() != Path(state["common"]) or branch != state["branch"]:
        raise TicketError("Checkout repository or branch changed; refusing lifecycle actions.")
    registered = any(item.get("worktree") == str(root)
                     and item.get("branch") == "refs/heads/" + state["branch"]
                     for item in worktrees(state["repo"]))
    if not registered:
        raise TicketError("Checkout is not registered as this ticket's worktree.")


def container(root, action):
    subprocess.run([sys.executable, str(CONTAINER_HELPER), "--workspace", str(root), action], check=True)


def ignored_files(root):
    result = subprocess.run(["git", "-C", str(root), "ls-files", "--others", "--ignored",
                             "--exclude-standard", "-z"], check=True, stdout=subprocess.PIPE)
    return [Path(p) for p in result.stdout.decode().split("\0") if p]


def local_path(root, relative):
    if not relative.parts or relative.is_absolute() or ".." in relative.parts or relative.parts[0] == ".git":
        raise TicketError("Archive contains an invalid path.")
    if root.is_symlink():
        raise TicketError("Archive/check-out root must not be a symlink.")
    target = root / relative
    parent = target.parent
    while parent != root:
        if parent.is_symlink():
            raise TicketError(f"Refusing to write through a symlink: {parent}")
        parent = parent.parent
    return target


def copy_file(source, destination):
    destination.parent.mkdir(parents=True, exist_ok=True)
    if source.is_symlink():
        destination.symlink_to(os.readlink(source))
    elif source.is_file():
        shutil.copy2(source, destination, follow_symlinks=False)
    else:
        raise TicketError(f"Cannot preserve non-file artifact: {source}")


def same_file(left, right):
    if left.is_symlink() or right.is_symlink():
        return left.is_symlink() and right.is_symlink() and os.readlink(left) == os.readlink(right)
    return left.is_file() and right.is_file() and filecmp.cmp(left, right, shallow=False)


def archive_files(root, snapshot):
    files = ignored_files(root)
    manifest = []
    for relative in files:
        source = local_path(root, relative)
        target = local_path(snapshot / "ignored", relative)
        copy_file(source, target)
        manifest.append(str(relative))
    write_json(snapshot / "ignored.json", {"files": manifest})
    return files


def verify_archive(root, snapshot, files):
    if set(files) != set(ignored_files(root)):
        raise TicketError("Ignored files changed during archival; checkout retained. Pause writers and retry.")
    for relative in files:
        if not same_file(local_path(root, relative), local_path(snapshot / "ignored", relative)):
            raise TicketError("Ignored files changed during archival; checkout retained. Pause writers and retry.")


def restore_files(directory, state):
    value = state.get("archive")
    if not value:
        return
    snapshot = Path(value)
    archive_root = directory / "records" / state["ticket"] / "archives"
    managed_paths(directory, snapshot)
    if snapshot.parent != archive_root or snapshot.is_symlink() or not snapshot.is_dir():
        raise TicketError("Invalid or missing ticket archive; refusing restoration.")
    root = Path(state["worktree"])
    files = [Path(p) for p in read_json(snapshot / "ignored.json")["files"]]
    for relative in files:
        source = local_path(snapshot / "ignored", relative)
        target = local_path(root, relative)
        if (target.exists() or target.is_symlink()) and not same_file(source, target):
            raise TicketError(f"Restore would overwrite a changed file; left unchanged: {target}")
    for relative in files:
        source = local_path(snapshot / "ignored", relative)
        target = local_path(root, relative)
        if not target.exists() and not target.is_symlink():
            copy_file(source, target)
    workspace = Path(state["workspace"])
    saved = snapshot / "ticket.code-workspace"
    if saved.exists() and not workspace.exists():
        shutil.copy2(saved, workspace)


def clean_checkout(state):
    verify_checkout(state)
    if git(state["worktree"], "status", "--porcelain", "--untracked-files=all"):
        raise TicketError("Ticket has uncommitted or untracked changes. Save/commit them before Finish; nothing was removed.")


def activate(directory, state_path, state):
    root = Path(state["worktree"])
    if state.get("stage") == "finishing":
        state["restore_pending"] = bool(state.get("archive"))
    if not root.exists():
        root.parent.mkdir(parents=True, exist_ok=True)
        creating = state.get("stage") == "creating"
        state["restore_pending"] = bool(state.get("archive"))
        # Persist restoration intent before recreating a removed worktree.
        save_state(state_path, state, "creating" if creating else "restoring")
        branch_exists = subprocess.run(["git", "-C", state["repo"], "show-ref", "--verify", "--quiet",
                                        "refs/heads/" + state["branch"]]).returncode == 0
        if not branch_exists and creating:
            git(state["repo"], "worktree", "add", "-b", state["branch"], str(root), state["base_commit"])
        else:
            git(state["repo"], "worktree", "add", str(root), state["branch"])
        save_state(state_path, state, "starting")
    verify_checkout(state)
    if state.get("restore_pending"):
        restore_files(directory, state)
        state["restore_pending"] = False
        save_state(state_path, state, "starting")
    check_config(root)
    ensure_workspace(Path(state["workspace"]), task_config(root, directory, state["ticket"]))
    try:
        save_state(state_path, state, "starting")
        container(root, "up")
    except (OSError, subprocess.CalledProcessError) as error:
        state["last_error"] = f"Container start failed: {type(error).__name__}"
        save_state(state_path, state, "start-failed")
        raise TicketError("Container start failed. The ticket and checkout were retained; use Resume after fixing the error.")
    state.pop("last_error", None)
    save_state(state_path, state, "ready")
    return state


def start(directory, profile, name, base=None, fetch=True):
    state_path, root, workspace = paths(directory, name)
    if state_path.exists():
        _, state = load_ticket(directory, profile, name)
        return activate(directory, state_path, state)
    branch = f"flow/{name}"
    exists = subprocess.run(["git", "-C", profile["repo"], "show-ref", "--verify", "--quiet",
                             "refs/heads/" + branch])
    if root.parent.is_symlink() or state_path.parent.is_symlink():
        raise TicketError("Managed checkout/record paths must not be symlinks.")
    if exists.returncode == 0 or root.exists() or root.is_symlink():
        raise TicketError("That branch or worktree path already exists outside the ticket record; choose another ticket name.")
    base = base or profile["base"]
    commit = base_commit(profile["repo"], base, fetch)
    state = {"schema": 1, "ticket": name, "repo": profile["repo"], "common": profile["common"],
             "branch": branch, "base_ref": base, "base_commit": commit,
             "worktree": str(root), "workspace": str(workspace), "created_at": now()}
    root.parent.mkdir(parents=True, exist_ok=True)
    save_state(state_path, state, "creating")
    git(profile["repo"], "worktree", "add", "-b", branch, str(root), commit)
    return activate(directory, state_path, state)


def finish(directory, state_path, state):
    root = Path(state["worktree"])
    if state.get("stage") == "finished":
        return state
    if not root.exists():
        # Recover an interrupted finish only when an archive was fully prepared.
        if state.get("stage") == "finishing" and state.get("archive"):
            if any(item.get("worktree") == str(root) for item in worktrees(state["repo"])):
                raise TicketError("The missing checkout is still registered with Git; repair it before Finish.")
            Path(state["workspace"]).unlink(missing_ok=True)
            save_state(state_path, state, "finished")
            return state
        raise TicketError("Ticket checkout is missing. Resume it before finishing.")
    clean_checkout(state)
    if state.get("stage") in ("starting", "start-failed") and not (root / ".dev-flow/container.json").exists():
        raise TicketError("The failed start has no verified container record. Fix and Resume it before Finish.")
    snapshot = state_path.parent / "archives" / uuid.uuid4().hex
    managed_paths(directory, snapshot)
    snapshot.mkdir(parents=True, mode=0o700)
    files = archive_files(root, snapshot)
    workspace = Path(state["workspace"])
    if workspace.is_symlink():
        raise TicketError("Refusing a symlinked workspace file.")
    if workspace.exists():
        shutil.copy2(workspace, snapshot / "ticket.code-workspace")
    head = git(root, "rev-parse", "HEAD")
    write_json(snapshot / "ticket.json", {**state, "head": head, "archived_at": now()})
    if (root / ".dev-flow/container.json").exists():
        container(root, "stop")
    clean_checkout(state)
    verify_archive(root, snapshot, files)
    if git(root, "rev-parse", "HEAD") != head:
        raise TicketError("Ticket HEAD changed during Finish; checkout retained.")
    state["archive"] = str(snapshot)
    state["head"] = head
    save_state(state_path, state, "finishing")
    # Git supplies the final clean/locked-worktree checks. Never use --force.
    git(state["repo"], "worktree", "remove", str(root))
    workspace.unlink(missing_ok=True)
    save_state(state_path, state, "finished")
    return state


def open_workspace(path):
    if sys.platform != "darwin":
        raise TicketError("Automatic editor opening currently supports macOS. Open the printed workspace path manually.")
    subprocess.run(["open", "-a", "Devin", str(path)], check=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--home", type=Path, default=DEFAULT_HOME)
    sub = parser.add_subparsers(dest="action", required=True)
    configure = sub.add_parser("setup", help="Create the permanent repo control workspace")
    configure.add_argument("--base")
    configure.add_argument("--open", action="store_true")
    begin = sub.add_parser("start", help="Create/resume a ticket and start its container")
    begin.add_argument("ticket", type=valid_name)
    begin.add_argument("--base")
    begin.add_argument("--no-fetch", action="store_true")
    begin.add_argument("--open", action="store_true")
    resume = sub.add_parser("resume", help="Restore/resume a ticket and start its container")
    resume.add_argument("ticket", type=valid_name)
    resume.add_argument("--open", action="store_true")
    complete = sub.add_parser("finish", help="Archive ignored files, stop the container and remove a clean worktree; keep its branch")
    complete.add_argument("ticket", type=valid_name)
    complete.add_argument("--open", action="store_true", help="Reopen the permanent repo workspace afterward")
    inspect = sub.add_parser("status", help="Show a ticket's saved state")
    inspect.add_argument("ticket", type=valid_name)
    sub.add_parser("list", help="List ticket stages and checkout paths")
    try:
        args = parser.parse_args(argv)
        repo, common, directory = identity(args.repo, args.home)
        with locked(directory):
            profile = setup(repo, common, directory, args.base if args.action == "setup" else None)
            if args.action == "setup":
                destination = directory / "repo.code-workspace"
                print(destination)
            elif args.action == "start":
                state = start(directory, profile, args.ticket, args.base, not args.no_fetch)
                destination = Path(state["workspace"])
                print(f"Ticket: {state['ticket']}\nBranch: {state['branch']}\nCheckout: {state['worktree']}\nWorkspace: {destination}")
            elif args.action in ("resume", "finish", "status"):
                state_path, state = load_ticket(directory, profile, args.ticket)
                if args.action == "resume":
                    state = activate(directory, state_path, state)
                elif args.action == "finish":
                    state = finish(directory, state_path, state)
                destination = directory / "repo.code-workspace" if args.action == "finish" else Path(state["workspace"])
                print(json.dumps({**state, "workflow": workflow_status(state_path, state)}, indent=2))
            else:
                records = sorted((directory / "records").glob("*/state.json"))
                if not records:
                    print("No managed tickets yet. Run Ticket: Start.")
                for path in records:
                    _, state = load_ticket(directory, profile, path.parent.name)
                    progress = workflow_status(path, state)
                    print(f"{state['ticket']}\t{state['stage']}\t{progress['stage']}\t{state['worktree']}")
                destination = None
        if getattr(args, "open", False):
            open_workspace(destination)
        return 0
    except (TicketError, OSError, ValueError, KeyError, subprocess.CalledProcessError) as error:
        if isinstance(error, subprocess.CalledProcessError):
            message = f"{error.cmd[0]} failed with exit {error.returncode}; existing work was retained."
        else:
            message = str(error)
        print(f"flow-ticket: {message}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
