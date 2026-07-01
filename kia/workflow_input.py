"""
kia/workflow_input.py
  collect_and_validate_user_input()
  resolve_target_library()
"""

import os
from pathlib import Path
from tkinter import filedialog, messagebox
from kia.symbol_resolver import resolve_target_symbol_file
from kia.debug import (
    dbg_blank,
    dbg_print, 
    Severity, 
)
from kia.workflow_status import (
    mark_success, 
    mark_failure, 
)

ALLOWED_IMPORT_SOURCE_SUFFIXES = {
    ".zip",
    ".kicad_mod",
    ".kicad_sym",
    ".step",
    ".stp",
}

MODEL_SUFFIXES = {".step", ".stp"}


def is_pretty_folder(path: Path) -> bool:
    """
    Return True if the selected path appears to be a KiCad .pretty folder.
    """
    return path.suffix.lower() == ".pretty"


def classify_import_source_selection(paths: list[Path]) -> tuple[str, list[Path]]:
    """
    Classify selected import source files.

    Valid:
      - exactly one ZIP file
      - one loose import set:
          up to one .kicad_mod
          up to one .kicad_sym
          up to one .step/.stp

    Returns:
      ("zip", [zip_path])
      ("loose_files", [paths...])

    Raises:
      ValueError for invalid combinations.
    """
    if not paths:
        raise ValueError("No files were selected.")

    invalid_suffixes = [
        path for path in paths
        if path.suffix.lower() not in ALLOWED_IMPORT_SOURCE_SUFFIXES
    ]

    if invalid_suffixes:
        raise ValueError(
            "Unsupported file type selected:\n"
            + "\n".join(f"- {path.name}" for path in invalid_suffixes)
        )

    zip_files = [
        path for path in paths
        if path.suffix.lower() == ".zip"
    ]

    loose_files = [
        path for path in paths
        if path.suffix.lower() != ".zip"
    ]

    if zip_files and loose_files:
        raise ValueError(
            "Choose either one ZIP file OR one loose symbol/footprint/model set.\n"
            "Do not mix ZIP files with loose files."
        )

    if len(zip_files) > 1:
        raise ValueError("Choose only one ZIP file at a time.")

    if len(zip_files) == 1:
        return "zip", zip_files

    footprints = [
        path for path in loose_files
        if path.suffix.lower() == ".kicad_mod"
    ]

    symbols = [
        path for path in loose_files
        if path.suffix.lower() == ".kicad_sym"
    ]

    models = [
        path for path in loose_files
        if path.suffix.lower() in MODEL_SUFFIXES
    ]

    errors = []

    if len(footprints) > 1:
        errors.append("Choose only one footprint file (.kicad_mod).")

    if len(symbols) > 1:
        errors.append("Choose only one symbol file (.kicad_sym).")

    if len(models) > 1:
        errors.append("Choose only one 3D model file (.step/.stp).")

    if errors:
        raise ValueError("\n".join(errors))

    return "loose_files", loose_files


def select_target_library_profile(config: dict, suggested_profile: str | None = None) -> str:
    """
    Ask the user which configured target library to use.
    """
    libraries = config.get("libraries", {})

    if not libraries:
        print()
        print("ERROR: No target library profiles are configured.")
        print("Check kicad_import_private_data.json.")
        raise SystemExit

    library_names = list(libraries.keys())
    last_config = config.get("last", {})

    default_library = (
        suggested_profile
        or last_config.get("target_library")
        or library_names[0]
    )

    if default_library not in libraries:
        default_library = library_names[0]

    print()
    print("Target library profiles:")

    for index, library_name in enumerate(library_names):
        settings = libraries[library_name]
        default_marker = "  <default>" if library_name == default_library else ""
        print(
            f"  {index}. {library_name}"
            f" -> {settings.get('footprint_dir')}"
            f"{default_marker}"
        )

    user_input = input(f"Target library profile [{default_library}]: ").strip()

    if user_input == "":
        selected_library = default_library

    elif user_input.isdigit():
        selected_index = int(user_input)

        if selected_index < 0 or selected_index >= len(library_names):
            print()
            print("ERROR: Invalid target library profile number.")
            raise SystemExit

        selected_library = library_names[selected_index]

    elif user_input in libraries:
        selected_library = user_input

    else:
        print()
        print("ERROR: Unknown target library profile.")
        print(f"  Entered: {user_input}")
        raise SystemExit

    config.setdefault("last", {})
    config["last"]["target_library"] = selected_library

    return selected_library


def infer_profile_from_selected_folder(selected_folder: Path, config: dict) -> str | None:
    """
    Infer a library profile from the selected .pretty folder.
    """
    if not is_pretty_folder(selected_folder):
        dbg_print(
            "Selected folder is not a .pretty folder; no profile inferred.",
            Severity.INFO,
            "libraries",
            stage="infer",
            source="library_resolution",
        )
        return None

    selected_folder_name = selected_folder.name

    for profile_name, settings in config.get("libraries", {}).items():
        if settings.get("footprint_dir") == selected_folder_name:
            dbg_print(
                f"Inferred profile '{profile_name}' from folder '{selected_folder_name}'.",
                Severity.INFO,
                "libraries",
                stage="infer",
                source="library_resolution",
            )
            return profile_name

    dbg_print(
        f"No configured profile matched selected folder '{selected_folder_name}'.",
        Severity.WARNING,
        "libraries",
        stage="infer",
        source="library_resolution",
    )

    return None


def resolve_library_root_from_selection(selected_folder: Path) -> Path:
    """
    Resolve the KiCad custom library root from the selected folder.

    If the user selected a .pretty folder, the library root is its parent.
    If the user selected the custom library root directly, use it as-is.
    """
    if is_pretty_folder(selected_folder):
        library_root = selected_folder.parent

        dbg_print(
            f"Selected .pretty folder; resolved library root: {library_root}",
            Severity.INFO,
            "libraries",
            stage="root",
            source="library_resolution",
        )

        return library_root

    dbg_print(
        f"Selected library root directly: {selected_folder}",
        Severity.INFO,
        "libraries",
        stage="root",
        source="library_resolution",
    )

    return selected_folder


def resolve_path(path_value: str) -> Path:
    """
    Expand Windows environment variables and user-home shortcuts.

    Examples:
    %USERPROFILE%/Downloads
    ~/Downloads
    """
    expanded = os.path.expandvars(path_value)
    expanded = os.path.expanduser(expanded)
    return Path(expanded)


def get_existing_initial_dir(path_value: str, fallback: Path) -> str:
    """
    Return a safe initial directory for a file/folder picker.

    Supports:
    - Windows environment variables like %USERPROFILE%
    - user-home shortcuts like ~
    """
    if path_value:
        candidate = resolve_path(path_value)
        if candidate.exists() and candidate.is_dir():
            return str(candidate)

    if fallback.exists() and fallback.is_dir():
        return str(fallback)

    return str(Path.home())


def select_import_source(config: dict) -> tuple[str, list[Path]]:
    """
    Open import source picker.

    Allows either:
      - one ZIP file
      - one loose KiCad import file set

    Invalid combinations show an error dialog and loop back to the picker.
    """
    last_config = config.get("last", {})

    initial_dir = get_existing_initial_dir(
        last_config.get("source_folder", ""),
        Path.home() / "Downloads",
    )

    current_initial_dir = Path(initial_dir)

    while True:
        selected_paths = filedialog.askopenfilenames(
            title="Select import source: one ZIP or one loose KiCad file set",
            initialdir=str(current_initial_dir),
            filetypes=[
                (
                    "KiCad import sources",
                    "*.zip *.kicad_mod *.kicad_sym *.step *.stp",
                ),
                ("Vendor ZIP", "*.zip"),
                ("KiCad footprint", "*.kicad_mod"),
                ("KiCad symbol", "*.kicad_sym"),
                ("STEP model", "*.step *.stp"),
                ("All files", "*.*"),
            ],
        )

        if not selected_paths:
            print("No import source selected. Exiting.")
            raise SystemExit

        paths = [Path(path) for path in selected_paths]

        if paths:
            current_initial_dir = paths[0].parent

        try:
            return classify_import_source_selection(paths)

        except ValueError as error:
            messagebox.showerror(
                title="Invalid import source selection",
                message=str(error),
            )


def select_library_folder(config: dict) -> Path:
    """
    Open folder picker using the last library root if possible.
    """
    initial_dir = get_existing_initial_dir(
        config.get("last", {}).get("library_root", ""),
        Path.home(),
    )

    selected_folder = filedialog.askdirectory(
        title="Select KiCad custom library root",
        initialdir = initial_dir,
    )

    if not selected_folder:
        print("No library root selected. Exiting.")
        raise SystemExit

    library_root = Path(selected_folder)
    
    dbg_blank(Severity.VERBOSE, "source", stage="dialogs", source="query")
    dbg_print(f"Selected: {library_root}", Severity.VERBOSE, "source", stage="dialogs", source="query")

    return library_root


def collect_and_validate_user_input(run_state: dict) -> dict:
    """
    Owns:
    - run_state["status"]
    - run_state["user_input"]
    - run_state["current"]
    """
    config = run_state["config"]["general_config"]

    try:
        source_mode, source_paths = select_import_source(config)
        library_folder = select_library_folder(config)

    except SystemExit as error:
        return mark_failure(
            run_state,
            script="kicad_import_assistant.py",
            step="collect_user_input",
            function_name="collect_and_validate_user_input",
            failure_reason=f"User input selection was canceled or failed.\n{error}",
            severity=Severity.ERROR,
        )

    if not source_paths:
        return mark_failure(
            run_state,
            script="kicad_import_assistant.py",
            step="collect_user_input",
            function_name="collect_and_validate_user_input",
            failure_reason="No import source paths were selected.",
            severity=Severity.ERROR,
        )

    invalid_paths = [
        path for path in source_paths
        if not path.exists() or not path.is_file()
    ]

    if invalid_paths:
        return mark_failure(
            run_state,
            script="kicad_import_assistant.py",
            step="collect_user_input",
            function_name="collect_and_validate_user_input",
            failure_reason=(
                "One or more selected import source files are invalid.\n"
                + "\n".join(f"- {path}" for path in invalid_paths)
            ),
            severity=Severity.ERROR,
        )

    run_state["current"]["source_mode"] = source_mode
    run_state["current"]["source_paths"] = source_paths
    run_state["current"]["source_folder"] = source_paths[0].parent
    run_state["current"]["library_folder"] = library_folder

    if source_mode == "zip":
        run_state["current"]["zip_path"] = source_paths[0]
    else:
        run_state["current"]["zip_path"] = None

    run_state["user_input"]["source_valid"] = True
    run_state["user_input"]["zip_file_valid"] = source_mode == "zip"
    run_state["user_input"]["library_folder_valid"] = True
    run_state["user_input"]["selections_valid"] = True

    return mark_success(
        run_state,
        script="kicad_import_assistant.py",
        step="collect_user_input",
        function_name="collect_and_validate_user_input",
        message="User input selections are valid.",
    )


def resolve_target_library(run_state: dict) -> dict:
    """
    Owns:
    - run_state["status"]
    - run_state["profile"]
    - run_state["current"]
    """
    config = run_state["config"]["general_config"]
    library_folder = run_state["current"]["library_folder"]

    library_root = resolve_library_root_from_selection(library_folder)

    if not library_root.exists() or not library_root.is_dir():
        return mark_failure(
            run_state,
            script="kicad_import_assistant.py",
            step="resolve_target_library",
            function_name="resolve_target_library",
            failure_reason=f"Resolved library root is not valid:\n{library_root}",
            severity=Severity.ERROR,
        )

    suggested_profile = infer_profile_from_selected_folder(
        selected_folder=library_folder,
        config=config,
    )

    target_library = select_target_library_profile(
        config=config,
        suggested_profile=suggested_profile,
    )

    library_settings = config.get("libraries", {}).get(target_library)

    if not library_settings:
        return mark_failure(
            run_state,
            script="kicad_import_assistant.py",
            step="resolve_target_library",
            function_name="resolve_target_library",
            failure_reason=f"Target library profile was not found:\n{target_library}",
            severity=Severity.ERROR,
        )

    target_footprint_dir = library_root / library_settings["footprint_dir"]

    if not target_footprint_dir.exists() or not target_footprint_dir.is_dir():
        return mark_failure(
            run_state,
            script="kicad_import_assistant.py",
            step="resolve_target_library",
            function_name="resolve_target_library",
            failure_reason=f"Target footprint/model folder is not valid:\n{target_footprint_dir}",
            severity=Severity.ERROR,
        )

    target_symbol_file, symbol_resolution_status = resolve_target_symbol_file(
        target_footprint_dir=target_footprint_dir,
        library_settings=library_settings,
    )

    run_state["current"]["library_root"] = library_root
    run_state["current"]["target_library"] = target_library
    run_state["current"]["target_footprint_dir"] = target_footprint_dir
    run_state["current"]["target_symbol_file"] = target_symbol_file

    run_state["profile"]["suggested_profile"] = suggested_profile
    run_state["profile"]["autosuggested"] = suggested_profile is not None
    run_state["profile"]["selected_profile"] = target_library
    run_state["profile"]["settings"] = library_settings
    run_state["profile"]["user_confirmed"] = True

    return mark_success(
        run_state,
        script="kicad_import_assistant.py",
        step="resolve_target_library",
        function_name="resolve_target_library",
        message="Target library resolved.",
    )

