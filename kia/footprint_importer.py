import re
import shutil
import uuid
from pathlib import Path
from kia.debug import (
    dbg_blank,
    dbg_print, 
    Severity, 
)


def confirm_import() -> bool:
    """
    Require a hard confirmation before modifying library files.

    This avoids accidental Enter/Y imports.
    """
    dbg_blank(Severity.VERBOSE, "importer", "confirm", "import")
    dbg_print("WRITE CONFIRMATION REQUIRED", Severity.VERBOSE, "importer", "confirm", "import")
    dbg_print("This will copy renamed footprint/model files into the target library folder.", Severity.VERBOSE, "importer", "confirm", "import")
    dbg_print("It will update the copied footprint internal name and 3D model path.", Severity.VERBOSE, "importer", "confirm", "import")
    dbg_print("It will NOT merge symbols yet.", Severity.VERBOSE, "importer", "confirm", "import")
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
        print("Overwrite protection is enabled; existing files will not be replaced.")
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
    model_filename: str | None = None,
) -> str:
    """
    Build the KiCad 3D model path for the copied model.

    Example:
    ${CHRIS_KICAD_LIB}/CONNECTORS.pretty/CONN_EXAMPLE.step

    If model_filename is provided, use the actual copied model filename.
    This preserves source extensions such as .step, .stp, or .wrl.
    """
    path_variable = config.get("path_variable", "CHRIS_KICAD_LIB")
    footprint_dir_name = library_settings.get("footprint_dir", "")

    if not model_filename:
        model_filename = f"{basename}.step"

    return f"${{{path_variable}}}/{footprint_dir_name}/{model_filename}"


def update_footprint_value_property(
    footprint_path: Path,
    basename: str,
) -> bool:
    """
    Update the copied footprint's visible Value field.

    Supports both newer KiCad property syntax:
      (property "Value" "Old_Value"

    and older/vendor footprint text syntax:
      (fp_text value "Old_Value"
    """
    text = footprint_path.read_text(encoding="utf-8")

    # Newer KiCad property syntax.
    updated_text, replacement_count = re.subn(
        pattern=r'(\(property\s+"Value"\s+)"[^"]+"',
        repl=rf'\1"{basename}"',
        string=text,
        count=1,
    )

    if replacement_count == 1:
        footprint_path.write_text(updated_text, encoding="utf-8")

        dbg_blank(Severity.VERBOSE, "importer", "footprint_value", "footprint_importer")
        dbg_print("Updated footprint Value property:", Severity.VERBOSE, "importer", "footprint_value", "footprint_importer")
        dbg_print(f"Footprint: {footprint_path.name}", Severity.VERBOSE, "importer", "footprint_value", "footprint_importer")
        dbg_print(f"Value: {basename}", Severity.VERBOSE, "importer", "footprint_value", "footprint_importer")

        return True

    # Older/vendor footprint text syntax.
    # Supports both:
    #   (fp_text value "Old_Value"
    #   (fp_text value Old_Value
    updated_text, replacement_count = re.subn(
        pattern=r'(\(fp_text\s+value\s+)("[^"]+"|[^\s\)]+)',
        repl=rf'\1"{basename}"',
        string=text,
        count=1,
    )

    if replacement_count == 1:
        footprint_path.write_text(updated_text, encoding="utf-8")

        dbg_blank(Severity.VERBOSE, "importer", "footprint_value", "footprint_importer")
        dbg_print("Updated footprint fp_text value:", Severity.VERBOSE, "importer", "footprint_value", "footprint_importer")
        dbg_print(f"Footprint: {footprint_path.name}", Severity.VERBOSE, "importer", "footprint_value", "footprint_importer")
        dbg_print(f"Value: {basename}", Severity.VERBOSE, "importer", "footprint_value", "footprint_importer")

        return True

    print()
    print("WARNING:")
    print("Could not confidently update footprint Value field.")
    print(f"  {footprint_path}")
    print('Expected either (property "Value" "Old_Value" or (fp_text value "Old_Value"')
    return False


def update_footprint_internal_name(
    footprint_path: Path,
    basename: str,
) -> bool:
    """
    Update the copied footprint's internal name.

    Supports newer KiCad syntax:
      (footprint "Old_Name"
      (footprint Old_Name

    Supports older KiCad/vendor syntax:
      (module "Old_Name"
      (module Old_Name
    """
    text = footprint_path.read_text(encoding="utf-8")

    patterns = [
        # Newer quoted footprint form:
        #   (footprint "Old_Name"
        r'^(\s*\(footprint\s+)"[^"]+"',

        # Newer unquoted footprint form:
        #   (footprint Old_Name
        r'^(\s*\(footprint\s+)([^\s\)]+)',

        # Older quoted module form:
        #   (module "Old_Name"
        r'^(\s*\(module\s+)"[^"]+"',

        # Older unquoted module form:
        #   (module Old_Name
        r'^(\s*\(module\s+)([^\s\)]+)',
    ]

    updated_text = text
    replacement_count = 0

    for pattern in patterns:
        updated_text, replacement_count = re.subn(
            pattern=pattern,
            repl=rf'\1"{basename}"',
            string=text,
            count=1,
            flags=re.MULTILINE,
        )

        if replacement_count == 1:
            break

    if replacement_count != 1:
        print()
        print("WARNING:")
        print("Could not confidently update footprint internal name.")
        print(f"  {footprint_path}")
        print("Expected to find one line like:")
        print('  (footprint "Old_Name"')
        print("or:")
        print("  (footprint Old_Name")
        print("or legacy KiCad/vendor syntax like:")
        print('  (module "Old_Name"')
        print("or:")
        print("  (module Old_Name")
        return False

    footprint_path.write_text(updated_text, encoding="utf-8")

    dbg_blank(Severity.VERBOSE, "importer", "fp_name", "footprint_importer")
    dbg_print("Updated footprint internal name:", Severity.VERBOSE, "importer", "fp_name", "footprint_importer")
    dbg_print(f"Footprint: {footprint_path.name}", Severity.VERBOSE, "importer", "fp_name", "footprint_importer")
    dbg_print(f"Name: {basename}", Severity.VERBOSE, "importer", "fp_name", "footprint_importer")

    return True


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
) -> str:
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

        dbg_blank(Severity.VERBOSE, "importer", "model_path", "footprint_importer")
        dbg_print("Updated footprint 3D model path:", Severity.VERBOSE, "importer", "model_path", "footprint_importer")
        dbg_print(f"Footprint: {footprint_path.name}", Severity.VERBOSE, "importer", "model_path", "footprint_importer")
        dbg_print(f"Model: {model_path_in_kicad}", Severity.VERBOSE, "importer", "model_path", "footprint_importer")
        return "updated"

    model_block = build_default_model_block(model_path_in_kicad)

    stripped_text = text.rstrip()

    if not stripped_text.endswith(")"):
        print()
        print("WARNING:")
        print("Could not add 3D model block because footprint does not end with ')'.")
        print(f"  {footprint_path}")
        return "failed"

    # Insert model block before final closing parenthesis of the footprint.
    updated_text = stripped_text[:-1] + model_block + ")\n"

    footprint_path.write_text(updated_text, encoding="utf-8")

    dbg_blank(Severity.VERBOSE, "importer", "model_path", "footprint_importer")
    dbg_print("Added footprint 3D model block:", Severity.VERBOSE, "importer", "model_path", "footprint_importer")
    dbg_print(f"Footprint: {footprint_path.name}", Severity.VERBOSE, "importer", "model_path", "footprint_importer")
    dbg_print(f"Model: {model_path_in_kicad}", Severity.VERBOSE, "importer", "model_path", "footprint_importer")
    
    return "added"


def copy_selected_import_files(
    selected_files: dict,
    library_root: Path,
    library_settings: dict,
    config: dict,
    basename: str,
    app_version: str,
) -> dict:
    """
    Copy selected footprint/model files to the target library folder.

    V0.7 behavior:
    - Copy footprint as <basename>.kicad_mod
    - Copy model as <basename>.step
    - Update copied footprint internal name
    - Update copied footprint 3D model path if a model file was selected
    - Do not merge symbols
    - Return detailed status
    """
    
    result = {
        "confirmed": True,
        "files_copied": False,
        "copied_files": [],
        "footprint_name_updated": False,
        "footprint_value_updated": False,
        "model_reference_updated": False,
        "model_reference_added": False,
        "metadata_added": False,
    }
    
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
        result["footprint_name_updated"] = update_footprint_internal_name(
            footprint_path=target_footprint,
            basename=basename,
        )

        result["footprint_value_updated"] = update_footprint_value_property(
            footprint_path=target_footprint,
            basename=basename,
        )
        
        if target_model:
            model_path_in_kicad = build_kicad_model_path(
                config=config,
                library_settings=library_settings,
                basename=basename,
            )

            model_result = update_footprint_model_path(
                footprint_path=target_footprint,
                model_path_in_kicad=model_path_in_kicad,
            )

            result["model_reference_updated"] = model_result == "updated"
            result["model_reference_added"] = model_result == "added"

            result["metadata_added"] = add_import_metadata_properties(
                footprint_path=target_footprint,
                importer_version=f"V{app_version}",
            )

    dbg_blank(Severity.VERBOSE, "importer", "copy", "footprint_importer")
    dbg_print("Copied files:", Severity.VERBOSE, "importer", "copy", "footprint_importer")

    if not copied_files:
        dbg_print("No footprint/model files were copied.", Severity.VERBOSE, "importer", "copy", "footprint_importer")
    else:
        for row in copied_files:
            dbg_print(f"{row['type']}:", Severity.VERBOSE, "importer", "copy", "footprint_importer")
            dbg_print(f"Source: {row['source']}", Severity.VERBOSE, "importer", "copy", "footprint_importer")
            dbg_print(f"Target: {row['target']}", Severity.VERBOSE, "importer", "copy", "footprint_importer")

    result["copied_files"] = copied_files
    result["files_copied"] = len(copied_files) > 0

    return result


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
        "\t\t\t\t(thickness 0.08)\n"
        "\t\t\t)\n"
        "\t\t)\n"
        "\t)\n"
    )


def add_import_metadata_properties(
    footprint_path: Path,
    importer_version: str,
) -> bool:
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
        return True

    stripped_text = text.rstrip()

    if not stripped_text.endswith(")"):
        print()
        print("WARNING:")
        print("Could not add import metadata properties because footprint does not end with ')'.")
        print(f"  {footprint_path}")
        return False

    metadata_block = "".join(blocks_to_add)

    # Insert metadata before the final closing parenthesis of the footprint.
    updated_text = stripped_text[:-1] + metadata_block + ")\n"

    footprint_path.write_text(updated_text, encoding="utf-8")

    dbg_blank(Severity.VERBOSE, "importer", "metadata", "footprint_importer")
    dbg_print("Added import metadata properties:", Severity.VERBOSE, "importer", "metadata", "footprint_importer")
    dbg_print(f"Footprint: {footprint_path.name}", Severity.VERBOSE, "importer", "metadata", "footprint_importer")

    for property_name, property_value in properties_to_add.items():
        dbg_print(
            f"{property_name}: {property_value}",
            Severity.VERBOSE,
            "importer",
            "metadata",
            "footprint_importer",
        )
    
    return True