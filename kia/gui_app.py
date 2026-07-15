"""
Tkinter GUI shell for the KiCad Import Assistant.
"""

import json
import os
import re
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from kia.app_info import APP_VERSION
from kia.config_dialog import resolve_dialog_path
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
DEFAULT_API_NAMES = ["mouser", "digikey", "octopart_nexar", "snapeda"]
LIBRARY_PROFILE_FIELDS = [
    "prefix",
    "footprint_dir",
    "symbol_file",
    "nickname",
    "schema_profile",
]


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

        self.applied_private_data = self.read_private_data_for_gui() or {}
        self.library_profiles = {}
        self.active_profile_key = ""
        self.api_keys = {}
        self.active_api_name = ""
        self.applied_log_settings = self.state.log_settings
        self.status_var = tk.StringVar(value=self.state.status_message)
        self.primary_action_var = tk.StringVar(value="Apply Import")
        self.reset_action_var = tk.StringVar(value="Reset Import")
        self._config_controls_ready = False

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

        log_settings = gui_preferences.get("logging", {})
        if isinstance(log_settings, dict):
            try:
                self.state.log_settings = LogSettings(
                    status_level=str(log_settings.get("status_level", "info")),
                    file_log_level=str(log_settings.get("file_log_level", "off")),
                    max_log_size_kb=int(log_settings.get("max_log_size_kb", 1024)),
                    retained_log_count=int(log_settings.get("retained_log_count", 3)),
                    redact_private_paths=bool(log_settings.get("redact_private_paths", True)),
                )
            except (TypeError, ValueError):
                self.state.log_settings = LogSettings()

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

        self.build_action_bar(outer)

        self.notebook = ttk.Notebook(outer)
        self.notebook.pack(side="top", fill="both", expand=True)
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
        self._config_controls_ready = False
        self.load_config_draft_from_private_data(self.applied_private_data)

        paths_frame = ttk.LabelFrame(self.config_tab, text="A. Paths", padding=12)
        paths_frame.grid(row=0, column=0, sticky="ew", pady=8)
        paths_frame.columnconfigure(1, weight=1)

        self.source_folder_var = tk.StringVar()
        self.library_root_var = tk.StringVar()
        self.library_folder_var = tk.StringVar()
        self.target_library_var = tk.StringVar()
        self.path_variable_var = tk.StringVar()

        self.add_path_row(paths_frame, 0, "Source folder:", self.source_folder_var, "Select Source Folder")
        self.add_path_row(paths_frame, 1, "Library root:", self.library_root_var, "Select Library Root")
        self.add_path_row(paths_frame, 2, "Library folder:", self.library_folder_var, "Select Library Folder")

        ttk.Label(paths_frame, text="Target library:").grid(row=3, column=0, sticky="w", pady=4)
        self.target_library_combo = ttk.Combobox(
            paths_frame,
            textvariable=self.target_library_var,
            values=[],
            state="readonly",
            width=36,
        )
        self.target_library_combo.grid(row=3, column=1, sticky="ew", padx=(8, 0), pady=4)
        self.target_library_combo.bind("<<ComboboxSelected>>", self.mark_config_dirty_from_controls)

        ttk.Label(paths_frame, text="Path variable:").grid(row=4, column=0, sticky="w", pady=4)
        ttk.Entry(paths_frame, textvariable=self.path_variable_var).grid(
            row=4,
            column=1,
            sticky="ew",
            padx=(8, 0),
            pady=4,
        )

        profiles_frame = ttk.LabelFrame(self.config_tab, text="B. Library Profiles", padding=12)
        profiles_frame.grid(row=1, column=0, sticky="nsew", pady=8)
        profiles_frame.columnconfigure(1, weight=1)
        self.config_tab.rowconfigure(1, weight=1)

        list_frame = ttk.Frame(profiles_frame)
        list_frame.grid(row=0, column=0, rowspan=7, sticky="ns", padx=(0, 12))

        self.profile_listbox = tk.Listbox(list_frame, height=8, exportselection=False, width=24)
        self.profile_listbox.pack(fill="both", expand=True)
        self.profile_listbox.bind("<<ListboxSelect>>", self.on_profile_selected)

        profile_buttons = ttk.Frame(list_frame)
        profile_buttons.pack(fill="x", pady=(8, 0))
        ttk.Button(profile_buttons, text="Add", command=self.add_library_profile).pack(side="left")
        ttk.Button(profile_buttons, text="Duplicate", command=self.duplicate_library_profile).pack(
            side="left",
            padx=(6, 0),
        )
        ttk.Button(profile_buttons, text="Delete", command=self.delete_library_profile).pack(
            side="left",
            padx=(6, 0),
        )

        self.profile_key_var = tk.StringVar()
        self.profile_prefix_var = tk.StringVar()
        self.profile_footprint_dir_var = tk.StringVar()
        self.profile_symbol_file_var = tk.StringVar()
        self.profile_nickname_var = tk.StringVar()
        self.profile_schema_profile_var = tk.StringVar()

        self.add_profile_row(profiles_frame, 0, "Library key:", self.profile_key_var)
        self.add_profile_row(profiles_frame, 1, "Prefix:", self.profile_prefix_var)
        self.add_profile_row(profiles_frame, 2, "Footprint dir:", self.profile_footprint_dir_var)
        self.add_profile_row(profiles_frame, 3, "Symbol file:", self.profile_symbol_file_var)
        self.add_profile_row(profiles_frame, 4, "Nickname:", self.profile_nickname_var)
        self.add_profile_row(profiles_frame, 5, "Schema profile:", self.profile_schema_profile_var)

        api_frame = ttk.LabelFrame(self.config_tab, text="C. API Keys", padding=12)
        api_frame.grid(row=2, column=0, sticky="ew", pady=8)
        api_frame.columnconfigure(1, weight=1)

        ttk.Label(api_frame, text="API:").grid(row=0, column=0, sticky="w", pady=4)
        self.api_name_var = tk.StringVar()
        self.api_combo = ttk.Combobox(
            api_frame,
            textvariable=self.api_name_var,
            values=[],
            state="readonly",
            width=22,
        )
        self.api_combo.grid(row=0, column=1, sticky="w", padx=(8, 0), pady=4)
        self.api_combo.bind("<<ComboboxSelected>>", self.on_api_selected)

        ttk.Label(api_frame, text="API key:").grid(row=1, column=0, sticky="w", pady=4)
        self.api_key_var = tk.StringVar()
        self.api_key_entry = ttk.Entry(api_frame, textvariable=self.api_key_var, show="*")
        self.api_key_entry.grid(row=1, column=1, sticky="ew", padx=(8, 0), pady=4)

        self.api_key_visible_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            api_frame,
            text="Show",
            variable=self.api_key_visible_var,
            command=self.toggle_api_key_visibility,
        ).grid(row=1, column=2, padx=(8, 0), pady=4)
        ttk.Button(api_frame, text="Clear", command=self.clear_api_key).grid(
            row=1,
            column=3,
            padx=(8, 0),
            pady=4,
        )

        logging_frame = ttk.LabelFrame(self.config_tab, text="D. Diagnostics / Logging", padding=12)
        logging_frame.grid(row=3, column=0, sticky="ew", pady=8)
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

        self.apply_private_data_to_config_controls(self.applied_private_data)
        self.apply_logging_settings_to_controls(self.applied_log_settings)
        self.refresh_profile_listbox()
        self.refresh_api_combo()
        self.bind_config_value_traces()
        self._config_controls_ready = True

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

    def add_path_row(
        self,
        parent: ttk.Frame,
        row: int,
        label: str,
        value_var: tk.StringVar,
        browse_title: str,
    ) -> None:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=4)
        ttk.Entry(parent, textvariable=value_var).grid(
            row=row,
            column=1,
            sticky="ew",
            padx=(8, 0),
            pady=4,
        )
        ttk.Button(
            parent,
            text="Browse...",
            command=lambda: self.choose_folder_for_var(value_var, browse_title),
        ).grid(row=row, column=2, padx=(8, 0), pady=4)

    def add_profile_row(
        self,
        parent: ttk.Frame,
        row: int,
        label: str,
        value_var: tk.StringVar,
    ) -> None:
        ttk.Label(parent, text=label).grid(row=row, column=1, sticky="w", pady=4)
        ttk.Entry(parent, textvariable=value_var).grid(
            row=row,
            column=2,
            sticky="ew",
            padx=(8, 0),
            pady=4,
        )

    def choose_folder_for_var(self, value_var: tk.StringVar, title: str) -> None:
        initial_value = value_var.get().strip()
        initial_dir = str(resolve_dialog_path(initial_value)) if initial_value else str(Path.home())

        selected_folder = filedialog.askdirectory(
            title=title,
            initialdir=initial_dir,
        )

        if selected_folder:
            value_var.set(selected_folder)
            self.mark_config_dirty_from_controls()

    def bind_config_value_traces(self) -> None:
        tracked_vars = [
            self.source_folder_var,
            self.library_root_var,
            self.library_folder_var,
            self.path_variable_var,
            self.profile_key_var,
            self.profile_prefix_var,
            self.profile_footprint_dir_var,
            self.profile_symbol_file_var,
            self.profile_nickname_var,
            self.profile_schema_profile_var,
            self.api_key_var,
        ]

        for value_var in tracked_vars:
            value_var.trace_add("write", self.mark_config_dirty_from_trace)

    def mark_config_dirty_from_trace(self, *_args) -> None:
        self.mark_config_dirty_from_controls()

    def load_config_draft_from_private_data(self, private_data: dict) -> None:
        libraries = private_data.get("libraries", {})
        if not isinstance(libraries, dict):
            libraries = {}

        self.library_profiles = {
            str(key): dict(value) if isinstance(value, dict) else {}
            for key, value in libraries.items()
        }

        api_integrations = private_data.get("api_integrations", {})
        if not isinstance(api_integrations, dict):
            api_integrations = {}

        api_keys = api_integrations.get("keys", {})
        if not isinstance(api_keys, dict):
            api_keys = {}

        self.api_keys = {str(key): str(value) for key, value in api_keys.items()}
        for api_name in DEFAULT_API_NAMES:
            self.api_keys.setdefault(api_name, "")

    def apply_private_data_to_config_controls(self, private_data: dict) -> None:
        last_config = private_data.get("last", {})
        if not isinstance(last_config, dict):
            last_config = {}

        self.source_folder_var.set(str(last_config.get("source_folder", "")))
        self.library_root_var.set(str(last_config.get("library_root", "")))
        self.library_folder_var.set(str(last_config.get("library_folder", "")))
        self.target_library_var.set(str(last_config.get("target_library", "")))
        self.path_variable_var.set(str(private_data.get("path_variable", "")))

    def refresh_profile_listbox(self) -> None:
        self.profile_listbox.delete(0, tk.END)

        for profile_key in sorted(self.library_profiles):
            self.profile_listbox.insert(tk.END, profile_key)

        profile_keys = list(self.profile_listbox.get(0, tk.END))
        self.target_library_combo["values"] = profile_keys

        target_library = self.target_library_var.get().strip()
        if target_library not in self.library_profiles and profile_keys:
            self.target_library_var.set(profile_keys[0])

        if target_library in self.library_profiles:
            self.select_profile_by_key(target_library)
        elif profile_keys:
            self.select_profile_by_key(profile_keys[0])
        else:
            self.load_profile_to_controls("", {})

    def select_profile_by_key(self, profile_key: str) -> None:
        profile_keys = list(self.profile_listbox.get(0, tk.END))

        if profile_key not in profile_keys:
            return

        index = profile_keys.index(profile_key)
        self.profile_listbox.selection_clear(0, tk.END)
        self.profile_listbox.selection_set(index)
        self.profile_listbox.activate(index)
        self.profile_listbox.see(index)
        self.load_profile_to_controls(profile_key, self.library_profiles.get(profile_key, {}))

    def load_profile_to_controls(self, profile_key: str, profile_data: dict) -> None:
        self.active_profile_key = profile_key
        self.profile_key_var.set(profile_key)
        self.profile_prefix_var.set(str(profile_data.get("prefix", "")))
        self.profile_footprint_dir_var.set(str(profile_data.get("footprint_dir", "")))
        self.profile_symbol_file_var.set(str(profile_data.get("symbol_file", "")))
        self.profile_nickname_var.set(str(profile_data.get("nickname", "")))
        self.profile_schema_profile_var.set(str(profile_data.get("schema_profile", "")))

    def sync_current_profile_from_controls(self) -> bool:
        if not self.active_profile_key and not self.profile_key_var.get().strip():
            return True

        new_key = self.profile_key_var.get().strip()

        if not new_key:
            return False

        if (
            self.active_profile_key
            and new_key != self.active_profile_key
            and new_key in self.library_profiles
        ):
            return False

        previous_key = self.active_profile_key
        profile_data = {
            "prefix": self.profile_prefix_var.get().strip(),
            "footprint_dir": self.profile_footprint_dir_var.get().strip(),
            "symbol_file": self.profile_symbol_file_var.get().strip(),
            "nickname": self.profile_nickname_var.get().strip(),
            "schema_profile": self.profile_schema_profile_var.get().strip(),
        }

        if self.active_profile_key and new_key != self.active_profile_key:
            self.library_profiles.pop(self.active_profile_key, None)

        self.library_profiles[new_key] = profile_data
        self.active_profile_key = new_key

        if self.target_library_var.get().strip() == previous_key:
            self.target_library_var.set(new_key)

        return True

    def on_profile_selected(self, event: tk.Event) -> None:
        del event

        selected = self.profile_listbox.curselection()
        if not selected:
            return

        selected_key = self.profile_listbox.get(selected[0])

        if selected_key == self.active_profile_key:
            return

        previous_key = self.active_profile_key
        if self._config_controls_ready and not self.sync_current_profile_from_controls():
            self.set_status("Current library profile has an invalid or duplicate key.", "warning")
            self.select_profile_by_key(self.active_profile_key)
            return

        if previous_key and previous_key != self.active_profile_key:
            self.refresh_profile_listbox()
            if selected_key in self.library_profiles:
                self.select_profile_by_key(selected_key)
            return

        controls_were_ready = self._config_controls_ready
        self._config_controls_ready = False
        self.load_profile_to_controls(selected_key, self.library_profiles.get(selected_key, {}))
        self._config_controls_ready = controls_were_ready

    def unique_profile_key(self, base_key: str) -> str:
        candidate = base_key
        index = 2

        while candidate in self.library_profiles:
            candidate = f"{base_key}_{index}"
            index += 1

        return candidate

    def add_library_profile(self) -> None:
        if not self.sync_current_profile_from_controls():
            self.set_status("Current library profile has an invalid or duplicate key.", "warning")
            return

        profile_key = self.unique_profile_key("NEW_LIBRARY")
        self.library_profiles[profile_key] = {
            "prefix": "",
            "footprint_dir": "",
            "symbol_file": "",
            "nickname": "",
            "schema_profile": "",
        }
        self.refresh_profile_listbox()
        self.select_profile_by_key(profile_key)
        self.mark_config_dirty_from_controls()

    def duplicate_library_profile(self) -> None:
        if not self.sync_current_profile_from_controls():
            self.set_status("Current library profile has an invalid or duplicate key.", "warning")
            return

        if not self.active_profile_key:
            return

        profile_key = self.unique_profile_key(f"{self.active_profile_key}_COPY")
        self.library_profiles[profile_key] = dict(self.library_profiles.get(self.active_profile_key, {}))
        self.refresh_profile_listbox()
        self.select_profile_by_key(profile_key)
        self.mark_config_dirty_from_controls()

    def delete_library_profile(self) -> None:
        if not self.active_profile_key:
            return

        delete_profile = messagebox.askyesno(
            title="Delete Library Profile",
            message=f"Delete library profile '{self.active_profile_key}'?",
        )

        if not delete_profile:
            return

        self.library_profiles.pop(self.active_profile_key, None)
        self.active_profile_key = ""
        self.refresh_profile_listbox()
        self.mark_config_dirty_from_controls()

    def refresh_api_combo(self) -> None:
        default_names = [api_name for api_name in DEFAULT_API_NAMES if api_name in self.api_keys]
        extra_names = sorted(api_name for api_name in self.api_keys if api_name not in DEFAULT_API_NAMES)
        api_names = default_names + extra_names
        self.api_combo["values"] = api_names

        if api_names:
            selected_api = self.active_api_name if self.active_api_name in api_names else api_names[0]
            self.api_name_var.set(selected_api)
            self.load_api_key_to_controls(selected_api)
        else:
            self.api_name_var.set("")
            self.active_api_name = ""
            self.api_key_var.set("")

    def load_api_key_to_controls(self, api_name: str) -> None:
        self.active_api_name = api_name
        self.api_name_var.set(api_name)
        self.api_key_var.set(self.api_keys.get(api_name, ""))

    def sync_current_api_from_controls(self) -> None:
        if self.active_api_name:
            self.api_keys[self.active_api_name] = self.api_key_var.get()

    def on_api_selected(self, event: tk.Event) -> None:
        del event
        self.sync_current_api_from_controls()
        controls_were_ready = self._config_controls_ready
        self._config_controls_ready = False
        self.load_api_key_to_controls(self.api_name_var.get())
        self._config_controls_ready = controls_were_ready

    def toggle_api_key_visibility(self) -> None:
        self.api_key_entry.configure(show="" if self.api_key_visible_var.get() else "*")

    def clear_api_key(self) -> None:
        self.api_key_var.set("")
        self.mark_config_dirty_from_controls()

    def build_action_bar(self, parent: ttk.Frame) -> None:
        bar = ttk.Frame(parent, padding=(0, 10, 0, 0))
        bar.pack(side="bottom", fill="x")
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

        if not self._config_controls_ready:
            return

        self.state.config_tab.dirty = True
        self.set_status("Config changes pending. Save Config or Revert Config.", "warning")
        self.refresh_action_bar()

    def validate_config_controls(self) -> list[str]:
        errors = []

        required_paths = [
            ("Source folder", self.source_folder_var.get()),
            ("Library root", self.library_root_var.get()),
            ("Library folder", self.library_folder_var.get()),
        ]

        for label, path_value in required_paths:
            if not path_value.strip():
                errors.append(f"{label} is required.")
                continue

            resolved_path = resolve_dialog_path(path_value)
            if not resolved_path.exists() or not resolved_path.is_dir():
                errors.append(f"{label} must be an existing folder.")

        if not self.path_variable_var.get().strip():
            errors.append("Path variable is required.")

        target_library = self.target_library_var.get().strip()
        if not target_library:
            errors.append("Target library is required.")
        elif target_library not in self.library_profiles:
            errors.append("Target library must match a configured library profile.")

        if not self.library_profiles:
            errors.append("At least one library profile is required.")

        for profile_key, profile_data in self.library_profiles.items():
            if not profile_key.strip():
                errors.append("Library profile keys cannot be blank.")

            for field_name in LIBRARY_PROFILE_FIELDS:
                if not str(profile_data.get(field_name, "")).strip():
                    errors.append(f"Library profile '{profile_key}' is missing {field_name}.")

        return errors

    def build_private_data_from_config_controls(self) -> dict | None:
        if not self.sync_current_profile_from_controls():
            self.set_status("Current library profile has an invalid or duplicate key.", "warning")
            return None

        self.sync_current_api_from_controls()

        private_data = self.read_private_data_for_gui()
        if private_data is None:
            messagebox.showerror(
                title="Config Save Failed",
                message="Private data is invalid. Fix the JSON file before saving from the GUI.",
            )
            return None

        private_data.setdefault("last", {})
        private_data["last"]["source_folder"] = self.source_folder_var.get().strip()
        private_data["last"]["library_root"] = self.library_root_var.get().strip()
        private_data["last"]["library_folder"] = self.library_folder_var.get().strip()
        private_data["last"]["target_library"] = self.target_library_var.get().strip()

        private_data["path_variable"] = self.path_variable_var.get().strip()
        private_data["libraries"] = {
            profile_key: dict(profile_data)
            for profile_key, profile_data in sorted(self.library_profiles.items())
        }

        private_data.setdefault("api_integrations", {})
        private_data["api_integrations"]["keys"] = dict(sorted(self.api_keys.items()))

        settings = self.logging_settings_from_controls()
        private_data.setdefault("gui", {})
        private_data["gui"]["logging"] = {
            "status_level": settings.status_level,
            "file_log_level": settings.file_log_level,
            "max_log_size_kb": settings.max_log_size_kb,
            "retained_log_count": settings.retained_log_count,
            "redact_private_paths": settings.redact_private_paths,
        }

        return private_data

    def save_config_action(self) -> None:
        private_data = self.build_private_data_from_config_controls()

        if private_data is None:
            return

        validation_errors = self.validate_config_controls()
        if validation_errors:
            messagebox.showerror(
                title="Config Validation Failed",
                message="\n".join(validation_errors[:8]),
            )
            self.logger.warning(
                "Config was not saved because validation failed.",
                details="\n".join(validation_errors),
                category="config",
                function_name="save_config_action",
            )
            return

        settings = self.logging_settings_from_controls()

        try:
            self.write_private_data_for_gui(private_data)
        except OSError as error:
            del error
            messagebox.showerror(
                title="Config Save Failed",
                message="Could not save private data. Check file permissions.",
            )
            return

        self.applied_private_data = private_data
        self.applied_log_settings = settings
        self.state.log_settings = settings
        self.logger.update_settings(settings)
        self._config_controls_ready = False
        self.load_config_draft_from_private_data(self.applied_private_data)
        self.refresh_profile_listbox()
        self.refresh_api_combo()
        self._config_controls_ready = True
        self.state.config_tab.dirty = False
        self.refresh_action_bar()
        self.set_status("Config saved.", "success")
        self.logger.info(
            "Config saved.",
            category="config",
            function_name="save_config_action",
        )

    def revert_config_action(self) -> None:
        self._config_controls_ready = False
        self.load_config_draft_from_private_data(self.applied_private_data)
        self.apply_private_data_to_config_controls(self.applied_private_data)
        self.refresh_profile_listbox()
        self.refresh_api_combo()
        self.apply_logging_settings_to_controls(self.applied_log_settings)
        self._config_controls_ready = True
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
