"""
Debug / diagnostic output helpers for KiCad Import Assistant.

Severity controls how important/noisy a message is.
Category controls which subsystem/domain the message belongs to.
Stage gives optional workflow detail.
Source gives optional module/source detail.
"""

from enum import IntEnum

DEBUG_LABEL_WIDTH = 8

class Severity(IntEnum):
    ERROR = 1       # Something failed or the user must fix something.
    WARNING = 2     # Something suspicious, unsafe, skipped, or needs review.
    INFO = 3        # Normal useful status messages.
    VERBOSE = 4     # Deep debug noise / internal details.


# Show messages at this severity or more important.
#
# Examples:
#   Severity.ERROR    -> show only ERROR
#   Severity.WARNING  -> show ERROR and WARNING
#   Severity.INFO     -> show ERROR, WARNING, and INFO
#   Severity.VERBOSE  -> show everything
DEBUG_MAX_SEVERITY = Severity.VERBOSE

DEBUG_CATEGORIES = {
    "config": False,       # loading/saving config, resolved config paths
    "schema": False,       # naming schema loading and parsing
    "zip": False,          # ZIP extraction/temp folder details
    "files": False,        # detected files, selected files
    "libraries": False,    #
    "suggest": False,      # JSON rule matches/defaults
    "tokens": False,       # prompt/default token values
    "basename": False,     # token cleanup and final basename generation
    "manifest": False,     # manifest rows/path
    "importer": False,     # copy paths, overwrite checks, footprint edits
    "symbols": False,      # processing of symbols and symbol libraries
    "dialogs": False,      # user file/folder dialogs
}


def _severity_label(severity: Severity) -> str:
    """
    Return printable severity label.
    """
    return severity.name


def dbg_blank(
    severity: Severity = Severity.INFO,
    category: str | None = None,
    stage: str | None = None,
    source: str | None = None,
) -> None:
    """
    Print a blank-looking debug line using the normal debug prefix.
    """
    dbg_print(
        "",
        severity=severity,
        category=category,
        stage=stage,
        source=source,
    )


def _format_debug_prefix(
    severity: Severity,
    category: str | None = None,
    stage: str | None = None,
    source: str | None = None,
) -> str:
    """
    Build a readable debug prefix.

    Format:
      [ SEVERITY / CATEGORY / STAGE ] (source)

    Only severity is required.
    """
    
    label_parts = []
    
    _severity_text = _severity_label(severity)
    _severity_text = _severity_text.center(DEBUG_LABEL_WIDTH, " ")
    label_parts.append(_severity_text)
    
    if category:
        category = category[:DEBUG_LABEL_WIDTH]
        category = category.upper()
        category = category.center(DEBUG_LABEL_WIDTH, " ")
        label_parts.append(category)

    if stage:
        stage = stage[:DEBUG_LABEL_WIDTH]
        stage = stage.upper()
        stage = stage.center(DEBUG_LABEL_WIDTH, " ")
        label_parts.append(stage.upper())

    prefix = "[" + "/".join(label_parts) + "]"

    if source:
        prefix += f" ({source})"

    return prefix


def dbg_print(
    message: str,
    severity: Severity = Severity.INFO,
    category: str | None = None,
    stage: str | None = None,
    source: str | None = None,
) -> None:
    """
    Print a developer/debug diagnostic message if enabled by severity/category.

    Category is optional. If no category is supplied, filtering is based only
    on severity.

    Examples:
      dbg_print("Config loaded.", Severity.INFO, "config", "load", "config")
      dbg_print("Target file exists.", Severity.WARNING, "importer")
      dbg_print("Temp cleanup skipped.", Severity.INFO)
      # dbg_print(text, Severity.INFO, "config", "load", "config")
    """
    if not isinstance(severity, Severity):
        severity = Severity(severity)

    if severity > DEBUG_MAX_SEVERITY:
        return

    if category is not None:
        if category not in DEBUG_CATEGORIES:
            print(f"[DEBUG/WARNING] Unknown debug category: {category}")
            return

        if not DEBUG_CATEGORIES.get(category, False):
            return

    prefix = _format_debug_prefix(
        severity=severity,
        category=category,
        stage=stage,
        source=source,
    )

    print(f"{prefix} {message}")

