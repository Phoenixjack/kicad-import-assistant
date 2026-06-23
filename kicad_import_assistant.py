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

from datetime import datetime
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

    run_state = prepare_import_source(run_state)
    stop_if_failed(run_state)

    run_state = discover_source_files(run_state)
    stop_if_failed(run_state)

    run_state = build_import_basename(run_state)
    stop_if_failed(run_state)

    print()
    print("Naming complete.")
    print(f"Basename: {run_state['import_plan']['basename']}")
    print("Next step: import plan creation.")
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


def prepare_import_source(run_state: dict) -> dict:
    """
    Owns:
    - run_state["status"]
    - run_state["import_plan"]["temp_folder_path"]

    Extracts the selected ZIP file to a temporary source folder.
    """
    zip_path = run_state["current"]["zip_path"]

    try:
        extract_root = extract_zip_to_temp(zip_path)

    except SystemExit as error:
        return mark_failure(
            run_state,
            script="kicad_import_assistant.py",
            step="prepare_import_source",
            function_name="prepare_import_source",
            failure_reason=f"ZIP extraction failed.\n{error}",
            severity=Severity.ERROR,
        )

    except Exception as error:
        return mark_failure(
            run_state,
            script="kicad_import_assistant.py",
            step="prepare_import_source",
            function_name="prepare_import_source",
            failure_reason=f"Unexpected error while extracting ZIP.\n{error}",
            severity=Severity.ERROR,
        )

    if not extract_root.exists() or not extract_root.is_dir():
        return mark_failure(
            run_state,
            script="kicad_import_assistant.py",
            step="prepare_import_source",
            function_name="prepare_import_source",
            failure_reason=f"Extracted source folder is not valid:\n{extract_root}",
            severity=Severity.ERROR,
        )

    run_state["import_plan"]["temp_folder_path"] = extract_root

    return mark_success(
        run_state,
        script="kicad_import_assistant.py",
        step="prepare_import_source",
        function_name="prepare_import_source",
        message="Import source extracted.",
    )


def discover_source_files(run_state: dict) -> dict:
    """
    Owns:
    - run_state["status"]
    - run_state["source_files"]
    - run_state["symbol"]["exists_in_source"]
    - run_state["footprint"]["exists_in_source"]
    - run_state["model"]["exists_in_source"]

    Scans the extracted source folder for KiCad-relevant files.
    """
    extract_root = run_state["import_plan"]["temp_folder_path"]

    if extract_root is None:
        return mark_failure(
            run_state,
            script="kicad_import_assistant.py",
            step="discover_source_files",
            function_name="discover_source_files",
            failure_reason="Cannot scan source files because temp_folder_path is None.",
            severity=Severity.ERROR,
        )

    if not extract_root.exists() or not extract_root.is_dir():
        return mark_failure(
            run_state,
            script="kicad_import_assistant.py",
            step="discover_source_files",
            function_name="discover_source_files",
            failure_reason=f"Cannot scan invalid source folder:\n{extract_root}",
            severity=Severity.ERROR,
        )

    found_files = find_import_files(extract_root)

    footprints = found_files.get("footprints", [])
    symbols = found_files.get("symbols", [])
    models = found_files.get("models", [])
    other = found_files.get("other", [])

    if not footprints and not symbols and not models:
        return mark_failure(
            run_state,
            script="kicad_import_assistant.py",
            step="discover_source_files",
            function_name="discover_source_files",
            failure_reason=(
                "No KiCad import files were found in the selected source.\n"
                f"Source folder: {extract_root}"
            ),
            severity=Severity.ERROR,
        )

    run_state["source_files"]["found_files"] = found_files
    run_state["source_files"]["footprints"] = footprints
    run_state["source_files"]["symbols"] = symbols
    run_state["source_files"]["models"] = models
    run_state["source_files"]["other"] = other
    run_state["source_files"]["scan_complete"] = True

    run_state["footprint"]["exists_in_source"] = bool(footprints)
    run_state["symbol"]["exists_in_source"] = bool(symbols)
    run_state["model"]["exists_in_source"] = bool(models)

    print()
    print("Source discovery summary:")
    print(f"  Footprints: {len(footprints)}")
    print(f"  Symbols: {len(symbols)}")
    print(f"  Models: {len(models)}")
    print(f"  Other files: {len(other)}")

    return mark_success(
        run_state,
        script="kicad_import_assistant.py",
        step="discover_source_files",
        function_name="discover_source_files",
        message="Source files discovered.",
    )


def build_import_basename(run_state: dict) -> dict:
    """
    Owns:
    - run_state["status"]
    - run_state["import_plan"]["basename"]
    - run_state["recent_values"]

    Builds the target basename using the existing naming prompt workflow.
    """
    config = run_state["config"]["general_config"]
    naming_schema = run_state["config"]["naming_schema"]
    library_settings = run_state["profile"]["settings"]
    found_files = run_state["source_files"]["found_files"]

    if not found_files:
        return mark_failure(
            run_state,
            script="kicad_import_assistant.py",
            step="build_import_basename",
            function_name="build_import_basename",
            failure_reason="Cannot build basename because no source files were discovered.",
            severity=Severity.ERROR,
        )

    if not library_settings:
        return mark_failure(
            run_state,
            script="kicad_import_assistant.py",
            step="build_import_basename",
            function_name="build_import_basename",
            failure_reason="Cannot build basename because no library profile settings are available.",
            severity=Severity.ERROR,
        )

    try:
        suggested_defaults = suggest_defaults_from_files(found_files)

        basename = build_basename_from_prompts(
            config=config,
            library_settings=library_settings,
            found_files=found_files,
            suggested_defaults=suggested_defaults,
            naming_schema=naming_schema,
        )

    except SystemExit as error:
        return mark_failure(
            run_state,
            script="kicad_import_assistant.py",
            step="build_import_basename",
            function_name="build_import_basename",
            failure_reason=f"Basename creation was canceled or failed validation.\n{error}",
            severity=Severity.ERROR,
        )

    except Exception as error:
        return mark_failure(
            run_state,
            script="kicad_import_assistant.py",
            step="build_import_basename",
            function_name="build_import_basename",
            failure_reason=f"Unexpected error while building basename.\n{error}",
            severity=Severity.ERROR,
        )

    if not basename:
        return mark_failure(
            run_state,
            script="kicad_import_assistant.py",
            step="build_import_basename",
            function_name="build_import_basename",
            failure_reason="Basename creation returned an empty value.",
            severity=Severity.ERROR,
        )

    run_state["import_plan"]["basename"] = basename

    # Current naming.py still writes recent values into config.
    # Capture them into run_state so final config save can later use run_state.
    run_state["recent_values"] = dict(config.get("recent_values", {}))

    dbg_blank(Severity.VERBOSE, "basename", stage="build", source="main")
    dbg_print(
        f"Generated target basename: {basename}",
        Severity.VERBOSE,
        "basename",
        stage="build",
        source="main",
    )

    return mark_success(
        run_state,
        script="kicad_import_assistant.py",
        step="build_import_basename",
        function_name="build_import_basename",
        message="Import basename built.",
    )


if __name__ == "__main__":
    main()


