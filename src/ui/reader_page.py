from pathlib import Path

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QPixmap, QKeyEvent, QWheelEvent, QIcon
from PySide6.QtCore import QSize
from PySide6.QtWidgets import (
    QWidget, QLabel, QPushButton, QListWidget, QListWidgetItem,
    QVBoxLayout, QHBoxLayout, QFrame, QScrollArea, QSizePolicy,
    QFileDialog, QSplitter, QStackedWidget,
)

from src.reader.cbz_loader import list_cbz_files, load_pages
from src.models.settings import Settings
from src.services.settings import save_settings


# ── Icon helper ──────────────────────────────────────────────────────────

def _icon(name: str, size: int = 16, tint: str | None = None) -> QIcon:
    from PySide6.QtGui import QPainter, QColor
    path = f"assets/icons/{name}.svg"
    px = QPixmap(path)
    if px.isNull():
        return QIcon()
    px = px.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    if tint:
        tinted = QPixmap(px.size())
        tinted.fill(Qt.transparent)
        p = QPainter(tinted)
        p.drawPixmap(0, 0, px)
        p.setCompositionMode(QPainter.CompositionMode_SourceIn)
        p.fillRect(tinted.rect(), QColor(tint))
        p.end()
        return QIcon(tinted)
    return QIcon(px)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _chapter_display_name(stem: str) -> str:
    """Turn "Chapter_0042" → "Chapter 42", leave unknown stems as-is."""
    import re
    m = re.fullmatch(r"Chapter[_-]0*(\d+)", stem, re.IGNORECASE)
    if m:
        return f"Chapter {m.group(1)}"
    # decimal: Chapter_0090-50 → Chapter 90.50
    m2 = re.fullmatch(r"Chapter[_-]0*(\d+)[_-](\d+)", stem, re.IGNORECASE)
    if m2:
        decimal = m2.group(2).rstrip('0')
        return f"Chapter {m2.group(1)}.{decimal}" if decimal else f"Chapter {m2.group(1)}"
    return stem


# ── Background page loader ────────────────────────────────────────────────

class PageLoaderWorker(QThread):
    done   = Signal(list)   # list[bytes]
    failed = Signal(str)

    def __init__(self, cbz_path: Path):
        super().__init__()
        self._path = cbz_path

    def run(self):
        try:
            self.done.emit(load_pages(self._path))
        except Exception as e:
            self.failed.emit(str(e))


# ── Page view (scrollable canvas of stacked images) ───────────────────

class PageView(QScrollArea):
    """Renders all pages of a chapter as a single stitched QPixmap."""

    min_width_needed = Signal(int)   # emitted after stitch with required window width

    def __init__(self):
        super().__init__()
        self.setWidgetResizable(False)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setFrameShape(QFrame.NoFrame)
        self.setObjectName("pageView")

        self._canvas = QLabel()
        self._canvas.setAlignment(Qt.AlignTop | Qt.AlignHCenter)
        self._canvas.setStyleSheet("background: transparent; border: none; padding: 0px; margin: 0px;")
        self.setWidget(self._canvas)

        self._fit_mode = "original"
        self._raw_pixmaps: list[QPixmap] = []

        from PySide6.QtCore import QTimer
        self._resize_timer = QTimer(self)
        self._resize_timer.setSingleShot(True)
        self._resize_timer.timeout.connect(self._stitch_and_display)

    # ── public ───────────────────────────────────────────────────────

    def load_pages(self, pages: list[bytes]):
        self._raw_pixmaps = []
        for data in pages:
            px = QPixmap()
            px.loadFromData(data)
            if not px.isNull():
                self._raw_pixmaps.append(px)

        self._stitch_and_display()
        self.verticalScrollBar().setValue(0)

    def set_fit_mode(self, mode: str):
        self._fit_mode = mode
        self._stitch_and_display()

    def page_count(self) -> int:
        return len(self._raw_pixmaps)

    # ── internal ─────────────────────────────────────────────────────

    def _scaled_pixmaps(self) -> list[QPixmap]:
        if not self._raw_pixmaps:
            return []
        vw = self.viewport().width()
        vh = self.viewport().height()
        out = []
        for px in self._raw_pixmaps:
            if self._fit_mode == "width":
                out.append(px.scaledToWidth(vw, Qt.SmoothTransformation))
            elif self._fit_mode == "height":
                out.append(px.scaledToHeight(vh, Qt.SmoothTransformation))
            else:
                out.append(px)
        return out

    def _stitch_and_display(self):
        scaled = self._scaled_pixmaps()
        if not scaled:
            self._canvas.clear()
            return
        # Signal the parent ReaderPage to update the window minimum width.
        from PySide6.QtWidgets import QStyle
        if self._fit_mode == "original" and scaled:
            page_w = max(p.width() for p in scaled)
            sb_w = self.style().pixelMetric(QStyle.PixelMetric.PM_ScrollBarExtent) + 8
            self.min_width_needed.emit(page_w + sb_w)
        else:
            self.min_width_needed.emit(400)

        total_w = max(p.width() for p in scaled)
        total_h = sum(p.height() for p in scaled)

        stitched = QPixmap(total_w, total_h)
        stitched.fill(Qt.transparent)

        from PySide6.QtGui import QPainter
        painter = QPainter(stitched)
        y = 0
        for px in scaled:
            x = (total_w - px.width()) // 2
            painter.drawPixmap(x, y, px)
            y += px.height()
        painter.end()

        self._canvas.setPixmap(stitched)
        self._canvas.setFixedSize(total_w, total_h)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._resize_timer.start(150)  # debounce — stitch once after resize settles


# ── Main Reader page ──────────────────────────────────────────────────

class ReaderPage(QWidget):
    # Emitted when user clicks "Switch to Downloader"
    switch_to_downloader = Signal()

    def __init__(self, settings: Settings):
        super().__init__()
        self._settings = settings
        self._folder: Path | None = None
        self._cbz_files: list[Path] = []
        self._current_index: int = -1
        self._build_ui()

        # Restore last opened folder
        if settings.last_reader_folder and settings.last_reader_folder.is_dir():
            self._load_folder(settings.last_reader_folder)

    # ── UI construction ───────────────────────────────────────────────

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Top bar ──────────────────────────────────────────────────
        bar = QFrame()
        bar.setObjectName("readerBar")
        bar.setFixedHeight(52)
        bar_layout = QHBoxLayout(bar)
        bar_layout.setContentsMargins(20, 0, 20, 0)
        bar_layout.setSpacing(10)

        self._folder_btn = QPushButton("  Open Folder")
        self._folder_btn.setIcon(_icon("folder-open"))
        self._folder_btn.setObjectName("readerBarBtn")
        self._folder_btn.setFixedWidth(130)
        self._folder_btn.clicked.connect(self._open_folder)

        self._chapter_label = QLabel("No folder selected")
        self._chapter_label.setObjectName("readerChapterLabel")
        self._chapter_label.setAlignment(Qt.AlignCenter)

        # Fit mode buttons
        self._btn_width    = self._fit_btn("Width",    "width",    "fit-width")
        self._btn_height   = self._fit_btn("Height",   "height",   "fit-height")
        self._btn_original = self._fit_btn("Original", "original", "fit-original")
        self._set_active_fit("original")

        # Prev / Next
        self._prev_btn = QPushButton("  Prev")
        self._prev_btn.setIcon(_icon("chevron-left"))
        self._prev_btn.setObjectName("readerNavBtn")
        self._prev_btn.setFixedWidth(90)
        self._prev_btn.clicked.connect(self._prev_chapter)
        self._prev_btn.setEnabled(False)

        self._next_btn = QPushButton("Next  ")
        self._next_btn.setIcon(_icon("chevron-right"))
        self._next_btn.setLayoutDirection(Qt.RightToLeft)
        self._next_btn.setObjectName("readerNavBtn")
        self._next_btn.setFixedWidth(90)
        self._next_btn.clicked.connect(self._next_chapter)
        self._next_btn.setEnabled(False)

        switch_btn = QPushButton("  Downloader")
        # Two-state icon: normal=pink (visible on dark bg), hover=dark (visible on pink bg)
        dl_icon = QIcon()
        px_normal = QPixmap("assets/icons/download.svg")
        if not px_normal.isNull():
            from PySide6.QtGui import QPainter, QColor
            def _tinted(px, color):
                t = QPixmap(px.size())
                t.fill(Qt.transparent)
                p = QPainter(t)
                p.drawPixmap(0, 0, px)
                p.setCompositionMode(QPainter.CompositionMode_SourceIn)
                p.fillRect(t.rect(), QColor(color))
                p.end()
                return t
            s = 16
            dl_icon.addPixmap(_tinted(px_normal, "#F2A7B8").scaled(s, s, Qt.KeepAspectRatio, Qt.SmoothTransformation), QIcon.Normal, QIcon.Off)
            dl_icon.addPixmap(_tinted(px_normal, "#19161B").scaled(s, s, Qt.KeepAspectRatio, Qt.SmoothTransformation), QIcon.Active, QIcon.Off)
        switch_btn.setIcon(dl_icon)
        switch_btn.setObjectName("readerSwitchBtn")
        switch_btn.setFixedWidth(130)
        switch_btn.clicked.connect(self.switch_to_downloader)

        self._panel_btn = QPushButton()
        self._panel_btn.setIcon(_icon("panel-left", tint="#BBAEB4"))
        self._panel_btn.setObjectName("readerNavBtn")
        self._panel_btn.setFixedWidth(38)
        self._panel_btn.setToolTip("Toggle chapter panel")
        self._panel_btn.clicked.connect(self._toggle_panel)

        bar_layout.addWidget(self._folder_btn)
        bar_layout.addWidget(self._panel_btn)
        bar_layout.addWidget(self._prev_btn)
        bar_layout.addWidget(self._next_btn)
        bar_layout.addStretch()
        bar_layout.addWidget(self._chapter_label)
        bar_layout.addStretch()
        bar_layout.addWidget(QLabel("Fit:"))
        bar_layout.addWidget(self._btn_width)
        bar_layout.addWidget(self._btn_height)
        bar_layout.addWidget(self._btn_original)
        bar_layout.addSpacing(12)
        bar_layout.addWidget(switch_btn)

        root.addWidget(bar)

        # ── Body: chapter list sidebar + page view ────────────────────
        self._splitter = QSplitter(Qt.Horizontal)
        self._splitter.setHandleWidth(1)
        self._splitter.setObjectName("readerSplitter")
        splitter = self._splitter
        self._panel_visible = True
        self._panel_width = 220

        # Sidebar
        sidebar = QFrame()
        sidebar.setObjectName("readerSidebar")
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)

        sidebar_title = QLabel("Chapters")
        sidebar_title.setObjectName("sectionTitle")
        sidebar_title.setContentsMargins(14, 12, 14, 12)

        self._chapter_list = QListWidget()
        self._chapter_list.setObjectName("chapterList")
        self._chapter_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._chapter_list.currentRowChanged.connect(self._on_chapter_selected)

        sidebar_layout.addWidget(sidebar_title)
        sidebar_layout.addWidget(self._chapter_list, 1)

        # Page view (or placeholder)
        self._stack = QStackedWidget()

        self._placeholder = QLabel("Open a folder containing CBZ files to start reading.")
        self._placeholder.setObjectName("readerPlaceholder")
        self._placeholder.setAlignment(Qt.AlignCenter)
        self._placeholder.setWordWrap(True)

        self._page_view = PageView()
        self._page_view.min_width_needed.connect(self._apply_min_width)

        self._stack.addWidget(self._placeholder)   # index 0
        self._stack.addWidget(self._page_view)     # index 1

        splitter.addWidget(sidebar)
        splitter.addWidget(self._stack)
        splitter.setSizes([220, 1220])
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.splitterMoved.connect(self._on_splitter_moved)

        root.addWidget(self._splitter, 1)

        # ── Status bar ───────────────────────────────────────────────
        status_bar = QFrame()
        status_bar.setObjectName("readerStatusBar")
        status_bar.setFixedHeight(24)
        status_bar.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        sb_layout = QHBoxLayout(status_bar)
        sb_layout.setContentsMargins(16, 0, 16, 0)

        self._status_label = QLabel("Ready.")
        self._status_label.setObjectName("statusText")

        self._page_label = QLabel("")
        self._page_label.setObjectName("statusText")
        self._page_label.setAlignment(Qt.AlignRight)

        sb_layout.addWidget(self._status_label)
        sb_layout.addStretch()
        sb_layout.addWidget(self._page_label)

        root.addWidget(status_bar)

    def _fit_btn(self, label: str, mode: str, icon_name: str = "") -> QPushButton:
        btn = QPushButton(f"  {label}")
        if icon_name:
            # Build a two-state QIcon: checked=dark (#19161B), unchecked=muted (#BBAEB4)
            icon = QIcon()
            # Active (checked) state — dark icon on pink bg
            px_on = QPixmap(f"assets/icons/{icon_name}.svg")
            if not px_on.isNull():
                icon.addPixmap(
                    px_on.scaled(14, 14, Qt.KeepAspectRatio, Qt.SmoothTransformation),
                    QIcon.Normal, QIcon.On,
                )
            # Inactive (unchecked) state — tint muted by swapping to a recoloured copy
            px_off = QPixmap(f"assets/icons/{icon_name}.svg")
            if not px_off.isNull():
                from PySide6.QtGui import QPainter, QColor
                px_muted = QPixmap(px_off.size())
                px_muted.fill(Qt.transparent)
                p = QPainter(px_muted)
                p.drawPixmap(0, 0, px_off)
                p.setCompositionMode(QPainter.CompositionMode_SourceIn)
                p.fillRect(px_muted.rect(), QColor("#BBAEB4"))
                p.end()
                icon.addPixmap(
                    px_muted.scaled(14, 14, Qt.KeepAspectRatio, Qt.SmoothTransformation),
                    QIcon.Normal, QIcon.Off,
                )
            btn.setIcon(icon)
        btn.setObjectName("fitBtn")
        btn.setFixedWidth(84)
        btn.setCheckable(True)
        btn.clicked.connect(lambda: self._on_fit(mode))
        return btn

    # ── Slots ─────────────────────────────────────────────────────────

    def _open_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self, "Open CBZ folder", str(Path.home())
        )
        if not folder:
            return
        self._load_folder(Path(folder))

    def _load_folder(self, folder: Path):
        self._settings.last_reader_folder = folder
        save_settings(self._settings)
        self._folder = folder
        self._cbz_files = list_cbz_files(folder)

        self._chapter_list.blockSignals(True)
        self._chapter_list.clear()
        for cbz in self._cbz_files:
            item = QListWidgetItem(_chapter_display_name(cbz.stem))
            item.setData(Qt.UserRole, str(cbz))  # store full path for loading
            self._chapter_list.addItem(item)
        self._chapter_list.blockSignals(False)

        if self._cbz_files:
            self._status_label.setText(
                f"{len(self._cbz_files)} chapter(s) found in {folder.name}"
            )
            self._chapter_list.setCurrentRow(0)
        else:
            self._status_label.setText("No CBZ files found in that folder.")
            self._stack.setCurrentIndex(0)

    def _on_chapter_selected(self, row: int):
        if row < 0 or row >= len(self._cbz_files):
            return
        self._current_index = row
        cbz = self._cbz_files[row]
        display = _chapter_display_name(cbz.stem)
        self._chapter_label.setText(display)
        self._status_label.setText(f"Loading {display}…")
        self._page_label.setText("")
        self._prev_btn.setEnabled(row > 0)
        self._next_btn.setEnabled(row < len(self._cbz_files) - 1)

        self._loader = PageLoaderWorker(cbz)
        self._loader.done.connect(self._on_pages_loaded)
        self._loader.failed.connect(self._on_load_failed)
        self._loader.start()

    def _on_pages_loaded(self, pages: list):
        self._page_view.load_pages(pages)
        self._stack.setCurrentIndex(1)
        count = self._page_view.page_count()
        self._status_label.setText(f"Loaded  —  {count} page(s)")
        self._page_label.setText(f"1 / {count}")
        self._page_view.setFocus()

    def _on_load_failed(self, error: str):
        self._status_label.setText(f"Failed to load: {error}")

    def _apply_min_width(self, width: int):
        win = self.window()
        if win:
            win.setMinimumWidth(width)
            if win.width() < width:
                win.resize(width, win.height())

    def _toggle_panel(self):
        if self._panel_visible:
            self._panel_width = self._splitter.sizes()[0] or 220
            self._splitter.setSizes([0, sum(self._splitter.sizes())])
            self._panel_visible = False
            self._panel_btn.setIcon(_icon("panel-left-open", tint="#F2A7B8"))
        else:
            total = sum(self._splitter.sizes())
            self._splitter.setSizes([self._panel_width, total - self._panel_width])
            self._panel_visible = True
            self._panel_btn.setIcon(_icon("panel-left", tint="#BBAEB4"))

    def _on_splitter_moved(self, pos: int, index: int):
        if self._splitter.sizes()[0] > 0:
            self._panel_visible = True
            self._panel_width = self._splitter.sizes()[0]
            self._panel_btn.setIcon(_icon("panel-left", tint="#BBAEB4"))
        else:
            self._panel_visible = False
            self._panel_btn.setIcon(_icon("panel-left-open", tint="#F2A7B8"))

    def _prev_chapter(self):
        if self._current_index > 0:
            self._chapter_list.setCurrentRow(self._current_index - 1)

    def _next_chapter(self):
        if self._current_index < len(self._cbz_files) - 1:
            self._chapter_list.setCurrentRow(self._current_index + 1)

    def _on_fit(self, mode: str):
        self._set_active_fit(mode)
        self._page_view.set_fit_mode(mode)

    def _set_active_fit(self, mode: str):
        self._btn_width.setChecked(mode == "width")
        self._btn_height.setChecked(mode == "height")
        self._btn_original.setChecked(mode == "original")

    # ── Keyboard navigation ───────────────────────────────────────────

    def keyPressEvent(self, event: QKeyEvent):
        key = event.key()
        sb = self._page_view.verticalScrollBar()
        step = self._page_view.viewport().height() * 0.85

        if key in (Qt.Key_Down, Qt.Key_Space, Qt.Key_PageDown):
            sb.setValue(int(sb.value() + step))
        elif key in (Qt.Key_Up, Qt.Key_PageUp):
            sb.setValue(int(sb.value() - step))
        elif key == Qt.Key_Home:
            sb.setValue(0)
        elif key == Qt.Key_End:
            sb.setValue(sb.maximum())
        elif key == Qt.Key_Right:
            self._next_chapter()
        elif key == Qt.Key_Left:
            self._prev_chapter()
        else:
            super().keyPressEvent(event)