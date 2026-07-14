"""
kia/config_dialog.py
  ensure_private_data_file_for_dialog()
  open_private_data_config_dialog()
"""

import copy
import json
import os
import shutil
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk


def resolve_dialog_path(path_value: str) -> Path:
    """
    Expand user-home and Windows environment variables for validation.
    """
    expanded = os.path.expandvars(path_value.strip())
    expanded = os.path.expanduser(expanded)
    return Path(expanded)


def write_private_data_file(private_data_path: Path, private_data: dict) -> None:
    """
    Write private data as readable UTF-8 JSON.
    """
    with private_data_path.open("w", encoding="utf-8") as file:
        json.dump(private_data, file, indent=2)
        file.write("\n")


def ensure_private_data_file_for_dialog(
    private_data_path: Path,
    private_data_example_path: Path,
) -> bool:
    """
    Create the private data file from the example when it is missing.

    Returns True when the private data file exists or was created.
    Returns False when the user cancels startup.
    """
    if private_data_path.exists():
        return True

    if not private_data_example_path.exists():
        messagebox.showerror(
            title="Private Data Missing",
            message=(
                "The private data file is missing, and the example template "
                "could not be found."
            ),
        )
        return False

    create_file = messagebox.askyesno(
        title="Create Private Data File?",
        message=(
            "The private data file is missing.\n\n"
            "Create it from the example template now?"
        ),
    )

    if not create_file:
        return False

    shutil.copy2(private_data_example_path, private_data_path)

    messagebox.showinfo(
        title="Private Data Created",
        message=(
            "The private data file was created from the example template.\n\n"
            "Review and update the values before continuing."
        ),
    )

    return True


def validate_dialog_private_data(private_data: dict) -> list[str]:
    """
    Validate the first-slice private config fields edited by the dialog.
    """
    errors = []

    last_config = private_data.get("last", {})
    libraries = private_data.get("libraries", {})

    if not isinstance(last_config, dict):
        errors.append("The `last` section must be a JSON object.")
        last_config = {}

    if not isinstance(libraries, dict) or not libraries:
        errors.append("At least one library profile is required.")
        libraries = {}

    required_paths = [
        ("Source folder", last_config.get("source_folder", "")),
        ("Library root", last_config.get("library_root", "")),
        ("Library folder", last_config.get("library_folder", "")),
    ]

    for label, path_value in required_paths:
        if not str(path_value).strip():
            errors.append(f"{label} is required.")
            continue

        resolved_path = resolve_dialog_path(str(path_value))

        if not resolved_path.exists() or not resolved_path.is_dir():
            errors.append(f"{label} must be an existing folder.")

    target_library = str(last_config.get("target_library", "")).strip()

    if not target_library:
        errors.append("Target library is required.")
    elif target_library not in libraries:
        errors.append("Target library must match a configured library profile.")
    else:
        selected_library = libraries.get(target_library, {})

        for field_name in ["footprint_dir", "nickname", "schema_profile"]:
            if not str(selected_library.get(field_name, "")).strip():
                errors.append(f"Selected library is missing `{field_name}`.")

    if not str(private_data.get("path_variable", "")).strip():
        errors.append("KiCad path variable is required.")

    return errors


def update_library_summary(
    target_var: tk.StringVar,
    libraries: dict,
    summary_var: tk.StringVar,
) -> None:
    """
    Update the read-only selected-library summary.
    """
    selected_library = target_var.get().strip()
    settings = libraries.get(selected_library, {})

    if not settings:
        summary_var.set("No configured library profile selected.")
        return

    summary_var.set(
        "\n".join(
            [
                f"Prefix: {settings.get('prefix', '')}",
                f"Footprint dir: {settings.get('footprint_dir', '')}",
                f"Symbol file: {settings.get('symbol_file', '')}",
                f"Nickname: {settings.get('nickname', '')}",
                f"Schema profile: {settings.get('schema_profile', '')}",
            ]
        )
    )


def choose_folder(entry_var: tk.StringVar, title: str) -> None:
    """
    Ask for a folder and update an entry variable.
    """
    initial_value = entry_var.get().strip()
    initial_dir = str(resolve_dialog_path(initial_value)) if initial_value else str(Path.home())

    selected_folder = filedialog.askdirectory(
        title=title,
        initialdir=initial_dir,
    )

    if selected_folder:
        entry_var.set(selected_folder)


def center_dialog(dialog: tk.Toplevel) -> None:
    """
    Center a dialog on the active screen after Tk calculates its size.
    """
    dialog.update_idletasks()

    width = dialog.winfo_width()
    height = dialog.winfo_height()
    screen_width = dialog.winfo_screenwidth()
    screen_height = dialog.winfo_screenheight()

    x_position = max((screen_width - width) // 2, 0)
    y_position = max((screen_height - height) // 2, 0)

    dialog.geometry(f"+{x_position}+{y_position}")


def bring_dialog_to_front(dialog: tk.Toplevel) -> None:
    """
    Make the startup dialog visible and focused on Windows console launches.
    """
    center_dialog(dialog)
    dialog.deiconify()
    dialog.lift()
    dialog.attributes("-topmost", True)
    dialog.focus_force()
    dialog.after(750, lambda: dialog.attributes("-topmost", False))


def open_private_data_config_dialog(
    default_config: dict,
    private_data: dict,
    private_data_path: Path,
) -> str:
    """
    Open the startup private data review/edit dialog.

    Returns:
      "save_continue"
      "continue"
      "cancel"
    """
    del default_config

    working_private_data = copy.deepcopy(private_data)
    working_private_data.setdefault("last", {})
    working_private_data.setdefault("libraries", {})

    last_config = working_private_data["last"]
    libraries = working_private_data["libraries"]

    parent = tk._default_root

    if parent is None:
        parent = tk.Tk()
        parent.withdraw()

    dialog = tk.Toplevel(parent)
    dialog.title("KiCad Import Assistant - Private Data Config")
    dialog.resizable(False, False)

    result = {"action": "cancel"}

    source_var = tk.StringVar(value=str(last_config.get("source_folder", "")))
    library_root_var = tk.StringVar(value=str(last_config.get("library_root", "")))
    library_folder_var = tk.StringVar(value=str(last_config.get("library_folder", "")))
    target_var = tk.StringVar(value=str(last_config.get("target_library", "")))
    path_variable_var = tk.StringVar(value=str(working_private_data.get("path_variable", "")))
    library_summary_var = tk.StringVar()

    library_names = list(libraries.keys())

    if target_var.get() not in library_names and library_names:
        target_var.set(library_names[0])

    update_library_summary(target_var, libraries, library_summary_var)

    main_frame = ttk.Frame(dialog, padding=16)
    main_frame.grid(row=0, column=0, sticky="nsew")

    header = ttk.Label(
        main_frame,
        text="Review private/local config before import.",
        font=("", 10, "bold"),
    )
    header.grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 10))

    fields = [
        ("Source folder", source_var, "Browse source folder"),
        ("Library root", library_root_var, "Browse library root"),
        ("Library folder", library_folder_var, "Browse library folder"),
    ]

    for row_index, (label_text, entry_var, browse_title) in enumerate(fields, start=1):
        ttk.Label(main_frame, text=f"{label_text}:").grid(
            row=row_index,
            column=0,
            sticky="w",
            pady=3,
        )
        ttk.Entry(main_frame, textvariable=entry_var, width=72).grid(
            row=row_index,
            column=1,
            sticky="ew",
            pady=3,
            padx=(8, 6),
        )
        ttk.Button(
            main_frame,
            text="Browse...",
            command=lambda var=entry_var, title=browse_title: choose_folder(var, title),
        ).grid(row=row_index, column=2, sticky="ew", pady=3)

    ttk.Label(main_frame, text="Target library:").grid(
        row=4,
        column=0,
        sticky="w",
        pady=3,
    )
    target_combo = ttk.Combobox(
        main_frame,
        textvariable=target_var,
        values=library_names,
        state="readonly" if library_names else "normal",
        width=69,
    )
    target_combo.grid(row=4, column=1, columnspan=2, sticky="ew", pady=3, padx=(8, 0))

    target_combo.bind(
        "<<ComboboxSelected>>",
        lambda event: update_library_summary(target_var, libraries, library_summary_var),
    )

    ttk.Label(main_frame, text="KiCad path variable:").grid(
        row=5,
        column=0,
        sticky="w",
        pady=3,
    )
    ttk.Entry(main_frame, textvariable=path_variable_var, width=72).grid(
        row=5,
        column=1,
        columnspan=2,
        sticky="ew",
        pady=3,
        padx=(8, 0),
    )

    summary_frame = ttk.LabelFrame(main_frame, text="Selected Library Profile", padding=10)
    summary_frame.grid(row=6, column=0, columnspan=3, sticky="ew", pady=(12, 4))

    ttk.Label(
        summary_frame,
        textvariable=library_summary_var,
        justify="left",
    ).grid(row=0, column=0, sticky="w")

    button_frame = ttk.Frame(main_frame)
    button_frame.grid(row=7, column=0, columnspan=3, sticky="e", pady=(12, 0))

    def sync_dialog_values() -> dict:
        updated_private_data = copy.deepcopy(working_private_data)
        updated_private_data.setdefault("last", {})

        updated_private_data["last"]["source_folder"] = source_var.get().strip()
        updated_private_data["last"]["library_root"] = library_root_var.get().strip()
        updated_private_data["last"]["library_folder"] = library_folder_var.get().strip()
        updated_private_data["last"]["target_library"] = target_var.get().strip()
        updated_private_data["path_variable"] = path_variable_var.get().strip()

        return updated_private_data

    def save_and_continue() -> None:
        updated_private_data = sync_dialog_values()
        validation_errors = validate_dialog_private_data(updated_private_data)

        if validation_errors:
            messagebox.showerror(
                title="Config Needs Attention",
                message="\n".join(validation_errors),
            )
            return

        try:
            write_private_data_file(private_data_path, updated_private_data)

        except OSError as error:
            messagebox.showerror(
                title="Save Failed",
                message=f"Could not save private data.\n\n{error}",
            )
            return

        result["action"] = "save_continue"
        dialog.destroy()

    def continue_without_saving() -> None:
        result["action"] = "continue"
        dialog.destroy()

    def cancel() -> None:
        result["action"] = "cancel"
        dialog.destroy()

    ttk.Button(
        button_frame,
        text="Save + Continue",
        command=save_and_continue,
    ).grid(row=0, column=0, padx=(0, 6))
    ttk.Button(
        button_frame,
        text="Continue Without Saving",
        command=continue_without_saving,
    ).grid(row=0, column=1, padx=(0, 6))
    ttk.Button(
        button_frame,
        text="Cancel",
        command=cancel,
    ).grid(row=0, column=2)

    dialog.protocol("WM_DELETE_WINDOW", cancel)
    bring_dialog_to_front(dialog)
    dialog.grab_set()
    dialog.wait_window()

    return result["action"]
