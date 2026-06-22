# KiCad Import Assistant Refactor Plan

Temporary planning document for the V0.10.x refactor pass.

This branch is a breaking refactor branch. Backward compatibility with earlier local config formats is not guaranteed during this work.

The purpose of this refactor is to replace the current mostly-linear script with a staged import pipeline built around a shared `run_state` dictionary. Each stage should perform one clear task, update its own section of `run_state`, report status through `run_state["status"]`, and allow `main()` to decide whether the workflow should continue.

---

## Refactor Goals

Primary goals:

* Make `main()` read like a high-level workflow instead of an implementation dump.
* Replace scattered local variables with a structured `run_state` object.
* Make every major stage report success/failure through `run_state["status"]`.
* Separate user selection, path interpretation, profile resolution, source discovery, naming, import planning, execution, and reporting.
* Replace the old “manifest” language with `import_plan`.
* Separate physical library target selection from naming/schema profile behavior.
* Prevent connector-oriented prompts from leaking into IC/sensor imports.
* Save config updates only after a successful or cleanly completed workflow.
* Keep helper functions small, explicit, and testable in isolation.

Non-goals for this refactor:

* No online metadata enrichment yet.
* No batch import yet.
* No full GUI rewrite yet.
* No KiCad plugin conversion yet.
* No complete S-expression parser unless absolutely necessary.
* No attempt to preserve backward compatibility with old flat `last_*` config keys on this branch.

---

## Abstraction Rule

Each function should do one clear kind of work:

* Ask: collect user selection/input.
* Interpret: convert raw selection into meaning.
* Resolve: map config/profile data into concrete paths/settings.
* Modify: write/copy/update files.
* Report: print user-facing or debug output.
* Validate: check whether required assumptions are true.

Avoid functions that ask, interpret, mutate config, resolve targets, and write files all at once.

---

## `run_state` Design

`run_state` is the shared runtime state for one import attempt.

It acts like a lightweight C-style struct:

* each stage reads/writes only its assigned section
* each stage updates `run_state["status"]`
* `main()` checks `run_state["status"]["success"]` after each stage
* config updates are staged in `run_state` first
* config is saved only after successful completion

Major sections:

```text
status
config
user_input
profile
current
import_plan
recent_values
symbol
footprint
model
copied_files / aggregate final flags
```

### `run_state["status"]`

Every major function must update this section before returning.

Fields:

```text
success
severity
script
step
function_name
failure_reason
message
```

Rules:

* `success == True` means the next stage may continue.
* `success == False` means `main()` should stop or call `critical_error()`.
* `severity` should use the shared `Severity` enum.
* `script`, `step`, and `function_name` should identify where the status came from.
* `failure_reason` may contain multi-line strings.

### Status helper functions

Preferred helpers:

```python
mark_success(run_state, script, step, function_name, message=None)
mark_failure(run_state, script, step, function_name, failure_reason, severity=Severity.ERROR)
stop_if_failed(run_state)
critical_error(run_state)
```

These helpers should prevent each stage from manually rebuilding the status object.

---

## New Config Shape

The config file should use nested objects instead of older flat `last_*` keys.

Target structure:

```json
{
  "last": {
    "zip_folder": "...",
    "library_root": "...",
    "library_folder": "...",
    "target_library": "IC",
    "profile": "ic"
  },
  "path_variable": "CHRIS_KICAD_LIB",
  "keep_temp_files": false,
  "libraries": {
    "CONNECTORS": {
      "prefix": "CONN",
      "schema_profile": "connector",
      "footprint_dir": "_testCONN.pretty",
      "symbol_file": "_testCONN.kicad_sym",
      "nickname": "_testCONN"
    },
    "IC": {
      "prefix": "IC",
      "schema_profile": "ic",
      "footprint_dir": "_testIC.pretty",
      "symbol_file": "_testIC.kicad_sym",
      "nickname": "_testIC"
    }
  },
  "recent_values": {
    "family": [],
    "role": [],
    "mount": [],
    "orient": [],
    "size": [],
    "pitch": [],
    "base": [],
    "feature": []
  }
}
```

Mapping:

```text
run_state["current"]       -> config["last"]
run_state["recent_values"] -> config["recent_values"]
```

Old flat keys such as these should be removed from the refactor branch:

```text
last_zip_folder
last_library_root
last_library_folder
last_target_library
```

---

## Proposed High-Level `main()` Shape

The goal is for `main()` to become a readable orchestration layer:

```python
def main() -> None:
    initialize_tkinter_dialogs()

    run_state = initialize_run_state()

    run_state = load_runtime_config(run_state)
    stop_if_failed(run_state)

    run_state = collect_and_validate_user_input(run_state)
    stop_if_failed(run_state)

    run_state = resolve_target_profile(run_state)
    stop_if_failed(run_state)

    run_state = prepare_import_source(run_state)
    stop_if_failed(run_state)

    run_state = discover_source_files(run_state)
    stop_if_failed(run_state)

    run_state = build_import_basename(run_state)
    stop_if_failed(run_state)

    run_state = select_files_for_import(run_state)
    stop_if_failed(run_state)

    run_state = create_import_plan(run_state)
    stop_if_failed(run_state)

    run_state = review_import_plan(run_state)
    stop_if_failed(run_state)

    run_state = execute_import(run_state)
    stop_if_failed(run_state)

    run_state = apply_successful_config_updates(run_state)
    stop_if_failed(run_state)

    print_final_import_report(run_state)
```

Each stage should be testable independently where practical.

---

## Pipeline Stages

### Stage 0 — Initialize

Function:

```python
initialize_run_state() -> dict
```

Responsibilities:

* create the default `run_state`
* initialize all known sections and flags
* avoid doing file I/O

Owns:

```text
run_state
```

---

### Stage 1 — Load Runtime Config

Function:

```python
load_runtime_config(run_state: dict) -> dict
```

Responsibilities:

* load `kicad_import_assistant_config.json`
* load naming schema JSON
* load suggestion rules JSON
* store loaded objects in `run_state["config"]`
* set aggregate loaded flag
* report failure through `run_state["status"]`

Owns:

```text
run_state["status"]
run_state["config"]
```

Must not:

* prompt the user
* select files/folders
* write config
* start import work

---

### Stage 2 — Collect and Validate User Input

Function:

```python
collect_and_validate_user_input(run_state: dict) -> dict
```

Responsibilities:

* open import source picker
* open library folder picker
* validate selected paths exist
* verify current source type is supported
* store raw selections in `run_state["current"]`
* update `run_state["user_input"]`

Owns:

```text
run_state["status"]
run_state["user_input"]
run_state["current"]
```

Must not:

* infer profile
* build filenames
* extract ZIPs
* copy files

---

### Stage 3 — Resolve Library/Profile

Function:

```python
resolve_target_profile(run_state: dict) -> dict
```

Responsibilities:

* interpret selected library folder
* resolve library root
* infer profile from selected `.pretty` folder
* prompt/confirm target library profile
* load selected profile settings
* resolve target footprint folder
* resolve target symbol file
* validate required profile keys

Owns:

```text
run_state["status"]
run_state["profile"]
run_state["current"]
```

Must not:

* copy files
* extract ZIPs
* build basename
* modify symbols/footprints

---

### Stage 4 — Prepare Import Source

Function:

```python
prepare_import_source(run_state: dict) -> dict
```

Responsibilities:

* extract ZIP to temp folder
* later support loose file/folder import
* store temp/source root in `run_state["import_plan"]["temp_folder_path"]`

Owns:

```text
run_state["status"]
run_state["import_plan"]["temp_folder_path"]
```

Must not:

* pick target library
* build basename
* write to target library

---

### Stage 5 — Discover Source Files

Function:

```python
discover_source_files(run_state: dict) -> dict
```

Responsibilities:

* scan extracted/source folder
* find symbol, footprint, and model candidates
* update source-existence flags

Owns:

```text
run_state["status"]
run_state["symbol"]["exists_in_source"]
run_state["footprint"]["exists_in_source"]
run_state["model"]["exists_in_source"]
```

May also stage source paths into:

```text
run_state["import_plan"]["symbol"]["source_path"]
run_state["import_plan"]["footprint"]["source_path"]
run_state["import_plan"]["model"]["source_path"]
```

---

### Stage 6 — Build Import Basename

Function:

```python
build_import_basename(run_state: dict) -> dict
```

Responsibilities:

* suggest naming defaults from source files
* use selected schema profile
* prompt user for naming fields
* build final basename
* update recent prompt values
* handle intentional blank optional fields

Owns:

```text
run_state["status"]
run_state["import_plan"]["basename"]
run_state["recent_values"]
run_state["user_entered_new_schema"]
```

Must not:

* copy files
* merge symbols
* save config

---

### Stage 7 — Select Files for Import

Function:

```python
select_files_for_import(run_state: dict) -> dict
```

Responsibilities:

* let user choose which source files to import
* update `user_chose_import` flags
* update aggregate `user_confirmed_import` later after final confirmation

Owns:

```text
run_state["status"]
run_state["symbol"]["user_chose_import"]
run_state["footprint"]["user_chose_import"]
run_state["model"]["user_chose_import"]
```

---

### Stage 8 — Create Import Plan

Function:

```python
create_import_plan(run_state: dict) -> dict
```

Responsibilities:

* build source/target path plan
* determine new filenames
* determine planned actions
* detect target duplicates
* prepare human-reviewable plan
* replace old manifest concept

Owns:

```text
run_state["status"]
run_state["import_plan"]
run_state["symbol"]["exists_in_target"]
run_state["footprint"]["exists_in_target"]
run_state["model"]["exists_in_target"]
run_state["symbol"]["duplicate"]
run_state["footprint"]["duplicate"]
run_state["model"]["duplicate"]
```

Must not:

* copy files
* modify footprints
* merge symbols

---

### Stage 9 — Review Import Plan

Function:

```python
review_import_plan(run_state: dict) -> dict
```

Responsibilities:

* print planned source/target actions
* optionally write import plan CSV
* ask final confirmation
* set `run_state["user_confirmed_import"]`

Owns:

```text
run_state["status"]
run_state["import_plan"]["user_wants_to_review"]
run_state["user_confirmed_import"]
```

---

### Stage 10 — Execute Import

Function:

```python
execute_import(run_state: dict) -> dict
```

Responsibilities:

* copy selected footprint/model files
* update footprint name/value/model path/metadata
* create symbol preview
* check symbol merge preconditions
* back up symbol library
* merge symbol if safe
* update copied files list and final flags

Owns:

```text
run_state["status"]
run_state["symbol"]
run_state["footprint"]
run_state["model"]
run_state["copied_files"]
run_state["files_copied"]
run_state["was_successful"]
```

Must require:

```text
run_state["user_confirmed_import"] == True
```

---

### Stage 11 — Apply Config Updates

Function:

```python
apply_successful_config_updates(run_state: dict) -> dict
```

Responsibilities:

* copy successful run values into loaded config object
* save config only after success/clean completion

Mapping:

```text
run_state["current"]       -> config["last"]
run_state["recent_values"] -> config["recent_values"]
```

Owns:

```text
run_state["status"]
run_state["config"]["general_config"]
```

---

### Stage 12 — Final Report and Cleanup

Functions:

```python
print_final_import_report(run_state: dict) -> None
cleanup_runtime_temp_files(run_state: dict) -> dict
```

Responsibilities:

* print summary
* print failure reason if needed
* clean temp folder according to config
* report kept temp folder if applicable

Owns:

```text
run_state["status"]
```

Cleanup should be safe and should not hide earlier errors.

---

## Proposed Module Structure

Target direction:

```text
kia/
├─ __init__.py
├─ config.py
├─ debug.py
├─ dialogs.py
├─ run_state.py
├─ workflow_status.py
├─ library_resolution.py
├─ source_scan.py
├─ schema.py
├─ suggestions.py
├─ naming.py
├─ import_plan.py
├─ footprint_importer.py
├─ symbol_resolver.py
├─ symbol_preview.py
└─ symbol_merge.py
```

---

## Proposed Module Responsibilities

### `kicad_import_assistant.py`

Main orchestration only.

Should:

* initialize Tkinter dialogs
* initialize `run_state`
* call each pipeline stage
* call `stop_if_failed()` after each critical stage
* print final report

Should avoid:

* direct symbol parsing
* direct footprint editing
* direct config repair
* detailed implementation logic
* long nested workflow branches

---

### `kia/run_state.py`

Responsibilities:

* define `initialize_run_state()`
* define any run-state helper accessors if needed

Should avoid:

* file I/O
* dialogs
* import execution

---

### `kia/workflow_status.py`

Responsibilities:

* define `mark_success()`
* define `mark_failure()`
* define `stop_if_failed()`
* define `critical_error()`
* possibly map `Severity` to user-facing behavior

Should avoid:

* import-specific logic
* KiCad file parsing

---

### `kia/config.py`

Responsibilities:

* define `CONFIG_PATH`
* define `DEFAULT_CONFIG`
* load config
* save config
* fail loudly on invalid JSON
* validate required config sections if appropriate

Should avoid:

* user dialogs
* source scanning
* footprint/symbol editing

---

### `kia/dialogs.py`

Responsibilities:

* file picker dialogs
* folder picker dialogs
* simple future Tkinter prompts

Should avoid:

* config mutation beyond maybe remembering picker starting folders
* library/profile inference
* import logic

---

### `kia/library_resolution.py`

Responsibilities:

* identify `.pretty` folders
* resolve library root from selected folder
* infer profile from selected folder
* select/confirm target profile
* resolve target footprint directory
* resolve target symbol file
* validate profile settings

Should avoid:

* source ZIP extraction
* naming prompts
* file copying
* symbol merge

---

### `kia/source_scan.py`

Responsibilities:

* extract ZIP to temp folder
* later support loose files/folders
* scan source folder for KiCad files
* cleanup temp folder

Should avoid:

* target library selection
* naming prompts
* file copying into target library

---

### `kia/schema.py`

Responsibilities:

* load naming schema JSON
* provide schema-profile data

Future profiles:

* connector
* ic
* sensor
* module
* passive
* power
* generic

---

### `kia/suggestions.py`

Responsibilities:

* load suggestion rules
* suggest default naming fields from filenames

Should avoid:

* prompting user
* building final basename
* copying files

---

### `kia/naming.py`

Responsibilities:

* prompt for naming fields
* display token menus
* normalize naming tokens
* build final basename
* update recent values in run state
* support intentional blank optional fields

Should avoid:

* target file writes
* symbol merge
* library root selection

---

### `kia/import_plan.py`

Replacement for old `manifest.py`.

Responsibilities:

* build planned source/target file actions
* detect planned target filenames
* optionally write CSV import plan
* print import plan for user review

Should avoid:

* copying files
* modifying footprints/symbols

---

### `kia/footprint_importer.py`

Responsibilities:

* copy selected footprint/model files
* refuse overwrites
* update footprint internal name
* update footprint `Value` field
* add/update 3D model path
* add import metadata

Should avoid:

* symbol parsing
* symbol merge
* config loading
* naming prompts

---

### `kia/symbol_resolver.py`

Responsibilities:

* locate target `.kicad_sym` file
* ignore backup/copy-looking symbol files
* prefer folder-name-matching symbol library
* warn/refuse ambiguous symbol targets
* return resolved path and status

---

### `kia/symbol_preview.py`

Responsibilities:

* read source symbol
* detect first symbol name
* rename parent symbol
* rename nested KiCad unit symbols
* update symbol `Footprint` property
* write temporary symbol preview file

---

### `kia/symbol_merge.py`

Responsibilities:

* check symbol merge preconditions
* detect duplicate symbol in target library
* create symbol library backup
* extract symbol block from preview file
* merge symbol block into target `.kicad_sym`

---

## Refactor Order

Recommended order:

1. Rename current shared state concept to `run_state`.
2. Add `kia/run_state.py`.
3. Add `initialize_run_state()`.
4. Add `kia/workflow_status.py`.
5. Add `mark_success()`, `mark_failure()`, `stop_if_failed()`, and `critical_error()`.
6. Update config JSON shape to use nested `last` object only.
7. Update `DEFAULT_CONFIG` to match new config shape.
8. Remove old flat `last_*` config keys.
9. Stabilize `dialogs.py` as raw file/folder selection only.
10. Stabilize `library_resolution.py`.
11. Make profile inference work from selected `.pretty` folder.
12. Make target profile prompt default to inferred profile.
13. Update `main()` to use staged pipeline structure.
14. Rename `manifest.py` to `import_plan.py`.
15. Rename `create_preview_manifest()` to `create_import_plan()`.
16. Rename `zip_scan.py` to `source_scan.py`.
17. Rename `symbols.py` to `symbol_resolver.py`.
18. Later split `symbol_editor.py` into `symbol_preview.py` and `symbol_merge.py`.
19. Update docs.
20. Commit once the staged pipeline runs through a basic cancel/import test.

---

## Testing Checklist

Before committing this refactor branch:

* Config loads with nested `last` object.
* Old flat `last_*` keys are no longer required.
* Invalid config JSON fails loudly.
* `run_state` initializes correctly.
* `mark_success()` updates status correctly.
* `mark_failure()` updates status correctly.
* `stop_if_failed()` calls `critical_error()` only when expected.
* Selecting `_testIC.pretty` resolves library root to parent folder.
* Selecting `_testIC.pretty` infers target library `IC`.
* Selecting library root directly uses default or last target library.
* Target profile prompt defaults to inferred profile when available.
* Connector import targets connector library.
* IC import targets IC library.
* Connector prompts do not leak into IC imports once schema profiles are implemented.
* Import plan shows correct source and target paths.
* Import plan can be reviewed before writing files.
* Model-only import does not attempt symbol merge.
* Symbol-only import does not attempt footprint/model edit.
* Duplicate target files are detected before write.
* Symbol duplicate is detected before merge.
* Symbol backup is created before merge.
* Temp cleanup works with `keep_temp_files: false`.
* Temp folder is retained with `keep_temp_files: true`.
* Final report reflects actual copied/merged files.

---

## Documentation Checklist

Before each commit:

* Update `README.md` for user-facing behavior changes.
* Update `FEATURES.md` for detailed capability/limitation/roadmap changes.
* Update `VERSION_HISTORY.md` with completed branch work.
* Mention breaking config changes in `VERSION_HISTORY.md`.
* Avoid expanding the main script header unless entry-point behavior meaningfully changes.
* Provide GitHub Desktop commit summary and description.
