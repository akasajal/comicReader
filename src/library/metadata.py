import json
from pathlib import Path

from src.models.series import Series


def save_metadata(series: Series, folder: Path):
    metadata = {
        "title": series.title,
        "url": series.url,
        "author": series.author,
        "status": series.status,
        "genres": series.genres,
        "description": series.description,
        "chapters": len(series.chapters),
    }

    with open(folder / "metadata.json", "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=4, ensure_ascii=False)