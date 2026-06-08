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

APP_VERSION = "0.6.1"

import tkinter as tk
from pathlib import Path

from kia.config import CONFIG_PATH, load_config, save_config
from kia.dialogs import select_zip_file, select_library_root
from kia.zip_scan import extract_zip_to_temp, find_import_files, print_import_file_summary
from kia.naming import build_basename_from_prompts, suggest_defaults_from_files, prompt_with_default
from kia.manifest import create_preview_manifest, select_import_files
from kia.importer import (
    confirm_import,
    copy_selected_import_files,
    find_existing_files_by_mpn,
    warn_about_existing_mpn_matches,
    confirm_continue_after_duplicate_warning,
)

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
    print(f"Assistant version: {APP_VERSION}")
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
    
    suggested_defaults = suggest_defaults_from_files(found_files)

    print()
    print("Early duplicate check.")
    early_mpn = prompt_with_default("MPN for duplicate search", suggested_defaults.get("mpn", ""))

    existing_matches = find_existing_files_by_mpn(
        library_root=library_root,
        library_settings=library_settings,
        mpn=early_mpn,
    )

    warn_about_existing_mpn_matches(existing_matches, early_mpn)

    if not confirm_continue_after_duplicate_warning(existing_matches):
        print()
        print("Import canceled before naming step.")
        raise SystemExit
    
    basename = build_basename_from_prompts(
        config,
        library_settings,
        found_files,
        override_defaults={"mpn": early_mpn},
    )
    print()
    print("Generated target basename:")
    print(f"  {basename}")

    selected_files = select_import_files(found_files)

    confirm_manifest = input("Create preview manifest? [Y/n]: ").strip().lower()

    if confirm_manifest in ["", "y", "yes"]:
        create_preview_manifest(
            selected_files=selected_files,
            extract_root=extract_root,
            library_root=library_root,
            library_settings=library_settings,
            basename=basename,
        )
    else:
        print("Preview manifest skipped.")

    print()
    print()
    print(f"V{APP_VERSION} can now copy selected footprint/model files and update the copied footprint.")
    print("Symbols are still preview-only and will not be merged yet.")

    if confirm_import():
        copy_selected_import_files(
            selected_files=selected_files,
            library_root=library_root,
            library_settings=library_settings,
            config=config,
            basename=basename,
            app_version=APP_VERSION,
        )
    else:
        print()
        print("Import canceled. No files were copied.")

    save_config(config)
    print()
    print(f"Config saved: {CONFIG_PATH}")

    print()
    print(f"Version {APP_VERSION} complete.")
    print("Footprint/model files may have been copied if IMPORT was confirmed.")
    print("The script attempted to update copied footprint internals.")
    print("Imported footprints were marked with review metadata properties.")
    print("Symbols were not merged.")


if __name__ == "__main__":
    main()