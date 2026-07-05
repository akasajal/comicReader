import re


INVALID = r'[<>:"/\\|?*]'


def safe_filename(name: str) -> str:
    return re.sub(INVALID, "_", name).strip()