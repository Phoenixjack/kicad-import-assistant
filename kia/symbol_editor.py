import re
from pathlib import Path
import shutil
from datetime import datetime
from kia.debug import debug_print


def detect_first_symbol_name(symbol_text: str) -> str:
    """
    Detect the first symbol name in a KiCad .kicad_sym file.

    Expected form:
      (symbol "OldSymbolName"
    """
    match = re.search(
        pattern=r'\(symbol\s+"([^"]+)"',
        string=symbol_text,
    )

    if not match:
        return ""

    return match.group(1)


def update_symbol_name(
    symbol_text: str,
    new_symbol_name: str,
) -> tuple[str, bool, str]:
    """
    Update the parent symbol name and any nested symbol unit names.

    KiCad symbol libraries may contain nested unit symbols such as:
      (symbol "OLD_0_0"

    If the parent symbol is renamed, those nested unit names must also use
    the new parent symbol name as their prefix.
    """
    old_symbol_name = detect_first_symbol_name(symbol_text)

    if not old_symbol_name:
        return symbol_text, False, ""

    # Replace:
    #   (symbol "OLD"
    #   (symbol "OLD_0_0"
    #
    # With:
    #   (symbol "NEW"
    #   (symbol "NEW_0_0"
    pattern = rf'(\(symbol\s+")({re.escape(old_symbol_name)})(?=("|_))'

    updated_text, replacement_count = re.subn(
        pattern=pattern,
        repl=rf'\1{new_symbol_name}',
        string=symbol_text,
    )

    return updated_text, replacement_count > 0, old_symbol_name


def update_symbol_footprint_property(
    symbol_text: str,
    footprint_value: str,
) -> tuple[str, bool]:
    """
    Update the first Footprint property in a KiCad symbol.

    Expected form:
      (property "Footprint" "old:value"

    If no Footprint property exists, this first version does not add one.
    """
    updated_text, replacement_count = re.subn(
        pattern=r'(\(property\s+"Footprint"\s+)"[^"]*"',
        repl=rf'\1"{footprint_value}"',
        string=symbol_text,
        count=1,
    )

    return updated_text, replacement_count == 1


def create_symbol_preview_file(
    selected_files: dict,
    library_settings: dict,
    basename: str,
    extract_root: Path,
) -> dict:
    """
    Create an edited preview copy of the source symbol file.

    This does not modify the target symbol library.
    """
    result = {
        "symbol_preview_created": False,
        "source_symbol": None,
        "preview_symbol": None,
        "old_symbol_name": "",
        "new_symbol_name": basename,
        "footprint_property": "",
        "symbol_name_updated": False,
        "footprint_property_updated": False,
    }

    source_symbol_path = selected_files.get("symbol")

    if not source_symbol_path:
        debug_print("symbols", "No source symbol selected; skipping symbol preview.")
        return result

    source_symbol_path = Path(source_symbol_path)

    if not source_symbol_path.exists():
        print()
        print("WARNING:")
        print("Selected source symbol file does not exist:")
        print(f"  {source_symbol_path}")
        return result

    nickname = library_settings.get("nickname", "")
    footprint_property = f"{nickname}:{basename}"

    result["source_symbol"] = source_symbol_path
    result["footprint_property"] = footprint_property

    symbol_text = source_symbol_path.read_text(encoding="utf-8")

    updated_text, name_updated, old_symbol_name = update_symbol_name(
        symbol_text=symbol_text,
        new_symbol_name=basename,
    )

    updated_text, footprint_updated = update_symbol_footprint_property(
        symbol_text=updated_text,
        footprint_value=footprint_property,
    )

    preview_symbol_path = extract_root / f"{basename}.symbol_preview.kicad_sym"
    preview_symbol_path.write_text(updated_text, encoding="utf-8")

    result["symbol_preview_created"] = True
    result["preview_symbol"] = preview_symbol_path
    result["old_symbol_name"] = old_symbol_name
    result["symbol_name_updated"] = name_updated
    result["footprint_property_updated"] = footprint_updated

    debug_print("symbols", "")
    debug_print("symbols", "Created symbol preview file:")
    debug_print("symbols", f"  Source: {source_symbol_path}")
    debug_print("symbols", f"  Preview: {preview_symbol_path}")
    debug_print("symbols", f"  Old symbol name: {old_symbol_name}")
    debug_print("symbols", f"  New symbol name: {basename}")
    debug_print("symbols", f"  Footprint property: {footprint_property}")
    debug_print("symbols", f"  Symbol name updated: {name_updated}")
    debug_print("symbols", f"  Footprint property updated: {footprint_updated}")

    return result


def target_symbol_exists(
    target_symbol_text: str,
    symbol_name: str,
) -> bool:
    """
    Return True if the target symbol library already contains symbol_name.

    Looks for:
      (symbol "symbol_name"
    """
    pattern = rf'\(symbol\s+"{re.escape(symbol_name)}"'
    return re.search(pattern, target_symbol_text) is not None


def build_symbol_backup_path(
    target_symbol_file: Path,
) -> Path:
    """
    Build a timestamped backup path for a target .kicad_sym file.

    Example:
      _testlibrary.kicad_sym
      _testlibrary.kicad_sym.20260609_231530.backup

    The backup intentionally does not end with .kicad_sym so normal symbol
    library scanning does not mistake it for an active KiCad symbol library.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    backup_name = f"{target_symbol_file.name}.{timestamp}.backup"

    return target_symbol_file.with_name(backup_name)


def create_symbol_library_backup(
    target_symbol_file: Path,
) -> Path | None:
    """
    Create a timestamped backup of the target symbol library.

    Returns the backup path if created.
    Returns None if the target symbol file does not exist.
    """
    if not target_symbol_file.exists():
        print()
        print("WARNING:")
        print("Cannot create symbol backup because target symbol file does not exist:")
        print(f"  {target_symbol_file}")
        return None

    backup_path = build_symbol_backup_path(target_symbol_file)

    shutil.copy2(target_symbol_file, backup_path)

    debug_print("symbols", "")
    debug_print("symbols", "Created symbol library backup:")
    debug_print("symbols", f"  Source: {target_symbol_file}")
    debug_print("symbols", f"  Backup: {backup_path}")

    return backup_path


def check_symbol_merge_preconditions(
    target_symbol_file: Path | None,
    new_symbol_name: str,
) -> dict:
    """
    Check whether a symbol merge would be safe to attempt.

    This does not modify the target symbol library.
    """
    result = {
        "target_symbol_file_exists": False,
        "target_symbol_already_exists": False,
        "symbol_merge_precheck_passed": False,
        "reason": "",
    }

    if target_symbol_file is None:
        result["reason"] = "No target symbol file resolved."
        return result

    target_symbol_file = Path(target_symbol_file)

    if not target_symbol_file.exists():
        result["reason"] = "Target symbol file does not exist."
        return result

    result["target_symbol_file_exists"] = True

    target_text = target_symbol_file.read_text(encoding="utf-8")

    if target_symbol_exists(
        target_symbol_text=target_text,
        symbol_name=new_symbol_name,
    ):
        result["target_symbol_already_exists"] = True
        result["reason"] = "Target symbol library already contains this symbol."
        return result

    result["symbol_merge_precheck_passed"] = True
    result["reason"] = "Symbol merge precheck passed."

    return result


def extract_first_symbol_block(symbol_text: str) -> tuple[str, bool]:
    """
    Extract the first complete top-level symbol block from a KiCad .kicad_sym file.

    Returns:
        symbol_block
        success flag
    """
    symbol_start = symbol_text.find('(symbol "')

    if symbol_start == -1:
        return "", False

    depth = 0
    in_string = False
    escape_next = False

    for index in range(symbol_start, len(symbol_text)):
        character = symbol_text[index]

        if escape_next:
            escape_next = False
            continue

        if character == "\\":
            escape_next = True
            continue

        if character == '"':
            in_string = not in_string
            continue

        if in_string:
            continue

        if character == "(":
            depth += 1

        elif character == ")":
            depth -= 1

            if depth == 0:
                symbol_block = symbol_text[symbol_start:index + 1]
                return symbol_block, True

    return "", False


def merge_symbol_preview_into_target(
    preview_symbol_file: Path,
    target_symbol_file: Path,
    new_symbol_name: str,
) -> dict:
    """
    Merge the edited preview symbol into the target .kicad_sym library.

    This assumes precheck and backup have already succeeded.
    """
    result = {
        "symbol_merged": False,
        "symbol_merge_reason": "",
        "merged_symbol_name": new_symbol_name,
    }

    if not preview_symbol_file.exists():
        result["symbol_merge_reason"] = "Preview symbol file does not exist."
        return result

    if not target_symbol_file.exists():
        result["symbol_merge_reason"] = "Target symbol file does not exist."
        return result

    preview_text = preview_symbol_file.read_text(encoding="utf-8")
    target_text = target_symbol_file.read_text(encoding="utf-8")

    if target_symbol_exists(
        target_symbol_text=target_text,
        symbol_name=new_symbol_name,
    ):
        result["symbol_merge_reason"] = "Target symbol library already contains this symbol."
        return result

    symbol_block, extracted = extract_first_symbol_block(preview_text)

    if not extracted:
        result["symbol_merge_reason"] = "Could not extract symbol block from preview file."
        return result

    stripped_target_text = target_text.rstrip()

    if not stripped_target_text.endswith(")"):
        result["symbol_merge_reason"] = "Target symbol library does not end with ')'."
        return result

    updated_target_text = (
        stripped_target_text[:-1]
        + "\n\n  "
        + symbol_block.replace("\n", "\n  ")
        + "\n)\n"
    )

    target_symbol_file.write_text(updated_target_text, encoding="utf-8")

    result["symbol_merged"] = True
    result["symbol_merge_reason"] = "Preview symbol merged into target symbol library."

    debug_print("symbols", "")
    debug_print("symbols", "Merged preview symbol into target library:")
    debug_print("symbols", f"  Preview: {preview_symbol_file}")
    debug_print("symbols", f"  Target: {target_symbol_file}")
    debug_print("symbols", f"  Symbol: {new_symbol_name}")

    return result



