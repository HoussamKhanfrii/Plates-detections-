import re


OCR_REPLACEMENTS = {
    "O": "0",
    "I": "1",
    "L": "1",
    "S": "5",
    "B": "8",
    "Z": "2",
}


PLATE_PATTERNS = {
    "generic": re.compile(r"^(?=.*[A-Z])(?=.*\d)[A-Z0-9]{4,12}$"),
    "morocco_latin": re.compile(r"^\d{1,6}[A-Z]\d{1,2}$"),
}


def normalize_text(raw_text):
    if raw_text is None:
        return ""
    text = str(raw_text).upper()
    return re.sub(r"[^A-Z0-9]", "", text)


def tokenize_ocr_text(raw_text):
    if raw_text is None:
        return []
    return [
        normalize_text(part)
        for part in re.split(r"[^A-Za-z0-9]+", str(raw_text).upper())
        if normalize_text(part)
    ]


def apply_common_ocr_fixes(text):
    fixed = []
    for index, char in enumerate(text):
        previous_is_digit = index > 0 and text[index - 1].isdigit()
        next_is_digit = index + 1 < len(text) and text[index + 1].isdigit()
        should_fix = char in OCR_REPLACEMENTS and (previous_is_digit or next_is_digit)
        fixed.append(OCR_REPLACEMENTS[char] if should_fix else char)
    return "".join(fixed)


def validate_plate_format(text, country_profile="generic"):
    pattern = PLATE_PATTERNS.get(country_profile, PLATE_PATTERNS["generic"])
    return bool(pattern.match(text))


def extract_plate_candidate(raw_text, country_profile="generic", apply_fixes=True):
    tokens = tokenize_ocr_text(raw_text)
    candidates = []

    for start_index in range(len(tokens)):
        combined = ""
        for end_index in range(start_index, min(start_index + 4, len(tokens))):
            combined += tokens[end_index]
            if not (4 <= len(combined) <= 12):
                continue

            cleaned = apply_common_ocr_fixes(combined) if apply_fixes else combined
            is_valid = validate_plate_format(cleaned, country_profile)
            digit_count = sum(char.isdigit() for char in cleaned)
            letter_count = sum(char.isalpha() for char in cleaned)
            length_score = 1.0 - min(abs(len(cleaned) - 7) / 7, 1.0)
            mix_score = min(digit_count, letter_count) / max(digit_count, letter_count, 1)
            position_score = 1.0 - (start_index * 0.08)
            validity_score = 1.0 if is_valid else 0.0
            score = (
                validity_score * 0.55
                + length_score * 0.22
                + mix_score * 0.18
                + max(position_score, 0) * 0.05
            )

            candidates.append(
                {
                    "candidate": cleaned,
                    "is_valid": is_valid,
                    "score": score,
                }
            )

    if candidates:
        candidates.sort(key=lambda item: item["score"], reverse=True)
        return candidates[0]

    normalized = normalize_text(raw_text)
    cleaned = apply_common_ocr_fixes(normalized) if apply_fixes else normalized
    return {
        "candidate": cleaned,
        "is_valid": validate_plate_format(cleaned, country_profile),
        "score": 0.0,
    }


def clean_plate_text(raw_text, country_profile="generic", apply_fixes=True):
    candidate = extract_plate_candidate(
        raw_text,
        country_profile=country_profile,
        apply_fixes=apply_fixes,
    )

    return {
        "cleaned_plate": candidate["candidate"],
        "is_valid": candidate["is_valid"],
        "country_profile": country_profile,
    }


def score_plate_candidate(cleaned_text, ocr_confidence, is_valid):
    length_score = min(len(cleaned_text) / 8, 1.0) if cleaned_text else 0
    validity_score = 1.0 if is_valid else 0.0
    return (ocr_confidence * 0.55) + (length_score * 0.2) + (validity_score * 0.25)
