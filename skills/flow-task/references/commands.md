# Local execution contract

Locate the installed checkout with `flow-pipeline paths`. Tools live in its scripts directory. If a command is missing from PATH but the installation is known, call its matching Python script with python3. The user supplies the feature; the agent operates the helper commands.

## Selected worktree

Devin owns new author worktrees. Use the session's actual working directory and verify it is a registered linked worktree, separate from the primary checkout and other writers. Inspect the actual branch, common Git directory, HEAD and status; do not infer ownership from the folder name. A session still in the primary checkout needs the user to select/start Worktree mode in Devin before implementation. Do not create a replacement checkout or open another window.

For a new, clean Devin worktree, pin its current HEAD before editing. Devin may have made an empty snapshot commit, so compare actual source/ancestry rather than requiring independent worktrees to have identical hashes. Preserve these snapshots and distinguish them from manual user acceptance. For a resume, use the base already saved in STATUS.json/TASK.md, even if HEAD changed after a manual commit. An earlier baseline cannot be reconstructed from a dirty checkout. Never overwrite another task's records or repin a resumed task.

```sh
git -C WORKTREE worktree list --porcelain
git -C WORKTREE rev-parse --show-toplevel --git-common-dir
git -C WORKTREE branch --show-current
git -C WORKTREE rev-parse HEAD
git -C WORKTREE status --short
flow-container --workspace WORKTREE up
flow-container --workspace WORKTREE status
flow-pipeline --workspace WORKTREE init --author claude --base PINNED_COMMIT
flow-pipeline --workspace WORKTREE status
flow-container --workspace WORKTREE exec -- make test
flow-pipeline --workspace WORKTREE stage implementing --summary "Implementing the accepted approach"
flow-pipeline --workspace WORKTREE check baseline
flow-pipeline --workspace WORKTREE check final
flow-pipeline --workspace WORKTREE review
flow-pipeline --workspace WORKTREE stage ready-for-human --summary "Checks and independent review complete"
```

Use `--author codex` for Codex. Substitute the actual repo's check command for make test. Application builds, tests, dependency installation and servers run inside the recorded container. Local scanner/reviewer helpers run on the Mac. Do not reopen the control editor in the container or fall back to host project toolchains.

Inspect repository configuration/scripts for shared writable siblings, shared volumes, fixed container names and fixed published ports before parallel startup. Each active worktree needs an isolated writable environment. The helper adds worktree/common-Git mounts without editing shared devcontainer source; it does not automatically isolate every arbitrary compose/sibling configuration. Surface a missing recipe before sharing source between workers.

## Durable records and progress

flow-pipeline init returns record_directory. Devin-owned worktrees use records under dev-flow/runs, outside source. Their explicit --base is required; the helper does not guess a task base. Existing flow-ticket-owned checkouts retain their manager record and pinned base; the native flow does not adopt new checkouts into that manager. --ticket-home supports an existing alternate manager home. Keep the returned path rather than constructing it by hand.

TASK.md records requirements, decisions, checkout owner, branch, worktree/common Git identity, pinned base and container identity. CHECKS.md records actual check commands, exits, results, logs and gaps. HANDOFF.md anchors review, REVIEW.md captures findings, FIX.md records dispositions and DEBRIEF.md explains human acceptance. Link useful files in the Devin conversation; use its Changes view or Source Control for the selected worktree. Helpers do not rename native sessions or create visible reviewer sessions.

Persisted work stages: planning, waiting-decision, implementing, checking, reviewing, fixing, ready-for-human, blocked, complete. Report meaningful transitions in the author conversation. There is no board dispatcher in this workflow. The user starts top-level Devin sessions; agents must not create another scheduler or spawn duplicate writers.

## Verification and review

The baseline scan is recorded once. Wait for all baseline project checks and scans before editing. Every final scan/review retains its own run directory. Semgrep CE uses p/default, metrics off and failing exit on findings. Gitleaks scans working files with redacted reports and also the task commit range when commits exist. Both scanners run even if one fails. Download/parse/coverage errors remain gaps. Finding IDs include rule/path/line, so shifted lines may conservatively appear new; investigate rather than replacing the original baseline.

Reviews use fresh codex exec read-only or claude -p with read tools and external tools disabled. They inspect source and author evidence without rerunning project checks. No permission-bypass flags, new API keys or billing changes. The default timeout is 900 seconds. Timeouts/auth failures are incomplete, not clean. The wrapper writes REVIEW.md and rejects stale source/index evidence.

Readiness checks current-source review and scan evidence, but CHECKS.md alone cannot prove tests ran: inspect logs. Unchanged historical findings remain visible for human assessment. New findings and scanner errors block readiness. Pipeline/manager locks do not stop arbitrary external writers; keep one writer per checkout and pause it during review.

## Finish

The user stages, commits and opens merge requests manually. With explicit cleanup requested and workers idle, flow-finish stops only the selected Devin worktree's recorded container, retains external evidence and leaves worktree/branch removal to Devin and the user. For an existing manager-owned ticket only, it can use flow-ticket Finish without opening another window. Never stop/rebuild/finish while another agent or application uses that environment.
