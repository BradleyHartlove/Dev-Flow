#!/usr/bin/env python3
"""Persist task progress, run local scans, and dispatch an independent CLI review."""

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
import re
from pathlib import Path
import signal
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LEGACY_HOME = ROOT / "tickets"
STAGES = ("planning", "waiting-decision", "implementing", "checking", "reviewing",
          "fixing", "ready-for-human", "blocked", "complete")
SCHEMA = {
    "type": "object", "additionalProperties": False,
    "properties": {
        "verdict": {"type": "string", "enum": ["clean", "changes_requested", "incomplete"]},
        "summary": {"type": "string"},
        "findings": {"type": "array", "items": {
            "type": "object", "additionalProperties": False,
            "properties": {key: {"type": "string"} for key in
                           ("severity", "file", "location", "trigger", "impact", "recommendation", "evidence")},
            "required": ["severity", "file", "location", "trigger", "impact", "recommendation", "evidence"]}},
        "coverage_gaps": {"type": "array", "items": {"type": "string"}},
    }, "required": ["verdict", "summary", "findings", "coverage_gaps"]}


def timestamp():
    return datetime.now(timezone.utc).isoformat()


def output(root, *args):
    return subprocess.run(["git", "-C", str(root), *args], check=True,
                          stdout=subprocess.PIPE).stdout


def read_json(path):
    if path.is_symlink():
        raise ValueError(f"Refusing symlinked record: {path}")
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object in {path}")
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


def registered_worktrees(root):
    return [entry.decode() for entry in output(root, "worktree", "list", "--porcelain", "-z").split(b"\0")
            if entry.startswith(b"worktree ")]


def context(workspace, home):
    root = Path(output(workspace.expanduser(), "rev-parse", "--show-toplevel").decode().strip()).resolve()
    common = Path(output(root, "rev-parse", "--path-format=absolute", "--git-common-dir").decode().strip()).resolve()
    worktrees = registered_worktrees(root)
    primary = Path(worktrees[0].removeprefix("worktree ")).resolve()
    # Keep earlier pilot evidence accessible at its original path.
    slug = re.sub(r"[^a-zA-Z0-9._-]+", "-", primary.name)
    key = hashlib.sha256(str(common).encode()).hexdigest()[:10]
    legacy = home.expanduser().resolve() / f"{slug}-{key}"
    record = legacy / "records" / root.name
    if root.parent == legacy / "worktrees" and (record / "state.json").is_file():
        state = read_json(record / "state.json")
        branch = output(root, "symbolic-ref", "--quiet", "--short", "HEAD").decode().strip()
        if (state["worktree"] != str(root) or state["common"] != str(common)
                or state["branch"] != branch or f"worktree {root}" not in worktrees):
            raise ValueError("Earlier pilot record belongs to a different checkout or branch.")
        return root, record / "pipeline", state["base_commit"]
    key = hashlib.sha256(str(root).encode()).hexdigest()[:12]
    return root, ROOT / "runs" / f"{root.name}-{key}" / "pipeline", None


def fingerprint(root, source_only=False):
    digest = hashlib.sha256()
    if not source_only:
        digest.update(output(root, "rev-parse", "HEAD"))
        digest.update(output(root, "status", "--porcelain=v1", "-z", "--untracked-files=all"))
        index = Path(output(root, "rev-parse", "--path-format=absolute", "--git-path", "index").decode().strip())
        if index.exists():
            digest.update(index.read_bytes())
    names = output(root, "ls-files", "--cached", "--others", "--exclude-standard", "-z")
    for raw in sorted(set(filter(None, names.split(b"\0")))):
        path = root / os.fsdecode(raw)
        if source_only and not path.exists() and not path.is_symlink():
            continue
        digest.update(raw + b"\0")
        if path.is_symlink():
            digest.update(b"link:" + os.fsencode(os.readlink(path)))
        elif path.is_file():
            digest.update(str(path.stat().st_mode).encode())
            with path.open("rb") as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    digest.update(chunk)
        else:
            digest.update(b"missing-or-directory")
    return digest.hexdigest()


def write_text(path, text):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with path.open("w") as stream:
        os.chmod(path, 0o600)
        stream.write(text)


@contextmanager
def locked(record):
    record.mkdir(parents=True, exist_ok=True, mode=0o700)
    with (record / ".pipeline.lock").open("a") as stream:
        try:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError("A check or reviewer is already running for this ticket.")
        try:
            yield
        finally:
            fcntl.flock(stream, fcntl.LOCK_UN)


def load(record, root):
    state = read_json(record / "STATUS.json")
    if state.get("workspace") != str(root):
        raise ValueError("Pipeline record points at a different checkout.")
    return state


def stage(record, state, value, summary):
    state.update(stage=value, summary=summary, updated_at=timestamp())
    write_json(record / "STATUS.json", state)


def run(command, root, record, stem, timeout=900, prompt=None):
    """No shell expansion; terminate the whole child process group on timeout."""
    stdout_path, stderr_path = record / f"{stem}.stdout", record / f"{stem}.stderr"
    for path in (stdout_path, stderr_path):
        write_text(path, "")
    try:
        with stdout_path.open("w") as stdout, stderr_path.open("w") as stderr:
            process = subprocess.Popen(command, cwd=root, stdin=subprocess.PIPE if prompt else subprocess.DEVNULL,
                                       stdout=stdout, stderr=stderr, text=True, start_new_session=True)
            previous_term = signal.getsignal(signal.SIGTERM)
            def terminate(signum, frame):
                raise InterruptedError("Pipeline was terminated")
            signal.signal(signal.SIGTERM, terminate)
            try:
                process.communicate(input=prompt, timeout=timeout)
            except (subprocess.TimeoutExpired, KeyboardInterrupt, InterruptedError):
                os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait()
                return {"command": command, "cwd": str(root), "exit_code": None,
                        "error": "Run timed out or was interrupted", "stdout": str(stdout_path), "stderr": str(stderr_path)}
            finally:
                signal.signal(signal.SIGTERM, previous_term)
        return {"command": command, "cwd": str(root), "exit_code": process.returncode,
                "stdout": str(stdout_path), "stderr": str(stderr_path)}
    except OSError as error:
        return {"command": command, "cwd": str(root), "exit_code": None,
                "error": str(error), "stdout": str(stdout_path), "stderr": str(stderr_path)}


def scan_result(tool, execution, path):
    result = {**execution, "tool": tool, "report": str(path), "finding_ids": [], "status": "error"}
    try:
        data = json.loads(path.read_text())
        if tool == "semgrep":
            rows = data["results"]
            rules = data.get("time", {}).get("rules", [])
            if data.get("errors") or not data.get("paths", {}).get("scanned") or not rules:
                raise ValueError("Semgrep reports errors, no scanned files, or no rule coverage.")
            identifiers = [f"{r['check_id']}:{r['path']}:{r['start']['line']}" for r in rows]
            result["rules"] = len(rules)
        else:
            if not isinstance(data, list):
                raise ValueError("Unexpected Gitleaks report format")
            identifiers = [f"{r['RuleID']}:{r['File']}:{r['StartLine']}" for r in data]
        if execution["exit_code"] not in (0, 1):
            raise ValueError("Scanner did not complete successfully")
        if (execution["exit_code"] == 1) != bool(identifiers):
            raise ValueError("Scanner result and exit code disagree")
        result.update(status="findings" if identifiers else "pass", finding_ids=sorted(set(identifiers)))
    except (OSError, ValueError, KeyError, TypeError) as error:
        result["error"] = execution.get("error", str(error))
    return result


def checks(root, record, state, phase, timeout):
    before = fingerprint(root)
    source_before = fingerprint(root, source_only=True)
    run_dir = record / "checks" / f"{phase}-{uuid.uuid4().hex[:10]}"
    run_dir.mkdir(parents=True, mode=0o700)
    stage(record, state, "checking", f"Running {phase} security scans")
    results = []
    commands = (
        ("semgrep", ["semgrep", "scan", "--oss-only", "--config", "p/default", "--metrics=off",
                     "--error", "--time", "--json", "--output", str(run_dir / "semgrep.json"), "."]),
        ("gitleaks", ["gitleaks", "dir", ".", "--redact", "--no-banner", "--report-format", "json",
                      "--report-path", str(run_dir / "gitleaks.json")]),
    )
    for tool, command in commands:
        print(f"Running {tool} ({phase}); reports: {run_dir}", flush=True)
        execution = run(command, root, run_dir, tool, timeout)
        results.append(scan_result(tool, execution, run_dir / f"{tool}.json"))
    # Directory scanning covers uncommitted files; scan task commits too if any exist.
    if output(root, "rev-parse", "HEAD").decode().strip() != state["base_commit"]:
        command = ["gitleaks", "git", ".", "--redact", "--no-banner", "--log-opts",
                   f"{state['base_commit']}..HEAD", "--report-format", "json",
                   "--report-path", str(run_dir / "gitleaks-commits.json")]
        execution = run(command, root, run_dir, "gitleaks-commits", timeout)
        result = scan_result("gitleaks", execution, run_dir / "gitleaks-commits.json")
        result["tool"] = "gitleaks-commits"
        results.append(result)
    value = {"phase": phase, "fingerprint": before, "source_fingerprint": source_before,
             "source_unchanged": fingerprint(root) == before,
             "results": results, "created_at": timestamp()}
    baseline_path = record / "baseline.json"
    baseline = read_json(baseline_path) if phase == "final" and baseline_path.exists() else {}
    for result in results:
        old = next((r for r in baseline.get("results", []) if r["tool"] == result["tool"] and r["status"] != "error"), None)
        result["new_finding_ids"] = sorted(set(result["finding_ids"]) - set(old["finding_ids"] if old else []))
    write_json(run_dir / "summary.json", value)
    write_json(record / f"{phase}.json", value)
    failed = not value["source_unchanged"] or any(r["status"] == "error" or r["new_finding_ids"] for r in results)
    stage(record, state, "blocked" if failed else "checking", f"{phase} scans recorded at {run_dir}")
    print(json.dumps(value, indent=2))
    return 1 if failed else 0


def review_command(reviewer, root, schema, response):
    if reviewer == "codex":
        return ["codex", "exec", "--sandbox", "read-only", "--cd", str(root),
                "--output-schema", str(schema), "--output-last-message", str(response), "-"]
    return ["claude", "-p", "--permission-mode", "plan", "--tools", "Read,Glob,Grep",
            "--add-dir", str(schema.parent.parent.parent), "--add-dir", str(ROOT / "skills"),
            "--disallowedTools", "mcp__*", "--strict-mcp-config", "--mcp-config", '{"mcpServers":{}}',
            "--output-format", "json", "--json-schema", json.dumps(SCHEMA)]


def validate_review(value):
    if not isinstance(value, dict) or set(value) != set(SCHEMA["required"]):
        raise ValueError("Reviewer response does not match the report schema")
    if value["verdict"] not in ("clean", "changes_requested", "incomplete") or not isinstance(value["summary"], str):
        raise ValueError("Invalid review verdict or summary")
    if not isinstance(value["coverage_gaps"], list) or not all(isinstance(v, str) for v in value["coverage_gaps"]):
        raise ValueError("Invalid coverage gaps")
    if not isinstance(value["findings"], list):
        raise ValueError("Invalid findings")
    fields = set(SCHEMA["properties"]["findings"]["items"]["required"])
    for finding in value["findings"]:
        if not isinstance(finding, dict) or set(finding) != fields or not all(isinstance(v, str) and v.strip() for v in finding.values()):
            raise ValueError("Incomplete finding")
    if value["findings"]:
        value["verdict"] = "changes_requested"
    elif value["coverage_gaps"]:
        value["verdict"] = "incomplete"
    return value


def review(root, record, state, timeout):
    for name in ("TASK.md", "HANDOFF.md", "CHECKS.md"):
        if not (record / name).is_file() or not (record / name).stat().st_size:
            raise ValueError(f"Missing {name}; the author must prepare the task and evidence first.")
    before = fingerprint(root)
    source_before = fingerprint(root, source_only=True)
    run_dir = record / "reviews" / uuid.uuid4().hex
    run_dir.mkdir(parents=True, mode=0o700)
    schema, response = run_dir / "schema.json", run_dir / "response.json"
    write_json(schema, SCHEMA)
    write_text(run_dir / "tracked.diff", output(root, "diff", "--no-ext-diff", "--no-textconv", state["base_commit"], "--").decode(errors="replace"))
    write_text(run_dir / "untracked.txt", output(root, "ls-files", "--others", "--exclude-standard").decode())
    reviewer = "codex" if state["author"] == "claude" else "claude"
    prompt = (f"Perform independent review with flow-review. Read {ROOT / 'skills/flow-review/SKILL.md'}.\n"
              f"Read requirements {record / 'TASK.md'} and applicable repository instructions, if present, first.\n"
              f"Checkout: {root}; pinned base: {state['base_commit']}.\n"
              f"Inspect {run_dir / 'tracked.diff'}, {run_dir / 'untracked.txt'} and actual source.\n"
              f"Then read {record / 'HANDOFF.md'}, {record / 'CHECKS.md'} and scanner summaries.\n"
              "This is a source-and-evidence review. Do not modify files, run project checks or launch agents. "
              "The author owns container checks; report genuinely missing evidence as coverage gaps. "
              "Not independently rerunning sufficient author checks alone is not a coverage gap. "
              "Return only the supplied structured JSON report; the wrapper writes REVIEW.md. "
              "Do not commit, stage, push, create PRs, or fix code. Include actionable bugs only.\n")
    write_text(run_dir / "prompt.txt", prompt)
    stage(record, state, "reviewing", f"Independent {reviewer} review; evidence at {run_dir}")
    print(f"Starting independent {reviewer} review; progress logs: {run_dir}", flush=True)
    execution = run(review_command(reviewer, root, schema, response), root, run_dir, "reviewer", timeout, prompt)
    value = {"verdict": "incomplete", "summary": "Reviewer did not complete", "findings": [], "coverage_gaps": []}
    try:
        if execution["exit_code"] != 0:
            raise ValueError(execution.get("error", f"Reviewer exited {execution['exit_code']}"))
        if reviewer == "claude":
            envelope = json.loads(Path(execution["stdout"]).read_text())
            if envelope.get("is_error"):
                raise ValueError("Claude reported an unsuccessful run")
            value = envelope["structured_output"]
        else:
            value = json.loads(response.read_text())
        value = validate_review(value)
    except (OSError, ValueError, KeyError, TypeError) as error:
        value = {"verdict": "incomplete", "summary": "Review execution failed", "findings": [], "coverage_gaps": [str(error)]}
    unchanged = fingerprint(root) == before
    if not unchanged:
        value["verdict"] = "incomplete"
        value["coverage_gaps"].append("Checkout or index changed during review; findings are stale. Nothing was reverted.")
    value.update(reviewer=reviewer, author=state["author"], fingerprint=before, source_fingerprint=source_before,
                 source_unchanged=unchanged, run_directory=str(run_dir), execution=execution)
    write_json(run_dir / "report.json", value)
    write_json(record / "review.json", value)
    text = f"# Independent review\n\nReviewer: {reviewer}\n\nVerdict: {value['verdict']}\n\n{value['summary']}\n"
    for item in value["findings"]:
        text += (f"\n## {item['severity']}: {item['file']} ({item['location']})\n\n"
                 f"Trigger: {item['trigger']}\n\nImpact: {item['impact']}\n\n"
                 f"Evidence: {item['evidence']}\n\nRecommendation: {item['recommendation']}\n")
    text += "\n## Coverage gaps\n\n" + ("\n".join(f"- {gap}" for gap in value["coverage_gaps"]) or "None reported.") + "\n"
    write_text(record / "REVIEW.md", text)
    next_stage = "checking" if value["verdict"] == "clean" else "fixing" if value["verdict"] == "changes_requested" else "blocked"
    stage(record, state, next_stage, f"{reviewer} review: {value['verdict']}; see {record / 'REVIEW.md'}")
    print(f"Review verdict: {value['verdict']}; report: {record / 'REVIEW.md'}", flush=True)
    return 0 if value["verdict"] == "clean" else 1


def readiness(root, record, after_commit=False):
    if after_commit and output(root, "status", "--porcelain", "--untracked-files=all").strip():
        raise ValueError("Commit all task source changes by hand before accepting the card.")
    current = fingerprint(root, source_only=after_commit)
    field = "source_fingerprint" if after_commit else "fingerprint"
    state = load(record, root)
    baseline = read_json(record / "baseline.json")
    if (not baseline.get("source_unchanged") or not baseline.get("results")
            or any(result.get("status") == "error" for result in baseline["results"])):
        raise ValueError("Usable baseline scan evidence is required.")
    review_data = read_json(record / "review.json")
    final = read_json(record / "final.json")
    if review_data.get("verdict") != "clean" or review_data.get(field) != current or not review_data.get("source_unchanged"):
        raise ValueError("A clean independent review of the current source/index is required.")
    expected_reviewer = "codex" if state["author"] == "claude" else "claude"
    if review_data.get("author") != state["author"] or review_data.get("reviewer") != expected_reviewer:
        raise ValueError("Review must be from the other agent for the current author.")
    if final.get(field) != current or not final.get("source_unchanged") or not final.get("results"):
        raise ValueError("Security scans must cover the current source/index.")
    if any(r.get("status") == "error" or r.get("new_finding_ids") for r in final["results"]):
        raise ValueError("Scanner errors or new findings remain. Resolve them before marking ready.")
    for name in ("CHECKS.md", "TESTING.md", "DEBRIEF.md"):
        if not (record / name).is_file() or not (record / name).stat().st_size:
            raise ValueError(f"Missing {name} for human acceptance.")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, default=Path.cwd())
    parser.add_argument("--ticket-home", type=Path, default=DEFAULT_LEGACY_HOME, help=argparse.SUPPRESS)
    sub = parser.add_subparsers(dest="action", required=True)
    sub.add_parser("paths", help="Show installation/resource paths without requiring a task checkout")
    init = sub.add_parser("init")
    init.add_argument("--author", choices=("claude", "codex"), required=True)
    init.add_argument("--base", help="Explicit base for a previously started checkout; defaults to the starting HEAD of a clean worktree")
    inspect = sub.add_parser("status")
    change = sub.add_parser("stage")
    change.add_argument("stage", choices=STAGES)
    change.add_argument("--summary", default="")
    check = sub.add_parser("check")
    check.add_argument("phase", choices=("baseline", "final"))
    check.add_argument("--timeout", type=int, default=900)
    dispatch = sub.add_parser("review")
    dispatch.add_argument("--timeout", type=int, default=900)
    try:
        args = parser.parse_args(argv)
        if args.action == "paths":
            print(json.dumps({"root": str(ROOT), "scripts": str(ROOT / "scripts"),
                              "skills": str(ROOT / "skills"), "runs": str(ROOT / "runs")}, indent=2))
            return 0
        root, record, managed_base = context(args.workspace, args.ticket_home)
        if args.action == "status":
            print(json.dumps({"record_directory": str(record), **load(record, root)}, indent=2))
            return 0
        with locked(record):
            if args.action == "init":
                worktrees = registered_worktrees(root)
                if f"worktree {root}" not in worktrees[1:]:
                    raise ValueError("Start implementation in a separate Paradev Worktree.")
                state_path = record / "STATUS.json"
                existing = load(record, root) if state_path.exists() else None
                base = args.base or managed_base or (existing["base_commit"] if existing else None)
                if base is None:
                    if output(root, "status", "--porcelain", "--untracked-files=all").strip():
                        raise ValueError("Cannot pin a baseline after editing. Use a fresh worktree or recover the original base.")
                    base = "HEAD"
                base = output(root, "rev-parse", "--verify", "--end-of-options", f"{base}^{{commit}}").decode().strip()
                if managed_base and base != managed_base:
                    raise ValueError("Requested base differs from the earlier pilot's pinned base.")
                if existing:
                    state = existing
                    if state["base_commit"] != base:
                        raise ValueError("Pinned task base changed; existing records retained.")
                    if state["author"] != args.author:
                        raise ValueError("Resume with the recorded author; changing it would invalidate review evidence.")
                else:
                    state = {"schema": 1, "workspace": str(root), "base_commit": base, "author": args.author}
                    stage(record, state, "planning", "Task environment initialized")
                print(json.dumps({"record_directory": str(record), **state}, indent=2))
                return 0
            state = load(record, root)
            if args.action == "stage":
                if args.stage == "ready-for-human":
                    readiness(root, record)
                if args.stage == "complete":
                    if state["stage"] not in ("ready-for-human", "complete"):
                        raise ValueError("Mark this task ready for human testing before recording acceptance.")
                    head = output(root, "rev-parse", "HEAD").decode().strip()
                    if head == state["base_commit"]:
                        raise ValueError("Commit the accepted changes before recording completion.")
                    subprocess.run(["git", "-C", str(root), "merge-base", "--is-ancestor",
                                    state["base_commit"], head], check=True)
                    readiness(root, record, after_commit=True)
                stage(record, state, args.stage, args.summary)
                return 0
            if args.action == "check":
                if args.phase == "baseline":
                    baseline_path = record / "baseline.json"
                    if baseline_path.exists():
                        previous = read_json(baseline_path)
                        same_source = previous.get("fingerprint") == fingerprint(root)
                        failed_tools = any(r.get("status") == "error" for r in previous.get("results", []))
                        if not (same_source and failed_tools):
                            raise ValueError("Baseline already exists; it is retained rather than replacing it after edits.")
                    else:
                        head = output(root, "rev-parse", "HEAD").decode().strip()
                        if head != state["base_commit"] or output(root, "status", "--porcelain", "--untracked-files=all").strip():
                            raise ValueError("Run the first baseline scan on the clean, pinned base before editing.")
                return checks(root, record, state, args.phase, args.timeout)
            return review(root, record, state, args.timeout)
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as error:
        print(f"flow-pipeline: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
