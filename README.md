# KiCad Import Assistant

KiCad Import Assistant is a small Python utility for importing vendor-provided KiCad symbols, footprints, and 3D models into a custom KiCad library structure.

The tool is being built around a cautious workflow:

1. Select a vendor ZIP file.
2. Select a custom KiCad library root folder.
3. Extract the ZIP to a temporary folder.
4. Detect `.kicad_mod`, `.kicad_sym`, `.step`, and `.stp` files.
5. Prompt for naming-convention fields.
6. Generate a proposed standardized basename.
7. Create a preview manifest.
8. Avoid modifying library files until explicitly confirmed.

## Project Status

Early development / work in progress.

Current version: V0.6.1
- Copies footprint/model files only after IMPORT confirmation
- Does not edit footprint internals yet
- Does not merge symbols yet
- Refuses overwrite
- Naming schema and suggestion rules are drafted but not fully wired in
- Adds hidden import/review metadata fields to copied footprints
- Records importer version in the copied footprint
- Remembers recently used naming-token values for future prompts

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
├─ _TOOLS/
│  ├─ kicad_import_assistant.py
│  ├─ kicad_import_assistant_config.json
   ├─ kicad_import_naming_schema.json
   ├─ kicad_import_suggestion_rules.json
   └─ kia/
│     ├─ __init__.py
│     ├─ config.py
│     ├─ dialogs.py
│     ├─ zip_scan.py
│     ├─ naming.py
      ├─ importer.py
│     └─ manifest.py
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
CONN_HDMI_RCPT_SMD_V_19P_SS53000_SS-53000-003
```

Where:

```text
CONN      Library/category prefix
HDMI      Connector family
RCPT      Receptacle
SMD       Surface mount
V         Vertical/top-entry
19P       19 electrical contacts
SS53000   Base/series
SS-53000-003 Exact manufacturer/orderable part number
```

## Current Safety Behavior

This tool is intentionally cautious.

As of version V0.5.1, it can copy and rename selected footprint and STEP/STP model files into the configured target `.pretty` folder, but only after explicit confirmation.

It currently does **not**:

- edit `.kicad_mod` file contents
- update internal footprint names
- update 3D model references inside footprints
- edit `.kicad_sym` files
- merge symbols
- update symbol `Footprint` properties
- overwrite existing target files

Before writing files, the tool requires the user to type:
```text
IMPORT
```

## Planned Features

Future goals include:

* Copy and rename footprint files
* Copy and rename STEP/STP model files
* Normalize `.stp`, `.STEP`, and `.STP` extensions to `.step`
* Update internal footprint names
* Update footprint 3D model paths
* Merge symbols into a target `.kicad_sym` file
* Update symbol `Footprint` properties
* Add stronger duplicate detection
* Add backup/rollback behavior
* Add batch import mode
* Add manifest-driven import mode
* Add configurable naming rules
* Add a more Sonarr/Radarr-style import review workflow

## Requirements

* Python 3.12 or newer required
* Tkinter, included with most standard Python installs
* Windows currently used for development/testing

No KiCad Python plugin or KiCad CLI integration is currently required.

## Running

From the `_TOOLS` folder:

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

GNU License V3.0
