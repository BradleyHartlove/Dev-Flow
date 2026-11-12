# Operating dev-flow

## What each tool owns

Paradev creates and manages Git worktrees, visible agent sessions, and diffs. Linear holds scope, dependencies, progress and acceptance status. The local helpers start Docker containers and keep the check and review records. The user decides what starts, accepts behavior and commits the result.

## Work branches

Use `fix/<short-description>` for a bug fix, `feat/<short-description>` for new functionality, and `chore/<short-description>` for version bumps, dependency updates, and other maintenance. Use lowercase words separated by single dashes, such as `fix/invalid-cache-setting`. The workspace name can be anything.

Use the issue's **Work branch** when creating its workspace. If Paradev's native launch would use a different branch from Linear, pass the work branch explicitly. Substitute the Paradev project ID, Linear issue UUID, issue URL, and intended base branch:

```sh
paradev workspaces create --local --project PROJECT_ID --task LINEAR_ISSUE_UUID \
  --name "Cache settings" --branch fix/invalid-cache-setting --skip-branch-prefix \
  --base-branch main --agent claude --prompt "Use flow-task for LINEAR_ISSUE_URL"
```

`flow-pipeline init` checks the branch when initializing a new ticket. Existing pipeline records can resume on their original branches.

## Containers

Claude Code and Codex run on the host. In a worktree, `flow-container up` invokes the Dev Container CLI using that repo's existing configuration. It verifies the checkout mount and stores the container ID in ignored local state. The mount lets tests see the same files the agent edits. The helper also mounts Git metadata so linked worktrees work inside the container.

```sh
flow-container status
flow-container exec -- uv run pytest -q
flow-container stop
```

Run these in the Paradev workspace terminal. Read the repo's README.md, CLAUDE.md, AGENTS.md, and any applicable contributor or directory guidance. Use the repo's documented project commands and record its required checks in CHECKS.md. `exec` targets the recorded container and fails if it is stopped or does not match the worktree. `up` resumes the environment. `stop` retains container data. `rebuild` replaces the container and its container-only files. Stop the container before archiving or removing the workspace.

Independent worktrees have independent container records. Check writable sibling mounts, shared Compose volumes, fixed names and published host ports before running in parallel. Both containers can listen on the same internal port. Use different host ports or test the servers in sequence.

## Evidence and usage limits

`flow-pipeline init --author claude` pins a clean worktree's starting HEAD. Keep the original base and evidence when resuming. `flow-pipeline status` shows the evidence directory. Inspect CHECKS.md for commands and results, REVIEW.md for the other provider's findings, TESTING.md for hands-on steps and DEBRIEF.md for the design choices.

OSV-Scanner runs offline for the baseline and final checks. Before the first scan for a repo, populate the local cache for its package ecosystems from the Paradev terminal:

```sh
osv-scanner scan source --recursive --offline --download-offline-databases --allow-no-lockfiles .
```

The setup scan can exit 1 if it finds known vulnerabilities. Check its output for download errors. Keep the same advisory cache for baseline and final scans where possible, since newly published advisories can change the comparison. A scan with no detected packages is recorded as `no_packages`. A missing scanner, database failure, or new finding blocks readiness. On an in-flight ticket with earlier scan records, `flow-pipeline check final` backfills OSV from a temporary checkout of the pinned base and preserves the earlier Semgrep and Gitleaks evidence.

Pause writes and run `flow-pipeline review`. Claude authors get two fresh Codex sessions, and Codex authors get two fresh Claude sessions. The first pass traces behavior through callers and error paths. The second checks that test assertions and recorded runs cover the acceptance criteria. Each pass reads the same worktree and writes its own report. `REVIEW.md` shows both outcomes, and readiness requires both to be clean. A worktree or index change invalidates the review.

If Codex hits its usage limit, Claude can keep working and a fresh Claude session can give a read-only second opinion. Record that as same-provider feedback. Keep cross-provider review pending until Codex resets, then rerun both passes in the same worktree.

After testing and committing, `flow-pipeline stage complete` verifies that the clean committed source matches the reviewed and scanned source. Use `flow-finish` to update Linear and, when requested, stop the container. Keep full logs and local paths in the Paradev session.

## Earlier local records

Existing worktrees, saved evidence and planning files remain on disk. `flow-pipeline status` can still locate earlier pilot records from their worktree. Import an existing checkout into Paradev only when you intend to resume it. New issues should start through Paradev's native worktree flow.
