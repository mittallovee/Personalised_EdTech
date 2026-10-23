import unicodedata


def no_control_characters(text: str) -> str:
    """Refuse control characters (NUL, newline, tab, bell...). PostgreSQL cannot store NUL, and the
    others would break a one-line name in a picker. Zero-width joiners (category Cf), which Indian
    scripts need, are not control characters and stay allowed."""
    if any(unicodedata.category(char) == "Cc" for char in text):
        raise ValueError("Control characters (such as a new line or tab) are not allowed.")
    return text
