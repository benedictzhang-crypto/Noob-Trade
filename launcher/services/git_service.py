from pathlib import Path


class GitService:
    """Clone or update the Noob Trade repository."""

    def __init__(self, process_service, git_command, repo_url):
        self.process_service = process_service
        self.git_command = git_command
        self.repo_url = repo_url

    def ensure_repo_ready(self, project_root, log_callback):
        project_root = Path(project_root)

        if (project_root / ".git").exists():
            self.pull_latest(project_root, log_callback)
            return project_root

        if project_root.exists() and any(project_root.iterdir()):
            raise RuntimeError(
                f"Project folder exists but is not a git repository: {project_root}"
            )

        project_root.parent.mkdir(parents=True, exist_ok=True)
        log_callback("Cloning Noob Trade from GitHub...")
        self.process_service.run_blocking(
            [*self.git_command, "clone", self.repo_url, str(project_root)],
            cwd=project_root.parent,
            log_callback=log_callback,
        )
        return project_root

    def pull_latest(self, project_root, log_callback):
        log_callback("Pulling latest code from GitHub...")
        self.process_service.run_blocking(
            [*self.git_command, "-C", str(project_root), "pull", "--rebase", "--autostash"],
            cwd=project_root,
            log_callback=log_callback,
        )
