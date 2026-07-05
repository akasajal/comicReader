from pathlib import Path
from types import SimpleNamespace

import pytest

from src.downloader.exceptions import InvalidSeriesError
from src.downloader.websites.toonily import ToonilyParser

FIXTURE = Path(__file__).parent / "fixtures" / "toonily_series.html"


class FakeHttpClient:
    """Minimal stand-in for HttpClient that serves canned text/content."""

    def __init__(self, text: str | None = None, content: bytes | None = None):
        self.text = text
        self.content = content

    def get(self, url: str, **kwargs):
        return SimpleNamespace(text=self.text, content=self.content)


@pytest.fixture
def series_html() -> str:
    return FIXTURE.read_text(encoding="utf-8")


def test_supports_matches_toonily_urls():
    parser = ToonilyParser(http=FakeHttpClient())

    assert parser.supports("https://toonily.com/webtoon/solo-leveling") is True
    assert parser.supports("https://TOONILY.com/webtoon/solo-leveling") is True
    assert parser.supports("https://mangadex.org/title/abc") is False


def test_analyze_parses_full_series_metadata(series_html):
    parser = ToonilyParser(http=FakeHttpClient(text=series_html))

    series = parser.analyze("https://toonily.com/webtoon/solo-leveling")

    assert series.title == "Solo Leveling"
    assert series.url == "https://toonily.com/webtoon/solo-leveling"
    assert series.cover_url == "https://cdn.example.com/covers/solo-leveling.jpg"
    assert series.author == "Chugong"
    assert series.status == "Completed"
    assert series.genres == ["Action", "Adventure", "Fantasy"]
    assert series.description is not None
    assert "Gate" in series.description
    assert series.total_chapters == 3


def test_analyze_orders_chapters_oldest_first(series_html):
    parser = ToonilyParser(http=FakeHttpClient(text=series_html))

    series = parser.analyze("https://toonily.com/webtoon/solo-leveling")
    numbers = [chapter.number for chapter in series.chapters]

    assert numbers == [1.0, 2.0, 3.0]
    assert series.chapters[0].url.endswith("/chapter-1")
    assert series.chapters[-1].url.endswith("/chapter-3")


def test_analyze_raises_on_non_series_page():
    bad_html = "<html><body><p>404 not found</p></body></html>"
    parser = ToonilyParser(http=FakeHttpClient(text=bad_html))

    with pytest.raises(InvalidSeriesError):
        parser.analyze("https://toonily.com/not-a-series")


def test_title_badge_is_stripped_from_title(series_html):
    parser = ToonilyParser(http=FakeHttpClient(text=series_html))

    series = parser.analyze("https://toonily.com/webtoon/solo-leveling")

    assert "Completed" not in series.title
    assert series.title == "Solo Leveling"
