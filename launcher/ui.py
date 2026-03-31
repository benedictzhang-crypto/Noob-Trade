from pathlib import Path
import queue
import threading
import traceback
import webbrowser
import tkinter as tk

import customtkinter as ctk
from PIL import Image

from launcher.config import APP_NAME, DEFAULT_LOCAL_PORT, PROJECT_ROOT, REPO_URL
from launcher.services.build_service import BuildService
from launcher.services.environment_service import EnvironmentService
from launcher.services.git_service import GitService
from launcher.services.process_service import ProcessService
from launcher.services.tunnel_service import TunnelService


class NoobTradeLauncher(ctk.CTk):
    """Small desktop GUI for syncing, building, launching, and sharing Noob Trade."""

    def __init__(self):
        super().__init__()
        self.title(APP_NAME)
        self.geometry("960x700")
        self.minsize(900, 640)

        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")

        self.project_root = PROJECT_ROOT
        self.log_queue = queue.Queue()
        self.is_busy = False
        self.current_share_url = ""
        self.window_icon = None

        self.environment_service = EnvironmentService()
        self.process_service = ProcessService()
        self.tooling = self.environment_service.get_tooling_snapshot()
        self.git_service = GitService(self.process_service, self.tooling.git_command, REPO_URL) if self.tooling.git_command else None
        self.build_service = (
            BuildService(
                self.process_service,
                self.tooling.python_command,
                self.tooling.npm_command,
                self.environment_service,
            )
            if self.tooling.python_command and self.tooling.npm_command
            else None
        )
        self.tunnel_service = TunnelService(self.process_service, self.tooling.ssh_command) if self.tooling.ssh_command else None

        self.github_status = ctk.StringVar(value="Waiting")
        self.build_status = ctk.StringVar(value="Waiting")
        self.backend_status = ctk.StringVar(value="Stopped")
        self.link_status = ctk.StringVar(value="No link yet")
        self.link_value = ctk.StringVar(value="")

        self._configure_app_icon()
        self._build_layout()
        self.after(150, self._pump_logs)
        self.after(350, self.start_full_cycle)
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def _configure_app_icon(self):
        assets_dir = Path(__file__).resolve().parent / "assets"
        png_icon = assets_dir / "noobtrade_icon.png"
        ico_icon = assets_dir / "noobtrade.ico"

        if png_icon.exists():
            try:
                self.window_icon = tk.PhotoImage(file=str(png_icon))
                self.iconphoto(True, self.window_icon)
            except Exception:
                pass

        if ico_icon.exists():
            try:
                self.iconbitmap(str(ico_icon))
            except Exception:
                pass

    def _build_layout(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(4, weight=1)

        header = ctk.CTkFrame(self, corner_radius=18)
        header.grid(row=0, column=0, padx=20, pady=(20, 12), sticky="ew")
        header.grid_columnconfigure(0, weight=1)
        logo_path = Path(__file__).resolve().parent / "assets" / "noobtrade_icon.png"

        if logo_path.exists():
            try:
                logo_image = ctk.CTkImage(light_image=Image.open(logo_path), size=(64, 64))
                self.logo_label = ctk.CTkLabel(header, text="", image=logo_image)
                self.logo_label.image = logo_image
                self.logo_label.grid(row=0, column=0, rowspan=2, padx=(20, 14), pady=18, sticky="w")
                title_padx = (98, 20)
            except Exception:
                title_padx = 20
        else:
            title_padx = 20

        ctk.CTkLabel(
            header,
            text="Noob Trade Launcher",
            font=ctk.CTkFont(size=28, weight="bold"),
        ).grid(row=0, column=0, padx=title_padx, pady=(18, 4), sticky="w")
        ctk.CTkLabel(
            header,
            text=f"Project root: {self.project_root}",
            font=ctk.CTkFont(size=13),
            text_color="#5b6472",
        ).grid(row=1, column=0, padx=title_padx, pady=(0, 18), sticky="w")

        status_frame = ctk.CTkFrame(self, corner_radius=18)
        status_frame.grid(row=1, column=0, padx=20, pady=12, sticky="ew")
        status_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)
        self._status_card(status_frame, 0, "GitHub Sync", self.github_status)
        self._status_card(status_frame, 1, "Build", self.build_status)
        self._status_card(status_frame, 2, "Flask Service", self.backend_status)
        self._status_card(status_frame, 3, "Share Link", self.link_status)

        link_frame = ctk.CTkFrame(self, corner_radius=18)
        link_frame.grid(row=2, column=0, padx=20, pady=12, sticky="ew")
        link_frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            link_frame,
            text="Temporary HTTPS Link",
            font=ctk.CTkFont(size=18, weight="bold"),
        ).grid(row=0, column=0, padx=20, pady=(18, 8), sticky="w")
        self.link_entry = ctk.CTkEntry(link_frame, textvariable=self.link_value, height=42)
        self.link_entry.grid(row=1, column=0, padx=(20, 10), pady=(0, 18), sticky="ew")
        ctk.CTkButton(link_frame, text="Copy Link", width=120, command=self.copy_link).grid(
            row=1, column=1, padx=(0, 10), pady=(0, 18)
        )
        ctk.CTkButton(link_frame, text="Open Link", width=120, command=self.open_link).grid(
            row=1, column=2, padx=(0, 20), pady=(0, 18)
        )

        action_frame = ctk.CTkFrame(self, corner_radius=18)
        action_frame.grid(row=3, column=0, padx=20, pady=12, sticky="ew")
        action_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)
        self.start_button = ctk.CTkButton(action_frame, text="启动", command=self.start_full_cycle)
        self.start_button.grid(row=0, column=0, padx=16, pady=16, sticky="ew")
        self.update_button = ctk.CTkButton(action_frame, text="一键更新", command=self.update_everything)
        self.update_button.grid(row=0, column=1, padx=16, pady=16, sticky="ew")
        self.stop_button = ctk.CTkButton(action_frame, text="停止服务", command=self.stop_everything)
        self.stop_button.grid(row=0, column=2, padx=16, pady=16, sticky="ew")
        self.relink_button = ctk.CTkButton(action_frame, text="重新生成链接", command=self.regenerate_link)
        self.relink_button.grid(row=0, column=3, padx=16, pady=16, sticky="ew")

        log_frame = ctk.CTkFrame(self, corner_radius=18)
        log_frame.grid(row=4, column=0, padx=20, pady=(12, 20), sticky="nsew")
        log_frame.grid_rowconfigure(1, weight=1)
        log_frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            log_frame,
            text="Launcher Log",
            font=ctk.CTkFont(size=18, weight="bold"),
        ).grid(row=0, column=0, padx=20, pady=(18, 8), sticky="w")
        self.log_box = ctk.CTkTextbox(log_frame, corner_radius=12, font=ctk.CTkFont(size=13))
        self.log_box.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="nsew")
        self.log_box.insert("end", "Launcher is ready.\n")
        self.log_box.configure(state="disabled")

    def _status_card(self, parent, column, title, variable):
        card = ctk.CTkFrame(parent, corner_radius=14)
        card.grid(row=0, column=column, padx=10, pady=14, sticky="ew")
        ctk.CTkLabel(card, text=title, font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=14, pady=(14, 4))
        ctk.CTkLabel(card, textvariable=variable, font=ctk.CTkFont(size=15)).pack(anchor="w", padx=14, pady=(0, 14))

    def enqueue_log(self, message):
        self.log_queue.put(message)

    def set_status(self, variable, value):
        self.after(0, lambda: variable.set(value))

    def set_link(self, value):
        self.after(0, lambda: self.link_value.set(value))

    def _pump_logs(self):
        while True:
            try:
                message = self.log_queue.get_nowait()
            except queue.Empty:
                break

            self.log_box.configure(state="normal")
            self.log_box.insert("end", f"{message}\n")
            self.log_box.see("end")
            self.log_box.configure(state="disabled")

        self.after(150, self._pump_logs)

    def copy_link(self):
        if not self.link_value.get():
            return

        self.clipboard_clear()
        self.clipboard_append(self.link_value.get())
        self.enqueue_log("Share link copied to clipboard.")

    def open_link(self):
        if self.link_value.get():
            webbrowser.open(self.link_value.get())

    def start_full_cycle(self):
        self._run_async(self._perform_full_start)

    def update_everything(self):
        self._run_async(self._perform_update_cycle)

    def stop_everything(self):
        self._run_async(self._perform_stop_cycle)

    def regenerate_link(self):
        self._run_async(self._perform_regenerate_link)

    def _run_async(self, task):
        if self.is_busy:
            self.enqueue_log("Launcher is busy. Please wait for the current action to finish.")
            return

        worker = threading.Thread(target=self._execute_task, args=(task,), daemon=True)
        worker.start()

    def _execute_task(self, task):
        self.is_busy = True
        self._set_buttons_state("disabled")

        try:
            task()
        except Exception as error:
            self.enqueue_log(str(error))
            self.enqueue_log(traceback.format_exc().strip())
        finally:
            self.is_busy = False
            self._set_buttons_state("normal")

    def _perform_full_start(self):
        self._validate_environment()
        self.set_status(self.github_status, "Syncing")
        project_root = self.git_service.ensure_repo_ready(self.project_root, self.enqueue_log)
        self.set_status(self.github_status, "Up to date")

        self.set_status(self.build_status, "Preparing")
        backend_python = self.build_service.ensure_backend_environment(project_root, self.enqueue_log)
        self.build_service.install_frontend_dependencies(project_root, self.enqueue_log)
        self.build_service.build_frontend(project_root, self.enqueue_log)
        self.set_status(self.build_status, "Ready")

        self.process_service.start_backend(
            python_executable=backend_python,
            backend_dir=project_root / "backend",
            log_callback=self.enqueue_log,
            port=DEFAULT_LOCAL_PORT,
        )
        self.set_status(self.backend_status, "Running")

        share_url = self.tunnel_service.create_tunnel(self.enqueue_log, local_port=DEFAULT_LOCAL_PORT)
        self.current_share_url = share_url
        self.set_link(share_url)
        self.set_status(self.link_status, "Active")

    def _perform_update_cycle(self):
        self.enqueue_log("Running one-click update...")
        self.process_service.stop_tunnel()
        self.process_service.stop_backend()
        self.set_link("")
        self.set_status(self.link_status, "Refreshing")
        self.set_status(self.backend_status, "Stopped")
        self._perform_full_start()

    def _perform_stop_cycle(self):
        self.enqueue_log("Stopping Flask and localhost.run...")
        self.process_service.stop_tunnel()
        self.process_service.stop_backend()
        self.set_link("")
        self.current_share_url = ""
        self.set_status(self.backend_status, "Stopped")
        self.set_status(self.link_status, "Stopped")
        self.set_status(self.github_status, "Idle")
        self.set_status(self.build_status, "Idle")

    def _perform_regenerate_link(self):
        self._validate_environment()

        if self.process_service.backend_process is None or self.process_service.backend_process.poll() is not None:
            raise RuntimeError("Flask service is not running yet. Start the launcher first.")

        self.process_service.stop_tunnel()
        self.set_status(self.link_status, "Refreshing")
        share_url = self.tunnel_service.create_tunnel(self.enqueue_log, local_port=DEFAULT_LOCAL_PORT)
        self.current_share_url = share_url
        self.set_link(share_url)
        self.set_status(self.link_status, "Active")

    def _validate_environment(self):
        missing_tools = self.tooling.missing

        if missing_tools:
            raise RuntimeError(
                "Missing required tools: " + ", ".join(missing_tools) +
                ". Please install them before using the launcher."
            )

    def _set_buttons_state(self, state):
        self.after(0, lambda: self.start_button.configure(state=state))
        self.after(0, lambda: self.update_button.configure(state=state))
        self.after(0, lambda: self.stop_button.configure(state=state))
        self.after(0, lambda: self.relink_button.configure(state=state))

    def on_close(self):
        self.process_service.stop_tunnel()
        self.process_service.stop_backend()
        self.destroy()
