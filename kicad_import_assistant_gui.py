"""
KiCad Import Assistant GUI launcher.

This entry point is intentionally separate from kicad_import_assistant.py while
the Tkinter GUI workflow is developed in parallel with the existing CLI flow.
"""

from kia.gui_app import run_gui_app


if __name__ == "__main__":
    run_gui_app()
