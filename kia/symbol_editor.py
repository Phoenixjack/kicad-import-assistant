import re
from pathlib import Path

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
    Update the first symbol name in a KiCad .kicad_sym file.

    Returns:
        updated_text
        success flag
        old symbol name
    """
    old_symbol_name = detect_first_symbol_name(symbol_text)

    if not old_symbol_name:
        return symbol_text, False, ""

    updated_text, replacement_count = re.subn(
        pattern=r'(\(symbol\s+)"[^"]+"',
        repl=rf'\1"{new_symbol_name}"',
        string=symbol_text,
        count=1,
    )

    return updated_text, replacement_count == 1, old_symbol_name


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