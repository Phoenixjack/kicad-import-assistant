DEBUG_ENABLED = True

DEBUG_CATEGORIES = {
    "config": False,
    "zip": False,
    "files": False,
    "suggestions": True,
    "tokens": True,
    "basename": True,
    "manifest": False,
    "importer": False,
    "critical": True,
    "warning": True,
    "error": True,
    "info": True,
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