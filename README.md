# KiCad Import Assistant

KiCad Import Assistant is a small Python utility for importing vendor-provided KiCad footprints, symbols, and 3D models into a custom KiCad library structure.

The project is built around a cautious import workflow:

1. Select a vendor ZIP file.
2. Select a custom KiCad library root folder.
3. Extract the ZIP to a temporary folder.
4. Detect `.kicad_mod`, `.kicad_sym`, `.step`, and `.stp` files.
5. Resolve the target footprint/model folder and symbol library path.
6. Suggest naming defaults from JSON-based rules.
7. Prompt for naming-convention fields using schema-driven token menus.
8. Generate a standardized target basename.
9. Optionally create a preview manifest.
10. Require explicit confirmation before copying files.
11. Copy and rename selected footprint/model files.
12. Update copied footprint metadata where possible.

## Project Status

Early development / work in progress.

Current version: **V0.7.0**

Current features:

* GUI file picker for selecting a vendor ZIP file
* GUI folder picker for selecting the custom KiCad library root
* JSON config support
* Remembers last ZIP folder, library root, target library, and recent naming-token values
* Safely falls back if remembered folders no longer exist
* Automatically handles accidentally selecting a `.pretty` folder as the library root
* Extracts ZIP files to a temporary folder
* Detects KiCad footprint, symbol, and 3D model files
* Resolves target symbol library path from config or by scanning the target `.pretty` folder
* Loads naming suggestions from JSON
* Loads naming vocabulary/options from JSON schema
* Provides numbered token menus for common naming fields
* Allows direct token entry and free-text custom values
* Generates a standardized target basename
* Optionally creates a preview manifest CSV
* Performs an early duplicate check by MPN
* Copies and renames selected footprint files into the target `.pretty` folder
* Copies and renames selected STEP/STP model files into the target `.pretty` folder
* Requires hard confirmation before modifying files
* Refuses to overwrite existing target files
* Updates copied footprint internal names when possible
* Updates copied footprint `Value` properties when possible
* Adds or updates copied footprint 3D model references
* Adds hidden import/review metadata fields to copied footprints
* Records importer version in copied footprints
* Provides lightweight debug-output categories for development/testing

## Why This Exists

Vendor-provided KiCad files are often inconsistent, messy, or named in ways that do not match a personal/custom library convention.

This tool is intended to reduce repetitive manual cleanup when importing parts such as:

* footprints
* symbols
* STEP/STP 3D models
* connector libraries
* vendor ZIP exports

The goal is not to replace KiCad’s library management. The goal is to assist with the boring, error-prone parts of organizing custom libraries.

## Intended Library Structure

This project currently assumes a custom KiCad library folder similar to:

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

The project currently separates local config, naming vocabulary, and suggestion rules.

```text
kicad_import_assistant_config.example.json
```

Example user/local configuration. The real local config file is intentionally ignored by Git.

```text
kicad_import_naming_schema.json
```

Naming vocabulary, token sets, field order, normalization rules, and validation rules.

```text
kicad_import_suggestion_rules.json
```

Filename-based suggestion rules used to prefill naming fields during import.

## Current Safety Behavior

This tool is intentionally cautious.

As of **V0.7.0**, the tool can copy and rename selected footprint and STEP/STP model files into the configured target `.pretty` folder, but only after explicit confirmation.

Before writing files, the tool requires the user to type:

```text
IMPORT
```

The tool currently refuses to overwrite existing target files.

After copying a footprint, the tool attempts to update:

* internal footprint name
* footprint `Value` property
* 3D model reference
* hidden import/review metadata fields

The tool currently does **not**:

* merge symbols into `.kicad_sym` libraries
* update symbol `Footprint` properties
* perform full KiCad S-expression validation
* guarantee 3D model orientation
* guarantee pad/schematic correctness
* replace human review

Imported footprints are marked with review metadata fields such as:

```text
ImportedBy
ImportStatus
Needs3DModelValidation
```

## Planned Features

Future goals include:

* Merge symbols into a target `.kicad_sym` file
* Update symbol `Footprint` properties
* Improve duplicate detection
* Add backup/rollback behavior
* Add batch import mode
* Add manifest-driven import mode
* Add stronger validation from naming schema
* Add safer ZIP extraction behavior
* Add optional 3D model transform prompts
* Add a Tkinter dialog-based workflow
* Explore a future KiCad plugin wrapper
* Add a more Sonarr/Radarr-style import review workflow

## Requirements

* Python 3.12 or newer required
* Tkinter, included with most standard Python installs
* Windows currently used for development/testing

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
