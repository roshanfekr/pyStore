def normalize_whitespace(value: str) -> str:
    return " ".join(value.split())


def is_blank(value: str | None) -> bool:
    return value is None or not value.strip()
