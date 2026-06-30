# KiCad Import Assistant

KiCad Import Assistant is a standalone Python utility for importing vendor-provided KiCad footprints, symbols, and 3D models into a custom KiCad library structure.

The tool is designed around a cautious workflow: preview first, review planned actions, confirm selected writes, create backups where needed, and refuse unsafe overwrites.

**Unreleased V0.14.0 simplify execution confirmation branch**

Current development branch: `feature/simplify-execution-confirmation`

## V0.14 simplify execution confirmation branch note

The `feature/simplify-execution-confirmation` branch replaces the older separate `COPY` and `MERGE` hard-confirmation prompts with one final selected-actions confirmation.

The user still chooses individual footprint/model/symbol actions first. After the import plan is reviewed, the tool prints a final summary of the selected actions and asks:

```text
Proceed with selected actions? [y/N]:
```

This keeps one final safety gate while removing redundant prompts after per-item action approval.

## What It Does

KiCad Import Assistant can currently:

* Select either a vendor ZIP file or a loose KiCad import file set.
* Validate import-source selections before staging:
  * one ZIP file only
  * or one footprint, one symbol, and one model file at most
* Remember the last successful import source folder as `source_folder`.
* Stage loose import files into a temporary import folder so the normal downstream workflow can process them.
* Extract vendor ZIP files into a temporary import folder.
* Detect KiCad footprint, symbol, and STEP/STP model files.
* Support older KiCad/vendor footprint roots using `(module ...)` as well as newer `(footprint ...)` roots.
* Suggest naming defaults from detected files.
* Prompt for naming tokens using schema-driven menus.
* Generate standardized footprint/symbol/model basenames.
* Detect possible existing imports by early MPN search.
* Create an import plan.
* Review planned footprint, model, and symbol actions before import.
* Skip individual footprint, model, or symbol actions before target-library writes.
* Avoid duplicate target writes by skipping existing footprint/model targets.
* Create and optionally write a preview import-plan CSV.
* Exclude skipped items from the preview import-plan CSV.
* Preserve `.step` and `.stp` model suffixes in preview manifest target paths.
* Show one final selected-actions confirmation before target-library writes.
* Copy and rename selected footprint/model files into a target `.pretty` folder.
* Update copied footprint internals:
  * internal footprint name
  * visible `Value` field
  * 3D model reference when a model was copied
  * hidden import/review metadata
* Create an edited symbol preview file when a symbol merge action is selected.
* Update symbol names, nested KiCad unit names, and symbol `Footprint` properties.
* Resolve the correct target `.kicad_sym` file.
* Create a timestamped backup of the target symbol library before symbol merge.
* Merge the previewed symbol into the target symbol library when safety checks pass.
* Refuse duplicate footprint/model overwrites.
* Refuse duplicate symbol merges.
* Save successful run state back to config.
* Clean up temporary extraction/staging folders when `keep_temp_files` is false.
* Print a final import summary.
* Report skipped footprint/model/symbol actions accurately in the final import summary.
* Offer to archive original source files after successful import.
* Move archived source files into a local `_imported` folder.
* Archive only the original source files that were actually imported or merged.
* Avoid overwriting archived source files by adding timestamped filenames when needed.

More detailed feature notes are available in [`FEATURES.md`](FEATURES.md).

Version-by-version history is available in [`VERSION_HISTORY.md`](VERSION_HISTORY.md).

Development note: active refactor planning is tracked in [`REFACTOR_PLAN.md`](REFACTOR_PLAN.md`.

## Basic Workflow

The current staged workflow is:
1. Select a vendor ZIP file or loose KiCad import file set.
2. Select the custom KiCad library root or target `.pretty` folder.
3. Resolve the target `.pretty` folder and `.kicad_sym` file.
4. Extract or stage the selected import source.
5. Detect footprint, symbol, and model source files.
6. Select candidate source footprint, symbol, and model files.
7. Suggest naming defaults.
8. Collect the manufacturer part number early.
9. Check for possible existing imports by MPN.
10. Prompt for naming tokens.
11. Generate the final basename.
12. Create the import plan.
13. Choose per-item import actions:
    * footprint import or skip
    * model import or skip
    * symbol merge or skip
14. Optionally write a preview import-plan CSV.
15. Show one final selected-actions confirmation.
16. Stop before writes if the user declines final confirmation.
17. Copy/rename selected footprint and/or model files.
18. Update the copied footprint when a footprint was imported.
19. Create an edited symbol preview when a symbol merge was selected.
20. Back up the target symbol library when a symbol merge was selected.
21. Merge the edited symbol into the target symbol library.
22. Save successful config state.
23. Clean up the temporary import folder when allowed.
24. Print the final import summary.
25. Optionally archive original source files that correspond to actions that actually ran.

## Safety Behavior

This tool is intentionally conservative.

Per-item skip actions allow the user to skip individual footprint, model, or symbol operations before writing to the target library.

Existing footprint/model targets are not overwritten in this version. When an existing footprint/model target is detected, the user can skip that item or stop the run.

Before any selected target-library writes occur, the tool prints a final selected-actions summary and asks:

```text
Proceed with selected actions? [y/N]:
```

Declining this final confirmation stops the workflow before footprint/model copy, symbol backup, symbol merge, config save, temp cleanup, final summary, and source archiving.

The tool currently refuses to overwrite existing footprint/model files.

Before merging a symbol, it checks whether the generated symbol already exists in the resolved target symbol library.

Before modifying a target `.kicad_sym` library, it creates a timestamped backup file.

Temp folders are deleted after successful completion when `keep_temp_files` is false. When `keep_temp_files` is true, the temp folder is preserved for review/debugging.

The tool can optionally move original selected source files into an `_imported` archive folder after successful import.

For loose-file imports, skipped source files are not archived. Only original source files corresponding to actions that actually ran are offered for archive.

Even with these safeguards, this is still early-development software. Back up your KiCad libraries before testing it against production libraries.

## Intended Library Structure

The project currently assumes a custom KiCad library layout similar to:

```text
CUSTOM_LIBRARIES/
├─ _testCONN.pretty/
│  ├─ *.kicad_mod
│  ├─ *.step
│  ├─ *.stp
│  └─ _testCONN.kicad_sym
├─ _testIC.pretty/
│  ├─ *.kicad_mod
│  ├─ *.step
│  ├─ *.stp
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
         ├─ workflow_execution.py
         ├─ workflow_final.py
         ├─ workflow_footprint.py
         ├─ workflow_input.py
         ├─ workflow_naming.py
         ├─ workflow_plan.py
         ├─ workflow_schema.py
         ├─ workflow_source.py
         ├─ workflow_source_cleanup.py
         ├─ workflow_status.py
         ├─ workflow_symbol.py
         └─ lower-level helper modules
```

Footprints, STEP/STP models, and the associated symbol library may be kept together inside the `.pretty` folder.

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

## Current Limitations

The tool currently does not:
* permanently delete imported source files
* import from a loose folder of files
* overwrite existing footprint/model files
* overwrite or replace existing symbol definitions
* perform per-item overwrite/replace actions
* auto-create missing target symbol libraries
* link an existing symbol to a newly imported footprint
* link an existing 3D model to a newly imported footprint
* guarantee that symbol `Footprint` properties point to an already-existing footprint when the footprint action is skipped
* perform full KiCad S-expression validation
* guarantee 3D model orientation
* validate all pad/pin/schematic correctness
* guarantee compatibility with all KiCad versions
* provide a full GUI configuration workflow
* operate as a native KiCad plugin
* query online part databases or distributor APIs
* enrich part metadata from manufacturer part numbers
* auto-suggest naming fields from verified external part data

Human review is still required.

## Near-Term Goals

Planned near-term work:
* Add missing target symbol library creation.
* Add per-item overwrite/replace actions with explicit backup behavior.
* Add workflows for linking existing symbols/models to newly imported footprints.
* Continue polishing normal/debug output boundaries as new workflow stages are added.

## Disclaimer

This project was vibe-coded with ChatGPT as a learning/tool-building exercise. It reflects an iterative assisted-development workflow, not a claim of independent Python expertise.

Use carefully. Back up your KiCad libraries before testing any version that modifies files.

## License

GNU General Public License v3.0