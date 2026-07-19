import sys
from pathlib import Path


def resource_path(*parts: str) -> Path:
    """
    Return an absolute Path to a bundled asset.

    When running from source:  resolves relative to this file's directory.
    When frozen by PyInstaller: resolves inside sys._MEIPASS.
    """
    if hasattr(sys, "_MEIPASS"):
        base = Path(sys._MEIPASS)
    else:
        base = Path(__file__).parent

    return base.joinpath(*parts)
