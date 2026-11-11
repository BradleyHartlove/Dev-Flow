# Devin Desktop and local containers

The default is one local Devin window with native worktree sessions. Devin owns session/checkout selection; flow-task uses the chosen worktree and handles containers, checks, independent review and debrief. No board or GitLab service connection is required. See [WORKFLOW.md](WORKFLOW.md) and the [two-agent scoped test](DEVIN-TEST.md).

## One window, separate working copies

Open the primary repository in Devin. Start an implementation session with Worktree selected in the location picker, choose Claude Agent or Codex Agent, and give it a flow-task request. The skill verifies its actual working directory before writing. A different implementation session needs a different worktree and container. Keep the primary checkout available for orientation/planning.

Use the session list and side-by-side sessions to monitor parallel work. Review the selected session's Changes view. In IDE mode, Source Control can also expose its Git worktrees. These settings are present in the installed Devin Git extension and are disabled by default:

```json
{
  "git.detectWorktrees": true,
  "git.showDevinWorktrees": true
}
```

Set them in user settings, not shared application source. Use Source Control: Focus on Repositories View if necessary. The native Changes view and worktree visibility for both ACP agents are part of the scoped UI test; they have not been proven by script tests. File links should open in the existing window; do not use Open IDE Window for This Session as the routine review path.

## Existing devcontainer configuration

Keep the editor and agent installations on the Mac. The agent runs flow-container up for its selected checkout. The helper reuses the repo's devcontainer definition, adds absolute worktree/common-Git mounts and records the verified container ID in ignored .dev-flow/container.json. No shared devcontainer.json edit is needed for this integration.

Project commands run with flow-container exec. Semgrep, Gitleaks and the independent reviewer are local pipeline processes. A container is not created just because the editor opens; the skill starts it when implementation begins. Baseline/final tests do not require manually opening terminals or installing agents in each image.

Do not use native Reopen in Container or Rebuild commands for the host control window: they omit the helper's extra mounts or change where agent processes run. If you need container-specific language/debugger support, an attached editor window may still be useful; the single-window test covers agent management and review, not every debugger/IntelliSense feature.

Inspect shared writable mounts, service names and fixed ports before running independent containers. Existing configs that reach writable sibling repositories need an isolation recipe before parallel execution. ForwardPorts alone does not publish a fixed Docker host port; the scoped test does not start web servers.

## Plans and review evidence

flow-plan writes a design document with context, decisions, an optional diagram and tickets. Open its linked PLAN.md in Markdown preview beside chat. Claude/Codex skills do not automatically produce the built-in Devin Local agent's approval cards or a general interactive Artifacts canvas.

At ready-for-human, the author links source, REVIEW.md and DEBRIEF.md. The independent reviewer is a background other-provider CLI; findings are saved and explained in chat, not automatically native inline annotations. You make the final commit and any merge request manually.

## Cleanup and compatibility tools

For a native worktree, flow-finish stops the recorded container after explicit request and manual commit. It leaves branch/worktree deletion to you and Devin. Do not delete an active worker's directory.

The standalone flow-workspace and flow-ticket tools remain available for previously managed checkouts or troubleshooting. They are not required to start this native workflow. Existing generated workspace tasks still target their explicit checkout; opening one does not retarget a conversation. Use their lifecycle controls only for the matching managed environment.

References: [Agent Command Center](https://docs.devin.ai/desktop/agent-command-center), [external agents](https://docs.devin.ai/desktop/acp), [local Changes and parallel sessions](https://docs.devin.ai/desktop/changelog).
