---
name: flow-task
description: Implement a linked Linear issue in its Paradev Worktree. Use when launched from a Paradev Linear task or asked to implement or resume an issue. Handles devcontainers, baseline and final checks, independent review, Linear progress and human handoff.
---

# Implement a Linear issue in Paradev

Read the linked issue and repository instructions. Confirm the exact issue ID and URL, its scope and acceptance criteria. If the prompt lacks the ID, use the connected Linear plugin to resolve it from the task context. Avoid posting to an ambiguous match. Give a short approach and bring consequential decisions back to the user.

## Start or resume

Use the existing Paradev Worktree as the host checkout. Verify its root, branch, registered Git worktree and repository identity. If the session is in the primary checkout, ask the user to start the issue in a Worktree. Use one author per checkout. Preserve existing changes on resume and read the saved task records before editing.

Before planning the implementation, editing files, or running project commands, read and follow the target repo's guidance. Start with its README.md, CLAUDE.md, AGENTS.md, and linked contributor or development docs where present. Check for directory-specific guidance before working in each affected area. Use the repo's commands and requirements for setup, builds, tests, lint, formatting, and generated files. Carry repo-required checks into the pipeline's CHECKS.md and record the exact commands and results. When relevant guidance conflicts or a required check cannot run through the container, surface the specific conflict or gap in the task record.

Run `flow-pipeline init --author claude` for Claude Code, or `flow-pipeline init --author codex` for Codex. It pins the starting HEAD of a clean linked worktree and returns the record directory. On resume use the same author and recorded base. If unrecorded edits already exist, recover the actual original base or report the evidence gap. A later scan cannot replace a baseline that was never captured.

Inspect the devcontainer configuration and scripts for writable sibling mounts, shared volumes, fixed container names and host ports. Resolve conflicting shared resources before running tasks in parallel. Run `flow-container up` and `flow-container status` in the worktree. Agents run on the host. Run project builds, tests, dependencies and application commands through `flow-container exec -- COMMAND` using the repository's documented commands. Use `--workspace` when running from elsewhere. Report routing or Docker errors and retain the checkout.

Save the issue URL/ID, requirements, decisions, worktree, branch, base and container identity in TASK.md under the pipeline record. Update the linked issue through the Linear plugin at start, meaningful progress, blockers and human handoff. Reuse existing states, verify writes, keep private source/paths/logs local, and reserve Done for human acceptance. If publishing fails, record pending updates in PROGRESS.md and report the gap. If native tools are missing, use the Paradev integrations skill and discover tools with `superset mcp tools --plugin linear` or `paradev`.

## Implement and verify

Before editing, finish the relevant baseline project tests and `flow-pipeline check baseline`. Keep earlier baseline evidence on resume. Record exact commands, exits and evidence in CHECKS.md. Preserve historical findings and report required checks that failed or could not run. Set pipeline stages as work progresses.

Implement the approved scope. Load frontend-design before UI edits. Rerun relevant container checks and `flow-pipeline check final`. Semgrep, Gitleaks, and offline OSV-Scanner are standard gates. Use WORKFLOW.md for OSV cache setup. Resolve introduced findings and report missing or incomplete evidence.

Pause writes and prepare HANDOFF.md with the issue requirements, pinned base, diff scope including untracked files and check evidence. Run `flow-pipeline review`. The other provider runs two fresh read-only sessions over the same paused worktree, one for behavior and one for regression tests. Use the local provider logins. Report the outcome of each pass in the author session. Verify findings against the code and test evidence, combine duplicates, fix confirmed findings, refresh evidence and rerun both passes. Stop with unresolved findings visible if two fix/review rounds have not resolved them or a decision is needed.

If Codex reaches its usage limit, continue in-scope work with Claude and optionally get a fresh read-only Claude second pass. Record it separately as same-provider feedback and leave cross-provider review pending. Resume the saved workspace and run `flow-pipeline review` after reset. Record actual limit/auth failures and preserve evidence.

## Hand off for acceptance

Write TESTING.md with actual test steps, verified startup and shutdown commands, and any published port or external prerequisite. Use flow-debrief for DEBRIEF.md. Run `flow-pipeline stage ready-for-human` only with fresh checks and cross-provider review. Update the Linear issue and link the local review, testing and debrief files in the Paradev session. Report the exact branch and checkout and show the user where to inspect the diff.

The user owns acceptance, staging, commits, push and merge requests. Keep the workspace available for feedback and resume in the same worktree. After acceptance and cleanup are requested, use flow-finish.
