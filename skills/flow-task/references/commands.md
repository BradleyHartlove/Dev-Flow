# Local execution contract

Locate the installed checkout with `flow-pipeline paths`. Tools live in its scripts directory. If a command is missing from PATH but the installation path is known, call its matching Python script directly with python3; do not ask the user to rewrite their feature prompt. Use explicit worktree paths because the conversation can remain in a control workspace.

```sh
flow-ticket --repo REPO setup
flow-ticket --repo REPO start NAME --open
flow-ticket --repo REPO start CHILD --base flow/PARENT --open
flow-ticket --repo REPO status NAME
flow-ticket --repo REPO list
flow-container --workspace WORKTREE status
flow-container --workspace WORKTREE exec -- make test
flow-pipeline --workspace WORKTREE init --author claude
flow-pipeline --workspace WORKTREE status
flow-pipeline --workspace WORKTREE stage implementing --summary "Implementing the accepted approach"
flow-pipeline --workspace WORKTREE check baseline
flow-pipeline --workspace WORKTREE check final
flow-pipeline --workspace WORKTREE review
flow-pipeline --workspace WORKTREE stage ready-for-human --summary "Checks and independent review complete"
```

flow-ticket start sets up the repo if needed, pins the base, fetches a remote-tracking base for a new ticket, creates worktree/workspace and starts its container. Existing tickets resume without resetting files or repinning. Use resume after failed startup. Stacking with --base flow/PARENT includes only committed prerequisite work: the user must commit it first. Never treat an unmet dependency as ready.

flow-pipeline init returns record_directory. Managed tickets store it under `dev-flow/tickets/REPO-IDENTITY/records/NAME/pipeline`, outside scanned source and retained across Finish. Intentionally resumed unmanaged checkouts require --base COMMIT; records live under dev-flow/runs. --ticket-home PATH supports alternate manager homes. Keep the returned absolute path; do not guess old .dev-flow task paths.

Work stages: planning, waiting-decision, implementing, checking, reviewing, fixing, ready-for-human, blocked, complete. Manager ready/starting/finished describe environment lifecycle. flow-ticket list/status expose both. Native Devin session titles/columns are not automatically changed.

The baseline scan is recorded once. Every final scan/review has a retained run directory. Scans run Semgrep CE (p/default, metrics off, failing exit on findings) and Gitleaks (working files, redacted reports; task commit range when present). Both run even if one fails. Rule downloads/scan errors stay errors. Finding IDs are rule/path/line; shifted lines can conservatively look new. Investigate rather than replacing the original baseline. Logs/reports stay local, private, and outside scanned source.

Reviews use fresh codex exec read-only or claude -p with read tools and external tools disabled. Required container tests belong to author evidence. The wrapper writes REVIEW.md, persists the outcome, and checks source/index stayed unchanged. No permission-bypass flags, new API keys, or billing changes. Default run timeout is 900 seconds. Timeouts/auth failures are incomplete, not clean.

CHECKS.md records actual project commands, exits, results, log paths and gaps. Readiness enforces scanner/reviewer freshness but cannot prove tests ran merely because CHECKS.md exists: inspect logs. Unchanged historical findings remain disclosed to the human. They are not silently suppressed or called a clean scan.

The manager locks lifecycle changes; the pipeline locks checks/reviews. These do not stop arbitrary external writers. Keep one writer per checkout and pause it during review. Do not stop/rebuild/finish while another agent/app still uses the environment. A worktree is not a security sandbox.
