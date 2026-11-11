#!/usr/bin/env python3
"""Link the standard flow skills/command into both local agent installations."""

from datetime import datetime, timezone
import os
from pathlib import Path
import shutil
import uuid


def main():
    base = Path(__file__).resolve().parents[1]
    backup = base / "backups" / ("installed-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:6])
    home = Path.home()
    pairs = []
    for agent in (".agents", ".claude"):
        for name in ("flow-plan", "flow-task", "flow-review", "flow-debrief", "flow-finish"):
            pairs.append((base / "skills" / name, home / agent / "skills" / name,
                          backup / agent.removeprefix(".") / name))
    for command in ("flow-container", "flow-workspace", "flow-ticket", "flow-pipeline"):
        script = command.replace("-", "_") + ".py"
        pairs.append((base / "scripts" / script, home / ".local/bin" / command, backup / "bin" / command))
    for source, target, saved in pairs:
        if not source.exists():
            raise SystemExit(f"Missing source; no further changes made: {source}")
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.is_symlink() and target.resolve() == source.resolve():
            print(f"Already linked: {target}")
            continue
        existed = os.path.lexists(target)
        if existed:
            saved.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            shutil.move(str(target), str(saved))
        try:
            target.symlink_to(source, target_is_directory=source.is_dir())
        except OSError:
            if existed:
                shutil.move(str(saved), str(target))
            raise
        print(f"Linked: {target}")
    if backup.exists():
        print(f"Previous installations preserved: {backup}")


if __name__ == "__main__":
    main()
