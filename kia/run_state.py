from kia.debug import (
    dbg_blank,
    dbg_print, 
    Severity, 
)

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
        # These may later update config["last"] if the run succeeds.
        "current": {
            "zip_path": None,
            "zip_folder": None,
            "library_root": None,
            "library_folder": None,
            "target_library": None,
            "target_footprint_dir": None,
            "target_symbol_file": None,
        },

        # Source files discovered after ZIP extraction / source scan.
        # These are the raw candidates found before the user chooses what to import.
        "source_files": {
            "found_files": None,
            "footprints": [],
            "symbols": [],
            "models": [],
            "other": [],
            "scan_complete": False,
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

