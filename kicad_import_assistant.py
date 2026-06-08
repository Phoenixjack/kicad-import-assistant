"""
KiCad Import Assistant

Purpose:
Import vendor ZIP files containing KiCad footprints and symbols
into a custom KiCad library structure.

Version 0.4 goals:
- Split into separate subscripts to improve readability
- Prompt for naming tokens
- Generate proposed basename
- Generate target filenames
- Write a preview manifest CSV
- Do not copy, rename, or edit library files yet

Future goals:
- Prompt user for naming tokens
- Rename/copy footprint files
- Update footprint internal name
- Update footprint 3D model name and path
- Merge symbols into target .kicad_sym file
- Update symbol Footprint property
- Add batch/manifest mode
"""

import tkinter as tk
from pathlib import Path

from kia.config import CONFIG_PATH, load_config, save_config
from kia.dialogs import select_zip_file, select_library_root
from kia.zip_scan import extract_zip_to_temp, find_import_files, print_import_file_summary
from kia.naming import build_basename_from_prompts
from kia.manifest import create_preview_manifest


def main() -> None:
    """
    Main script entry point.
    """
    config = load_config()

    root = tk.Tk()
    root.withdraw()

    zip_path = select_zip_file(config)
    library_root = select_library_root(config)

    target_library = config.get("last_target_library", "CONNECTORS")
    library_settings = config.get("libraries", {}).get(target_library, {})

    print()
    print("Selected import settings:")
    print(f"ZIP:             {zip_path}")
    print(f"Library root:    {library_root}")
    print(f"Target library:  {target_library}")
    print(f"Path variable:   {config.get('path_variable')}")
    print(f"Footprint dir:   {library_settings.get('footprint_dir')}")
    print(f"Symbol file:     {library_settings.get('symbol_file')}")
    print(f"Nickname:        {library_settings.get('nickname')}")
    print(f"Prefix:          {library_settings.get('prefix')}")

    target_footprint_dir = library_root / library_settings.get("footprint_dir", "")
    target_symbol_file = target_footprint_dir / library_settings.get("symbol_file", "")

    print()
    print("Resolved target paths:")
    print(f"Footprint/model folder: {target_footprint_dir}")
    print(f"Symbol library file:    {target_symbol_file}")

    if not target_footprint_dir.exists():
        print()
        print("WARNING:")
        print("Target footprint/model folder does not exist yet:")
        print(f"  {target_footprint_dir}")
        print("The script will not create or modify anything in this version.")

    extract_root = extract_zip_to_temp(zip_path)
    found_files = find_import_files(extract_root)
    print_import_file_summary(found_files, extract_root)

    basename = build_basename_from_prompts(config, library_settings, found_files)

    print()
    print("Generated target basename:")
    print(f"  {basename}")

    confirm_manifest = input("Create preview manifest? [Y/n]: ").strip().lower()

    if confirm_manifest in ["", "y", "yes"]:
        create_preview_manifest(
            found_files=found_files,
            extract_root=extract_root,
            library_root=library_root,
            library_settings=library_settings,
            basename=basename,
        )
    else:
        print("Preview manifest skipped.")

    save_config(config)
    print()
    print(f"Config saved: {CONFIG_PATH}")

    print()
    print("Version 0.4 complete.")
    print("No library files were modified.")


if __name__ == "__main__":
    main()