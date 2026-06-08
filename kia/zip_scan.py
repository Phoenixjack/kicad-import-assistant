import tempfile
import zipfile
from pathlib import Path


def extract_zip_to_temp(zip_path: Path) -> Path:
    """
    Extract the selected ZIP file to a temporary folder.

    The temp folder is not automatically deleted yet so the user can inspect it
    if needed. Later, cleanup behavior can be added.
    """
    temp_root = Path(tempfile.mkdtemp(prefix="kicad_import_"))

    print()
    print("Extracting ZIP:")
    print(f"  Source: {zip_path}")
    print(f"  Temp:   {temp_root}")

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
    print()
    print("Detected files:")

    categories = [
        ("Footprints", "footprints"),
        ("Symbols", "symbols"),
        ("3D models", "models"),
        ("Other files", "other"),
    ]

    for label, key in categories:
        files = found_files.get(key, [])
        print()
        print(f"{label}: {len(files)}")

        if not files:
            continue

        for file_path in files:
            relative_path = file_path.relative_to(extract_root)
            print(f"  - {relative_path}")