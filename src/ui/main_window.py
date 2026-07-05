from PySide6.QtWidgets import QMainWindow, QStackedWidget

from src.models.settings import Settings
from src.ui.downloader_page import DownloaderPage
from src.ui.reader_page import ReaderPage


class MainWindow(QMainWindow):
    def __init__(self, settings: Settings):
        super().__init__()
        self.setWindowTitle("Comic Reader")
        self.resize(1280, 960)

        self._stack = QStackedWidget()
        self.setCentralWidget(self._stack)

        self._downloader = DownloaderPage(settings)
        self._reader = ReaderPage(settings)

        self._stack.addWidget(self._downloader)   # 0
        self._stack.addWidget(self._reader)        # 1

        # Wire toggle signals
        self._downloader.switch_to_reader.connect(self._go_reader)
        self._reader.switch_to_downloader.connect(self._go_downloader)

    def _go_reader(self):
        self._stack.setCurrentIndex(1)
        self._reader.setFocus()

    def _go_downloader(self):
        self._stack.setCurrentIndex(0)