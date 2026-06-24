"""
  Library resolution handling
"""

from pathlib import Path
from kia.config import (
    CONFIG_PATH, 
    load_config, 
    save_config,
)
from kia.debug import (
    dbg_blank,
    dbg_print, 
    Severity, 
)


def select_target_library_profile(config: dict, suggested_profile: str | None = None) -> str:
    """
    Ask the user which configured library profile to use.
    """
    libraries = config.get("libraries", {})

    if not libraries:
        print()
        print("ERROR: No library profiles are configured.")
        print("Check kicad_import_assistant_config.json.")
        raise SystemExit

    library_names = list(libraries.keys())
    default_library = suggested_profile or config.get("last_target_library", library_names[0])

    if default_library not in libraries:
        default_library = library_names[0]

    print()
    print("Target library profiles:")

    for index, library_name in enumerate(library_names):
        settings = libraries[library_name]
        default_marker = "  <default>" if library_name == default_library else ""
        print(
            f"  {index}. {library_name}"
            f" -> {settings.get('footprint_dir')}"
            f"{default_marker}"
        )

    user_input = input(f"Target library profile [{default_library}]: ").strip()

    if user_input == "":
        selected_library = default_library

    elif user_input.isdigit():
        selected_index = int(user_input)

        if selected_index < 0 or selected_index >= len(library_names):
            print()
            print("ERROR: Invalid target library profile number.")
            raise SystemExit

        selected_library = library_names[selected_index]

    elif user_input in libraries:
        selected_library = user_input

    else:
        print()
        print("ERROR: Unknown target library profile.")
        print(f"  Entered: {user_input}")
        raise SystemExit

    config["last_target_library"] = selected_library
    return selected_library


def is_pretty_folder(path: Path) -> bool:
    """
    Return True if the selected path appears to be a KiCad .pretty folder.
    """
    return path.suffix.lower() == ".pretty"


def resolve_library_root_from_selection(selected_folder: Path) -> Path:
    """
    Resolve the KiCad custom library root from the selected folder.

    If the user selected a .pretty folder, the library root is its parent.
    If the user selected the custom library root directly, use it as-is.
    """
    if is_pretty_folder(selected_folder):
        library_root = selected_folder.parent

        dbg_print(
            f"Selected .pretty folder; resolved library root: {library_root}",
            Severity.INFO,
            "libraries",
            stage="root",
            source="library_resolution",
        )

        return library_root

    dbg_print(
        f"Selected library root directly: {selected_folder}",
        Severity.INFO,
        "libraries",
        stage="root",
        source="library_resolution",
    )

    return selected_folder


def infer_profile_from_selected_folder(selected_folder: Path, config: dict) -> str | None:
    """
    Infer a library profile from the selected .pretty folder.
    """
    if not is_pretty_folder(selected_folder):
        dbg_print(
            "Selected folder is not a .pretty folder; no profile inferred.",
            Severity.INFO,
            "libraries",
            stage="infer",
            source="library_resolution",
        )
        return None

    selected_folder_name = selected_folder.name

    for profile_name, settings in config.get("libraries", {}).items():
        if settings.get("footprint_dir") == selected_folder_name:
            dbg_print(
                f"Inferred profile '{profile_name}' from folder '{selected_folder_name}'.",
                Severity.INFO,
                "libraries",
                stage="infer",
                source="library_resolution",
            )
            return profile_name

    dbg_print(
        f"No configured profile matched selected folder '{selected_folder_name}'.",
        Severity.WARNING,
        "libraries",
        stage="infer",
        source="library_resolution",
    )

    return None