"""
kia/workflow_input.py
  collect_and_validate_user_input()
  resolve_target_library()
"""

import os
from pathlib import Path
from tkinter import filedialog
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


def is_pretty_folder(path: Path) -> bool:
    """
    Return True if the selected path appears to be a KiCad .pretty folder.
    """
    return path.suffix.lower() == ".pretty"


def select_target_library_profile(config: dict, suggested_profile: str | None = None) -> str:
    """
    Ask the user which configured library profile to use.
    """
    libraries = config.get("libraries", {})

    if not libraries:
        print()
        print("ERROR: No library profiles are configured.")
        print("Check kicad_import_assistant_config.json.")
        raise SystemExit

    library_names = list(libraries.keys())
    default_library = suggested_profile or config.get("last_target_library", library_names[0])

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

    config["last_target_library"] = selected_library
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


def select_import_source(config: dict) -> Path:
    """
    Open ZIP file picker using the last ZIP folder if possible.
    """
    initial_dir = get_existing_initial_dir(
        config.get("last", {}).get("zip_folder", ""),
        Path.home() / "Downloads",
    )

    zip_path = filedialog.askopenfilename(
        title="Select vendor ZIP file",
        initialdir = initial_dir,
        filetypes = [("ZIP files", "*.zip"), ("All files", "*.*")],
    )

    if not zip_path:
        print("No ZIP selected. Exiting.")
        raise SystemExit

    zip_path = Path(zip_path)
    config["last_zip_folder"] = str(zip_path.parent)

    return zip_path


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
        zip_path = select_import_source(config)
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

    if not zip_path.exists() or not zip_path.is_file():
        return mark_failure(
            run_state,
            script="kicad_import_assistant.py",
            step="collect_user_input",
            function_name="collect_and_validate_user_input",
            failure_reason=f"Selected import source is not a valid file:\n{zip_path}",
            severity=Severity.ERROR,
        )

    if zip_path.suffix.lower() != ".zip":
        return mark_failure(
            run_state,
            script="kicad_import_assistant.py",
            step="collect_user_input",
            function_name="collect_and_validate_user_input",
            failure_reason=(
                "Selected import source is not a ZIP file.\n"
                f"Source: {zip_path}\n"
                "Loose-file/folder imports are planned but not active yet."
            ),
            severity=Severity.ERROR,
        )

    if not library_folder.exists() or not library_folder.is_dir():
        return mark_failure(
            run_state,
            script="kicad_import_assistant.py",
            step="collect_user_input",
            function_name="collect_and_validate_user_input",
            failure_reason=f"Selected library folder is not valid:\n{library_folder}",
            severity=Severity.ERROR,
        )

    run_state["current"]["zip_path"] = zip_path
    run_state["current"]["zip_folder"] = zip_path.parent
    run_state["current"]["library_folder"] = library_folder

    run_state["user_input"]["zip_file_valid"] = True
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

