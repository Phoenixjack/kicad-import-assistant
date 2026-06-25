from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox


ALLOWED_SUFFIXES = {
    ".zip",
    ".kicad_mod",
    ".kicad_sym",
    ".step",
    ".stp",
}


def classify_source_selection(paths: list[Path]) -> tuple[str, list[Path]]:
    """
    Return:
      ("zip", [zip_path])
      ("loose_files", [paths...])

    Raises ValueError for invalid combinations.
    """
    if not paths:
        raise ValueError("No files were selected.")

    invalid = [
        path for path in paths
        if path.suffix.lower() not in ALLOWED_SUFFIXES
    ]

    if invalid:
        raise ValueError(
            "Unsupported file type selected:\n"
            + "\n".join(f"- {path.name}" for path in invalid)
        )

    zip_files = [path for path in paths if path.suffix.lower() == ".zip"]
    loose_files = [path for path in paths if path.suffix.lower() != ".zip"]

    if zip_files and loose_files:
        raise ValueError(
            "Choose either one ZIP file OR one loose symbol/footprint/model set.\n"
            "Do not mix ZIP files with loose files."
        )

    if len(zip_files) > 1:
        raise ValueError("Choose only one ZIP file at a time.")

    if len(zip_files) == 1:
        return "zip", zip_files

    footprints = [path for path in loose_files if path.suffix.lower() == ".kicad_mod"]
    symbols = [path for path in loose_files if path.suffix.lower() == ".kicad_sym"]
    models = [
        path for path in loose_files
        if path.suffix.lower() in {".step", ".stp"}
    ]

    errors = []

    if len(footprints) > 1:
        errors.append("Choose only one footprint file (.kicad_mod).")

    if len(symbols) > 1:
        errors.append("Choose only one symbol file (.kicad_sym).")

    if len(models) > 1:
        errors.append("Choose only one 3D model file (.step/.stp).")

    if errors:
        raise ValueError("\n".join(errors))

    return "loose_files", loose_files


def select_import_source(initial_dir: Path) -> tuple[str, list[Path]] | None:
    """
    Loop until the user chooses a valid import source or cancels.

    Remembers the folder used in the previous selection attempt so invalid
    selections do not kick the user back to the original initial_dir.
    """
    current_initial_dir = initial_dir

    while True:
        selected_paths = filedialog.askopenfilenames(
            title="Select import source: one ZIP or one loose KiCad file set",
            initialdir=str(current_initial_dir),
            filetypes=[
                (
                    "KiCad import sources",
                    "*.zip *.kicad_mod *.kicad_sym *.step *.stp",
                ),
                ("Vendor ZIP", "*.zip"),
                ("KiCad footprint", "*.kicad_mod"),
                ("KiCad symbol", "*.kicad_sym"),
                ("STEP model", "*.step *.stp"),
                ("All files", "*.*"),
            ],
        )

        if not selected_paths:
            return None

        paths = [Path(path) for path in selected_paths]

        # Remember where the user just selected files from, even if the
        # selected combination turns out to be invalid.
        if paths:
            current_initial_dir = paths[0].parent

        try:
            return classify_source_selection(paths)

        except ValueError as error:
            messagebox.showerror(
                title="Invalid import source selection",
                message=str(error),
            )
            # Loop back to the file picker, now starting from current_initial_dir.


def main() -> None:
    root = tk.Tk()
    root.withdraw()
    # C:\Users\phoen\Documents\KiCAD\CUSTOM_LIBRARIES\_IMPORT_REVIEW\kia_testing
    result = select_import_source(Path.home() / "Downloads")

    if result is None:
        print("Canceled.")
        return

    source_mode, source_paths = result

    print(f"Source mode: {source_mode}")
    print("Selected files:")

    for path in source_paths:
        print(f"  {path}")


if __name__ == "__main__":
    main()