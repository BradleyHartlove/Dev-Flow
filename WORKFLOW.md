# Standard development flow

Use one local Devin window to plan, run parallel author sessions and inspect their changes. The user creates/selects each implementation worktree in Devin. Skills operate inside that selected checkout and handle containers, tests, source scans, independent review and debrief. The user owns final Git staging, commits, pushes and merge requests. No GitLab service connection is required.

## The skills

| Skill | Purpose |
| --- | --- |
| flow-plan | Research the code, explain design decisions and write a readable plan with dependency-ordered tickets. |
| flow-task | Implement in the selected worktree, start its container, verify, scan, get the other provider's review, fix and prepare human acceptance. |
| flow-review | Independently inspect the author's source and evidence without implementing fixes. |
| flow-debrief | Explain behavior, decisions, checks, review and limits in the author conversation and saved records. |
| flow-finish | After a manual commit and explicit cleanup request, stop the task container and respect native/manager checkout ownership. |

Start a fresh Claude Agent or Codex Agent session after skill changes so its descriptions refresh. Both use the same installed skill sources. Start one implementation session per worktree; several independent worktree sessions may run concurrently. The background reviewer is read-only and uses the author's paused checkout.

## Planning is a document

A broad feature starts with flow-plan in a read-only planning conversation. PLAN.md includes the goal, current behavior, design, decisions/tradeoffs, an optional diagram, and the ticket table with dependencies and acceptance criteria. Its link opens in Devin's editor/Markdown preview beside chat. This is not a general interactive Artifacts canvas or an automatically generated native approval UI for a third-party agent.

The plan identifies which tickets can run together. Planning does not create implementation worktrees, containers or author sessions. The user starts the chosen Worktree sessions in Devin. Dependent work waits until its manually committed prerequisites are present in the selected base.

## Implementation in the selected worktree

1. Create/select the ticket's Worktree location in Devin before sending the feature prompt. Choose Claude Agent or Codex Agent and give the ticket to flow-task.
2. The skill verifies the session's actual checkout, branch and Git identity. A session still in the primary checkout pauses instead of quietly writing elsewhere. A fresh native worktree's current HEAD becomes its pinned base; a resume preserves its recorded base.
3. The skill checks for shared writable resources, starts the task's container through flow-container, verifies its mapping and reports its checkout/base/container identities.
4. Baseline project checks run in the container; baseline Semgrep and Gitleaks run through the local pipeline. All baseline processes finish before source edits.
5. The author implements, runs final container checks/scans, pauses source writes, and invokes flow-pipeline review. Claude authors get a Codex CLI reviewer; Codex authors get a Claude CLI reviewer.
6. Confirmed findings get fixes and fresh checks/review, with at most two routine fix cycles unless repo instructions require more. Infrastructure/design blockers remain visible.
7. The author writes the debrief and reaches ready-for-human only after current-source readiness passes. It links changed files and review/debrief evidence in the same conversation.
8. Review the session's Changes view or its worktree in the same window's Source Control. You stage/commit and open any merge request manually. There is no automatic merge or acceptance on an agent's completion.

Opening an editor workspace does not retarget an agent session. Native Changes should correspond to the session's real worktree. If it shows another checkout, diagnose the mismatch instead of opening a new window as the default workaround.

## Containers and records

Claude/Codex run on the Mac. Project tools run in one isolated container per active worktree, using the existing repository devcontainer configuration plus the helper's Git/worktree mounts. Container isolation does not require separate editor windows. Do not install the agents in each container or use native Reopen/Rebuild to replace helper-managed containers. Rebuild/stop is explicit recovery/cleanup, not part of a routine handoff.

Native worktree pipeline records live under dev-flow/runs; flow-pipeline returns their exact location. They stay outside application source. TASK.md records checkout owner and identity. CHECKS.md records real evidence, HANDOFF.md defines review scope, REVIEW.md holds independent findings, FIX.md records dispositions and DEBRIEF.md explains the result. Scan/review logs remain private and local. See the [agent command contract](skills/flow-task/references/commands.md).

The user follows progress in Devin's session list and author messages. There is no background board/scheduler. The reviewer reports through artifacts and the author conversation; it is not automatically another visible Devin session. Native UI state and the persisted pipeline stage have different purposes.

## Finish and compatibility

After manual commit and an explicit flow-finish request, the skill verifies clean Git status and idle workers, stops the selected native worktree's recorded container, records completion and leaves checkout/branch removal to Devin and the user. Closing a session alone does not stop a container or authorize removal.

Existing flow-ticket-managed checkouts remain supported when explicitly resumed. Their manager retains environment records and can archive/remove a clean managed checkout. The new native workflow does not call flow-ticket Start, adopt native worktrees into that manager, or open extra workspaces/windows.

## Limits and validation

- Shared writable sibling mounts, compose volumes, fixed container names and published ports need a task-specific isolation recipe. Separate Git worktrees alone do not solve those conflicts.
- No service-side GitLab integration, automatic commits/PRs/merges/deployments, or automatic worktree deletion is part of flow-task.
- Readiness validates scan/review freshness, not test execution from a prose claim. Reviewers/humans inspect actual command logs. Existing findings and unavailable coverage remain visible.
- The reviewer inspects source/evidence and does not independently rerun author tests. Existing Claude/Codex CLI authentication and subscription limits apply.
- Native session creation, ACP Changes rendering and layout are validated by the [user-run scoped test](DEVIN-TEST.md); helper tests alone cannot establish the editor experience.
