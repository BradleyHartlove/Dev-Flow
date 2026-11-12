---
name: flow-plan
description: Plan a change in Paradev and create or reuse Linear issues once the user agrees to the scope. Use for a bug, feature, or several workstreams before launching implementation.
---

# Plan in Paradev

Inspect the current source and relevant repository instructions. Explain the behavior and ask about decisions that affect scope, design, compatibility, or verification. For UI work, establish design direction and note that frontend-design applies.

Break work into changes the user can test and accept independently. Keep tightly coupled changes in one issue/workspace when they need to ship together. State the repo, starting branch, behavior, exclusions, tests and dependencies for each issue. For a dependency, identify the accepted branch or commit the next workspace should start from. Call out shared files, services, ports or writable mounts that affect parallel work.

Use the connected Linear plugin. Read the target project and search for existing issues before publishing. If native tools are unavailable, use the Paradev integrations skill to discover the Linear tools with `superset mcp tools --plugin linear` (or `paradev`). Once the scope is agreed, create or reuse issues in the selected Linear project, use its existing workflow states, link dependencies, and verify writes. Keep issue descriptions self-contained so a new author can start from the issue. Keep credentials, logs, private paths and full diffs local.

Return the actual Linear issue IDs and links, the recommended first batch and any open decisions. Stop at planning. The user starts implementation from the issue in Paradev.
