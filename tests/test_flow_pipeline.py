import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch


SCRIPT = Path(__file__).parents[1] / "scripts/flow_pipeline.py"
SPEC = importlib.util.spec_from_file_location("flow_pipeline", SCRIPT)
flow = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(flow)


def git(root, *args):
    return subprocess.run(["git", "-C", str(root), *args], check=True,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout.decode().strip()


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="flow-pipeline-test-")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.root = self.base / "repo with spaces"
        self.root.mkdir()
        git(self.root, "init", "-b", "main")
        git(self.root, "config", "user.name", "Flow Test")
        git(self.root, "config", "user.email", "flow@example.invalid")
        (self.root / "app.py").write_text("value = 1\n")
        git(self.root, "add", ".")
        git(self.root, "commit", "-m", "fixture: base")
        self.record = self.base / "private records"
        self.record.mkdir()
        self.state = {"workspace": str(self.root), "base_commit": git(self.root, "rev-parse", "HEAD"),
                      "author": "claude", "schema": 1}
        flow.stage(self.record, self.state, "planning", "fixture")
        for name in ("TASK.md", "HANDOFF.md", "CHECKS.md", "DEBRIEF.md"):
            (self.record / name).write_text("fixture requirements/evidence\n")

    def test_source_fingerprint_detects_untracked_content_and_staging(self):
        first = flow.fingerprint(self.root)
        extra = self.root / "new.py"
        extra.write_text("a = 1\n")
        second = flow.fingerprint(self.root)
        extra.write_text("a = 2\n")
        third = flow.fingerprint(self.root)
        git(self.root, "add", "new.py")
        fourth = flow.fingerprint(self.root)
        self.assertEqual(len({first, second, third, fourth}), 4)

    def test_installation_paths_do_not_require_a_git_checkout(self):
        with patch.object(flow, "context", side_effect=AssertionError("Git should not be queried")):
            self.assertEqual(flow.main(["paths"]), 0)

    def fake_scanner(self, command, root, record, stem, timeout):
        path = Path(command[command.index("--output") + 1] if command[0] == "semgrep"
                    else command[command.index("--report-path") + 1])
        if command[0] == "semgrep":
            payload = {"results": [{"check_id": "fixture-rule", "path": "app.py", "start": {"line": 1}}],
                       "errors": [], "paths": {"scanned": ["app.py"]}, "time": {"rules": ["fixture-rule"]}}
        else:
            payload = []
        path.write_text(json.dumps(payload))
        return {"exit_code": 1 if command[0] == "semgrep" else 0}

    def test_baseline_findings_are_visible_but_not_silently_rebaselined(self):
        with patch.object(flow, "run", side_effect=self.fake_scanner):
            self.assertEqual(flow.checks(self.root, self.record, self.state, "baseline", 2), 1)
            self.assertEqual(flow.checks(self.root, self.record, self.state, "final", 2), 0)
        final = json.loads((self.record / "final.json").read_text())
        self.assertEqual(final["results"][0]["status"], "findings")
        self.assertEqual(final["results"][0]["new_finding_ids"], [])
        with patch.object(flow, "context", return_value=(self.root, self.record, self.state["base_commit"])):
            self.assertEqual(flow.main(["check", "baseline"]), 1)

    def test_one_scanner_failure_does_not_skip_the_other(self):
        with patch.object(flow, "run", return_value={"exit_code": None, "error": "not installed"}) as run:
            self.assertEqual(flow.checks(self.root, self.record, self.state, "final", 2), 1)
            self.assertEqual(run.call_count, 2)
        final = json.loads((self.record / "final.json").read_text())
        self.assertTrue(all(r["status"] == "error" for r in final["results"]))

    def test_zero_coverage_or_scanner_errors_never_pass(self):
        path = self.record / "scan.json"
        for data in (
            {"results": [], "errors": [], "paths": {"scanned": []}, "time": {"rules": ["r"]}},
            {"results": [], "errors": [], "paths": {"scanned": ["app.py"]}},
            {"results": [], "errors": ["parse failure"], "paths": {"scanned": ["app.py"]}, "time": {"rules": ["r"]}},
        ):
            path.write_text(json.dumps(data))
            self.assertEqual(flow.scan_result("semgrep", {"exit_code": 0}, path)["status"], "error")

    def test_failed_baseline_can_retry_only_while_source_is_unchanged(self):
        with patch.object(flow, "run", return_value={"exit_code": None, "error": "fixture failure"}):
            flow.checks(self.root, self.record, self.state, "baseline", 2)
        with patch.object(flow, "context", return_value=(self.root, self.record, self.state["base_commit"])), \
             patch.object(flow, "checks", return_value=0) as checks:
            self.assertEqual(flow.main(["check", "baseline"]), 0)
            checks.assert_called_once()
            checks.reset_mock()
            (self.root / "app.py").write_text("changed = True\n")
            self.assertEqual(flow.main(["check", "baseline"]), 1)
            checks.assert_not_called()

    def fake_reviewer(self, command, root, record, stem, timeout, prompt):
        value = {"verdict": "clean", "summary": "Inspected fixture", "findings": [], "coverage_gaps": []}
        if command[0] == "codex":
            Path(command[command.index("--output-last-message") + 1]).write_text(json.dumps(value))
            self.assertIn("read-only", command)
        else:
            self.assertNotIn("Bash", command)
            self.assertIn("Read,Glob,Grep", command)
        stdout = record / "reviewer.stdout"
        stdout.write_text(json.dumps({"structured_output": value, "is_error": False}))
        return {"exit_code": 0, "stdout": str(stdout)}

    def test_both_author_routes_choose_other_provider_and_write_report(self):
        for author, reviewer in (("claude", "codex"), ("codex", "claude")):
            self.state["author"] = author
            with patch.object(flow, "run", side_effect=self.fake_reviewer) as run:
                self.assertEqual(flow.review(self.root, self.record, self.state, 2), 0)
            data = json.loads((self.record / "review.json").read_text())
            self.assertEqual(data["reviewer"], reviewer)
            self.assertEqual(run.call_args.args[0][0], reviewer)
            self.assertIn("Verdict: clean", (self.record / "REVIEW.md").read_text())
            self.assertEqual(git(self.root, "status", "--porcelain"), "")

    def test_failed_malformed_or_contradictory_review_never_passes(self):
        for execution in ({"exit_code": 1}, {"exit_code": 0}):
            with patch.object(flow, "run", return_value=execution):
                self.assertEqual(flow.review(self.root, self.record, self.state, 2), 1)
                self.assertEqual(json.loads((self.record / "review.json").read_text())["verdict"], "incomplete")
        value = {"verdict": "clean", "summary": "done", "findings": [], "coverage_gaps": ["missing tests"]}
        self.assertEqual(flow.validate_review(value)["verdict"], "incomplete")

    def test_source_change_during_review_invalidates_it_without_reverting_change(self):
        def mutate(*args):
            result = self.fake_reviewer(*args)
            (self.root / "app.py").write_text("concurrent change\n")
            return result
        with patch.object(flow, "run", side_effect=mutate):
            self.assertEqual(flow.review(self.root, self.record, self.state, 2), 1)
        self.assertEqual((self.root / "app.py").read_text(), "concurrent change\n")
        self.assertFalse(json.loads((self.record / "review.json").read_text())["source_unchanged"])

    def test_readiness_requires_current_other_provider_review_and_final_scan(self):
        with patch.object(flow, "run", side_effect=self.fake_scanner):
            flow.checks(self.root, self.record, self.state, "baseline", 2)
            flow.checks(self.root, self.record, self.state, "final", 2)
        with patch.object(flow, "run", side_effect=self.fake_reviewer):
            flow.review(self.root, self.record, self.state, 2)
        flow.readiness(self.root, self.record)
        (self.root / "new.py").write_text("unreviewed = True\n")
        with self.assertRaisesRegex(ValueError, "current source"):
            flow.readiness(self.root, self.record)

    def test_real_child_process_timeout_does_not_become_success(self):
        result = flow.run(["/bin/sleep", "5"], self.root, self.record, "timeout", timeout=0.01)
        self.assertIsNone(result["exit_code"])
        self.assertIn("timed out", result["error"])

    def test_cli_init_requires_base_and_preserves_pin(self):
        record = self.base / "new records"
        with patch.object(flow, "context", return_value=(self.root, record, None)):
            self.assertEqual(flow.main(["init", "--author", "claude"]), 1)
            self.assertEqual(flow.main(["init", "--author", "claude", "--base", self.state["base_commit"]]), 0)
            self.assertEqual(json.loads((record / "STATUS.json").read_text())["base_commit"], self.state["base_commit"])

    def test_managed_ticket_context_uses_the_managers_pinned_base_and_external_record(self):
        (self.root / ".devcontainer.json").write_text('{"image":"fixture-only"}')
        git(self.root, "add", ".devcontainer.json")
        git(self.root, "commit", "-m", "fixture: container config")
        home = self.base / "ticket-manager"
        primary, common, directory = flow.ticket.identity(self.root, home)
        profile = flow.ticket.setup(primary, common, directory)
        with patch.object(flow.ticket, "container"):
            state = flow.ticket.start(directory, profile, "managed", fetch=False)
        root, record, base = flow.context(Path(state["worktree"]), home)
        self.assertEqual(root, Path(state["worktree"]))
        self.assertEqual(record, directory / "records/managed/pipeline")
        self.assertFalse(record.is_relative_to(root))
        self.assertEqual(base, state["base_commit"])


if __name__ == "__main__":
    unittest.main()
