---
name: flow-review
description: Independently review a dev-flow task using its requirements, pinned base commits, source, and verification evidence. Use for a task handoff or a requested dev-flow review; do not implement fixes unless asked.
---

# Review a task independently

Start from the supplied task record or HANDOFF.md. Read applicable repository instructions. Verify the repository paths, base commit hashes, branch heads, and working-tree state. If an implementation is still changing, ask its owner to pause before reviewing. Read requirements and inspect source before reading the author's justification.

Run the reviewer on the Mac host in the implementation task's worktree. Do not create a new board card that gives the reviewer a different checkout. For project checks, use the task's recorded container through `flow-container exec -- <command>` or an explicitly verified Dev Container CLI mapping. Do not substitute host toolchains when the container is unavailable. Source-only inspection and host-compatible source scanners may run on the host.

Review the whole task: committed changes since each pinned base, staged and unstaged changes, and relevant untracked files. For cross-repository work, check both sides of shared contracts and generated bindings. Explicitly list missing repositories or unavailable artifacts as coverage gaps.

Focus on behavior, error paths, permissions, concurrency, compatibility, data integrity, and useful regression tests. Follow changed code into callers and callees. Use available code intelligence to navigate, but verify claims against current source and account for incomplete or stale indexes. Check UI changes against the repository's design system and required frontend-design guidance.

Do not modify code during review. Run targeted, non-destructive checks when they materially establish a finding; otherwise assess the supplied evidence and say what you did not rerun. Do not turn a routine review into a four-persona audit unless requested or required by repository instructions.

For each actionable finding, report severity, file and line, a concrete triggering condition, observable impact, and the evidence. Distinguish confirmed bugs from unresolved questions. Skip stylistic preferences and speculative cleanup. A finding must change what a reasonable engineer would ship.

Write REVIEW.md next to the task record when a record directory was supplied. Include findings, examined repositories/files, checks run, coverage gaps, and remaining uncertainty. If there are no actionable findings, say so without claiming the code is correct or secure. Do not approve, merge, push, or post to an external service.

For re-review, inspect the fixes and their affected paths, rerun relevant checks as needed, and identify unresolved original findings or new regressions. Return control after one focused pass unless the user or repository requires more.
