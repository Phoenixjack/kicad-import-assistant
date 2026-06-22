"""
KiCad Import Assistant

Main entry point for the standalone KiCad import workflow.

This script coordinates:
- config loading
- ZIP selection/extraction
- file discovery
- naming prompts
- preview manifest generation
- footprint/model import
- symbol preview and merge workflow
- final status reporting
  
Detailed behavior, safety notes, compatibility notes, and version history are
documented in README.md, FEATURES.md, and VERSION_HISTORY.md.

"""

APP_VERSION = "0.10.0"

import tkinter as tk
from pathlib import Path
from kia.debug import (
    dbg_blank,
    dbg_print, 
    Severity, 
)
from kia.config import (
    CONFIG_PATH, 
    load_config, 
    save_config,
)
from kia.run_state import initialize_run_state
from kia.workflow_status import (
    mark_success, 
    mark_failure, 
    stop_if_failed,
    critical_error,
)
from kia.schema import load_naming_schema
from kia.dialogs import (
    select_import_source,
    select_library_folder,
)
from kia.library_resolution import (
    select_target_library_profile, 
    resolve_library_root_from_selection,
    infer_profile_from_selected_folder,
)

from kia.symbol_resolver import resolve_target_symbol_file
from kia.source_scan import (
    extract_zip_to_temp,
    find_import_files,
    cleanup_temp_folder,
    print_import_file_summary,
)
from kia.naming import (
    build_basename_from_prompts, 
    suggest_defaults_from_files, 
    prompt_with_default,
)
from kia.import_plan import (
    create_preview_manifest, 
    select_import_files,
)
from kia.symbol_editor import (
    create_symbol_preview_file,
    check_symbol_merge_preconditions,
    create_symbol_library_backup,
    merge_symbol_preview_into_target,
)
from kia.footprint_importer import (
    confirm_import,
    copy_selected_import_files,
    find_existing_files_by_mpn,
    warn_about_existing_mpn_matches,
    confirm_continue_after_duplicate_warning,
)



def main() -> None:
    """
    Main script entry point.

    Main should orchestrate the workflow only.
    Each stage updates run_state and reports success/failure through
    run_state["status"].
    """
    initialize_tkinter_dialogs()

    run_state = initialize_run_state()

    run_state = load_runtime_config(run_state)
    stop_if_failed(run_state)

    run_state = collect_and_validate_user_input(run_state)
    stop_if_failed(run_state)

    run_state = resolve_target_library(run_state)
    stop_if_failed(run_state)

    print()
    print("Early staged workflow complete.")
    print("Next step: source extraction / file discovery.")
    # END MAIN()


def initialize_tkinter_dialogs() -> tk.Tk:
    root = tk.Tk()
    root.withdraw()
    return root


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


def load_runtime_config(run_state: dict) -> dict:
    """
    Owns:
    - run_state["status"]
    - run_state["config"]
    """
    try:
        general_config = load_config()
        naming_schema = load_naming_schema()

    except Exception as error:
        return mark_failure(
            run_state,
            script="kicad_import_assistant.py",
            step="load_runtime_config",
            function_name="load_runtime_config",
            failure_reason=f"Failed to load required runtime config.\n{error}",
            severity=Severity.ERROR,
        )

    run_state["config"]["general_config"] = general_config
    run_state["config"]["naming_schema"] = naming_schema
    run_state["config"]["general_config_loaded"] = True
    run_state["config"]["naming_schema_loaded"] = True
    run_state["config"]["loaded"] = True

    return mark_success(
        run_state,
        script="kicad_import_assistant.py",
        step="load_runtime_config",
        function_name="load_runtime_config",
        message="Runtime config loaded.",
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


if __name__ == "__main__":
    main()


