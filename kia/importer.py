import re
import shutil
import uuid
from pathlib import Path


def confirm_import() -> bool:
    """
    Require a hard confirmation before modifying library files.

    This avoids accidental Enter/Y imports.
    """
    print()
    print("WRITE CONFIRMATION REQUIRED")
    print("This will copy renamed footprint/model files into the target library folder.")
    print("It will update the copied footprint internal name and 3D model path.")
    print("It will NOT merge symbols yet.")
    print()
    confirmation = input("Type IMPORT to continue, or anything else to cancel: ").strip()

    return confirmation == "IMPORT"


def ensure_target_folder_exists(target_folder: Path) -> None:
    """
    Ensure the target footprint/model folder exists.

    V0.6 does not auto-create missing folders. The user should create/select
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
        print(f"Version {APP_VERSION} refuses to overwrite existing files.")
        raise SystemExit


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


def build_kicad_model_path(
    config: dict,
    library_settings: dict,
    basename: str,
) -> str:
    """
    Build the KiCad 3D model path for the copied STEP model.

    Example:
    ${CHRIS_KICAD_LIB}/CONNECTORS.pretty/CONN_EXAMPLE.step
    """
    path_variable = config.get("path_variable", "CHRIS_KICAD_LIB")
    footprint_dir_name = library_settings.get("footprint_dir", "")

    return f"${{{path_variable}}}/{footprint_dir_name}/{basename}.step"


def update_footprint_internal_name(
    footprint_path: Path,
    basename: str,
) -> None:
    """
    Update the copied footprint's internal name.

    Supports both newer quoted KiCad syntax:
      (footprint "Old_Name"

    and older/unquoted vendor syntax:
      (footprint Old_Name
    """
    text = footprint_path.read_text(encoding="utf-8")

    # Quoted form
    updated_text, replacement_count = re.subn(
        pattern=r'^(\s*\(footprint\s+)"[^"]+"',
        repl=rf'\1"{basename}"',
        string=text,
        count=1,
        flags=re.MULTILINE,
    )

    # Older/unquoted form
    if replacement_count == 0:
        updated_text, replacement_count = re.subn(
            pattern=r'^(\s*\(footprint\s+)([^\s\)]+)',
            repl=rf'\1"{basename}"',
            string=text,
            count=1,
            flags=re.MULTILINE,
        )

    if replacement_count != 1:
        print()
        print("WARNING:")
        print("Could not confidently update footprint internal name.")
        print(f"  {footprint_path}")
        print("Expected to find one line like:")
        print('  (footprint "Old_Name"')
        print("or:")
        print("  (footprint Old_Name")
        return

    footprint_path.write_text(updated_text, encoding="utf-8")

    print()
    print("Updated footprint internal name:")
    print(f"  {footprint_path.name}")
    print(f"  Name: {basename}")


def build_default_model_block(model_path_in_kicad: str) -> str:
    """
    Build a default KiCad 3D model block.

    Default transform matches KiCad's typical neutral model placement.
    """
    return (
        f'\n\t(model "{model_path_in_kicad}"\n'
        "\t\t(offset\n"
        "\t\t\t(xyz 0 0 0)\n"
        "\t\t)\n"
        "\t\t(scale\n"
        "\t\t\t(xyz 1 1 1)\n"
        "\t\t)\n"
        "\t\t(rotate\n"
        "\t\t\t(xyz 0 0 0)\n"
        "\t\t)\n"
        "\t)\n"
    )


def update_footprint_model_path(
    footprint_path: Path,
    model_path_in_kicad: str,
) -> None:
    """
    Update the copied footprint's 3D model path.

    If a model block exists, update the first model path.
    If no model block exists, add a default model block before the footprint's
    final closing parenthesis.
    """
    text = footprint_path.read_text(encoding="utf-8")

    updated_text, replacement_count = re.subn(
        pattern=r'\(model\s+"[^"]+"',
        repl=f'(model "{model_path_in_kicad}"',
        string=text,
        count=1,
    )

    if replacement_count > 0:
        footprint_path.write_text(updated_text, encoding="utf-8")

        print()
        print("Updated footprint 3D model path:")
        print(f"  {footprint_path.name}")
        print(f"  Model: {model_path_in_kicad}")
        return

    model_block = build_default_model_block(model_path_in_kicad)

    stripped_text = text.rstrip()

    if not stripped_text.endswith(")"):
        print()
        print("WARNING:")
        print("Could not add 3D model block because footprint does not end with ')'.")
        print(f"  {footprint_path}")
        return

    # Insert model block before final closing parenthesis of the footprint.
    updated_text = stripped_text[:-1] + model_block + ")\n"

    footprint_path.write_text(updated_text, encoding="utf-8")

    print()
    print("Added footprint 3D model block:")
    print(f"  {footprint_path.name}")
    print(f"  Model: {model_path_in_kicad}")


def copy_selected_import_files(
    selected_files: dict,
    library_root: Path,
    library_settings: dict,
    config: dict,
    basename: str,
    app_version: str,
) -> list[dict]:
    """
    Copy selected footprint/model files to the target library folder.

    V0.6 behavior:
    - Copy footprint as <basename>.kicad_mod
    - Copy model as <basename>.step
    - Update copied footprint internal name
    - Update copied footprint 3D model path if a model file was selected
    - Do not merge symbols
    """
    footprint_dir_name = library_settings.get("footprint_dir", "")
    target_folder = library_root / footprint_dir_name

    ensure_target_folder_exists(target_folder)

    copied_files = []

    footprint_path = selected_files.get("footprint")
    model_path = selected_files.get("model")

    target_footprint = None
    target_model = None

    if footprint_path:
        target_footprint = target_folder / f"{basename}.kicad_mod"
        check_target_file_available(target_footprint)

    if model_path:
        target_model = target_folder / f"{basename}.step"
        check_target_file_available(target_model)

    if footprint_path and target_footprint:
        shutil.copy2(footprint_path, target_footprint)

        copied_files.append({
            "type": "footprint",
            "source": footprint_path,
            "target": target_footprint,
        })

    if model_path and target_model:
        shutil.copy2(model_path, target_model)

        copied_files.append({
            "type": "model",
            "source": model_path,
            "target": target_model,
        })

    if target_footprint:
        update_footprint_internal_name(
            footprint_path=target_footprint,
            basename=basename,
        )

        if target_model:
            model_path_in_kicad = build_kicad_model_path(
                config=config,
                library_settings=library_settings,
                basename=basename,
            )

            update_footprint_model_path(
                footprint_path=target_footprint,
                model_path_in_kicad=model_path_in_kicad,
            )

            add_import_metadata_properties(
                footprint_path=target_footprint,
                importer_version=f"V{app_version}",
            )

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


def build_hidden_footprint_property_block(
    property_name: str,
    property_value: str,
) -> str:
    """
    Build a hidden KiCad footprint property block.

    The property is hidden and placed at 0,0 on F.SilkS.
    A unique UUID is generated for each property.
    """
    property_uuid = uuid.uuid4()

    return (
        f'\n\t(property "{property_name}" "{property_value}"\n'
        "\t\t(at 0 0 0)\n"
        '\t\t(layer "F.SilkS")\n'
        "\t\t(hide yes)\n"
        f'\t\t(uuid "{property_uuid}")\n'
        "\t\t(effects\n"
        "\t\t\t(font\n"
        "\t\t\t\t(size 1 1)\n"
        "\t\t\t\t(thickness 0.1)\n"
        "\t\t\t)\n"
        "\t\t)\n"
        "\t)\n"
    )


def add_import_metadata_properties(
    footprint_path: Path,
    importer_version: str,
) -> None:
    """
    Add hidden import/review metadata properties to the copied footprint.

    These properties make imported footprints searchable and clearly mark
    validation work that still needs to be performed.
    """
    text = footprint_path.read_text(encoding="utf-8")

    properties_to_add = {
        "ImportedBy": f"kicad-import-assistant {importer_version}",
        "ImportStatus": "NEEDS_REVIEW",
        "Needs3DModelValidation": "YES",
    }

    blocks_to_add = []

    for property_name, property_value in properties_to_add.items():
        if f'(property "{property_name}" ' in text:
            continue

        blocks_to_add.append(
            build_hidden_footprint_property_block(
                property_name=property_name,
                property_value=property_value,
            )
        )

    if not blocks_to_add:
        print()
        print("Import metadata properties already present:")
        print(f"  {footprint_path.name}")
        return

    stripped_text = text.rstrip()

    if not stripped_text.endswith(")"):
        print()
        print("WARNING:")
        print("Could not add import metadata properties because footprint does not end with ')'.")
        print(f"  {footprint_path}")
        return

    metadata_block = "".join(blocks_to_add)

    # Insert metadata before the final closing parenthesis of the footprint.
    updated_text = stripped_text[:-1] + metadata_block + ")\n"

    footprint_path.write_text(updated_text, encoding="utf-8")

    print()
    print("Added import metadata properties:")
    print(f"  {footprint_path.name}")
    for property_name, property_value in properties_to_add.items():
        print(f"  {property_name}: {property_value}")

