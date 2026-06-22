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
    import_result will be updated at each step to report status
    Whenever possible, we will avoid SystemExit calls to keep troubleshooting simpler
    Steps may be skipped if moving forward would cause an error, and
    addressed with the outgoing summary
    """
    
    root = initialize_tkinter_dialogs()
    config = load_config()
    naming_schema = load_naming_schema()

    # -------------- PLACEHOLDER FOR REWORK --------------
    
    # create a JSON dictionary of flags and temp data
    import_result = initialize_import_result()

    input_context = collect_and_validate_user_input(config)

    zip_path = input_context["zip_path"]
    library_folder = input_context["library_folder"]
    library_root = input_context["library_root"]
    suggested_profile = input_context["suggested_profile"]
    target_library = input_context["target_library"]
    library_settings = input_context["library_settings"]
    target_footprint_dir = input_context["target_footprint_dir"]

    if confirm_import():
        print("we're doin it")
        # now do import stuff
    
    # IF NOT config.keep_temp_files && import_result.files_extracted THEN cleanup_temp_folder()
    # IF import_result.import_complete THEN update_config()
    # perform final_report()
    # END MAIN()


def initialize_tkinter_dialogs() -> tk.Tk:
    root = tk.Tk()
    root.withdraw()
    return root


def initialize_run_state() -> dict:
    """
    Create the shared runtime state for one import attempt.

    This acts like a lightweight C-style struct:
    - each stage reads/writes only its assigned section
    - each stage updates run_state["status"]
    - main() checks status after each stage
    - config updates are staged here first, then saved only after success
    """

    run_state = {
        # Latest stage status.
        # main() uses this to decide whether to continue or stop.
        "status": {
            "success": False,
            "severity": Severity.VERBOSE,
            "script": None,
            "step": None,
            "function_name": None,
            "failure_reason": None,
            "message": None,
        },

        # Config/schema/rules loaded from disk.
        # These are required before the import workflow can safely continue.
        "config": {
            "general_config_loaded": False,
            "naming_schema_loaded": False,
            "suggestion_rules_loaded": False,
            "loaded": False,

            # Actual loaded data objects.
            "general_config": None,
            "naming_schema": None,
            "suggestion_rules": None,
        },

        # Raw user selections and basic validation results.
        # This stage should confirm paths exist and are usable.
        "user_input": {
            "zip_file_valid": False,
            "library_folder_valid": False,
            "library_root_valid": False,
            "selections_valid": False,
        },

        # Library/profile selection.
        # This connects selected folders to configured library profiles.
        "profile": {
            "autosuggested": False,
            "suggested_profile": None,
            "user_confirmed": False,
            "selected_profile": None,
            "settings": None,
        },

        # Current paths/profile values for this run.
        # These may later update config["last_*"] values if the run succeeds.
        "current": {
            "zip_path": None,
            "zip_folder": None,
            "library_root": None,
            "library_folder": None,
            "target_library": None,
            "target_footprint_dir": None,
            "target_symbol_file": None,
        },

        # Planned import actions before anything is written.
        # This replaces the old "manifest" concept.
        "import_plan": {
            "temp_folder_path": None,
            "basename": None,

            "symbol": {
                "source_path": None,
                "target_path": None,
                "raw_filename": None,
                "new_filename": None,
                "action": None,
            },

            "footprint": {
                "source_path": None,
                "target_path": None,
                "raw_filename": None,
                "new_filename": None,
                "action": None,
            },

            "model": {
                "source_path": None,
                "target_path": None,
                "raw_filename": None,
                "new_filename": None,
                "action": None,
            },

            "is_complete": False,
            "user_wants_to_review": False,
        },

        # Recent prompt values gathered during this run.
        # These should only be saved back to config after successful completion.
        "recent_values": {},

        # Future flag for user-entered schema options.
        # Example: new family/role/orientation values not already in schema.
        "user_entered_new_schema": False,

        # Symbol-specific state.
        # Symbols are merged into a .kicad_sym library.
        "symbol": {
            "exists_in_source": False,
            "exists_in_target": False,
            "duplicate": False,
            "preview_created": False,
            "name_updated": False,
            "metadata_added": False,
            "library_backed_up": False,
            "footprint_property_updated": False,
            "user_chose_import": False,
            "merged": False,
        },

        # Footprint-specific state.
        # Footprints are copied/renamed/edited, not merged.
        "footprint": {
            "exists_in_source": False,
            "exists_in_target": False,
            "duplicate": False,
            "preview_created": False,
            "name_updated": False,
            "metadata_added": False,
            "model_property_updated": False,
            "user_chose_import": False,
            "copied": False,
        },

        # Model-specific state.
        # Models are copied/renamed and referenced by footprints.
        "model": {
            "exists_in_source": False,
            "exists_in_target": False,
            "duplicate": False,
            "preview_created": False,
            "name_updated": False,
            "metadata_added": False,
            "user_chose_import": False,
            "copied": False,
        },

        # Final aggregate flags/results.
        "user_confirmed_import": False,
        "copied_files": [],
        "files_copied": False,
        "was_successful": False,
    }

    return run_state


def stage_config_updates(run_state: dict) -> dict:
    """
    Build the config sections that should be saved after a successful run.

    Does not write to disk.
    """
    return {
        "last": run_state["current"],
        "recent_values": run_state["recent_values"],
    }


def apply_successful_config_updates(config: dict, run_state: dict) -> dict:
    config["last"] = run_state["current"]
    config["recent_values"] = run_state["recent_values"]
    return config






def critical_error(config: dict) -> None:
    print("CRITICAL ERROR")
    print(f"{config.status.failure_reason}")
    print(f"{config.status.script} / {config.status.step} / {config.status.function_name}")
    raise SystemExit
    
def collect_and_validate_user_input(config: dict) -> dict:
    """
    Collect user-selected import source and target library info.

    Returns a context dictionary containing validated paths/profile settings.
    Raises SystemExit on invalid required input.
    """
    zip_path = select_import_source(config)

    dbg_print(
        f"Selected import source: {zip_path}",
        Severity.INFO,
        "dialogs",
        stage="select",
        source="main",
    )

    if not zip_path.exists():
        print()
        print("ERROR: Selected import source does not exist.")
        print(f"  Source: {zip_path}")
        raise SystemExit

    if not zip_path.is_file():
        print()
        print("ERROR: Selected import source is not a file.")
        print(f"  Source: {zip_path}")
        raise SystemExit

    if zip_path.suffix.lower() != ".zip":
        print()
        print("ERROR: Current import source must be a ZIP file.")
        print(f"  Source: {zip_path}")
        print()
        print("Loose-file and folder imports are planned but not implemented yet.")
        raise SystemExit

    library_folder = select_library_folder(config)

    suggested_profile = infer_profile_from_selected_folder(
        selected_folder = library_folder,
        config = config,
    )

    if suggested_profile:
        dbg_print(
            f"Inferred target library profile: {suggested_profile}",
            Severity.INFO,
            "libraries",
            stage = "infer",
            source = "main",
        )
    else:
        dbg_print(
            "No target library profile inferred from selected folder.",
            Severity.WARNING,
            "libraries",
            stage = "infer",
            source = "main",
        )

    target_library = select_target_library_profile(
        config = config,
        suggested_profile = suggested_profile,
    )

    dbg_print(
        f"Selected library folder: {library_folder}",
        Severity.INFO,
        "dialogs",
        stage = "select",
        source = "main",
    )

    if not library_folder.exists():
        print()
        print("ERROR: Selected library folder does not exist.")
        print(f"  Folder: {library_folder}")
        raise SystemExit

    if not library_folder.is_dir():
        print()
        print("ERROR: Selected library path is not a folder.")
        print(f"  Folder: {library_folder}")
        raise SystemExit

    library_root = resolve_library_root_from_selection(library_folder)

    dbg_print(
        f"Resolved library root: {library_root}",
        Severity.INFO,
        "libraries",
        stage="root",
        source="main",
    )

    if not library_root.exists():
        print()
        print("ERROR: Resolved library root does not exist.")
        print(f"  Root: {library_root}")
        raise SystemExit

    if not library_root.is_dir():
        print()
        print("ERROR: Resolved library root is not a folder.")
        print(f"  Root: {library_root}")
        raise SystemExit

    config["last_library_folder"] = str(library_folder)
    config["last_library_root"] = str(library_root)

    library_settings = config.get("libraries", {}).get(target_library, {})

    if not library_settings:
        print()
        print("ERROR: Target library profile was not found in config.")
        print(f"  Profile: {target_library}")
        print()
        print("Check kicad_import_assistant_config.json.")
        raise SystemExit

    required_profile_keys = [
        "prefix",
        "footprint_dir",
        "symbol_file",
        "nickname",
    ]

    missing_keys = [
        key for key in required_profile_keys
        if not library_settings.get(key)
    ]

    if missing_keys:
        print()
        print("ERROR: Target library profile is missing required fields.")
        print(f"  Profile: {target_library}")
        print(f"  Missing: {', '.join(missing_keys)}")
        raise SystemExit

    target_footprint_dir = library_root / library_settings["footprint_dir"]

    if not target_footprint_dir.exists():
        print()
        print("ERROR: Target footprint/model folder does not exist.")
        print(f"  Folder: {target_footprint_dir}")
        raise SystemExit

    if not target_footprint_dir.is_dir():
        print()
        print("ERROR: Target footprint/model path is not a folder.")
        print(f"  Folder: {target_footprint_dir}")
        raise SystemExit

    return {
        "zip_path": zip_path,
        "library_folder": library_folder,
        "library_root": library_root,
        "suggested_profile": suggested_profile,
        "target_library": target_library,
        "library_settings": library_settings,
        "target_footprint_dir": target_footprint_dir,
    }


def extract_zip(zip_path: Path, output_folder: Path) -> None:
    with zipfile.ZipFile(zip_path, "r") as zip_file:
        zip_file.extractall(output_folder)


def find_kicad_files(root_folder: Path) -> list[Path]:
    valid_extensions = {
        ".kicad_mod",
        ".kicad_sym",
        ".step",
        ".stp",
        ".wrl",
    }

    found_files = []

    for file in root_folder.rglob("*"):
        if file.is_file() and file.suffix.lower() in valid_extensions:
            found_files.append(file)

    return found_files


def copy_files_to_library(files: list[Path], library_root: Path) -> None:
    library_root.mkdir(parents=True, exist_ok=True)

    for source_file in files:
        destination = library_root / source_file.name
        shutil.copy2(source_file, destination)


def print_profile_settings(config: dict) -> None:
    dbg_print(f"Assistant version: {APP_VERSION}", Severity.INFO, "config")
    dbg_print(" ", Severity.INFO, "config")
    dbg_print("Selected import settings:", Severity.INFO, "config")
    dbg_print(f"ZIP...................... {zip_path}", Severity.INFO, "config")
    dbg_print(f"Library root............. {library_root}", Severity.VERBOSE, "config")
    dbg_print(f"Target library........... {target_library}", Severity.INFO, "config")
    dbg_print(f"Path variable............ {config.get('path_variable')}", Severity.INFO, "config")
    dbg_print(f"Nickname................. {library_settings.get('nickname')}", Severity.VERBOSE, "config")
    dbg_print(f"Prefix................... {library_settings.get('prefix')}", Severity.INFO, "config")
    if not target_footprint_dir.exists():
        dbg_print(" ", Severity.WARNING, "config", "load", "main")
        dbg_print(f"Missing target footprint/model folder: {target_footprint_dir}", Severity.WARNING, "config", "load", "main")
        dbg_print("The script may fail if this folder is needed for import.", Severity.WARNING, "config", "load", "main")
    else:
        dbg_print(f"Footprint dir............ {library_settings.get('footprint_dir')}", Severity.VERBOSE, "config")
        dbg_print(f"Footprint/model folder .. {target_footprint_dir}", Severity.INFO, "config")

    if target_symbol_file is not None:
        dbg_print(f"Symbol library file ..... {target_symbol_file}", Severity.INFO, "config")
    else:
        dbg_print("Symbol library file ..... <not resolved>", Severity.ERROR, "config", "RESOLVE", "MAIN")
        
    dbg_print(" ", Severity.VERBOSE, "config")
    dbg_print(f"Raw config .............. {config}", Severity.VERBOSE, "config")
    dbg_print(" ", Severity.VERBOSE, "config")
    dbg_print(f"Library settings ........ {library_settings}", Severity.VERBOSE, "config")
    dbg_print(" ", Severity.VERBOSE, "config")

    print("Active target library profile:")
    print(f"  Profile: {target_library}")
    print(f"  Prefix: {library_settings.get('prefix')}")
    print(f"  Footprint/model folder: {target_footprint_dir}")
    print(f"  Symbol file: {library_settings.get('symbol_file')}")
    print(f"  Nickname: {library_settings.get('nickname')}")
    return


def do_zip_stuff() -> None:
    extract_root = extract_zip_to_temp(zip_path)
    temp_cleanup_performed = False
    found_files = find_import_files(extract_root)
    print_import_file_summary(found_files, extract_root)
    return


def check_for_duplicate() -> None:
    print("Early duplicate check.")
    early_mpn = prompt_with_default("MPN for duplicate search", suggested_defaults.get("mpn", ""))

    existing_matches = find_existing_files_by_mpn(
        library_root=library_root,
        library_settings=library_settings,
        mpn=early_mpn,
    )

    warn_about_existing_mpn_matches(existing_matches, early_mpn)

    if not confirm_continue_after_duplicate_warning(existing_matches):
        print()
        print("Import canceled before naming step.")
        raise SystemExit

    return


def create_basename() -> None:
    basename = build_basename_from_prompts(
        config,
        library_settings,
        found_files,
        override_defaults={"mpn": early_mpn},
        suggested_defaults=suggested_defaults,
        naming_schema=naming_schema,
    )
    dbg_blank(Severity.VERBOSE, "basename", stage="build", source="main")
    dbg_print("Generated target basename:", Severity.VERBOSE, "basename", stage="build", source="main")
    dbg_print(f"{basename}", Severity.VERBOSE, "basename", stage="build", source="main")
    return


def perform_symbol_precheck() -> None:
    symbol_preview_result = create_symbol_preview_file(
    selected_files=selected_files,
    library_settings=library_settings,
    basename=basename,
    extract_root=extract_root,

    dbg_blank(Severity.VERBOSE, "symbols", stage="precheck", source="main")
    dbg_print(
        f"Target symbol file: {target_symbol_file}",
        Severity.VERBOSE,
        "symbols",
        stage="precheck",
        source="main",
    )
    dbg_print(
        f"Target symbol file type: {type(target_symbol_file)}",
        Severity.VERBOSE,
        "symbols",
        stage="precheck",
        source="main",
    )

    if target_symbol_file is not None:
        dbg_print(
            f"Target symbol file exists: {target_symbol_file.exists()}",
            Severity.VERBOSE,
            "symbols",
            stage="precheck",
            source="main",
        )
    
    symbol_merge_precheck = check_symbol_merge_preconditions(
        target_symbol_file=target_symbol_file,
        new_symbol_name=basename,
    )

    print()
    print("Symbol merge precheck:")
    print(f"  Target symbol file exists: {'YES' if symbol_merge_precheck.get('target_symbol_file_exists') else 'NO'}")
    print(f"  Target symbol already exists: {'YES' if symbol_merge_precheck.get('target_symbol_already_exists') else 'NO'}")
    print(f"  Precheck passed: {'YES' if symbol_merge_precheck.get('symbol_merge_precheck_passed') else 'NO'}")
    print(f"  Reason: {symbol_merge_precheck.get('reason')}")
    
    print()
    print("Symbol preview:")
    if symbol_preview_result.get("symbol_preview_created"):
        print(f"  Preview file: {symbol_preview_result.get('preview_symbol')}")
        print(f"  Old symbol name: {symbol_preview_result.get('old_symbol_name')}")
        print(f"  New symbol name: {symbol_preview_result.get('new_symbol_name')}")
        print(f"  Footprint property: {symbol_preview_result.get('footprint_property')}")
        print(f"  Symbol name updated: {'YES' if symbol_preview_result.get('symbol_name_updated') else 'NO'}")
        print(f"  Footprint property updated: {'YES' if symbol_preview_result.get('footprint_property_updated') else 'NO'}")
    else:
        print("  No symbol preview created.")
        
    dbg_blank(Severity.VERBOSE, "symbols", stage="preview", source="main")
    dbg_print(
        f"Selected file keys: {list(selected_files.keys())}",
        Severity.VERBOSE,
        "symbols",
        stage="preview",
        source="main",
    )
    dbg_print(
        f"Selected symbol: {selected_files.get('symbol')}",
        Severity.VERBOSE,
        "symbols",
        stage="preview",
        source="main",
    )
    dbg_print(
        f"Extract root: {extract_root}",
        Severity.VERBOSE,
        "symbols",
        stage="preview",
        source="main",
    )
    
            if symbol_merge_precheck.get("symbol_merge_precheck_passed", False):
            symbol_backup_path = create_symbol_library_backup(target_symbol_file)

            if symbol_backup_path is not None:
                import_result["symbol_backup_created"] = True
                import_result["symbol_backup_path"] = symbol_backup_path

                merge_result = merge_symbol_preview_into_target(
                    preview_symbol_file=symbol_preview_result.get("preview_symbol"),
                    target_symbol_file=target_symbol_file,
                    new_symbol_name=basename,
                )

                import_result.update(merge_result)
            else:
                import_result["symbol_merge_reason"] = "Symbol backup was not created; merge skipped."
        else:
            import_result["symbol_merge_reason"] = symbol_merge_precheck.get(
                "reason",
                "Symbol merge precheck failed.",
            )
            
    return


def create_manifest() -> None:
    confirm_manifest = input("Create preview manifest? [y/N]: ").strip().lower()

    if confirm_manifest in ["", "n", "no"]:
        dbg_print("Preview manifest skipped.", Severity.INFO, "manifest", stage="preview", source="main")
    else:
        create_preview_manifest(
            selected_files=selected_files,
            extract_root=extract_root,
            library_root=library_root,
            library_settings=library_settings,
            basename=basename,
            target_symbol_file=target_symbol_file,
        )
    return


def perform_import() -> None:
    copy_result = copy_selected_import_files(
    selected_files=selected_files,
    library_root=library_root,
    library_settings=library_settings,
    config=config,
    basename=basename,
    app_version=APP_VERSION,

    import_result.update(copy_result)
    return

if __name__ == "__main__":
    main()


def junkyard() -> None:
    
    suggested_defaults = suggest_defaults_from_files(found_files)

    selected_files = select_import_files(found_files)

    import_result["symbol_preview_created"] = symbol_preview_result.get("symbol_preview_created", False)
    import_result["symbol_name_updated"] = symbol_preview_result.get("symbol_name_updated", False)
    import_result["symbol_footprint_property_updated"] = symbol_preview_result.get("footprint_property_updated", False)

    save_config(config)
    dbg_blank(Severity.VERBOSE, "config", stage="save", source="main")
    dbg_print(f"Config saved: {CONFIG_PATH}", Severity.VERBOSE, "config", stage="save", source="main")
    print()
    print(f"Version {APP_VERSION} complete.")
    print()
    print("Import status:")

    if import_result.get("confirmed", False):
        print(f"  Files copied: {'YES' if import_result.get('files_copied') else 'NO'}")
        print(f"  Footprint internal name updated: {'YES' if import_result.get('footprint_name_updated') else 'NO'}")
        print(f"  Footprint Value field updated: {'YES' if import_result.get('footprint_value_updated') else 'NO'}")

        if import_result.get("model_reference_added"):
            print("  3D model reference: ADDED")
        elif import_result.get("model_reference_updated"):
            print("  3D model reference: UPDATED")
        else:
            print("  3D model reference: NO")
        
        print(f"  Import metadata present: {'YES' if import_result.get('metadata_added') else 'NO'}")
        print(f"  Symbol preview created: {'YES' if import_result.get('symbol_preview_created') else 'NO'}")
        print(f"  Symbol name preview updated: {'YES' if import_result.get('symbol_name_updated') else 'NO'}")
        print(f"  Symbol Footprint property preview updated: {'YES' if import_result.get('symbol_footprint_property_updated') else 'NO'}")
        print(f"  Symbol merged: {'YES' if import_result.get('symbol_merged') else 'NO'}")
        print(f"    Reason: {import_result.get('symbol_merge_reason')}")
        print(f"  Symbol backup created: {'YES' if import_result.get('symbol_backup_created') else 'NO'}")

        if import_result.get("symbol_backup_path"):
            print(f"    Backup: {import_result.get('symbol_backup_path')}")
    else:
        print("  Files copied: NO - import was canceled")
        print("  Footprint updates: NOT ATTEMPTED")
        print("  Symbol merged: NO")

    keep_temp_files = bool(config.get("keep_temp_files", True))

    temp_cleanup_performed = cleanup_temp_folder(
        temp_folder=extract_root,
        keep_temp_files=keep_temp_files,
    )

    print(f"  Temp folder cleanup: {'YES' if temp_cleanup_performed else 'NO'}")

    if keep_temp_files and extract_root is not None:
        print(f"    Temp folder kept: {extract_root}")