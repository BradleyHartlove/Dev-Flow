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
        for name in ("TASK.md", "HANDOFF.md", "CHECKS.md", "TESTING.md", "DEBRIEF.md"):
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
        if command[0] == "osv-scanner":
            self.assertIn("--offline", command)
            return self.osv_report(root, record)
        path = Path(command[command.index("--output") + 1] if command[0] == "semgrep"
                    else command[command.index("--report-path") + 1])
        if command[0] == "semgrep":
            payload = {"results": [{"check_id": "fixture-rule", "path": "app.py", "start": {"line": 1}}],
                       "errors": [], "paths": {"scanned": ["app.py"]}, "time": {"rules": ["fixture-rule"]}}
        else:
            payload = []
        path.write_text(json.dumps(payload))
        return {"exit_code": 1 if command[0] == "semgrep" else 0}

    def osv_report(self, root, record, *advisories):
        path = record / "osv-scanner.stdout"
        path.write_text(json.dumps({"results": [{
            "source": {"path": str(root / "package-lock.json")},
            "packages": [{"package": {"ecosystem": "npm", "name": "fixture", "version": "1.0.0"},
                          "vulnerabilities": [{"id": advisory} for advisory in advisories]}],
        }]}))
        return {"exit_code": int(bool(advisories)), "stdout": str(path)}

    def test_osv_compares_findings_to_baseline_and_keeps_existing_findings_visible(self):
        def scan(command, root, record, stem, timeout):
            if command[0] == "osv-scanner":
                advisories = ["OSV-existing"]
                if (root / "new-lockfile").exists():
                    advisories.append("OSV-new")
                return self.osv_report(root, record, *advisories)
            return self.fake_scanner(command, root, record, stem, timeout)

        with patch.object(flow, "run", side_effect=scan):
            flow.checks(self.root, self.record, self.state, "baseline", 2)
            self.assertEqual(flow.checks(self.root, self.record, self.state, "final", 2), 0)
            (self.root / "new-lockfile").touch()
            self.assertEqual(flow.checks(self.root, self.record, self.state, "final", 2), 1)
        osv = next(r for r in flow.read_json(self.record / "final.json")["results"] if r["tool"] == "osv-scanner")
        self.assertEqual(len(osv["finding_ids"]), 2)
        self.assertEqual([json.loads(identity)[-1] for identity in osv["new_finding_ids"]], ["OSV-new"])

    def test_final_backfills_legacy_osv_baseline_from_pinned_commit(self):
        def scan(command, root, record, stem, timeout):
            if command[0] == "osv-scanner":
                advisories = ["OSV-existing"]
                if "changed" in (root / "app.py").read_text():
                    advisories.append("OSV-new")
                return self.osv_report(root, record, *advisories)
            return self.fake_scanner(command, root, record, stem, timeout)

        with patch.object(flow, "run", side_effect=scan):
            flow.checks(self.root, self.record, self.state, "baseline", 2)
            baseline_path = self.record / "baseline.json"
            baseline = flow.read_json(baseline_path)
            baseline["results"] = [r for r in baseline["results"] if r["tool"] != "osv-scanner"]
            flow.write_json(baseline_path, baseline)
            (self.root / "app.py").write_text("changed = True\n")
            self.assertEqual(flow.checks(self.root, self.record, self.state, "final", 2), 1)

        recovered = flow.read_json(baseline_path)
        self.assertEqual(recovered["fingerprint"], baseline["fingerprint"])
        self.assertEqual(recovered["results"][:-1], baseline["results"])
        self.assertEqual(recovered["results"][-1]["base_commit"], self.state["base_commit"])
        final = flow.read_json(self.record / "final.json")
        osv = next(r for r in final["results"] if r["tool"] == "osv-scanner")
        self.assertEqual([json.loads(identity)[-1] for identity in osv["new_finding_ids"]], ["OSV-new"])
        self.assertEqual(len(flow.registered_worktrees(self.root)), 1)
        self.assertEqual((self.root / "app.py").read_text(), "changed = True\n")

    def test_osv_no_packages_is_distinct_from_error_or_clean_package_scan(self):
        path = self.record / "osv-scanner.stdout"
        for payload, exit_code, expected in (({"results": []}, 0, "no_packages"),
                                              ({"results": None}, 0, "no_packages"),
                                              ({}, 0, "error"),
                                              ({"results": []}, 127, "error")):
            path.write_text(json.dumps(payload))
            with patch.object(flow, "run", return_value={"stdout": str(path), "exit_code": exit_code}):
                self.assertEqual(flow.scan_dependencies(self.root, self.record, 2)["status"], expected)

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
            self.assertEqual(run.call_count, 3)
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
            self.assertEqual(run.call_count, 2)
            behavior, regression = (call.args for call in run.call_args_list)
            for command, root, record, stem, timeout, prompt in (behavior, regression):
                self.assertEqual(command[0], reviewer)
                self.assertEqual(root, self.root)
                self.assertIn(self.state["base_commit"], prompt)
                self.assertIn("README.md, CLAUDE.md, AGENTS.md", prompt)
                self.assertIn("directory-specific guidance", prompt)
            self.assertIn("Trace changed behavior", behavior[-1])
            self.assertIn("actual test assertions", regression[-1])
            self.assertNotEqual(behavior[2], regression[2])
            self.assertEqual(list(data["passes"]), ["behavior", "regression-tests"])
            self.assertIn("Verdict: clean", (self.record / "REVIEW.md").read_text())
            self.assertEqual(git(self.root, "status", "--porcelain"), "")

    def test_clean_behavior_pass_does_not_cover_a_failed_regression_pass(self):
        def review(command, root, record, stem, timeout, prompt):
            if record.name == "regression-tests":
                return {"exit_code": None, "error": "timed out"}
            return self.fake_reviewer(command, root, record, stem, timeout, prompt)

        with patch.object(flow, "run", side_effect=review):
            self.assertEqual(flow.review(self.root, self.record, self.state, 2), 1)
        report = flow.read_json(self.record / "review.json")
        self.assertEqual(report["verdict"], "incomplete")
        self.assertEqual(report["passes"]["behavior"]["verdict"], "clean")
        self.assertEqual(report["coverage_gaps"], ["regression-tests: timed out"])

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
        with patch.object(flow, "run", side_effect=mutate) as run:
            self.assertEqual(flow.review(self.root, self.record, self.state, 2), 1)
            run.assert_called_once()
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

    def test_readiness_requires_both_passes_and_osv_evidence(self):
        with patch.object(flow, "run", side_effect=self.fake_scanner):
            flow.checks(self.root, self.record, self.state, "baseline", 2)
            flow.checks(self.root, self.record, self.state, "final", 2)
        with patch.object(flow, "run", side_effect=self.fake_reviewer):
            flow.review(self.root, self.record, self.state, 2)
        review_path = self.record / "review.json"
        review = flow.read_json(review_path)
        flow.write_json(review_path, {**review, "passes": {"behavior": review["passes"]["behavior"]}})
        with self.assertRaisesRegex(ValueError, "behavior and regression-test passes"):
            flow.readiness(self.root, self.record)
        flow.write_json(review_path, review)

        final_path = self.record / "final.json"
        final = flow.read_json(final_path)
        final["results"] = [r for r in final["results"] if r["tool"] != "osv-scanner"]
        flow.write_json(final_path, final)
        with self.assertRaisesRegex(ValueError, "baseline and final OSV scans"):
            flow.readiness(self.root, self.record)

    def test_manual_commit_preserves_reviewed_content_but_extra_edits_do_not(self):
        (self.root / "app.py").write_text("value = 2\n")
        (self.root / "new.py").write_text("new_value = 3\n")
        with patch.object(flow, "run", side_effect=self.fake_scanner):
            flow.checks(self.root, self.record, self.state, "baseline", 2)
            flow.checks(self.root, self.record, self.state, "final", 2)
        with patch.object(flow, "run", side_effect=self.fake_reviewer):
            flow.review(self.root, self.record, self.state, 2)
        before = flow.fingerprint(self.root, source_only=True)
        git(self.root, "add", ".")
        git(self.root, "commit", "-m", "fixture: manual acceptance commit")
        self.assertEqual(before, flow.fingerprint(self.root, source_only=True))
        flow.readiness(self.root, self.record, after_commit=True)
        (self.root / "app.py").write_text("value = 4\n")
        git(self.root, "add", ".")
        git(self.root, "commit", "-m", "fixture: unreviewed additional change")
        with self.assertRaisesRegex(ValueError, "current source"):
            flow.readiness(self.root, self.record, after_commit=True)

    def test_completion_requires_review_ready_and_a_matching_manual_commit(self):
        args = ["stage", "complete"]
        with patch.object(flow, "context", return_value=(self.root, self.record, None)):
            self.assertEqual(flow.main(args), 1)
            (self.root / "app.py").write_text("value = 2\n")
            with patch.object(flow, "run", side_effect=self.fake_scanner):
                flow.checks(self.root, self.record, self.state, "baseline", 2)
                flow.checks(self.root, self.record, self.state, "final", 2)
            with patch.object(flow, "run", side_effect=self.fake_reviewer):
                flow.review(self.root, self.record, self.state, 2)
            self.assertEqual(flow.main(["stage", "ready-for-human"]), 0)
            self.assertEqual(flow.main(args), 1)
            git(self.root, "add", ".")
            git(self.root, "commit", "-m", "fixture: manual acceptance")
            self.assertEqual(flow.main(args), 0)
            self.assertEqual(flow.load(self.record, self.root)["stage"], "complete")

    def test_real_child_process_timeout_does_not_become_success(self):
        result = flow.run(["/bin/sleep", "5"], self.root, self.record, "timeout", timeout=0.01)
        self.assertIsNone(result["exit_code"])
        self.assertIn("timed out", result["error"])

    def test_init_refuses_primary_checkout_and_dirty_unrecorded_worktree(self):
        worktree = self.base / "dirty"
        git(self.root, "worktree", "add", "-b", "dirty", str(worktree))
        (worktree / "app.py").write_text("dirty = True\n")
        with patch.object(flow, "ROOT", self.base / "flow-installation"):
            for root in (self.root, worktree):
                args = ["--workspace", str(root), "init", "--author", "claude"]
                self.assertEqual(flow.main(args), 1)

    def test_earlier_pilot_record_uses_its_pinned_base(self):
        home = self.base / "earlier-tickets"
        common = git(self.root, "rev-parse", "--path-format=absolute", "--git-common-dir")
        key = flow.hashlib.sha256(common.encode()).hexdigest()[:10]
        directory = home / f"repo-with-spaces-{key}"
        worktree = directory / "worktrees" / "health"
        git(self.root, "worktree", "add", "-b", "flow/health", str(worktree))
        base = git(worktree, "rev-parse", "HEAD")
        state_path = directory / "records" / "health" / "state.json"
        flow.write_json(state_path, {"worktree": str(worktree), "common": common,
                                     "branch": "flow/health", "base_commit": base})
        self.assertEqual(flow.context(worktree, home),
                         (worktree, state_path.parent / "pipeline", base))

    def test_native_worktrees_have_separate_external_records_and_preserve_their_base(self):
        home = self.base / "unused-manager"
        roots = [self.base / "native health", self.base / "native search"]
        base = git(self.root, "rev-parse", "HEAD")
        for index, root in enumerate(roots):
            git(self.root, "worktree", "add", "-b", f"native-{index}", str(root), base)
            git(root, "commit", "--allow-empty", "-m", f"fixture: native editor snapshot {index}")
        pinned = {root: git(root, "rev-parse", "HEAD") for root in roots}
        self.assertNotEqual(pinned[roots[0]], pinned[roots[1]])
        self.assertEqual(git(roots[0], "rev-parse", "HEAD^{tree}"), git(roots[1], "rev-parse", "HEAD^{tree}"))
        registered = git(self.root, "worktree", "list", "--porcelain")
        records = []
        with patch.object(flow, "ROOT", self.base / "flow-installation"):
            for author, root in zip(["claude", "codex"], roots):
                selected, record, managed_base = flow.context(root, home)
                self.assertEqual(selected, root)
                self.assertIsNone(managed_base)
                self.assertFalse(record.is_relative_to(root))
                self.assertEqual(flow.main(["--workspace", str(root), "--ticket-home", str(home),
                                          "init", "--author", author]), 0)
                records.append(record)
            base = pinned[roots[0]]
            (roots[0] / "app.py").write_text("health = True\n")
            git(roots[0], "add", "app.py")
            git(roots[0], "commit", "-m", "fixture: user's manual health commit")
            new_head = git(roots[0], "rev-parse", "HEAD")
            args = ["--workspace", str(roots[0]), "--ticket-home", str(home), "init", "--author", "claude"]
            self.assertEqual(flow.main(args), 0)
            self.assertEqual(flow.main([*args[:-1], "codex"]), 1)
            self.assertEqual(flow.main([*args, "--base", new_head]), 1)
        self.assertNotEqual(records[0], records[1])
        self.assertEqual(flow.load(records[0], roots[0])["base_commit"], base)
        self.assertEqual((roots[1] / "app.py").read_text(), "value = 1\n")
        self.assertEqual((self.root / "app.py").read_text(), "value = 1\n")
        self.assertFalse(home.exists())
        self.assertEqual(git(self.root, "worktree", "list", "--porcelain").count("worktree "),
                         registered.count("worktree "))


if __name__ == "__main__":
    unittest.main()
