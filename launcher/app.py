from pathlib import Path
import sys


if __package__ in (None, ""):
    project_root = Path(__file__).resolve().parents[1]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

from launcher.ui import NoobTradeLauncher


def main():
    app = NoobTradeLauncher()
    app.mainloop()


if __name__ == "__main__":
    main()
