"""
kia/workflow_final.py
  print_final_import_summary()
  ensure_finalization_state()
"""

from kia.workflow_status import mark_success

def print_final_import_summary(run_state: dict) -> dict:
    """
    Owns:
    - run_state["status"]
    - run_state["finalization"]["final_summary_printed"]
    - run_state["was_successful"]

    Prints the final successful import summary.
    """
    run_state = ensure_finalization_state(run_state)
    basename = run_state["import_plan"]["basename"]
    footprint_plan = run_state["import_plan"]["footprint"]
    model_plan = run_state["import_plan"]["model"]
    symbol_plan = run_state["import_plan"]["symbol"]

    target_footprint = footprint_plan.get("target_path")
    target_model = model_plan.get("target_path")
    target_symbol_file = run_state["current"].get("target_symbol_file")
    symbol_backup = run_state["symbol_merge"].get("backup_path")
    manifest_path = run_state["import_plan"].get("manifest_path")
    temp_folder = run_state["import_plan"].get("temp_folder_path")

    print()
    print("IMPORT COMPLETE")
    print(f"  Basename: {basename}")

    print()
    print("Imported files:")

    footprint_was_imported = (
        run_state["footprint"].get("copied")
        or footprint_plan.get("action") == "COPIED_UPDATED"
    )

    model_was_imported = (
        run_state["model"].get("copied")
        or model_plan.get("action") == "COPIED_REFERENCED"
    )

    if footprint_was_imported and target_footprint is not None:
        print(f"  Footprint: {target_footprint}")
    else:
        print("  Footprint: SKIPPED")

    if model_was_imported and target_model is not None:
        print(f"  3D model:  {target_model}")
    else:
        print("  3D model:  SKIPPED")

    symbol_merge_result = run_state["symbol_merge"].get("merge_result") or {}

    symbol_was_merged = (
        run_state["symbol"].get("merged")
        or symbol_merge_result.get("symbol_merged")
        or symbol_plan.get("action") == "MERGED"
    )

    if symbol_was_merged:
        print(f"  Symbol:    {target_symbol_file}")
    else:
        print("  Symbol:    SKIPPED")

    print()
    print("Safety artifacts:")

    if symbol_backup is not None:
        print(f"  Symbol backup: {symbol_backup}")
    else:
        print("  Symbol backup: none")

    if manifest_path is not None:
        print(f"  Preview CSV:    {manifest_path}")
    else:
        print("  Preview CSV:    not written")

    print()
    print("Cleanup:")
    print(f"  Temp folder: {temp_folder}")
    print(f"  Temp deleted: {run_state['finalization']['temp_cleanup_performed']}")

    run_state["finalization"]["final_summary_printed"] = True
    run_state["was_successful"] = True

    return mark_success(
        run_state,
        script="kicad_import_assistant.py",
        step="print_final_import_summary",
        function_name="print_final_import_summary",
        message="Final import summary printed.",
    )


def ensure_finalization_state(run_state: dict) -> dict:
    """
    Ensure finalization state exists even if an older/incomplete run_state
    initializer is being used.
    """
    defaults = {
        "attempted": False,
        "config_saved": False,
        "temp_cleanup_attempted": False,
        "temp_cleanup_performed": False,
        "temp_cleanup_skipped_reason": None,
        "temp_folder": None,
        "final_summary_printed": False,
    }

    run_state.setdefault("finalization", {})

    for key, value in defaults.items():
        run_state["finalization"].setdefault(key, value)

    return run_state
