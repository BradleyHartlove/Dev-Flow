---
name: flow-review
description: Independently review a dev-flow ticket against requirements, pinned base, source and verification evidence. Used automatically by flow-task's other-provider reviewer or for an explicitly requested review; do not implement fixes.
---

# Review independently

Read TASK.md (requirements/exclusions/decisions), applicable repo instructions, pinned base and actual source before HANDOFF.md/the author's explanation. Inspect the full task: commits since the pinned base, staged/unstaged changes and relevant untracked files. Follow contracts into callers, schemas, generated code and related repos. Check UI changes against frontend-design and existing patterns.

Use the writer's exact worktree after writes pause; do not create another checkout. Focus on behavior, error paths, concurrency, permissions, compatibility, data integrity and regression coverage. Findings need a concrete trigger, observable impact, location, evidence and useful direction. Separate confirmed bugs from questions and missing evidence. Skip stylistic preferences and speculative cleanup.

Inspect CHECKS.md, command logs and baseline/final scan summaries; read actual reports as needed. Check the verification strategy against acceptance criteria. Tool errors, zero coverage, stale evidence and unexplained required-check failures are gaps. Existing baseline findings remain visible; “no new findings” is not a clean full-source scan. Source scanning does not replace tests or dependency checks.

When launched by flow-pipeline, perform source-and-evidence review. The wrapper supplies a tracked diff, untracked list and source access. Do not run builds/tests, modify files, launch agents or recursively invoke the pipeline. Return the requested structured JSON; the wrapper writes REVIEW.md and status. Clean means no actionable findings and sufficient evidence. Use incomplete for material missing evidence/unavailable files. Not independently rerunning sufficient author checks alone is not a coverage gap. Do not claim checks were rerun.

Reserve coverage_gaps for missing evidence that prevents a supported verdict; explain the affected requirement or risk. An absent optional AGENTS.md is not a gap. Scanner exclusions need context: excluded changed production code may leave a material gap, while excluded tests that were manually reviewed and exercised are not automatically a blocker. Put informational scan limits in the summary when evidence is otherwise sufficient; never hide a material gap or change the verdict just to unblock dispatch.

For a directly requested interactive review, run targeted non-destructive container checks only when useful to establish a finding. Never use host project toolchains. Write REVIEW.md in the supplied pipeline record and distinguish independently rerun checks from author evidence. Locate records using flow-pipeline status; do not invent a base for existing work.

Re-review inspects fixes and affected paths, validates dispositions and identifies unresolved/new regressions. Read the prior review and FIX.md, but assess current source independently. Return after the requested pass. Do not fix source, stage, commit, push, approve, merge, create PRs or contact collaborators. Human acceptance belongs to the user.
