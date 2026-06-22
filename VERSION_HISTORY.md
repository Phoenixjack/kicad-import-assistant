# Version History

## VERSION_HISTORY.md update

## Unreleased - V0.10 Refactor Branch

Breaking refactor work in progress on the `refactor-debug-cleanup` branch.

Completed in this checkpoint:

* Adds `kia/run_state.py`.
* Adds `initialize_run_state()` as the central per-import workflow state initializer.
* Adds `kia/workflow_status.py`.
* Adds status helper functions:

  * `mark_success()`
  * `mark_failure()`
  * `stop_if_failed()`
  * `critical_error()`
* Updates `kicad_import_assistant.py` so `main()` uses a short staged workflow.
* Adds early-stage runtime config loading through `load_runtime_config()`.
* Adds early-stage user input collection and validation through `collect_and_validate_user_input()`.
* Adds early-stage target library/profile resolution through `resolve_target_library()`.
* Updates dialog startup behavior to use the nested `config["last"]` structure.
* Updates library folder selection so the picker uses `config["last"]["library_root"]`.
* Confirms selecting a `.pretty` folder resolves the custom library root from its parent folder.
* Confirms selecting `_testIC.pretty` can infer the `IC` target profile.
* Renames workflow status helper parameters from `import_result` to `run_state`.
* Updates stale comments referring to old `config["last_*"]` keys.

Current intentional limitation:

* The staged workflow currently stops after early validation and target library resolution.
* Source extraction, file discovery, naming, import planning, and actual import execution are not yet restored into the new staged pipeline.

Breaking changes:

* This branch no longer preserves backward compatibility with the older flat `last_*` config keys.
* The config structure is moving toward a nested `config["last"]` object.
* `run_state` is now the intended runtime data structure for workflow state and staged status reporting.


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
