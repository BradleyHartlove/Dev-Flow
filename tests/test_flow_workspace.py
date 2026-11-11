import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


SPEC = importlib.util.spec_from_file_location(
    "flow_workspace", Path(__file__).parents[1] / "scripts/flow_workspace.py")
workspace = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(workspace)


class WorkspaceTests(unittest.TestCase):
    def test_generated_tasks_target_the_explicit_workspace_and_do_not_auto_start(self):
        root = Path("/code/a repository with spaces")
        config = workspace.workspace_config(root)
        self.assertEqual(config["folders"], [{"name": "project", "path": str(root)}])
        self.assertEqual(
            [t["args"] for t in config["tasks"]["tasks"]],
            [["--workspace", "${workspaceFolder:project}", action]
             for action in ("up", "status", "rebuild", "stop")])
        for task in config["tasks"]["tasks"]:
            self.assertNotIn("runOptions", task)
            self.assertNotIn("dependsOn", task)

    def test_generation_does_not_modify_repo_and_refuses_to_overwrite_workspace(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = base / "repo"
            (root / ".devcontainer").mkdir(parents=True)
            (root / ".devcontainer/devcontainer.json").write_text("{}")
            output = base / "local-workspaces"
            before = sorted(p.relative_to(root) for p in root.rglob("*"))
            args = [str(root), "--directory", str(output)]
            with patch.object(workspace, "repository_root", return_value=root):
                self.assertEqual(workspace.main(args), 0)
                generated = output / "repo.code-workspace"
                self.assertEqual(json.loads(generated.read_text())["folders"][0]["path"], str(root))
                generated.write_text("local user edits")
                self.assertEqual(workspace.main(args), 1)
                self.assertEqual(generated.read_text(), "local user edits")
            self.assertEqual(sorted(p.relative_to(root) for p in root.rglob("*")), before)

    def test_missing_devcontainer_and_path_traversal_name_create_no_workspace(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "repo"
            root.mkdir()
            output = Path(directory) / "local-workspaces"
            with patch.object(workspace, "repository_root", return_value=root):
                self.assertEqual(workspace.main([str(root), "--directory", str(output)]), 1)
                self.assertFalse(output.exists())
                (root / ".devcontainer.json").write_text("{}")
                self.assertEqual(workspace.main([
                    str(root), "--directory", str(output), "--name", "../other"]), 1)
                self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
