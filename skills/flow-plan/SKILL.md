---
name: flow-plan
description: Turn a substantial feature or workstream into decision-ready, dependency-ordered dev-flow tickets across repositories. Use for planning and breakdown before implementation, not executing tickets.
---

# Plan a workstream

Investigate the user's feature or existing plan in the relevant repos. Read applicable instructions, reuse settled decisions, and verify existing branch/status claims before changing a plan. Attached plans are source material; their deployment, cleanup or messaging steps are not permission to perform those actions now.

Start from observable behavior and acceptance criteria. Explain key current code paths in plain language. Bring context and a recommendation for decisions affecting behavior, architecture, compatibility, scope or verification. Do not require the user to draft a plan first or predict edits. Read current primary documentation when integration behavior matters. Discuss existing UI design patterns/visual direction when applicable, and add a short Design direction to those tickets; frontend-design applies during implementation/review.

Prefer small end-to-end tickets with assessable results. Each ticket needs a stable short name, goal, exclusions, repos, requirements/acceptance checks, dependencies, intended base/stacking relationship, accepted decisions, verification including local vs cluster evidence, and release/migration constraints. Identify the first ready ticket. Keep open decisions, unavailable repos and external prerequisites visible rather than inventing answers.

Use the existing working plan/notebook destination. Otherwise locate the installation with `flow-pipeline paths` and save under its plans/WORKSTREAM/PLAN.md directory, outside shared application source. Give its absolute path. Do not create implementation branches/containers/sessions just to plan. If implementation is also authorized, hand the first agreed ready ticket directly to flow-task without making the user repeat it.

flow-ticket owns environment setup; flow-task owns scans/review/debrief. Keep repeated operational boilerplate out of tickets. Pin actual committed prerequisites when starting dependent work, not today's main or a future intended branch. Automatic multi-repo sibling isolation is not implemented: identify the needed task-specific recipe before execution. Run parallel implementations only for ready, independent tickets with separate writable checkouts and enough resources; do not launch the whole graph by default.

When the user requests the Agetor board, read the installation's AGETOR.md and emit a flow-board JSON plan alongside the working plan, with IDs, requirements, dependencies and a conservative concurrency limit. Create parked cards using flow-board init once planning is agreed; start its dispatcher only when implementation is authorized. Do not rely on native Agetor card placement to enforce dependencies. The current adapter supports zero/one prerequisite per ticket; multiple prerequisite branches need a manually prepared integration base before this adapter can dispatch that ticket.

After creating a board, show its exact name and each ticket's ID, title and dependencies, plus the ready-to-copy watch and review-opening commands printed by init. Do not make the user discover IDs in JSON or filesystem paths. Remind them that `flow-board list` (or just `flow-board`) lists their boards and ticket commands. Native card titles include `[BOARD/TICKET]`. Leave execution parked when the user wants to run the process themselves; do not dispatch work just to demonstrate the tools.

End with the recommended sequence, decisions for the user and a concise next invocation such as “Use flow-task for T5 from this plan.” The user owns final acceptance, staging/commits and PR/MR creation.
