"""
Tkinter GUI shell for the KiCad Import Assistant.
"""

import tkinter as tk
from tkinter import messagebox, ttk

from kia.app_info import APP_VERSION
from kia.gui_log import GuiLogger
from kia.gui_state import GuiAppState


TAB_IDS = {
    "import": 0,
    "config": 1,
    "schema": 2,
}


class KiCadImportAssistantGui:
    """
    Main GUI application shell.
    """

    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title(f"KiCad Import Assistant v{APP_VERSION}")
        self.root.minsize(1100, 800)
        self.root.geometry("1200x850")

        self.state = GuiAppState()
        self.status_var = tk.StringVar(value=self.state.status_message)
        self.primary_action_var = tk.StringVar(value="Apply Import")
        self.reset_action_var = tk.StringVar(value="Reset Import")

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
        ttk.Combobox(
            logging_frame,
            textvariable=self.status_level_var,
            values=["Error", "Warning", "Info", "Debug"],
            state="readonly",
            width=16,
        ).grid(row=0, column=1, sticky="w", padx=(8, 0), pady=4)

        ttk.Label(logging_frame, text="File log level:").grid(row=1, column=0, sticky="w", pady=4)
        self.file_log_level_var = tk.StringVar(value="Off")
        ttk.Combobox(
            logging_frame,
            textvariable=self.file_log_level_var,
            values=["Off", "Error", "Warning", "Info", "Debug"],
            state="readonly",
            width=16,
        ).grid(row=1, column=1, sticky="w", padx=(8, 0), pady=4)

        ttk.Label(logging_frame, text="Max log size:").grid(row=2, column=0, sticky="w", pady=4)
        self.max_log_size_var = tk.StringVar(value="1 MB")
        ttk.Combobox(
            logging_frame,
            textvariable=self.max_log_size_var,
            values=["256 KB", "1 MB", "5 MB"],
            state="readonly",
            width=16,
        ).grid(row=2, column=1, sticky="w", padx=(8, 0), pady=4)

        ttk.Label(logging_frame, text="Retention:").grid(row=3, column=0, sticky="w", pady=4)
        self.retention_var = tk.StringVar(value="Keep last 3 logs")
        ttk.Combobox(
            logging_frame,
            textvariable=self.retention_var,
            values=["Current session only", "Keep last 3 logs", "Keep last 7 logs"],
            state="readonly",
            width=24,
        ).grid(row=3, column=1, sticky="w", padx=(8, 0), pady=4)

        self.redact_paths_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            logging_frame,
            text="Redact private paths when copying/exporting diagnostics",
            variable=self.redact_paths_var,
        ).grid(row=4, column=0, columnspan=2, sticky="w", pady=(8, 0))

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
        self.state.status_message = entry.short_message
        self.state.status_severity = entry.severity
        self.status_var.set(entry.short_message)

    def primary_action(self) -> None:
        self.logger.info(
            "Primary action is not wired yet.",
            category="app",
            function_name="primary_action",
        )

    def reset_current_tab(self) -> None:
        self.logger.info(
            "Reset action is not wired yet.",
            category="app",
            function_name="reset_current_tab",
        )

    def open_log_viewer(self) -> None:
        viewer = tk.Toplevel(self.root)
        viewer.title("KiCad Import Assistant Log")
        viewer.geometry("900x500")
        viewer.minsize(700, 400)
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

        columns = ("timestamp", "severity", "category", "function", "message")
        tree = ttk.Treeview(viewer, columns=columns, show="headings")

        for column in columns:
            tree.heading(column, text=column.title())

        tree.column("timestamp", width=150, stretch=False)
        tree.column("severity", width=80, stretch=False)
        tree.column("category", width=120, stretch=False)
        tree.column("function", width=180, stretch=False)
        tree.column("message", width=360, stretch=True)
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
            tree.delete(*tree.get_children())
            displayed_entries = self.logger.filtered_entries(severity_var.get())

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

        severity_combo.bind("<<ComboboxSelected>>", lambda event: refresh_entries())
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

        self.root.destroy()

    def run(self) -> None:
        self.root.mainloop()


def run_gui_app() -> None:
    app = KiCadImportAssistantGui()
    app.run()
