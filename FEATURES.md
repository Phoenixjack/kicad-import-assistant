# Features

This file describes the current capabilities and known limitations of KiCad Import Assistant.

Current version: **Unreleased V0.11.0 loose-file import branch** 

Current development branch: `feature/loose-file-import`

## Import Source Handling

The tool can currently: * Select a vendor ZIP file using a GUI file picker. 
* Select a loose KiCad import file set using the same GUI file picker. 
* Validate that the selected source is either: 
	* exactly one `.zip` file 
* or a loose file set containing no more than: 
	* one `.kicad_mod` 
	* one `.kicad_sym` 
	* one `.step` or `.stp` 
* Reject invalid source selections with an error dialog and return to the picker. 
* Remember the last attempted picker folder during selection retries. 
* Remember the last successful import source folder in config as `source_folder`. 
* Extract ZIP files to a temporary folder. 
* Stage loose import files into a temporary folder. 
* Recursively detect: 
	* `.kicad_mod` 
	* `.kicad_sym` 
	* `.step` 
	* `.stp` 
* Select candidate footprint, symbol, and model files for import.

## Config Handling

The tool can:

* Load local JSON configuration.
* Save updated local JSON configuration after successful import.
* Remember:

  * last ZIP folder
  * last selected library root
  * last selected library folder
  * last target library
  * recent naming-token values
* Safely fall back when remembered folders no longer exist.
* Correct accidental selection of a `.pretty` folder as the library root.
* Respect `keep_temp_files` during final cleanup.

## Target Library Resolution

The tool can:

* Resolve the target footprint/model folder from config.
* Resolve the target `.kicad_sym` file.
* Use the configured symbol file if it exists.
* Scan the target `.pretty` folder for symbol libraries.
* Ignore backup/copy-style `.kicad_sym` files during symbol target resolution.
* Prefer a symbol library that matches the target `.pretty` folder name.

Example:

```text
_testIC.pretty
└─ _testIC.kicad_sym
```

The resolver prefers `_testIC.kicad_sym`.

## Workflow Architecture

The V0.10 refactor branch uses a staged workflow built around `run_state`.

The main script is intended to perform orchestration only. Workflow behavior is split into helper modules:

```text
kicad_import_assistant.py
kia/run_state.py
kia/workflow_config.py
kia/workflow_input.py
kia/workflow_source.py
kia/workflow_naming.py
kia/workflow_plan.py
kia/workflow_footprint.py
kia/workflow_symbol.py
kia/workflow_final.py
kia/workflow_status.py
```

The goal is to keep each workflow stage responsible for a clear section of `run_state`.

## Naming Workflow

The tool can:

* Load naming vocabulary/options from JSON schema.
* Suggest naming defaults from detected vendor filenames.
* Collect the manufacturer part number early.
* Check for possible existing imports before full naming.
* Prompt for naming tokens using schema-driven menus.
* Allow:

  * Enter to accept defaults
  * number selection from menus
  * direct token entry
  * custom/free-text values
  * explicit blanking for optional fields
* Normalize pitch tokens.
* Remember recently used naming-token values.

Current generated naming format:

```text
LIB_FAMILY_ROLE_MOUNT_ORIENT_SIZE[_PITCH][_BASE][_FEATURE]_MPN
```

Example:

```text
CONN_HDMI_RCPT_SMD_V_19P_P0.50_SS53000_SS-53000-003
```

## Preview Import Plan

The tool can optionally create a preview import-plan CSV.

The preview can show:

* source footprint file
* target footprint path
* source model file
* target model path
* source symbol file
* target symbol library path
* intended actions
* notes about pending or performed steps

The preview CSV is written into the temporary extraction folder.

## Footprint/Model Import

After explicit `COPY` confirmation, the tool can:

* Copy and rename the selected footprint file.
* Copy and rename the selected STEP/STP model file.
* Refuse to overwrite existing footprint/model files.
* Update the copied footprint internal name.
* Update the copied footprint visible `Value` field.
* Add or update a 3D model reference.
* Add hidden import/review metadata fields.
* Supports newer KiCad footprint roots using `(footprint ...)`. 
* Supports older KiCad/vendor footprint roots using `(module ...)` when updating the copied footprint internal name.

Metadata fields currently include:

```text
ImportedBy
ImportStatus
Needs3DModelValidation
```

The tool supports both newer KiCad property syntax and older/vendor unquoted footprint syntax in several common cases.

## Symbol Preview

The tool can create a temporary edited symbol preview file.

The preview can:

* Rename the parent symbol.
* Rename nested KiCad symbol unit names.
* Update the symbol `Footprint` property.
* Add hidden import/review metadata to the parent symbol.
* Preserve the original source symbol file.
* Write the edited preview symbol into the temporary extraction folder.

This preview step happens before the real target symbol library is modified.

## Symbol Merge

After explicit `MERGE` confirmation, the tool can merge the previewed symbol into the resolved target `.kicad_sym` library.

Before merging, the tool:

* Confirms that a target symbol library was resolved.
* Confirms that the target symbol library exists.
* Checks whether the generated symbol name already exists.
* Refuses duplicate symbol merges.
* Creates a timestamped backup of the target symbol library.

The merge inserts the edited symbol block into the target symbol library before the final library closing parenthesis.

## Backup Behavior

Before modifying a target symbol library, the tool creates a timestamped backup.

Backup filenames intentionally do not end with `.kicad_sym` so the resolver does not mistake them for active KiCad symbol libraries.

Example:

```text
_testIC.kicad_sym.20260623_192658.backup
```

## Finalization and Cleanup

After successful import, the tool can:

* Save successful run values back to config.
* Save recent naming-token values.
* Delete the temporary extraction folder when `keep_temp_files` is false.
* Preserve the temporary extraction folder when `keep_temp_files` is true.
* Print a final import summary.


## Source File Cleanup

After a successful loose-file import, the tool can optionally move the original selected source files into an archive folder.

Current behavior:

* Applies only to loose-file imports.
* Does not apply to ZIP imports.
* Prompts the user after successful import.
* Defaults to `N`.
* Moves files into an `_imported` folder beside the original source files.
* Avoids overwriting existing archived files by adding a timestamp when needed.
* Leaves files in place when the user declines.

Example:

```text
kia_testing/
├─ SS-53000-003.kicad_mod
├─ SS-53000-003.kicad_sym
├─ SS-53000-003.step
└─ _imported/
   ├─ SS-53000-003.20260625_133138.kicad_mod
   ├─ SS-53000-003.20260625_133138.kicad_sym
   └─ SS-53000-003.20260625_133138.step
````

Source cleanup is intentionally conservative. It moves files to an archive folder; it does not permanently delete them.


## Debug Output

The tool has a lightweight developer/debug output system.

Debug messages can be filtered by:

* severity
* category
* optional workflow stage
* optional source/module label

Current severity levels:

```text
ERROR
WARNING
INFO
VERBOSE
```

Normal output is intentionally limited to user decisions, safety confirmations, warnings/errors, import-plan review, config-save status, and the final import summary. Detailed stage diagnostics are routed through `dbg_print()` and can be enabled by debug category when needed.

## Current Limitations

The tool currently does not:

* permanently delete imported source files
* archive ZIP sources after import
* import from a loose folder of files
* perform partial imports intentionally
* link an existing symbol to a newly imported footprint
* link an existing 3D model to a newly imported footprint
* overwrite existing footprint/model files
* overwrite existing symbol definitions
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

* Continue polishing normal/debug output boundaries as new workflow stages are added.
* Add partial import support.
* Add workflows for linking existing symbols/models to newly imported footprints.

## Future Metadata Enrichment Goals

Future versions may add optional online metadata enrichment.

The intended workflow would be:

1. Detect or ask for a manufacturer part number.
2. Query one or more configured metadata providers.
3. Present the best candidate match to the user.
4. Allow the user to accept, reject, or manually override the result.
5. Use accepted metadata to prefill naming fields and symbol properties.
6. Ask manual questions only for fields that could not be confidently inferred.

Possible metadata sources may include provider APIs such as Nexar/Octopart, DigiKey, Mouser, SnapMagic/SnapEDA, or other structured part-data services.

Metadata enrichment should remain optional. The core importer should continue working offline from local files alone.

External metadata should be treated as a suggestion requiring user review, not as unquestioned truth. Geometry, pin mapping, footprint correctness, 3D model orientation, and schematic correctness should still require human validation.

