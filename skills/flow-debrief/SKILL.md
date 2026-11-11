---
name: flow-debrief
description: Prepare a dev-flow ticket's human acceptance explanation, covering behavior, decisions, verification and independent review. Called automatically by flow-task or for a requested debrief.
---

# Explain the result for human acceptance

Read TASK.md, CHECKS.md, the actual final diff, REVIEW.md and any FIX.md from the pipeline record returned by flow-pipeline status. Follow any required repository/user debrief skill, destination and format. Also save DEBRIEF.md in the pipeline record, linking any required work-notes version, so readiness and later sessions can find it.

Explain before/after behavior with a concrete example and trace the important flow through a few source locations. For real decisions, state the choice, actual alternative considered, reason specific to the codebase, tradeoff and who made the call. Do not invent rationale or alternatives. Identify agent-made decisions for the user to assess.

Report actual project checks, source scans, baseline/new findings, dependency checks where relevant, independent review outcome, coverage gaps, accepted limitations and unresolved issues. An agent saying a check passed is not a substitute for its recorded result/log. Give three likely teammate questions with clear answers; do not require a quiz.

Present the exact worktree, branch, record path and a few useful diff locations. The user reviews, stages, commits and opens PRs/MRs by hand. Do none of those actions, and leave the environment available. Ready for human review is not accepted, released or shipped.
