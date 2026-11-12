# Operating dev-flow

## What each tool owns

Paradev creates and manages Git worktrees, visible agent sessions, and diffs. Linear holds scope, dependencies, progress and acceptance status. The local helpers start Docker containers and keep the check and review records. The user decides what starts, accepts behavior and commits the result.

## Containers

Claude Code and Codex run on the host. In a worktree, `flow-container up` invokes the Dev Container CLI using that repo's existing configuration. It verifies the checkout mount and stores the container ID in ignored local state. The mount lets tests see the same files the agent edits. The helper also mounts Git metadata so linked worktrees work inside the container.

```sh
flow-container status
flow-container exec -- uv run pytest -q
flow-container stop
```

Run these in the Paradev workspace terminal. Substitute the repo's test command. `exec` targets the recorded container and fails if it is stopped or does not match the worktree. `up` resumes the environment. `stop` retains container data. `rebuild` replaces the container and its container-only files. Stop the container before archiving or removing the workspace.

Independent worktrees have independent container records. Check writable sibling mounts, shared Compose volumes, fixed names and published host ports before running in parallel. Both containers can listen on the same internal port. Use different host ports or test the servers in sequence.

## Evidence and usage limits

`flow-pipeline init --author claude` pins a clean worktree's starting HEAD. Keep the original base and evidence when resuming. `flow-pipeline status` shows the evidence directory. Inspect CHECKS.md for commands and results, REVIEW.md for the other provider's findings, TESTING.md for hands-on steps and DEBRIEF.md for the design choices.

Claude authors get a focused Codex source-and-evidence review. The reviewer runs in the background, with its start and outcome relayed by the visible author session. If Codex hits its usage limit, Claude can keep working and a fresh Claude session can give a read-only second opinion. Record that as same-provider feedback. Keep cross-review pending until Codex resets. Resume the same worktree after any provider limit.

After testing and committing, `flow-pipeline stage complete` verifies that the clean committed source matches the reviewed and scanned source. Use `flow-finish` to update Linear and, when requested, stop the container. Keep full logs and local paths in the Paradev session.

## Earlier local records

Existing worktrees, saved evidence and planning files remain on disk. `flow-pipeline status` can still locate earlier pilot records from their worktree. Import an existing checkout into Paradev only when you intend to resume it. New issues should start through Paradev's native worktree flow.
