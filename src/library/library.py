from pathlib import Path

from src.models.series import Series
from src.models.settings import Settings
from src.services.filesystem import safe_filename


class Library:
    def __init__(self, settings: Settings):
        self.settings = settings

    @property
    def root(self) -> Path:
        return self.settings.library_path

    def create_series(self, series: Series) -> Path:
        path = self.root / safe_filename(series.title)

        path.mkdir(parents=True, exist_ok=True)

        return path