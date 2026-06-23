import csv
from pathlib import Path
from kia.debug import debug_print


def choose_single_file(files: list[Path], file_type_label: str) -> Path | None:
    """
    Choose a single file from a list.

    If no files exist, return None.
    If one file exists, return it.
    If multiple files exist, prompt the user to choose one.
    """
    if not files:
        return None

    if len(files) == 1:
        return files[0]

    print()
    print(f"Multiple {file_type_label} files found:")
    for index, file_path in enumerate(files, start=1):
        print(f"  {index}. {file_path.name}")

    while True:
        choice = input(f"Choose {file_type_label} file number, or leave blank to skip: ").strip()

        if not choice:
            return None

        try:
            choice_number = int(choice)
        except ValueError:
            print("Enter a number.")
            continue

        if 1 <= choice_number <= len(files):
            return files[choice_number - 1]

        print("Choice out of range.")


def select_import_files(found_files: dict) -> dict:
    """
    Select one footprint, one symbol, and one 3D model from detected files.

    If only one file exists in a category, it is selected automatically.
    """
    selected_files = {
        "footprint": choose_single_file(found_files.get("footprints", []), "footprint"),
        "symbol": choose_single_file(found_files.get("symbols", []), "symbol"),
        "model": choose_single_file(found_files.get("models", []), "3D model"),
    }

    if not any(selected_files.values()):
        print()
        print("ERROR: No footprint, symbol, or model files were selected.")
        raise SystemExit

    return selected_files


def create_preview_manifest(
    selected_files: dict,
    extract_root: Path,
    library_root: Path,
    library_settings: dict,
    basename: str,
    target_symbol_file: Path | None = None,
) -> Path:
    """
    Create a preview manifest CSV.

    This does not modify the KiCad library.
    It only records what would happen in an import step.
    """
    footprint_dir_name = library_settings.get("footprint_dir", "")
    symbol_file_name = library_settings.get("symbol_file", "")
    nickname = library_settings.get("nickname", "")

    target_footprint_dir = library_root / footprint_dir_name
    
    if target_symbol_file is not None:
        symbol_target = target_symbol_file
    else:
        footprint_dir_name = library_settings.get("footprint_dir", "")
        symbol_file_name = library_settings.get("symbol_file", "")
        symbol_target = library_root / footprint_dir_name / symbol_file_name
    
    selected_footprint = selected_files.get("footprint")
    selected_symbol = selected_files.get("symbol")
    selected_model = selected_files.get("model")

    manifest_rows = []

    if selected_footprint:
        manifest_rows.append({
            "type": "footprint",
            "source_file": str(selected_footprint.relative_to(extract_root)),
            "target_file": str(target_footprint_dir / f"{basename}.kicad_mod"),
            "action": "COPY_RENAME_PENDING",
            "notes": "Footprint will be copied/renamed; internal name, Value property, 3D model path, and metadata will be updated during import execution.",
        })

    if selected_model:
        manifest_rows.append({
            "type": "model",
            "source_file": str(selected_model.relative_to(extract_root)),
            "target_file": str(target_footprint_dir / f"{basename}.step"),
            "action": "COPY_RENAME_PENDING",
            "notes": "Model will be copied/renamed and referenced by the copied footprint when a footprint is imported.",
        })

    if selected_symbol:
        manifest_rows.append({
            "type": "symbol",
            "source_file": str(selected_symbol.relative_to(extract_root)),
            "target_file": str(target_symbol_file),
            "action": "MERGE_PENDING",
            "notes": f"Symbol will be merged into the target library and its Footprint property will be updated to {library_settings.get('nickname')}:{basename}.",
        })

    manifest_path = extract_root / "kicad_import_preview_manifest.csv"

    with manifest_path.open("w", newline="", encoding="utf-8") as csv_file:
        fieldnames = ["type", "source_file", "target_file", "action", "notes"]
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(manifest_rows)

    print()
    print("Preview manifest:")
    for row in manifest_rows:
        print(f"  {row['type']}:")
        print(f"    Source: {row['source_file']}")
        print(f"    Target: {row['target_file']}")
        print(f"    Action: {row['action']}")
        print(f"    Notes:  {row['notes']}")

    print()
    print("Manifest written:")
    print(f"  {manifest_path}")

    return manifest_path