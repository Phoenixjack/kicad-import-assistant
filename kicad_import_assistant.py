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
import shutil
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
    build_kicad_model_path,
    update_footprint_internal_name,
    update_footprint_value_property,
    update_footprint_model_path,
    add_import_metadata_properties,
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

    run_state = collect_part_identity(run_state)
    stop_if_failed(run_state)

    run_state = check_for_existing_part(run_state)
    stop_if_failed(run_state)

    run_state = build_import_basename(run_state)
    stop_if_failed(run_state)

    run_state = select_files_for_import(run_state)
    stop_if_failed(run_state)

    run_state = create_import_plan(run_state)
    stop_if_failed(run_state)

    run_state = review_import_plan(run_state)
    stop_if_failed(run_state)

    run_state = confirm_file_copy_execution(run_state)
    stop_if_failed(run_state)

    run_state = copy_planned_footprint_and_model_files(run_state)
    stop_if_failed(run_state)

    run_state = update_copied_footprint_contents(run_state)
    stop_if_failed(run_state)

    print()
    print("Footprint content update complete.")
    print("Next step: symbol preview / merge.")
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


def collect_part_identity(run_state: dict) -> dict:
    """
    Owns:
    - run_state["status"]
    - run_state["naming"]["suggested_defaults"]
    - run_state["naming"]["mpn"]
    - run_state["naming"]["mpn_collected"]

    Collects the part identity early so duplicate checking can later happen
    before the full naming workflow.
    """
    found_files = run_state["source_files"]["found_files"]

    if not found_files:
        return mark_failure(
            run_state,
            script="kicad_import_assistant.py",
            step="collect_part_identity",
            function_name="collect_part_identity",
            failure_reason="Cannot collect part identity because no source files were discovered.",
            severity=Severity.ERROR,
        )

    try:
        suggested_defaults = suggest_defaults_from_files(found_files)

        mpn = prompt_with_default(
            "MPN for duplicate search",
            suggested_defaults.get("mpn", ""),
        )

    except SystemExit as error:
        return mark_failure(
            run_state,
            script="kicad_import_assistant.py",
            step="collect_part_identity",
            function_name="collect_part_identity",
            failure_reason=f"MPN collection was canceled or failed.\n{error}",
            severity=Severity.ERROR,
        )

    except Exception as error:
        return mark_failure(
            run_state,
            script="kicad_import_assistant.py",
            step="collect_part_identity",
            function_name="collect_part_identity",
            failure_reason=f"Unexpected error while collecting MPN.\n{error}",
            severity=Severity.ERROR,
        )

    mpn = mpn.strip()

    if not mpn:
        return mark_failure(
            run_state,
            script="kicad_import_assistant.py",
            step="collect_part_identity",
            function_name="collect_part_identity",
            failure_reason="MPN is required for naming and future duplicate checks.",
            severity=Severity.ERROR,
        )

    suggested_defaults["mpn"] = mpn

    run_state["naming"]["suggested_defaults"] = suggested_defaults
    run_state["naming"]["mpn"] = mpn
    run_state["naming"]["mpn_collected"] = True

    return mark_success(
        run_state,
        script="kicad_import_assistant.py",
        step="collect_part_identity",
        function_name="collect_part_identity",
        message="Part identity collected.",
    )


def check_for_existing_part(run_state: dict) -> dict:
    """
    Owns:
    - run_state["status"]
    - run_state["duplicate_check"]

    Checks the selected target library for files matching the early MPN.
    If possible duplicates are found, the user may stop before full naming.
    """
    library_root = run_state["current"]["library_root"]
    library_settings = run_state["profile"]["settings"]
    mpn = run_state["naming"].get("mpn", "")

    if not mpn:
        return mark_failure(
            run_state,
            script="kicad_import_assistant.py",
            step="check_for_existing_part",
            function_name="check_for_existing_part",
            failure_reason="Cannot perform duplicate check because MPN is missing.",
            severity=Severity.ERROR,
        )

    if library_root is None:
        return mark_failure(
            run_state,
            script="kicad_import_assistant.py",
            step="check_for_existing_part",
            function_name="check_for_existing_part",
            failure_reason="Cannot perform duplicate check because library_root is missing.",
            severity=Severity.ERROR,
        )

    if not library_settings:
        return mark_failure(
            run_state,
            script="kicad_import_assistant.py",
            step="check_for_existing_part",
            function_name="check_for_existing_part",
            failure_reason="Cannot perform duplicate check because library profile settings are missing.",
            severity=Severity.ERROR,
        )

    try:
        existing_matches = find_existing_files_by_mpn(
            library_root=library_root,
            library_settings=library_settings,
            mpn=mpn,
        )

        warn_about_existing_mpn_matches(existing_matches, mpn)

        user_continued = confirm_continue_after_duplicate_warning(existing_matches)

    except Exception as error:
        return mark_failure(
            run_state,
            script="kicad_import_assistant.py",
            step="check_for_existing_part",
            function_name="check_for_existing_part",
            failure_reason=f"Unexpected error while checking for existing MPN matches.\n{error}",
            severity=Severity.ERROR,
        )

    run_state["duplicate_check"]["checked"] = True
    run_state["duplicate_check"]["mpn"] = mpn
    run_state["duplicate_check"]["possible_duplicate"] = bool(existing_matches)
    run_state["duplicate_check"]["matches"] = [str(match) for match in existing_matches]
    run_state["duplicate_check"]["match_count"] = len(existing_matches)
    run_state["duplicate_check"]["user_continued"] = user_continued

    if existing_matches and not user_continued:
        return mark_failure(
            run_state,
            script="kicad_import_assistant.py",
            step="check_for_existing_part",
            function_name="check_for_existing_part",
            failure_reason=(
                "Import canceled after possible duplicate MPN match.\n"
                f"MPN: {mpn}\n"
                f"Matches found: {len(existing_matches)}"
            ),
            severity=Severity.INFO,
        )

    if not existing_matches:
        print()
        print("Duplicate check:")
        print(f"  MPN: {mpn}")
        print("  Existing matches: none")

    return mark_success(
        run_state,
        script="kicad_import_assistant.py",
        step="check_for_existing_part",
        function_name="check_for_existing_part",
        message="Duplicate check complete.",
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

    suggested_defaults = run_state["naming"].get("suggested_defaults", {})
    mpn = run_state["naming"].get("mpn", "")

    if not suggested_defaults:
        suggested_defaults = suggest_defaults_from_files(found_files)

    if mpn:
        suggested_defaults["mpn"] = mpn

    try:
        basename = build_basename_from_prompts(
            config=config,
            library_settings=library_settings,
            found_files=found_files,
            suggested_defaults=suggested_defaults,
            override_defaults={"mpn": mpn},
            naming_schema=naming_schema,
            prompt_mpn=False,
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


def select_files_for_import(run_state: dict) -> dict:
    """
    Owns:
    - run_state["status"]
    - run_state["import_plan"]["selected_files"]
    - run_state["symbol"]["user_chose_import"]
    - run_state["footprint"]["user_chose_import"]
    - run_state["model"]["user_chose_import"]

    Lets the user select which discovered source files should be included
    in the import plan.
    """
    found_files = run_state["source_files"]["found_files"]

    if not found_files:
        return mark_failure(
            run_state,
            script="kicad_import_assistant.py",
            step="select_files_for_import",
            function_name="select_files_for_import",
            failure_reason="Cannot select import files because no source files were discovered.",
            severity=Severity.ERROR,
        )

    try:
        selected_files = select_import_files(found_files)

    except SystemExit as error:
        return mark_failure(
            run_state,
            script="kicad_import_assistant.py",
            step="select_files_for_import",
            function_name="select_files_for_import",
            failure_reason=f"File selection was canceled or failed.\n{error}",
            severity=Severity.INFO,
        )

    except Exception as error:
        return mark_failure(
            run_state,
            script="kicad_import_assistant.py",
            step="select_files_for_import",
            function_name="select_files_for_import",
            failure_reason=f"Unexpected error while selecting import files.\n{error}",
            severity=Severity.ERROR,
        )

    run_state["import_plan"]["selected_files"] = selected_files

    run_state["footprint"]["user_chose_import"] = selected_files.get("footprint") is not None
    run_state["symbol"]["user_chose_import"] = selected_files.get("symbol") is not None
    run_state["model"]["user_chose_import"] = selected_files.get("model") is not None

    return mark_success(
        run_state,
        script="kicad_import_assistant.py",
        step="select_files_for_import",
        function_name="select_files_for_import",
        message="Import files selected.",
    )


def create_import_plan(run_state: dict) -> dict:
    """
    Owns:
    - run_state["status"]
    - run_state["import_plan"]

    Builds planned source/target file actions without writing to the target
    KiCad library.
    """
    selected_files = run_state["import_plan"]["selected_files"]
    basename = run_state["import_plan"]["basename"]
    target_footprint_dir = run_state["current"]["target_footprint_dir"]
    target_symbol_file = run_state["current"]["target_symbol_file"]

    if not basename:
        return mark_failure(
            run_state,
            script="kicad_import_assistant.py",
            step="create_import_plan",
            function_name="create_import_plan",
            failure_reason="Cannot create import plan because basename is missing.",
            severity=Severity.ERROR,
        )

    if not selected_files or not any(selected_files.values()):
        return mark_failure(
            run_state,
            script="kicad_import_assistant.py",
            step="create_import_plan",
            function_name="create_import_plan",
            failure_reason="Cannot create import plan because no files were selected.",
            severity=Severity.ERROR,
        )

    if target_footprint_dir is None:
        return mark_failure(
            run_state,
            script="kicad_import_assistant.py",
            step="create_import_plan",
            function_name="create_import_plan",
            failure_reason="Cannot create import plan because target footprint folder is missing.",
            severity=Severity.ERROR,
        )

    selected_footprint = selected_files.get("footprint")
    selected_symbol = selected_files.get("symbol")
    selected_model = selected_files.get("model")

    if selected_footprint:
        run_state["import_plan"]["footprint"]["source_path"] = selected_footprint
        run_state["import_plan"]["footprint"]["target_path"] = (
            target_footprint_dir / f"{basename}.kicad_mod"
        )
        run_state["import_plan"]["footprint"]["raw_filename"] = selected_footprint.name
        run_state["import_plan"]["footprint"]["new_filename"] = f"{basename}.kicad_mod"
        run_state["import_plan"]["footprint"]["action"] = "COPY_RENAME_PENDING"

    if selected_model:
        model_suffix = selected_model.suffix
        run_state["import_plan"]["model"]["source_path"] = selected_model
        run_state["import_plan"]["model"]["target_path"] = (
            target_footprint_dir / f"{basename}{model_suffix}"
        )
        run_state["import_plan"]["model"]["raw_filename"] = selected_model.name
        run_state["import_plan"]["model"]["new_filename"] = f"{basename}{model_suffix}"
        run_state["import_plan"]["model"]["action"] = "COPY_RENAME_PENDING"

    if selected_symbol:
        run_state["import_plan"]["symbol"]["source_path"] = selected_symbol
        run_state["import_plan"]["symbol"]["target_path"] = target_symbol_file
        run_state["import_plan"]["symbol"]["raw_filename"] = selected_symbol.name
        run_state["import_plan"]["symbol"]["new_filename"] = basename
        run_state["import_plan"]["symbol"]["action"] = "MERGE_PENDING"

    run_state["import_plan"]["is_complete"] = True

    return mark_success(
        run_state,
        script="kicad_import_assistant.py",
        step="create_import_plan",
        function_name="create_import_plan",
        message="Import plan created.",
    )


def review_import_plan(run_state: dict) -> dict:
    """
    Owns:
    - run_state["status"]
    - run_state["import_plan"]["manifest_path"]
    - run_state["import_plan"]["user_wants_to_review"]

    Prints the planned import actions and optionally writes a preview CSV.
    This does not modify the target KiCad library.
    """
    selected_files = run_state["import_plan"]["selected_files"]
    extract_root = run_state["import_plan"]["temp_folder_path"]
    library_root = run_state["current"]["library_root"]
    library_settings = run_state["profile"]["settings"]
    basename = run_state["import_plan"]["basename"]
    target_symbol_file = run_state["current"]["target_symbol_file"]

    if not run_state["import_plan"]["is_complete"]:
        return mark_failure(
            run_state,
            script="kicad_import_assistant.py",
            step="review_import_plan",
            function_name="review_import_plan",
            failure_reason="Cannot review import plan because the plan is not complete.",
            severity=Severity.ERROR,
        )

    print()
    print("Import plan:")
    print(f"  Basename: {basename}")

    for file_type in ["footprint", "model", "symbol"]:
        plan_item = run_state["import_plan"][file_type]

        if plan_item["source_path"] is None:
            print(f"  {file_type}: SKIPPED")
            continue

        print(f"  {file_type}:")
        print(f"    Source: {plan_item['source_path']}")
        print(f"    Target: {plan_item['target_path']}")
        print(f"    Action: {plan_item['action']}")

    print()
    create_csv = input("Write preview import-plan CSV? [Y/n]: ").strip().lower()

    if create_csv in ["", "y", "yes"]:
        try:
            manifest_path = create_preview_manifest(
                selected_files=selected_files,
                extract_root=extract_root,
                library_root=library_root,
                library_settings=library_settings,
                basename=basename,
                target_symbol_file=target_symbol_file,
            )

        except Exception as error:
            return mark_failure(
                run_state,
                script="kicad_import_assistant.py",
                step="review_import_plan",
                function_name="review_import_plan",
                failure_reason=f"Failed to write preview import-plan CSV.\n{error}",
                severity=Severity.ERROR,
            )

        run_state["import_plan"]["manifest_path"] = manifest_path
        run_state["import_plan"]["user_wants_to_review"] = True

    else:
        print("Preview import-plan CSV skipped.")
        run_state["import_plan"]["user_wants_to_review"] = False

    return mark_success(
        run_state,
        script="kicad_import_assistant.py",
        step="review_import_plan",
        function_name="review_import_plan",
        message="Import plan reviewed.",
    )


def confirm_file_copy_execution(run_state: dict) -> dict:
    """
    Owns:
    - run_state["status"]
    - run_state["file_copy"]["user_confirmed"]
    - run_state["user_confirmed_import"]

    Requires a hard confirmation before copying files into the target library.
    This checkpoint only copies/renames footprint and model files.
    It does not edit footprint contents and does not merge symbols.
    """
    if not run_state["import_plan"]["is_complete"]:
        return mark_failure(
            run_state,
            script="kicad_import_assistant.py",
            step="confirm_file_copy_execution",
            function_name="confirm_file_copy_execution",
            failure_reason="Cannot confirm file copy because the import plan is not complete.",
            severity=Severity.ERROR,
        )

    print()
    print("FILE COPY CONFIRMATION REQUIRED")
    print("This will copy/rename selected footprint and model files into the target library folder.")
    print("It will NOT edit the copied footprint contents yet.")
    print("It will NOT merge symbols yet.")
    print()

    confirmation = input("Type COPY to continue, or anything else to stop: ").strip()

    if confirmation != "COPY":
        return mark_failure(
            run_state,
            script="kicad_import_assistant.py",
            step="confirm_file_copy_execution",
            function_name="confirm_file_copy_execution",
            failure_reason="File copy canceled by user before target-library writes.",
            severity=Severity.INFO,
        )

    run_state["file_copy"]["user_confirmed"] = True
    run_state["user_confirmed_import"] = True

    return mark_success(
        run_state,
        script="kicad_import_assistant.py",
        step="confirm_file_copy_execution",
        function_name="confirm_file_copy_execution",
        message="File copy confirmed.",
    )


def copy_planned_footprint_and_model_files(run_state: dict) -> dict:
    """
    Owns:
    - run_state["status"]
    - run_state["file_copy"]
    - run_state["copied_files"]
    - run_state["files_copied"]
    - run_state["footprint"]["copied"]
    - run_state["model"]["copied"]

    Copies selected footprint and model files to their planned target paths.
    This does not edit footprint contents and does not merge symbols.
    """
    if not run_state["file_copy"]["user_confirmed"]:
        return mark_failure(
            run_state,
            script="kicad_import_assistant.py",
            step="copy_planned_files",
            function_name="copy_planned_footprint_and_model_files",
            failure_reason="Cannot copy files because file copy was not confirmed.",
            severity=Severity.ERROR,
        )

    if not run_state["import_plan"]["is_complete"]:
        return mark_failure(
            run_state,
            script="kicad_import_assistant.py",
            step="copy_planned_files",
            function_name="copy_planned_footprint_and_model_files",
            failure_reason="Cannot copy files because the import plan is not complete.",
            severity=Severity.ERROR,
        )

    copied_files = []
    run_state["file_copy"]["attempted"] = True

    for file_type in ["footprint", "model"]:
        plan_item = run_state["import_plan"][file_type]

        source_path = plan_item.get("source_path")
        target_path = plan_item.get("target_path")

        if source_path is None:
            continue

        if target_path is None:
            return mark_failure(
                run_state,
                script="kicad_import_assistant.py",
                step="copy_planned_files",
                function_name="copy_planned_footprint_and_model_files",
                failure_reason=f"Cannot copy {file_type}; target path is missing.",
                severity=Severity.ERROR,
            )

        source_path = Path(source_path)
        target_path = Path(target_path)

        if not source_path.exists() or not source_path.is_file():
            return mark_failure(
                run_state,
                script="kicad_import_assistant.py",
                step="copy_planned_files",
                function_name="copy_planned_footprint_and_model_files",
                failure_reason=f"Cannot copy {file_type}; source file is invalid:\n{source_path}",
                severity=Severity.ERROR,
            )

        if not target_path.parent.exists() or not target_path.parent.is_dir():
            return mark_failure(
                run_state,
                script="kicad_import_assistant.py",
                step="copy_planned_files",
                function_name="copy_planned_footprint_and_model_files",
                failure_reason=f"Cannot copy {file_type}; target folder is invalid:\n{target_path.parent}",
                severity=Severity.ERROR,
            )

        if target_path.exists():
            return mark_failure(
                run_state,
                script="kicad_import_assistant.py",
                step="copy_planned_files",
                function_name="copy_planned_footprint_and_model_files",
                failure_reason=(
                    f"Cannot copy {file_type}; target file already exists.\n"
                    f"Overwrite protection is enabled:\n{target_path}"
                ),
                severity=Severity.ERROR,
            )

        try:
            shutil.copy2(source_path, target_path)

        except Exception as error:
            return mark_failure(
                run_state,
                script="kicad_import_assistant.py",
                step="copy_planned_files",
                function_name="copy_planned_footprint_and_model_files",
                failure_reason=f"Failed to copy {file_type}.\n{error}",
                severity=Severity.ERROR,
            )

        copied_row = {
            "type": file_type,
            "source": source_path,
            "target": target_path,
        }

        copied_files.append(copied_row)

        run_state[file_type]["copied"] = True
        run_state["import_plan"][file_type]["action"] = "COPIED_UNEDITED"

    run_state["file_copy"]["copied_files"] = copied_files
    run_state["file_copy"]["complete"] = True

    run_state["copied_files"] = copied_files
    run_state["files_copied"] = len(copied_files) > 0

    print()
    print("Copied files:")

    if not copied_files:
        print("  No footprint/model files were selected for copy.")
    else:
        for copied_file in copied_files:
            print(f"  {copied_file['type']}:")
            print(f"    Source: {copied_file['source']}")
            print(f"    Target: {copied_file['target']}")

    if run_state["import_plan"]["symbol"]["source_path"] is not None:
        print()
        print("Symbol merge skipped for this checkpoint.")
        print(f"  Pending target: {run_state['import_plan']['symbol']['target_path']}")

    return mark_success(
        run_state,
        script="kicad_import_assistant.py",
        step="copy_planned_files",
        function_name="copy_planned_footprint_and_model_files",
        message="Planned footprint/model files copied.",
    )


def update_copied_footprint_contents(run_state: dict) -> dict:
    """
    Owns:
    - run_state["status"]
    - run_state["footprint_update"]
    - run_state["footprint"]["name_updated"]
    - run_state["footprint"]["model_property_updated"]
    - run_state["footprint"]["metadata_added"]

    Updates the copied footprint file only.

    This stage:
    - updates the footprint internal name
    - updates the Value property
    - updates/adds the 3D model reference when a model was copied
    - adds import metadata properties

    This stage does not merge symbols and does not save config.
    """
    if not run_state["file_copy"]["complete"]:
        return mark_failure(
            run_state,
            script="kicad_import_assistant.py",
            step="update_copied_footprint_contents",
            function_name="update_copied_footprint_contents",
            failure_reason="Cannot update footprint contents because file copy is not complete.",
            severity=Severity.ERROR,
        )

    footprint_plan = run_state["import_plan"]["footprint"]
    model_plan = run_state["import_plan"]["model"]

    target_footprint = footprint_plan.get("target_path")
    basename = run_state["import_plan"]["basename"]

    config = run_state["config"]["general_config"]
    library_settings = run_state["profile"]["settings"]

    if target_footprint is None:
        print()
        print("Footprint content update skipped.")
        print("  No footprint was selected for import.")

        run_state["footprint_update"]["complete"] = True

        return mark_success(
            run_state,
            script="kicad_import_assistant.py",
            step="update_copied_footprint_contents",
            function_name="update_copied_footprint_contents",
            message="No copied footprint required updates.",
        )

    target_footprint = Path(target_footprint)

    if not target_footprint.exists() or not target_footprint.is_file():
        return mark_failure(
            run_state,
            script="kicad_import_assistant.py",
            step="update_copied_footprint_contents",
            function_name="update_copied_footprint_contents",
            failure_reason=f"Cannot update copied footprint because target file is invalid:\n{target_footprint}",
            severity=Severity.ERROR,
        )

    if not basename:
        return mark_failure(
            run_state,
            script="kicad_import_assistant.py",
            step="update_copied_footprint_contents",
            function_name="update_copied_footprint_contents",
            failure_reason="Cannot update copied footprint because basename is missing.",
            severity=Severity.ERROR,
        )

    run_state["footprint_update"]["attempted"] = True
    run_state["footprint_update"]["target_footprint"] = target_footprint

    update_errors = []

    internal_name_updated = update_footprint_internal_name(
        footprint_path=target_footprint,
        basename=basename,
    )

    run_state["footprint_update"]["internal_name_updated"] = internal_name_updated
    run_state["footprint"]["name_updated"] = internal_name_updated

    if not internal_name_updated:
        update_errors.append("Footprint internal name was not updated.")

    value_updated = update_footprint_value_property(
        footprint_path=target_footprint,
        basename=basename,
    )

    run_state["footprint_update"]["value_updated"] = value_updated

    if not value_updated:
        update_errors.append("Footprint Value property was not updated.")

    target_model = model_plan.get("target_path")

    if target_model is not None:
        target_model = Path(target_model)

        model_path_in_kicad = build_kicad_model_path(
            config=config,
            library_settings=library_settings,
            basename=basename,
            model_filename=target_model.name,
        )

        model_update_result = update_footprint_model_path(
            footprint_path=target_footprint,
            model_path_in_kicad=model_path_in_kicad,
        )

        model_reference_updated = model_update_result == "updated"
        model_reference_added = model_update_result == "added"
        model_reference_failed = model_update_result == "failed"

        run_state["footprint_update"]["model_reference_updated"] = model_reference_updated
        run_state["footprint_update"]["model_reference_added"] = model_reference_added
        run_state["footprint"]["model_property_updated"] = (
            model_reference_updated or model_reference_added
        )

        if model_reference_failed:
            update_errors.append("Footprint 3D model reference was not updated or added.")

    else:
        print()
        print("Footprint 3D model reference update skipped.")
        print("  No model file was selected for import.")

    metadata_added = add_import_metadata_properties(
        footprint_path=target_footprint,
        importer_version=f"V{APP_VERSION}",
    )

    run_state["footprint_update"]["metadata_added"] = metadata_added
    run_state["footprint"]["metadata_added"] = metadata_added

    if not metadata_added:
        update_errors.append("Footprint import metadata was not added.")

    if update_errors:
        failure_reason = (
            "Copied footprint content update did not complete cleanly.\n"
            f"Footprint: {target_footprint}\n"
            + "\n".join(f"- {error}" for error in update_errors)
        )

        return mark_failure(
            run_state,
            script="kicad_import_assistant.py",
            step="update_copied_footprint_contents",
            function_name="update_copied_footprint_contents",
            failure_reason=failure_reason,
            severity=Severity.ERROR,
        )

    run_state["footprint_update"]["complete"] = True
    run_state["import_plan"]["footprint"]["action"] = "COPIED_UPDATED"

    if target_model is not None:
        run_state["import_plan"]["model"]["action"] = "COPIED_REFERENCED"

    print()
    print("Footprint content updates:")
    print(f"  Footprint: {target_footprint.name}")
    print(f"  Internal name updated: {internal_name_updated}")
    print(f"  Value updated: {value_updated}")

    if target_model is not None:
        print(f"  Model reference updated: {run_state['footprint_update']['model_reference_updated']}")
        print(f"  Model reference added: {run_state['footprint_update']['model_reference_added']}")
        print(f"  Model path: {model_path_in_kicad}")

    print(f"  Metadata added: {metadata_added}")

    if run_state["import_plan"]["symbol"]["source_path"] is not None:
        print()
        print("Symbol merge still pending.")
        print(f"  Pending target: {run_state['import_plan']['symbol']['target_path']}")

    return mark_success(
        run_state,
        script="kicad_import_assistant.py",
        step="update_copied_footprint_contents",
        function_name="update_copied_footprint_contents",
        message="Copied footprint contents updated.",
    )


if __name__ == "__main__":
    main()


