"""CBZ / folder loader for the reader."""
import re
import zipfile
from pathlib import Path


IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}


def _cbz_sort_key(p: Path) -> tuple:
    """Numeric sort: Chapter_0090 → (90, 0), Chapter_0090-60 → (90, 60)."""
    m = re.fullmatch(r"Chapter[_-]0*(\d+)[_-]0*(\d+)", p.stem, re.IGNORECASE)
    if m:
        return (int(m.group(1)), int(m.group(2)))
    m2 = re.fullmatch(r"Chapter[_-]0*(\d+)", p.stem, re.IGNORECASE)
    if m2:
        return (int(m2.group(1)), 0)
    return (float("inf"), 0, p.stem)


def list_cbz_files(folder: Path) -> list[Path]:
    """Return .cbz files in *folder*, sorted numerically by chapter number."""
    return sorted(
        (p for p in folder.iterdir() if p.suffix.lower() == ".cbz"),
        key=_cbz_sort_key,
    )


def load_pages(cbz_path: Path) -> list[bytes]:
    """Extract and return image bytes from a CBZ, in page order."""
    with zipfile.ZipFile(cbz_path, "r") as zf:
        names = sorted(
            n for n in zf.namelist()
            if Path(n).suffix.lower() in IMAGE_EXTS
        )
        return [zf.read(name) for name in names]