"""Misc. string related utilities."""


def remove_prefix(text: str, prefix: str) -> str:
    """Removes the prefix from the string if it exists, and returns the result."""
    if text.startswith(prefix):
        return text[len(prefix):]
    return text


def remove_suffix(text: str, suffix: str) -> str:
    """Removes the suffix from the string if it exists, and returns the result."""
    if suffix != "" and text.endswith(suffix):
        return text[:-len(suffix)]
    return text
