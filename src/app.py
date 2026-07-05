import logging
import sys

from PySide6.QtWidgets import QApplication

from src.services.settings import load_settings
from src.ui.main_window import MainWindow
from src.utils.theme import load_theme

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("comic_reader.log", encoding="utf-8"),
    ],
)
# Keep third-party libs quieter.
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("requests").setLevel(logging.WARNING)


class ComicReaderApp:
    def __init__(self):
        self.app = QApplication([])
        self.app.setStyleSheet(load_theme("cherry_blossom"))
        self.settings = load_settings()
        self.window = MainWindow(self.settings)

    def run(self):
        self.window.show()
        self.app.exec()