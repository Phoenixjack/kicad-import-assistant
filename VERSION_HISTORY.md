# Version History

## Unreleased - V0.20.5 Destination Alignment

Feature branch: `feature/main-gui-import-workflow`

Aligns the GUI Import workflow around destination selection while preserving the existing private-data shape.

Changes:
* Adds a Destination selector to the Import tab.
* Hides the generated-name `library` token from Configure Base Name so it is not confused with the selected destination.
* Derives the basename prefix from the selected destination's private-data settings.
* Derives output preview paths from the selected destination instead of only the last saved target.
* Reframes GUI-facing profile language as import destinations.
* Removes last-used source and default output folder fields from the standalone GUI Config tab while preserving their private-data keys.
* Keeps the existing `libraries` private-data structure and CLI behavior unchanged.
* Bumps app version to `0.20.5`.

Tested:
* `python -m py_compile kicad_import_assistant.py` passes.
* `python -m py_compile kicad_import_assistant_gui.py` passes.
* `python -m compileall -f -q kia kicad_import_assistant.py kicad_import_assistant_gui.py` passes.

Current limitations:
* Destination selection updates GUI preview state only.
* GUI import execution is not wired yet.

## Unreleased - V0.20.4 Import Tab Static Workflow

Feature branch: `feature/main-gui-import-workflow`

Replaces the Import tab placeholders with a non-destructive static workflow preview.

Changes:
* Adds an Import Source section with file selection, clear selection, and selected item status rows.
* Adds schema-driven naming controls and generated base-name preview.
* Moves MPN to the top of the naming area with a disabled API Lookup placeholder.
* Labels the schema `size` field as Pin Count in the GUI.
* Shows recognized filenames inside selected ZIP files without extracting them.
* Clears dependent naming fields except MPN when the selected library changes.
* Enables Reset Import when the static import preview has unsaved work.
* Adds a static Import Actions table for symbol, footprint, and 3D model rows.
* Adds output preview and validation summary text for selected files and required naming fields.
* Keeps actual import execution disabled for this milestone.
* Bumps app version to `0.20.4`.

Tested:
* `python -m py_compile kicad_import_assistant.py` passes.
* `python -m py_compile kicad_import_assistant_gui.py` passes.
* `python -m compileall -f -q kia kicad_import_assistant.py kicad_import_assistant_gui.py` passes.

Current limitations:
* Import source selection only updates GUI preview state.
* GUI import execution is not wired yet.

## Unreleased - V0.20.3 Schema Read-Only Tab

Feature branch: `feature/main-gui-import-workflow`

Turns the GUI Schema tab into a read-only browser for naming-schema data.

Changes:
* Loads `kicad_import_naming_schema.json` into the GUI Schema tab.
* Adds library, token-set, and text search filters.
* Shows schema metadata, field order, required fields, optional fields, and selected-library hints.
* Shows global token sets, per-library families, and per-library token overrides in a read-only table.
* Routes schema load failures through the GUI logger/status strip.
* Creates missing private data from `kicad_import_private_data.example.json` when the GUI starts.
* Adds vertical scrolling to all main tabs so smaller window heights remain usable.
* Bumps app version to `0.20.3`.

Tested:
* `python -m py_compile kicad_import_assistant.py` passes.
* `python -m py_compile kicad_import_assistant_gui.py` passes.
* `python -m compileall -f -q kia kicad_import_assistant.py kicad_import_assistant_gui.py` passes.

Current limitations:
* Schema editing is intentionally disabled.
* GUI import execution is not wired yet.

## Unreleased - V0.20.2 Config Tab

Feature branch: `feature/main-gui-import-workflow`

Turns the GUI Config tab into a draft editor for ignored private data.

Changes:
* Replaces Config-tab path placeholders with editable `last.*` path fields, target library selection, and path variable editing.
* Adds library-profile list editing with add, duplicate, delete, and per-profile detail fields.
* Adds storage-only API key editing for configured API integrations.
* Saves Config-tab changes only when `Save Config` is pressed.
* Reverts unsaved Config-tab changes from the last saved private-data state.
* Persists GUI logging settings in the private data `gui.logging` section.
* Bumps app version to `0.20.2`.

Tested:
* `python -m py_compile kicad_import_assistant.py` passes.
* `python -m py_compile kicad_import_assistant_gui.py` passes.
* `python -m compileall -f -q kia kicad_import_assistant.py kicad_import_assistant_gui.py` passes.

Current limitations:
* API keys are stored only; lookup workflows are not wired yet.
* GUI import execution is not wired yet.

## Unreleased - V0.20.1 Logging and Diagnostics

Feature branch: `feature/main-gui-import-workflow`

Expands the parallel GUI shell with functional logging and diagnostics controls.

Changes:
* Wires Config-tab diagnostics controls into draft settings that apply only when `Save Config` is pressed.
* Adds optional JSON-lines file logging to `logs/kia-current.log`.
* Adds size-based log rotation to timestamped `logs/kia-YYYYMMDD-HHMMSS.log` files.
* Adds retention handling for current-session-only, last 3 logs, and last 7 logs.
* Adds local-path redaction for copied/exported diagnostics and optional file logging.
* Expands the log viewer with severity, category, function, and text filters.
* Adds Copy Filtered and Open Log Folder actions to the log viewer.
* Keeps status-strip messages capped for compact display.
* Saves and restores GUI window size, position, and maximized state through ignored private data.
* Bumps app version to `0.20.1`.

Tested:
* `python -m py_compile kicad_import_assistant.py` passes.
* `python -m py_compile kicad_import_assistant_gui.py` passes.
* `python -m compileall -f -q kia kicad_import_assistant.py kicad_import_assistant_gui.py` passes.
* `git diff --check` passes.
* Non-GUI logger helper check passes for filtering, truncation, and temp-folder file logging.
* GUI window-geometry helper check passes for valid/invalid geometry handling.

Current limitations:
* GUI import execution is not wired yet.

## Unreleased - V0.20.0 Main GUI Shell

Feature branch: `feature/main-gui-import-workflow`

Starts the parallel Tkinter GUI workflow while keeping the existing CLI launcher intact.

Changes:
* Adds `kicad_import_assistant_gui.py` as a separate GUI launcher.
* Adds `kia/gui_app.py` for the main Tkinter window shell.
* Adds `kia/gui_state.py` for GUI/session state separate from per-import `run_state`.
* Adds `kia/gui_log.py` for in-memory GUI log entries and status-strip routing.
* Adds Import, Config, and Schema tabs.
* Adds persistent status/action bar with dynamic primary/reset labels.
* Adds persistent `View Log` button.
* Adds log viewer popup with severity filtering.
* Adds initial Diagnostics / Logging controls placeholder on the Config tab.
* Adds `logs/` to `.gitignore` for later file logging.
* Bumps app version to `0.20.0`.

Tested:
* `python -m py_compile kicad_import_assistant.py` passes.
* `python -m py_compile kicad_import_assistant_gui.py` passes.
* `python -m compileall -f -q kia kicad_import_assistant.py kicad_import_assistant_gui.py` passes.
* `git diff --check` passes.

Current limitations:
* GUI import execution is not wired yet.
* Config tab controls are placeholders except for initial logging-control layout.
* Schema tab is a read-only placeholder.
* File logging is not active yet; current GUI logging is in-memory only.

Planned V0.20.x follow-up:
* V0.20.1: Logging and diagnostics.
* V0.20.2: Config tab.
* V0.20.3: Schema read-only tab.
* V0.20.4: Import tab static workflow.
* V0.20.5: Target library alignment.
* V0.20.6: Source selection and naming preview.
* V0.20.7: Import action planning.
* V0.20.8: CLI prompt retirement pass.
* V0.20.9: Polish and stabilization.

## Unreleased - V0.19.0 Private Data Config Dialog

Feature branch: `feature/private-data-config-dialog`

Adds a startup Tkinter dialog for reviewing and editing core private/local config before the import workflow begins.

Changes:
* Adds `kia/config_dialog.py`.
* Opens a private-data config dialog after config files load and before source-file selection.
* Allows editing startup paths, selected target library, and KiCad path variable.
* Shows a read-only summary of the selected library profile.
* Saves dialog changes only to `kicad_import_private_data.json`.
* Allows continuing without saving or canceling startup.
* Offers to create missing private data from `kicad_import_private_data.example.json`.
* Reloads merged runtime config after dialog save.
* Keeps public defaults, naming schema, and suggestion rules read-only for this branch.
* Brings the startup dialog forward on Windows console launches.
* Bumps app version to `0.19.0`.

Tested:
* `python -m py_compile kicad_import_assistant.py` passes.
* `python -m compileall -f -q kia kicad_import_assistant.py` passes.
* `git diff --check` passes.
* Non-GUI validation helper check passes.
* Manual startup check confirms the dialog appears on Windows after focus handling was adjusted.

Current limitations:
* Library-profile editing is not active yet.
* API key editing is not active yet.
* Recent-value maintenance is not active yet.
* The dialog edits private data only.

## Unreleased - V0.18.0 Per-Item Replace Actions

Feature branch: `feature/per-item-replace-actions`

Adds explicit per-item replacement choices for existing footprint, model, and symbol targets. Replacement defaults to skip and only runs when the user explicitly chooses it.

Changes:
* Detects existing footprint and model target files during per-item action selection.
* Prompts to replace existing footprint/model targets with `[y/N]` defaulting to skip.
* Creates timestamped backups before replacing existing footprint/model files.
* Detects existing symbol definitions in the target symbol library during action selection.
* Prompts to replace existing symbol definitions with `[y/N]` defaulting to skip.
* Allows selected symbol replacement to pass preview and merge prechecks.
* Replaces the existing symbol block with the edited preview symbol when replacement is selected.
* Creates the existing target symbol library backup before symbol replacement.
* Updates selected-action confirmation text to distinguish import, merge, replace, and skip actions.
* Tracks replacement action states in the import plan.
* Bumps app version to `0.18.0`.

Tested:
* `python -m py_compile kicad_import_assistant.py` passes.
* `python -m compileall -f -q kia kicad_import_assistant.py` passes.
* `git diff --check` passes.
* Direct helper checks confirm footprint/model replacement backup path behavior.
* Direct helper checks confirm symbol block replacement preserves unrelated symbols.
* Controlled workflow test confirms selected footprint, model, and symbol replacement creates backups and replaces target content.
* Default-skip check confirms an existing footprint target is skipped when the user presses Enter.

Current limitations:
* Existing-target replacement is prompt-driven; there is no bulk replace-all mode.
* The importer still requires the target `.pretty` folder itself to exist.
* Linking existing symbols/models to newly imported footprints is not active yet.

## Unreleased - V0.17.0 Missing Symbol Library Creation

Feature branch: `feature/create-missing-symbol-library`

Creates a target `.kicad_sym` library when a symbol merge is selected and no active symbol library exists in the target `.pretty` folder.

Changes:
* Resolves a missing configured target symbol library path without writing before final confirmation.
* Falls back to a target `.kicad_sym` filename matching the selected `.pretty` folder when no configured symbol file and no active symbol libraries exist.
* Creates the missing target symbol library after final selected-actions confirmation and before symbol merge precheck.
* Builds a minimal empty KiCad symbol library using the existing `kicad_symbol_lib` wrapper.
* Keeps using existing symbol libraries when one can be resolved.
* Keeps timestamped backups for pre-existing target symbol libraries.
* Skips symbol-library backup when the target library was newly created by the same import.
* Tracks missing-symbol-library creation state in `run_state`.
* Updates symbol action prompts so missing target symbol libraries can be created and merged instead of forcing symbol skip.
* Bumps app version to `0.17.0`.

Tested:
* `python -m py_compile kicad_import_assistant.py` passes.
* `python -m compileall -f -q kia kicad_import_assistant.py` passes.
* `git diff --check` passes.
* Direct resolver checks confirm missing symbol library paths are resolved without writing before confirmation.
* Direct creation checks confirm empty target symbol libraries pass merge preconditions.
* Controlled workflow test confirms a missing `_test*.pretty` symbol library is created, merged into, and restored afterward.

Current limitations:
* Per-item overwrite is not active yet.
* Symbol replacement is not active yet.
* Existing footprint/model targets can be skipped, but not overwritten.
* The importer still requires the target `.pretty` folder itself to exist.

## Unreleased - V0.16.0 Stale Reference Cleanup

Feature branch: `feature/stale-reference-cleanup`

Adds explicit cleanup prompts for stale references when related per-item import actions are skipped.

Changes:
* Detects existing footprint 3D model references when a footprint is imported but the model action is skipped.
* Prompts the user to clear stale vendor 3D model references from the copied footprint.
* Removes all detected footprint `(model ...)` blocks when the user confirms stale model-reference cleanup.
* Detects existing symbol `Footprint` properties when a symbol is merged but the footprint action is skipped.
* Prompts the user to clear stale symbol `Footprint` properties.
* Clears the preview symbol `Footprint` property before merge when the user confirms stale symbol-reference cleanup.
* Tracks cleared, present, and left-unchanged reference cleanup state in `run_state`.
* Reports reference cleanup status in the final import summary.
* Bumps app version to `0.16.0`.
* Keeps existing overwrite protection, symbol merge backup behavior, source archiving behavior, and public/private config behavior intact.

Tested:
* `python -m py_compile kicad_import_assistant.py` passes.
* `python -m compileall -f -q kia kicad_import_assistant.py` passes.
* Direct helper checks pass for symbol preview `update`, `clear`, and `leave` modes.
* Direct helper checks pass for detecting and clearing multiple footprint model blocks with quoted and unquoted model paths.
* Automated full loose-file import workflow passes.
* Automated skip-model workflow passes and clears stale footprint 3D model references.
* Automated skip-footprint workflow passes and clears stale symbol `Footprint` property.
* Automated workflow tests restore the selected `_test*.pretty` library and private config after completion.

Current limitations:
* Per-item overwrite is not active yet.
* Symbol replacement is not active yet.
* Existing footprint/model targets can be skipped, but not overwritten.
* Missing target symbol libraries are not auto-created yet.
* Clearing stale references is prompt-driven; the importer does not validate whether a kept reference points to an existing KiCad asset.

## Unreleased - V0.15.0 Split Public Defaults and Private Data

Feature branch: `feature/split-public-private-config`

Splits KiCad Import Assistant configuration into tracked public defaults and ignored private/local data.

The public default config now contains factory-safe behavior settings only. Local paths, library profiles, recent values, and API keys belong in ignored private data.

Changes:
* Adds `kicad_import_assistant_default_config.json` as the tracked public default config.
* Adds `kicad_import_private_data.example.json` as the tracked private-data template.
* Uses `kicad_import_private_data.json` for ignored local/private data.
* Loads runtime config from layered sources:
  * Python fallback defaults
  * tracked public default config
  * ignored private data
* Saves successful runtime state only to `kicad_import_private_data.json`.
* Keeps `kicad_import_assistant_default_config.json` unchanged during normal imports.
* Removes `zip_folder` from the active config contract.
* Uses `last.source_folder` as the canonical remembered import-source folder.
* Removes ambiguous `last.profile` from the active config contract.
* Uses `last.target_library` as the canonical remembered target-library key.
* Keeps per-library naming behavior under each library entry’s `schema_profile`.
* Removes stale active references to the old `kicad_import_assistant_config.json` workflow.
* Updates config error messages to point to private data and the private-data example file.
* Keeps existing ZIP, loose-file, per-item action, symbol merge, and source archive workflows intact.

Tested:
* `python -m compileall -f -q kia kicad_import_assistant.py` passes.
* ZIP import with footprint, symbol, and 3D model passes.
* Loose-file import with footprint, symbol, and 3D model passes.
* Per-item skip workflow passes.
* Symbol-only workflow passes.
* Missing private data file exits cleanly with useful guidance.
* Successful imports update `kicad_import_private_data.json`.
* Successful imports do not modify `kicad_import_assistant_default_config.json`.
* Active Python and Markdown files no longer reference:
  * `zip_folder`
  * `last_target_library`
  * old active `kicad_import_assistant_config.json` workflow

Known follow-up:
* Vendor-provided stale model references may remain in imported footprints when model import is skipped.
* Vendor-provided stale Footprint properties may remain in imported symbols when footprint import is skipped.
* A follow-up branch should add explicit cleanup/clear behavior for skipped reference fields.

Current limitations:
* Per-item overwrite is not active yet.
* Symbol replacement is not active yet.
* Existing footprint/model targets can be skipped, but not overwritten.
* Missing target symbol libraries are not auto-created yet.
* Stale footprint model references are not cleared when model import is skipped.
* Stale symbol Footprint properties are not cleared when footprint import is skipped.

## Unreleased - V0.14.0 Simplify Execution Confirmation

Feature branch: `feature/simplify-execution-confirmation`

Replaces the older separate `COPY` and `MERGE` hard-confirmation prompts with one final selected-actions confirmation.

The user still chooses per-item footprint/model/symbol actions first. After import-plan review, the tool summarizes the selected actions and asks for one final confirmation before target-library writes occur.

Changes:
* Adds `kia/workflow_execution.py`.
* Adds one final selected-actions confirmation stage.
* Prints selected footprint, model, and symbol actions before writes.
* Shows source and target paths for selected actions.
* Replaces the separate `COPY` and `MERGE` user-facing prompts with one `[y/N]` confirmation.
* Updates main workflow orchestration to call the final execution confirmation once after import-plan review.
* Keeps footprint/model overwrite protection unchanged.
* Keeps timestamped symbol-library backup behavior unchanged.
* Keeps per-item skipped-action behavior unchanged.
* Allows symbol merge state to be populated by the symbol preview stage instead of the old `MERGE` confirmation stage.
* Ensures no selected writes occur when the final confirmation is declined.
* Updates README and FEATURES documentation for the new confirmation flow.

Tested:
* Full import with footprint, model, and symbol kept.
* Import with model skipped and footprint/symbol kept.
* Symbol-only merge with footprint/model skipped.
* Footprint/model import with symbol skipped.
* Final confirmation declined before writes.
* No `COPY` prompt appears.
* No `MERGE` prompt appears.
* Symbol merge still creates a timestamped backup.
* Source archive prompt still includes only source files for actions that actually ran.
* Skipped source files are left in place.

Current limitations:
* Per-item overwrite is not active yet.
* Symbol replacement is not active yet.
* Existing footprint/model targets can be skipped, but not overwritten.
* Missing target symbol libraries are not auto-created yet.

## Unreleased - V0.13.0 Per-Item Skip Actions

Feature branch: `feature/per-item-skip-actions`

Adds per-item import action choices so footprint, model, and symbol operations can be kept or skipped independently before the import writes to the target library.

Changes:
* Adds per-item action prompts after the import plan is created.
* Allows the user to keep or skip each planned import item:
  * footprint import
  * 3D model import
  * symbol merge
* Marks skipped plan items as `SKIPPED_BY_USER`.
* Updates footprint/model copy logic to ignore skipped items.
* Updates symbol preview/merge logic to ignore skipped symbols.
* Skips the global file-copy confirmation when no footprint/model copy actions remain.
* Prevents skipped loose source files from being archived after import.
* Archives only original source files that correspond to import actions that actually ran.
* Updates final import summary so skipped footprint/model/symbol actions are reported correctly.
* Updates preview manifest behavior so skipped items are excluded.
* Fixes preview manifest model target extension handling so `.stp` and `.step` are preserved correctly.
* Keeps existing hard-confirmation prompts for file copy and symbol merge when those action types are still selected.

Tested:
* Full import with footprint, model, and symbol kept.
* Loose-file import with model skipped and footprint/symbol kept.
* Loose-file import with symbol skipped and footprint/model kept.
* Loose-file import with footprint/model skipped and symbol kept.
* Existing target footprint skipped while model and symbol were imported.
* Skip-all path exits cleanly before writes.
* Archive prompt includes only source files for actions that actually ran.
* Skipped source files are left in place.
* No file-copy prompt is shown when all footprint/model actions are skipped.
* No target footprint overwrite occurs when the footprint is skipped.
* Symbol merge still creates a timestamped backup.

Current limitations:
* Per-item overwrite is not active yet.
* Symbol replacement is not active yet.
* Existing footprint/model targets can be skipped, but not overwritten.
* Missing target symbol libraries are not auto-created yet.
* The global COPY and MERGE confirmation prompts still appear when their corresponding action types are selected.


## Unreleased - V0.12.1 Duplicate Target Warning Severity

Fix branch: `fix/duplicate-target-warning-severity`

Changes:
* Reclassifies existing target footprint/model overwrite protection from error severity to warning severity.
* Keeps overwrite protection behavior unchanged.
* Prevents intentional duplicate-target stops from being displayed as `CRITICAL ERROR`.

Tested:
* Existing target footprint/model import attempt stops safely with warning severity.
* No target files are overwritten.
* No source archive prompt is shown because the import did not complete successfully.

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
