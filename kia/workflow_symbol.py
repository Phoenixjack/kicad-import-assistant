"""
kia/workflow_symbol.py
  create_symbol_preview_stage()
  confirm_symbol_merge_execution()
  backup_target_symbol_library()
  merge_symbol_preview_stage()
"""

from pathlib import Path

from kia.app_info import APP_VERSION
from kia.debug import dbg_blank, dbg_print, Severity
from kia.workflow_status import mark_success, mark_failure
from kia.symbol_editor import (
    create_symbol_preview_file,
    check_symbol_merge_preconditions,
    create_symbol_library_backup,
    merge_symbol_preview_into_target,
)


def create_symbol_preview_stage(run_state: dict) -> dict:
    """
    Owns:
    - run_state["status"]
    - run_state["symbol_preview"]
    - run_state["symbol"]["preview_created"]
    - run_state["symbol"]["name_updated"]
    - run_state["symbol"]["footprint_property_updated"]
    - run_state["symbol"]["metadata_added"]

    Creates an edited preview symbol file in the temp import folder.

    This stage:
    - renames the preview symbol to the generated basename
    - updates the preview symbol Footprint property
    - adds preview symbol metadata
    - checks whether the target symbol library is ready for a future merge

    This stage does not modify the target symbol library.
    """
    selected_files = run_state["import_plan"]["selected_files"]
    library_settings = run_state["profile"]["settings"]
    basename = run_state["import_plan"]["basename"]
    extract_root = run_state["import_plan"]["temp_folder_path"]
    target_symbol_file = run_state["current"]["target_symbol_file"]

    source_symbol = run_state["import_plan"]["symbol"].get("source_path")

    if run_state["import_plan"]["symbol"].get("action") == "SKIPPED_BY_USER":
        dbg_blank(Severity.INFO, "symbols", "preview", "workflow_symbol")
        dbg_print("Symbol preview skipped by user.", Severity.INFO, "symbols", "preview", "workflow_symbol")

        run_state["symbol_preview"]["complete"] = True
        run_state["symbol_merge"]["complete"] = True

        return mark_success(
            run_state,
            script="kicad_import_assistant.py",
            step="create_symbol_preview",
            function_name="create_symbol_preview_stage",
            message="Symbol preview skipped by user.",
        )

    if source_symbol is None:
        dbg_blank(Severity.INFO, "symbols", "preview", "workflow_symbol")
        dbg_print("Symbol preview skipped.", Severity.INFO, "symbols", "preview", "workflow_symbol")
        dbg_print("No symbol was selected for import.", Severity.INFO, "symbols", "preview", "workflow_symbol")

        run_state["symbol_preview"]["complete"] = True

        return mark_success(
            run_state,
            script="kicad_import_assistant.py",
            step="create_symbol_preview",
            function_name="create_symbol_preview_stage",
            message="No symbol preview required.",
        )

    if not basename:
        return mark_failure(
            run_state,
            script="kicad_import_assistant.py",
            step="create_symbol_preview",
            function_name="create_symbol_preview_stage",
            failure_reason="Cannot create symbol preview because basename is missing.",
            severity=Severity.ERROR,
        )

    if extract_root is None:
        return mark_failure(
            run_state,
            script="kicad_import_assistant.py",
            step="create_symbol_preview",
            function_name="create_symbol_preview_stage",
            failure_reason="Cannot create symbol preview because temp folder is missing.",
            severity=Severity.ERROR,
        )

    if not library_settings:
        return mark_failure(
            run_state,
            script="kicad_import_assistant.py",
            step="create_symbol_preview",
            function_name="create_symbol_preview_stage",
            failure_reason="Cannot create symbol preview because library settings are missing.",
            severity=Severity.ERROR,
        )

    run_state["symbol_preview"]["attempted"] = True

    try:
        preview_result = create_symbol_preview_file(
            selected_files=selected_files,
            library_settings=library_settings,
            basename=basename,
            extract_root=extract_root,
            importer_version=f"V{APP_VERSION}",
        )

    except Exception as error:
        return mark_failure(
            run_state,
            script="kicad_import_assistant.py",
            step="create_symbol_preview",
            function_name="create_symbol_preview_stage",
            failure_reason=f"Unexpected error while creating symbol preview.\n{error}",
            severity=Severity.ERROR,
        )

    if not preview_result.get("symbol_preview_created"):
        return mark_failure(
            run_state,
            script="kicad_import_assistant.py",
            step="create_symbol_preview",
            function_name="create_symbol_preview_stage",
            failure_reason="Symbol preview file was not created.",
            severity=Severity.ERROR,
        )

    merge_precheck = check_symbol_merge_preconditions(
        target_symbol_file=target_symbol_file,
        new_symbol_name=basename,
    )

    run_state["symbol_preview"]["source_symbol"] = preview_result.get("source_symbol")
    run_state["symbol_preview"]["preview_symbol"] = preview_result.get("preview_symbol")
    run_state["symbol_preview"]["old_symbol_name"] = preview_result.get("old_symbol_name")
    run_state["symbol_preview"]["new_symbol_name"] = preview_result.get("new_symbol_name")
    run_state["symbol_preview"]["footprint_property"] = preview_result.get("footprint_property")
    run_state["symbol_preview"]["symbol_name_updated"] = preview_result.get("symbol_name_updated")
    run_state["symbol_preview"]["footprint_property_updated"] = preview_result.get("footprint_property_updated")
    run_state["symbol_preview"]["metadata_added"] = preview_result.get("metadata_added")
    run_state["symbol_preview"]["merge_precheck"] = merge_precheck

    run_state["symbol"]["preview_created"] = preview_result.get("symbol_preview_created")
    run_state["symbol"]["name_updated"] = preview_result.get("symbol_name_updated")
    run_state["symbol"]["footprint_property_updated"] = preview_result.get("footprint_property_updated")
    run_state["symbol"]["metadata_added"] = preview_result.get("metadata_added")

    update_errors = []

    if not preview_result.get("symbol_name_updated"):
        update_errors.append("Preview symbol name was not updated.")

    if not preview_result.get("footprint_property_updated"):
        update_errors.append("Preview symbol Footprint property was not updated.")

    if not preview_result.get("metadata_added"):
        update_errors.append("Preview symbol metadata was not added.")

    if not merge_precheck.get("symbol_merge_precheck_passed"):
        update_errors.append(
            "Symbol merge precheck failed: "
            + merge_precheck.get("reason", "Unknown reason.")
        )

    if update_errors:
        failure_reason = (
            "Symbol preview did not complete cleanly.\n"
            + "\n".join(f"- {error}" for error in update_errors)
        )

        return mark_failure(
            run_state,
            script="kicad_import_assistant.py",
            step="create_symbol_preview",
            function_name="create_symbol_preview_stage",
            failure_reason=failure_reason,
            severity=Severity.ERROR,
        )

    run_state["symbol_preview"]["complete"] = True
    run_state["import_plan"]["symbol"]["action"] = "PREVIEW_READY"

    dbg_blank(Severity.INFO, "symbols", "preview", "workflow_symbol")
    dbg_print("Symbol preview:", Severity.INFO, "symbols", "preview", "workflow_symbol")
    dbg_print(f"Source: {preview_result.get('source_symbol')}", Severity.INFO, "symbols", "preview", "workflow_symbol")
    dbg_print(f"Preview: {preview_result.get('preview_symbol')}", Severity.INFO, "symbols", "preview", "workflow_symbol")
    dbg_print(f"Old symbol name: {preview_result.get('old_symbol_name')}", Severity.INFO, "symbols", "preview", "workflow_symbol")
    dbg_print(f"New symbol name: {preview_result.get('new_symbol_name')}", Severity.INFO, "symbols", "preview", "workflow_symbol")
    dbg_print(f"Footprint property: {preview_result.get('footprint_property')}", Severity.INFO, "symbols", "preview", "workflow_symbol")
    dbg_print(f"Symbol name updated: {preview_result.get('symbol_name_updated')}", Severity.INFO, "symbols", "preview", "workflow_symbol")
    dbg_print(f"Footprint property updated: {preview_result.get('footprint_property_updated')}", Severity.INFO, "symbols", "preview", "workflow_symbol")
    dbg_print(f"Metadata added: {preview_result.get('metadata_added')}", Severity.INFO, "symbols", "preview", "workflow_symbol")

    dbg_blank(Severity.INFO, "symbols", "precheck", "workflow_symbol")
    dbg_print("Symbol merge precheck:", Severity.INFO, "symbols", "precheck", "workflow_symbol")
    dbg_print(f"Target symbol file exists: {merge_precheck.get('target_symbol_file_exists')}", Severity.INFO, "symbols", "precheck", "workflow_symbol")
    dbg_print(f"Target symbol already exists: {merge_precheck.get('target_symbol_already_exists')}", Severity.INFO, "symbols", "precheck", "workflow_symbol")
    dbg_print(f"Merge precheck passed: {merge_precheck.get('symbol_merge_precheck_passed')}", Severity.INFO, "symbols", "precheck", "workflow_symbol")
    dbg_print(f"Reason: {merge_precheck.get('reason')}", Severity.INFO, "symbols", "precheck", "workflow_symbol")
    dbg_print("Target symbol library was not modified.", Severity.INFO, "symbols", "precheck", "workflow_symbol")

    return mark_success(
        run_state,
        script="kicad_import_assistant.py",
        step="create_symbol_preview",
        function_name="create_symbol_preview_stage",
        message="Symbol preview created.",
    )


def confirm_symbol_merge_execution(run_state: dict) -> dict:
    """
    Owns:
    - run_state["status"]
    - run_state["symbol_merge"]["user_confirmed"]

    Requires hard confirmation before modifying the target symbol library.
    """
    if not run_state["symbol_preview"]["complete"]:
        return mark_failure(
            run_state,
            script="kicad_import_assistant.py",
            step="confirm_symbol_merge",
            function_name="confirm_symbol_merge_execution",
            failure_reason="Cannot confirm symbol merge because symbol preview is not complete.",
            severity=Severity.ERROR,
        )

    preview_symbol_file = run_state["symbol_preview"].get("preview_symbol")
    target_symbol_file = run_state["current"].get("target_symbol_file")
    basename = run_state["import_plan"].get("basename")

    if preview_symbol_file is None:
        dbg_blank(Severity.INFO, "symbols", "merge", "workflow_symbol")
        dbg_print("Symbol merge skipped.", Severity.INFO, "symbols", "merge", "workflow_symbol")
        dbg_print("No symbol preview exists.", Severity.INFO, "symbols", "merge", "workflow_symbol")

        run_state["symbol_merge"]["complete"] = True

        return mark_success(
            run_state,
            script="kicad_import_assistant.py",
            step="confirm_symbol_merge",
            function_name="confirm_symbol_merge_execution",
            message="No symbol merge required.",
        )

    print()
    print("SYMBOL MERGE CONFIRMATION REQUIRED")
    print("This will modify the target symbol library.")
    print()
    print(f"Preview symbol file: {preview_symbol_file}")
    print(f"Target symbol file:  {target_symbol_file}")
    print(f"Symbol name:         {basename}")
    print()
    print("A timestamped backup will be created before merge.")
    print()

    confirmation = input("Type MERGE to modify the target symbol library, or anything else to stop: ").strip()

    if confirmation != "MERGE":
        return mark_failure(
            run_state,
            script="kicad_import_assistant.py",
            step="confirm_symbol_merge",
            function_name="confirm_symbol_merge_execution",
            failure_reason="Symbol merge canceled by user before target symbol library modification.",
            severity=Severity.INFO,
        )

    run_state["symbol_merge"]["user_confirmed"] = True
    run_state["symbol_merge"]["preview_symbol_file"] = preview_symbol_file
    run_state["symbol_merge"]["target_symbol_file"] = target_symbol_file
    run_state["symbol_merge"]["merged_symbol_name"] = basename

    return mark_success(
        run_state,
        script="kicad_import_assistant.py",
        step="confirm_symbol_merge",
        function_name="confirm_symbol_merge_execution",
        message="Symbol merge confirmed.",
    )


def backup_target_symbol_library(run_state: dict) -> dict:
    """
    Owns:
    - run_state["status"]
    - run_state["symbol_merge"]["backup_path"]
    - run_state["symbol_merge"]["precheck"]
    - run_state["symbol"]["library_backed_up"]

    Rechecks merge preconditions and creates a timestamped backup of the
    target symbol library before merge.
    """
    if run_state["symbol_merge"]["complete"]:
        return mark_success(
            run_state,
            script="kicad_import_assistant.py",
            step="backup_target_symbol_library",
            function_name="backup_target_symbol_library",
            message="No symbol backup required.",
        )

    if not run_state["symbol_merge"]["user_confirmed"]:
        return mark_failure(
            run_state,
            script="kicad_import_assistant.py",
            step="backup_target_symbol_library",
            function_name="backup_target_symbol_library",
            failure_reason="Cannot backup symbol library because symbol merge was not confirmed.",
            severity=Severity.ERROR,
        )

    target_symbol_file = run_state["current"]["target_symbol_file"]
    basename = run_state["import_plan"]["basename"]

    if target_symbol_file is None:
        return mark_failure(
            run_state,
            script="kicad_import_assistant.py",
            step="backup_target_symbol_library",
            function_name="backup_target_symbol_library",
            failure_reason="Cannot backup symbol library because target symbol file is missing.",
            severity=Severity.ERROR,
        )

    precheck = check_symbol_merge_preconditions(
        target_symbol_file=target_symbol_file,
        new_symbol_name=basename,
    )

    run_state["symbol_merge"]["precheck"] = precheck

    if not precheck.get("symbol_merge_precheck_passed"):
        return mark_failure(
            run_state,
            script="kicad_import_assistant.py",
            step="backup_target_symbol_library",
            function_name="backup_target_symbol_library",
            failure_reason=(
                "Cannot backup/merge symbol because merge precheck failed.\n"
                f"Reason: {precheck.get('reason')}"
            ),
            severity=Severity.ERROR,
        )

    try:
        backup_path = create_symbol_library_backup(target_symbol_file)

    except Exception as error:
        return mark_failure(
            run_state,
            script="kicad_import_assistant.py",
            step="backup_target_symbol_library",
            function_name="backup_target_symbol_library",
            failure_reason=f"Failed to create target symbol library backup.\n{error}",
            severity=Severity.ERROR,
        )

    if backup_path is None:
        return mark_failure(
            run_state,
            script="kicad_import_assistant.py",
            step="backup_target_symbol_library",
            function_name="backup_target_symbol_library",
            failure_reason=(
                "Target symbol library backup was not created.\n"
                f"Target: {target_symbol_file}"
            ),
            severity=Severity.ERROR,
        )

    run_state["symbol_merge"]["backup_path"] = backup_path
    run_state["symbol"]["library_backed_up"] = True

    dbg_blank(Severity.INFO, "symbols", "backup", "workflow_symbol")
    dbg_print("Symbol library backup created:", Severity.INFO, "symbols", "backup", "workflow_symbol")
    dbg_print(f"Target: {target_symbol_file}", Severity.INFO, "symbols", "backup", "workflow_symbol")
    dbg_print(f"Backup: {backup_path}", Severity.INFO, "symbols", "backup", "workflow_symbol")

    return mark_success(
        run_state,
        script="kicad_import_assistant.py",
        step="backup_target_symbol_library",
        function_name="backup_target_symbol_library",
        message="Target symbol library backed up.",
    )


def merge_symbol_preview_stage(run_state: dict) -> dict:
    """
    Owns:
    - run_state["status"]
    - run_state["symbol_merge"]
    - run_state["symbol"]["merged"]
    - run_state["import_plan"]["symbol"]["action"]

    Merges the edited preview symbol into the target symbol library.

    This stage modifies the target .kicad_sym file.
    """
    if run_state["symbol_merge"]["complete"]:
        return mark_success(
            run_state,
            script="kicad_import_assistant.py",
            step="merge_symbol_preview",
            function_name="merge_symbol_preview_stage",
            message="No symbol merge required.",
        )

    if not run_state["symbol_merge"]["user_confirmed"]:
        return mark_failure(
            run_state,
            script="kicad_import_assistant.py",
            step="merge_symbol_preview",
            function_name="merge_symbol_preview_stage",
            failure_reason="Cannot merge symbol because merge was not confirmed.",
            severity=Severity.ERROR,
        )

    if not run_state["symbol"]["library_backed_up"]:
        return mark_failure(
            run_state,
            script="kicad_import_assistant.py",
            step="merge_symbol_preview",
            function_name="merge_symbol_preview_stage",
            failure_reason="Cannot merge symbol because target symbol library was not backed up.",
            severity=Severity.ERROR,
        )

    preview_symbol_file = run_state["symbol_merge"]["preview_symbol_file"]
    target_symbol_file = run_state["symbol_merge"]["target_symbol_file"]
    basename = run_state["symbol_merge"]["merged_symbol_name"]

    if preview_symbol_file is None:
        return mark_failure(
            run_state,
            script="kicad_import_assistant.py",
            step="merge_symbol_preview",
            function_name="merge_symbol_preview_stage",
            failure_reason="Cannot merge symbol because preview symbol file is missing.",
            severity=Severity.ERROR,
        )

    if target_symbol_file is None:
        return mark_failure(
            run_state,
            script="kicad_import_assistant.py",
            step="merge_symbol_preview",
            function_name="merge_symbol_preview_stage",
            failure_reason="Cannot merge symbol because target symbol file is missing.",
            severity=Severity.ERROR,
        )

    if not basename:
        return mark_failure(
            run_state,
            script="kicad_import_assistant.py",
            step="merge_symbol_preview",
            function_name="merge_symbol_preview_stage",
            failure_reason="Cannot merge symbol because symbol name is missing.",
            severity=Severity.ERROR,
        )

    preview_symbol_file = Path(preview_symbol_file)
    target_symbol_file = Path(target_symbol_file)

    try:
        merge_result = merge_symbol_preview_into_target(
            preview_symbol_file=preview_symbol_file,
            target_symbol_file=target_symbol_file,
            new_symbol_name=basename,
        )

    except Exception as error:
        return mark_failure(
            run_state,
            script="kicad_import_assistant.py",
            step="merge_symbol_preview",
            function_name="merge_symbol_preview_stage",
            failure_reason=f"Unexpected error while merging symbol preview.\n{error}",
            severity=Severity.ERROR,
        )

    run_state["symbol_merge"]["merge_result"] = merge_result

    if not merge_result.get("symbol_merged"):
        return mark_failure(
            run_state,
            script="kicad_import_assistant.py",
            step="merge_symbol_preview",
            function_name="merge_symbol_preview_stage",
            failure_reason=(
                "Symbol preview was not merged into target symbol library.\n"
                f"Reason: {merge_result.get('symbol_merge_reason')}"
            ),
            severity=Severity.ERROR,
        )

    dbg_blank(Severity.INFO, "symbols", "merge", "workflow_symbol")
    dbg_print("Symbol merge:", Severity.INFO, "symbols", "merge", "workflow_symbol")
    dbg_print(f"Preview: {preview_symbol_file}", Severity.INFO, "symbols", "merge", "workflow_symbol")
    dbg_print(f"Target: {target_symbol_file}", Severity.INFO, "symbols", "merge", "workflow_symbol")
    dbg_print(f"Symbol: {basename}", Severity.INFO, "symbols", "merge", "workflow_symbol")
    dbg_print(f"Result: {merge_result.get('symbol_merge_reason')}", Severity.INFO, "symbols", "merge", "workflow_symbol")
    dbg_print(f"Backup: {run_state['symbol_merge']['backup_path']}", Severity.INFO, "symbols", "merge", "workflow_symbol")

    return mark_success(
        run_state,
        script="kicad_import_assistant.py",
        step="merge_symbol_preview",
        function_name="merge_symbol_preview_stage",
        message="Symbol preview merged into target library.",
    )

