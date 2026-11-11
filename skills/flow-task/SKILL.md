---
name: flow-task
description: Implement or resume a development ticket with automatic ticket/workspace/container setup, security scans, independent cross-agent review, fixes, and a human acceptance packet. Use for dev-flow implementation; commits and PRs stay with the user.
---

# Own a development ticket

The user supplies the work, not the procedure. Run this loop without asking them to paste check commands, move handoff files, or launch a reviewer. Read the local [command contract](references/commands.md) for helpers and record locations. Keep the user engaged through behavior, decisions, research questions, and results.

## Establish the task

Read applicable repository instructions and the requested ticket/plan. Reuse requirements, exclusions, dependencies, accepted decisions and source references. Ask only when missing information materially changes the work. Verify branch/status claims in existing plans against Git. For an oversized or unclear workstream, use flow-plan before creating implementation checkouts.

If already in a matching flow-ticket worktree, resume it. Otherwise use `flow-ticket --repo REPO start NAME --open` to create or resume a managed ticket, workspace, and container. Choose a stable short name from the feature/ticket or use the plan's name/base. Never implement in a primary checkout just because the conversation started there. Preserve existing unmanaged work: resume it only when explicitly intended, pin its established base, and initialize the pipeline with `--base`; do not silently copy, adopt, reset or recreate it.

For an Agetor card dispatched by flow-board, the manager-owned checkout and TASK.md are already supplied. Use them directly; Agetor's own isolation is off. Do not create another ticket/worktree or start dependent cards. The dispatcher owns dependency/concurrency gates. Leave the card for human review at ready-for-human; the user commits and moves it to Done. Never use Agetor's Commit & push action.

A conversation may remain attached to the control workspace. Use the returned worktree as the explicit directory for every command and absolute target for edits. If tools cannot access it, surface that access issue once. Opening a workspace does not create or retarget a Devin agent session; do not claim it does.

Verify branch, pinned base, container ID, and host/container mapping before writing. If Colima is stopped and is the established Docker backend, starting it is routine local setup; do not change an unrelated active Docker context. Isolate every writable sibling repo and pin every base. If the manager rejects sibling configuration, report the missing isolation recipe; do not use shared writable siblings or claim automated multi-repo setup is supported.

Initialize flow-pipeline with this author (`claude` or `codex`). Use its returned record directory for TASK.md, CHECKS.md, HANDOFF.md, FIX.md, DEBRIEF.md and reports. Save requirements, accepted decisions and affected repo/base identities in TASK.md. Resume existing records. Keep records out of tracked application source.

## Plan and implement

Set persisted stages as work moves. Give a short approach: affected components, observable behavior, tradeoffs and verification. Ask for consequential decisions, not permission for already-authorized routine steps. An approved ticket with sufficient design can proceed directly. Use waiting-decision with a specific question when needed; continue independent investigation where useful.

Read source and use configured code intelligence when useful; verify index freshness and fall back to source search. Trace shared contracts. Load frontend-design before UI edits. Repository checks still apply. Older skills are not automatically part of this loop unless invoked or required. Do not impose prediction exercises or quizzes.

Agents run on the Mac. Project builds, tests, dependencies and application commands run through `flow-container --workspace WORKTREE exec -- COMMAND`. Container start/status is routine; rebuild is explicit recovery and discards container-only files. Never fall back to host project toolchains when routing fails.

Before editing, run appropriate baseline project checks and `flow-pipeline ... check baseline`. Record test commands, exits, results and log paths in CHECKS.md. Preserve baseline findings and discuss material existing failures; do not suppress them. If resuming after edits without an earlier baseline, record the gap rather than calling current code the original baseline.

Wait for every baseline process to finish before editing source. An in-flight baseline test can read a mixture of old and new code; if that happens, discard its claim as a baseline and record the gap. For a well-defined approved ticket, proceed after successful baseline checks without asking the user for a routine go-ahead.

Implement the authorized scope, run required container checks and `flow-pipeline ... check final`. Semgrep and Gitleaks are standard gates, not optional prompt details. Run repository-appropriate dependency checks when relevant, separately from source scans. Missing tools, failed rule downloads, zero coverage, parse errors and unavailable infrastructure are gaps. Do not buy/install another service automatically. Fix introduced findings and rerun affected checks without expanding into unrelated historical cleanup.

## Review automatically

Pause source writes. Prepare HANDOFF.md with requirements/base references, diff scope including relevant untracked files, decisions and CHECKS.md/report paths. Update CHECKS.md for the current source.

Run `flow-pipeline --workspace WORKTREE review`. It starts a fresh other-provider CLI reviewer (Claude author -> Codex reviewer; Codex author -> Claude reviewer), supplies requirements/base/diff/source/evidence, captures findings and writes REVIEW.md. It uses existing local CLI login/configuration; do not read credentials or switch to API billing. Authentication/limit/permission failures are blocked reviews, not approval. The subprocess does not automatically become a visible Devin session.

Wait/poll for the launched review and report meaningful stage changes. A manual handoff is not the normal completion path. If dispatch fails, retain evidence, explain the exact issue and smallest recovery; do not repeatedly spawn workers or bypass permission controls. This source/evidence review does not claim to independently rerun author tests.

Validate findings against code and set fixing. Fix confirmed issues in scope, record dispositions in FIX.md, rerun affected checks and final scans, refresh HANDOFF.md, then launch a fresh focused review. Default to at most two fix/re-review cycles; stop earlier for a design decision, repeated infrastructure failure or scope change. Stop after the limit with unresolved issues visible. Repository-mandated loops take precedence. Rejected findings need concrete evidence. If the helper detects source/index changes during review, pause competing writers and retry without reverting their work.

## Prepare human acceptance

After a clean independent review and current checks, run flow-debrief automatically. Save DEBRIEF.md in the pipeline record as well as any required work-notes version. Run `flow-pipeline ... stage ready-for-human --summary ...`; it verifies current-source review/scan evidence. Resolve or accurately report refusal; never bypass the gate by editing state. Historical baseline findings remain visible in acceptance.

Present before/after behavior, agent-made decisions, verification and gaps, independent review outcome and a few source locations. Include the exact worktree, branch, record path and persisted stage. Leave the environment available for inspection.

The user reviews, stages files, makes final Git commits, and opens PRs/MRs by hand. Do not git add/commit, push, create PRs, merge, release, deploy or clean up the checkout in this skill. Ready for the human is not accepted or shipped. After the user commits and requests cleanup, use flow-finish.
