from PySide6.QtCore import Qt, QThread, QTimer, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtSvgWidgets import QSvgWidget
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget,
    QLabel,
    QPushButton,
    QLineEdit,
    QFrame,
    QFileDialog,
    QMessageBox,
    QVBoxLayout,
    QHBoxLayout,
    QSizePolicy,
    QScrollArea,
)

from src.downloader.analyzer import Analyzer
from src.downloader.downloader import Downloader
from src.ui.chapter_select_dialog import ChapterSelectDialog
from src.ui.download_worker import DownloadWorker
from src.downloader.exceptions import UnsupportedWebsiteError
from src.models.series import Series
from src.models.settings import Settings
from src.utils.format import format_size
from src.utils.url import normalize_url


class AnalyzerWorker(QThread):
    """Runs Analyzer.analyze() on a background thread.

    Emits:
      progress(str)          — human-readable step update
      finished(Series)       — analysis succeeded
      failed(str, bool)      — message + is_unsupported flag
    """

    progress = Signal(str)
    finished = Signal(object)
    failed   = Signal(str, bool)

    def __init__(self, analyzer: Analyzer, url: str):
        super().__init__()
        self._analyzer = analyzer
        self._url = url

    def run(self):
        try:
            # Patch the http client to forward step signals.
            # We wrap the real get() so we can emit before each call.
            original_get = self._analyzer.http.get

            call_count = [0]

            def instrumented_get(url, **kwargs):
                call_count[0] += 1
                if call_count[0] == 1:
                    self.progress.emit("Fetching series page via FlareSolverr…")
                elif call_count[0] == 2:
                    self.progress.emit("Fetching sample chapter for size estimation…")
                else:
                    self.progress.emit(f"Network request {call_count[0]}…")
                return original_get(url, **kwargs)

            self._analyzer.http.get = instrumented_get

            self.progress.emit("Connecting to FlareSolverr…")
            series = self._analyzer.analyze(self._url)
            self.progress.emit("Parsing series metadata…")
            self.finished.emit(series)

        except UnsupportedWebsiteError as e:
            self.failed.emit(str(e), True)
        except Exception as e:
            self.failed.emit(str(e), False)
        finally:
            # Always restore the original method.
            try:
                self._analyzer.http.get = original_get
            except UnboundLocalError:
                pass


class DownloaderPage(QWidget):
    switch_to_reader = Signal()

    def __init__(self, settings: Settings):
        super().__init__()

        self.settings = settings
        self._series = None
        self.analyzer = Analyzer(flaresolverr_url=settings.flaresolverr_url)
        self.downloader = Downloader(self.analyzer.http)

        self._elapsed_seconds = 0
        self._elapsed_timer = QTimer(self)
        self._elapsed_timer.setInterval(1000)
        self._elapsed_timer.timeout.connect(self._tick_elapsed)
        self._current_step = ""

        self.build_ui()

    def build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(16)

        # ── Header: logo + title/subtitle ───────────────────────────────
        header_row = QHBoxLayout()
        header_row.setSpacing(14)

        self.logo_label = QSvgWidget("assets/icons/logo.svg")
        self.logo_label.setObjectName("logoBox")
        self.logo_label.setFixedSize(52, 52)

        title_col = QVBoxLayout()
        title_col.setSpacing(2)

        title = QLabel("Comic Reader")
        title.setObjectName("pageTitle")

        subtitle = QLabel("Paste a series URL to fetch and save chapters for offline reading.")
        subtitle.setObjectName("pageSubtitle")

        title_col.addWidget(title)
        title_col.addWidget(subtitle)

        header_row.addWidget(self.logo_label)
        header_row.addLayout(title_col)
        header_row.addStretch()

        reader_btn = QPushButton("📖  Reader")
        reader_btn.setObjectName("readerSwitchBtn")
        reader_btn.setFixedWidth(110)
        reader_btn.setCursor(Qt.PointingHandCursor)
        reader_btn.clicked.connect(self.switch_to_reader)
        header_row.addWidget(reader_btn)

        layout.addLayout(header_row)

        # ── URL card ─────────────────────────────────────────────────────
        url_card = QFrame()
        url_card.setObjectName("card")

        url_layout = QVBoxLayout(url_card)
        url_layout.setContentsMargins(18, 14, 18, 14)
        url_layout.setSpacing(8)

        url_label = QLabel("Series URL")
        url_label.setObjectName("fieldLabel")

        input_row = QHBoxLayout()
        input_row.setSpacing(10)

        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://mangasite.com/series/example")
        self.url_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.url_input.returnPressed.connect(self.analyze_series)

        self.analyze_btn = QPushButton("Analyze")
        self.analyze_btn.setObjectName("analyzeBtn")
        self.analyze_btn.setFixedWidth(110)
        self.analyze_btn.setCursor(Qt.PointingHandCursor)
        self.analyze_btn.clicked.connect(self.analyze_series)

        input_row.addWidget(self.url_input)
        input_row.addWidget(self.analyze_btn)

        url_layout.addWidget(url_label)
        url_layout.addLayout(input_row)

        layout.addWidget(url_card)

        # ── Series info card ─────────────────────────────────────────────
        info_card = QFrame()
        info_card.setObjectName("card")

        info_card_layout = QVBoxLayout(info_card)
        info_card_layout.setContentsMargins(0, 0, 0, 0)
        info_card_layout.setSpacing(0)

        # Title bar
        info_heading = QLabel("Series Information")
        info_heading.setObjectName("sectionTitle")
        info_heading.setContentsMargins(18, 14, 18, 14)

        info_card_layout.addWidget(info_heading)

        # Divider under heading
        top_div = QFrame()
        top_div.setObjectName("divider")
        top_div.setFrameShape(QFrame.HLine)
        info_card_layout.addWidget(top_div)

        # Body: cover art left, metadata right
        body_row = QHBoxLayout()
        body_row.setContentsMargins(18, 18, 18, 18)
        body_row.setSpacing(20)

        # Cover art — framed box
        cover_frame = QFrame()
        cover_frame.setObjectName("coverFrame")
        cover_frame.setFixedSize(164, 224)

        cover_frame_layout = QVBoxLayout(cover_frame)
        cover_frame_layout.setContentsMargins(2, 2, 2, 2)
        cover_frame_layout.setSpacing(0)

        self.cover_label = QLabel()
        self.cover_label.setObjectName("coverArt")
        self.cover_label.setFixedSize(160, 220)
        self.cover_label.setAlignment(Qt.AlignCenter)
        self.cover_label.setText("cover art")

        cover_frame_layout.addWidget(self.cover_label)

        # Right side: two metadata columns
        self.title_value   = QLabel("—")
        self.author_value  = QLabel("—")
        self.genre_value   = QLabel("—")
        self.status_value  = QLabel("—")
        self.chapter_value = QLabel("—")
        self.size_value    = QLabel("—")

        left_col = QVBoxLayout()
        left_col.setSpacing(12)
        left_col.setAlignment(Qt.AlignTop)
        for field, value in [
            ("Title",  self.title_value),
            ("Author", self.author_value),
            ("Genre",  self.genre_value),
        ]:
            left_col.addLayout(self._info_row(field, value))

        right_col = QVBoxLayout()
        right_col.setSpacing(12)
        right_col.setAlignment(Qt.AlignTop)
        for field, value in [
            ("Status",         self.status_value),
            ("Chapters",       self.chapter_value),
            ("Estimated Size", self.size_value),
        ]:
            right_col.addLayout(self._info_row(field, value))

        meta_cols = QHBoxLayout()
        meta_cols.setSpacing(32)
        meta_cols.addLayout(left_col, 1)
        meta_cols.addLayout(right_col, 1)

        # Description in a fixed-height scroll area so it never bloats the card
        self.desc_value = QLabel("—")
        self.desc_value.setObjectName("fieldValue")
        self.desc_value.setWordWrap(True)
        self.desc_value.setAlignment(Qt.AlignTop)
        self.desc_value.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        desc_scroll = QScrollArea()
        desc_scroll.setObjectName("descScroll")
        desc_scroll.setWidget(self.desc_value)
        desc_scroll.setWidgetResizable(True)
        desc_scroll.setFixedHeight(80)
        desc_scroll.setFrameShape(QFrame.NoFrame)
        desc_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        desc_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        desc_row = QHBoxLayout()
        desc_row.setSpacing(8)
        desc_lbl = QLabel("Description:")
        desc_lbl.setObjectName("fieldLabel")
        desc_lbl.setFixedWidth(120)
        desc_lbl.setAlignment(Qt.AlignTop)
        desc_lbl.setContentsMargins(0, 4, 0, 0)
        desc_row.addWidget(desc_lbl)
        desc_row.addWidget(desc_scroll, 1)

        right_side = QVBoxLayout()
        right_side.setSpacing(14)
        right_side.setAlignment(Qt.AlignTop)
        right_side.addLayout(meta_cols)
        right_side.addLayout(desc_row)

        body_row.addWidget(cover_frame, 0, Qt.AlignTop)
        body_row.addLayout(right_side, 1)

        info_card_layout.addLayout(body_row)

        # Divider above download button
        bottom_div = QFrame()
        bottom_div.setObjectName("divider")
        bottom_div.setFrameShape(QFrame.HLine)
        info_card_layout.addWidget(bottom_div)

        # Full-width download button
        self.download_btn = QPushButton("Select Chapters to Download")
        self.download_btn.setObjectName("downloadBtn")
        self.download_btn.setCursor(Qt.PointingHandCursor)
        self.download_btn.setEnabled(False)
        self.download_btn.setFixedHeight(42)
        self.download_btn.setContentsMargins(0, 0, 0, 0)
        self.download_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self.download_btn.clicked.connect(self._open_chapter_select)
        info_card_layout.addWidget(self.download_btn)

        layout.addWidget(info_card)

        # ── Activity card ────────────────────────────────────────────────
        activity_card = QFrame()
        activity_card.setObjectName("card")

        activity_layout = QVBoxLayout(activity_card)
        activity_layout.setContentsMargins(18, 14, 18, 14)
        activity_layout.setSpacing(6)

        activity_label = QLabel("Activity")
        activity_label.setObjectName("fieldLabel")

        self.status_label = QLabel("Waiting for analysis.")
        self.status_label.setObjectName("statusText")
        self.status_label.setWordWrap(True)

        activity_layout.addWidget(activity_label)
        activity_layout.addWidget(self.status_label)

        layout.addWidget(activity_card)
        layout.addStretch()

    # ── Helpers ──────────────────────────────────────────────────────────

    def _info_row(self, label: str, value_label: QLabel) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(8)

        lbl = QLabel(f"{label}:")
        lbl.setObjectName("fieldLabel")
        lbl.setFixedWidth(120)

        value_label.setObjectName("fieldValue")
        value_label.setWordWrap(True)

        row.addWidget(lbl)
        row.addWidget(value_label, 1)

        return row

    def _set_cover(self, pixmap: QPixmap | None):
        if pixmap and not pixmap.isNull():
            self.cover_label.setPixmap(
                pixmap.scaled(
                    self.cover_label.size(),
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation,
                )
            )
            self.cover_label.setText("")
        else:
            self.cover_label.setPixmap(QPixmap())
            self.cover_label.setText("cover art")

    def _load_cover_pixmap(self, cover_url: str | None) -> QPixmap | None:
        if not cover_url:
            return None
        try:
            # Cover art is a CDN image, not a Cloudflare-protected page —
            # use get_direct so we get raw image bytes, not solver HTML.
            response = self.analyzer.http.get_direct(cover_url)
        except Exception:
            return None
        pixmap = QPixmap()
        if not pixmap.loadFromData(response.content):
            return None
        return pixmap

    def _tick_elapsed(self):
        self._elapsed_seconds += 1
        self.status_label.setText(
            f"{self._current_step} ({self._elapsed_seconds}s)"
        )

    def _set_step(self, step: str):
        self._current_step = step
        self.status_label.setText(
            f"{step} ({self._elapsed_seconds}s)"
        )

    # ── Slots ────────────────────────────────────────────────────────────

    def analyze_series(self):
        url = normalize_url(self.url_input.text())

        if not url:
            self.status_label.setText("Please enter a series URL.")
            QMessageBox.warning(self, "Missing URL", "Please paste a series URL.")
            return

        self._elapsed_seconds = 0
        self._current_step = "Starting…"
        self.status_label.setText("Starting…")
        self._elapsed_timer.start()

        self.analyze_btn.setEnabled(False)
        self.download_btn.setEnabled(False)

        self._worker = AnalyzerWorker(self.analyzer, url)
        self._worker.progress.connect(self._set_step)
        self._worker.finished.connect(self._on_analysis_done)
        self._worker.failed.connect(self._on_analysis_failed)
        self._worker.start()

    def _on_analysis_done(self, series: Series):
        self._series = series
        self._elapsed_timer.stop()

        self.title_value.setText(series.title)
        self.author_value.setText(series.author or "Unknown")
        self.chapter_value.setText(str(series.total_chapters))
        self.size_value.setText(format_size(series.estimated_size))
        self.status_value.setText(series.status or "Unknown")
        self.genre_value.setText(", ".join(series.genres) if series.genres else "Unknown")
        self.desc_value.setText(series.description or "No description available.")

        self._set_cover(self._load_cover_pixmap(series.cover_url))

        self.download_btn.setEnabled(True)
        self.analyze_btn.setEnabled(True)
        self.status_label.setText(
            f"Found {series.total_chapters} chapter(s). Ready to download."
        )

    def _open_chapter_select(self):
        if not self._series:
            return

        dialog = ChapterSelectDialog(self._series.chapters, parent=self)
        if not dialog.exec():
            return

        selected = dialog.selected_chapters()
        if not selected:
            return

        # Ask where to save.
        folder = QFileDialog.getExistingDirectory(
            self,
            "Choose download folder",
            str(Path.home()),
        )
        if not folder:
            return

        self._start_download(selected, Path(folder))

    def _start_download(self, chapters, output_dir: Path):
        total = len(chapters)
        self.analyze_btn.setEnabled(False)
        self.status_label.setText(f"Starting download of {total} chapter(s)…")

        # Flip the button into cancel mode.
        self.download_btn.setText("Cancel Download")
        self.download_btn.setEnabled(True)
        self.download_btn.clicked.disconnect()
        self.download_btn.clicked.connect(self._cancel_download)

        self._dl_worker = DownloadWorker(
            downloader=self.downloader,
            series=self._series,
            chapters=chapters,
            output_dir=output_dir,
        )
        self._dl_worker.chapter_started.connect(self._on_chapter_started)
        self._dl_worker.page_progress.connect(self._on_page_progress)
        self._dl_worker.chapter_done.connect(self._on_chapter_done)
        self._dl_worker.chapter_failed.connect(self._on_chapter_failed)
        self._dl_worker.all_done.connect(self._on_download_all_done)
        self._dl_worker.start()

    def _cancel_download(self):
        if hasattr(self, "_dl_worker") and self._dl_worker.isRunning():
            self._dl_worker.abort()
            self.download_btn.setEnabled(False)
            self.status_label.setText("Cancelling… finishing current chapter.")

    # ── Download progress slots ───────────────────────────────────────────

    def _on_chapter_started(self, idx: int, total: int, title: str):
        self.status_label.setText(f"[{idx}/{total}] Downloading: {title}…")

    def _on_page_progress(self, current: int, total: int):
        current_text = self.status_label.text().split(" — ")[0]
        self.status_label.setText(f"{current_text} — page {current}/{total}")

    def _on_chapter_done(self, idx: int, cbz_path: str):
        pass  # chapter_started already updated the label; all_done will summarise

    def _on_chapter_failed(self, idx: int, title: str, error: str):
        # Log but keep going — all_done will report the tally.
        self.status_label.setText(f"Chapter '{title}' failed: {error}")

    def _on_download_all_done(self, completed: int, failed: int):
        # Restore button to its normal state.
        self.download_btn.setText("Select Chapters to Download")
        self.download_btn.setEnabled(True)
        self.download_btn.clicked.disconnect()
        self.download_btn.clicked.connect(self._open_chapter_select)
        self.analyze_btn.setEnabled(True)

        parts = [f"{completed} chapter(s) downloaded"]
        if failed:
            parts.append(f"{failed} failed")
        self.status_label.setText("  ·  ".join(parts) + ".")

    def _on_analysis_failed(self, message: str, is_unsupported: bool):
        self._elapsed_timer.stop()
        self.analyze_btn.setEnabled(True)
        if is_unsupported:
            self.status_label.setText("Unsupported website.")
            QMessageBox.warning(self, "Unsupported Website", message)
        else:
            self.status_label.setText(message)
            QMessageBox.critical(self, "Analysis Failed", message)