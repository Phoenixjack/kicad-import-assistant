import copy
import json
import os
from pathlib import Path
from kia.debug import debug_print


SCRIPT_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = SCRIPT_DIR / "kicad_import_assistant_config.json"


DEFAULT_CONFIG = {
    "last_zip_folder": "%USERPROFILE%/Downloads",
    "last_library_root": "%USERPROFILE%/Documents/KiCAD/CUSTOM_LIBRARIES",
    "last_target_library": "CONNECTORS",
    "path_variable": "CHRIS_KICAD_LIB",
    "keep_temp_files": False,
    "libraries": {
        "CONNECTORS": {
            "prefix": "CONN",
            "footprint_dir": "CONNECTORS.pretty",
            "symbol_file": "CONNECTORS.kicad_sym",
            "nickname": "CONNECTORS",
        }
    },
}


def resolve_path(path_value: str) -> Path:
    """
    Expand Windows environment variables and user-home shortcuts.

    Examples:
    %USERPROFILE%/Downloads
    ~/Downloads
    """
    expanded = os.path.expandvars(path_value)
    expanded = os.path.expanduser(expanded)
    return Path(expanded)


def load_config() -> dict:
    """
    Load config from disk, merged over defaults.

    Invalid JSON should stop the program instead of silently falling back
    to DEFAULT_CONFIG.
    """
    config = DEFAULT_CONFIG.copy()

    if not CONFIG_PATH.exists():
        save_config(config)
        return config

    try:
        with CONFIG_PATH.open("r", encoding="utf-8") as file:
            loaded_config = json.load(file)

    except json.JSONDecodeError as error:
        print()
        print("ERROR: Config file is not valid JSON.")
        print(f"  File: {CONFIG_PATH}")
        print(f"  Line: {error.lineno}")
        print(f"  Column: {error.colno}")
        print(f"  Problem: {error.msg}")
        print()
        print("Fix the config file before running the importer.")
        raise SystemExit

    config.update(loaded_config)
    return config


def save_config(config: dict) -> None:
    """
    Save config back to disk as readable JSON.
    """
    with CONFIG_PATH.open("w", encoding="utf-8") as file:
        json.dump(config, file, indent=2)