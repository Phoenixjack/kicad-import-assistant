"""
kia/workflow_execution.py
  confirm_selected_import_actions()
"""

from kia.debug import Severity
from kia.workflow_status import mark_success, mark_failure


def plan_item_is_selected(plan_item: dict) -> bool:
    """
    Return True if a plan item still has an action selected.
    """
    if plan_item.get("source_path") is None:
        return False

    if plan_item.get("action") == "SKIPPED_BY_USER":
        return False

    return True


def has_selected_file_copy_actions(run_state: dict) -> bool:
    """
    Return True if footprint/model copy actions remain.
    """
    for file_type in ["footprint", "model"]:
        plan_item = run_state["import_plan"].get(file_type, {})

        if plan_item_is_selected(plan_item):
            return True

    return False


def has_selected_symbol_merge_action(run_state: dict) -> bool:
    """
    Return True if a symbol merge action remains.
    """
    symbol_plan = run_state["import_plan"].get("symbol", {})
    return plan_item_is_selected(symbol_plan)


def describe_selected_action(file_type: str, plan_item: dict) -> str:
    """
    Return a user-facing action description for one plan item.
    """
    if plan_item.get("source_path") is None:
        return "SKIP"

    if plan_item.get("action") == "SKIPPED_BY_USER":
        return "SKIP"

    if file_type == "footprint":
        return "COPY_RENAME + UPDATE"

    if file_type == "model":
        return "COPY_RENAME"

    if file_type == "symbol":
        return "MERGE with backup"

    return str(plan_item.get("action"))


def print_selected_execution_actions(run_state: dict) -> None:
    """
    Print the final selected actions before target-library writes.
    """
    print()
    print("Ready to execute selected actions:")
    print()

    for file_type in ["footprint", "model", "symbol"]:
        plan_item = run_state["import_plan"].get(file_type, {})
        action_description = describe_selected_action(file_type, plan_item)

        print(f"  {file_type.capitalize()}: {action_description}")

        if action_description != "SKIP":
            print(f"    Source: {plan_item.get('source_path')}")
            print(f"    Target: {plan_item.get('target_path')}")

    print()
    print("Safety behavior:")
    print("  - Existing footprint/model targets will not be overwritten.")
    print("  - Symbol merge will create a timestamped backup.")
    print("  - Skipped items will not be imported or archived.")


def confirm_selected_import_actions(run_state: dict) -> dict:
    """
    Ask for one final confirmation before selected target-library writes.

    This replaces the separate COPY and MERGE hard prompts.
    """
    if not run_state["import_plan"]["is_complete"]:
        return mark_failure(
            run_state,
            script="workflow_execution.py",
            step="confirm_selected_import_actions",
            function_name="confirm_selected_import_actions",
            failure_reason="Cannot confirm execution because the import plan is not complete.",
            severity=Severity.ERROR,
        )

    file_copy_needed = has_selected_file_copy_actions(run_state)
    symbol_merge_needed = has_selected_symbol_merge_action(run_state)

    if not file_copy_needed and not symbol_merge_needed:
        return mark_failure(
            run_state,
            script="workflow_execution.py",
            step="confirm_selected_import_actions",
            function_name="confirm_selected_import_actions",
            failure_reason="No selected import actions remain.",
            severity=Severity.INFO,
        )

    print_selected_execution_actions(run_state)

    print()
    response = input("Proceed with selected actions? [y/N]: ").strip().lower()

    if response not in ["y", "yes"]:
        return mark_failure(
            run_state,
            script="workflow_execution.py",
            step="confirm_selected_import_actions",
            function_name="confirm_selected_import_actions",
            failure_reason="Import execution canceled by user before target-library writes.",
            severity=Severity.INFO,
        )

    run_state.setdefault("execution_confirmation", {})
    run_state["execution_confirmation"]["user_confirmed"] = True
    run_state["execution_confirmation"]["file_copy_needed"] = file_copy_needed
    run_state["execution_confirmation"]["symbol_merge_needed"] = symbol_merge_needed

    run_state["file_copy"]["user_confirmed"] = file_copy_needed

    if not file_copy_needed:
        run_state["file_copy"]["complete"] = True

    run_state["symbol_merge"]["user_confirmed"] = symbol_merge_needed

    run_state["user_confirmed_import"] = True

    return mark_success(
        run_state,
        script="workflow_execution.py",
        step="confirm_selected_import_actions",
        function_name="confirm_selected_import_actions",
        message="Selected import actions confirmed.",
    )