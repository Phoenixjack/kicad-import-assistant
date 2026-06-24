import tempfile
import shutil
import zipfile
from pathlib import Path
from kia.debug import (
    dbg_blank,
    dbg_print, 
    Severity, 
)

def extract_zip_to_temp(zip_path: Path) -> Path:
    """
    Extract the selected ZIP file to a temporary folder.

    The temp folder is not automatically deleted yet so the user can inspect it
    if needed. Later, cleanup behavior can be added.
    """
    temp_root = Path(tempfile.mkdtemp(prefix="kicad_import_"))

    dbg_blank(Severity.VERBOSE, "source", stage="scan", source="extract")
    dbg_print(f"Extracting ZIP: {zip_path}", Severity.INFO, "source", stage="scan", source="extract")
    dbg_print(f"Temporary extract folder: {temp_root}", Severity.INFO, "source", stage="scan", source="extract")

    try:
        with zipfile.ZipFile(zip_path, "r") as zip_file:
            zip_file.extractall(temp_root)
    except zipfile.BadZipFile:
        print("ERROR: Selected file is not a valid ZIP archive.")
        raise SystemExit

    return temp_root


def find_import_files(extract_root: Path) -> dict:
    """
    Recursively find KiCad-relevant files inside the extracted ZIP folder.
    """
    found_files = {
        "footprints": [],
        "symbols": [],
        "models": [],
        "other": [],
    }

    for path in extract_root.rglob("*"):
        if not path.is_file():
            continue

        suffix = path.suffix.lower()

        if suffix == ".kicad_mod":
            found_files["footprints"].append(path)
        elif suffix == ".kicad_sym":
            found_files["symbols"].append(path)
        elif suffix in [".step", ".stp"]:
            found_files["models"].append(path)
        else:
            found_files["other"].append(path)

    return found_files


def print_import_file_summary(found_files: dict, extract_root: Path) -> None:
    """
    Print a readable summary of detected files.
    """
    dbg_blank(Severity.VERBOSE, "source", stage="scan", source="summary")
    dbg_print("Detected files:", Severity.INFO, "source", stage="scan", source="summary")

    categories = [
        ("Footprints", "footprints"),
        ("Symbols", "symbols"),
        ("3D models", "models"),
        ("Other files", "other"),
    ]

    for label, key in categories:
        files = found_files.get(key, [])
        dbg_blank(Severity.VERBOSE, "source", stage="scan", source="summary")
        dbg_print(f"{label}: {len(files)}", Severity.INFO, "source", stage="scan", source="summary")

        if not files:
            continue

        for file_path in files:
            relative_path = file_path.relative_to(extract_root)
            dbg_print(f"  - {relative_path}", Severity.INFO, "source", stage="scan", source="summary")


def cleanup_temp_folder(temp_folder: Path | None, keep_temp_files: bool) -> bool:
    """
    Delete the temporary import folder unless keep_temp_files is enabled.

    Returns True if cleanup was performed.
    Returns False if cleanup was skipped or could not be performed.
    """
    if keep_temp_files:
        return False

    if temp_folder is None:
        return False

    if not temp_folder.exists():
        return False

    temp_folder_name = temp_folder.name.lower()

    if not temp_folder_name.startswith("kicad_import_"):
        print()
        print("WARNING:")
        print("Refusing to delete temp folder because it does not look like one of ours:")
        print(f"  {temp_folder}")
        return False

    shutil.rmtree(temp_folder)
    return True