# Standard development flow

The user supplies the feature or ticket. The author agent owns environment setup, implementation, verification, review coordination and the final explanation. The user makes important decisions, accepts the result, stages files, makes final Git commits and opens PRs/MRs manually.

## The skills to use

| Skill | When to invoke it | What it owns |
| --- | --- | --- |
| flow-plan | Optional, for broad or unclear work | Investigation, design decisions, dependency-ordered tickets and verification criteria. |
| flow-task | The daily implementation entry point | Ticket/worktree/workspace/container setup, baseline, implementation, checks/scans, automatic reviewer, fixes/re-review, debrief and human acceptance packet. |
| flow-review | Normally internal; available for direct review | Independent source/evidence review of the writer's checkout. |
| flow-debrief | Normally called by flow-task | Explanation of behavior, decisions, evidence and limits. |
| flow-finish | After the user's commit, when cleanup is requested | Archive local artifacts, stop the container, remove the clean managed worktree and retain the branch. |

Examples:

```text
Use flow-plan for the media-models workstream in ~/code/media-frontends/TICKETS.md.
Use flow-task to implement T5 from that plan.
Use flow-task to resume media-t5.
Use flow-finish for media-t5. I have reviewed and committed it; its agents are idle.
```

The words about scanners, containers, handoffs and reviewer prompts belong in skills, not every feature request. Give actual feature requirements and constraints when they are not already in a ticket. Planning does not force a separate interview for a well-defined small fix.

## What happens after flow-task

1. The author reads the ticket and repo instructions, chooses/resumes a stable managed ticket, and runs flow-ticket Start. This creates the branch/worktree, workspace and container; it does not modify shared devcontainer configuration.
2. It uses the returned checkout explicitly, initializes the pipeline record, resolves meaningful decisions and records baseline checks/scans.
3. It implements the scope and runs the repo's checks in its container. Semgrep and Gitleaks run locally on the Mac; reports are outside source. Existing findings stay visible separately from introduced ones.
4. It pauses writing, prepares task/handoff/check evidence, and launches the other provider's CLI through flow-pipeline review. Claude authors are reviewed by Codex; Codex authors by Claude.
5. It validates and fixes confirmed findings, reruns affected checks/scans, and requests a fresh review. The routine limit is two fix/re-review cycles; unresolved design or infrastructure issues return to the user with evidence.
6. It writes the debrief and marks ready-for-human only when the current-source readiness checks pass. It leaves the environment available.
7. The user reviews the diff and explanation, stages, commits and opens the PR/MR manually. Cleanup is a separate requested flow-finish action.

## Monitoring and records

For an actual kanban board and dependency-aware dispatch, use the optional [Agetor adapter](AGETOR.md). It preserves flow-ticket ownership of checkouts and automatically maps pipeline stages to native card columns. The paragraphs below describe the standalone Devin conversation workflow.

Devin shows the author conversation. The background reviewer runs locally and reports through that conversation and durable ticket artifacts; it does not automatically become another native Devin session. Native board/session titles and columns are not manipulated.

Use Ticket: List in the repo control workspace, or:

```sh
flow-ticket --repo /path/to/repo list
flow-ticket --repo /path/to/repo status ticket-name
flow-pipeline --workspace /path/to/ticket-checkout status
```

List shows environment lifecycle and work stage separately. Work stages are planning, waiting-decision, implementing, checking, reviewing, fixing, ready-for-human, blocked and complete. Container ready means startup succeeded, not that tests or review passed. Closing a window/session does not stop or finish the task.

Managed records live under `tickets/REPO-IDENTITY/records/NAME/pipeline/`, retained outside the source checkout. TASK.md holds requirements/decisions, CHECKS.md records actual commands/exits/logs, HANDOFF.md anchors the review, REVIEW.md holds findings, FIX.md records dispositions, and DEBRIEF.md prepares human acceptance. Every scan/review keeps a distinct run directory and private logs. Runtime helper commands are documented in [the command contract](skills/flow-task/references/commands.md).

## What is enforced and what is agent-owned

flow-ticket deterministically manages checkout identity, pinned base, workspace/container lifecycle and archival. flow-pipeline runs both scanners, retains the baseline, dispatches the other provider, validates the structured response, detects source/index changes during review and checks scan/review freshness before ready-for-human. Missing tools, failed scans, invalid reports, timeouts or stale results do not become approval.

Repository-specific tests, good implementation decisions, coverage assessment and clear explanations remain agent responsibilities. CHECKS.md alone does not prove a test passed: reviewer/human should inspect its logs. Scanners are one source of evidence, not a security guarantee. Readiness allows unchanged historical findings to remain visible for human assessment; new IDs or scanner errors block it. A moved line can conservatively count as a new ID.

The reviewer is read-only source/evidence review and does not independently run project tests. Codex uses read-only sandbox mode; Claude is given file-read tools, without Bash/write/MCP tools. No permission-bypass flags or new API keys are used. CLI login/configuration and subscription limits apply. If authentication fails, fix that existing login; the pipeline does not switch billing modes.

## Current boundaries

- The initial author session is opened by the user in Devin. An author can start/resume tickets from a repo control session and use explicit checkout paths; opening a workspace does not retarget that session or grant additional file permissions.
- Multi-repo writable sibling isolation still needs a repo-specific recipe. The manager rejects known sibling configurations; skills surface the missing recipe rather than weakening isolation.
- Starting a dependent ticket from its parent's branch includes committed code only. The user commits the prerequisite before dependent implementation begins.
- Skills are normally discovered by both agents from their user-level directories. Start a fresh agent session after installation so descriptions refresh. Legacy bradley skills remain available and are not rewritten; repo requirements still apply.
- No PR automation, Git staging/commits, pushes, releases, deployments, contact with collaborators, or automatic cleanup are part of flow-task.

## Validation

The helper suite covers real disposable Git lifecycle behavior and pipeline failure/staleness paths. The standard skill validator checks all five skills. Live smoke tests exercised Semgrep's default rules, Gitleaks and both CLI reviewer routes using existing local authentication against a disposable fixture. This validates the automation plumbing; an actual feature still needs its repository checks and acceptance evidence.

Primary references: [Codex non-interactive mode](https://learn.chatgpt.com/docs/non-interactive-mode), [Claude CLI reference](https://code.claude.com/docs/en/cli-reference), [Semgrep CLI](https://docs.semgrep.dev/cli-reference), [Gitleaks](https://github.com/gitleaks/gitleaks).
