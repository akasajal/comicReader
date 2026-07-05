import json
from pathlib import Path

from src.models.settings import Settings


SETTINGS_FILE = Path("data/settings.json")


def load_settings() -> Settings:
    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)

    default = Settings(
        library_path=Path("data/library")
    )

    if not SETTINGS_FILE.exists() or SETTINGS_FILE.stat().st_size == 0:
        save_settings(default)
        return default

    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        return Settings(
            library_path=Path(data["library_path"]),
            theme=data["theme"],
            fit_mode=data["fit_mode"],
            smooth_scrolling=data["smooth_scrolling"],
            preload_chapters=data["preload_chapters"],
            flaresolverr_url=data.get("flaresolverr_url") or None,
            last_reader_folder=Path(data["last_reader_folder"]) if data.get("last_reader_folder") else None,
        )

    except (json.JSONDecodeError, KeyError):
        save_settings(default)
        return default


def save_settings(settings: Settings) -> None:
    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)

    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(
            {
                "library_path": str(settings.library_path),
                "theme": settings.theme,
                "fit_mode": settings.fit_mode,
                "smooth_scrolling": settings.smooth_scrolling,
                "preload_chapters": settings.preload_chapters,
                "flaresolverr_url": settings.flaresolverr_url,
                "last_reader_folder": str(settings.last_reader_folder) if settings.last_reader_folder else None,
            },
            f,
            indent=4,
        )