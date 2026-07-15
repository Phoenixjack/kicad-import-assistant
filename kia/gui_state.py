"""
GUI state containers for the KiCad Import Assistant.
"""

from dataclasses import dataclass, field


SEVERITY_ORDER = {
    "debug": 10,
    "info": 20,
    "success": 25,
    "warning": 30,
    "error": 40,
}


@dataclass
class LogSettings:
    status_level: str = "info"
    file_log_level: str = "off"
    max_log_size_kb: int = 1024
    retained_log_count: int = 3
    redact_private_paths: bool = True


@dataclass
class TabState:
    dirty: bool = False
    stage: str = "idle"


@dataclass
class GuiAppState:
    active_tab: str = "import"
    status_message: str = "Ready."
    status_severity: str = "info"
    log_settings: LogSettings = field(default_factory=LogSettings)
    import_tab: TabState = field(default_factory=TabState)
    config_tab: TabState = field(default_factory=TabState)
    schema_tab: TabState = field(default_factory=lambda: TabState(stage="read_only"))

    def tab_is_dirty(self, tab_name: str) -> bool:
        tab_state = self.get_tab_state(tab_name)
        return tab_state.dirty

    def get_tab_state(self, tab_name: str) -> TabState:
        if tab_name == "config":
            return self.config_tab

        if tab_name == "schema":
            return self.schema_tab

        return self.import_tab

    def has_dirty_work(self) -> bool:
        return (
            self.import_tab.dirty
            or self.config_tab.dirty
            or self.schema_tab.dirty
        )
