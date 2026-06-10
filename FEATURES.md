# Features

This file describes the current capabilities and known limitations of KiCad Import Assistant.

Current version: **V0.9.0**

## Import Source Handling

The tool can:

* Select a vendor ZIP file using a GUI file picker.
* Extract the ZIP file to a temporary folder.
* Recursively detect:

  * `.kicad_mod`
  * `.kicad_sym`
  * `.step`
  * `.stp`
* Summarize detected import files.
* Select candidate footprint, symbol, and model files for import.

## Config Handling

The tool can:

* Load local JSON configuration.
* Save updated local JSON configuration.
* Remember:

  * last ZIP folder
  * last selected library root
  * last target library
  * recent naming-token values
* Safely fall back when remembered folders no longer exist.
* Correct accidental selection of a `.pretty` folder as the library root.

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
_testlibrary.pretty
└─ _testlibrary.kicad_sym
```

The resolver prefers `_testlibrary.kicad_sym`.

## Naming Workflow

The tool can:

* Load filename-based suggestion rules.
* Load naming vocabulary/options from JSON schema.
* Suggest naming defaults from detected vendor filenames.
* Prompt for naming tokens using schema-driven menus.
* Allow:

  * Enter to accept defaults
  * number selection from menus
  * direct token entry
  * custom/free-text values
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

## Preview Manifest

The tool can optionally create a preview manifest CSV.

The manifest can show:

* source footprint file
* target footprint path
* source model file
* target model path
* source symbol file
* target symbol library path
* intended actions
* notes about pending or performed steps

Manifest creation currently defaults off and can be enabled at runtime.

## Footprint/Model Import

After explicit confirmation, the tool can:

* Copy and rename the selected footprint file.
* Copy and rename the selected STEP/STP model file.
* Refuse to overwrite existing footprint/model files.
* Update the copied footprint internal name.
* Update the copied footprint visible `Value` field.
* Add or update a 3D model reference.
* Add hidden import/review metadata fields.

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
* Preserve the original source symbol file.
* Write the edited preview symbol into the temporary extraction folder.

This preview step happens before the real target symbol library is modified.

## Symbol Merge

The tool can merge the previewed symbol into the resolved target `.kicad_sym` library.

Before merging, the tool:

* Confirms that a target symbol library was resolved.
* Confirms that the target symbol library exists.
* Checks whether the generated symbol name already exists.
* Refuses duplicate symbol merges.
* Creates a timestamped backup of the target symbol library.
* Only merges after the user explicitly types `IMPORT`.

The merge inserts the edited symbol block into the target symbol library before the final library closing parenthesis.

## Backup Behavior

Before modifying a target symbol library, the tool creates a timestamped backup.

Backup filenames intentionally do not end with `.kicad_sym` so the resolver does not mistake them for active KiCad symbol libraries.

Example:

```text
_testlibrary.kicad_sym.20260609_201609.backup
```

## Debug Output

The tool has lightweight debug categories for development/testing.

Current debug categories include areas such as:

```text
config
zip
files
suggestions
tokens
basename
manifest
importer
symbols
schema
info
verbose
```

Debug output is still under active cleanup. Future work may add more structured prefixes, subcategories, and cleaner toggles.

## Current Limitations

The tool currently does not:

* Does not currently query online part databases or distributor APIs.
* Does not currently enrich part metadata from manufacturer part numbers.
* Does not currently auto-suggest naming fields from verified external part data.
* overwrite existing footprint/model files
* overwrite existing symbol definitions
* perform full KiCad S-expression validation
* guarantee 3D model orientation
* validate all pad/pin/schematic correctness
* guarantee compatibility with all KiCad versions
* clean up temporary extraction folders automatically
* provide a full GUI configuration workflow
* operate as a native KiCad plugin

Human review is still required.

## Future Metadata Enrichment Goals

- Add part-class-specific schema profiles so connector, IC, passive, module, power, mechanical, and generic imports can use different prompt vocabularies.
- Separate physical import targets from naming/prompt profiles.
- Avoid using connector-specific role/orientation prompts for non-connector parts.
- Add stronger guardrails for target folders containing multiple active `.kicad_sym` libraries.
- Warn if more than N active .kicad_sym files are found in one .pretty folder.
- Refuse automatic symbol merge if multiple active symbol libraries exist and none matches the .pretty folder name.
- Add an interactive symbol-library selection step when multiple valid target libraries are present.
- Print the candidate list clearly.
- Require the user to pick one manually or fix config.


Future versions may add optional online metadata enrichment.

The intended workflow would be:

1. Detect or ask for a manufacturer part number.
2. Query one or more configured metadata providers.
3. Present the best candidate match to the user.
4. Allow the user to accept, reject, or manually override the result.
5. Use accepted metadata to prefill naming fields and symbol properties.
6. Ask manual questions only for fields that could not be confidently inferred.

Possible metadata sources may include provider APIs such as Nexar/Octopart, DigiKey, Mouser, SnapMagic/SnapEDA, or other structured part-data services.

Potential fields to enrich:

* manufacturer
* manufacturer part number
* short description
* datasheet URL
* product page URL
* package/case
* contact count or pin count
* pitch
* mount style
* orientation
* base series
* lifecycle/status
* RoHS/REACH data
* distributor SKUs

Metadata enrichment should remain optional. The core importer should continue working offline from local files alone.

External metadata should be treated as a suggestion requiring user review, not as unquestioned truth. Geometry, pin mapping, footprint correctness, 3D model orientation, and schematic correctness should still require human validation.
