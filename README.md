# KiCad Import Assistant

KiCad Import Assistant is a standalone Python utility for importing vendor-provided KiCad footprints, symbols, and 3D models into a custom KiCad library structure.

The tool is designed around a cautious workflow: preview first, confirm explicitly, create backups where needed, and refuse unsafe overwrites.

**Unreleased V0.11.0 loose-file import branch**

Current development branch: `feature/loose-file-import`

Update the branch note/status to something like:

## V0.11 loose-file import branch note

The `feature/loose-file-import` branch adds support for selecting either a single vendor ZIP file or a loose KiCad import file set.

Supported source selections:

- one `.zip` file
- or one loose file set containing up to:
  - one `.kicad_mod`
  - one `.kicad_sym`
  - one `.step` or `.stp`

Invalid mixed selections, duplicate footprints, duplicate symbols, duplicate models, or multiple ZIP files are rejected before the import workflow begins.

## What It Does

KiCad Import Assistant can currently:

* Select either a vendor ZIP file or a loose KiCad import file set.
* Validate import-source selections before staging: 
	* one ZIP file only 
	* or one footprint, one symbol, and one model file at most 
* Remember the last successful import source folder as `source_folder`. 
* Stage loose import files into a temporary import folder so the normal downstream workflow can process them. 
* Support older KiCad/vendor footprint roots using `(module ...)` as well as newer `(footprint ...)` roots.
* Extract the ZIP to a temporary folder.
* Detect KiCad footprint, symbol, and STEP/STP model files.
* Suggest naming defaults from detected files.
* Prompt for naming tokens using schema-driven menus.
* Generate standardized footprint/symbol/model basenames.
* Detect possible existing imports by early MPN search.
* Create and optionally write a preview import-plan CSV.
* Require explicit confirmation before file-copy writes.
* Copy and rename footprint/model files into a target `.pretty` folder.
* Update copied footprint internals:

  * internal footprint name
  * visible `Value` field
  * 3D model reference
  * hidden import/review metadata
* Create an edited symbol preview file.
* Update symbol names, nested KiCad unit names, and symbol `Footprint` properties.
* Resolve the correct target `.kicad_sym` file.
* Require explicit confirmation before modifying the target symbol library.
* Create a timestamped backup of the target symbol library.
* Merge the previewed symbol into the target symbol library when safety checks pass.
* Refuse duplicate footprint/model overwrites.
* Refuse duplicate symbol merges.
* Save successful run state back to config.
* Clean up temporary extraction folders when `keep_temp_files` is false.
* Print a final import summary.
* Offer to archive original source files after successful import. 
* Move archived source files into a local `_imported` folder. 
* Avoid overwriting archived source files by adding timestamped filenames when needed.

More detailed feature notes are available in [`FEATURES.md`](FEATURES.md).

Version-by-version history is available in [`VERSION_HISTORY.md`](VERSION_HISTORY.md).

Development note: active refactor planning is tracked in [`REFACTOR_PLAN.md`](REFACTOR_PLAN.md) while the debug/refactor cleanup branch is in progress.

## Basic Workflow

The current staged workflow is:

1. Select a vendor ZIP file.
2. Select the custom KiCad library root or target `.pretty` folder.
3. Resolve the target `.pretty` folder and `.kicad_sym` file.
4. Extract and scan the ZIP.
5. Suggest naming defaults.
6. Collect the manufacturer part number early.
7. Check for possible existing imports by MPN.
8. Prompt for naming tokens.
9. Generate the final basename.
10. Select source footprint, symbol, and model files.
11. Create the import plan.
12. Optionally write a preview import-plan CSV.
13. Require the user to type `COPY`.
14. Copy/rename footprint and model files.
15. Update the copied footprint.
16. Create an edited symbol preview.
17. Require the user to type `MERGE`.
18. Back up the target symbol library.
19. Merge the edited symbol into the target symbol library.
20. Save successful config state.
21. Clean up the temporary import folder when allowed.
22. Print the final import summary.

## Safety Behavior

This tool is intentionally conservative.

Before copying footprint/model files, it requires this exact confirmation:

```text
COPY
```

Before modifying a target symbol library, it requires this exact confirmation:

```text
MERGE
```

The tool currently refuses to overwrite existing footprint/model files.

Before merging a symbol, it checks whether the generated symbol already exists in the resolved target symbol library.

Before modifying a target `.kicad_sym` library, it creates a timestamped backup file.

Temp folders are deleted after successful completion when `keep_temp_files` is false. When `keep_temp_files` is true, the temp folder is preserved for review/debugging.

The tool can optionally move the original selected source files into an `_imported` archive folder after successful import.

Even with these safeguards, this is still early-development software. Back up your KiCad libraries before testing it against production libraries.

## Intended Library Structure

The project currently assumes a custom KiCad library layout similar to:

```text
CUSTOM_LIBRARIES/
├─ _testCONN.pretty/
│  ├─ *.kicad_mod
│  ├─ *.step
│  └─ _testCONN.kicad_sym
├─ _testIC.pretty/
│  ├─ *.kicad_mod
│  ├─ *.step
│  └─ _testIC.kicad_sym
└─ _TOOLS/
   └─ kicad-import-assistant/
      ├─ kicad_import_assistant.py
      ├─ kicad_import_assistant_config.json
      ├─ kicad_import_naming_schema.json
      └─ kia/
         ├─ app_info.py
         ├─ debug.py
         ├─ run_state.py
         ├─ workflow_config.py
         ├─ workflow_final.py
         ├─ workflow_footprint.py
         ├─ workflow_input.py
         ├─ workflow_naming.py
         ├─ workflow_plan.py
         ├─ workflow_schema.py
         ├─ workflow_source.py
         ├─ workflow_status.py
         ├─ workflow_symbol.py
         └─ lower-level helper modules
```

Footprints, STEP models, and the associated symbol library may be kept together inside the `.pretty` folder.

## Naming Convention

The current naming convention is:

```text
LIB_FAMILY_ROLE_MOUNT_ORIENT_SIZE[_PITCH][_BASE][_FEATURE]_MPN
```

For connector parts:

```text
CONN_FAMILY_ROLE_MOUNT_ORIENT_SIZE[_PITCH][_BASE][_FEATURE]_MPN
```

Example:

```text
CONN_HDMI_RCPT_SMD_V_19P_P0.50_SS53000_SS-53000-003
```

Where:

```text
CONN          Library/category prefix
HDMI          Connector family
RCPT          Receptacle
SMD           Surface mount
V             Vertical/top-entry
19P           19 electrical contacts
P0.50         0.50 mm pitch
SS53000       Base/series
SS-53000-003  Exact manufacturer/orderable part number
```

## JSON Files

The project uses separate JSON files for local config, naming vocabulary, and suggestion rules.

```text
kicad_import_assistant_config.example.json
```

Example local/user configuration. The real local config file is intentionally ignored by Git.

```text
kicad_import_naming_schema.json
```

Naming vocabulary, token sets, field order, normalization rules, and validation rules.

```text
kicad_import_suggestion_rules.json
```

Filename-based suggestion rules used to prefill naming fields during import.

## KiCad Compatibility

Development/testing is currently being done against a modern KiCad environment using current KiCad S-expression symbol and footprint formats.

Known state:

* Tested primarily with recent KiCad 9/10-style files and workflows.
* KiCad 8/9-style S-expression files are expected to be broadly compatible, but not guaranteed.
* KiCad 6/7 compatibility has not been tested.
* Legacy or unusual vendor file formats may require manual review or parser updates.

## Requirements

* Python 3.12 or newer
* Tkinter, included with most standard Python installs
* Windows is currently used for development/testing

No KiCad Python plugin or KiCad CLI integration is currently required.

## Running

From the repository folder:

```powershell
py kicad_import_assistant.py
```

or:

```powershell
python kicad_import_assistant.py
```

## Disclaimer

This project was vibe-coded with ChatGPT as a learning/tool-building exercise. It reflects an iterative assisted-development workflow, not a claim of independent Python expertise.

Use carefully. Back up your KiCad libraries before testing any version that modifies files.

## License

GNU General Public License v3.0
