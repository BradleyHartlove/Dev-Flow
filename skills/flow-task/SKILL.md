---
name: flow-task
description: Implement or resume a development ticket in the worktree selected in Devin, with container setup, security scans, independent cross-agent review, fixes, and a human acceptance packet. Commits and PRs stay with the user.
---

# Own a development ticket

The user supplies the work, not the procedure. Run this loop without asking them to paste check commands, move handoff files, or launch a reviewer. Read the local [command contract](references/commands.md) for helpers and record locations. Keep the user engaged through behavior, decisions, research questions, and results.

## Establish the task

Read applicable repository instructions and the requested ticket/plan. Reuse requirements, exclusions, dependencies, accepted decisions and source references. Ask only when missing information materially changes the work. Verify branch/status claims in existing plans against Git. For an oversized or unclear workstream, use flow-plan before implementation.

Devin owns the author session and its selected Git worktree. Resolve the session's actual working directory, Git root, branch, HEAD, common Git directory and registered worktrees before writing. Use this exact checkout throughout; do not create a second checkout, call flow-ticket Start, switch branches, or open another editor window. Worktree paths and branch names come from Git, not guesses about Devin's naming convention. A new implementation needs its own registered linked worktree, separate from the primary checkout and other writers. If this session is still in the primary checkout, do read-only orientation and tell the user to start/select a Worktree session in Devin before implementation; do not silently edit elsewhere while the chat remains attached here.

For a fresh Devin-created worktree, confirm there are no pre-existing application changes, pin its current HEAD before edits, and initialize flow-pipeline with `--base COMMIT --author claude|codex`. A dependent task must already contain the user's committed prerequisite; verify that commit and required behavior before continuing. Do not merge or copy another worker's uncommitted changes. On resume, read the existing pipeline state/TASK.md and retain its original base rather than repinning to today's HEAD. Preserve unexpected staged/unstaged/untracked work; only resume it when the user intended that work and its original base is established. Missing pre-edit baseline evidence is a gap, not a reason to reset files or relabel the current source as baseline.

Devin may create an empty snapshot commit while preparing a worktree. Different starting hashes can still represent identical source. Verify ancestry/source as needed, record the actual starting HEAD, and preserve editor-generated commits. Do not reset them to force a shared hash or attribute them to a manual user acceptance commit. Source/index changes during scans/review still invalidate evidence; diagnose them rather than relaxing freshness checks.

A pre-existing flow-ticket-managed worktree can be explicitly resumed in place using its recorded identity/base. Do not adopt a Devin-owned checkout into that manager. Use the selected worktree as the explicit directory for every command and absolute target for edits. If tools cannot access it, surface that access issue once. Opening files/workspaces does not retarget an existing agent session; do not claim it does.

Inspect the devcontainer configuration and scripts for writable sibling mounts, shared volumes, fixed container names and fixed published ports before starting parallel work. A linked worktree alone does not isolate those resources. Isolate every writable sibling repo and pin every base; if a task-specific recipe is missing, report it before startup instead of sharing writable source. Run `flow-container --workspace WORKTREE up` to create/resume this checkout's container. Verify branch, pinned base, recorded container ID, and host/container mapping before writing. If Colima is stopped and is the established Docker backend, starting it is routine local setup; do not change an unrelated active Docker context. Do not edit shared devcontainer.json just to integrate this workflow.

Use flow-pipeline's returned record directory for TASK.md, CHECKS.md, HANDOFF.md, FIX.md, DEBRIEF.md and reports. Save requirements, accepted decisions, checkout owner (`Devin` or existing `flow-ticket`), actual branch/worktree/common Git directory, pinned base and container identity in TASK.md. Resume existing records. Keep records out of tracked application source. Give a brief initial report with ticket/goal, exact checkout, branch, base and container; this lets the user verify each parallel session is isolated without managing helper commands.

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

Keep progress in this Devin conversation with short updates at meaningful stages. Direct human review to this session's Changes view or the selected worktree in the same window's Source Control. Include links to changed files, REVIEW.md and DEBRIEF.md. Do not create a board, launch another top-level session, open a new IDE window or ask the user to relay reviewer prompts. If the UI shows the wrong checkout, diagnose that mismatch before claiming its diff is this task's result.

Native ACP session Changes rendering is not guaranteed: the live inventory trial produced real uncommitted Git changes with empty Changes panes. Do not assert that the user can see edits there without confirmation. Use the actual worktree's Git Source Control diff as the dependable fallback, and report empty/stale native panes as an editor integration gap rather than missing code. Sidebar workspace grouping follows folder identity and need not combine related worktrees.

The user reviews, stages files, makes final Git commits, and opens PRs/MRs by hand. Do not git add/commit, push, create PRs, merge, release, deploy or clean up the checkout in this skill. Ready for the human is not accepted or shipped. After the user commits and requests cleanup, use flow-finish.
