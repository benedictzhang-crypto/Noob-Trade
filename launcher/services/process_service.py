from pathlib import Path
import os
import subprocess
import time
from urllib.request import urlopen

from launcher.config import BACKEND_LOG_PATH, DEFAULT_LOCAL_PORT, TUNNEL_LOG_PATH


class ProcessService:
    """Start, stop, and stream child processes used by the launcher."""

    def __init__(self):
        self.backend_process = None
        self.tunnel_process = None

    def run_blocking(self, command, cwd, log_callback, env=None):
        process = subprocess.Popen(
            command,
            cwd=str(cwd),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            creationflags=self._creationflags(),
        )

        output_lines = []

        assert process.stdout is not None
        for line in process.stdout:
            clean_line = line.rstrip()
            output_lines.append(clean_line)
            if clean_line:
                log_callback(clean_line)

        return_code = process.wait()

        if return_code != 0:
            raise RuntimeError(
                f"Command failed ({return_code}): {' '.join(command)}\n" + "\n".join(output_lines[-20:])
            )

        return output_lines

    def start_backend(self, python_executable, backend_dir, log_callback, port=DEFAULT_LOCAL_PORT):
        self.stop_backend()
        env = os.environ.copy()
        env["FLASK_DEBUG"] = "false"
        env["HOST"] = "127.0.0.1"
        env["PORT"] = str(port)

        log_file = open(BACKEND_LOG_PATH, "w", encoding="utf-8")
        self.backend_process = subprocess.Popen(
            [str(python_executable), "app.py"],
            cwd=str(backend_dir),
            env=env,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            creationflags=self._creationflags(),
        )
        log_callback("Flask service is starting...")
        self._wait_for_healthcheck(port)
        log_callback(f"Flask service is live on http://127.0.0.1:{port}")

    def stop_backend(self):
        self._stop_process(self.backend_process)
        self.backend_process = None

    def stop_tunnel(self):
        self._stop_process(self.tunnel_process)
        self.tunnel_process = None

    def start_tunnel_process(self, command):
        self.stop_tunnel()
        log_file = open(TUNNEL_LOG_PATH, "w", encoding="utf-8")
        self.tunnel_process = subprocess.Popen(
            command,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            text=True,
            creationflags=self._creationflags(),
        )
        return self.tunnel_process

    def _wait_for_healthcheck(self, port):
        deadline = time.time() + 45

        while time.time() < deadline:
            try:
                with urlopen(f"http://127.0.0.1:{port}/api/health", timeout=2) as response:
                    if response.status == 200:
                        return
            except Exception:
                time.sleep(1)

        raise RuntimeError("Flask health check did not become ready in time.")

    def _stop_process(self, process):
        if process is None:
            return

        if process.poll() is not None:
            return

        process.terminate()

        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()

    def _creationflags(self):
        if os.name == "nt":
            return subprocess.CREATE_NO_WINDOW

        return 0
