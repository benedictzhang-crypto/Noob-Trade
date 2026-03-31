from dataclasses import dataclass
from pathlib import Path
import os
import shutil
import subprocess
import sys

from launcher.config import BACKEND_VENV_DIR


@dataclass
class ToolingSnapshot:
    python_command: list[str] | None
    git_command: list[str] | None
    npm_command: list[str] | None
    ssh_command: list[str] | None

    @property
    def missing(self):
        missing_tools = []

        if self.python_command is None:
            missing_tools.append("Python 3")
        if self.git_command is None:
            missing_tools.append("git")
        if self.npm_command is None:
            missing_tools.append("npm")
        if self.ssh_command is None:
            missing_tools.append("ssh")

        return missing_tools


class EnvironmentService:
    """Resolve cross-platform tool paths used by the launcher."""

    def get_tooling_snapshot(self):
        return ToolingSnapshot(
            python_command=self._resolve_python_command(),
            git_command=self._resolve_command("git"),
            npm_command=self._resolve_npm_command(),
            ssh_command=self._resolve_command("ssh"),
        )

    def backend_venv_python(self):
        if os.name == "nt":
            return BACKEND_VENV_DIR / "Scripts" / "python.exe"

        return BACKEND_VENV_DIR / "bin" / "python"

    def _resolve_command(self, name):
        command_path = shutil.which(name)
        return [command_path] if command_path else None

    def _resolve_npm_command(self):
        candidates = ["npm.cmd", "npm"] if os.name == "nt" else ["npm"]

        for candidate in candidates:
            command_path = shutil.which(candidate)
            if command_path:
                return [command_path]

        return None

    def _resolve_python_command(self):
        if not getattr(sys, "frozen", False):
            executable = Path(sys.executable)

            if executable.exists():
                return [str(executable)]

        candidates = (
            [["py", "-3"], ["python"], ["python3"]]
            if os.name == "nt"
            else [["python3"], ["python"]]
        )

        for candidate in candidates:
            try:
                subprocess.run(
                    [*candidate, "--version"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=True,
                    text=True,
                )
                return candidate
            except Exception:
                continue

        return None
