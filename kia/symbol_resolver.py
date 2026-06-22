from pathlib import Path

from kia.debug import debug_print


def resolve_target_symbol_file(
    target_footprint_dir: Path,
    library_settings: dict,
) -> tuple[Path | None, str]:
    """
    Resolve the target .kicad_sym file for the selected library.

    Resolution order:
    1. Use configured symbol_file if it exists.
    2. If configured file does not exist, scan the target .pretty folder.
    3. If exactly one .kicad_sym file is found, use it.
    4. If none or multiple are found, return the configured path or None with a status message.

    Returns:
        (resolved_path, resolution_status)
    """
    configured_symbol_file = library_settings.get("symbol_file", "").strip()

    debug_print("symbols", f"Configured symbol_file: {configured_symbol_file}")
    debug_print("symbols", f"Target footprint dir: {target_footprint_dir}")

    if not target_footprint_dir.exists() or not target_footprint_dir.is_dir():
        debug_print("symbols", "Target footprint directory does not exist or is not a directory.")

        if configured_symbol_file:
            return (
                target_footprint_dir / configured_symbol_file,
                "configured symbol file path shown, but target folder does not exist",
            )

        return (
            None,
            "no symbol file resolved because target folder does not exist",
        )

    if configured_symbol_file:
        configured_path = target_footprint_dir / configured_symbol_file

        if configured_path.exists():
            debug_print("symbols", f"Using configured symbol file: {configured_path}")
            return (
                configured_path,
                "configured symbol file exists",
            )

        debug_print("symbols", f"Configured symbol file does not exist: {configured_path}")
    else:
        configured_path = None
        debug_print("symbols", "No configured symbol_file value found.")

    all_symbol_matches = sorted(target_footprint_dir.glob("*.kicad_sym"))

    symbol_matches = [
        path for path in all_symbol_matches
        if not is_symbol_backup_file(path)
    ]

    debug_print("symbols", f"All symbol file matches found: {[path.name for path in all_symbol_matches]}")
    debug_print("symbols", f"Active symbol file matches after backup filter: {[path.name for path in symbol_matches]}")

    folder_stem = target_footprint_dir.stem
    preferred_symbol_name = f"{folder_stem}.kicad_sym"

    folder_name_matches = [
        path for path in symbol_matches
        if path.name.lower() == preferred_symbol_name.lower()
    ]

    if len(folder_name_matches) == 1:
        return (
            folder_name_matches[0],
            "auto-detected symbol file matching target folder name",
        )

    if len(symbol_matches) == 1:
        return (
            symbol_matches[0],
            "auto-detected one symbol file in target folder",
        )

    if len(symbol_matches) == 0:
        if configured_path is not None:
            return (
                configured_path,
                "configured symbol file does not exist and no .kicad_sym files were found",
            )

        return (
            None,
            "no configured symbol file and no .kicad_sym files were found",
        )

    if configured_path is not None:
        return (
            configured_path,
            "multiple .kicad_sym files found; keeping configured symbol file path",
        )

    return (
        None,
        "multiple .kicad_sym files found and no configured symbol file was provided",
    )


def is_symbol_backup_file(path: Path) -> bool:
    """
    Return True if a .kicad_sym-looking file should be treated as a backup.

    Handles older backup naming styles such as:
      _testlibrary.20260609_193642.backup.kicad_sym

    and manual backup names containing backup/bak/copy.
    """
    name_lower = path.name.lower()

    backup_markers = [
        ".backup.",
        ".backup",
        "_backup",
        "-backup",
        ".bak.",
        ".bak",
        "_bak",
        "-bak",
        " copy",
        "_copy",
        "-copy",
    ]

    return any(marker in name_lower for marker in backup_markers)

