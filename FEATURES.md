# Features

This file describes the current capabilities and known limitations of KiCad Import Assistant.

Current version: **Unreleased V0.15.0 public/private config split branch**

Current development branch: `feature/split-public-private-config`

## Import Source Handling

The tool can currently:

* Select a vendor ZIP file using a GUI file picker.
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
* Remember the last successful import source folder in private data as `last.source_folder`.
* Use the same remembered source folder for ZIP imports and loose-file imports.

## Config Handling

The tool now separates public defaults from local/private data.

Tracked public files:
```text
kicad_import_assistant_default_config.json
kicad_import_private_data.example.json
```

Ignored private/local file:
```text
kicad_import_private_data.json
```

The runtime config is loaded in layers:
```text
Python fallback defaults
  -> tracked public default config
    -> ignored private data
```

Private/local data wins over public defaults.

The public default config is intended for factory-safe behavior only. It should not contain:
* local paths
* user-specific library profiles
* recent naming values
* API keys
* secrets

The private data file may contain:
* `last.source_folder`
* `last.library_root`
* `last.library_folder`
* `last.target_library`
* `path_variable`
* `libraries`
* `recent_values`
* `api_integrations.keys`

Successful imports save updated local state only to `kicad_import_private_data.json`.

The tracked public default config is not modified during normal imports.

The importer uses `last.source_folder` as the canonical remembered import-source folder for both ZIP imports and loose-file imports.

The older ZIP-only `zip_folder` key is no longer part of the active config contract.

The importer uses `last.target_library` as the canonical remembered target-library key.

The older ambiguous `last.profile` key is no longer part of the active config contract. Library-specific naming behavior belongs in each library entry’s `schema_profile` value.

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

The tool uses a staged workflow built around `run_state`.

The main script is intended to perform orchestration only. Workflow behavior is split into helper modules:
```text
kicad_import_assistant.py
kia/run_state.py
kia/workflow_config.py
kia/workflow_execution.py
kia/workflow_input.py
kia/workflow_source.py
kia/workflow_naming.py
kia/workflow_plan.py
kia/workflow_footprint.py
kia/workflow_symbol.py
kia/workflow_final.py
kia/workflow_source_cleanup.py
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

## Per-Item Import Actions

The importer can let the user keep or skip individual planned import actions before target-library writes occur.

Supported per-item choices:
* import or skip footprint
* import or skip 3D model
* merge or skip symbol

Skipped items are marked as `SKIPPED_BY_USER` in the import plan and are ignored by later workflow stages.

Current behavior:
* Existing footprint/model targets are detected during action selection.
* Overwrite is not supported yet.
* Existing footprint/model targets can be skipped safely.
* Skipped items are excluded from the preview manifest.
* Skipped loose source files are not archived after import.
* Final import summary reports skipped items correctly.
* Skip-all exits cleanly before target-library writes.
* The selected-actions confirmation summarizes what will run before writes occur.

This allows workflows such as:
* import footprint and symbol, skip model
* import footprint and model, skip symbol
* merge symbol only
* import model only
* skip an already-existing footprint while importing the matching model and symbol
* skip all planned actions and exit cleanly before writes

## Selected-Actions Execution Confirmation

After per-item action selection and import-plan review, the tool shows one final selected-actions confirmation.

The confirmation summarizes:
* footprint action
* model action
* symbol action
* source paths for selected actions
* target paths for selected actions
* safety behavior

The final prompt is:
```text
Proceed with selected actions? [y/N]:
```

If the user declines, the workflow stops before:
* footprint/model copy
* copied-footprint update
* symbol backup
* symbol merge
* config save
* temp cleanup
* final summary
* source archive prompt

This replaces the older separate `COPY` and `MERGE` hard prompts.

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

The preview CSV is written into the temporary extraction/staging folder.

Skipped items are excluded from the preview manifest.

Model target paths preserve the selected model extension, so `.step` and `.stp` source files preview with matching destination suffixes.

## Footprint/Model Import

After final selected-actions confirmation, when footprint/model copy actions remain, the tool can:
* Copy and rename the selected footprint file.
* Copy and rename the selected STEP/STP model file.
* Refuse to overwrite existing footprint/model files.
* Update the copied footprint internal name.
* Update the copied footprint visible `Value` field.
* Add or update a 3D model reference when a model was copied.
* Avoid adding a 3D model reference when the model was skipped.
* Add hidden import/review metadata fields.
* Support newer KiCad footprint roots using `(footprint ...)`.
* Support older KiCad/vendor footprint roots using `(module ...)` when updating the copied footprint internal name.

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
* Write the edited preview symbol into the temporary extraction/staging folder.
* Populate symbol merge state for the later backup and merge stages.

This preview step happens before the real target symbol library is modified.

If the symbol import action is skipped, symbol preview, symbol backup, and symbol merge are skipped.

## Symbol Merge

After final selected-actions confirmation, when a symbol merge action remains, the tool can merge the previewed symbol into the resolved target `.kicad_sym` library.

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
* Delete the temporary extraction/staging folder when `keep_temp_files` is false.
* Preserve the temporary extraction/staging folder when `keep_temp_files` is true.
* Print a final import summary.

The final import summary reports skipped footprint/model/symbol actions accurately.

## Source File Cleanup
After a successful import, the tool can optionally move original source files into an archive folder.

Current behavior:

* Applies to ZIP imports when ZIP source archiving is enabled.
* Applies to loose-file imports when loose-file source archiving is enabled.
* Prompts the user after successful import.
* Defaults to `N`.
* Moves files into an `_imported` folder beside the original source files.
* Avoids overwriting existing archived files by adding a timestamp when needed.
* Leaves files in place when the user declines.
* Archives only original source files, not temporary staged/extracted files.
* For loose-file imports, archives only source files whose corresponding import action actually ran.
* For loose-file imports, skipped source files are left in place.

Example loose-file cleanup:
```text
kia_testing/
├─ SS-53000-003.kicad_mod
├─ SS-53000-003.kicad_sym
├─ SS-53000-003.step
└─ _imported/
   ├─ SS-53000-003.20260625_133138.kicad_mod
   ├─ SS-53000-003.20260625_133138.kicad_sym
   └─ SS-53000-003.20260625_133138.step
```

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

Normal output is intentionally limited to user decisions, safety confirmations, warnings/errors, import-plan review, config-save status, archive prompts, and the final import summary. Detailed stage diagnostics are routed through `dbg_print()` and can be enabled by debug category when needed.

## Current Limitations

The tool currently does not:
* clear stale footprint 3D model references when model import is skipped
* clear stale symbol Footprint properties when footprint import is skipped
* permanently delete imported source files
* import from a loose folder of files
* overwrite existing footprint/model files
* overwrite existing symbol definitions
* replace existing symbol definitions
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