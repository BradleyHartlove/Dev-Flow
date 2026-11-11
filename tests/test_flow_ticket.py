import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


SCRIPT = Path(__file__).parents[1] / "scripts/flow_ticket.py"
SPEC = importlib.util.spec_from_file_location("flow_ticket", SCRIPT)
ticket = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ticket)


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], check=True, text=True,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout.strip()


class TicketTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="flow-ticket-test-")
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name).resolve()
        self.repo = self.base / "repo with spaces"
        self.repo.mkdir()
        git(self.repo, "init", "-b", "main")
        git(self.repo, "config", "user.name", "Flow Test")
        git(self.repo, "config", "user.email", "flow-test@example.invalid")
        (self.repo / ".devcontainer").mkdir()
        (self.repo / ".devcontainer/devcontainer.json").write_text('{"image":"fixture-only"}')
        (self.repo / ".gitignore").write_text(".dev-flow/\ncache/\n.env\nlink\n")
        (self.repo / "app.txt").write_text("base\n")
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-m", "fixture: initial")
        self.home = self.base / "manager"
        self.primary, self.common, self.directory = ticket.identity(self.repo, self.home)
        self.calls = []
        self.runner = patch.object(ticket, "container", side_effect=self.fake_container)
        self.runner.start()
        self.addCleanup(self.runner.stop)
        self.profile = ticket.setup(self.primary, self.common, self.directory)

    def fake_container(self, root, action):
        self.calls.append((Path(root), action))
        if action == "up":
            path = Path(root) / ".dev-flow/container.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps({"workspace": str(root), "container_id": "fixture123"}))

    def begin(self, name="t5"):
        return ticket.start(self.directory, self.profile, name, fetch=False)

    def load(self, name="t5"):
        return ticket.load_ticket(self.directory, self.profile, name)

    def test_start_finish_resume_preserves_commits_reports_ignored_files_and_symlinks(self):
        state = self.begin()
        root = Path(state["worktree"])
        (root / "app.txt").write_text("implemented\n")
        git(root, "add", "app.txt")
        git(root, "commit", "-m", "feat: implement fixture")
        head = git(root, "rev-parse", "HEAD")
        report = root / ".dev-flow/task/REVIEW.md"
        report.parent.mkdir(parents=True)
        report.write_text("review evidence\n")
        (root / ".env").write_text("LOCAL_SETTING=fixture\n")
        (root / "cache").mkdir()
        (root / "cache/result").write_text("keep me")
        (root / "link").symlink_to("cache/result")
        state_path, state = self.load()
        ticket.finish(self.directory, state_path, state)
        self.assertFalse(root.exists())
        self.assertFalse(Path(state["workspace"]).exists())
        self.assertEqual(git(self.repo, "rev-parse", "flow/t5"), head)
        self.assertEqual((self.repo / "app.txt").read_text(), "base\n")
        archive = Path(state["archive"])
        self.assertEqual((archive / "ignored/.dev-flow/task/REVIEW.md").read_text(), "review evidence\n")
        ticket.activate(self.directory, state_path, state)
        self.assertEqual(git(root, "rev-parse", "HEAD"), head)
        self.assertEqual(report.read_text(), "review evidence\n")
        self.assertEqual((root / ".env").read_text(), "LOCAL_SETTING=fixture\n")
        self.assertTrue((root / "link").is_symlink())
        self.assertEqual(os.readlink(root / "link"), "cache/result")
        self.assertEqual(self.calls[-1], (root, "up"))

    def test_repeated_start_preserves_dirty_checkout_and_original_base(self):
        first = self.begin()
        root = Path(first["worktree"])
        (root / "app.txt").write_text("in progress")
        second = self.begin()
        self.assertEqual(first["base_commit"], second["base_commit"])
        self.assertEqual(first["worktree"], second["worktree"])
        self.assertEqual((root / "app.txt").read_text(), "in progress")
        self.assertEqual(len(ticket.worktrees(self.repo)), 2)

    def test_workflow_progress_is_distinct_from_container_lifecycle(self):
        state = self.begin()
        path, state = self.load()
        self.assertEqual(ticket.workflow_status(path, state)["stage"], "not-started")
        ticket.write_json(path.parent / "pipeline/STATUS.json", {
            "workspace": state["worktree"], "stage": "reviewing", "summary": "Codex reviewing"})
        progress = ticket.workflow_status(path, state)
        self.assertEqual(state["stage"], "ready")
        self.assertEqual(progress["stage"], "reviewing")
        state["stage"] = "finished"
        self.assertEqual(ticket.workflow_status(path, state)["stage"], "complete")

    def test_finish_refuses_staged_unstaged_and_untracked_changes_before_stopping(self):
        state = self.begin()
        root = Path(state["worktree"])
        path, state = self.load()
        for kind in ("unstaged", "staged", "untracked"):
            with self.subTest(kind=kind):
                if kind == "untracked":
                    (root / "new.txt").write_text("untracked")
                else:
                    (root / "app.txt").write_text("dirty")
                    if kind == "staged":
                        git(root, "add", "app.txt")
                with self.assertRaisesRegex(ticket.TicketError, "uncommitted or untracked"):
                    ticket.finish(self.directory, path, state)
                self.assertTrue(root.exists())
                self.assertFalse(any(action == "stop" for _, action in self.calls))
                if kind == "untracked":
                    (root / "new.txt").unlink()
                else:
                    git(root, "restore", "--staged", "--worktree", "app.txt")

    def test_finish_stop_failure_preserves_checkout(self):
        state = self.begin()
        path, state = self.load()
        with patch.object(ticket, "container", side_effect=subprocess.CalledProcessError(1, ["fixture"])):
            with self.assertRaises(subprocess.CalledProcessError):
                ticket.finish(self.directory, path, state)
        self.assertTrue(Path(state["worktree"]).exists())

    def test_finish_detects_ignored_file_changes_while_stopping(self):
        state = self.begin()
        root = Path(state["worktree"])
        (root / ".env").write_text("before")
        path, state = self.load()
        with patch.object(ticket, "container", side_effect=lambda *_: (root / ".env").write_text("after")):
            with self.assertRaisesRegex(ticket.TicketError, "changed during archival"):
                ticket.finish(self.directory, path, state)
        self.assertTrue(root.exists())
        self.assertEqual((root / ".env").read_text(), "after")

    def test_finish_is_idempotent_and_retains_branch(self):
        self.begin()
        path, state = self.load()
        ticket.finish(self.directory, path, state)
        archive = state["archive"]
        ticket.finish(self.directory, path, state)
        self.assertEqual(state["archive"], archive)
        self.assertEqual(len([c for c in self.calls if c[1] == "stop"]), 1)
        self.assertTrue(git(self.repo, "rev-parse", "flow/t5"))

    def test_failed_container_start_keeps_worktree_and_can_resume(self):
        with patch.object(ticket, "container", side_effect=subprocess.CalledProcessError(1, ["fixture"])):
            with self.assertRaisesRegex(ticket.TicketError, "retained"):
                self.begin()
        path, state = self.load()
        self.assertEqual(state["stage"], "start-failed")
        self.assertTrue(Path(state["worktree"]).exists())
        with self.assertRaisesRegex(ticket.TicketError, "no verified container record"):
            ticket.finish(self.directory, path, state)
        ticket.activate(self.directory, path, state)
        self.assertEqual(state["stage"], "ready")

    def test_wrong_branch_or_tampered_record_cannot_be_finished(self):
        state = self.begin()
        path, state = self.load()
        git(state["worktree"], "checkout", "-b", "unrelated")
        with self.assertRaisesRegex(ticket.TicketError, "branch changed"):
            ticket.finish(self.directory, path, state)
        state["worktree"] = str(self.repo)
        ticket.write_json(path, state)
        with self.assertRaisesRegex(ticket.TicketError, "identity/path mismatch"):
            self.load()
        self.assertFalse(any(action == "stop" for _, action in self.calls))

    def test_existing_unmanaged_branch_is_not_adopted_or_reset(self):
        git(self.repo, "branch", "flow/t5")
        head = git(self.repo, "rev-parse", "flow/t5")
        with self.assertRaisesRegex(ticket.TicketError, "already exists"):
            self.begin()
        self.assertEqual(git(self.repo, "rev-parse", "flow/t5"), head)
        self.assertEqual(self.calls, [])

    def test_restore_refuses_overwrite_and_path_traversal(self):
        self.begin()
        path, state = self.load()
        root = Path(state["worktree"])
        (root / ".env").write_text("saved")
        ticket.finish(self.directory, path, state)
        git(self.repo, "worktree", "add", str(root), state["branch"])
        (root / ".env").write_text("new local edit")
        with self.assertRaisesRegex(ticket.TicketError, "overwrite"):
            ticket.restore_files(self.directory, state)
        self.assertEqual((root / ".env").read_text(), "new local edit")
        for relative in (Path(".."), Path("."), Path("/tmp/outside"), Path(".git")):
            with self.assertRaises(ticket.TicketError):
                ticket.local_path(root, relative)

    def test_repo_lock_and_workspace_tasks_are_explicit(self):
        with ticket.locked(self.directory):
            with self.assertRaisesRegex(ticket.TicketError, "Another ticket"):
                with ticket.locked(self.directory):
                    pass
        config = json.loads((self.directory / "repo.code-workspace").read_text())
        tasks = config["tasks"]["tasks"]
        self.assertEqual([t["label"] for t in tasks], [
            "Ticket: Start", "Ticket: Resume", "Ticket: Finish", "Ticket: List"])
        for task in tasks:
            self.assertEqual([v["value"] for v in task["args"][:2]], ["--repo", str(self.repo)])
            self.assertEqual(task["command"]["quoting"], "strong")
            self.assertTrue(all(v["quoting"] == "strong" for v in task["args"]))
            self.assertNotIn("runOptions", task)

    def test_failed_worktree_creation_can_be_retried_without_losing_record(self):
        original_git = ticket.git
        def fail_creation(repo, *args):
            if args[:2] == ("worktree", "add"):
                raise subprocess.CalledProcessError(1, ["git", *args])
            return original_git(repo, *args)
        with patch.object(ticket, "git", side_effect=fail_creation):
            with self.assertRaises(subprocess.CalledProcessError):
                self.begin()
        path, state = self.load()
        self.assertEqual(state["stage"], "creating")
        ticket.activate(self.directory, path, state)
        self.assertEqual(state["stage"], "ready")

    def test_interrupted_resume_keeps_restoration_intent(self):
        state = self.begin()
        root = Path(state["worktree"])
        (root / ".env").write_text("preserve after interruption")
        path, state = self.load()
        ticket.finish(self.directory, path, state)
        with patch.object(ticket, "restore_files", side_effect=RuntimeError("interrupted")):
            with self.assertRaises(RuntimeError):
                ticket.activate(self.directory, path, state)
        path, saved = self.load()
        self.assertTrue(saved["restore_pending"])
        ticket.activate(self.directory, path, saved)
        self.assertEqual((root / ".env").read_text(), "preserve after interruption")

    def test_open_failure_does_not_remove_prepared_checkout(self):
        argv = ["--repo", str(self.repo), "--home", str(self.home), "start", "t5", "--no-fetch", "--open"]
        with patch.object(ticket, "open_workspace", side_effect=OSError("editor unavailable")), \
             contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(ticket.main(argv), 1)
        _, state = self.load()
        self.assertEqual(state["stage"], "ready")
        self.assertTrue(Path(state["worktree"]).is_dir())

    def test_finish_open_returns_to_the_permanent_repo_workspace(self):
        self.begin()
        argv = ["--repo", str(self.repo), "--home", str(self.home), "finish", "t5", "--open"]
        with patch.object(ticket, "open_workspace") as opener, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(ticket.main(argv), 0)
        opener.assert_called_once_with(self.directory / "repo.code-workspace")

    def test_git_locked_worktree_is_never_force_removed(self):
        state = self.begin()
        path, state = self.load()
        git(self.repo, "worktree", "lock", state["worktree"])
        with self.assertRaises(subprocess.CalledProcessError):
            ticket.finish(self.directory, path, state)
        self.assertTrue(Path(state["worktree"]).is_dir())
        self.assertTrue(git(self.repo, "rev-parse", state["branch"]))

    def test_interrupted_finish_can_complete_after_worktree_removal(self):
        self.begin()
        path, state = self.load()
        save = ticket.save_state
        def interrupted(path, state, stage=None):
            if stage == "finished":
                raise RuntimeError("interruption after remove")
            return save(path, state, stage)
        with patch.object(ticket, "save_state", side_effect=interrupted):
            with self.assertRaises(RuntimeError):
                ticket.finish(self.directory, path, state)
        path, saved = self.load()
        self.assertEqual(saved["stage"], "finishing")
        self.assertFalse(Path(saved["worktree"]).exists())
        ticket.finish(self.directory, path, saved)
        self.assertEqual(saved["stage"], "finished")

    def test_symlinked_manager_ancestor_is_rejected(self):
        outside = self.base / "outside"
        outside.mkdir()
        (self.directory / "worktrees").symlink_to(outside, target_is_directory=True)
        with self.assertRaisesRegex(ticket.TicketError, "symlinks"):
            self.begin()
        self.assertEqual(list(outside.iterdir()), [])

    def test_remote_base_is_fetched_without_changing_primary_checkout(self):
        remote = self.base / "origin.git"
        remote.mkdir()
        git(remote, "init", "--bare", "-b", "main")
        git(self.repo, "remote", "add", "origin", str(remote))
        git(self.repo, "push", "-u", "origin", "main")
        other = self.base / "other"
        subprocess.run(["git", "clone", "--local", str(remote), str(other)], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        git(other, "config", "user.name", "Flow Test")
        git(other, "config", "user.email", "flow-test@example.invalid")
        (other / "remote.txt").write_text("new upstream")
        git(other, "add", ".")
        git(other, "commit", "-m", "feat: upstream fixture")
        git(other, "push", "origin", "main")
        old_head = git(self.repo, "rev-parse", "HEAD")
        expected = git(other, "rev-parse", "HEAD")
        state = ticket.start(self.directory, self.profile, "fresh", base="origin/main")
        self.assertEqual(state["base_commit"], expected)
        self.assertEqual(git(self.repo, "rev-parse", "HEAD"), old_head)

    def test_real_cli_with_fake_container_tools(self):
        commands = self.base / "commands"
        commands.mkdir()
        docker_state = self.base / "docker.json"
        shim = '''#!/usr/bin/env python3
import json, os
from pathlib import Path
import sys
p = Path(os.environ['FLOW_FIXTURE_DOCKER'])
args = sys.argv[1:]
if Path(sys.argv[0]).name == 'devcontainer':
    root = args[args.index('--workspace-folder') + 1]
    mounts = [args[i + 1] for i, value in enumerate(args) if value == '--mount']
    info = {'Id': 'abc123fixture', 'State': {'Running': True}, 'Mounts': []}
    for mount in mounts:
        parts = dict(value.split('=', 1) for value in mount.split(','))
        info['Mounts'].append({'Type': 'bind', 'Source': parts['source'], 'Destination': parts['target'], 'RW': True})
    p.write_text(json.dumps(info))
    print(json.dumps({'outcome': 'success', 'containerId': 'abc123fixture', 'remoteWorkspaceFolder': root, 'remoteUser': 'fixture'}))
elif args[0] == 'inspect':
    print(json.dumps([json.loads(p.read_text())]))
elif args[0] == 'stop':
    info = json.loads(p.read_text())
    info['State']['Running'] = False
    p.write_text(json.dumps(info))
else:
    sys.exit(2)
'''
        for name in ("docker", "devcontainer"):
            executable = commands / name
            executable.write_text(shim)
            executable.chmod(0o755)
        env = os.environ.copy()
        env["PATH"] = str(commands) + os.pathsep + env["PATH"]
        env["FLOW_FIXTURE_DOCKER"] = str(docker_state)
        argv = [sys.executable, str(SCRIPT), "--repo", str(self.repo), "--home", str(self.home)]
        for command in (["start", "cli-test", "--no-fetch"], ["status", "cli-test"],
                        ["finish", "cli-test"], ["resume", "cli-test"], ["list"]):
            result = subprocess.run([*argv, *command], env=env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        _, state = self.load("cli-test")
        self.assertEqual(state["stage"], "ready")
        self.assertEqual(git(state["worktree"], "branch", "--show-current"), "flow/cli-test")
        self.assertTrue(json.loads(docker_state.read_text())["State"]["Running"])

    def test_rejects_sibling_mounts_and_unsafe_names(self):
        (self.repo / ".devcontainer/devcontainer.json").write_text(
            '{"mounts":["source=${localWorkspaceFolder}/../aictl,target=/aictl,type=bind"]}')
        with self.assertRaisesRegex(ticket.TicketError, "sibling"):
            ticket.check_config(self.repo)
        for name in ("../outside", "/absolute", "UPPER", "", "-option", "foo.lock", "foo..bar", "foo."):
            with self.assertRaises(ticket.TicketError):
                ticket.valid_name(name)

    def test_start_uses_main_instead_of_the_current_release_branch(self):
        expected = git(self.repo, "rev-parse", "main")
        git(self.repo, "checkout", "-b", "release")
        (self.repo / "app.txt").write_text("release only")
        git(self.repo, "commit", "-am", "chore: release fixture")
        state = self.begin()
        self.assertEqual(state["base_commit"], expected)
        self.assertEqual(git(self.repo, "branch", "--show-current"), "release")


if __name__ == "__main__":
    unittest.main()
