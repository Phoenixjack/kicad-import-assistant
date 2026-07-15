"""
Tkinter GUI shell for the KiCad Import Assistant.
"""

import json
import os
import re
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

from kia.app_info import APP_VERSION
from kia.gui_log import GuiLogger
from kia.gui_state import GuiAppState, LogSettings


TAB_IDS = {
    "import": 0,
    "config": 1,
    "schema": 2,
}

DEFAULT_WINDOW_GEOMETRY = "1200x850"
MIN_WINDOW_WIDTH = 1100
MIN_WINDOW_HEIGHT = 800
WINDOW_GEOMETRY_PATTERN = re.compile(r"^(\d+)x(\d+)([+-]\d+)?([+-]\d+)?$")
PRIVATE_DATA_PATH = Path(__file__).resolve().parent.parent / "kicad_import_private_data.json"


class KiCadImportAssistantGui:
    """
    Main GUI application shell.
    """

    def __init__(self) -> None:
        self.state = GuiAppState()
        self.load_gui_preferences()

        self.root = tk.Tk()
        self.root.title(f"KiCad Import Assistant v{APP_VERSION}")
        self.root.minsize(MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT)
        self.root.geometry(self.state.window_geometry)

        if self.state.window_state == "zoomed":
            self.root.state("zoomed")

        self.applied_log_settings = LogSettings()
        self.status_var = tk.StringVar(value=self.state.status_message)
        self.primary_action_var = tk.StringVar(value="Apply Import")
        self.reset_action_var = tk.StringVar(value="Reset Import")
        self._logging_controls_ready = False

        self.logger = GuiLogger(
            settings=self.state.log_settings,
            status_callback=self.update_status_from_log,
        )

        self._tab_change_in_progress = False

        self.build_window()
        self.refresh_action_bar()
        self.logger.info(
            "GUI shell ready.",
            category="app",
            function_name="KiCadImportAssistantGui.__init__",
        )

    def load_gui_preferences(self) -> None:
        """
        Load GUI-only preferences from the ignored private data file.
        """
        private_data = self.read_private_data_for_gui()

        if private_data is None:
            return

        gui_preferences = private_data.get("gui", {})

        if not isinstance(gui_preferences, dict):
            return

        geometry = gui_preferences.get("window_geometry", "")
        if self.is_valid_window_geometry(geometry):
            self.state.window_geometry = geometry

        window_state = gui_preferences.get("window_state", "normal")
        if window_state in {"normal", "zoomed"}:
            self.state.window_state = window_state

    def save_gui_preferences(self) -> None:
        """
        Save GUI-only preferences without touching public config files.
        """
        private_data = self.read_private_data_for_gui()

        if private_data is None:
            self.logger.warning(
                "Window placement was not saved because private data is invalid.",
                category="config",
                function_name="save_gui_preferences",
            )
            return

        private_data.setdefault("gui", {})
        private_data["gui"]["window_geometry"] = self.get_current_window_geometry()
        private_data["gui"]["window_state"] = self.get_current_window_state()

        try:
            self.write_private_data_for_gui(private_data)
        except OSError as error:
            del error
            self.logger.warning(
                "Window placement could not be saved.",
                details="Check private data file permissions.",
                category="config",
                function_name="save_gui_preferences",
            )

    def read_private_data_for_gui(self) -> dict | None:
        """
        Quietly read ignored private data for GUI preferences.
        """
        if not PRIVATE_DATA_PATH.exists():
            return {}

        try:
            with PRIVATE_DATA_PATH.open("r", encoding="utf-8") as file:
                private_data = json.load(file)
        except (OSError, json.JSONDecodeError):
            return None

        if not isinstance(private_data, dict):
            return None

        return private_data

    def write_private_data_for_gui(self, private_data: dict) -> None:
        """
        Write ignored private data without exposing local path details.
        """
        with PRIVATE_DATA_PATH.open("w", encoding="utf-8") as file:
            json.dump(private_data, file, indent=2)
            file.write("\n")

    def is_valid_window_geometry(self, geometry: object) -> bool:
        if not isinstance(geometry, str):
            return False

        match = WINDOW_GEOMETRY_PATTERN.match(geometry)
        if match is None:
            return False

        width = int(match.group(1))
        height = int(match.group(2))
        return width >= MIN_WINDOW_WIDTH and height >= MIN_WINDOW_HEIGHT

    def get_current_window_geometry(self) -> str:
        self.root.update_idletasks()
        geometry = self.root.geometry()

        if self.is_valid_window_geometry(geometry):
            return geometry

        return DEFAULT_WINDOW_GEOMETRY

    def get_current_window_state(self) -> str:
        window_state = self.root.state()

        if window_state == "zoomed":
            return "zoomed"

        return "normal"

    def build_window(self) -> None:
        outer = ttk.Frame(self.root, padding=10)
        outer.pack(fill="both", expand=True)

        self.notebook = ttk.Notebook(outer)
        self.notebook.pack(fill="both", expand=True)
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)

        self.import_tab = ttk.Frame(self.notebook, padding=10)
        self.config_tab = ttk.Frame(self.notebook, padding=10)
        self.schema_tab = ttk.Frame(self.notebook, padding=10)

        self.notebook.add(self.import_tab, text="Import")
        self.notebook.add(self.config_tab, text="Config")
        self.notebook.add(self.schema_tab, text="Schema (Read Only)")

        self.build_import_tab()
        self.build_config_tab()
        self.build_schema_tab()
        self.build_action_bar(outer)

        self.root.protocol("WM_DELETE_WINDOW", self.close_application)

    def build_import_tab(self) -> None:
        self.add_placeholder_section(
            self.import_tab,
            title="A. Import Source",
            body="Source selection UI will be wired in V0.20.x after the shell is stable.",
            row=0,
        )
        self.add_placeholder_section(
            self.import_tab,
            title="B. Configure Base Name",
            body="Schema-driven naming controls will appear here.",
            row=1,
        )
        self.add_placeholder_section(
            self.import_tab,
            title="C. Import Actions",
            body="Per-item action dropdowns will appear here.",
            row=2,
        )
        self.add_placeholder_section(
            self.import_tab,
            title="D. Output Preview / Validation Summary",
            body="Generated basename, output plan, warnings, and blockers will appear here.",
            row=3,
        )

    def build_config_tab(self) -> None:
        self.add_placeholder_section(
            self.config_tab,
            title="A. Paths",
            body="Private-data path controls will be embedded here.",
            row=0,
        )
        self.add_placeholder_section(
            self.config_tab,
            title="B. Library Profiles",
            body="Library profile editing will be added here.",
            row=1,
        )

        logging_frame = ttk.LabelFrame(self.config_tab, text="C. Diagnostics / Logging", padding=12)
        logging_frame.grid(row=2, column=0, sticky="ew", pady=8)
        logging_frame.columnconfigure(1, weight=1)

        ttk.Label(logging_frame, text="Status level:").grid(row=0, column=0, sticky="w", pady=4)
        self.status_level_var = tk.StringVar(value="Info")
        self.status_level_combo = ttk.Combobox(
            logging_frame,
            textvariable=self.status_level_var,
            values=["Error", "Warning", "Info", "Debug"],
            state="readonly",
            width=16,
        )
        self.status_level_combo.grid(row=0, column=1, sticky="w", padx=(8, 0), pady=4)

        ttk.Label(logging_frame, text="File log level:").grid(row=1, column=0, sticky="w", pady=4)
        self.file_log_level_var = tk.StringVar(value="Off")
        self.file_log_level_combo = ttk.Combobox(
            logging_frame,
            textvariable=self.file_log_level_var,
            values=["Off", "Error", "Warning", "Info", "Debug"],
            state="readonly",
            width=16,
        )
        self.file_log_level_combo.grid(row=1, column=1, sticky="w", padx=(8, 0), pady=4)

        ttk.Label(logging_frame, text="Max log size:").grid(row=2, column=0, sticky="w", pady=4)
        self.max_log_size_var = tk.StringVar(value="1 MB")
        self.max_log_size_combo = ttk.Combobox(
            logging_frame,
            textvariable=self.max_log_size_var,
            values=["256 KB", "1 MB", "5 MB"],
            state="readonly",
            width=16,
        )
        self.max_log_size_combo.grid(row=2, column=1, sticky="w", padx=(8, 0), pady=4)

        ttk.Label(logging_frame, text="Retention:").grid(row=3, column=0, sticky="w", pady=4)
        self.retention_var = tk.StringVar(value="Keep last 3 logs")
        self.retention_combo = ttk.Combobox(
            logging_frame,
            textvariable=self.retention_var,
            values=["Current session only", "Keep last 3 logs", "Keep last 7 logs"],
            state="readonly",
            width=24,
        )
        self.retention_combo.grid(row=3, column=1, sticky="w", padx=(8, 0), pady=4)

        self.redact_paths_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            logging_frame,
            text="Redact private paths when copying/exporting diagnostics",
            variable=self.redact_paths_var,
            command=self.mark_config_dirty_from_controls,
        ).grid(row=4, column=0, columnspan=2, sticky="w", pady=(8, 0))

        for combo in [
            self.status_level_combo,
            self.file_log_level_combo,
            self.max_log_size_combo,
            self.retention_combo,
        ]:
            combo.bind("<<ComboboxSelected>>", self.mark_config_dirty_from_controls)

        self._logging_controls_ready = True

    def build_schema_tab(self) -> None:
        self.add_placeholder_section(
            self.schema_tab,
            title="Schema Viewer",
            body="Read-only schema viewer placeholder. Editing is intentionally disabled.",
            row=0,
        )

    def add_placeholder_section(self, parent: ttk.Frame, title: str, body: str, row: int) -> None:
        frame = ttk.LabelFrame(parent, text=title, padding=12)
        frame.grid(row=row, column=0, sticky="ew", pady=8)
        parent.columnconfigure(0, weight=1)
        ttk.Label(frame, text=body).grid(row=0, column=0, sticky="w")

    def build_action_bar(self, parent: ttk.Frame) -> None:
        bar = ttk.Frame(parent, padding=(0, 10, 0, 0))
        bar.pack(fill="x")
        bar.columnconfigure(0, weight=1)

        ttk.Label(bar, textvariable=self.status_var).grid(row=0, column=0, sticky="w")

        ttk.Button(
            bar,
            text="View Log",
            command=self.open_log_viewer,
        ).grid(row=0, column=1, padx=(8, 0))

        self.primary_button = ttk.Button(
            bar,
            textvariable=self.primary_action_var,
            command=self.primary_action,
        )
        self.primary_button.grid(row=0, column=2, padx=(8, 0))

        self.reset_button = ttk.Button(
            bar,
            textvariable=self.reset_action_var,
            command=self.reset_current_tab,
        )
        self.reset_button.grid(row=0, column=3, padx=(8, 0))

        ttk.Button(
            bar,
            text="Close",
            command=self.close_application,
        ).grid(row=0, column=4, padx=(8, 0))

    def on_tab_changed(self, event: tk.Event) -> None:
        if self._tab_change_in_progress:
            return

        selected_index = self.notebook.index(self.notebook.select())
        selected_tab = self.tab_name_from_index(selected_index)
        previous_tab = self.state.active_tab

        if previous_tab != selected_tab and self.state.tab_is_dirty(previous_tab):
            self._tab_change_in_progress = True
            self.notebook.select(TAB_IDS[previous_tab])
            self._tab_change_in_progress = False
            self.logger.warning(
                "Finish, save, reset, or cancel the current work before switching tabs.",
                category="navigation",
                function_name="on_tab_changed",
            )
            return

        self.state.active_tab = selected_tab
        self.refresh_action_bar()

    def tab_name_from_index(self, tab_index: int) -> str:
        for tab_name, index in TAB_IDS.items():
            if index == tab_index:
                return tab_name

        return "import"

    def refresh_action_bar(self) -> None:
        active_tab = self.state.active_tab

        if active_tab == "config":
            self.primary_action_var.set("Save Config")
            self.reset_action_var.set("Revert Config")
            if self.state.config_tab.dirty:
                self.primary_button.state(["!disabled"])
                self.reset_button.state(["!disabled"])
            else:
                self.primary_button.state(["disabled"])
                self.reset_button.state(["disabled"])
            return

        if active_tab == "schema":
            self.primary_action_var.set("Schema Read Only")
            self.reset_action_var.set("Reset")
            self.primary_button.state(["disabled"])
            self.reset_button.state(["disabled"])
            return

        self.primary_action_var.set("Apply Import")
        self.reset_action_var.set("Reset Import")
        self.primary_button.state(["disabled"])
        self.reset_button.state(["disabled"])

    def update_status_from_log(self, entry) -> None:
        self.set_status(entry.short_message, entry.severity)

    def set_status(self, message: str, severity: str = "info") -> None:
        self.state.status_message = message
        self.state.status_severity = severity
        self.status_var.set(message)

    def parse_max_log_size_kb(self) -> int:
        value = self.max_log_size_var.get()

        if value == "256 KB":
            return 256

        if value == "5 MB":
            return 5 * 1024

        return 1024

    def parse_retained_log_count(self) -> int:
        value = self.retention_var.get()

        if value == "Current session only":
            return 0

        if value == "Keep last 7 logs":
            return 7

        return 3

    def logging_settings_from_controls(self) -> LogSettings:
        return LogSettings(
            status_level=self.status_level_var.get().lower(),
            file_log_level=self.file_log_level_var.get().lower(),
            max_log_size_kb=self.parse_max_log_size_kb(),
            retained_log_count=self.parse_retained_log_count(),
            redact_private_paths=self.redact_paths_var.get(),
        )

    def apply_logging_settings_to_controls(self, settings: LogSettings) -> None:
        status_level = settings.status_level.capitalize()
        file_log_level = settings.file_log_level.capitalize()

        if file_log_level == "Off":
            file_log_level = "Off"

        self.status_level_var.set(status_level)
        self.file_log_level_var.set(file_log_level)

        if settings.max_log_size_kb == 256:
            self.max_log_size_var.set("256 KB")
        elif settings.max_log_size_kb == 5 * 1024:
            self.max_log_size_var.set("5 MB")
        else:
            self.max_log_size_var.set("1 MB")

        if settings.retained_log_count == 0:
            self.retention_var.set("Current session only")
        elif settings.retained_log_count == 7:
            self.retention_var.set("Keep last 7 logs")
        else:
            self.retention_var.set("Keep last 3 logs")

        self.redact_paths_var.set(settings.redact_private_paths)

    def mark_config_dirty_from_controls(self, event: tk.Event | None = None) -> None:
        del event

        if not self._logging_controls_ready:
            return

        self.state.config_tab.dirty = True
        self.set_status("Config changes pending. Save Config or Revert Config.", "warning")
        self.refresh_action_bar()

    def save_config_action(self) -> None:
        settings = self.logging_settings_from_controls()
        self.applied_log_settings = settings
        self.state.log_settings = settings
        self.logger.update_settings(settings)
        self.state.config_tab.dirty = False
        self.refresh_action_bar()
        self.set_status("Config settings saved for this session.", "success")
        self.logger.info(
            "Config settings saved for this session.",
            category="config",
            function_name="save_config_action",
        )

    def revert_config_action(self) -> None:
        self._logging_controls_ready = False
        self.apply_logging_settings_to_controls(self.applied_log_settings)
        self._logging_controls_ready = True
        self.state.config_tab.dirty = False
        self.refresh_action_bar()
        self.set_status("Config changes reverted.", "info")
        self.logger.info(
            "Config changes reverted.",
            category="config",
            function_name="revert_config_action",
        )

    def primary_action(self) -> None:
        if self.state.active_tab == "config":
            self.save_config_action()
            return

        self.logger.info(
            "Primary action is not wired yet.",
            category="app",
            function_name="primary_action",
        )

    def reset_current_tab(self) -> None:
        if self.state.active_tab == "config":
            self.revert_config_action()
            return

        self.logger.info(
            "Reset action is not wired yet.",
            category="app",
            function_name="reset_current_tab",
        )

    def open_log_viewer(self) -> None:
        self.logger.debug(
            "Log viewer opened.",
            category="diagnostics",
            function_name="open_log_viewer",
        )

        viewer = tk.Toplevel(self.root)
        viewer.title("KiCad Import Assistant Log")
        viewer.geometry("1000x560")
        viewer.minsize(800, 450)
        viewer.transient(self.root)

        controls = ttk.Frame(viewer, padding=10)
        controls.pack(fill="x")

        ttk.Label(controls, text="Severity:").pack(side="left")
        severity_var = tk.StringVar(value="All")
        severity_combo = ttk.Combobox(
            controls,
            textvariable=severity_var,
            values=self.logger.severity_values(),
            state="readonly",
            width=14,
        )
        severity_combo.pack(side="left", padx=(6, 12))

        ttk.Label(controls, text="Category:").pack(side="left")
        category_var = tk.StringVar(value="All")
        category_combo = ttk.Combobox(
            controls,
            textvariable=category_var,
            values=self.logger.category_values(),
            state="readonly",
            width=16,
        )
        category_combo.pack(side="left", padx=(6, 12))

        ttk.Label(controls, text="Function:").pack(side="left")
        function_var = tk.StringVar(value="All")
        function_combo = ttk.Combobox(
            controls,
            textvariable=function_var,
            values=self.logger.function_values(),
            state="readonly",
            width=22,
        )
        function_combo.pack(side="left", padx=(6, 12))

        ttk.Label(controls, text="Search:").pack(side="left")
        search_var = tk.StringVar()
        search_entry = ttk.Entry(controls, textvariable=search_var, width=22)
        search_entry.pack(side="left", padx=(6, 12))

        button_row = ttk.Frame(viewer, padding=(10, 0, 10, 8))
        button_row.pack(fill="x")

        columns = ("timestamp", "severity", "category", "function", "message")
        tree = ttk.Treeview(viewer, columns=columns, show="headings")

        for column in columns:
            tree.heading(column, text=column.title())

        tree.column("timestamp", width=150, stretch=False)
        tree.column("severity", width=80, stretch=False)
        tree.column("category", width=120, stretch=False)
        tree.column("function", width=180, stretch=False)
        tree.column("message", width=420, stretch=True)
        tree.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        details_var = tk.StringVar(value="Select a log entry for details.")
        ttk.Label(
            viewer,
            textvariable=details_var,
            padding=(10, 0, 10, 10),
            wraplength=850,
            justify="left",
        ).pack(fill="x")

        displayed_entries = []

        def refresh_entries() -> None:
            nonlocal displayed_entries
            category_combo["values"] = self.logger.category_values()
            function_combo["values"] = self.logger.function_values()
            tree.delete(*tree.get_children())
            displayed_entries = self.logger.filtered_entries(
                severity_filter=severity_var.get(),
                category_filter=category_var.get(),
                function_filter=function_var.get(),
                text_filter=search_var.get(),
            )

            for index, entry in enumerate(displayed_entries):
                tree.insert(
                    "",
                    "end",
                    iid=str(index),
                    values=(
                        entry.timestamp,
                        entry.severity.upper(),
                        entry.category,
                        entry.function_name,
                        entry.short_message,
                    ),
                )

        def update_details(event: tk.Event) -> None:
            del event
            selected = tree.selection()

            if not selected:
                details_var.set("Select a log entry for details.")
                return

            entry = displayed_entries[int(selected[0])]
            details_var.set(entry.details or entry.short_message)

        def copy_filtered_entries() -> None:
            text = self.logger.format_entries_for_clipboard(displayed_entries)
            viewer.clipboard_clear()
            viewer.clipboard_append(text)
            self.logger.success(
                "Filtered log entries copied.",
                category="diagnostics",
                function_name="copy_filtered_entries",
            )

        def open_log_folder() -> None:
            self.logger.log_dir.mkdir(parents=True, exist_ok=True)
            try:
                os.startfile(self.logger.log_dir)
            except OSError as error:
                messagebox.showerror(
                    title="Open Log Folder Failed",
                    message=str(error),
                )

        ttk.Button(
            button_row,
            text="Refresh",
            command=refresh_entries,
        ).pack(side="left")
        ttk.Button(
            button_row,
            text="Copy Filtered",
            command=copy_filtered_entries,
        ).pack(side="left", padx=(8, 0))
        ttk.Button(
            button_row,
            text="Open Log Folder",
            command=open_log_folder,
        ).pack(side="left", padx=(8, 0))

        severity_combo.bind("<<ComboboxSelected>>", lambda event: refresh_entries())
        category_combo.bind("<<ComboboxSelected>>", lambda event: refresh_entries())
        function_combo.bind("<<ComboboxSelected>>", lambda event: refresh_entries())
        search_entry.bind("<KeyRelease>", lambda event: refresh_entries())
        tree.bind("<<TreeviewSelect>>", update_details)
        refresh_entries()

    def close_application(self) -> None:
        if self.state.has_dirty_work():
            close_anyway = messagebox.askyesno(
                title="Unsaved or unfinished work",
                message="There is unfinished work. Close anyway and discard changes?",
            )

            if not close_anyway:
                return

        self.save_gui_preferences()
        self.root.destroy()

    def run(self) -> None:
        self.root.mainloop()


def run_gui_app() -> None:
    app = KiCadImportAssistantGui()
    app.run()
