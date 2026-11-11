# dev-flow

A local development workflow for people who want to manage coding agents while staying responsible for the result. Describe the feature or ticket; the agent handles its checkout, development container, checks, security scans, independent review and handoff back to you.

You make the important decisions, review the final diff, stage files, make the Git commit and open the PR/MR yourself.

The current setup targets **macOS, Devin Desktop, Claude Code and Codex CLI**, using one local Devin window and its native worktree sessions. Agents run on the Mac; project builds, tests and dependency commands run in dev containers. Your Git hosting service does not need an integration.

## What it includes

| Tool | Responsibility |
| --- | --- |
| `flow-ticket` | Create/resume a ticket branch, isolated Git worktree, editor workspace and container; archive a clean ticket later. |
| `flow-container` | Start, inspect, rebuild, stop and execute commands in the recorded container, with mounts that keep linked worktrees usable. |
| `flow-pipeline` | Persist work stages, run Semgrep/Gitleaks, dispatch the other provider for review and check readiness for human review. |
| `flow-workspace` | Generate a standalone local editor workspace for an existing checkout. Useful without the ticket manager. |
| `flow-board` | Optional Agetor kanban adapter: list board/ticket IDs and review commands, open review workspaces, dispatch independent tickets and hold dependent work until a prerequisite is manually committed and accepted. |
| Five `flow-*` skills | Tell the author and reviewer how to use these tools consistently. |

Devin is the conversation, progress and diff-review surface. The default skills use its selected worktree without creating another checkout or opening another IDE window. The helpers are ordinary local Python programs, and the skills are Markdown instructions shared by Claude and Codex.

## Requirements

- macOS and Devin Desktop for the documented native-session workflow. Windows is unsupported; non-macOS editor opening is not implemented.
- Git, Python 3.10 or newer, and zsh. The helpers use Python's standard library.
- A working Docker CLI/daemon, through Colima or Docker Desktop.
- The [Dev Container CLI](https://github.com/devcontainers/cli), available as `devcontainer`.
- [Claude Code](https://code.claude.com/docs/en/overview) and [Codex CLI](https://developers.openai.com/codex/cli), installed and authenticated locally. The automatic review needs both.
- [Semgrep](https://docs.semgrep.dev/semgrep-ce) and [Gitleaks](https://github.com/gitleaks/gitleaks), available on PATH.
- Application repos with `.devcontainer/devcontainer.json` or `.devcontainer.json`, plus their normal build/test instructions.

Common install commands for the container CLI and scanners are:

```sh
npm install -g @devcontainers/cli
uv tool install semgrep
brew install gitleaks
```

These assume Node/npm, uv and Homebrew are already installed. Install and authenticate the agent CLIs using their official instructions. The workflow reuses their existing login/configuration; it does not introduce an API key or change billing modes. Normal subscription limits still apply.

Any additional skills required by your repositories, such as frontend-design or a personal debrief workflow, must be installed separately.

## Install on a machine

Clone this repository to a stable location, then run:

```sh
cd /path/to/dev-flow
python3 scripts/install_flow.py
```

The installer creates:

```text
~/.local/bin/flow-container
~/.local/bin/flow-workspace
~/.local/bin/flow-ticket
~/.local/bin/flow-pipeline
~/.local/bin/flow-board
~/.agents/skills/flow-*     # Codex discovery
~/.claude/skills/flow-*     # Claude discovery
```

These are links to this checkout, so both agents use one maintained copy. Existing conflicting installations are moved into `backups/` before replacement. Re-running the installer leaves correct links alone.

Ensure `~/.local/bin` is on your PATH. If needed, add this line once to your shell configuration and open a new terminal:

```sh
export PATH="$HOME/.local/bin:$PATH"
```

Start fresh agent sessions after installing skills. For a quick installation check:

```sh
flow-ticket --help
flow-pipeline paths
devcontainer --version
docker info
semgrep --version
gitleaks version
claude auth status --text
codex login status
```

Start your Docker backend first if necessary, for example `colima start`. Tools must also be visible in Devin's terminal; generated tasks use a login zsh.

## Daily use

The default is one local Devin window. See the [two-agent scoped test](DEVIN-TEST.md) for a complete first run using the inventory example.

### Plan when needed

Start a planning conversation on the relevant primary repo:

```text
Use flow-plan for this feature: [requirements or a path to the working plan].
```

The agent writes a linked design document with context, decisions, optional diagrams and dependency-ordered tickets. Open it in Devin's Markdown preview beside chat. Planning does not launch implementations.

### Select a worktree, then implement

Create/select a separate Worktree location in Devin for each implementation session. Choose Claude Agent or Codex Agent and send the ticket or small feature:

```text
Use flow-task to implement T5 from this plan: /absolute/path/to/PLAN.md.
```

The skill uses the session's actual checkout, pins its initial commit, starts an isolated container and handles baseline checks, implementation, final checks, Semgrep, Gitleaks, independent review and debrief. No separate board or user-entered lifecycle commands are needed. A session still in the primary checkout pauses instead of silently editing a different directory.

Claude authors get a fresh Codex CLI reviewer; Codex authors get a fresh Claude CLI reviewer. The existing local logins/subscriptions are used. Routine fixes and re-review are bounded to two cycles; unresolved design/infrastructure issues remain visible.

### Monitor, review and commit

Use Devin's session list or side-by-side session layout. Detailed stages and the final review/debrief appear in the author conversation. The independent reviewer is a local background process, not automatically another visible session.

At ready-for-human, inspect the session's Changes view or its worktree in Source Control in the same window. You stage, commit, push and open merge requests manually. No GitLab service integration is required. Agent review is evidence for your decision; it is not human acceptance.

### Finish when requested

After your manual commit and with workers idle:

```text
Use flow-finish for this task. I reviewed and committed it; its workers are idle.
```

For a Devin-owned worktree, this stops its verified recorded container and retains evidence. Worktree/branch removal remains with Devin and you. A session ending alone does not authorize cleanup.

Previously flow-ticket-managed checkouts remain supported when explicitly resumed. Their manager handles archival/removal; the new skills do not adopt native worktrees into that manager. Standalone workspace/board tools remain optional compatibility tools outside the default skills.

## Where things live

```text
skills/          Shared skill source
scripts/         Local helpers and installer
tests/           Automated helper tests
profiles/        Thin compatibility prompts
tickets/         Local managed worktrees, records, archives and workspaces
workspaces/      Local standalone editor workspaces
runs/            Local pipeline records for unmanaged checkouts
plans/           Local plans when no existing plan destination was supplied
backups/         Previous local installations preserved by the installer
```

The last five directories are Git-ignored. Records include requirements, check evidence, independent findings and debriefs; each scan/review keeps a separate run directory. Archives may include ignored `.env` files and other local secrets. Keep local state private rather than committing it.

**Transfer the tooling, not ticket state.** On another machine, clone the repo, install dependencies, authenticate its agents, run the installer and create fresh repo/ticket workspaces. Existing workspaces/records use machine-specific absolute paths and are not portable. Git branches and committed application changes travel through your normal Git remotes. Keep this tool checkout at a stable path; moving it requires repairing links and dealing with existing local workspace references.

## Verification and boundaries

- Semgrep CE scans use `p/default`, metrics off and failing exits on findings. Rules are downloaded; unavailable rules or zero coverage remain errors.
- Gitleaks scans working files with redacted reports, plus the task's commit range when present. Final scans retain historical findings separately from newly identified ones.
- Reports live outside scanned application source. A finding ID uses rule/path/line, so moved lines can conservatively look new.
- Automatic review is source-and-evidence review. Codex uses a read-only sandbox; Claude has file-read tools and no Bash/write/MCP tools. The reviewer does not independently rerun project tests.
- Readiness requires current-source scans and a clean independent report. Project-specific test selection and the truth of recorded evidence still need agent/reviewer/human judgment.
- Known sibling-checkout configurations are rejected until a task-specific isolation recipe exists. Automatic multi-repo isolation, dependency rebases and release ordering are not implemented.
- Native Devin board columns/session titles are not updated automatically. Skills own coordination; helper records own durable progress.
- Closing a window does not stop a container. Rebuild/Stop/Finish are explicit actions; keep agents idle before using them. Worktrees do not sandbox host agent permissions.

## Tests

Run the helper suite without Docker or provider credentials:

```sh
python3 -m unittest discover -s tests
```

Tests use disposable Git repositories and fake container/reviewer/scanner commands where appropriate. They cover lifecycle preservation, routing, scan failures, reviewer output, source changes during review and readiness. Live smoke testing has also exercised the installed scanners and both authenticated CLI reviewer routes on a disposable fixture. That does not replace each application's own checks.

## More detail

- [Standard skill workflow](WORKFLOW.md)
- [One-window, two-agent Devin test](DEVIN-TEST.md)
- [Agetor kanban setup and dependency pilot](AGETOR.md)
- [Ticket lifecycle and recovery](TICKETS.md)
- [Devin workspace/container controls](DEVIN.md)
- [Agent command contract](skills/flow-task/references/commands.md)

