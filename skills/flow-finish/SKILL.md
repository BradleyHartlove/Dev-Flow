---
name: flow-finish
description: Archive and close a managed dev-flow ticket after the user has reviewed and manually committed it. Use for requested ticket cleanup; never stage, commit, push or open a PR.
---

# Finish after the human

Identify the managed ticket and read its pipeline status/results. Confirm the user requested cleanup and that writers/reviewers/app processes using the worktree are idle. Wait for a running reviewer instead of stopping its container. A chat ending is not a cleanup request.

Verify actual Git status. If staged, unstaged or non-ignored untracked files remain, leave everything in place and report what still needs the user's manual commit. Do not stage, commit, stash, reset, force removal or edit ignore rules to make cleanup pass. If the final manual commit changed source beyond the reviewed result, recommend a focused recheck before declaring completion.

Run `flow-ticket --repo REPO finish NAME --open`. The manager archives ignored local files/reports, stops the recorded container, removes the clean managed worktree without force, preserves the branch/commits and opens the control workspace. Respect refusals; do not manually delete paths. A push/merge is not required because the user manages those separately.

After successful Finish, save a concise COMPLETE.md in the retained pipeline record with the user's manual commit and finished lifecycle state. Do not recreate the removed checkout just to update pipeline status. Report retained branch, commit and archive/record paths. Resume uses flow-ticket resume. Do not delete branches or prune archives/containers without a separate request.
