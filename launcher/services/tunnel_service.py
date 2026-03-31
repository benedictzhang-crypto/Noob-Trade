from pathlib import Path
import re
import time

from launcher.config import DEFAULT_LOCAL_PORT, DEFAULT_TUNNEL_HOST, TUNNEL_LOG_PATH


class TunnelService:
    """Create and monitor a localhost.run HTTPS sharing tunnel."""

    URL_PATTERN = re.compile(r"https://[a-zA-Z0-9./?=_:-]+")

    def __init__(self, process_service, ssh_command):
        self.process_service = process_service
        self.ssh_command = ssh_command

    def create_tunnel(self, log_callback, local_port=DEFAULT_LOCAL_PORT):
        command = [
            *self.ssh_command,
            "-o",
            "StrictHostKeyChecking=no",
            "-o",
            "ServerAliveInterval=30",
            "-o",
            "ExitOnForwardFailure=yes",
            "-R",
            f"80:127.0.0.1:{local_port}",
            f"nokey@{DEFAULT_TUNNEL_HOST}",
        ]

        log_callback("Opening temporary HTTPS tunnel...")
        self.process_service.start_tunnel_process(command)

        deadline = time.time() + 45

        while time.time() < deadline:
            log_text = Path(TUNNEL_LOG_PATH).read_text(encoding="utf-8", errors="ignore") if Path(TUNNEL_LOG_PATH).exists() else ""
            match = self.URL_PATTERN.search(log_text)

            if match:
                share_url = match.group(0)
                log_callback(f"Public share link ready: {share_url}")
                return share_url

            if self.process_service.tunnel_process and self.process_service.tunnel_process.poll() is not None:
                raise RuntimeError("Tunnel process exited before a public URL was assigned.")

            time.sleep(1)

        raise RuntimeError("Timed out while waiting for localhost.run to publish a link.")
