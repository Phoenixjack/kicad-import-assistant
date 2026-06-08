import copy
import json
import os
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = SCRIPT_DIR / "kicad_import_assistant_config.json"


DEFAULT_CONFIG = {
    "last_zip_folder": "%USERPROFILE%/Downloads",
    "last_library_root": "%USERPROFILE%/Documents/KiCAD/CUSTOM_LIBRARIES",
    "last_target_library": "CONNECTORS",
    "path_variable": "CHRIS_KICAD_LIB",
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
    Load JSON config from disk.
    If the config does not exist or is invalid, return default settings.
    """
    if not CONFIG_PATH.exists():
        print(f"No config found. Using defaults: {CONFIG_PATH}")
        return copy.deepcopy(DEFAULT_CONFIG)

    try:
        with CONFIG_PATH.open("r", encoding="utf-8") as file:
            loaded_config = json.load(file)

        config = copy.deepcopy(DEFAULT_CONFIG)

        for key, value in loaded_config.items():
            if key != "libraries":
                config[key] = value

        loaded_libraries = loaded_config.get("libraries", {})
        for library_name, library_settings in loaded_libraries.items():
            if library_name not in config["libraries"]:
                config["libraries"][library_name] = {}

            config["libraries"][library_name].update(library_settings)

        return config

    except json.JSONDecodeError as error:
        print(f"Config file contains invalid JSON: {CONFIG_PATH}")
        print(error)
        print("Using defaults instead.")
        return copy.deepcopy(DEFAULT_CONFIG)


def save_config(config: dict) -> None:
    """
    Save config back to disk as readable JSON.
    """
    with CONFIG_PATH.open("w", encoding="utf-8") as file:
        json.dump(config, file, indent=2)