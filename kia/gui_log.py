"""
GUI logging helpers.
"""

import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable

from kia.gui_state import SEVERITY_ORDER, LogSettings


SHORT_MESSAGE_LIMIT = 120
LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
CURRENT_LOG_NAME = "kia-current.log"


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


def severity_meets_threshold(severity: str, threshold: str) -> bool:
    """
    Return True when severity is visible at the selected threshold.
    """
    if threshold.lower() == "off":
        return False

    return SEVERITY_ORDER.get(severity.lower(), 0) >= SEVERITY_ORDER.get(threshold.lower(), 20)


def redact_private_paths(text: str) -> str:
    """
    Redact common local Windows user path prefixes before copying/exporting logs.
    """
    if not text:
        return ""

    redacted = re.sub(
        r"[A-Za-z]:[\\/]+Users[\\/]+[^\\/\"'\s]+",
        "%USERPROFILE%",
        text,
    )
    return redacted


class GuiLogger:
    """
    Collect log entries, update the status bar, and optionally write a file log.
    """

    def __init__(
        self,
        settings: LogSettings,
        status_callback: Callable[[LogEntry], None] | None = None,
    ) -> None:
        self.settings = settings
        self.status_callback = status_callback
        self.entries: list[LogEntry] = []
        self.log_dir = LOG_DIR
        self.current_log_path = self.log_dir / CURRENT_LOG_NAME
        self._session_file_initialized = False

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

        self.write_entry_to_file_if_enabled(entry)

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
        return severity_meets_threshold(entry.severity, self.settings.status_level)

    def entry_meets_file_threshold(self, entry: LogEntry) -> bool:
        return severity_meets_threshold(entry.severity, self.settings.file_log_level)

    def severity_values(self) -> list[str]:
        return ["All", "Error", "Warning", "Success", "Info", "Debug"]

    def category_values(self) -> list[str]:
        values = sorted({entry.category for entry in self.entries if entry.category})
        return ["All"] + values

    def function_values(self) -> list[str]:
        values = sorted({entry.function_name for entry in self.entries if entry.function_name})
        return ["All"] + values

    def filtered_entries(
        self,
        severity_filter: str = "All",
        category_filter: str = "All",
        function_filter: str = "All",
        text_filter: str = "",
    ) -> list[LogEntry]:
        filtered = list(self.entries)

        if severity_filter != "All":
            selected = severity_filter.lower()
            filtered = [entry for entry in filtered if entry.severity == selected]

        if category_filter != "All":
            filtered = [entry for entry in filtered if entry.category == category_filter]

        if function_filter != "All":
            filtered = [entry for entry in filtered if entry.function_name == function_filter]

        if text_filter.strip():
            needle = text_filter.strip().lower()
            filtered = [
                entry for entry in filtered
                if (
                    needle in entry.short_message.lower()
                    or needle in entry.details.lower()
                    or needle in entry.category.lower()
                    or needle in entry.function_name.lower()
                )
            ]

        return filtered

    def update_settings(self, settings: LogSettings) -> None:
        """
        Replace logger settings and prepare file logging if enabled.
        """
        self.settings = settings

        if self.settings.file_log_level.lower() != "off":
            self.prepare_file_logging()

    def prepare_file_logging(self) -> None:
        """
        Create the log folder and initialize session logging once.
        """
        self.log_dir.mkdir(parents=True, exist_ok=True)

        if self._session_file_initialized:
            return

        if self.settings.retained_log_count == 0:
            self.current_log_path.write_text("", encoding="utf-8")

        self._session_file_initialized = True

    def write_entry_to_file_if_enabled(self, entry: LogEntry) -> None:
        """
        Append one entry to the rolling file log when enabled.
        """
        if not self.entry_meets_file_threshold(entry):
            return

        self.prepare_file_logging()
        self.rotate_log_if_needed()

        entry_data = asdict(entry)

        if self.settings.redact_private_paths:
            entry_data["short_message"] = redact_private_paths(entry_data["short_message"])
            entry_data["details"] = redact_private_paths(entry_data["details"])

        with self.current_log_path.open("a", encoding="utf-8") as file:
            json.dump(entry_data, file)
            file.write("\n")

    def rotate_log_if_needed(self) -> None:
        """
        Rotate kia-current.log when it exceeds the configured size.
        """
        if not self.current_log_path.exists():
            return

        max_bytes = self.settings.max_log_size_kb * 1024

        if self.current_log_path.stat().st_size < max_bytes:
            return

        if self.settings.retained_log_count == 0:
            self.current_log_path.write_text("", encoding="utf-8")
            return

        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        rotated_path = self.log_dir / f"kia-{timestamp}.log"
        self.current_log_path.replace(rotated_path)
        self.purge_old_logs()

    def purge_old_logs(self) -> None:
        """
        Keep only the configured number of rotated log files.
        """
        if self.settings.retained_log_count <= 0:
            for log_path in self.log_dir.glob("kia-*.log"):
                log_path.unlink(missing_ok=True)
            return

        rotated_logs = sorted(
            self.log_dir.glob("kia-*.log"),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )

        for old_log in rotated_logs[self.settings.retained_log_count:]:
            old_log.unlink(missing_ok=True)

    def format_entries_for_clipboard(self, entries: list[LogEntry]) -> str:
        """
        Build a copy-friendly diagnostics text block.
        """
        lines = []

        for entry in entries:
            short_message = entry.short_message
            details = entry.details or entry.short_message

            if self.settings.redact_private_paths:
                short_message = redact_private_paths(short_message)
                details = redact_private_paths(details)

            lines.append(
                "\t".join(
                    [
                        entry.timestamp,
                        entry.severity.upper(),
                        entry.category,
                        entry.function_name,
                        short_message,
                    ]
                )
            )

            if details and details != short_message:
                lines.append(f"  {details}")

        return "\n".join(lines)
