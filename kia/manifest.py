import csv
from pathlib import Path


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


def create_preview_manifest(
    found_files: dict,
    extract_root: Path,
    library_root: Path,
    library_settings: dict,
    basename: str,
) -> Path:
    """
    Create a preview manifest CSV.

    This does not modify the KiCad library.
    It only records what would happen in a future import step.
    """
    footprint_dir_name = library_settings.get("footprint_dir", "")
    symbol_file_name = library_settings.get("symbol_file", "")
    nickname = library_settings.get("nickname", "")

    target_footprint_dir = library_root / footprint_dir_name
    target_symbol_file = target_footprint_dir / symbol_file_name

    selected_footprint = choose_single_file(found_files.get("footprints", []), "footprint")
    selected_symbol = choose_single_file(found_files.get("symbols", []), "symbol")
    selected_model = choose_single_file(found_files.get("models", []), "3D model")

    manifest_rows = []

    if selected_footprint:
        manifest_rows.append({
            "type": "footprint",
            "source_file": str(selected_footprint.relative_to(extract_root)),
            "target_file": str(target_footprint_dir / f"{basename}.kicad_mod"),
            "action": "COPY_RENAME_PENDING",
            "notes": "Future step: update internal footprint name and 3D model path",
        })

    if selected_model:
        manifest_rows.append({
            "type": "model",
            "source_file": str(selected_model.relative_to(extract_root)),
            "target_file": str(target_footprint_dir / f"{basename}.step"),
            "action": "COPY_RENAME_PENDING",
            "notes": "Future step: normalize .stp/.STEP/.STP to .step",
        })

    if selected_symbol:
        manifest_rows.append({
            "type": "symbol",
            "source_file": str(selected_symbol.relative_to(extract_root)),
            "target_file": str(target_symbol_file),
            "action": "MERGE_PENDING",
            "notes": f"Future step: update symbol name and Footprint property to {nickname}:{basename}",
        })

    if not manifest_rows:
        print()
        print("ERROR: No footprint, symbol, or model files were selected for manifest.")
        raise SystemExit

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