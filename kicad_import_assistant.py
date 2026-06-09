"""
KiCad Import Assistant

Purpose:
Import vendor ZIP files containing KiCad footprints, symbols, and 3D models
into a custom KiCad library structure.

Current version:
0.6.2

Current behavior:
- Adds target symbol file resolution helper.
- Uses configured symbol file when present.
- Falls back to scanning the target .pretty folder for one .kicad_sym file.
- Reports symbol resolution status in selected import settings.
- Adds a symbols debug category.
- Select vendor ZIP file
- Select KiCad custom library root
- Extract ZIP to a temporary folder
- Detect .kicad_mod, .kicad_sym, .step, and .stp files
- Load naming suggestions from JSON
- Prompt for naming tokens
- Generate standardized basename
- Create preview manifest CSV
- Require hard confirmation before writing files
- Copy/rename selected footprint and STEP/STP model files
- Update copied footprint internal name, Value property, 3D model path, and import metadata
- Refuse to overwrite existing files
- Leave symbols preview-only for now

Future goals:
- Merge symbols into target .kicad_sym file
- Update symbol Footprint property
- Add schema-driven prompt menus
- Add batch/manifest mode
"""

APP_VERSION = "0.6.2"

import tkinter as tk
from kia.debug import debug_print
from pathlib import Path
from kia.config import CONFIG_PATH, load_config, save_config
from kia.dialogs import select_zip_file, select_library_root
from kia.zip_scan import extract_zip_to_temp, find_import_files, print_import_file_summary
from kia.naming import build_basename_from_prompts, suggest_defaults_from_files, prompt_with_default
from kia.manifest import create_preview_manifest, select_import_files
from kia.symbols import resolve_target_symbol_file
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
    target_footprint_dir = library_root / library_settings.get("footprint_dir", "")
    target_symbol_file, symbol_resolution_status = resolve_target_symbol_file(
        target_footprint_dir=target_footprint_dir,
        library_settings=library_settings,
    )
    debug_print("verbose", "")
    debug_print("verbose", f"Assistant version: {APP_VERSION}")
    print()
    print("Selected import settings:")
    print(f"Assistant version..{APP_VERSION}")
    print(f"ZIP................{zip_path}")
    print(f"Library root.......{library_root}")
    print(f"Target library.....{target_library}")
    print(f"Path variable......{config.get('path_variable')}")
    print(f"Footprint dir......{library_settings.get('footprint_dir')}")
    print(f"Resolved symbol....{target_symbol_file}")
    print(f"Nickname...........{library_settings.get('nickname')}")
    print(f"Prefix.............{library_settings.get('prefix')}")
    print()
    print()
    print("Resolved target paths:")
    print(f"Footprint/model folder .. {target_footprint_dir}")

    if target_symbol_file is not None:
        print(f"Symbol library file ..... {target_symbol_file}")
    else:
        print("Symbol library file ..... <not resolved>")

    print(f"Symbol resolution ....... {symbol_resolution_status}")
    
    debug_print("config", "")
    debug_print("config", f"Raw config .............. {config}")
    debug_print("config", "")
    debug_print("config", f"Library settings ........ {library_settings}")
    debug_print("config", "")

    if not target_footprint_dir.exists():
        print()
        print("WARNING:")
        print("Target footprint/model folder does not exist yet:")
        print(f"  {target_footprint_dir}")
        print("The script may fail if this folder is needed for import.")

        print(f"Missing target footprint/model folder: {target_footprint_dir}")

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
        suggested_defaults=suggested_defaults,
    )
    debug_print("verbose", "")
    debug_print("verbose", "Generated target basename:")
    debug_print("verbose", f"  {basename}")

    selected_files = select_import_files(found_files)

    confirm_manifest = input("Create preview manifest? [y/N]: ").strip().lower()

    if confirm_manifest in ["", "n", "no"]:
        debug_print("verbose", "Preview manifest skipped.")
    else:
        create_preview_manifest(
            selected_files=selected_files,
            extract_root=extract_root,
            library_root=library_root,
            library_settings=library_settings,
            basename=basename,
        )

    debug_print("verbose", "")
    debug_print("verbose", "")
    debug_print("verbose", f"V{APP_VERSION} can now copy selected footprint/model files and update the copied footprint.")
    debug_print("verbose", "Symbols are still preview-only and will not be merged yet.")

    print()
    print("Selected files for import:")
    for file_type, file_path in selected_files.items():
        if file_path:
            print(f"  {file_type}: {file_path}")
        else:
            print(f"  {file_type}: <none>")
        
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
    debug_print("verbose", "")
    debug_print("verbose", f"Config saved: {CONFIG_PATH}")
    # TODO: convert each print statement based on flags from earlier instead of all this "maybe I did it, maybe I didn't"
    print()
    print(f"Version {APP_VERSION} complete.")
    #    print("Footprint/model files may have been copied if IMPORT was confirmed.")
    debug_print("verbose", "The script attempted to update copied footprint internals.")
    debug_print("verbose", "Imported footprints were marked with review metadata properties.")
    debug_print("verbose", "Symbols were not merged.")


if __name__ == "__main__":
    main()