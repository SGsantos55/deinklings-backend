MAX_TAGS = 6
MAX_TAG_LEN = 40

# camelCase API field -> (column name, validator key)
TEXT_RULES = {
    "title": ("Title", 1, 120),
    "format": ("Format", 1, None),
    "genre": ("Genre", 1, None),
    "body": ("Story text", 200, 200000),
    "logline": ("Logline", 10, 160),
    "synopsis": ("Synopsis", 80, 2000),
}
FLAG_FIELDS = {
    "openToAdaptation": "open_to_adaptation",
    "openToCollaboration": "open_to_collaboration",
    "openToLicensing": "open_to_licensing",
}
FLAG_DEFAULTS = {"openToAdaptation": True, "openToCollaboration": False, "openToLicensing": False}


def _text(data, key):
    label, lo, hi = TEXT_RULES[key]
    value = data.get(key)
    if not isinstance(value, str):
        return None, f"{label} is required"
    value = value.strip()
    if len(value) < lo or (hi is not None and len(value) > hi):
        if hi is None:
            return None, f"{label} is required"
        return None, f"{label} must be between {lo} and {hi} characters"
    return value, None


def _string_list(value, label):
    if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
        return None, f"{label} must be a list of strings"
    return [v.strip() for v in value if v.strip()], None


def validate_listing(data, partial=False):
    """Return (clean_columns, error_message). In partial mode only supplied keys are checked."""
    clean = {}

    for key in TEXT_RULES:
        if key not in data:
            if partial:
                continue
        value, err = _text(data, key)
        if err:
            return None, err
        clean[key] = value

    if "mood" in data:
        if not isinstance(data["mood"], str):
            return None, "Mood must be text"
        clean["mood"] = data["mood"].strip()
    elif not partial:
        clean["mood"] = ""

    if "tags" in data:
        tags, err = _string_list(data["tags"], "Tags")
        if err:
            return None, err
        if len(tags) > MAX_TAGS:
            return None, f"You can add at most {MAX_TAGS} tags"
        if any(len(t) > MAX_TAG_LEN for t in tags):
            return None, f"Each tag must be at most {MAX_TAG_LEN} characters"
        clean["tags"] = tags
    elif not partial:
        clean["tags"] = []

    if "mediums" in data or not partial:
        mediums, err = _string_list(data.get("mediums", []), "Mediums")
        if err:
            return None, err
        if not mediums:
            return None, "Pick at least one medium"
        clean["mediums"] = mediums

    for key, column in FLAG_FIELDS.items():
        if key in data:
            if not isinstance(data[key], bool):
                return None, f"{key} must be true or false"
            clean[column] = data[key]
        elif not partial:
            clean[column] = FLAG_DEFAULTS[key]

    return clean, None
