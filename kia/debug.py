DEBUG_ENABLED = True

DEBUG_CATEGORIES = {
    "config": False,
    "zip": False,
    "dialogs": False,
    "files": False,
    "suggestions": False,
    "tokens": False,
    "rules": False,
    "basename": False,
    "manifest": False,
    "importer": False,
    "critical": True,
    "warning": True,
    "error": True,
    "info": False,
    "verbose": False,
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