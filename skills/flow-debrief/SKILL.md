---
name: flow-debrief
description: Prepare a dev-flow ticket's human acceptance explanation, covering behavior, decisions, verification and independent review. Called automatically by flow-task or for a requested debrief.
---

# Explain the result for human acceptance

Read TASK.md, CHECKS.md, the actual final diff, REVIEW.md and any FIX.md from the pipeline record returned by flow-pipeline status. Follow any required repository/user debrief skill, destination and format. Also save DEBRIEF.md in the pipeline record, linking any required work-notes version, so readiness and later sessions can find it.

Explain before/after behavior with a concrete example and trace the important flow through a few source locations. For real decisions, state the choice, actual alternative considered, reason specific to the codebase, tradeoff and who made the call. Do not invent rationale or alternatives. Identify agent-made decisions for the user to assess.

Report actual project checks, source scans, baseline/new findings, dependency checks where relevant, independent review outcome, coverage gaps, accepted limitations and unresolved issues. An agent saying a check passed is not a substitute for its recorded result/log. Give three likely teammate questions with clear answers; do not require a quiz.

Present the exact worktree, branch, record path and a few useful diff locations. The user reviews, stages, commits and opens PRs/MRs by hand. Do none of those actions, and leave the environment available. Ready for human review is not accepted, released or shipped.

Keep the result in the author conversation with links to REVIEW.md, DEBRIEF.md and changed source. Direct the user to the session's Changes view or that worktree's Source Control entry in the same Devin window. Include the exact checkout and branch so they can verify which diff they are accepting. Do not launch editor windows or create task boards automatically. The reviewer report is evidence; it does not automatically become a native inline-comment review or separate visible agent session.

Only recommend the native Changes pane as working when the user has verified it for that ACP session. Empty native panes can coexist with real Git changes; distinguish the two and provide the correct worktree/branch for Source Control review instead of claiming native rendering succeeded.
