# KiCad Import Assistant Refactor Plan

Temporary planning document for the V0.9.x / V0.10.x refactor pass.

This file exists to map current responsibilities, identify module boundaries, and reduce accidental spaghetti growth while refactoring.

## Refactor Goals

Primary goals:

* Reduce confusion about which module owns which behavior.
* Improve debug output so messages identify category and source/stage.
* Separate physical library target selection from naming schema/prompt behavior.
* Make symbol resolution, symbol preview, symbol backup, and symbol merge easier to reason about.
* Keep the tool behavior stable while reorganizing code.
* Avoid large untested rewrites.

Non-goals for this refactor:

* No new online API metadata enrichment yet.
* No batch import yet.
* No full GUI rewrite yet.
* No KiCad plugin conversion yet.
* No complete S-expression parser unless absolutely necessary.

## Current Pain Points

Known issues:

* Debug output is noisy and difficult to visually scan.
* Some debug categories do not clearly identify the source file or workflow stage.
* `symbols.py` and `symbol_editor.py` contain related but different responsibilities.
* Physical library targets and naming/prompt behavior are partly tangled.
* Connector-oriented naming prompts currently leak into non-connector imports.
* Config behavior is improving but still needs clearer validation/reporting.
* Temporary folder cleanup now exists, but cleanup/reporting should remain simple and safe.

## Proposed Module Structure

Current modules may evolve toward this structure:

```text
kia/
├─ __init__.py
├─ config.py
├─ debug.py
├─ dialogs.py
├─ importer.py
├─ manifest.py
├─ naming.py
├─ schema.py
├─ suggestions.py
├─ zip_scan.py
├─ library_profiles.py
├─ symbol_resolver.py
├─ symbol_preview.py
└─ symbol_merge.py
```

## Proposed Responsibilities

### `kicad_import_assistant.py`

Main orchestration only.

Responsibilities:

* Load config.
* Prompt for ZIP/source.
* Prompt/select target library.
* Call ZIP/file discovery.
* Call naming workflow.
* Call symbol preview/precheck/merge workflow.
* Call footprint/model importer.
* Print final status.
* Save config.

Should avoid:

* Direct symbol parsing.
* Direct footprint editing.
* Direct config repair.
* Complex debug formatting.
* Detailed implementation logic.

### `kia/config.py`

Responsibilities:

* Define `CONFIG_PATH`.
* Define `DEFAULT_CONFIG`.
* Load config.
* Save config.
* Fail loudly on invalid JSON.
* Merge older configs over defaults.
* Possibly validate required config sections later.

Should avoid:

* Knowing KiCad file formats.
* Selecting libraries interactively.
* Performing import logic.

### `kia/debug.py`

Responsibilities:

* Define debug category/stage toggles.
* Format debug output.
* Support readable prefixes.

Possible future output styles:

```text
[CONFIG/load] Loaded config file
[ZIP/extract] Extracted vendor ZIP
[SYMBOLS/resolve] Preferred folder-matching symbol library
[SYMBOLS/merge] Merged preview symbol into target library
[IMPORTER/model] Added 3D model reference
```

Possible future call style:

```python
debug_print("symbols", "resolve", "Preferred symbol library found")
```

or:

```python
debug_print("symbols.resolve", "Preferred symbol library found")
```

Decision needed before implementation.

### `kia/dialogs.py`

Responsibilities:

* File picker dialogs.
* Folder picker dialogs.
* Any future simple Tkinter prompts.

Should avoid:

* Import logic.
* Naming logic.
* Config mutation except returning selected paths.

### `kia/zip_scan.py`

Responsibilities:

* Extract ZIP to temp folder.
* Find KiCad import files.
* Print import file summary.
* Cleanup temp folder.

Future possible rename:

```text
source_scan.py
```

if loose-file and folder import are added.

### `kia/suggestions.py`

Responsibilities:

* Load suggestion rules.
* Suggest default naming fields from filenames.
* Return suggested defaults.

Should avoid:

* Prompting the user.
* Building final basenames.
* Copying files.

### `kia/schema.py`

Responsibilities:

* Load naming schema JSON.
* Provide schema data to naming logic.
* Later support schema profiles:

  * connector
  * IC
  * module
  * passive
  * power
  * generic

### `kia/naming.py`

Responsibilities:

* Prompt for naming fields.
* Display token menus.
* Normalize naming tokens.
* Build final basename.
* Manage recent naming-token values.

Future improvement:

* Use schema profiles so connector-specific prompts do not appear for IC imports.

### `kia/library_profiles.py`

New proposed module.

Responsibilities:

* Read configured library profiles.
* Select active library profile.
* Resolve target footprint directory from selected profile.
* Provide prefix, nickname, footprint directory, symbol file, and schema profile.
* Separate physical target from naming prompt behavior.

Example future profile:

```json
"libraries": {
  "CONNECTORS": {
    "prefix": "CONN",
    "schema_profile": "connector",
    "footprint_dir": "CONNECTORS.pretty",
    "symbol_file": "CONNECTORS.kicad_sym",
    "nickname": "CONNECTORS"
  },
  "IC": {
    "prefix": "IC",
    "schema_profile": "ic",
    "footprint_dir": "IC.pretty",
    "symbol_file": "IC.kicad_sym",
    "nickname": "IC"
  }
}
```

### `kia/importer.py`

Responsibilities:

* Copy selected footprint/model files.
* Refuse overwrites.
* Update footprint internal name.
* Update footprint `Value` field.
* Add/update 3D model path.
* Add import metadata.

Should avoid:

* Symbol parsing.
* Symbol merge.
* Config loading.
* Prompting for naming fields.

### `kia/manifest.py`

Responsibilities:

* Build preview manifest data.
* Write preview manifest CSV.
* Report intended import actions.

Should avoid:

* Copying files.
* Modifying footprints/symbols.

### `kia/symbol_resolver.py`

Proposed replacement/split from `symbols.py`.

Responsibilities:

* Locate target `.kicad_sym` file.
* Ignore backup/copy-looking symbol files.
* Prefer folder-name-matching symbol library.
* Warn/refuse ambiguous symbol targets.
* Return resolved path and status.

### `kia/symbol_preview.py`

Proposed split from `symbol_editor.py`.

Responsibilities:

* Read source symbol.
* Detect first symbol name.
* Rename parent symbol.
* Rename nested KiCad unit symbols.
* Update symbol `Footprint` property.
* Write temporary symbol preview file.

### `kia/symbol_merge.py`

Proposed split from `symbol_editor.py`.

Responsibilities:

* Check symbol merge preconditions.
* Detect duplicate symbol in target library.
* Create symbol library backup.
* Extract symbol block from preview file.
* Merge symbol block into target `.kicad_sym`.

## Refactor Order

Recommended order:

1. Improve debug output format without changing behavior.
2. Add `library_profiles.py` or clarify existing library-selection helpers.
3. Split `symbols.py` into `symbol_resolver.py`.
4. Split `symbol_editor.py` into `symbol_preview.py` and `symbol_merge.py`.
5. Update imports in `kicad_import_assistant.py`.
6. Test connector import.
7. Test IC import into `_testIC.pretty`.
8. Test duplicate detection.
9. Test temp cleanup.
10. Update README / FEATURES / VERSION_HISTORY.
11. Commit.

## Testing Checklist

Before committing refactor work:

* Run normal connector import into test connector library.
* Run duplicate connector import and confirm refusal.
* Run IC import into test IC library.
* Confirm generated names use expected prefix.
* Confirm symbol preview file is created.
* Confirm symbol merge backup is created.
* Confirm merged symbol opens in KiCad.
* Confirm temp cleanup works with `keep_temp_files: false`.
* Confirm temp folder is retained with `keep_temp_files: true`.
* Confirm invalid config JSON fails loudly.
* Confirm GitHub Desktop does not show private config file if ignored.

## Documentation Checklist

Before each commit:

* Update `README.md` for user-facing behavior changes.
* Update `FEATURES.md` for detailed capability/limitation/roadmap changes.
* Update `VERSION_HISTORY.md` for completed version changes.
* Avoid expanding the main script header unless the entry-point behavior meaningfully changes.
* Provide commit summary and description.
