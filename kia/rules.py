import json
from pathlib import Path
from kia.debug import debug_print


SCRIPT_DIR = Path(__file__).resolve().parent.parent
RULES_PATH = SCRIPT_DIR / "kicad_import_naming_rules.json"


DEFAULT_NAMING_DEFAULTS = {
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


def load_naming_rules() -> dict:
    """
    Load naming rules from kicad_import_naming_rules.json.

    If the rules file is missing or invalid, return an empty rule set.
    """
    if not RULES_PATH.exists():
        debug_print("rules", "")
        debug_print("rules", f"Naming rules file not found: {RULES_PATH}")
        debug_print("rules", "Continuing with no naming rules.")
        return {"rules": []}

    try:
        with RULES_PATH.open("r", encoding="utf-8") as file:
            rules = json.load(file)

        if "rules" not in rules or not isinstance(rules["rules"], list):
            debug_print("rules", "")
            debug_print("rules", "Naming rules file is missing a valid 'rules' list.")
            debug_print("rules", "Continuing with no naming rules.")
            return {"rules": []}

        return rules

    except json.JSONDecodeError as error:
        debug_print("rules", "")
        debug_print("rules", f"Naming rules file contains invalid JSON: {RULES_PATH}")
        debug_print("rules", error)
        debug_print("rules", "Continuing with no naming rules.")
        return {"rules": []}


def collect_detected_names(found_files: dict) -> str:
    """
    Collect detected filenames into one uppercase search string.
    """
    all_names = []

    for file_list in found_files.values():
        for file_path in file_list:
            all_names.append(file_path.name)

    return " ".join(all_names).upper()


def rule_matches(rule: dict, combined_names: str) -> bool:
    """
    Check whether a rule matches detected filenames.

    Current behavior:
    - match_any: rule matches if any listed text appears in filenames.
    """
    match_any = rule.get("match_any", [])

    for pattern in match_any:
        if str(pattern).upper() in combined_names:
            return True

    return False


def suggest_defaults_from_rules(found_files: dict) -> dict:
    """
    Suggest naming defaults using external naming rules.
    """
    print("I'M IN THE RULES!")
    defaults = DEFAULT_NAMING_DEFAULTS.copy()
    rules_data = load_naming_rules()
    combined_names = collect_detected_names(found_files)

    matched_rules = []

    for rule in rules_data.get("rules", []):
        if rule_matches(rule, combined_names):
            matched_rules.append(rule)

    if not matched_rules:
        return defaults

    if len(matched_rules) > 1:
        debug_print("rules", "")
        debug_print("rules", "Multiple naming rules matched. Using the first one:")
        for rule in matched_rules:
            debug_print("rules", f"  - {rule.get('name', '<unnamed rule>')}")

    selected_rule = matched_rules[0]
    rule_defaults = selected_rule.get("defaults", {})

    defaults.update(rule_defaults)

    debug_print("rules", "")
    debug_print("rules", "Naming rule matched:")
    debug_print("rules", f"  {selected_rule.get('name', '<unnamed rule>')}")

    return defaults