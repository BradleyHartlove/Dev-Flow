import importlib.util
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import call, patch


SPEC = importlib.util.spec_from_file_location("flow_board", Path(__file__).parents[1] / "scripts/flow_board.py")
board = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(board)


def row(key, requires=None, status="queued"):
    return {"id": key, "title": key, "description": "fixture", "requires": requires or [],
            "status": status, "card_id": "card-" + key}


class BoardTests(unittest.TestCase):
    def test_default_listing_exposes_board_ids_and_copyable_commands_without_agetor(self):
        with tempfile.TemporaryDirectory(prefix="boards with spaces ") as temporary:
            home = Path(temporary)
            state = {"name": "feature", "repo": "/repo", "tickets": [row("search"), row("stock", ["search"])]}
            board.save(home / "feature", state)
            before = (home / "feature/state.json").read_bytes()
            output = io.StringIO()
            with patch.object(board, "agetor") as native, contextlib.redirect_stdout(output):
                self.assertEqual(board.main(["--home", str(home)]), 0)
            text = output.getvalue()
            self.assertIn("Board: feature", text)
            self.assertIn("Depends on: search", text)
            self.assertIn(board.command_for(home / "feature", "open", "stock"), text)
            native.assert_not_called()
            self.assertEqual((home / "feature/state.json").read_bytes(), before)

    def test_empty_board_list_neither_creates_state_nor_contacts_agetor(self):
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary) / "unused"
            output = io.StringIO()
            with patch.object(board, "agetor") as native, contextlib.redirect_stdout(output):
                self.assertEqual(board.main(["--home", str(home), "list"]), 0)
            self.assertIn("No boards yet", output.getvalue())
            self.assertFalse(home.exists())
            native.assert_not_called()

    def test_status_and_list_keep_explicit_machine_readable_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary)
            state = {"name": "feature", "repo": "/repo", "tickets": [row("search")]}
            board.save(home / "feature", state)
            for command, expected in [(["status", "feature", "--json"], state), (["list", "--json"], [state])]:
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    self.assertEqual(board.main(["--home", str(home), *command]), 0)
                self.assertEqual(json.loads(output.getvalue()), expected)

    def test_initialization_labels_parked_cards_and_saves_discovery_commands(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary) / "feature"
            repo = Path(temporary) / "repo"
            repo.mkdir()
            calls = []
            def cli(*args):
                calls.append(args)
                if args[0] == "add":
                    return {"task": {"id": "card-" + str(len(calls))}}
                return {}
            plan = {"tickets": [row("search"), row("stock", ["search"])]}
            with patch.object(board.ticket, "git", side_effect=[str(repo), "b" * 40]), \
                 patch.object(board, "agetor", side_effect=cli), patch.object(board, "start_row") as start:
                board.initialize(directory, repo, plan, "feature")
            titles = [args[args.index("--title") + 1] for args in calls if args[0] == "add"]
            self.assertEqual(titles, ["[feature/search] search", "[feature/stock] stock"])
            self.assertTrue(all(args[0] in ("add", "move") for args in calls))
            self.assertIn(board.command_for(directory, "open", "search"), (directory / "BOARD.md").read_text())
            self.assertTrue((directory / "review.code-workspace").is_file())
            start.assert_not_called()

    def test_review_launcher_tasks_open_the_named_ticket_and_preserve_user_edits(self):
        with tempfile.TemporaryDirectory(prefix="board with spaces ") as temporary:
            directory = Path(temporary) / "pilot"
            state = {"name": "pilot", "tickets": [row("search"), row("health")]}
            workspace = board.review_workspace(directory, state)
            config = json.loads(workspace.read_text())
            tasks = config["tasks"]["tasks"]
            self.assertEqual([t["args"][-3:] for t in tasks],
                             [["open", "pilot", "search"], ["open", "pilot", "health"]])
            self.assertTrue(all(t["type"] == "process" for t in tasks))
            config["settings"]["editor.fontSize"] = 18
            workspace.write_text(json.dumps(config))
            board.review_workspace(directory, state)
            self.assertEqual(json.loads(workspace.read_text()), config)

    def test_open_print_path_does_not_start_workers_or_change_board_state(self):
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary)
            directory = home / "pilot"
            state = {"name": "pilot", "tickets": [row("search")]}
            board.save(directory, state)
            before = (directory / "state.json").read_bytes()
            with patch.object(board, "ticket_workspace", return_value=Path("/review/ticket.code-workspace")), \
                 patch.object(board.ticket, "open_workspace") as opener, \
                 patch.object(board, "agetor") as native, \
                 patch.object(board, "tick") as tick, contextlib.redirect_stdout(io.StringIO()):
                result = board.main(["--home", str(home), "open", "pilot", "search", "--print-path"])
            self.assertEqual(result, 0)
            opener.assert_not_called()
            native.assert_not_called()
            tick.assert_not_called()
            self.assertEqual((directory / "state.json").read_bytes(), before)

    def test_open_ticket_uses_separate_editor_window(self):
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary)
            board.save(home / "pilot", {"name": "pilot", "tickets": [row("search")]})
            workspace = Path("/review/ticket.code-workspace")
            with patch.object(board, "ticket_workspace", return_value=workspace), \
                 patch.object(board.ticket, "open_workspace") as opener, \
                 patch.object(board, "agetor") as native, contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(board.main(["--home", str(home), "open", "pilot", "search"]), 0)
            opener.assert_called_once_with(workspace, new_window=True)
            native.assert_not_called()

    def test_unprepared_ticket_cannot_be_started_by_open(self):
        with self.assertRaisesRegex(ValueError, "not been prepared"):
            board.ticket_workspace({"tickets": [row("stock")]}, "stock")

    def test_open_refuses_a_workspace_for_another_checkout(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "checkout"
            root.mkdir()
            record = Path(temporary) / "record"
            workspace = record / "ticket.code-workspace"
            item = {**row("search"), "manager_name": "pilot-search", "worktree": str(root),
                    "record_directory": str(record / "pipeline")}
            environment = {"repo": "/repo", "ticket": "pilot-search", "worktree": str(root),
                           "workspace": str(workspace), "branch": "flow/pilot-search"}
            board.ticket.write_json(record / "state.json", environment)
            board.ticket.write_json(workspace, {"folders": [{"name": "project", "path": "/other"}]})
            with patch.object(board.ticket, "verify_checkout"), self.assertRaisesRegex(ValueError, "points elsewhere"):
                board.ticket_workspace({"repo": "/repo", "tickets": [item]}, "search")

    def test_internal_review_and_fix_stages_do_not_move_a_running_card(self):
        item = {**row("a", status="working"), "worktree": "/fixture", "record_directory": "/records",
                "board_phase": "running"}
        state = {"max_parallel": 2, "tickets": [item]}
        detail = {"task": {"column": "running", "runId": "run"},
                  "runs": [{"id": "run", "status": "running"}]}
        with tempfile.TemporaryDirectory() as directory, patch.object(board, "agetor", return_value=detail), \
             patch.object(board, "board_column") as move, patch.object(board.pipeline, "load") as load:
            for phase in ["reviewing", "blocked", "fixing", "checking"]:
                load.return_value = {"stage": phase}
                board.tick(Path(directory), state)
        move.assert_not_called()

    def test_manual_column_move_is_not_reasserted_on_each_poll(self):
        item = {**row("a", status="working"), "worktree": "/fixture", "record_directory": "/records",
                "board_phase": "running"}
        state = {"max_parallel": 2, "tickets": [item]}
        detail = {"task": {"column": "review", "runId": "run"},
                  "runs": [{"id": "run", "status": "running"}]}
        with tempfile.TemporaryDirectory() as directory, patch.object(board, "agetor", return_value=detail), \
             patch.object(board, "board_column") as move, \
             patch.object(board.pipeline, "load", return_value={"stage": "checking"}):
            board.tick(Path(directory), state)
            board.tick(Path(directory), state)
        move.assert_not_called()

    def test_invalid_done_stays_put_and_does_not_release_dependency(self):
        item = row("a", status="review")
        state = {"max_parallel": 2, "tickets": [item, row("b", ["a"])]}
        detail = {"task": {"column": "done", "runId": None}, "runs": []}
        with tempfile.TemporaryDirectory() as directory, patch.object(board, "agetor", return_value=detail), \
             patch.object(board, "board_column") as move, patch.object(board, "start_row") as start, \
             patch.object(board, "accepted_commit", side_effect=ValueError("Commit manually first")):
            board.tick(Path(directory), state)
            board.tick(Path(directory), state)
        move.assert_not_called()
        start.assert_not_called()
        self.assertEqual(item["error"], "Commit manually first")
        self.assertNotIn("accepted_commit", item)

    def test_idle_failed_card_returns_to_ready_before_start(self):
        detail = {"task": {"column": "blocked", "runId": "old", "hasOpenableRun": False},
                  "runs": [{"id": "old", "status": "failed"}]}
        with patch.object(board, "agetor", return_value=detail) as cli:
            board.launch_worker(row("a"), Path("/records"))
        self.assertEqual(cli.call_args_list, [call("show", "card-a"),
                         call("move", "card-a", "ready"), call("start", "card-a")])

    def test_pending_question_is_never_overwritten_by_launch(self):
        detail = {"task": {"runId": None, "pendingInteractionCount": 1}, "runs": []}
        with patch.object(board, "agetor", return_value=detail) as cli:
            with self.assertRaisesRegex(ValueError, "question is already active"):
                board.launch_worker(row("a"), Path("/records"))
        cli.assert_called_once_with("show", "card-a")

    def test_dependency_cycles_unknown_ids_and_multiple_parents_are_rejected(self):
        for rows in ([row("a", ["b"]), row("b", ["a"])], [row("a", ["unknown"])],
                     [row("a"), row("b"), row("c", ["a", "b"])]):
            with self.assertRaises(ValueError):
                board.validate_plan({"tickets": rows})

    def test_parallel_limit_and_unsatisfied_dependency_prevent_dispatch(self):
        state = {"repo": "/fixture", "base_commit": "base", "max_parallel": 2,
                 "tickets": [row("a"), row("b"), row("c", ["a"]), row("d")]}
        def detail(*args):
            return {"task": {"id": args[1], "column": "ready", "runId": None}, "runs": []}
        launched = []
        def start(directory, state, item, base):
            launched.append((item["id"], base))
            item["status"] = "working"
        with tempfile.TemporaryDirectory() as directory, patch.object(board, "agetor", side_effect=detail), \
             patch.object(board, "start_row", side_effect=start):
            board.tick(Path(directory), state)
        self.assertEqual(launched, [("a", "base"), ("b", "base")])
        self.assertEqual(state["tickets"][2]["status"], "queued")

    def test_dependent_uses_the_accepted_immutable_commit(self):
        state = {"repo": "/fixture", "base_commit": "old-main", "max_parallel": 2,
                 "tickets": [{**row("a", status="accepted"), "accepted_commit": "accepted-parent"}, row("b", ["a"])]}
        with tempfile.TemporaryDirectory() as directory, \
             patch.object(board, "agetor", return_value={"task": {"column": "ready", "runId": None}, "runs": []}), \
             patch.object(board, "start_row") as start:
            board.tick(Path(directory), state)
        self.assertEqual(start.call_args.args[-1], "accepted-parent")

    def test_running_worker_blocks_acceptance_even_if_card_is_dragged_done(self):
        detail = {"task": {"runId": "worker", "column": "done"},
                  "runs": [{"id": "worker", "status": "running"}]}
        with self.assertRaisesRegex(ValueError, "still running"), patch.object(board.pipeline, "readiness") as ready:
            board.accepted_commit(row("a"), detail)
        ready.assert_not_called()

    def test_failed_preparation_is_retained_as_blocked_and_not_retried_automatically(self):
        state = {"repo": "/fixture", "base_commit": "base", "max_parallel": 2, "tickets": [row("a")]}
        with tempfile.TemporaryDirectory() as directory, \
             patch.object(board, "agetor", return_value={"task": {"column": "ready", "runId": None}, "runs": []}), \
             patch.object(board, "start_row", side_effect=ValueError("environment unavailable")) as start:
            board.tick(Path(directory), state)
            board.tick(Path(directory), state)
        self.assertEqual(state["tickets"][0]["status"], "blocked")
        start.assert_called_once()

    def test_native_worker_failure_becomes_explicitly_retryable_blocked_state(self):
        item = {**row("a", status="working"), "worktree": "/fixture", "record_directory": "/records"}
        state = {"repo": "/fixture", "base_commit": "base", "max_parallel": 2, "tickets": [item]}
        detail = {"task": {"column": "blocked", "runId": "run", "pendingInteractionCount": 0},
                  "runs": [{"id": "run", "status": "failed"}]}
        with tempfile.TemporaryDirectory() as directory, patch.object(board, "agetor", return_value=detail), \
             patch.object(board.pipeline, "load", return_value={"stage": "planning"}), \
             patch.object(board, "start_row") as start:
            board.tick(Path(directory), state)
        self.assertEqual(item["status"], "blocked")
        self.assertIn("Worker stopped", item["error"])
        start.assert_not_called()


if __name__ == "__main__":
    unittest.main()
