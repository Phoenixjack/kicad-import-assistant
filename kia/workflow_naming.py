"""
kia/workflow_naming.py
  collect_part_identity()
  check_for_existing_part()
  build_import_basename()
"""

from kia.debug import dbg_blank, dbg_print, Severity
from kia.workflow_status import mark_success, mark_failure
from kia.naming import (
    build_basename_from_prompts,
    suggest_defaults_from_files,
    prompt_with_default,
)
from kia.footprint_importer import (
    find_existing_files_by_mpn,
    warn_about_existing_mpn_matches,
    confirm_continue_after_duplicate_warning,
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
