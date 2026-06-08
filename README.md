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

Current version: **0.4**

Current features:

* GUI file picker for selecting a vendor ZIP file
* GUI folder picker for selecting the custom KiCad library root
* JSON config support
* Remembers last ZIP folder, library root, and target library
* Safely falls back if remembered folders no longer exist
* Automatically handles accidentally selecting a `.pretty` folder as the library root
* Extracts ZIP files to a temporary folder
* Detects KiCad footprint, symbol, and 3D model files
* Suggests naming defaults for known parts/rules
* Prompts for naming tokens
* Generates a standardized target basename
* Creates a preview manifest CSV
* Does **not** modify KiCad library files yet

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
│  └─ kia/
│     ├─ __init__.py
│     ├─ config.py
│     ├─ dialogs.py
│     ├─ zip_scan.py
│     ├─ naming.py
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

As of version 0.4, it does **not**:

* copy files into the target library
* rename actual library files
* edit `.kicad_mod` files
* edit `.kicad_sym` files
* merge symbols
* update 3D model paths
* update footprint links

It only generates a preview manifest.

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

* Python 3.12 or newer recommended
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

This project was vibe-coded with ChatGPT as a learning/tool-building exercise. It should not be taken as a direct representation of my independent Python programming ability.

Use carefully. Back up your KiCad libraries before testing any version that modifies files.

## License

GNU License V3.0
