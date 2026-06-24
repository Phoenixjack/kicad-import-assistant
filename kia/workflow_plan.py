"""
kia/workflow_plan.py
  select_files_for_import()
  create_import_plan()
  review_import_plan()
"""

from kia.debug import Severity
from kia.workflow_status import mark_success, mark_failure
from kia.import_plan import (
    create_preview_manifest,
    select_import_files,
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
