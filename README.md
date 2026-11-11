# dev-flow

A local development workflow for people who want to manage coding agents while staying responsible for the result. Describe the feature or ticket; the agent handles its checkout, development container, checks, security scans, independent review and handoff back to you.

You make the important decisions, review the final diff, stage files, make the Git commit and open the PR/MR yourself.

The current setup targets **macOS, Claude Code and Codex CLI**, with Devin Desktop for the editor workflow or Agetor for a kanban board. Agents run on the Mac; project builds, tests and dependency commands run in dev containers. Your Git hosting service does not need an integration.

## What it includes

| Tool | Responsibility |
| --- | --- |
| `flow-ticket` | Create/resume a ticket branch, isolated Git worktree, editor workspace and container; archive a clean ticket later. |
| `flow-container` | Start, inspect, rebuild, stop and execute commands in the recorded container, with mounts that keep linked worktrees usable. |
| `flow-pipeline` | Persist work stages, run Semgrep/Gitleaks, dispatch the other provider for review and check readiness for human review. |
| `flow-workspace` | Generate a standalone local editor workspace for an existing checkout. Useful without the ticket manager. |
| `flow-board` | Optional Agetor kanban adapter: list board/ticket IDs and review commands, open review workspaces, dispatch independent tickets and hold dependent work until a prerequisite is manually committed and accepted. |
| Five `flow-*` skills | Tell the author and reviewer how to use these tools consistently. |

Devin can be the conversation and monitoring surface; Agetor adds cards and dependency-aware dispatch through flow-board. The helpers are ordinary local Python programs, and the skills are Markdown instructions shared by Claude and Codex.

## Requirements

- macOS, plus Devin Desktop for the documented editor workflow or Agetor and its CLI for the optional board. Windows is unsupported; non-macOS editor opening is not implemented.
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

### 1. Plan when the work needs it

Start an author conversation in Devin against the relevant repo or control workspace. For a broad workstream:

```text
Use flow-plan for this feature: [requirements or a path to the working plan].
```

The skill investigates the code, brings you meaningful decisions and produces dependency-ordered tickets. Small, well-defined work can go straight to implementation.

### 2. Give the author a ticket

Use either Claude Agent or Codex Agent:

```text
Use flow-task to implement T5 from this plan: /absolute/path/to/PLAN.md.
```

Or describe a small feature directly. You do not need to repeat the container, scanning or handoff procedure.

`flow-task` creates/resumes the managed ticket environment, reads repo instructions, records a baseline, implements the agreed scope, runs project checks in its container and runs the local scanners. It pauses source writes and starts a fresh reviewer automatically:

| Author | Automatic reviewer |
| --- | --- |
| Claude | Codex CLI |
| Codex | Claude Code CLI |

The author handles confirmed findings and focused re-review, then prepares a debrief and human acceptance packet. Routine fix/re-review is bounded to two cycles; unresolved decisions or failures return to you with evidence.

### 3. Monitor and make decisions

Follow the author in Devin. The background reviewer reports through the ticket's artifacts and author conversation; it does **not** automatically appear as a separate native Devin session.

```sh
flow-ticket --repo ~/code/my-app list
flow-ticket --repo ~/code/my-app status ticket-name
```

Environment lifecycle and work stage are separate. A container can be `ready` while work is `implementing`, `reviewing`, `blocked` or `ready-for-human`.

You can also create a permanent local control workspace:

```sh
flow-ticket --repo ~/code/my-app setup --open
```

Open workspace files in Devin's **IDE view** to load their tasks, then use **Cmd+Shift+P → Tasks: Run Task**. Selecting an agent conversation's folder is not the same as opening an editor workspace. Opening a ticket workspace does not automatically retarget an existing agent session; the skill uses explicit checkout paths.

### 4. Review and commit by hand

At `ready-for-human`, inspect the diff, checks, independent findings and debrief. Stage files, commit, push and open the PR/MR using your normal tools.

The skills do not stage, commit, push, create PRs, merge or deploy for you. A clean agent review is evidence for your decision, not your acceptance.

### 5. Finish or resume

After your manual commit, with agents and application processes idle:

```text
Use flow-finish for ticket-name.
```

Or use the manager directly:

```sh
flow-ticket --repo ~/code/my-app finish ticket-name --open
flow-ticket --repo ~/code/my-app resume ticket-name --open
```

Finish refuses uncommitted/untracked source changes. It archives ignored local artifacts, stops the recorded container and removes the clean worktree without force. The branch and commits remain. It does not require the branch to be pushed or merged.

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
- [Agetor kanban setup and dependency pilot](AGETOR.md)
- [Ticket lifecycle and recovery](TICKETS.md)
- [Devin workspace/container controls](DEVIN.md)
- [Agent command contract](skills/flow-task/references/commands.md)

