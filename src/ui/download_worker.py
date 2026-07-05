from pathlib import Path

from PySide6.QtCore import QThread, Signal

from src.downloader.downloader import Downloader
from src.models.chapter import Chapter
from src.models.series import Series


class DownloadWorker(QThread):
    """Downloads a list of chapters on a background thread.

    Signals
    -------
    chapter_started(chapter_index, total_chapters, chapter_title)
    page_progress(current_page, total_pages)
    chapter_done(chapter_index, cbz_path)
    chapter_failed(chapter_index, chapter_title, error_message)
    all_done(completed, failed)
    """

    chapter_started  = Signal(int, int, str)   # idx, total, title
    page_progress    = Signal(int, int)         # current_page, total_pages
    chapter_done     = Signal(int, str)         # idx, cbz_path
    chapter_failed   = Signal(int, str, str)    # idx, title, error
    all_done         = Signal(int, int)         # completed, failed

    def __init__(
        self,
        downloader: Downloader,
        series: Series,
        chapters: list[Chapter],
        output_dir: Path,
    ):
        super().__init__()
        self._downloader = downloader
        self._series = series
        self._chapters = chapters
        self._output_dir = output_dir
        self._abort = False

    def abort(self):
        self._abort = True

    def run(self):
        completed = 0
        failed = 0
        total = len(self._chapters)

        for idx, chapter in enumerate(self._chapters, start=1):
            if self._abort:
                break

            self.chapter_started.emit(idx, total, chapter.title)

            try:
                cbz_path = self._downloader.download_chapter(
                    chapter=chapter,
                    series=self._series,
                    output_dir=self._output_dir,
                    on_progress=lambda cur, tot: self.page_progress.emit(cur, tot),
                )
                self.chapter_done.emit(idx, str(cbz_path))
                completed += 1
            except Exception as exc:
                self.chapter_failed.emit(idx, chapter.title, str(exc))
                failed += 1

        self.all_done.emit(completed, failed)