import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch


SPEC = importlib.util.spec_from_file_location(
    "flow_container", Path(__file__).parents[1] / "scripts/flow_container.py")
flow = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(flow)


class RoutingTests(unittest.TestCase):
    def setUp(self):
        self.root = Path("/work/task with spaces")
        self.common = Path("/work/main repo/.git")
        self.record = {"workspace": str(self.root), "container_id": "abc123"}
        self.info = {"Id": "abc123def", "State": {"Running": True}, "Mounts": [
            {"Type": "bind", "Source": str(self.root),
             "Destination": str(self.root), "RW": True}]}

    def test_mounts_keep_space_containing_paths_as_single_arguments(self):
        command = flow.up_command(self.root, self.common)
        self.assertEqual(command[command.index("--workspace-folder") + 1], str(self.root))
        mounts = [command[i + 1] for i, value in enumerate(command) if value == "--mount"]
        self.assertEqual(mounts, [f"type=bind,source={p},target={p}"
                                  for p in (self.root, self.common)])

    def test_rejects_mount_delimiters_in_paths(self):
        with self.assertRaises(flow.FlowError):
            flow.up_command(Path("/work/a,b"), self.common)

    def test_rebuild_keeps_worktree_mounts_and_only_rebuild_requests_replacement(self):
        normal = flow.up_command(self.root, self.common)
        rebuild = flow.up_command(self.root, self.common, rebuild=True)
        self.assertNotIn("--remove-existing-container", normal)
        self.assertIn("--remove-existing-container", rebuild)
        self.assertEqual([arg for arg in rebuild if arg != "--remove-existing-container"], normal)

    def test_rebuild_records_new_container_only_after_verifying_its_mounts(self):
        with tempfile.TemporaryDirectory() as directory:
            record_path = Path(directory) / "container.json"
            record_path.write_text(json.dumps({**self.record, "container_id": "old123"}))
            result = {"outcome": "success", "containerId": "abc123",
                      "remoteWorkspaceFolder": "/workspaces/project", "remoteUser": "vscode"}
            with patch.object(flow, "context", return_value=(self.root, self.common, record_path)), \
                 patch.object(flow, "prepare_records"), \
                 patch.object(flow, "capture", side_effect=[json.dumps(result), json.dumps([self.info])]) as capture:
                self.assertEqual(flow.main(["rebuild"]), 0)
                self.assertIn("--remove-existing-container", capture.call_args_list[0].args[0])
                self.assertEqual(json.loads(record_path.read_text())["container_id"], "abc123")

    def test_rebuild_rejects_incorrect_mounts_without_recording_new_container(self):
        self.info["Mounts"][0]["Source"] = "/work/other"
        with tempfile.TemporaryDirectory() as directory:
            record_path = Path(directory) / "container.json"
            result = {"outcome": "success", "containerId": "abc123"}
            with patch.object(flow, "context", return_value=(self.root, self.common, record_path)), \
                 patch.object(flow, "prepare_records"), \
                 patch.object(flow, "capture", side_effect=[json.dumps(result), json.dumps([self.info])]):
                self.assertEqual(flow.main(["rebuild"]), 1)
                self.assertFalse(record_path.exists())

    def test_wrong_workspace_never_queries_docker(self):
        with patch.object(flow, "capture") as capture:
            with self.assertRaises(flow.FlowError):
                flow.inspect_record(Path("/work/other"), self.record)
            capture.assert_not_called()

    def test_rejects_unrelated_container_mount(self):
        self.info["Mounts"][0]["Source"] = "/work/other"
        with patch.object(flow, "capture", return_value=json.dumps([self.info])):
            with self.assertRaises(flow.FlowError):
                flow.inspect_record(self.root, self.record)

    def test_rejects_read_only_worktree_mount(self):
        self.info["Mounts"][0]["RW"] = False
        with patch.object(flow, "capture", return_value=json.dumps([self.info])):
            with self.assertRaises(flow.FlowError):
                flow.inspect_record(self.root, self.record)

    def test_exec_selects_recorded_id_and_preserves_arguments_and_exit_status(self):
        with tempfile.TemporaryDirectory() as directory:
            record_path = Path(directory) / "container.json"
            record_path.write_text(json.dumps(self.record))
            with patch.object(flow, "context", return_value=(self.root, self.common, record_path)), \
                 patch.object(flow, "capture", return_value=json.dumps([self.info])), \
                 patch.object(flow.subprocess, "run", return_value=subprocess.CompletedProcess([], 7)) as run:
                self.assertEqual(flow.main(["exec", "--", "printf", "%s", "hello world"]), 7)
                self.assertEqual(run.call_args.args[0], [
                    "devcontainer", "exec", "--workspace-folder", str(self.root),
                    "--container-id", "abc123", "printf", "%s", "hello world"])

    def test_stopped_container_does_not_fall_back_to_host(self):
        self.info["State"]["Running"] = False
        with tempfile.TemporaryDirectory() as directory:
            record_path = Path(directory) / "container.json"
            record_path.write_text(json.dumps(self.record))
            with patch.object(flow, "context", return_value=(self.root, self.common, record_path)), \
                 patch.object(flow, "capture", return_value=json.dumps([self.info])), \
                 patch.object(flow.subprocess, "run") as run:
                self.assertEqual(flow.main(["exec", "--", "just", "test"]), 1)
                run.assert_not_called()

    def test_failed_start_does_not_create_container_record(self):
        with tempfile.TemporaryDirectory() as directory:
            record_path = Path(directory) / "container.json"
            with patch.object(flow, "context", return_value=(self.root, self.common, record_path)), \
                 patch.object(flow, "prepare_records"), \
                 patch.object(flow, "capture", side_effect=subprocess.CalledProcessError(3, ["devcontainer"])):
                self.assertEqual(flow.main(["up"]), 3)
                self.assertFalse(record_path.exists())

    def test_refuses_to_use_tracked_record_files(self):
        with patch.object(flow, "capture", return_value=".dev-flow/existing.txt"), \
             patch.object(flow.subprocess, "run") as run:
            with self.assertRaises(flow.FlowError):
                flow.prepare_records(self.root, self.common)
            run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
