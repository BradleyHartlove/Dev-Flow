---
name: flow-debrief
description: Explain the final behavior, design decisions, verification, and limitations of a completed dev-flow task. Use when that task finishes or the user requests its debrief.
---

# Debrief a completed task

Read its task record, actual final diff, and review results. Follow any repository- or user-required debrief skill, destination, and format; this skill does not replace them. Otherwise save DEBRIEF.md beside the task record.

Explain the resulting behavior with a concrete before/after example. Trace the important flow through a few source locations. For each real design decision, state the choice, actual alternative considered, reason grounded in this codebase, tradeoff, and who made the call. Do not invent alternatives or rationale.

Record checks actually run, important coverage gaps, unresolved review findings, and accepted limitations. An agent's statement that a test passed is evidence to inspect, not a substitute for a recorded result.

Give the user three likely questions from a teammate and clear answers. Keep the explanation focused on what the user needs to understand and defend. Do not require a quiz or pause merely to close the task. Report the saved path and decisions the agent made on the user's behalf.
