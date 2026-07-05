import json
from pathlib import Path


class ReadingHistory:
    def load(self, file: Path) -> dict:
        if not file.exists():
            return {}

        with open(file, "r", encoding="utf-8") as f:
            return json.load(f)

    def save(self, file: Path, history: dict):
        with open(file, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=4)