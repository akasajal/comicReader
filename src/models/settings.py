from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class Settings:
    library_path: Path

    theme: str = "dark"

    fit_mode: str = "width"      # width | height | original

    smooth_scrolling: bool = True

    preload_chapters: int = 1

    flaresolverr_url: str | None = None  # e.g. "http://localhost:8191"

    last_reader_folder: Path | None = None