# Ticket manager in Devin

The ticket manager bundles branch/worktree creation, local workspace generation, and container startup into one action. It lives outside your application repositories and uses the existing `flow-container` helper. Agents still run on the Mac.

## One-time setup per repository

```sh
flow-ticket --repo ~/code/patapsco-ai-operator setup --open
```

This opens a permanent repo control workspace in Devin. Use **IDE view → Cmd+Shift+P → Tasks: Run Task**. Agent view's selected conversation folder does not load editor workspace tasks. Setup creates only local manager files; it does not create a branch or start a container.

The default base is the remote's recorded default branch, then `origin/main`, `origin/master`, `main`, or `master`. To configure another base:

```sh
flow-ticket --repo ~/code/patapsco-ai-operator setup --base origin/main
```

## Daily use

1. Run **Ticket: Start** and enter a short name, for example `media-t5`. The manager fetches a remote-tracking base, pins its commit, creates branch `flow/media-t5` in a separate worktree, starts the container with worktree mounts, and opens the ticket workspace in Devin. Starting an existing ticket resumes it without resetting any files or changing its base.
2. Start an author conversation in the repo control workspace or select the printed **Checkout** path in Agents view. Invoke `flow-task` with the feature/ticket. It can run Ticket Start itself, operates on the returned worktree, and owns checks, scans, automatic other-provider CLI review, fixes and debrief. Opening a workspace does not automatically create or retarget agent sessions.
3. Monitor the author in Devin and the persisted work stage with **Ticket: List** or CLI status. The automatic reviewer reports through the ticket record and author conversation; it is not a separate native Devin session. At ready-for-human, review the result, stage files, commit and open the PR/MR yourself. The ticket workspace retains Start/Status/Rebuild/Stop controls. See [WORKFLOW.md](WORKFLOW.md).
4. After both agents are idle and changes are committed, run **Ticket: Finish** in the ticket workspace. It knows the current ticket name. The manager archives ignored files (including `.dev-flow`, reports, local `.env` files and caches), stops its recorded container, removes the clean worktree without force, and returns to the permanent repo workspace. The local branch and its commits are retained even if not pushed or merged.
5. To continue later, run **Ticket: Resume** in the permanent workspace and enter the name. It recreates the worktree from the retained branch, restores archived ignored files and the workspace, then starts the container. The writer and reviewer can use the same checkout again.

**Ticket: List** shows ticket name, environment lifecycle, workflow stage, and checkout path. `ready` means startup last succeeded; it does not claim an agent is running or independently query Docker. `ready-for-human` is a distinct workflow stage checked by flow-pipeline. Use **Flow: Container status** for live container state; CLI status includes the workflow summary and record path. Finished tickets with pipeline records display workflow complete while retaining their last record.

Finishing is an explicit action. Closing a chat or editor window does not trigger cleanup. The manager cannot detect whether external agents still use a checkout: make them idle before Finish, Stop, or Rebuild. It refuses Finish if there are staged, unstaged, or non-ignored untracked files, if the branch/checkout identity changed, or if Git locks the worktree. It never uses force removal, deletes branches, commits, merges, pushes, or changes GitLab tickets.

## Terminal equivalents

```sh
flow-ticket --repo ~/code/patapsco-ai-operator start media-t5 --open
flow-ticket --repo ~/code/patapsco-ai-operator list
flow-ticket --repo ~/code/patapsco-ai-operator status media-t5
flow-ticket --repo ~/code/patapsco-ai-operator finish media-t5 --open
flow-ticket --repo ~/code/patapsco-ai-operator resume media-t5 --open
```

When starting a new ticket offline, add `--no-fetch`. A stacked ticket can use `start next-ticket --base flow/media-t5`; that pins its existing local parent commit without modifying the other ticket. It does not automate dependency rebases or release ordering.

If the command is not on PATH, invoke scripts/flow_ticket.py from the installed dev-flow checkout with python3 and the same arguments. Tasks use the script's absolute path and a login zsh. `devcontainer`, Docker, and the normal user shell environment must be available. Start Colima separately if it is stopped.

## Storage and recovery

Default storage is the dev-flow checkout's `tickets/<repo-name>-<identity>/` directory:

```text
repo.json                         Repo identity and chosen base
repo.code-workspace               Permanent control workspace
worktrees/<ticket>/               Active checkout
records/<ticket>/state.json       Pinned base, branch, paths and lifecycle stage
records/<ticket>/ticket.code-workspace
records/<ticket>/archives/<id>/   Ignored local files, workspace and ticket snapshot
```

Profiles, records, and archives are local. The repo profile directory is created with user-only access, and JSON records use mode 0600. Archives can contain local secrets because ignored local files are preserved; keep this directory private. Archives and retained containers can consume disk space. They are not automatically pruned, and Finish stops rather than removes containers so container-only data remains available.

A failed startup keeps the checkout and branch. Fix the reported environment/configuration issue and use Resume. If startup failed before the helper recorded a container, Finish refuses to guess which container to stop. Use Resume successfully first. Rebuild remains explicit and can discard container-only files.

Ignored files are copied before the checkout is removed and checked again after container stop. Resume refuses to overwrite different files during restoration. Lifecycle actions are locked per repo so two Start/Finish commands cannot race. External agent writes do not participate in that lock, which is why agents must be idle for cleanup.

The manager owns only tickets it creates. It does not adopt, remove, or migrate your existing manual worktrees. The old `flow-workspace` and workspaces remain usable.

## Current limits

- macOS editor opening uses `open -a Devin`. The CLI prints paths as well.
- Root `.devcontainer/devcontainer.json` or `.devcontainer.json` is required, matching the existing container helper.
- Configurations with `${localWorkspaceFolder}/../...` sibling references are rejected until they have a task-specific isolation recipe. Other custom mounts and Compose naming/port conflicts still need repo-specific review; automatic multi-repo task setup is outside this version.
- Restoring a completed ticket requires its retained local branch. Branch pruning is deliberately separate.
- Setup does not itself run scans or create/retarget agent conversations. flow-task plus flow-pipeline perform scans and automatic local reviewer dispatch after implementation. Workflow stages appear in ticket status/list; native Devin session titles and board columns are not updated automatically.
- The CLI lifecycle has been tested with real disposable Git repositories and fake Docker/Dev Container commands. This new manager's task prompts, actual Docker lifecycle, and macOS editor opening still need the first Devin smoke test.
