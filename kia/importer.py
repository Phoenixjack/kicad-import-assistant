import shutil
from pathlib import Path


def confirm_import() -> bool:
    """
    Require a hard confirmation before modifying library files.

    This avoids accidental Enter/Y imports.
    """
    print()
    print("WRITE CONFIRMATION REQUIRED")
    print("This will copy renamed footprint/model files into the target library folder.")
    print("It will NOT edit footprint internals or merge symbols yet.")
    print()
    confirmation = input("Type IMPORT to continue, or anything else to cancel: ").strip()

    return confirmation == "IMPORT"


def ensure_target_folder_exists(target_folder: Path) -> None:
    """
    Ensure the target footprint/model folder exists.

    V0.5 does not auto-create missing folders. The user should create/select
    the target test library intentionally.
    """
    if not target_folder.exists():
        print()
        print("ERROR: Target folder does not exist:")
        print(f"  {target_folder}")
        print()
        print("Create the folder first or update the config.")
        raise SystemExit

    if not target_folder.is_dir():
        print()
        print("ERROR: Target path exists but is not a folder:")
        print(f"  {target_folder}")
        raise SystemExit


def check_target_file_available(target_path: Path) -> None:
    """
    Prevent accidental overwrite of existing target files.
    """
    if target_path.exists():
        print()
        print("ERROR: Target file already exists:")
        print(f"  {target_path}")
        print()
        print("V0.5 refuses to overwrite existing files.")
        raise SystemExit


def copy_selected_import_files(
    selected_files: dict,
    library_root: Path,
    library_settings: dict,
    basename: str,
) -> list[dict]:
    """
    Copy selected footprint/model files to the target library folder.

    V0.5 behavior:
    - Copy footprint as <basename>.kicad_mod
    - Copy model as <basename>.step
    - Do not edit file contents
    - Do not merge symbols
    """
    footprint_dir_name = library_settings.get("footprint_dir", "")
    target_folder = library_root / footprint_dir_name

    ensure_target_folder_exists(target_folder)

    copied_files = []

    footprint_path = selected_files.get("footprint")
    model_path = selected_files.get("model")

    if footprint_path:
        target_footprint = target_folder / f"{basename}.kicad_mod"
        check_target_file_available(target_footprint)

        shutil.copy2(footprint_path, target_footprint)

        copied_files.append({
            "type": "footprint",
            "source": footprint_path,
            "target": target_footprint,
        })

    if model_path:
        target_model = target_folder / f"{basename}.step"
        check_target_file_available(target_model)

        shutil.copy2(model_path, target_model)

        copied_files.append({
            "type": "model",
            "source": model_path,
            "target": target_model,
        })

    print()
    print("Copied files:")
    if not copied_files:
        print("  No footprint/model files were copied.")
    else:
        for row in copied_files:
            print(f"  {row['type']}:")
            print(f"    Source: {row['source']}")
            print(f"    Target: {row['target']}")

    return copied_files


def find_existing_files_by_mpn(
    library_root: Path,
    library_settings: dict,
    mpn: str,
) -> list[Path]:
    """
    Search the target footprint/model folder for existing files containing the MPN.
    """
    footprint_dir_name = library_settings.get("footprint_dir", "")
    target_folder = library_root / footprint_dir_name

    if not target_folder.exists() or not target_folder.is_dir():
        return []

    if not mpn.strip():
        return []

    search_pattern = f"*{mpn.strip()}*"

    return sorted(target_folder.glob(search_pattern))


def warn_about_existing_mpn_matches(matches: list[Path], mpn: str) -> None:
    """
    Print duplicate/previous-import warning for matching MPN files.
    """
    if not matches:
        return

    print()
    print("POSSIBLE DUPLICATE FOUND")
    print(f"Existing files matching MPN '{mpn}':")

    for match in matches:
        print(f"  - {match.name}")

    print()
    print("This may mean the part was already imported.")


def confirm_continue_after_duplicate_warning(matches: list[Path]) -> bool:
    """
    Ask whether to continue after possible duplicate matches.
    """
    if not matches:
        return True

    response = input("Continue anyway? [y/N]: ").strip().lower()
    return response in ["y", "yes"]