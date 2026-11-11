import contextlib
import importlib.util
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


SPEC = importlib.util.spec_from_file_location(
    "install_flow", Path(__file__).parents[1] / "scripts/install_flow.py")
install = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(install)


class InstallTests(unittest.TestCase):
    def test_relocated_install_preserves_old_files_and_repeat_install_is_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve() / "a differently located checkout"
            home = Path(directory).resolve() / "another user's home"
            for name in ("flow-plan", "flow-task", "flow-review", "flow-debrief", "flow-finish"):
                source = base / "skills" / name
                source.mkdir(parents=True)
                (source / "SKILL.md").write_text("new skill\n")
            (base / "scripts").mkdir()
            for name in ("flow_container", "flow_workspace", "flow_ticket", "flow_pipeline", "flow_board"):
                (base / "scripts" / f"{name}.py").write_text("# fixture\n")
            old = home / ".claude/skills/flow-task"
            old.mkdir(parents=True)
            (old / "custom.md").write_text("preserve my edits\n")
            with patch.object(install, "__file__", str(base / "scripts/install_flow.py")), \
                 patch.object(install.Path, "home", return_value=home), \
                 contextlib.redirect_stdout(io.StringIO()):
                install.main()
                backups = list((base / "backups").iterdir())
                install.main()
            self.assertEqual(list((base / "backups").iterdir()), backups)
            self.assertEqual((backups[0] / "claude/flow-task/custom.md").read_text(), "preserve my edits\n")
            self.assertEqual(old.resolve(), base / "skills/flow-task")
            self.assertEqual((home / ".agents/skills/flow-plan").resolve(), base / "skills/flow-plan")
            for command in ("flow-container", "flow-workspace", "flow-ticket", "flow-pipeline", "flow-board"):
                self.assertEqual((home / ".local/bin" / command).resolve(),
                                 base / "scripts" / (command.replace("-", "_") + ".py"))


if __name__ == "__main__":
    unittest.main()
