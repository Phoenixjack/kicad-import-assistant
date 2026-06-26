"""
kia/workflow_footprint.py
  confirm_file_copy_execution()
  copy_planned_footprint_and_model_files()
  update_copied_footprint_contents()
"""

import shutil
from pathlib import Path

from kia.app_info import APP_VERSION
from kia.debug import dbg_blank, dbg_print, Severity
from kia.workflow_status import mark_success, mark_failure
from kia.footprint_importer import (
    build_kicad_model_path,
    update_footprint_internal_name,
    update_footprint_value_property,
    update_footprint_model_path,
    add_import_metadata_properties,
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
            severity=Severity.WARNING,
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
            severity=Severity.WARNING,
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
                severity=Severity.WARNING,
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

    dbg_blank(Severity.INFO, "importer", "copy", "workflow_footprint")
    dbg_print("Copied files:", Severity.INFO, "importer", "copy", "workflow_footprint")

    if not copied_files:
        dbg_print(
            "No footprint/model files were selected for copy.",
            Severity.INFO,
            "importer",
            "copy",
            "workflow_footprint",
        )
    else:
        for copied_file in copied_files:
            dbg_print(f"{copied_file['type']}:", Severity.INFO, "importer", "copy", "workflow_footprint")
            dbg_print(f"Source: {copied_file['source']}", Severity.INFO, "importer", "copy", "workflow_footprint")
            dbg_print(f"Target: {copied_file['target']}", Severity.INFO, "importer", "copy", "workflow_footprint")

    if run_state["import_plan"]["symbol"]["source_path"] is not None:
        dbg_blank(Severity.INFO, "importer", "copy", "workflow_footprint")
        dbg_print("Symbol merge still pending.", Severity.INFO, "importer", "copy", "workflow_footprint")
        dbg_print(
            f"Pending target: {run_state['import_plan']['symbol']['target_path']}",
            Severity.INFO,
            "importer",
            "copy",
            "workflow_footprint",
        )

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
        dbg_blank(Severity.INFO, "importer", "footprint", "workflow_footprint")
        dbg_print("Footprint content update skipped.", Severity.INFO, "importer", "footprint", "workflow_footprint")
        dbg_print("No footprint was selected for import.", Severity.INFO, "importer", "footprint", "workflow_footprint")

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
        dbg_blank(Severity.INFO, "importer", "model", "workflow_footprint")
        dbg_print("Footprint 3D model reference update skipped.", Severity.INFO, "importer", "model", "workflow_footprint")
        dbg_print("No model file was selected for import.", Severity.INFO, "importer", "model", "workflow_footprint")

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

    dbg_blank(Severity.INFO, "importer", "footprint", "workflow_footprint")
    dbg_print("Footprint content updates:", Severity.INFO, "importer", "footprint", "workflow_footprint")
    dbg_print(f"Footprint: {target_footprint.name}", Severity.INFO, "importer", "footprint", "workflow_footprint")
    dbg_print(f"Internal name updated: {internal_name_updated}", Severity.INFO, "importer", "footprint", "workflow_footprint")
    dbg_print(f"Value updated: {value_updated}", Severity.INFO, "importer", "footprint", "workflow_footprint")

    if target_model is not None:
        dbg_print(
            f"Model reference updated: {run_state['footprint_update']['model_reference_updated']}",
            Severity.INFO,
            "importer",
            "footprint",
            "workflow_footprint",
        )
        dbg_print(
            f"Model reference added: {run_state['footprint_update']['model_reference_added']}",
            Severity.INFO,
            "importer",
            "footprint",
            "workflow_footprint",
        )
        dbg_print(f"Model path: {model_path_in_kicad}", Severity.INFO, "importer", "footprint", "workflow_footprint")

    dbg_print(f"Metadata added: {metadata_added}", Severity.INFO, "importer", "footprint", "workflow_footprint")

    if run_state["import_plan"]["symbol"]["source_path"] is not None:
        dbg_blank(Severity.INFO, "importer", "footprint", "workflow_footprint")
        dbg_print("Symbol merge still pending.", Severity.INFO, "importer", "footprint", "workflow_footprint")
        dbg_print(
            f"Pending target: {run_state['import_plan']['symbol']['target_path']}",
            Severity.INFO,
            "importer",
            "footprint",
            "workflow_footprint",
        )

    return mark_success(
        run_state,
        script="kicad_import_assistant.py",
        step="update_copied_footprint_contents",
        function_name="update_copied_footprint_contents",
        message="Copied footprint contents updated.",
    )
