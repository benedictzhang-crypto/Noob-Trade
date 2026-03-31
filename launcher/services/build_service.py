from pathlib import Path
import os

from launcher.config import BACKEND_VENV_DIR


class BuildService:
    """Create the backend runtime and build the frontend bundle."""

    def __init__(self, process_service, python_command, npm_command, environment_service):
        self.process_service = process_service
        self.python_command = python_command
        self.npm_command = npm_command
        self.environment_service = environment_service

    def ensure_backend_environment(self, project_root, log_callback):
        project_root = Path(project_root)
        backend_dir = project_root / "backend"

        if not BACKEND_VENV_DIR.exists():
            BACKEND_VENV_DIR.parent.mkdir(parents=True, exist_ok=True)
            log_callback("Creating isolated backend runtime...")
            self.process_service.run_blocking(
                [*self.python_command, "-m", "venv", str(BACKEND_VENV_DIR)],
                cwd=project_root,
                log_callback=log_callback,
            )

        backend_python = self.environment_service.backend_venv_python()
        log_callback("Installing backend dependencies...")
        self.process_service.run_blocking(
            [str(backend_python), "-m", "pip", "install", "--upgrade", "pip"],
            cwd=backend_dir,
            log_callback=log_callback,
        )
        self.process_service.run_blocking(
            [str(backend_python), "-m", "pip", "install", "-r", "requirements.txt"],
            cwd=backend_dir,
            log_callback=log_callback,
        )
        return backend_python

    def install_frontend_dependencies(self, project_root, log_callback):
        frontend_dir = Path(project_root) / "frontend"
        log_callback("Installing frontend dependencies...")
        self.process_service.run_blocking(
            [*self.npm_command, "install"],
            cwd=frontend_dir,
            log_callback=log_callback,
            env=os.environ.copy(),
        )

    def build_frontend(self, project_root, log_callback):
        frontend_dir = Path(project_root) / "frontend"
        log_callback("Building frontend bundle...")
        self.process_service.run_blocking(
            [*self.npm_command, "run", "build"],
            cwd=frontend_dir,
            log_callback=log_callback,
            env=os.environ.copy(),
        )
