---
name: flow-finish
description: Finish an accepted Paradev Linear issue after the user's manual commit. Verify evidence, update Linear, and stop the workspace's recorded container when requested.
---

# Finish a Paradev issue

Resolve the exact linked issue and checkout from the author session and TASK.md. Wait for writers, reviewers and app processes to finish. Confirm the user's hands-on acceptance and manual commit. Run `flow-pipeline stage complete` to verify the reviewed source matches the clean committed source. Report any refusal and preserve the workspace.

Update the existing issue to the team's Done state only after verified acceptance. Confirm the update. Keep local paths and evidence in the author session. If Linear is unavailable, record the pending update in PROGRESS.md.

When the user requests cleanup, run `flow-container stop` from the workspace before it is archived. This stops only the recorded container and retains its data. Leave worktree archival and branch lifecycle to Paradev and the user. The user owns staging, commits, pushes, merges and deletions.
