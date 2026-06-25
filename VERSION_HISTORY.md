# Version History

## Unreleased - V0.12.0 Archive Imported Source Files

Feature branch: `feature/archive-imported-source-files`

Adds optional post-import archiving for import sources.

Changes:

* Adds optional archive prompt after successful imports.
* Moves original selected source files into an `_imported` archive folder when the user confirms.
* Defaults the archive prompt to `N` so source files are not moved by accidental Enter.
* Avoids overwriting archived source files by adding a timestamp when the destination filename already exists.
* Records archived, skipped, and failed source-cleanup files in `run_state`.
* Keeps source cleanup separate from the core import result; a source archive issue does not retroactively fail a successful import.

Tested:

* Import with archive declined leaves source files in place.
* Import with archive accepted moves source files into `_imported`.
* Archive filename collision uses timestamped destination filenames.
* Missing source file during archive is skipped without critical failure.

Current limitations:

* Source cleanup does not hard-delete files.


## Unreleased - V0.11.0 Loose-File Import Branch

Feature branch: `feature/loose-file-import`

Adds loose-file import source selection while preserving the existing ZIP import workflow.

Changes:

* Adds unified import-source file picker.
* Allows selecting either:
  * exactly one vendor ZIP file
  * or one loose KiCad import file set
* Supports loose file sets containing up to:
  * one `.kicad_mod`
  * one `.kicad_sym`
  * one `.step` or `.stp`
* Rejects invalid source selections before import:
  * ZIP mixed with loose files
  * multiple ZIP files
  * multiple footprint files
  * multiple symbol files
  * multiple model files
  * unsupported file extensions
* Reopens the source picker in the last attempted folder after invalid source selection.
* Adds `source_folder` config tracking for the last successful import source folder.
* Stages loose source files into a temporary import folder so the existing downstream import workflow can process them.
* Keeps ZIP import behavior intact.
* Adds support for older KiCad/vendor footprint roots using `(module ...)` when updating copied footprint internal names.
* Confirms ZIP import path still passes.
* Confirms loose footprint/symbol/model import path passes.
* Confirms invalid source-selection tests pass.

Current limitations:

* Loose folder import is not active yet.
* Partial imports are not active yet.
* Per-item overwrite/merge/import decisions are not active yet.
* Source-file cleanup/deletion after successful import is not active yet.
* Missing target symbol library auto-creation is not active yet.


## Unreleased - V0.10.1 Refactor Branch

Breaking refactor work in progress on the `refactor/quiet-normal-output` branch.

This branch refactors the importer around a staged `run_state` workflow and splits many workflow-stage functions out of `kicad_import_assistant.py`.

Current status:

* `python -m compileall` passes.

Completed in this branch so far:

* Reduces normal workflow output by moving successful stage-detail chatter behind `dbg_print()`. 
* Keeps prompts, confirmations, warnings/errors, import-plan review, config-save status, and final summary visible. 
* Reclassifies duplicate target-file overwrite protection as a controlled warning stop instead of a critical error. 
* Fixes final summary symbol reporting so successfully merged symbols are not displayed as `SKIPPED`. 
* Updates debug label width to 9 characters to reduce truncation while keeping debug prefixes compact.
* Adds `kia/run_state.py`.
* Adds `initialize_run_state()` as the central per-import workflow state initializer.
* Adds staged status handling through `kia/workflow_status.py`.
* Adds workflow status helpers:

  * `mark_success()`
  * `mark_failure()`
  * `stop_if_failed()`
  * `graceful_stop()`
  * `critical_error()`
* Refactors `kicad_import_assistant.py` toward orchestration-only behavior.
* Splits workflow stages into helper modules:

  * `kia/workflow_config.py`
  * `kia/workflow_input.py`
  * `kia/workflow_source.py`
  * `kia/workflow_naming.py`
  * `kia/workflow_plan.py`
  * `kia/workflow_footprint.py`
  * `kia/workflow_symbol.py`
  * `kia/workflow_final.py`
  * `kia/workflow_schema.py`
* Adds `kia/app_info.py` for shared application version metadata.
* Restores the full staged ZIP import path after the initial refactor split.
* Adds early MPN collection before full naming.
* Adds duplicate/previous-import warning based on early MPN search.
* Updates basename generation to reuse the early-collected MPN.
* Adds staged import-plan creation.
* Adds optional preview import-plan CSV creation.
* Changes file-copy confirmation from older `IMPORT` confirmation to explicit `COPY`.
* Adds staged footprint/model copy and rename behavior.
* Adds copied-footprint content update stage.
* Updates copied footprint:

  * internal footprint name
  * visible `Value` field
  * 3D model reference
  * hidden import metadata
* Adds staged symbol preview generation.
* Updates preview symbol:

  * parent symbol name
  * nested KiCad unit names
  * `Footprint` property
  * hidden import metadata
* Fixes symbol metadata placement so metadata is added to the parent symbol, not nested drawing/unit symbol blocks.
* Changes symbol-library modification confirmation from older `IMPORT` confirmation to explicit `MERGE`.
* Adds target symbol library backup before merge.
* Adds staged symbol preview merge into the target `.kicad_sym` library.
* Adds finalization state.
* Adds successful config-save stage.
* Adds temp-folder cleanup stage.
* Changes cleanup behavior so `keep_temp_files` is the sole preservation control.
* Adds final import summary stage.
* Sets `run_state["was_successful"]` after full successful completion.
* Fixes finalization `run_state` nesting error.
* Adds defensive `ensure_finalization_state()`.
* Repairs workflow-module dependency/import issues after splitting the monolithic script.
* Confirms the refactored module split compiles with `python -m compileall`.

Current intentional limitations:

* Loose-file imports are not active yet.
* Partial imports are not active yet.
* Existing-symbol/existing-model linking workflows are not active yet.

Breaking changes:

* This branch no longer preserves backward compatibility with the older flat `last_*` config keys as the primary config structure.
* The config structure is moving toward a nested `config["last"]` object.
* `run_state` is now the intended runtime data structure for workflow state and staged status reporting.
* Confirmation prompts are now stage-specific:

  * `COPY` for footprint/model copy writes
  * `MERGE` for symbol-library modification


## V0.9.0

Major milestone: first real symbol-library merge.

Changes:

* Adds safe symbol merge into the resolved target `.kicad_sym` library.
* Extracts the edited symbol block from the temporary preview symbol file.
* Inserts the previewed symbol into the target symbol library after `IMPORT` confirmation.
* Requires symbol merge precheck to pass before merging.
* Creates a timestamped target symbol library backup before merging.
* Refuses duplicate symbol merges when the generated symbol name already exists.
* Updates nested KiCad symbol unit names when renaming symbols.
* Fixes overwrite protection messaging so duplicate footprint/model imports fail cleanly.
* Updates documentation for the new symbol merge workflow.

## V0.8.2

Target symbol resolution cleanup.

Changes:

* Changes symbol backup filenames so backups no longer end with `.kicad_sym`.
* Filters backup-looking symbol files during target symbol resolution.
* Prefers a symbol library matching the target `.pretty` folder name.
* Reduces ambiguity when backup, copied, or extra symbol files are present.
* Keeps symbol merge disabled at this stage.

## V0.8.1

Symbol merge precheck and backup checkpoint.

Changes:

* Adds symbol merge precheck against the resolved target `.kicad_sym` file.
* Detects whether the target symbol library already contains the generated symbol name.
* Creates a timestamped backup of the target symbol library after `IMPORT` confirmation.
* Reports symbol precheck and backup status in final import summary.
* Keeps real symbol merge disabled at this stage.

## V0.8.0

Symbol integration preview.

Changes:

* Adds temporary symbol preview generation.
* Updates source symbol name in preview files.
* Updates symbol `Footprint` property in preview files.
* Reports symbol preview status in final import summary.
* Keeps target `.kicad_sym` libraries unchanged.

## V0.7.1

Accurate final import status.

Changes:

* Adds import result flags for copied files and footprint updates.
* Reports whether footprint internal name was updated.
* Reports whether footprint `Value` field was updated.
* Reports whether 3D model reference was added or updated.
* Reports whether import metadata is present.
* Keeps symbol merge status explicit as not implemented at this stage.
* Improves final status output so it reports what actually happened.

## V0.7.0

Schema-driven token menus.

Changes:

* Loads naming schema from `kicad_import_naming_schema.json`.
* Adds numbered token menus for:

  * library prefix
  * family
  * role
  * mount
  * orientation
  * pitch
* Allows Enter to accept defaults.
* Allows direct token entry and free-text custom values.
* Uses resolved symbol path in preview manifests.
* Updates stale preview manifest notes.

## V0.6.2

Target symbol file resolution.

Changes:

* Adds target symbol file resolution helper.
* Uses configured symbol file when present.
* Falls back to scanning the target `.pretty` folder for one `.kicad_sym` file.
* Reports symbol resolution status in selected import settings.
* Adds a symbols debug category.

## V0.6.1

Import metadata and recent defaults.

Changes:

* Adds hidden import/review metadata fields to copied footprints.
* Records importer version in the copied footprint.
* Adds app version reporting to diagnostic output.
* Remembers recently used naming-token values such as orientation and pitch.

## V0.6.0

Copied footprint internals.

Changes:

* Updates copied footprint internal name.
* Adds or updates copied footprint 3D model path.
* Supports older/unquoted vendor footprint naming syntax.
* Adds a default 3D model block when the source footprint has no model block.

## V0.5.1

Safer copy workflow polish.

Changes:

* Adds/adjusts duplicate MPN detection.
* Improves pitch normalization.
* Continues refusing overwrite of existing target files.
* Keeps symbol handling preview-only.

## V0.5.0

First copy/rename workflow.

Changes:

* Adds hard-confirmed import workflow.
* Copies and renames selected footprint files.
* Copies and renames selected STEP/STP model files.
* Requires exact `IMPORT` confirmation before copying.
* Refuses to overwrite existing target files.
* Does not edit footprint internals yet.
* Does not merge symbols.

## V0.4.0

Preview manifest workflow.

Changes:

* Prompts for naming tokens.
* Generates proposed basename.
* Generates target filenames.
* Writes a preview manifest CSV.
* Does not copy, rename, or edit library files.

## Earlier V0.1–V0.3 Milestones

Early prototype stages included:

* GUI ZIP file picker.
* GUI library root folder picker.
* JSON config loading/saving.
* Remembering last selected paths.
* Extracting ZIPs to temporary folders.
* Detecting KiCad footprint, symbol, and 3D model files.
