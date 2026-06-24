# Features

This file describes the current capabilities and known limitations of KiCad Import Assistant.

Current version: **Unreleased V0.10.0 refactor branch**

Branch: `refactor-debug-cleanup`

## Import Source Handling

The tool can currently:

* Select a vendor ZIP file using a GUI file picker.
* Extract the ZIP file to a temporary folder.
* Recursively detect:

  * `.kicad_mod`
  * `.kicad_sym`
  * `.step`
  * `.stp`
* Summarize detected import files.
* Select candidate footprint, symbol, and model files for import.

Current limitation:

* Loose-file imports are not active yet.
* Folder imports are not active yet.
* Current active path is still vendor ZIP import.

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

Future work will continue moving normal runtime chatter behind `dbg_print()` so normal output becomes shorter while debug output remains available when needed.

## Current Limitations

The tool currently does not:

* import loose `.kicad_sym`, `.kicad_mod`, `.step`, or `.stp` files directly
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

* Reduce normal output verbosity.
* Move additional diagnostic output behind `dbg_print()`.
* Add loose-file import support.
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

