from pathlib import Path
import os


APP_NAME = "Noob Trade Launcher"
REPO_URL = "git@github.com:samuel-mingdao-ma/pattern-matching-trading-system.git"
DEFAULT_LOCAL_PORT = 5000
DEFAULT_TUNNEL_HOST = "localhost.run"
DEFAULT_CLONE_ROOT = Path.home() / "NoobTradeWorkspace" / "stock_pattern_project"


def resolve_project_root():
    candidates = []
    env_override = os.getenv("NOOBTRADE_PROJECT_ROOT")

    if env_override:
        candidates.append(Path(env_override).expanduser())

    local_repo_root = Path(__file__).resolve().parents[1]
    candidates.append(local_repo_root)
    candidates.append(DEFAULT_CLONE_ROOT)

    for candidate in candidates:
        if (candidate / "frontend").exists() and (candidate / "backend").exists():
            return candidate

    return candidates[-1]


PROJECT_ROOT = resolve_project_root()
LAUNCHER_RUNTIME_DIR = PROJECT_ROOT / ".launcher_runtime"
BACKEND_VENV_DIR = LAUNCHER_RUNTIME_DIR / "backend_env"
BACKEND_LOG_PATH = LAUNCHER_RUNTIME_DIR / "backend.log"
TUNNEL_LOG_PATH = LAUNCHER_RUNTIME_DIR / "tunnel.log"
