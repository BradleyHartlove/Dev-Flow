# Agetor board adapter

flow-board connects the existing flow to an actual local kanban board. Agetor owns cards and agent sessions. flow-ticket owns the branches/worktrees/containers. Each card uses Agetor isolation `none` and is pointed at its own verified manager-owned checkout before the worker starts. This avoids nested checkouts and keeps the existing lifecycle and review helpers.

## Setup

Install Agetor and its CLI, connect Claude Code/Codex, and run `python3 scripts/install_flow.py` in this checkout to install flow-board alongside the other commands. Keep the Agetor app/core running. The adapter uses the official CLI with `--no-daemon`; it does not read app tokens or edit its database.

Create a Git baseline commit in the application repo by hand. The adapter requires an existing HEAD. Check its root devcontainer configuration and make sure the Docker backend is running.

## Ticket graph

A plan contains `max_parallel` and a `tickets` list. Each ticket has `id`, `title`, `description`, optional `harness` (`claude-code` or `codex`), optional `model` and `effort`, and a `requires` list. Set an explicit effort for Codex models that require it. Requirements belong in description; the adapter and skills supply operating instructions.

See [the inventory pilot](examples/inventory-pilot.json). It has two independent tickets, search and health, and a stock-filter ticket that depends on search. Search uses Claude with a Codex reviewer; health uses Codex with a Claude reviewer. Adjust model names to ones available in your installed harness and subscription.

```sh
flow-board init inventory-pilot \
  --repo ~/code/inventory-repo-testing \
  --plan /path/to/dev-flow/examples/inventory-pilot.json

flow-board watch inventory-pilot
```

Init creates parked cards without starting agents or containers. Watch prepares ready tasks, starts their agents and publishes broad workflow transitions to board columns. Planning, coding, tests, scans, AI review and routine fixes all stay Running. Review means ready for the human. Blocked means a dependency, an ended worker, or a question requiring attention. Detailed internal stages remain in the ticket record. The dispatcher publishes a column transition once; it does not continually reset native or manually moved columns. The plan's concurrency limit counts active card workers, including authors waiting on their automatic reviewer. Independent tickets receive separate manager worktrees and containers.

Init prints the board name, every ticket ID/title/dependency, and the exact watch/open commands. It also saves those commands in `boards/NAME/BOARD.md`, visible in the review launcher. Agetor card titles begin with `[BOARD/TICKET]`, for example `[inventory-pilot/search]`. These local IDs are distinct from Agetor's generated UUIDs.

At any time, run `flow-board` or `flow-board list` to see all board names, ticket IDs, titles, states and review commands. No filesystem search or JSON inspection is needed. `flow-board status NAME` shows the same readable view for one board; add `--json` to status/list for machine-readable records. Listing works without Agetor running and does not dispatch work.

Watch runs in the foreground; keep its terminal/process alive. Ctrl+C stops dispatching and leaves existing agents and containers running. It can be restarted with the same command. `flow-board tick NAME` performs one scheduling/synchronization pass. This is a local coordinator, not an automatically installed login service.

## How acceptance releases dependent work

Open a prepared ticket in its own Devin IDE window:

```sh
flow-board open inventory-pilot search
flow-board open inventory-pilot health
```

To use a task menu instead, run `flow-board open inventory-pilot`. This opens a local review-launcher workspace. In its IDE view, choose **Cmd+Shift+P → Tasks: Run Task → Review: Open …** for the ticket you want. Each task opens that ticket's existing workspace in a separate window. The launcher shows board records, not an application checkout; review and commit in the ticket window it opens. Reopen the launcher through Devin's Open Recent menu.

In the ticket window, use **Cmd+Shift+G** for Source Control or **Git: Open All Changes** from the command palette. The existing ticket tasks still provide container controls. Opening for review does not start agents, change board columns or start/rebuild containers. Unprepared or archived tickets produce an error rather than creating a checkout. Add `--print-path` to print the workspace location without opening Devin. Agetor need not be running for this command.

1. The author implements, checks, scans and gets independent review, then reaches ready-for-human. The card appears in Review. Automatic AI review remains part of Running.
2. Inspect the result, then stage and make the final commit yourself in the printed ticket worktree. Open any PR/MR manually.
3. After the worker finishes, move the card to Done in Agetor.
4. The dispatcher checks that the worker is idle, Git is clean, the commit descends from the pinned base, and its source content still matches the reviewed/scanned source. It records that immutable accepted commit.
5. A dependent ticket starts from that commit, not stale main. No merge or prerequisite commit is created for you.

Moving an uncommitted or unverified card to Done does not release dependencies. The card stays where you put it; the dispatcher records and prints why acceptance is pending. Read the reason with `flow-board status NAME`, address it, and acceptance is checked again while the card is Done. You can also move it back yourself. Staging/committing alone does not invalidate an otherwise unchanged source review; additional unreviewed source changes do.

Do not use Agetor's Commit & push action with this workflow. The user owns commits, PRs and integration. Marking Done does not run flow-ticket Finish or remove the checkout; use flow-finish separately once no dependent/worker needs it.

## Status and recovery

```sh
flow-board status inventory-pilot
flow-ticket --repo ~/code/inventory-repo-testing list
flow-ticket --repo ~/code/inventory-repo-testing status inventory-pilot-search
```

Board state is private and ignored under `boards/NAME/state.json`. It links native card IDs to stable manager ticket names, pinned bases, pipeline records and accepted commits. No GitLab integration is needed.

Startup errors leave a card Blocked and preserve its checkout; the dispatcher does not loop automatic startup retries. After correcting the problem:

```sh
flow-board retry inventory-pilot search
```

An active worker or pending native question must be answered/stopped first; Retry will not duplicate it. Resume uses the existing agent conversation when available. If a watch process stopped during startup, the saved starting state can be explicitly retried. Native permission/question cards remain Blocked while waiting for the user.

In Agetor 1.2.0, Claude startup fails if its session log does not appear within 30 seconds. A synchronous user SessionStart hook can cause this delay. Inspect the card's logs before retrying; a nonessential status-display hook may be suitable for Claude's `async: true` hook option. Do not disable permission or security hooks to work around startup. The adapter returns an idle failed card to Ready before calling Start, as the CLI otherwise refuses a Blocked card.

## Current limits

- The adapter supports zero or one prerequisite branch per ticket. Multiple prerequisite branches need a manually prepared integration base; there is no automatic multi-branch merge or rebase.
- Concurrency is per plan, not a machine-wide resource allocator. Multiple watchers should not be used as a way to exceed the intended limit.
- Manually running parked placeholder cards bypasses the normal dispatcher entry point. They start in Plan mode and instruct the agent to wait for the prepared checkout. Use Watch to launch implementation.
- Cards get their checkout only when eligible. Agetor may show these managed directories as separate project folders; use All projects to see the pilot together.
- Workspaces, records and runtime state are local to this machine. The shared plan/adapter are portable; the ignored state is not.
- Native card completion is not a clean review. The pipeline's evidence and the user's final acceptance determine readiness.

The pilot is complete when both independent cards have run concurrently in different worktrees/containers, their checks/scans/reviews are inspectable, and the dependent card waits for and then starts from the user's accepted prerequisite commit.
