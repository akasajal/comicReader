from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QCheckBox,
    QScrollArea,
    QWidget,
    QFrame,
    QSizePolicy,
)

from src.models.chapter import Chapter


class ChapterSelectDialog(QDialog):
    def __init__(self, chapters: list[Chapter], parent=None):
        super().__init__(parent)
        self._chapters = chapters
        self._checkboxes: list[QCheckBox] = []

        self.setWindowTitle("Select Chapters")
        self.setMinimumSize(480, 560)
        self.resize(520, 640)

        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(14)

        # ── Header ───────────────────────────────────────────────────
        header = QLabel(f"Select chapters to download  ({len(self._chapters)} total)")
        header.setObjectName("sectionTitle")
        root.addWidget(header)

        # ── Select-all row ───────────────────────────────────────────
        top_bar = QHBoxLayout()
        top_bar.setSpacing(10)

        self._select_all = QCheckBox("Select all")
        self._select_all.setObjectName("fieldLabel")
        self._select_all.setChecked(True)
        self._select_all.stateChanged.connect(self._on_select_all)

        self._count_label = QLabel()
        self._count_label.setObjectName("pageSubtitle")
        self._count_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        top_bar.addWidget(self._select_all)
        top_bar.addStretch()
        top_bar.addWidget(self._count_label)
        root.addLayout(top_bar)

        # ── Divider ──────────────────────────────────────────────────
        div = QFrame()
        div.setObjectName("divider")
        div.setFrameShape(QFrame.HLine)
        root.addWidget(div)

        # ── Chapter list in a scroll area ────────────────────────────
        scroll = QScrollArea()
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        list_widget = QWidget()
        list_layout = QVBoxLayout(list_widget)
        list_layout.setContentsMargins(0, 4, 0, 4)
        list_layout.setSpacing(2)

        for chapter in self._chapters:
            cb = QCheckBox(self._chapter_label(chapter))
            cb.setObjectName("fieldValue")
            cb.setChecked(True)
            cb.stateChanged.connect(self._on_checkbox_changed)
            self._checkboxes.append(cb)
            list_layout.addWidget(cb)

        list_layout.addStretch()
        scroll.setWidget(list_widget)
        root.addWidget(scroll, 1)

        # ── Divider ──────────────────────────────────────────────────
        div2 = QFrame()
        div2.setObjectName("divider")
        div2.setFrameShape(QFrame.HLine)
        root.addWidget(div2)

        # ── Action buttons ───────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        self._cancel_btn = QPushButton("Cancel")
        self._cancel_btn.setObjectName("cancelBtn")
        self._cancel_btn.setFixedHeight(38)
        self._cancel_btn.setCursor(Qt.PointingHandCursor)
        self._cancel_btn.clicked.connect(self.reject)

        self._download_btn = QPushButton("Download Selected")
        self._download_btn.setObjectName("downloadBtn")
        self._download_btn.setFixedHeight(38)
        self._download_btn.setCursor(Qt.PointingHandCursor)
        self._download_btn.clicked.connect(self.accept)

        btn_row.addWidget(self._cancel_btn)
        btn_row.addWidget(self._download_btn, 1)
        root.addLayout(btn_row)

        self._refresh_count()

    # ── Helpers ──────────────────────────────────────────────────────

    def _chapter_label(self, chapter: Chapter) -> str:
        if chapter.is_extra:
            return f"  {chapter.title}"
        num = int(chapter.number) if chapter.number == int(chapter.number) else chapter.number
        return f"  Chapter {num}  —  {chapter.title}" if chapter.title != f"Chapter {num}" else f"  Chapter {num}"

    def _refresh_count(self):
        selected = sum(cb.isChecked() for cb in self._checkboxes)
        total = len(self._checkboxes)
        self._count_label.setText(f"{selected} / {total} selected")
        self._download_btn.setEnabled(selected > 0)

        # Keep select-all tri-state in sync without re-triggering its signal.
        self._select_all.blockSignals(True)
        if selected == 0:
            self._select_all.setCheckState(Qt.Unchecked)
        elif selected == total:
            self._select_all.setCheckState(Qt.Checked)
        else:
            self._select_all.setCheckState(Qt.PartiallyChecked)
        self._select_all.blockSignals(False)

    # ── Slots ─────────────────────────────────────────────────────────

    def _on_select_all(self, state: int):
        checked = state == Qt.Checked.value
        for cb in self._checkboxes:
            cb.blockSignals(True)
            cb.setChecked(checked)
            cb.blockSignals(False)
        self._refresh_count()

    def _on_checkbox_changed(self):
        self._refresh_count()

    # ── Result ────────────────────────────────────────────────────────

    def selected_chapters(self) -> list[Chapter]:
        return [
            chapter
            for chapter, cb in zip(self._chapters, self._checkboxes)
            if cb.isChecked()
        ]