# Devin Desktop and local containers

The standard agent-led entry point is now [WORKFLOW.md](WORKFLOW.md): use flow-plan when needed, then flow-task with only the feature/ticket. It uses flow-ticket to create the workspace/container and automatically runs checks, scans, cross-provider review and debrief. You manually stage, commit and open PRs. The workspace tasks below remain useful local controls.

For routine tickets, use the [ticket manager](TICKETS.md): one permanent repo workspace provides **Ticket: Start**, **Resume**, **Finish**, and **List**. It creates task worktrees and starts their containers for you. The container-only workspaces below remain useful for existing checkouts and troubleshooting.

For a standalone workspace, run `flow-workspace ~/code/my-app` and open the printed file with **File → Open Workspace from File** in Devin's editor. The generated file lives outside the application repository. It adds workspace tasks without modifying `.vscode`, `devcontainer.json`, or other shared source files. For managed tickets, flow-ticket generates the workspace automatically.

Keep this workspace local on the Mac. Claude and Codex run there using their existing host installations. The container holds the project toolchain. Do not use Devin's **Reopen in Container** or native **Rebuild** commands in this control workspace: those would change where terminals run or omit the extra worktree mounts.

## Lifecycle tasks

Use **Cmd+Shift+P → Tasks: Run Task**:

| Task | Behavior |
| --- | --- |
| Flow: Start container | Create or resume the container using the repository configuration plus local worktree mounts. Record its ID. |
| Flow: Container status | Check the recorded container and show its workspace mapping and running state. |
| Flow: Rebuild container (replaces container) | Replace this workspace's container using the same extra mounts. Bind-mounted source stays intact; container-only files are discarded. Use this for the earlier trial container that was created without those mounts. |
| Flow: Test | Start the container, then run `just test` inside the recorded container. |
| Flow: Lint | Start the container, then run `just lint` inside the recorded container. |
| Flow: Stop container | Stop the recorded container without deleting it or its data. |

Tasks use a login zsh so user-installed tools can be found through the normal shell setup. Docker/Colima and the `devcontainer` CLI must be available there. They do not start Colima automatically. The helper verifies the worktree mount before using a recorded container; failed commands do not fall back to the Mac.

There is no start-on-open or stop-on-close hook. A Claude session can end while Codex is still reviewing the same worktree. Stop the container after all sessions using that worktree are idle. A container can be resumed with Start. Rebuild is for configuration changes or recovery, not routine task handoffs. Do not run Rebuild or Stop while another agent uses that container.

## Agent instructions

The installed flow-task skill owns the operating procedure. In the task conversation, use a feature-only request:

```text
Use flow-task to implement T5 from the media-models plan.
```

For the first run after the failed native-container attempt, use the Rebuild task once. A normal Start may reuse that earlier container without the required mounts.

flow-task pauses writes and calls flow-pipeline review, which starts the other provider's local CLI against the same checkout and retains its report. The author handles findings and re-review before returning the human acceptance packet. Workspace tasks alone do not launch reviewers; the skill and pipeline helper own that step. Devin's built-in hooks are not assumed to cover external agents.

The CLI equivalents from the host worktree are:

```sh
flow-container up
flow-container status
flow-container exec -- just test
flow-container exec -- just lint
flow-container rebuild
flow-container stop
```

If an editor attached to the container is useful, attach a separate Devin or VS Code window to the running container. Preserve the local control workspace for the host agents. Devin supports **Dev Containers: Attach to Running Container**; agent placement in that attached window has not been tested.

## More tasks and repositories

Generate a local workspace for any existing repository checkout or worktree:

```sh
flow-workspace ~/code/my-app
flow-workspace /path/to/an/existing/worktree --name task-name
```

The command prints the workspace path under the dev-flow checkout's workspaces directory. Open that file in Devin's IDE view to load the tasks; choosing a session's folder in Agents view is not sufficient. Existing files are never overwritten: reopen the existing workspace or choose another `--name`. If the command is not on PATH, invoke scripts/flow_workspace.py from the installed checkout with python3 and the same arguments.

Generated workspaces contain four container lifecycle tasks. Test/Lint tasks in the original trial workspace are specific to zip-ties-runner; the generator does not assume those commands apply to another repo. Let `flow-task` discover each repository's checks and run them through `flow-container exec`.

A workspace file is an editor configuration pointing at a checkout; it does not create a branch, copy code, or isolate concurrent writers. Reuse it across sequential tasks in the same checkout. For two independent implementation tasks in the same repo, create separate worktrees first and generate a workspace for each. The writer and its independent reviewer use the same worktree, sequentially. Add only task-specific sibling checkouts if the repository mounts sibling repositories; a worktree does not isolate a shared sibling checkout.

Workspace files may stay together in this local `workspaces` directory. Each task targets its explicit workspace, and each worktree has an ignored `.dev-flow/container.json` record. Starting a fresh agent session does not require a fresh container.

## Validation and limits

The helper's unit tests cover routing, exit status, rebuild mounts, ID recording, and failure behavior. The workspace JSON and Start/Rebuild command expansion have been checked locally without launching containers. The task menu, shell environment, real container rebuild, and external-agent behavior in Devin still need the first manual smoke test. No application repository files were changed.

References: [workspace tasks](https://code.visualstudio.com/docs/editing/workspaces/multi-root-workspaces#_workspace-task-configuration), [Devin container commands](https://docs.devin.ai/desktop/advanced#dev-containers), [external agent configuration](https://docs.devin.ai/desktop/acp).
