import io
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from PIL import Image

from src.models.settings import Settings
from src.ui.downloader_page import DownloaderPage

FIXTURE = Path(__file__).parent / "fixtures" / "toonily_series.html"


def _valid_png_bytes() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (4, 4), color=(242, 167, 184)).save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture
def page(qapp, tmp_path):
    settings = Settings(library_path=tmp_path / "library")
    return DownloaderPage(settings)


def test_analyze_series_populates_fields_on_success(page):
    html = FIXTURE.read_text(encoding="utf-8")
    cover_bytes = _valid_png_bytes()

    def fake_get(url, **kwargs):
        if url.endswith(".jpg"):
            return SimpleNamespace(content=cover_bytes)
        return SimpleNamespace(text=html)

    page.analyzer.http.get = fake_get
    page.url_input.setText("https://toonily.com/webtoon/solo-leveling")

    page.analyze_series()

    assert page.title_value.text() == "Solo Leveling"
    assert page.author_value.text() == "Chugong"
    assert page.genre_value.text() == "Action, Adventure, Fantasy"
    assert page.status_value.text() == "Completed"
    assert page.chapter_value.text() == "3"
    assert page.download_btn.isEnabled() is True
    assert "3 chapter" in page.status_label.text()

    pixmap = page.cover_label.pixmap()
    assert pixmap is not None and not pixmap.isNull()


def test_analyze_series_warns_on_unsupported_website(page):
    page.url_input.setText("https://example.com/some-comic")

    with patch("src.ui.downloader_page.QMessageBox.warning") as mock_warn:
        page.analyze_series()
        assert mock_warn.called

    assert page.status_label.text() == "Unsupported website."
    assert page.download_btn.isEnabled() is False


def test_analyze_series_warns_on_empty_url(page):
    page.url_input.setText("   ")

    with patch("src.ui.downloader_page.QMessageBox.warning") as mock_warn:
        page.analyze_series()
        assert mock_warn.called

    assert page.status_label.text() == "Please enter a series URL."
