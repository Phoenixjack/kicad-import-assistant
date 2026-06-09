from pathlib import Path
from tkinter import filedialog
from kia.debug import debug_print
from kia.config import resolve_path


def get_existing_initial_dir(path_value: str, fallback: Path) -> str:
    """
    Return a safe initial directory for a file/folder picker.

    Supports:
    - Windows environment variables like %USERPROFILE%
    - user-home shortcuts like ~
    """
    if path_value:
        candidate = resolve_path(path_value)
        if candidate.exists() and candidate.is_dir():
            return str(candidate)

    if fallback.exists() and fallback.is_dir():
        return str(fallback)

    return str(Path.home())


def select_zip_file(config: dict) -> Path:
    """
    Open ZIP file picker using the last ZIP folder if possible.
    """
    initial_dir = get_existing_initial_dir(
        config.get("last_zip_folder", ""),
        Path.home() / "Downloads",
    )

    zip_path = filedialog.askopenfilename(
        title="Select vendor ZIP file",
        initialdir=initial_dir,
        filetypes=[("ZIP files", "*.zip"), ("All files", "*.*")],
    )

    if not zip_path:
        print("No ZIP selected. Exiting.")
        raise SystemExit

    zip_path = Path(zip_path)
    config["last_zip_folder"] = str(zip_path.parent)

    return zip_path


def select_library_root(config: dict) -> Path:
    """
    Open folder picker using the last library root if possible.
    """
    initial_dir = get_existing_initial_dir(
        config.get("last_library_root", ""),
        Path.home(),
    )

    selected_folder = filedialog.askdirectory(
        title="Select KiCad custom library root",
        initialdir=initial_dir,
    )

    if not selected_folder:
        print("No library root selected. Exiting.")
        raise SystemExit

    library_root = Path(selected_folder)

    debug_print("dialogs", "")
    debug_print("dialogs", "Selected:")
    debug_print("dialogs", f"  {library_root}")
    if library_root.suffix.lower() == ".pretty":
        debug_print("dialogs", "")
        debug_print("dialogs", "WARNING:")
        debug_print("dialogs", "You selected a .pretty folder as the library root.")
        debug_print("dialogs", "This script expects the parent custom library folder.")
        debug_print("dialogs", "")
        debug_print("dialogs", "Using parent folder instead:")
        debug_print("dialogs", f"  {library_root.parent}")
        debug_print("dialogs", "")

        library_root = library_root.parent

    config["last_library_root"] = str(library_root)

    return library_root