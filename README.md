# dev-flow for Paradev and Linear

Plan with Claude Code in Paradev, hand off through Linear, and run each issue in its own Paradev Worktree. Claude Code handles implementation by default. Codex reviews changed behavior and regression coverage in two fresh sessions using your existing ChatGPT login. You decide what starts, test the result, and commit it.

## One-time setup

1. Install Paradev, sign in to Claude Code and Codex in local Paradev terminals, and connect the Linear plugin. The task picker can open a Linear issue as a workspace. The plugin gives the agents tools to create and update issues. Verify that the planner can read your intended project. [Paradev Linear integration](https://docs.paradev.com/use-with-linear) · [Linear plugin](https://docs.paradev.com/plugins/available/linear)
2. Install the Docker CLI and backend, the Dev Container CLI, Semgrep, Gitleaks, [OSV-Scanner v2](https://google.github.io/osv-scanner/installation/), and Python 3.9 or later. Your application repo needs a root `.devcontainer.json` or `.devcontainer/devcontainer.json`. Run `python3 scripts/install_flow.py` from this checkout. It installs both helpers into `~/.local/bin` and links the skills into Claude Code and Codex. Confirm `flow-container --help`, `flow-pipeline paths`, and `osv-scanner --version` work inside a Paradev terminal. See [Operating dev-flow](WORKFLOW.md#evidence-and-usage-limits) for the one-time OSV database setup.
3. In Paradev **Settings → Agent commands → Claude → Command**, enter the command printed by the installer. The command follows this format:

   ```sh
   claude --append-system-prompt-file /absolute/path/to/dev-flow/paradev/claude-instructions.txt
   ```

   Leave **Prompt-only args** and **Prompt transport** as they are. Start a fresh Claude session so the launch command takes effect. When you launch a linked Linear issue for implementation, Paradev supplies the issue prompt and Claude loads the [workflow instructions](paradev/claude-instructions.txt). [Paradev launch settings](https://docs.paradev.com/agent-integration) · [Claude Code CLI options](https://code.claude.com/docs/en/cli-reference)

Use `flow-plan` in your planning chat, or save the [planning prompt](paradev/planning-prompt.txt) for reuse. If you start an author session without a linked issue, provide the issue link. For Codex author sessions, ask it to use `flow-task`. Codex reviews launched by the pipeline need no Paradev configuration.

## Day-to-day workflow

1. In a Paradev Claude session, ask `flow-plan` to inspect the project and propose issues. Agree on the scope and which issues can run together. The planner files or reuses issues in the agreed Linear project and verifies the links.
2. In Paradev, run an eligible Linear issue on **This device** in a new **Worktree**. Use the issue's `fix/`, `feat/`, or `chore/` work branch and the intended base. The workspace name can be anything. If Paradev inherits a different branch from Linear, use the [exact-branch launch](WORKFLOW.md#work-branches). Run independent work in separate workspaces and start dependent work from the accepted prerequisite commit.
3. Follow the agent and its diff in Paradev. The author starts the container, tests before and after editing, runs Semgrep, Gitleaks, and OSV-Scanner, gets both review passes from the other provider, and updates the linked issue. Check the acceptance packet in the author session.
4. Test the result yourself and give feedback in the same workspace. After a manual commit, tell the author to use `flow-finish` to verify acceptance and update Linear. Ask it to stop the container before you archive the workspace in Paradev.

See [workflow and container details](WORKFLOW.md) and the [inventory pilot tickets](examples/inventory-pilot.json).

## Verify this checkout

```sh
python3 -m unittest discover -s tests
```

Tests use disposable Git repositories and fake checks/reviewers. Use a real Linear issue to verify your installed Paradev version passes the issue to Claude with the configured launch command, connects to Linear, and can run both authenticated CLIs.
