#!/usr/bin/env python3
"""Dispatch dependency-ordered local tickets through the Agetor CLI."""

import argparse
import json
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
import flow_pipeline as pipeline
import flow_ticket as ticket

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_HOME = ROOT / "boards"


def agetor(*args):
    executable = shutil.which("agetor")
    if not executable:
        raise ValueError("Agetor CLI is not on PATH.")
    result = subprocess.run([executable, "--no-daemon", "--json", *map(str, args)],
                            check=False, capture_output=True, text=True)
    if result.returncode:
        raise ValueError(f"Agetor {' '.join(map(str, args[:2]))} failed: {result.stderr.strip()[:1000]}")
    return json.loads(result.stdout)


def validate_plan(plan):
    rows = plan.get("tickets", [])
    if not rows or not isinstance(plan.get("max_parallel", 2), int) or not 1 <= plan.get("max_parallel", 2) <= 8:
        raise ValueError("Provide tickets and max_parallel between 1 and 8.")
    ids = [ticket.valid_name(row["id"]) for row in rows]
    if len(set(ids)) != len(ids):
        raise ValueError("Ticket IDs must be unique.")
    dependencies = {}
    for row in rows:
        if not row.get("title") or not row.get("description"):
            raise ValueError("Every ticket needs a title and description.")
        if row.get("harness", "claude-code") not in ("claude-code", "codex"):
            raise ValueError("This adapter supports Claude Code and Codex.")
        deps = row.get("requires", [])
        if not isinstance(deps, list) or any(dep not in ids for dep in deps):
            raise ValueError("Dependencies must name tickets in this plan.")
        # A dependent branch can inherit one prerequisite without an automatic merge.
        if len(deps) > 1:
            raise ValueError("Multiple prerequisite branches require a manually prepared integration base; split or integrate them before dispatch.")
        dependencies[row["id"]] = deps
    def visit(key, ancestors):
        if key in ancestors:
            raise ValueError("Ticket dependency cycle detected.")
        for dep in dependencies[key]:
            visit(dep, ancestors | {key})
    for key in ids:
        visit(key, set())
    return rows


def save(directory, state):
    ticket.write_json(directory / "state.json", state)


def board_column(row, column):
    agetor("move", row["card_id"], column)


def command_for(directory, action, *args):
    directory = directory.resolve()
    command = ["flow-board"]
    if directory.parent != DEFAULT_HOME.resolve():
        command += ["--home", str(directory.parent)]
    return shlex.join([*command, action, directory.name, *args])


def board_summary(directory, state):
    width = max([len("TICKET ID"), *(len(row["id"]) for row in state["tickets"])])
    lines = [f"Board: {state['name']}", f"Repository: {state['repo']}", "",
             f"{'TICKET ID':<{width}}  {'STATE':<11} TITLE"]
    for row in state["tickets"]:
        status = row["status"]
        if status == "queued" and row.get("requires"):
            status = "waiting"
        lines.append(f"{row['id']:<{width}}  {status:<11} {row['title']}")
        if row.get("requires"):
            lines.append(f"  Depends on: {', '.join(row['requires'])}")
        if row.get("error"):
            lines.append(f"  Attention: {row['error']}")
        lines.append(f"  Review: {command_for(directory, 'open', row['id'])}")
    lines += ["", f"Review task menu: {command_for(directory, 'open')}",
              f"Run/resume dispatcher: {command_for(directory, 'watch')}",
              "Review opens a prepared checkout; waiting tickets may not have one yet."]
    return "\n".join(lines)


def list_boards(home, as_json=False):
    states = [(path.parent, ticket.read_json(path)) for path in sorted(home.glob("*/state.json"))]
    if as_json:
        print(json.dumps([state for _, state in states], indent=2))
    elif states:
        print("\n\n".join(board_summary(directory, state) for directory, state in states))
    else:
        print("No boards yet. Use flow-plan in Devin to plan work and create an Agetor board; no agents were started.")


def review_workspace(directory, state):
    """Create local review-launcher tasks without changing application files."""
    config = {
        "folders": [{"name": "board-records", "path": str(directory)}],
        "settings": {"window.title": f"{state['name']} — Review launcher"},
        "tasks": {"version": "2.0.0", "tasks": [
            {"label": f"Review: Open {row['id']} — {row['title']}", "type": "process",
             "command": sys.executable,
             "args": [str(Path(__file__).resolve()), "--home", str(directory.parent),
                      "open", state["name"], row["id"]],
             "options": {"cwd": str(ROOT)}, "problemMatcher": []}
            for row in state["tickets"]]},
    }
    destination = directory / "review.code-workspace"
    ticket.ensure_workspace(destination, config)
    return destination


def ticket_workspace(state, ticket_id):
    row = next((r for r in state["tickets"] if r["id"] == ticket_id), None)
    if row is None:
        raise ValueError(f"Unknown board ticket {ticket_id}.")
    if not row.get("worktree") or not row.get("record_directory"):
        raise ValueError(f"Ticket {ticket_id} has not been prepared yet; no checkout was created or started.")
    record = Path(row["record_directory"]).parent
    environment = ticket.read_json(record / "state.json")
    root, workspace = Path(row["worktree"]), record / "ticket.code-workspace"
    expected = {"repo": state["repo"], "ticket": row["manager_name"],
                "worktree": str(root), "workspace": str(workspace),
                "branch": f"flow/{row['manager_name']}"}
    if any(environment.get(key) != value for key, value in expected.items()):
        raise ValueError("Board and ticket checkout identities disagree; nothing was opened.")
    if not root.is_dir() or not workspace.is_file():
        raise ValueError(f"Ticket {ticket_id}'s checkout/workspace is unavailable. Resume it explicitly if archived.")
    ticket.verify_checkout(environment)
    folders = ticket.read_json(workspace).get("folders")
    if folders != [{"name": "project", "path": str(root)}]:
        raise ValueError("Ticket workspace points elsewhere; nothing was opened.")
    return workspace


def initialize(directory, repo, plan, name, existing=None):
    rows = validate_plan(plan)
    if (directory / "state.json").exists():
        raise ValueError("Board already exists; use status or watch to resume it.")
    repo = Path(ticket.git(repo, "rev-parse", "--show-toplevel")).resolve()
    base = ticket.git(repo, "rev-parse", "HEAD")
    state = {"schema": 1, "name": name, "repo": str(repo), "base_commit": base,
             "max_parallel": plan.get("max_parallel", 2), "tickets": []}
    for spec in rows:
        manager_name = ticket.valid_name(f"{name}-{spec['id']}")
        state["tickets"].append({**spec, "manager_name": manager_name,
                                 "status": "queued", "card_id": None})
    save(directory, state)
    create_cards(directory, state, existing or {})
    review_workspace(directory, state)
    pipeline.write_text(directory / "BOARD.md", "# Board commands\n\n```text\n" + board_summary(directory, state) + "\n```\n")
    return state


def create_cards(directory, state, existing=None):
    for row in state["tickets"]:
        if row.get("card_id"):
            continue
        card_id = (existing or {}).get(row["id"])
        if card_id:
            detail = agetor("show", card_id)
            task = detail["task"]
            if detail.get("runs") or task["isolation"] != "none" or Path(task["workdir"]).resolve() != Path(state["repo"]):
                raise ValueError("Only an unstarted, non-isolated card for this exact repo may be adopted.")
        else:
            prompt = (f"Queued ticket {row['id']}: {row['description']}\n"
                      f"Dependencies: {', '.join(row.get('requires', [])) or 'none'}. "
                      "Do not implement from this placeholder. flow-board will prepare the isolated checkout and supply the task record before launch.")
            args = ["add", "--title", f"[{state['name']}/{row['id']}] {row['title']}", "--prompt", prompt,
                    "--agent", row.get("harness", "claude-code"), "--mode", "plan",
                    "--workdir", state["repo"], "--isolation", "none", "--type", "task"]
            if row.get("model"):
                args += ["--model", row["model"]]
            if row.get("effort"):
                args += ["--effort", row["effort"]]
            card_id = agetor(*args)["task"]["id"]
        row["card_id"] = card_id
        save(directory, state)
        board_column(row, "blocked" if row.get("requires") else "ready")


def active(detail):
    # The current run's status, not the card column, determines execution lifetime.
    run_id = detail["task"].get("runId")
    return any(run.get("id") == run_id and run.get("status") in ("running", "starting", "pending")
               for run in detail.get("runs", []))


def accepted_commit(row, detail):
    if active(detail):
        raise ValueError("The card's worker is still running.")
    root, record = Path(row["worktree"]), Path(row["record_directory"])
    state = pipeline.load(record, root)
    if state["stage"] != "ready-for-human":
        raise ValueError("The workflow has not reached ready-for-human.")
    pipeline.readiness(root, record, after_commit=True)
    head = ticket.git(root, "rev-parse", "HEAD")
    if head == row["base_commit"]:
        raise ValueError("Make the final commit by hand before marking this ticket Done.")
    subprocess.run(["git", "-C", str(root), "merge-base", "--is-ancestor", row["base_commit"], head], check=True)
    return head


def launch_worker(row, record):
    detail = agetor("show", row["card_id"])
    if active(detail) or detail["task"].get("pendingInteractionCount"):
        raise ValueError("An agent or question is already active for this card; it was not duplicated.")
    if detail["task"].get("hasOpenableRun"):
        agetor("send", row["card_id"], f"Use flow-task to resume the task recorded at {record / 'TASK.md'}.")
    else:
        # The CLI refuses `start` for a Blocked card even when its run failed.
        board_column(row, "ready")
        agetor("start", row["card_id"])


def start_row(directory, state, row, base):
    detail = agetor("show", row["card_id"])
    if active(detail) or detail["task"].get("pendingInteractionCount"):
        raise ValueError("An agent or question is already active for this card; it was not duplicated.")
    harness = detail["task"]["agent"]
    if harness not in ("claude-code", "codex"):
        raise ValueError("Choose Claude Code or Codex for this flow card.")
    row["harness"] = harness
    row["status"] = "starting"
    save(directory, state)
    print(f"Preparing {row['id']} from {base}", flush=True)
    repo, common, manager = ticket.identity(Path(state["repo"]), ticket.DEFAULT_HOME)
    with ticket.locked(manager):
        profile = ticket.setup(repo, common, manager)
        environment = ticket.start(manager, profile, row["manager_name"], base=base, fetch=False)
    root = Path(environment["worktree"])
    author = "codex" if harness == "codex" else "claude"
    if pipeline.main(["--workspace", str(root), "init", "--author", author]):
        raise ValueError("Pipeline initialization failed.")
    _, record, _ = pipeline.context(root, ticket.DEFAULT_HOME)
    row.update(worktree=str(root), record_directory=str(record), base_commit=environment["base_commit"])
    requirements = (f"# {row['title']}\n\n{row['description']}\n\n"
                    f"Plan: {directory / 'state.json'}\n\nTicket: {row['id']}\n\n"
                    f"Checkout: {root}\n\nBranch: {environment['branch']}\n\nPinned base: {environment['base_commit']}\n\n"
                    f"Environment owner: flow-ticket. Agetor card: {row['card_id']}.\n\n"
                    "The requested implementation is approved. Bring only material ambiguities or design changes to the user. "
                    "The user handles staging, commits and PRs manually.\n")
    if not (record / "TASK.md").exists():
        pipeline.write_text(record / "TASK.md", requirements)
    prompt_path = record / "agetor-prompt.txt"
    pipeline.write_text(prompt_path,
                        f"Use flow-task to implement ticket {row['id']}. Read the task record at {record / 'TASK.md'}. "
                        f"This Agetor card is already attached to the correct flow-ticket-owned checkout {root}. "
                        "Complete checks, automatic independent review and debrief; stop at ready-for-human. "
                        "Do not stage, commit, push or open a PR.\n")
    agetor("edit", row["card_id"], "--workdir", str(root), "--mode", "auto", "--prompt-file", str(prompt_path))
    save(directory, state)
    launch_worker(row, record)
    row["status"] = "working"
    row["board_phase"] = "running"
    row.pop("error", None)
    save(directory, state)
    print(f"Started {row['id']}: {root}", flush=True)


def tick(directory, state):
    create_cards(directory, state)
    by_id = {row["id"]: row for row in state["tickets"]}
    active_count = 0
    for row in state["tickets"]:
        detail = agetor("show", row["card_id"])
        if active(detail):
            active_count += 1
        if row["status"] not in ("working", "review"):
            continue
        if detail["task"]["column"] == "done":
            try:
                row["accepted_commit"] = accepted_commit(row, detail)
                row["status"] = "accepted"
                row.pop("error", None)
                print(f"Accepted {row['id']} at {row['accepted_commit']}", flush=True)
            except (ValueError, OSError, subprocess.CalledProcessError) as error:
                message = str(error)
                if row.get("error") != message:
                    print(f"Acceptance pending for {row['id']}: {message}", flush=True)
                row["error"] = message
            continue
        record = Path(row["record_directory"])
        workflow = pipeline.load(record, Path(row["worktree"]))
        phase = workflow["stage"]
        desired = None
        if not active(detail) and detail.get("runs") and phase != "ready-for-human":
            row.update(status="blocked", error="Worker stopped before ready-for-human; inspect its Agetor logs and retry after recovery.")
            desired = "blocked"
        elif phase == "ready-for-human":
            row["status"] = "review"
            desired = "review"
        elif phase == "waiting-decision":
            desired = "blocked"
        elif phase in ("implementing", "checking", "fixing", "planning", "reviewing", "blocked"):
            desired = "running" if active(detail) else "blocked"
        # Preserve native permission/question cards while a worker is waiting.
        if detail["task"].get("pendingInteractionCount"):
            desired = "blocked"
        # Publish coarse workflow transitions once, rather than reasserting a
        # column every poll and fighting native Agetor or the user's moves.
        if desired and row.get("board_phase") != desired:
            if detail["task"]["column"] != desired:
                board_column(row, desired)
            row["board_phase"] = desired
        row["work_stage"] = phase
    save(directory, state)
    for row in state["tickets"]:
        if active_count >= state["max_parallel"]:
            break
        if row["status"] != "queued":
            continue
        deps = [by_id[key] for key in row.get("requires", [])]
        if any(dep["status"] != "accepted" for dep in deps):
            continue
        base = deps[0]["accepted_commit"] if deps else state["base_commit"]
        try:
            start_row(directory, state, row, base)
            active_count += 1
        except (ValueError, OSError, subprocess.CalledProcessError, ticket.TicketError) as error:
            row.update(status="blocked", error=str(error))
            save(directory, state)
            board_column(row, "blocked")
            print(f"Blocked {row['id']}: {error}", flush=True)
    save(directory, state)
    return state


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--home", type=Path, default=DEFAULT_HOME)
    sub = parser.add_subparsers(dest="action")
    listing = sub.add_parser("list", help="Show local board names, ticket IDs and review commands")
    listing.add_argument("--json", action="store_true", help="Print saved records as JSON")
    init = sub.add_parser("init", help="Create parked Agetor cards from a local ticket graph")
    init.add_argument("name", type=ticket.valid_name)
    init.add_argument("--repo", type=Path, required=True)
    init.add_argument("--plan", type=Path, required=True)
    init.add_argument("--existing", action="append", default=[], help="Adopt an unstarted card as ticket-id=card-uuid")
    for command in ("tick", "watch", "status"):
        p = sub.add_parser(command)
        p.add_argument("name", type=ticket.valid_name)
        if command == "status":
            p.add_argument("--json", action="store_true", help="Print the full saved record as JSON")
        if command == "watch":
            p.add_argument("--interval", type=float, default=5)
    retry = sub.add_parser("retry", help="Requeue a blocked/start-interrupted ticket after fixing its environment")
    retry.add_argument("name", type=ticket.valid_name)
    retry.add_argument("ticket_id", type=ticket.valid_name)
    editor = sub.add_parser("open", help="Open a ticket in its own Devin window, or the board's review launcher")
    editor.add_argument("name", type=ticket.valid_name)
    editor.add_argument("ticket_id", nargs="?", type=ticket.valid_name)
    editor.add_argument("--print-path", action="store_true", help="Print the workspace path without launching Devin")
    try:
        args = parser.parse_args(argv)
        home = args.home.expanduser().resolve()
        if args.action in (None, "list"):
            list_boards(home, getattr(args, "json", False))
            return 0
        directory = home / args.name
        if args.action == "open":
            state = ticket.read_json(directory / "state.json")
            workspace = (ticket_workspace(state, args.ticket_id) if args.ticket_id
                         else review_workspace(directory, state))
            print(workspace, flush=True)
            if not args.print_path:
                ticket.open_workspace(workspace, new_window=True)
            return 0
        if args.action == "init":
            with ticket.locked(directory):
                state = initialize(directory, args.repo, json.loads(args.plan.read_text()), args.name,
                                   dict(value.split("=", 1) for value in args.existing))
            print(board_summary(directory, state))
            print(f"\nSaved commands: {directory / 'BOARD.md'}")
            return 0
        if args.action == "status":
            state = ticket.read_json(directory / "state.json")
            print(json.dumps(state, indent=2) if args.json else board_summary(directory, state))
            return 0
        if args.action == "retry":
            with ticket.locked(directory):
                state = ticket.read_json(directory / "state.json")
                row = next((r for r in state["tickets"] if r["id"] == args.ticket_id), None)
                if row is None or row["status"] not in ("blocked", "starting"):
                    raise ValueError("Only a blocked or interrupted-start ticket can be retried.")
                detail = agetor("show", row["card_id"])
                if active(detail) or detail["task"].get("pendingInteractionCount"):
                    raise ValueError("Answer or stop the existing worker first; it will not be duplicated.")
                row["status"] = "queued"
                row.pop("error", None)
                save(directory, state)
            return 0
        while True:
            with ticket.locked(directory):
                state = tick(directory, ticket.read_json(directory / "state.json"))
            summary = ", ".join(f"{row['id']}={row['status']}({row.get('work_stage','not-started')})" for row in state["tickets"])
            if summary != locals().get("last_summary"):
                print(summary, flush=True)
                last_summary = summary
            if args.action == "tick" or all(row["status"] == "accepted" for row in state["tickets"]):
                return 0
            time.sleep(max(1, args.interval))
    except KeyboardInterrupt:
        print("Dispatcher stopped. Agent sessions and containers were left running.")
        return 0
    except (ValueError, OSError, KeyError, subprocess.CalledProcessError, ticket.TicketError) as error:
        print(f"flow-board: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
