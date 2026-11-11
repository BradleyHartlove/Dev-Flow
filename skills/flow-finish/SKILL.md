---
name: flow-finish
description: Finish a dev-flow ticket after human review and a manual commit, respecting Devin or flow-ticket ownership of its checkout. Use for requested cleanup; never stage, commit, push or open a PR.
---

# Finish after the human

Identify the selected ticket/worktree, checkout owner in TASK.md, pinned base and pipeline status/results. Verify ownership against Git and any manager record; do not infer it from a directory name. Confirm the user requested cleanup and that writers/reviewers/app processes using the worktree are idle. Wait for a running reviewer instead of stopping its container. A chat ending is not a cleanup request.

Verify actual Git status. If staged, unstaged or non-ignored untracked files remain, leave everything in place and report what still needs the user's manual commit. Do not stage, commit, stash, reset, force removal or edit ignore rules to make cleanup pass. If the final manual commit changed source beyond the reviewed result, recommend a focused recheck before declaring completion.

For a Devin-owned worktree, leave checkout/branch removal to Devin and the user. Stop only its verified recorded container with `flow-container --workspace WORKTREE stop`, record the user's commit and completion in the external pipeline record, and mark the pipeline complete. Do not call flow-ticket Finish, adopt the checkout, delete native session files or open another window. Explain that the user can close/archive the session and explicitly remove its worktree later in Devin, retaining any unmerged branch/commit.

For a pre-existing flow-ticket-owned checkout only, run `flow-ticket --repo REPO finish NAME` without --open. The manager archives ignored local files/reports, stops the recorded container, removes the clean managed worktree without force and preserves its branch/commits. Respect refusals; do not manually delete paths. Save COMPLETE.md in the retained pipeline record and do not recreate the removed checkout to update status. Resume uses flow-ticket resume without opening another window.

Report the retained branch, commit, record/archive paths and exact cleanup performed. A push/merge is not required because the user manages those separately. Do not delete branches, discard work or prune containers/archives without a separate request.
