---
name: flow-task
description: Carry one development task through investigation, implementation, checks, and an independent-review handoff. Use when the user asks to run the dev-flow pipeline on a task.
---

# Run a task

The user owns behavior, scope, and material tradeoffs. The agent owns implementation and routine follow-through. Read applicable repository instructions; this skill does not replace their checks or change commit, push, merge, or deployment permissions. If frontend work is involved, load the required frontend-design skill before editing UI.

Run Claude Code or Codex on the Mac host in the task's existing worktree. Keep agent installations, credentials, skills, and code intelligence on the host. Use the task's development container for project builds, tests, dependency installation, and application processes. Use `flow-container up`, `flow-container status`, and `flow-container exec -- <command>` when the helper is installed. Otherwise use the Dev Container CLI with an explicit task workspace and verified container ID. Never silently run project commands on the host when container execution fails.

Verify the branch, host worktree, container workspace, and mounted sibling repositories before writing. For changes spanning repositories, record each checkout and base commit; never let two writing tasks share a writable sibling checkout. A worktree alone is not a sandbox, and host agents retain their host permissions. A sibling mount such as `../aictl` needs task-specific configuration before using a board-created worktree in an unrelated directory. Stop for that mapping rather than using a shared writable sibling.

## Task record

Use a task-record path the user supplies. Otherwise use `.dev-flow/task` under the host worktree and report its absolute path. The container helper adds `.dev-flow/` to the repository's local Git exclusions. Verify that records are ignored before writing them, and stop if that directory contains tracked files. Keep scanner reports there too. Do not store reports inside `.git`, which agent sandboxes may protect. Record:

- Goal, acceptance criteria, explicit exclusions, and current stage.
- Repository paths, branches, immutable base commit hashes, host/container workspace mapping, container ID, and accepted decisions.
- Applicable check commands, results, known baseline failures, and unverified behavior.
- Independent findings, their disposition, and the next action.

Resume an existing record when supplied rather than investigating from scratch.

## Investigate and implement

Use code intelligence if configured, verify index freshness against the actual worktree, and read the relevant source. Fall back to source search when the graph is missing or incomplete. Trace shared APIs, schemas, generated code, and runtime boundaries explicitly.

Present a short approach with the affected components, observable behavior, main risk, and verification strategy. Ask only for decisions that materially affect requirements, compatibility, architecture, or scope. Once the approach is authorized, complete routine implementation and checks without per-slice predictions, quizzes, or requests to continue. Follow any explicit gates in applicable instructions.

Run the checks appropriate to this repository and change. Host-compatible source and secret scanners may run on the host; project toolchains and dependency checks run in the container. Tests, lint, static security checks, secret scans, and dependency scans are separate forms of evidence. Record tool errors, zero applicable rules, skipped tests, and unavailable infrastructure as gaps; do not describe them as a clean pass. Do not suppress or baseline a finding merely to make a gate green. Keep credentials redacted in reports.

## Independent review

Pause writes and prepare HANDOFF.md in the task-record directory. Include requirements, every repository and pinned base hash, working-tree status, intended checks, actual results, decisions, and known gaps. Include commands that show committed and uncommitted task changes, and tell the reviewer to inspect untracked files separately.

Request a fresh review from the other agent using flow-review if available. Both agents review the same host worktree sequentially. If a board creates a new worktree for every card, do not make a separate reviewer card against a different checkout: use a sequential pipeline step in the original worktree, or launch the reviewer directly there. A handoff file does not start that agent: report the exact next action if no authorized integration can launch it. Do not claim the task is independently reviewed until its findings have been received. The reviewer should read requirements and code before reading the author's defense of the implementation.

Validate findings against code, fix confirmed issues, rerun affected checks, and request a focused re-review. Default to one fix/re-review cycle for routine work; report unresolved issues instead of looping indefinitely. Repository-mandated review requirements take precedence.

Finish with behavior before/after, important decisions, checks and gaps, unresolved findings, and a few source locations for the user to inspect. Keep the task in review until human acceptance. Follow the repository's commit/push rules and required debrief workflow.
