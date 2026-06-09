from pathlib import Path
from kia.suggestions import suggest_defaults_from_rules
from kia.debug import debug_print


def prompt_with_default(label: str, default: str = "") -> str:
    """
    Prompt the user for a value, allowing Enter to accept a default.
    """
    if default:
        user_input = input(f"{label} [{default}]: ").strip()
        return user_input if user_input else default

    return input(f"{label}: ").strip()


def clean_name_token(value: str) -> str:
    """
    Clean a filename token.

    This is intentionally conservative for now:
    - Strip whitespace
    - Replace spaces with hyphens
    - Remove empty tokens later when building basename
    """
    return value.strip().replace(" ", "-")


def normalize_pitch_token(value: str) -> str:
    """
    Normalize pitch tokens.

    Examples:
    0.50    -> P0.50
    P0.50   -> P0.50
    p0.50   -> P0.50
    2.54mm  -> P2.54
    P2.54mm -> P2.54
    """
    cleaned = value.strip()

    if not cleaned:
        return ""

    cleaned = cleaned.replace(" ", "")
    cleaned = cleaned.replace("mm", "").replace("MM", "")

    if cleaned.upper().startswith("P"):
        cleaned = cleaned[1:]

    return f"P{cleaned}"


def suggest_defaults_from_files(found_files: dict) -> dict:
    """
    Suggest naming-token defaults based on detected filenames.

    Suggestion rules are loaded from kicad_import_suggestion_rules.json.
    """
    return suggest_defaults_from_rules(found_files)


def get_recent_default(config: dict, field_name: str) -> str:
    """
    Return the most recently used value for a naming field, if available.
    """
    recent_values = config.get("recent_values", {})
    values = recent_values.get(field_name, [])

    if not values:
        return ""

    return values[0]


def remember_recent_value(config: dict, field_name: str, value: str, max_count: int = 10) -> None:
    """
    Store a recently used naming value in config.

    Most recent value is kept at the front of the list.
    """
    cleaned = value.strip()

    if not cleaned:
        return

    if "recent_values" not in config:
        config["recent_values"] = {}

    if field_name not in config["recent_values"]:
        config["recent_values"][field_name] = []

    values = config["recent_values"][field_name]

    if cleaned in values:
        values.remove(cleaned)

    values.insert(0, cleaned)

    del values[max_count:]


def normalize_menu_input(user_input: str) -> str:
    """
    Normalize menu text input.

    Most naming tokens are uppercase by convention.
    """
    return user_input.strip().upper()


def get_schema_options(
    naming_schema: dict,
    section_name: str,
) -> dict:
    """
    Get an option dictionary from naming schema.

    Returns an empty dict if the section is missing or not a dict.
    """
    if not naming_schema:
        return {}

    token_sets = naming_schema.get("token_sets", {})
    options = token_sets.get(section_name, {})

    if isinstance(options, dict):
        return options

    return {}


def get_library_options(naming_schema: dict) -> dict:
    """
    Get library/category options from naming schema.

    Expected schema shape:
      "libraries": {
        "CONN": {
          "description": "Connectors",
          ...
        }
      }

    Falls back to empty dict if unavailable.
    """
    libraries = naming_schema.get("libraries", {})

    if not isinstance(libraries, dict):
        return {}

    options = {}

    for key, value in libraries.items():
        if isinstance(value, dict):
            description = value.get("description", "")
        else:
            description = str(value)

        options[key] = description

    return options


def get_family_options_for_library(
    naming_schema: dict,
    library_prefix: str,
) -> dict:
    """
    Get family options for the selected library/category.

    Expected schema shape:
      "libraries": {
        "CONN": {
          "families": {
            "HDMI": "HDMI connectors"
          }
        }
      }
    """
    libraries = naming_schema.get("libraries", {})
    library_data = libraries.get(library_prefix, {})

    if not isinstance(library_data, dict):
        return {}

    families = library_data.get("families", {})

    if not isinstance(families, dict):
        return {}

    return families


def prompt_from_options(
    label: str,
    options: dict,
    default: str = "",
    allow_free_text: bool = True,
) -> str:
    """
    Prompt user from numbered options.

    Allows:
    - Enter to accept default
    - number selection
    - direct token entry
    - free text when enabled
    """
    if not options:
        return prompt_with_default(label, default)

    print()
    print(f"{label} options:")

    option_keys = list(options.keys())

    for index, key in enumerate(option_keys):
        description = options.get(key, "")

        if description:
            print(f"  {index}. {key} - {description}")
        else:
            print(f"  {index}. {key}")

    if default:
        prompt = f"{label} [{default}]: "
    else:
        prompt = f"{label}: "

    while True:
        user_input = input(prompt).strip()

        if not user_input and default:
            return default

        if not user_input:
            return ""

        if user_input.isdigit():
            index = int(user_input)

            if 0 <= index < len(option_keys):
                return option_keys[index]

            print("Choice out of range.")
            continue

        normalized_input = normalize_menu_input(user_input)

        if normalized_input in options:
            return normalized_input

        if allow_free_text:
            return user_input.strip()

        print("Invalid option. Enter a number or listed token.")


def build_basename_from_prompts(config: dict, library_settings: dict, found_files: dict, override_defaults: dict | None = None, suggested_defaults: dict | None = None, naming_schema: dict | None = None,) -> str:
    """
    Ask the user for naming-convention tokens and build the target basename.

    Format:
    LIB_FAMILY_ROLE_MOUNT_ORIENT_SIZE[_PITCH][_BASE][_FEATURE]_MPN
    """
    
    if naming_schema is None:
        naming_schema = {}
    
    if suggested_defaults is None:
        suggested = suggest_defaults_from_files(found_files)
    else:
        suggested = dict(suggested_defaults)

    if override_defaults:
        suggested.update(override_defaults)

    # Use recent values only when suggestion rules did not provide a value.
    for field_name in ["family", "role", "mount", "orient", "size", "pitch", "base", "feature"]:
        if not suggested.get(field_name, ""):
            suggested[field_name] = get_recent_default(config, field_name)
        
    print()
    print("Enter naming tokens.")
    print("Press Enter to accept defaults where shown.")
    print()

    library_options = get_library_options(naming_schema)

    prefix_default = library_settings.get("prefix", "")
    if not prefix_default:
        prefix_default = suggested.get("library", "")

    prefix = prompt_from_options(
        label="Library prefix",
        options=library_options,
        default=prefix_default,
        allow_free_text=True,
    )

    family_options = get_family_options_for_library(
        naming_schema=naming_schema,
        library_prefix=prefix,
    )

    family = prompt_from_options(
        label="Family",
        options=family_options,
        default=suggested["family"],
        allow_free_text=True,
    )

    role_options = get_schema_options(naming_schema, "roles")
    mount_options = get_schema_options(naming_schema, "mounts")
    orientation_options = get_schema_options(naming_schema, "orientations")
    pitch_options = get_schema_options(naming_schema, "common_pitches")

    role = prompt_from_options(
        label="Role",
        options=role_options,
        default=suggested["role"],
        allow_free_text=True,
    )

    mount = prompt_from_options(
        label="Mount",
        options=mount_options,
        default=suggested["mount"],
        allow_free_text=True,
    )

    orient = prompt_from_options(
        label="Orientation",
        options=orientation_options,
        default=suggested["orient"],
        allow_free_text=True,
    )

    size = prompt_with_default("Size", suggested["size"])

    pitch = normalize_pitch_token(
        prompt_from_options(
            label="Pitch",
            options=pitch_options,
            default=suggested["pitch"],
            allow_free_text=True,
        )
    )

    base = prompt_with_default("Base / series", suggested["base"])
    feature = prompt_with_default("Feature", suggested["feature"])
    mpn = prompt_with_default("MPN", suggested["mpn"])
    required_fields = {
        "Library prefix": prefix,
        "Family": family,
        "Role": role,
        "Mount": mount,
        "Orientation": orient,
        "Size": size,
        "MPN": mpn,
    }

    missing = [name for name, value in required_fields.items() if not value.strip()]

    if missing:
        print()
        print("ERROR: Missing required naming fields:")
        for name in missing:
            print(f"  - {name}")
        print()
        raise SystemExit
        
    # Remember recent values after validation succeeds.
    # Do not remember MPN; it is part-specific.
    remember_recent_value(config, "family", family)
    remember_recent_value(config, "role", role)
    remember_recent_value(config, "mount", mount)
    remember_recent_value(config, "orient", orient)
    remember_recent_value(config, "size", size)
    remember_recent_value(config, "pitch", pitch)
    remember_recent_value(config, "base", base)
    remember_recent_value(config, "feature", feature)
    
    tokens = [
        prefix,
        family,
        role,
        mount,
        orient,
        size,
        pitch,
        base,
        feature,
        mpn,
    ]

    cleaned_tokens = [clean_name_token(token) for token in tokens]
    cleaned_tokens = [token for token in cleaned_tokens if token]

    return "_".join(cleaned_tokens)