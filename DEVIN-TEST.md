# Two-agent test in one Devin window

This is a user-run test of native Devin sessions plus the shared flow skills. The inventory repo remains untouched until you start implementation. No board, dispatcher, GitLab connection, extra IDE window or agent installation inside a container is required.

## 1. Open the clean primary repo

Close the old pilot workspace/windows. In one local Devin window, open `/Users/bradleyhartlove/code/inventory-repo-testing`. Keep it on main. Its known clean baseline is `baf46fe9863e53cb9962c29c812286d85a0fb618` (four existing API tests). Do not reopen the editor in a container.

In Devin's user settings, enable these existing Git settings if you want worktrees visible in Source Control:

```json
{
  "git.detectWorktrees": true,
  "git.showDevinWorktrees": true
}
```

No application repository configuration edit is needed. The session Changes view is the first review path; Source Control is the same-window fallback. Start fresh agent sessions so the updated skills load.

## 2. Optional: test the plan document first

Start a Claude or Codex planning conversation on the primary repo. Send:

> Use flow-plan to plan two independent tickets for this repo: GET /health returning {"status":"ok"}, and optional case-insensitive name search with q on GET /items. Include acceptance criteria and stop after planning.

The result should be a linked PLAN.md with the goal, design, decisions and a small ticket table. Open its link in Devin and choose Markdown preview (Open Preview to the Side is also available). This is the persistent planning document; the external agent does not automatically create a Claude-style interactive Artifact or a native Devin Local approval card. Planning should create no implementation worktrees or containers.

The next prompts specify the complete small features, so you do not need to copy generated IDs, board names or long plan paths for this test.

## 3. Start Health with Claude

In the same Devin window, create a new session for this repo. Select Worktree in the location picker and create a NEW worktree from the unchanged main baseline. Choose Claude Agent. If offered a name, use health-test; otherwise keep Devin's generated name and rename the session to Health test for readability. If you already created a clean native worktree/session, you can use that for Health instead of creating another one. Wait for Devin to finish preparing its working directory, then send:

> Use flow-task to add GET /health returning HTTP 200 with JSON {"status":"ok"}. Put the route in app/health.py and register it in app/main.py. Test repeated responses and that health requests do not change inventory. Preserve the existing item API and tests.

The skill supplies the container/scanning/review procedure. You should see an initial report of its actual worktree, branch, pinned base and container ID. It should use this selected checkout, create no nested checkout, and open no new window. It should run the existing four tests and baseline scans before editing.

If the location picker cannot create/select a separate worktree for this ACP agent, stop here and report that concrete UI issue. Do not send the implementation prompt to the primary checkout or create a hidden replacement session.

## 4. Start Search with Codex

While Health is running, create a second session in the SAME window. Choose Codex Agent and a different NEW worktree from unchanged main. Do not reuse Health's worktree or branch. Name the session Search test and send:

> Use flow-task to add an optional q query parameter to GET /items. Match item names by case-insensitive substring, preserve insertion order, and return every item when q is omitted or empty. Add focused tests and preserve POST validation and the existing tests.

Compare the two startup reports. They must show different worktree paths, different branches and different container IDs. Both should start with the original baseline source. Devin may create an empty snapshot commit per worktree, so their starting hashes can differ even when their source is identical; each agent must pin its own actual starting HEAD and preserve those snapshots. Health and Search may both edit app/main.py safely because their checkouts are separate. Do not start app servers for this test; only tests/checks run, so port forwarding is not needed.

## 5. Monitor in the same window

Use Devin's session sidebar to switch between Health and Search. You can drag one session onto another to try the documented side-by-side layout. Native session status shows activity/questions; the author conversation reports baseline, implementation, checks, independent review and ready-for-human stages.

You should not need to enter helper commands, launch a reviewer, move handoff files, start a scheduler or open another IDE window. Answer meaningful design or permission questions if they arise. Neither author should edit source while its baseline checks are still running or while its reviewer is inspecting the checkout.

The author/reviewer pairs are Claude -> Codex and Codex -> Claude. Review is read-only source/evidence review; it does not independently rerun the tests. It is a local background CLI process whose results are explained in the author conversation.

## 6. Review each result

When an author reaches ready-for-human, select that session and its Changes view. You should see its own files and diff beside the chat. The author should link REVIEW.md, DEBRIEF.md and changed source, and provide real check evidence. Health should include app/health.py and tests/test_health.py; Search should change the list handler and include focused search tests. Documentation changes are possible if justified. Neither worktree should contain the other feature.

If Changes is missing or stale, switch to IDE mode within the same window and use Cmd+Shift+G. Run Source Control: Focus on Repositories View if needed, select the reported worktree/branch and inspect its changed and untracked files. Do not switch the primary branch, merge work or open another window just to inspect a diff. If both sessions show the same worktree's changes, the UI/session binding has failed this test; stop and report it.

Each result needs passing final container tests, Semgrep and Gitleaks evidence, a clean other-provider review, a debrief and ready-for-human status. Baseline findings or material gaps must remain visible. Neither agent should stage files or create feature commits. Devin may create its own snapshot commits; those are editor bookkeeping and do not count as your manual acceptance. The agent should identify any such snapshots, preserve them, and report metadata changes that invalidate review evidence.

## 7. Manual acceptance and finish

After review, select the correct worktree repository in Source Control, confirm its branch and make its final commit yourself. Repeat for the other worktree. This trial leaves the two branches separate; it does not automatically merge their overlapping app/main.py edits into main. Do not use a Merge action as a substitute for reviewing integration.

In each task conversation, after its manual commit and once its workers are idle, send:

> Use flow-finish for this task. I reviewed and committed it; its workers are idle.

For a native worktree this stops only its recorded container and saves completion outside source. It leaves worktree/branch removal to you and Devin. Do not remove the worktree before container cleanup. You can keep the branches for inspection or request discarding the dummy trial separately.

## What counts as success

Observed in the first native UI trial: the two worktrees had real unstaged source changes, but both ACP Changes panes were empty. Sessions were grouped under separate checkout folders, and side-by-side placement was not confirmed. The native Changes/combined-session UI portion has therefore not passed. Review actual Git diffs in IDE Source Control; do not treat an empty session pane as evidence that code was not written. The Search worktree was created from the Health worktree's context, but both initial snapshot trees still matched the original baseline.

- One Devin window manages two independent native worktree sessions.
- Different checkouts/branches/containers protect concurrent writes; main remains unchanged.
- Both agents use the installed skills without repeated operating instructions.
- Baseline checks precede edits; final tests/scans and cross-provider reviews complete with inspectable evidence.
- You can follow progress and inspect each correct diff near its conversation without terminal/board/window hopping.
- You own final staging, commits and any later integration; native cleanup respects Devin ownership.

Helper tests validate native linked-worktree metadata, container mount arguments, isolated pipeline records and pinned bases. They do not prove ACP session creation, rendering or layout; those are what you are testing here. Container-specific debugging/IntelliSense is outside this trial and may still benefit from an attached editor later.
