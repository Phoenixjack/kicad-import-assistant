import json
from pathlib import Path

from kia.debug import (
    dbg_blank,
    dbg_print, 
    Severity, 
)


SCRIPT_DIR = Path(__file__).resolve().parent.parent
NAMING_SCHEMA_PATH = SCRIPT_DIR / "kicad_import_naming_schema.json"


def load_naming_schema() -> dict:
    """
    Load naming schema from kicad_import_naming_schema.json.

    If the schema cannot be loaded, return an empty dict so the importer
    can fall back to plain text prompts.
    """
    
    dbg_print(f"Loading naming schema: {NAMING_SCHEMA_PATH}", Severity.INFO, "schema", "load", "schema")
    dbg_print("Naming schema loaded successfully.", Severity.INFO, "schema", "load", "schema")

    if not NAMING_SCHEMA_PATH.exists():
        print()
        print("WARNING:")
        print(f"Naming schema file not found: {NAMING_SCHEMA_PATH}")
        print("Continuing with plain text prompts.")
        return {}

    try:
        with NAMING_SCHEMA_PATH.open("r", encoding="utf-8") as file:
            schema = json.load(file)

    except json.JSONDecodeError as error:
        print()
        print("WARNING:")
        print(f"Naming schema file contains invalid JSON: {NAMING_SCHEMA_PATH}")
        print(error)
        print("Continuing with plain text prompts.")
        return {}

    dbg_print("Naming schema loaded successfully.", Severity.INFO, "schema", "load", "schema")
    return schema