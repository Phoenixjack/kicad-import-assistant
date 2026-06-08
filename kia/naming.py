from pathlib import Path


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


def suggest_defaults_from_files(found_files: dict) -> dict:
    """
    Suggest naming-token defaults based on detected filenames.

    This is intentionally simple for now. Later this can become a smarter
    rule/config system.
    """
    all_names = []

    for file_list in found_files.values():
        for file_path in file_list:
            all_names.append(file_path.name)

    combined_names = " ".join(all_names).upper()

    defaults = {
        "family": "",
        "role": "",
        "mount": "",
        "orient": "",
        "size": "",
        "pitch": "",
        "base": "",
        "feature": "",
        "mpn": "",
    }

    if "SS-53000-003" in combined_names:
        defaults.update({
            "family": "HDMI",
            "role": "RCPT",
            "mount": "SMD",
            "orient": "V",
            "size": "19P",
            "base": "SS53000",
            "mpn": "SS-53000-003",
        })
    elif "SS-53000-002" in combined_names:
        defaults.update({
            "family": "HDMI",
            "role": "RCPT",
            "mount": "SMD",
            "orient": "RA",
            "size": "19P",
            "base": "SS53000",
            "mpn": "SS-53000-002",
        })
    elif "SS-53000-001" in combined_names:
        defaults.update({
            "family": "HDMI",
            "role": "RCPT",
            "mount": "SMD",
            "orient": "RA",
            "size": "19P",
            "base": "SS53000",
            "mpn": "SS-53000-001",
        })

    return defaults


def build_basename_from_prompts(config: dict, library_settings: dict, found_files: dict) -> str:
    """
    Ask the user for naming-convention tokens and build the target basename.

    Format:
    LIB_FAMILY_ROLE_MOUNT_ORIENT_SIZE[_PITCH][_BASE][_FEATURE]_MPN
    """
    suggested = suggest_defaults_from_files(found_files)

    print()
    print("Enter naming tokens.")
    print("Press Enter to accept defaults where shown.")
    print()

    prefix = prompt_with_default(
        "Library prefix",
        library_settings.get("prefix", "CONN"),
    )

    family = prompt_with_default("Family", suggested["family"])
    role = prompt_with_default("Role", suggested["role"])
    mount = prompt_with_default("Mount", suggested["mount"])
    orient = prompt_with_default("Orientation", suggested["orient"])
    size = prompt_with_default("Size", suggested["size"])
    pitch = prompt_with_default("Pitch", suggested["pitch"])
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