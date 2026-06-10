# KiCad Import Assistant

KiCad Import Assistant is a standalone Python utility for importing vendor-provided KiCad footprints, symbols, and 3D models into a custom KiCad library structure.

The tool is designed around a cautious workflow: preview first, confirm explicitly, create backups where needed, and refuse unsafe overwrites.

## Current Version

**V0.9.0**

## What It Does

KiCad Import Assistant can currently:

* Select a vendor ZIP file.
* Extract the ZIP to a temporary folder.
* Detect KiCad footprint, symbol, and STEP/STP model files.
* Suggest naming defaults from JSON rules.
* Prompt for naming tokens using schema-driven menus.
* Generate standardized footprint/symbol/model basenames.
* Copy and rename footprint/model files into a target `.pretty` folder.
* Update copied footprint internals:

  * internal footprint name
  * visible `Value` field
  * 3D model reference
  * hidden import/review metadata
* Create an edited symbol preview file.
* Update symbol names, nested KiCad unit names, and symbol `Footprint` properties.
* Resolve the correct target `.kicad_sym` file.
* Create a timestamped backup of the target symbol library.
* Merge the previewed symbol into the target symbol library when safety checks pass.
* Refuse duplicate footprint/model overwrites.
* Refuse duplicate symbol merges.

More detailed feature notes are available in [`FEATURES.md`](FEATURES.md).

Version-by-version history is available in [`VERSION_HISTORY.md`](VERSION_HISTORY.md).

## Basic Workflow

The current workflow is:

1. Select a vendor ZIP file.
2. Select the custom KiCad library root.
3. Resolve the target `.pretty` folder and `.kicad_sym` file.
4. Extract and scan the ZIP.
5. Suggest naming defaults.
6. Prompt for naming tokens.
7. Generate the final basename.
8. Create a symbol preview.
9. Optionally create a manifest CSV.
10. Require the user to type `IMPORT`.
11. Copy/rename footprint and model files.
12. Update the copied footprint.
13. Back up the target symbol library.
14. Merge the edited symbol into the target symbol library.

## Safety Behavior

This tool is intentionally conservative.

Before writing files, it requires this exact confirmation:

```text
IMPORT
```

The tool currently refuses to overwrite existing footprint/model files.

Before merging a symbol, it checks whether the generated symbol already exists in the resolved target symbol library.

Before modifying a target `.kicad_sym` library, it creates a timestamped backup file.

Even with these safeguards, this is still early-development software. Back up your KiCad libraries before testing it against production libraries.

## Intended Library Structure

The project currently assumes a custom KiCad library layout similar to:

```text
CUSTOM_LIBRARIES/
├─ CONNECTORS.pretty/
│  ├─ *.kicad_mod
│  ├─ *.step
│  └─ CONNECTORS.kicad_sym
└─ _TOOLS/
   └─ kicad-import-assistant/
      ├─ kicad_import_assistant.py
      ├─ kicad_import_assistant_config.example.json
      ├─ kicad_import_naming_schema.json
      ├─ kicad_import_suggestion_rules.json
      └─ kia/
         ├─ __init__.py
         ├─ config.py
         ├─ debug.py
         ├─ dialogs.py
         ├─ importer.py
         ├─ manifest.py
         ├─ naming.py
         ├─ schema.py
         ├─ suggestions.py
         ├─ symbol_editor.py
         ├─ symbols.py
         └─ zip_scan.py
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
