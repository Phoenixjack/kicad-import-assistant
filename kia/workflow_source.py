"""
kia/workflow_source.py
  prepare_import_source()
  discover_source_files()
  cleanup_import_temp_files()
"""

from kia.debug import Severity
from kia.workflow_status import mark_success, mark_failure
from kia.source_scan import (
    extract_zip_to_temp,
    find_import_files,
    cleanup_temp_folder,
)
from kia.workflow_final import ensure_finalization_state


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


def cleanup_import_temp_files(run_state: dict) -> dict:
    """
    Owns:
    - run_state["status"]
    - run_state["finalization"]["temp_cleanup_attempted"]
    - run_state["finalization"]["temp_cleanup_performed"]
    - run_state["finalization"]["temp_cleanup_skipped_reason"]

    Deletes the temporary import folder only when it is safe to do so.

    Preserve temp files when:
    - keep_temp_files is enabled
    - preview/import-plan CSV was written
    """
    run_state = ensure_finalization_state(run_state)
    config = run_state["config"]["general_config"]
    temp_folder = run_state["import_plan"].get("temp_folder_path")
    manifest_path = run_state["import_plan"].get("manifest_path")

    keep_temp_files = bool(config.get("keep_temp_files", False))

    preserve_temp_files = False
    skipped_reason = None

    preserve_temp_files = keep_temp_files
    skipped_reason = None

    if keep_temp_files:
        skipped_reason = "Config keep_temp_files is enabled."

    run_state["finalization"]["temp_cleanup_attempted"] = True
    run_state["finalization"]["temp_folder"] = temp_folder

    try:
        cleanup_performed = cleanup_temp_folder(
            temp_folder=temp_folder,
            keep_temp_files=preserve_temp_files,
        )

    except Exception as error:
        return mark_failure(
            run_state,
            script="kicad_import_assistant.py",
            step="cleanup_import_temp_files",
            function_name="cleanup_import_temp_files",
            failure_reason=f"Failed during temp-folder cleanup.\n{error}",
            severity=Severity.ERROR,
        )

    run_state["finalization"]["temp_cleanup_performed"] = cleanup_performed
    run_state["finalization"]["temp_cleanup_skipped_reason"] = skipped_reason

    print()
    print("Temp folder cleanup:")

    if cleanup_performed:
        print("  Deleted temp folder.")
        print(f"  Temp folder: {temp_folder}")

    elif skipped_reason:
        print("  Preserved temp folder.")
        print(f"  Reason: {skipped_reason}")
        print(f"  Temp folder: {temp_folder}")

    else:
        print("  Temp folder cleanup was skipped or not needed.")
        print(f"  Temp folder: {temp_folder}")

    return mark_success(
        run_state,
        script="kicad_import_assistant.py",
        step="cleanup_import_temp_files",
        function_name="cleanup_import_temp_files",
        message="Temp-folder cleanup stage complete.",
    )


