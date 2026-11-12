# Paradev worktree commands

Run these in the Paradev workspace terminal. Use `--workspace /absolute/worktree/path` before the subcommand when running from elsewhere.

Read the target repo's README.md, CLAUDE.md, AGENTS.md, and applicable contributor or directory guidance before choosing project commands. Use its required setup, test, and lint commands inside the recorded container and capture their results in CHECKS.md.

```sh
git rev-parse --show-toplevel
git branch --show-current
flow-pipeline init --author claude
flow-container up
flow-container status
flow-container exec -- uv run pytest -q
flow-pipeline check baseline
```

Use `--author codex` for a Codex author and the repository's test command in place of pytest. Finish baseline work before editing. After editing, rerun project checks through the container, then run `flow-pipeline check final`. Prepare TASK.md, CHECKS.md and HANDOFF.md in the directory returned by `flow-pipeline status` before `flow-pipeline review`.

Clean behavior and regression-test passes on current source, fresh scans, CHECKS.md, TESTING.md and DEBRIEF.md allow `flow-pipeline stage ready-for-human`. See WORKFLOW.md for local OSV database setup. After human testing and a manual commit, `flow-pipeline stage complete` verifies acceptance evidence against the committed source. Stop the workspace's container with `flow-container stop` before archiving it in Paradev.

Commands use local provider authentication. Full evidence stays under the local pipeline record. Keep Linear updates concise and verify each remote write.
