"""
kia/workflow_config.py
  CONFIG_PATH, 
  load_config, 
  save_config,
  load_runtime_config()
  save_successful_config_state()
"""

import json
from pathlib import Path

from kia.debug import dbg_print, Severity
from kia.workflow_schema import load_naming_schema
from kia.workflow_status import mark_success, mark_failure
from kia.workflow_final import ensure_finalization_state


SCRIPT_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = SCRIPT_DIR / "kicad_import_assistant_config.json"


DEFAULT_CONFIG = {
    "last": {
        "zip_folder": "%USERPROFILE%/Downloads",
        "library_root": "%USERPROFILE%/Documents/KiCAD/CUSTOM_LIBRARIES",
        "library_folder": "%USERPROFILE%/Documents/KiCAD/CUSTOM_LIBRARIES",
        "target_library": "CONNECTORS",
        "profile": "connector",
    },
    "path_variable": "CHRIS_KICAD_LIB",
    "keep_temp_files": False,
    "libraries": {
        "CONNECTORS": {
            "prefix": "CONN",
            "footprint_dir": "_testCONN.pretty",
            "symbol_file": "_testCONN.kicad_sym",
            "nickname": "_testCONN",
            "schema_profile": "connector",
        },
        "IC": {
            "prefix": "IC",
            "footprint_dir": "_testIC.pretty",
            "symbol_file": "_testIC.kicad_sym",
            "nickname": "_testIC",
            "schema_profile": "ic",
        },
    },
    "recent_values": {
        "family": [],
        "role": [],
        "mount": [],
        "orient": [],
        "size": [],
        "pitch": [],
        "base": [],
        "feature": [],
    },
}


def load_config() -> dict:
    """
    Load config from disk, merged over defaults.

    Invalid JSON should stop the program instead of silently falling back
    to DEFAULT_CONFIG.
    """
    config = copy.deepcopy(DEFAULT_CONFIG)

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
    
    dbg_print(f"Config loaded from {CONFIG_PATH}", Severity.VERBOSE, "config", "load", "config")
    dbg_print(f"keep_temp_files = {config.get('keep_temp_files')}", Severity.VERBOSE, "config", "load", "config")

    return config


def save_config(config: dict) -> None:
    """
    Save config back to disk as readable JSON.
    """
    with CONFIG_PATH.open("w", encoding="utf-8") as file:
        json.dump(config, file, indent=2)


def load_runtime_config(run_state: dict) -> dict:
    """
    Owns:
    - run_state["status"]
    - run_state["config"]
    """
    try:
        general_config = load_config()
        naming_schema = load_naming_schema()

    except Exception as error:
        return mark_failure(
            run_state,
            script="workflow_config.py",
            step="load_runtime_config",
            function_name="load_runtime_config",
            failure_reason=f"Failed to load required runtime config.\n{error}",
            severity=Severity.ERROR,
        )

    run_state["config"]["general_config"] = general_config
    run_state["config"]["naming_schema"] = naming_schema
    run_state["config"]["general_config_loaded"] = True
    run_state["config"]["naming_schema_loaded"] = True
    run_state["config"]["loaded"] = True

    return mark_success(
        run_state,
        script="workflow_config.py",
        step="load_runtime_config",
        function_name="load_runtime_config",
        message="Runtime config loaded.",
    )


def save_successful_config_state(run_state: dict) -> dict:
    """
    Owns:
    - run_state["status"]
    - run_state["finalization"]["config_saved"]

    Saves recent successful run values back to config.

    This stage runs only after import writes have succeeded.
    """
    run_state = ensure_finalization_state(run_state)
    config = run_state["config"]["general_config"]

    if config is None:
        return mark_failure(
            run_state,
            script="workflow_config.py",
            step="save_successful_config_state",
            function_name="save_successful_config_state",
            failure_reason="Cannot save config because loaded config is missing.",
            severity=Severity.ERROR,
        )

    run_state["finalization"]["attempted"] = True

    try:
        config.setdefault("last", {})

        if run_state["current"].get("zip_folder") is not None:
            config["last"]["zip_folder"] = str(run_state["current"]["zip_folder"])

        if run_state["current"].get("library_root") is not None:
            config["last"]["library_root"] = str(run_state["current"]["library_root"])

        if run_state["current"].get("library_folder") is not None:
            config["last"]["library_folder"] = str(run_state["current"]["library_folder"])

        if run_state["current"].get("target_library") is not None:
            config["last"]["target_library"] = run_state["current"]["target_library"]

        if run_state["profile"].get("selected_profile") is not None:
            config["last"]["profile"] = run_state["profile"]["selected_profile"]

        if run_state.get("recent_values"):
            config["recent_values"] = run_state["recent_values"]

        save_config(config)

    except Exception as error:
        return mark_failure(
            run_state,
            script="workflow_config.py",
            step="save_successful_config_state",
            function_name="save_successful_config_state",
            failure_reason=f"Failed to save successful config state.\n{error}",
            severity=Severity.ERROR,
        )

    run_state["finalization"]["config_saved"] = True

    print()
    print("Config updated:")
    print(f"  Config file: {CONFIG_PATH}")

    return mark_success(
        run_state,
        script="workflow_config.py",
        step="save_successful_config_state",
        function_name="save_successful_config_state",
        message="Successful config state saved.",
    )

