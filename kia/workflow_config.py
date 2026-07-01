"""
kia/workflow_config.py
  CONFIG_PATH
  DEFAULT_CONFIG_PATH
  PRIVATE_DATA_PATH
  load_config()
  save_config()
  load_runtime_config()
  save_successful_config_state()
"""

import copy
import json
from pathlib import Path

from kia.debug import dbg_print, Severity
from kia.workflow_schema import load_naming_schema
from kia.workflow_status import mark_success, mark_failure
from kia.workflow_final import ensure_finalization_state


SCRIPT_DIR = Path(__file__).resolve().parent.parent

DEFAULT_CONFIG_PATH = SCRIPT_DIR / "kicad_import_assistant_default_config.json"
PRIVATE_DATA_PATH = SCRIPT_DIR / "kicad_import_private_data.json"
PRIVATE_DATA_EXAMPLE_PATH = SCRIPT_DIR / "kicad_import_private_data.example.json"


# Keep CONFIG_PATH as an alias for older imports/messages.
# Runtime saves now go to the private data file.
CONFIG_PATH = PRIVATE_DATA_PATH


RECENT_VALUE_FIELDS = [
    "family",
    "role",
    "mount",
    "orient",
    "size",
    "pitch",
    "base",
    "feature",
]


DEFAULT_CONFIG = {
    "config_schema_version": 1,
    "keep_temp_files": False,
    "source_cleanup": {
        "prompt_after_success": True,
        "mode": "archive",
        "archive_folder_name": "_imported",
        "archive_loose_files": True,
        "archive_zip_files": True,
    },
    "api_integrations": {
        "supported_apis": [
            "mouser",
        ],
    },
}


def deep_merge_dicts(base: dict, overlay: dict) -> dict:
    """
    Recursively merge overlay into base.

    Values from overlay win.
    Nested dicts are merged instead of replaced wholesale.
    """
    result = copy.deepcopy(base)

    for key, overlay_value in overlay.items():
        base_value = result.get(key)

        if isinstance(base_value, dict) and isinstance(overlay_value, dict):
            result[key] = deep_merge_dicts(base_value, overlay_value)
        else:
            result[key] = copy.deepcopy(overlay_value)

    return result


def load_json_file(path: Path, *, required: bool = False) -> dict:
    """
    Load a JSON object from disk.

    Missing optional files return an empty dict.
    Invalid JSON stops the program.
    """
    if not path.exists():
        if required:
            print()
            print("ERROR: Required JSON file is missing.")
            print(f"  File: {path}")
            raise SystemExit

        return {}

    try:
        with path.open("r", encoding="utf-8") as file:
            loaded_data = json.load(file)

    except json.JSONDecodeError as error:
        print()
        print("ERROR: JSON file is not valid.")
        print(f"  File: {path}")
        print(f"  Line: {error.lineno}")
        print(f"  Column: {error.colno}")
        print(f"  Problem: {error.msg}")
        print()
        print("Fix the JSON file before running the importer.")
        raise SystemExit

    if not isinstance(loaded_data, dict):
        print()
        print("ERROR: JSON file must contain an object at the top level.")
        print(f"  File: {path}")
        raise SystemExit

    return loaded_data


def write_json_file(path: Path, data: dict) -> None:
    """
    Write a JSON object to disk as readable UTF-8 JSON.
    """
    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=2)
        file.write("\n")


def ensure_runtime_config_defaults(config: dict) -> dict:
    """
    Add runtime-safe defaults that should exist even when omitted
    from the public default config or private data file.
    """
    config.setdefault("recent_values", {})

    for field_name in RECENT_VALUE_FIELDS:
        config["recent_values"].setdefault(field_name, [])

    config.setdefault("api_integrations", {})
    config["api_integrations"].setdefault("supported_apis", [])
    config["api_integrations"].setdefault("keys", {})

    return config


def validate_runtime_config(config: dict) -> None:
    """
    Validate config sections required for the current importer workflow.

    The public default config intentionally does not include local paths
    or library profiles, so those must come from private data.
    """
    errors = []

    last_config = config.get("last")
    libraries = config.get("libraries")

    if not isinstance(last_config, dict) or not last_config:
        errors.append(
            "Missing private `last` settings. "
            "Add local picker/library defaults to kicad_import_private_data.json."
        )

    if not isinstance(libraries, dict) or not libraries:
        errors.append(
            "Missing private `libraries` settings. "
            "Add at least one target library profile to kicad_import_private_data.json."
        )

    if not config.get("path_variable"):
        errors.append(
            "Missing `path_variable`. "
            "Add the KiCad path variable name to kicad_import_private_data.json."
        )

    if isinstance(last_config, dict):
        if not last_config.get("source_folder"):
            errors.append("Missing `last.source_folder` in private data.")

        if not last_config.get("library_root"):
            errors.append("Missing `last.library_root` in private data.")

        if not last_config.get("library_folder"):
            errors.append("Missing `last.library_folder` in private data.")

        if not last_config.get("target_library"):
            errors.append("Missing `last.target_library` in private data.")

    if errors:
        print()
        print("ERROR: Runtime config is incomplete.")
        print()
        print("The importer now uses layered config files:")
        print(f"  Public defaults: {DEFAULT_CONFIG_PATH}")
        print(f"  Private data:    {PRIVATE_DATA_PATH}")
        print()
        print("Problems found:")

        for error in errors:
            print(f"  - {error}")

        print()
        print("Use the example private data file as a template:")
        print(f"  {PRIVATE_DATA_EXAMPLE_PATH}")
        raise SystemExit


def build_private_data_to_save(config: dict) -> dict:
    """
    Build the local/private data payload that should be saved after a
    successful import.

    The public default config is not modified during normal use.
    """
    private_data = {
        "config_schema_version": config.get("config_schema_version", 1),
    }

    if isinstance(config.get("last"), dict):
        private_data["last"] = copy.deepcopy(config["last"])

    if config.get("path_variable") is not None:
        private_data["path_variable"] = config["path_variable"]

    if isinstance(config.get("libraries"), dict):
        private_data["libraries"] = copy.deepcopy(config["libraries"])

    if isinstance(config.get("recent_values"), dict):
        private_data["recent_values"] = copy.deepcopy(config["recent_values"])

    api_integrations = config.get("api_integrations", {})

    if isinstance(api_integrations, dict):
        api_keys = api_integrations.get("keys")

        if isinstance(api_keys, dict):
            private_data.setdefault("api_integrations", {})
            private_data["api_integrations"]["keys"] = copy.deepcopy(api_keys)

    return private_data


def load_config() -> dict:
    """
    Load runtime config from layered sources.

    Precedence:
      1. Python DEFAULT_CONFIG fallback
      2. tracked public default config JSON
      3. ignored private data JSON

    Private/local data wins over public defaults.
    """
    config = copy.deepcopy(DEFAULT_CONFIG)

    default_config = load_json_file(DEFAULT_CONFIG_PATH, required=False)

    if not PRIVATE_DATA_PATH.exists():
        print()
        print("ERROR: Private data file is missing.")
        print()
        print("Create a private data file before running the importer:")
        print(f"  {PRIVATE_DATA_PATH}")
        print()
        print("Use this example as a template:")
        print(f"  {PRIVATE_DATA_EXAMPLE_PATH}")
        raise SystemExit

    private_data = load_json_file(PRIVATE_DATA_PATH, required=True)

    config = deep_merge_dicts(config, default_config)
    config = deep_merge_dicts(config, private_data)
    config = ensure_runtime_config_defaults(config)

    validate_runtime_config(config)

    dbg_print(
        f"Default config path = {DEFAULT_CONFIG_PATH}",
        Severity.VERBOSE,
        "config",
        "load",
        "config",
    )
    dbg_print(
        f"Private data path = {PRIVATE_DATA_PATH}",
        Severity.VERBOSE,
        "config",
        "load",
        "config",
    )
    dbg_print(
        f"keep_temp_files = {config.get('keep_temp_files')}",
        Severity.VERBOSE,
        "config",
        "load",
        "config",
    )

    return config


def save_config(config: dict) -> None:
    """
    Save private/local config data.

    The tracked public default config file is never modified during normal use.
    """
    existing_private_data = load_json_file(PRIVATE_DATA_PATH, required=False)
    runtime_private_data = build_private_data_to_save(config)

    private_data_to_save = deep_merge_dicts(
        existing_private_data,
        runtime_private_data,
    )

    write_json_file(PRIVATE_DATA_PATH, private_data_to_save)


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

    Saves recent successful run values back to private data.

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

        if run_state["current"].get("source_folder") is not None:
            config["last"]["source_folder"] = str(run_state["current"]["source_folder"])

        if run_state["current"].get("library_root") is not None:
            config["last"]["library_root"] = str(run_state["current"]["library_root"])

        if run_state["current"].get("library_folder") is not None:
            config["last"]["library_folder"] = str(run_state["current"]["library_folder"])

        if run_state["current"].get("target_library") is not None:
            config["last"]["target_library"] = run_state["current"]["target_library"]

        if run_state.get("recent_values"):
            config["recent_values"] = run_state["recent_values"]

        save_config(config)

    except Exception as error:
        return mark_failure(
            run_state,
            script="workflow_config.py",
            step="save_successful_config_state",
            function_name="save_successful_config_state",
            failure_reason=f"Failed to save successful private data state.\n{error}",
            severity=Severity.ERROR,
        )

    run_state["finalization"]["config_saved"] = True

    print()
    print("Private data updated:")
    print(f"  Private data file: {PRIVATE_DATA_PATH}")

    return mark_success(
        run_state,
        script="workflow_config.py",
        step="save_successful_config_state",
        function_name="save_successful_config_state",
        message="Successful private data state saved.",
    )