"""
In-memory GUI logging helpers.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Callable

from kia.gui_state import SEVERITY_ORDER, LogSettings


SHORT_MESSAGE_LIMIT = 120


@dataclass
class LogEntry:
    timestamp: str
    severity: str
    category: str
    function_name: str
    short_message: str
    details: str = ""


def truncate_short_message(message: str) -> str:
    """
    Keep status-strip messages compact.
    """
    message = " ".join(str(message).split())

    if len(message) <= SHORT_MESSAGE_LIMIT:
        return message

    return message[: SHORT_MESSAGE_LIMIT - 3].rstrip() + "..."


class GuiLogger:
    """
    Collect log entries and optionally forward visible entries to the status bar.
    """

    def __init__(
        self,
        settings: LogSettings,
        status_callback: Callable[[LogEntry], None] | None = None,
    ) -> None:
        self.settings = settings
        self.status_callback = status_callback
        self.entries: list[LogEntry] = []

    def log(
        self,
        severity: str,
        short_message: str,
        *,
        category: str = "app",
        function_name: str = "",
        details: str = "",
    ) -> LogEntry:
        severity = severity.lower()

        entry = LogEntry(
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            severity=severity,
            category=category,
            function_name=function_name,
            short_message=truncate_short_message(short_message),
            details=details,
        )

        self.entries.append(entry)

        if self.status_callback and self.entry_meets_status_threshold(entry):
            self.status_callback(entry)

        return entry

    def debug(self, short_message: str, **kwargs) -> LogEntry:
        return self.log("debug", short_message, **kwargs)

    def info(self, short_message: str, **kwargs) -> LogEntry:
        return self.log("info", short_message, **kwargs)

    def success(self, short_message: str, **kwargs) -> LogEntry:
        return self.log("success", short_message, **kwargs)

    def warning(self, short_message: str, **kwargs) -> LogEntry:
        return self.log("warning", short_message, **kwargs)

    def error(self, short_message: str, **kwargs) -> LogEntry:
        return self.log("error", short_message, **kwargs)

    def entry_meets_status_threshold(self, entry: LogEntry) -> bool:
        status_level = self.settings.status_level.lower()
        entry_level = entry.severity.lower()

        return SEVERITY_ORDER.get(entry_level, 0) >= SEVERITY_ORDER.get(status_level, 20)

    def severity_values(self) -> list[str]:
        return ["All", "Error", "Warning", "Success", "Info", "Debug"]

    def filtered_entries(self, severity_filter: str = "All") -> list[LogEntry]:
        if severity_filter == "All":
            return list(self.entries)

        selected = severity_filter.lower()
        return [entry for entry in self.entries if entry.severity == selected]
