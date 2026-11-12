---
name: flow-review
description: Independently review a dev-flow ticket against requirements, pinned base, source and verification evidence. Used automatically by flow-task's other-provider reviewer or for an explicitly requested review; do not implement fixes.
---

# Review independently

Read TASK.md (requirements, exclusions and decisions), applicable repo instructions, the pinned base and actual source before reading HANDOFF.md. Read and follow README.md, CLAUDE.md, AGENTS.md, linked contributor docs and directory-specific guidance where present. Check the implementation against the repo's conventions and the recorded evidence against its required commands and checks. Inspect commits since the pinned base, staged and unstaged changes, and relevant untracked files. Follow contracts into callers, schemas, generated code and related repos. Check UI changes against frontend-design and existing patterns.

Use the writer's exact worktree after writes pause; do not create another checkout. Focus on behavior, error paths, concurrency, permissions, compatibility, data integrity and regression coverage. Findings need a concrete trigger, observable impact, location, evidence and useful direction. Separate confirmed bugs from questions and missing evidence. Skip stylistic preferences and speculative cleanup.

Inspect CHECKS.md, command logs and baseline/final scan summaries; read actual reports as needed. Check the verification strategy against acceptance criteria. Tool errors, zero coverage, stale evidence and unexplained required-check failures are gaps. Existing baseline findings remain visible; “no new findings” is not a clean full-source scan. Source scanning does not replace tests or dependency checks.

When launched by flow-pipeline, follow the focus in the prompt. For the behavior pass, trace contracts through callers and error paths. For the regression-test pass, connect each acceptance criterion to the assertions and recorded results that cover it. The wrapper supplies a tracked diff, untracked list and source access. Assess your pass independently of the other review. Do not run builds/tests, modify files, launch agents or recursively invoke the pipeline. Return the requested structured JSON. Clean means no actionable findings and sufficient evidence for this pass. Use incomplete for material missing evidence or unavailable files. Not independently rerunning sufficient author checks alone is not a coverage gap. Do not claim checks were rerun.

Reserve coverage_gaps for missing evidence that prevents a supported verdict; explain the affected requirement or risk. An absent optional AGENTS.md is not a gap. Scanner exclusions need context: excluded changed production code may leave a material gap, while excluded tests that were manually reviewed and exercised are not automatically a blocker. Put informational scan limits in the summary when evidence is otherwise sufficient; never hide a material gap or change the verdict just to unblock dispatch.

For a directly requested interactive review, run targeted non-destructive container checks only when useful to establish a finding. Never use host project toolchains. Write REVIEW.md in the supplied pipeline record and distinguish independently rerun checks from author evidence. Locate records using flow-pipeline status; do not invent a base for existing work.

Re-review inspects fixes and affected paths, validates dispositions and identifies unresolved/new regressions. Read the prior review and FIX.md, but assess current source independently. Return after the requested pass. Do not fix source, stage, commit, push, approve, merge, create PRs or contact collaborators. Human acceptance belongs to the user.
