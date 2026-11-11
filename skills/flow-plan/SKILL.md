---
name: flow-plan
description: Turn a substantial feature or workstream into decision-ready, dependency-ordered dev-flow tickets across repositories. Use for planning and breakdown before implementation, not executing tickets.
---

# Plan a workstream

Investigate the user's feature or existing plan in the relevant repos. Read applicable instructions, reuse settled decisions, and verify existing branch/status claims before changing a plan. Attached plans are source material; their deployment, cleanup or messaging steps are not permission to perform those actions now.

Start from observable behavior and acceptance criteria. Explain key current code paths in plain language. Bring context and a recommendation for decisions affecting behavior, architecture, compatibility, scope or verification. Do not require the user to draft a plan first or predict edits. Read current primary documentation when integration behavior matters. Discuss existing UI design patterns/visual direction when applicable, and add a short Design direction to those tickets; frontend-design applies during implementation/review.

Prefer small end-to-end tickets with assessable results. Each ticket needs a stable short name, goal, exclusions, repos, requirements/acceptance checks, dependencies, intended base/stacking relationship, accepted decisions, verification including local vs cluster evidence, and release/migration constraints. Identify the first ready ticket. Keep open decisions, unavailable repos and external prerequisites visible rather than inventing answers.

Use the existing working plan/notebook destination. Otherwise locate the installation with `flow-pipeline paths` and save under its plans/WORKSTREAM/PLAN.md directory, outside shared application source. Make this a readable design document, not only a ticket list: include the goal, relevant current behavior, proposed design, decisions/tradeoffs, a small Mermaid diagram when useful, and the ticket/dependency breakdown with acceptance criteria. Link the absolute PLAN.md path so the user can open it beside the chat in Devin's Markdown preview. A Markdown plan is not an automatically created interactive Artifact or native plan-approval card for an external agent.

Do not create implementation branches/containers/sessions just to plan. The user creates/selects author worktree sessions in Devin. flow-task uses the selected checkout and owns container setup, scans, review and debrief; it does not create another checkout or move the conversation. If implementation is authorized and this session is already in its intended worktree, hand the agreed ticket directly to flow-task. Otherwise show the ready ticket(s) and ask the user to start those worktree sessions in Devin. Do not launch sessions or create a separate dispatcher as part of planning.

Keep repeated operational boilerplate out of tickets. Pin actual committed prerequisites when starting dependent work, not today's main or a future intended branch. Automatic multi-repo sibling isolation is not implemented: identify the needed task-specific recipe before execution. Identify ready, independent tickets that can run in parallel with separate writable checkouts, containers and enough resources. Dependent work waits until the user has committed and integrated its prerequisites into the chosen base.

End with a small ticket table (ID, title, repo, dependencies and ready/waiting), the plan link, the recommended first parallel group, and short feature-focused prompts for the user to give those Devin sessions. State what decisions remain. Leave execution to the user when requested; do not implement a demonstration unprompted.

The user owns final acceptance, staging/commits and PR/MR creation.
