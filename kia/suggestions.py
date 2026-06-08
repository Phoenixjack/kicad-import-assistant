import json
import re
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent.parent
SUGGESTION_RULES_PATH = SCRIPT_DIR / "kicad_import_suggestion_rules.json"


DEFAULT_SUGGESTIONS = {
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


def load_suggestion_rules() -> dict:
    """
    Load suggestion rules from kicad_import_suggestion_rules.json.

    If the file is missing or invalid, continue with no rules.
    """
    if not SUGGESTION_RULES_PATH.exists():
        print()
        print(f"Suggestion rules file not found: {SUGGESTION_RULES_PATH}")
        print("Continuing with no suggestion rules.")
        return {"rules": []}

    try:
        with SUGGESTION_RULES_PATH.open("r", encoding="utf-8") as file:
            data = json.load(file)

    except json.JSONDecodeError as error:
        print()
        print(f"Suggestion rules file contains invalid JSON: {SUGGESTION_RULES_PATH}")
        print(error)
        print("Continuing with no suggestion rules.")
        return {"rules": []}

    if "rules" not in data or not isinstance(data["rules"], list):
        print()
        print("Suggestion rules file is missing a valid 'rules' list.")
        print("Continuing with no suggestion rules.")
        return {"rules": []}

    return data


def collect_detected_filename_text(found_files: dict) -> str:
    """
    Collect detected filenames into a single searchable string.
    """
    names = []

    for file_list in found_files.values():
        for file_path in file_list:
            names.append(file_path.name)

    return " ".join(names)


def rule_matches(rule: dict, detected_text: str) -> bool:
    """
    Check whether a suggestion rule matches detected filenames.

    Current behavior:
    - match_any: match if any listed text appears in detected filenames.
    """
    detected_upper = detected_text.upper()

    for pattern in rule.get("match_any", []):
        if str(pattern).upper() in detected_upper:
            return True

    return False


def normalize_extracted_mpn(value: str) -> str:
    """
    Normalize an extracted MPN enough for filename use.

    Example:
    SS_53000_003 -> SS-53000-003
    SS 53000 003 -> SS-53000-003
    """
    cleaned = value.strip()
    cleaned = re.sub(r"[\s_]+", "-", cleaned)
    return cleaned


def apply_extract_rules(rule: dict, detected_text: str, defaults: dict) -> dict:
    """
    Apply regex extraction rules, such as extracting MPN from filenames.
    """
    extract_rules = rule.get("extract", {})

    mpn_regex = extract_rules.get("mpn", "")
    if mpn_regex:
        match = re.search(mpn_regex, detected_text, flags=re.IGNORECASE)
        if match:
            defaults["mpn"] = normalize_extracted_mpn(match.group(1))

    return defaults


def suggest_defaults_from_rules(found_files: dict) -> dict:
    """
    Suggest naming-token defaults using external JSON suggestion rules.
    """
    suggestions = DEFAULT_SUGGESTIONS.copy()
    detected_text = collect_detected_filename_text(found_files)
    rules_data = load_suggestion_rules()

    matched_rules = []

    for rule in rules_data.get("rules", []):
        if rule_matches(rule, detected_text):
            matched_rules.append(rule)

    if not matched_rules:
        return suggestions

    if len(matched_rules) > 1:
        print()
        print("Multiple suggestion rules matched. Using the first one:")
        for rule in matched_rules:
            print(f"  - {rule.get('name', '<unnamed rule>')}")

    selected_rule = matched_rules[0]

    print()
    print("Suggestion rule matched:")
    print(f"  {selected_rule.get('name', '<unnamed rule>')}")

    rule_defaults = selected_rule.get("defaults", {})
    suggestions.update(rule_defaults)

    suggestions = apply_extract_rules(
        rule=selected_rule,
        detected_text=detected_text,
        defaults=suggestions,
    )

    return suggestions