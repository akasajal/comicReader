import re

from bs4 import BeautifulSoup

from src.downloader.exceptions import InvalidSeriesError
from src.downloader.websites.base import WebsiteParser
from src.models.chapter import Chapter
from src.models.series import Series
from src.services.http import HttpClient


class ToonilyParser(WebsiteParser):
    """Parser for toonily.com (Madara WordPress theme).

    Selector notes:
    - Series info, title, and cover selectors below match the Madara
      theme's standard "tab-summary" series page layout.
    - Chapter list selectors match Madara's "listing-chapters_wrap"
      block, which is shared by every Madara-based site (Toonily,
      Asura-style mirrors, etc.) with only minor styling differences.
    """

    def __init__(self, http: HttpClient):
        self.http = http

    def supports(self, url: str) -> bool:
        return "toonily" in url.lower()

    def analyze(self, url: str) -> Series:
        response = self.http.get(url)
        soup = BeautifulSoup(response.text, "html.parser")

        summary = soup.select_one("div.tab-summary")
        if summary is None:
            raise InvalidSeriesError(
                "This page doesn't look like a Toonily series page."
            )

        title = self._parse_title(summary)
        cover_url = self._parse_cover(summary)
        author = self._parse_post_content(summary, "author")
        status = self._parse_post_content(summary, "status")
        genres = self._parse_genres(summary)
        description = self._parse_description(soup)
        chapters = self._parse_chapters(soup)
        estimated_size = self._estimate_download_size(chapters)

        return Series(
            title=title,
            url=url,
            cover_url=cover_url,
            author=author,
            status=status,
            genres=genres,
            description=description,
            chapters=chapters,
            total_chapters=len(chapters),
            estimated_size=estimated_size,
        )

    # ── Field parsers ────────────────────────────────────────────────

    def _parse_title(self, summary) -> str:
        title_box = summary.select_one("div.post-content > div.post-title")
        if title_box is None:
            return "Unknown Series"

        heading = title_box.select_one("h1")
        if heading is None:
            return "Unknown Series"

        # Badges (e.g. "Hot", "Completed") sit inside the heading as
        # their own span and aren't part of the actual title text.
        for badge in heading.select("span.manga-title-badges"):
            badge.extract()

        return heading.get_text(strip=True) or "Unknown Series"

    def _parse_cover(self, summary) -> str | None:
        img = summary.select_one("div.summary_image img")
        if img is None:
            return None

        # Madara lazy-loads cover art; the real URL is in data-src,
        # falling back to src for themes/pages that don't lazy-load.
        return img.get("data-src") or img.get("src")

    def _parse_post_content(self, summary, field: str) -> str | None:
        """Read a labeled row from the post-content metadata block.

        Madara renders author/artist/status/etc as:
            <div class="post-content_item">
              <div class="summary-heading"><h5>Author(s)</h5></div>
              <div class="summary-content">Some Value</div>
            </div>
        We match the heading by keyword rather than a fixed class name
        since Madara installs vary slightly in their exact markup.
        """
        for item in summary.select("div.post-content_item"):
            heading = item.select_one(".summary-heading")
            value = item.select_one(".summary-content")

            if heading is None or value is None:
                continue

            label = heading.get_text(strip=True).lower()

            if field == "author" and ("author" in label or "writer" in label):
                return value.get_text(strip=True) or None

            if field == "status" and "status" in label:
                return value.get_text(strip=True) or None

        return None

    def _parse_genres(self, summary) -> list[str]:
        for item in summary.select("div.post-content_item"):
            heading = item.select_one(".summary-heading")
            value = item.select_one(".summary-content")

            if heading is None or value is None:
                continue

            if "genre" not in heading.get_text(strip=True).lower():
                continue

            genres = [a.get_text(strip=True) for a in value.select("a")]
            return [g for g in genres if g]

        return []

    def _parse_description(self, soup) -> str | None:
        summary = soup.select_one("div.summary__content")
        if summary is None:
            return None

        text = summary.get_text(separator=" ", strip=True)
        text = re.sub(r"\s+", " ", text)
        return text or None

    def _parse_chapters(self, soup) -> list[Chapter]:
        rows = soup.select("div.listing-chapters_wrap > ul > li")
        chapters: list[Chapter] = []

        for row in rows:
            link = row.select_one("a")
            if link is None:
                continue

            chapter_url = (link.get("href") or "").strip()
            if not chapter_url:
                continue

            raw_name = link.get_text(strip=True)
            number = self._extract_chapter_number(raw_name)

            chapters.append(
                Chapter(
                    number=number if number is not None else 0.0,
                    title=raw_name or "Untitled Chapter",
                    url=chapter_url,
                    is_extra=number is None,
                )
            )

        # Madara lists chapters newest-first in the DOM. Reverse first so
        # ties (e.g. multiple specials, or same-numbered duplicates) keep
        # their original chronological order, then sort numbered chapters
        # ascending with all extras/specials pushed after them.
        chapters.reverse()
        chapters.sort(key=lambda c: (c.is_extra, c.number))

        return chapters

    def _extract_chapter_number(self, name: str) -> float | None:
        """Return the chapter number parsed from a chapter title.

        Returns None (rather than 0.0) when no number is present, so
        callers can distinguish a genuine "Chapter 0" from a special
        or extra entry that has no chapter number at all.
        """
        match = re.search(r"(\d+(?:\.\d+)?)", name)
        if match:
            return float(match.group(1))
        return None

    # ── Size estimation ──────────────────────────────────────────────

    def _parse_page_image_urls(self, chapter_html: str) -> list[str]:
        """Extract page image URLs from a chapter reading page.

        Selector confirmed against Madara/Toonily's reading page
        layout: each page is an <img> inside a no-gaps page-break div,
        with the real source in data-src (lazy-loaded).
        """
        soup = BeautifulSoup(chapter_html, "html.parser")
        images = soup.select("div.reading-content div.page-break.no-gaps img")

        urls = []
        for img in images:
            src = (img.get("data-src") or img.get("src") or "").strip()
            if src:
                urls.append(src)

        return urls

    def _estimate_download_size(self, chapters: list[Chapter]) -> int | None:
        """Estimate total download size in bytes by sampling one chapter.

        Fetches the most recent numbered chapter, sums its image sizes
        via lightweight HEAD requests, and extrapolates across the full
        chapter count. Returns None on any failure (missing chapters,
        network errors, no images found) rather than guessing — an
        estimate we can't actually measure shouldn't be shown as one.
        """
        if not chapters:
            return None

        sample_chapter = self._pick_sample_chapter(chapters)
        if sample_chapter is None:
            return None

        try:
            # The FlareSolverr solve for the series page already set
            # session cookies, so the chapter page can be fetched
            # directly — no second browser solve needed.
            response = self.http.get_direct(sample_chapter.url)
        except Exception:
            return None

        image_urls = self._parse_page_image_urls(response.text)
        if not image_urls:
            return None

        # Sample only the first 3 pages to keep estimation fast,
        # then extrapolate to the full chapter and all chapters.
        sample_urls = image_urls[:3]
        sample_size = self._sum_image_sizes(sample_urls)
        if sample_size is None:
            return None

        avg_page_size = sample_size / len(sample_urls)
        chapter_size = int(avg_page_size * len(image_urls))
        return chapter_size * len(chapters)

    def _pick_sample_chapter(self, chapters: list[Chapter]) -> Chapter | None:
        """Pick a representative chapter to sample for size estimation.

        Prefers the most recent numbered chapter (last in our sorted,
        ascending list) since it's most likely to reflect the site's
        current image hosting and format. Falls back to the last
        chapter overall if every entry is an extra/special.
        """
        numbered = [c for c in chapters if not c.is_extra]
        if numbered:
            return numbered[-1]

        return chapters[-1]

    def _sum_image_sizes(self, image_urls: list[str]) -> int | None:
        """Sum image sizes across URLs.

        Tries HEAD first for speed; if the server omits Content-Length
        (common on CDNs that stream or chunk), falls back to a direct GET
        and measures the actual response body length.
        Returns None only if every URL fails completely.
        """
        total = 0
        successful = 0

        for image_url in image_urls:
            size = self._measure_image_size(image_url)
            if size is not None:
                total += size
                successful += 1

        if successful == 0:
            return None

        return total

    def _measure_image_size(self, image_url: str) -> int | None:
        """Return byte size for a single image URL, or None on failure."""
        # Try HEAD first — fast, no body transfer.
        try:
            response = self.http.head(image_url)
            content_length = response.headers.get("Content-Length")
            if content_length is not None:
                return int(content_length)
        except Exception:
            pass

        # HEAD gave no Content-Length — download the body and measure it.
        try:
            response = self.http.get_direct(image_url)
            return len(response.content)
        except Exception:
            return None