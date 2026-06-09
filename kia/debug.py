DEBUG_ENABLED = True

DEBUG_CATEGORIES = {
    "config": False,       # loading/saving config, resolved config paths
    "zip": False,          # ZIP extraction/temp folder details
    "dialogs": False,      # user prompts
    "files": False,        # detected files, selected files
    "suggestions": False,  # JSON rule matches/defaults
    "tokens": False,       # prompt/default token values
    "symbols": True,       # processing of symbols and symbol libraries
    "basename": False,     # token cleanup and final basename generation
    "manifest": False,     # manifest rows/path
    "importer": True,      # copy paths, overwrite checks, footprint edits
    "info": False,         # success announcements
    "verbose": False,      # extra information
    "schema": False,       # handles tokens as menus as derived from kicad_import_naming_schema.json 
}


def debug_print(category: str, message: str) -> None:
    """
    Print debug messages only when global debug and category debug are enabled.
    """
    if not DEBUG_ENABLED:
        return

    if not DEBUG_CATEGORIES.get(category, False):
        return

    print(f"[{category.upper()}] {message}")