"""
kia/workflow_source_cleanup.py
  archive_successful_loose_source_files()
"""

import shutil
from datetime import datetime
from pathlib import Path

from kia.debug import dbg_blank, dbg_print, Severity
from kia.workflow_status import mark_success


def make_unique_archive_path(archive_dir: Path, source_path: Path) -> Path:
    """
    Build a non-overwriting archive destination path.

    If foo.step exists, use foo.<timestamp>.step.
    """
    candidate = archive_dir / source_path.name

    if not candidate.exists():
        return candidate

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return archive_dir / f"{source_path.stem}.{timestamp}{source_path.suffix}"


def prompt_archive_source_files(source_paths: list[Path], archive_dir: Path) -> bool:
    """
    Ask whether to archive original loose source files after successful import.
    """
    print()
    if source_mode == "zip":
        print("ZIP import source was processed successfully.")
    else:
        print("Loose source files were imported successfully.")
    print()
    print("Move original source files to archive folder?")
    print(f"  {archive_dir}")
    print()
    print("Source files:")

    for source_path in source_paths:
        print(f"  - {source_path.name}")

    print()
    response = input("Move source files? [y/N]: ").strip().lower()

    return response in ["y", "yes"]


def archive_successful_source_files(run_state: dict) -> dict:
    """
    Offer to archive original loose source files after successful import.

    This only applies to loose-file imports.
    ZIP files are intentionally skipped.
    """
    config = run_state["config"]["general_config"]
    cleanup_config = config.get("source_cleanup", {})

    run_state.setdefault("source_cleanup", {})
    run_state["source_cleanup"].setdefault("archived_files", [])
    run_state["source_cleanup"].setdefault("skipped_files", [])
    run_state["source_cleanup"].setdefault("failed_files", [])

    source_mode = run_state["current"].get("source_mode")
    source_paths = run_state["current"].get("source_paths", [])

    source_mode = run_state["current"].get("source_mode")

    archive_loose_files = bool(cleanup_config.get("archive_loose_files", True))
    archive_zip_files = bool(cleanup_config.get("archive_zip_files", True))

    if source_mode == "loose_files" and not archive_loose_files:
        return mark_success(
            run_state,
            script="workflow_source_cleanup.py",
            step="archive_source_files",
            function_name="archive_successful_source_files",
            message="Source cleanup skipped because loose-file archiving is disabled.",
        )

    if source_mode == "zip" and not archive_zip_files:
        return mark_success(
            run_state,
            script="workflow_source_cleanup.py",
            step="archive_source_files",
            function_name="archive_successful_source_files",
            message="Source cleanup skipped because ZIP archiving is disabled.",
        )

    if source_mode not in ["loose_files", "zip"]:
        return mark_success(
            run_state,
            script="workflow_source_cleanup.py",
            step="archive_source_files",
            function_name="archive_successful_source_files",
            message=f"Source cleanup skipped for unsupported source mode: {source_mode}",
        )

    if not cleanup_config.get("prompt_after_success", True):
        return mark_success(
            run_state,
            script="workflow_source_cleanup.py",
            step="archive_source_files",
            function_name="archive_successful_loose_source_files",
            message="Source cleanup skipped by config.",
        )

    if cleanup_config.get("mode", "archive") != "archive":
        return mark_success(
            run_state,
            script="workflow_source_cleanup.py",
            step="archive_source_files",
            function_name="archive_successful_loose_source_files",
            message="Source cleanup skipped because cleanup mode is not archive.",
        )

    if not source_paths:
        return mark_success(
            run_state,
            script="workflow_source_cleanup.py",
            step="archive_source_files",
            function_name="archive_successful_loose_source_files",
            message="Source cleanup skipped because no source paths were recorded.",
        )

    source_paths = [Path(path) for path in source_paths]

    source_folder = run_state["current"].get("source_folder")

    if source_folder is None:
        source_folder = source_paths[0].parent

    source_folder = Path(source_folder)

    archive_folder_name = cleanup_config.get("archive_folder_name", "_imported")
    archive_dir = source_folder / archive_folder_name

    run_state["source_cleanup"]["attempted"] = True
    run_state["source_cleanup"]["offered"] = True
    run_state["source_cleanup"]["mode"] = "archive"
    run_state["source_cleanup"]["archive_dir"] = archive_dir

    user_confirmed = prompt_archive_source_files(
        source_paths=source_paths,
        archive_dir=archive_dir,
    )

    run_state["source_cleanup"]["user_confirmed"] = user_confirmed

    if not user_confirmed:
        print()
        print("Source files left in place.")
        return mark_success(
            run_state,
            script="workflow_source_cleanup.py",
            step="archive_source_files",
            function_name="archive_successful_loose_source_files",
            message="User chose not to archive source files.",
        )

    archive_dir.mkdir(parents=True, exist_ok=True)

    print()
    print("Archiving source files:")

    for source_path in source_paths:
        try:
            if not source_path.exists():
                run_state["source_cleanup"]["skipped_files"].append(source_path)
                print(f"  SKIPPED missing file: {source_path.name}")
                continue

            if not source_path.is_file():
                run_state["source_cleanup"]["skipped_files"].append(source_path)
                print(f"  SKIPPED not a file: {source_path.name}")
                continue

            destination_path = make_unique_archive_path(
                archive_dir=archive_dir,
                source_path=source_path,
            )

            shutil.move(str(source_path), str(destination_path))

            run_state["source_cleanup"]["archived_files"].append(destination_path)
            print(f"  MOVED: {source_path.name} -> {destination_path.name}")

        except Exception as error:
            run_state["source_cleanup"]["failed_files"].append(
                {
                    "source": source_path,
                    "error": str(error),
                }
            )
            print(f"  WARNING: Failed to move {source_path.name}")
            print(f"    {error}")

    dbg_blank(Severity.INFO, "source", "archive", "cleanup")
    dbg_print(
        f"Archived files: {len(run_state['source_cleanup']['archived_files'])}",
        Severity.INFO,
        "source",
        "archive",
        "cleanup",
    )
    dbg_print(
        f"Skipped files: {len(run_state['source_cleanup']['skipped_files'])}",
        Severity.INFO,
        "source",
        "archive",
        "cleanup",
    )
    dbg_print(
        f"Failed files: {len(run_state['source_cleanup']['failed_files'])}",
        Severity.INFO,
        "source",
        "archive",
        "cleanup",
    )

    return mark_success(
        run_state,
        script="workflow_source_cleanup.py",
        step="archive_source_files",
        function_name="archive_successful_loose_source_files",
        message="Source cleanup archive stage complete.",
    )