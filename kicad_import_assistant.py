"""
KiCad Import Assistant

Purpose:
Import vendor ZIP files containing KiCad footprints, symbols, and 3D models
into a custom KiCad library structure.

Current version:
0.8.0

Current behavior:
- Select a vendor ZIP file.
- Select a KiCad custom library root.
- Load naming schema and suggestion-rule JSON files.
- Extract the vendor ZIP to a temporary folder.
- Detect .kicad_mod, .kicad_sym, .step, and .stp files.
- Resolve the target footprint/model folder.
- Resolve the target .kicad_sym file from config or by scanning the target .pretty folder.
- Suggest naming defaults from detected filenames.
- Prompt for naming tokens using schema-driven menus where available.
- Generate a standardized basename.
- Create a temporary edited symbol preview file when a source symbol is available.
- Update the preview symbol name.
- Update the preview symbol Footprint property.
- Optionally create a preview manifest CSV.
- Require hard confirmation before writing footprint/model files.
- Copy/rename selected footprint and STEP/STP model files.
- Update copied footprint internal name, Value field, 3D model path, and import metadata.
- Refuse to overwrite existing footprint/model files.
- Report final operation status using import result flags.
- Leave target .kicad_sym libraries unchanged for now.

Future goals:
- Safely merge previewed symbols into target .kicad_sym files.
- Create backups before modifying symbol libraries.
- Refuse symbol merge if the target symbol already exists.
- Add stronger validation from the naming schema.
- Add backup/rollback behavior.
- Add batch/manifest mode.
- Explore dialog-based and/or KiCad plugin workflows.
"""

APP_VERSION = "0.8.0"

import tkinter as tk
from kia.debug import debug_print
from pathlib import Path
from kia.config import CONFIG_PATH, load_config, save_config
from kia.dialogs import select_zip_file, select_library_root
from kia.zip_scan import extract_zip_to_temp, find_import_files, print_import_file_summary
from kia.naming import build_basename_from_prompts, suggest_defaults_from_files, prompt_with_default
from kia.manifest import create_preview_manifest, select_import_files
from kia.symbols import resolve_target_symbol_file
from kia.symbol_editor import create_symbol_preview_file
from kia.schema import load_naming_schema
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
    
    naming_schema = load_naming_schema()

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
        naming_schema=naming_schema,
    )
    debug_print("verbose", "")
    debug_print("verbose", "Generated target basename:")
    debug_print("verbose", f"  {basename}")

    import_result = {
        "confirmed": False,
        "files_copied": False,
        "copied_files": [],
        "footprint_name_updated": False,
        "footprint_value_updated": False,
        "model_reference_updated": False,
        "model_reference_added": False,
        "metadata_added": False,
        "symbols_merged": False,
        "symbol_preview_created": False,
        "symbol_name_updated": False,
        "symbol_footprint_property_updated": False,
    }
    
    selected_files = select_import_files(found_files)
    
    print()
    print("DEBUG symbol preview call:")
    print(f"  selected_files keys: {list(selected_files.keys())}")
    print(f"  selected symbol: {selected_files.get('symbol')}")
    print(f"  extract_root: {extract_root}")

    symbol_preview_result = create_symbol_preview_file(
        selected_files=selected_files,
        library_settings=library_settings,
        basename=basename,
        extract_root=extract_root,
    )
    
    print()
    print("Symbol preview:")
    if symbol_preview_result.get("symbol_preview_created"):
        print(f"  Preview file: {symbol_preview_result.get('preview_symbol')}")
        print(f"  Old symbol name: {symbol_preview_result.get('old_symbol_name')}")
        print(f"  New symbol name: {symbol_preview_result.get('new_symbol_name')}")
        print(f"  Footprint property: {symbol_preview_result.get('footprint_property')}")
        print(f"  Symbol name updated: {'YES' if symbol_preview_result.get('symbol_name_updated') else 'NO'}")
        print(f"  Footprint property updated: {'YES' if symbol_preview_result.get('footprint_property_updated') else 'NO'}")
    else:
        print("  No symbol preview created.")
        
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
            target_symbol_file=target_symbol_file,
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

    import_result["symbol_preview_created"] = symbol_preview_result.get("symbol_preview_created", False)
    import_result["symbol_name_updated"] = symbol_preview_result.get("symbol_name_updated", False)
    import_result["symbol_footprint_property_updated"] = symbol_preview_result.get("footprint_property_updated", False)

    if confirm_import():
        copy_result = copy_selected_import_files(
            selected_files=selected_files,
            library_root=library_root,
            library_settings=library_settings,
            config=config,
            basename=basename,
            app_version=APP_VERSION,
        )

        import_result.update(copy_result)

    else:
        print()
        print("Import canceled. No files were copied.")

    save_config(config)
    debug_print("verbose", "")
    debug_print("verbose", f"Config saved: {CONFIG_PATH}")
    print()
    print(f"Version {APP_VERSION} complete.")
    print()
    print("Import status:")

    if import_result.get("confirmed", False):
        print(f"  Files copied: {'YES' if import_result.get('files_copied') else 'NO'}")
        print(f"  Footprint internal name updated: {'YES' if import_result.get('footprint_name_updated') else 'NO'}")
        print(f"  Footprint Value field updated: {'YES' if import_result.get('footprint_value_updated') else 'NO'}")

        if import_result.get("model_reference_added"):
            print("  3D model reference: ADDED")
        elif import_result.get("model_reference_updated"):
            print("  3D model reference: UPDATED")
        else:
            print("  3D model reference: NO")
        
        print(f"  Import metadata present: {'YES' if import_result.get('metadata_added') else 'NO'}")
        print(f"  Symbol preview created: {'YES' if import_result.get('symbol_preview_created') else 'NO'}")
        print(f"  Symbol name preview updated: {'YES' if import_result.get('symbol_name_updated') else 'NO'}")
        print(f"  Symbol Footprint property preview updated: {'YES' if import_result.get('symbol_footprint_property_updated') else 'NO'}")
        print("  Symbol merged: NO - preview only")
    else:
        print("  Files copied: NO - import was canceled")
        print("  Footprint updates: NOT ATTEMPTED")
        print("  Symbol merged: NO - preview only")


if __name__ == "__main__":
    main()