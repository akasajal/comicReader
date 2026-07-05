from pathlib import Path
from types import SimpleNamespace

import pytest

from src.downloader.websites.toonily import ToonilyParser

FIXTURES = Path(__file__).parent / "fixtures"
SERIES_HTML = (FIXTURES / "toonily_series.html").read_text(encoding="utf-8")
EXTRAS_HTML = (FIXTURES / "toonily_series_with_extras.html").read_text(encoding="utf-8")
CHAPTER_HTML = (FIXTURES / "toonily_chapter_page.html").read_text(encoding="utf-8")


class RoutedFakeHttpClient:
    """Fake HttpClient that serves different responses per URL/method,
    used for tests that need a series page, a chapter page, and image
    HEAD responses to all behave independently."""

    def __init__(self, pages: dict[str, str] | None = None, image_sizes: dict[str, int] | None = None):
        self.pages = pages or {}
        self.image_sizes = image_sizes or {}
        self.get_calls: list[str] = []
        self.head_calls: list[str] = []

    def get(self, url: str, **kwargs):
        self.get_calls.append(url)
        if url not in self.pages:
            raise AssertionError(f"Unexpected GET to {url}")
        return SimpleNamespace(text=self.pages[url])

    def head(self, url: str, **kwargs):
        self.head_calls.append(url)
        if url not in self.image_sizes:
            raise AssertionError(f"Unexpected HEAD to {url}")
        return SimpleNamespace(headers={"Content-Length": str(self.image_sizes[url])})


# ── Download size estimation ─────────────────────────────────────────


def test_estimate_download_size_samples_most_recent_chapter():
    series_url = "https://toonily.com/webtoon/solo-leveling"
    chapter3_url = "https://toonily.com/webtoon/solo-leveling/chapter-3"

    http = RoutedFakeHttpClient(
        pages={series_url: SERIES_HTML, chapter3_url: CHAPTER_HTML},
        image_sizes={
            "https://cdn.example.com/pages/ch3/001.jpg": 1_000_000,
            "https://cdn.example.com/pages/ch3/002.jpg": 1_200_000,
            "https://cdn.example.com/pages/ch3/003.jpg": 900_000,
        },
    )
    parser = ToonilyParser(http=http)

    series = parser.analyze(series_url)

    # Sample chapter (chapter 3) totals 3,100,000 bytes across 3 pages.
    # Series has 3 chapters total, so estimate = 3,100,000 * 3.
    assert series.estimated_size == 3_100_000 * 3
    assert chapter3_url in http.get_calls


def test_estimate_download_size_returns_none_when_chapter_fetch_fails():
    series_url = "https://toonily.com/webtoon/solo-leveling"

    class FailingHttp(RoutedFakeHttpClient):
        def get(self, url, **kwargs):
            if url == series_url:
                return SimpleNamespace(text=SERIES_HTML)
            raise ConnectionError("network down")

    parser = ToonilyParser(http=FailingHttp())
    series = parser.analyze(series_url)

    assert series.estimated_size is None
    # The rest of analysis should still succeed despite the failed estimate.
    assert series.title == "Solo Leveling"
    assert series.total_chapters == 3


def test_estimate_download_size_returns_none_when_no_images_found():
    series_url = "https://toonily.com/webtoon/solo-leveling"
    chapter3_url = "https://toonily.com/webtoon/solo-leveling/chapter-3"

    http = RoutedFakeHttpClient(
        pages={series_url: SERIES_HTML, chapter3_url: "<html><body>no images here</body></html>"},
    )
    parser = ToonilyParser(http=http)

    series = parser.analyze(series_url)

    assert series.estimated_size is None


def test_estimate_download_size_returns_none_when_head_requests_all_fail():
    series_url = "https://toonily.com/webtoon/solo-leveling"
    chapter3_url = "https://toonily.com/webtoon/solo-leveling/chapter-3"

    class NoHeadHttp(RoutedFakeHttpClient):
        def head(self, url, **kwargs):
            raise ConnectionError("HEAD not supported")

    http = NoHeadHttp(pages={series_url: SERIES_HTML, chapter3_url: CHAPTER_HTML})
    parser = ToonilyParser(http=http)

    series = parser.analyze(series_url)

    assert series.estimated_size is None


def test_estimate_download_size_skips_images_missing_content_length():
    series_url = "https://toonily.com/webtoon/solo-leveling"
    chapter3_url = "https://toonily.com/webtoon/solo-leveling/chapter-3"

    class PartialHeadersHttp(RoutedFakeHttpClient):
        def head(self, url, **kwargs):
            self.head_calls.append(url)
            if url.endswith("002.jpg"):
                return SimpleNamespace(headers={})  # no Content-Length
            return SimpleNamespace(headers={"Content-Length": "1000000"})

    http = PartialHeadersHttp(pages={series_url: SERIES_HTML, chapter3_url: CHAPTER_HTML})
    parser = ToonilyParser(http=http)

    series = parser.analyze(series_url)

    # 2 of 3 images had usable Content-Length (1,000,000 each = 2,000,000),
    # extrapolated across 3 chapters.
    assert series.estimated_size == 2_000_000 * 3


# ── Extras / specials chapter ordering ───────────────────────────────


def test_extras_and_specials_are_flagged_and_sorted_after_numbered_chapters():
    series_url = "https://toonily.com/webtoon/test-series"
    http = RoutedFakeHttpClient(pages={series_url: EXTRAS_HTML})
    parser = ToonilyParser(http=http)

    series = parser.analyze(series_url)
    titles = [c.title for c in series.chapters]
    flags = [c.is_extra for c in series.chapters]

    # Numbered chapters first, ascending (including the decimal),
    # then extras in their original chronological (upload) order.
    assert titles == [
        "Chapter 1",
        "Chapter 2",
        "Chapter 2.5",
        "Chapter 3",
        "Prologue",
        "Special Event",
    ]
    assert flags == [False, False, False, False, True, True]


def test_decimal_chapter_number_parses_correctly():
    series_url = "https://toonily.com/webtoon/test-series"
    http = RoutedFakeHttpClient(pages={series_url: EXTRAS_HTML})
    parser = ToonilyParser(http=http)

    series = parser.analyze(series_url)
    decimal_chapter = next(c for c in series.chapters if c.title == "Chapter 2.5")

    assert decimal_chapter.number == 2.5
    assert decimal_chapter.is_extra is False


def test_extras_do_not_collapse_to_chapter_zero():
    series_url = "https://toonily.com/webtoon/test-series"
    http = RoutedFakeHttpClient(pages={series_url: EXTRAS_HTML})
    parser = ToonilyParser(http=http)

    series = parser.analyze(series_url)
    prologue = next(c for c in series.chapters if c.title == "Prologue")

    # Prologue has no chapter number — it must be flagged as an extra,
    # not silently treated as chapter 0 (which would sort it before
    # chapter 1).
    assert prologue.is_extra is True
