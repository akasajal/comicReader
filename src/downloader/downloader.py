import logging
import re
import zipfile
from pathlib import Path

from bs4 import BeautifulSoup

from src.models.chapter import Chapter
from src.models.series import Series
from src.services.http import HttpClient

log = logging.getLogger(__name__)


class Downloader:
    def __init__(self, http: HttpClient):
        self.http = http

    def download_chapter(
        self,
        chapter: Chapter,
        series: Series,
        output_dir: Path,
        on_progress=None,
    ) -> Path:
        # ── Step 1: fetch chapter reading page ──────────────────────
        log.debug("Fetching chapter page: %s", chapter.url)
        response = self.http.get_direct(chapter.url)
        log.debug("Chapter page status: %s, content length: %d",
                  response.status_code, len(response.content))

        # Sniff whether we got a real page or a Cloudflare block.
        content_type = response.headers.get("Content-Type", "")
        if "text/html" not in content_type and len(response.content) < 5000:
            raise RuntimeError(
                f"Unexpected response fetching chapter page "
                f"(status={response.status_code}, "
                f"content-type={content_type!r}, "
                f"size={len(response.content)}B). "
                "Cloudflare may have expired — try re-analyzing the series."
            )

        image_urls = self._parse_image_urls(response.text)
        log.debug("Found %d image URLs in chapter page", len(image_urls))

        if not image_urls:
            # Dump a snippet so we can diagnose selector mismatches.
            snippet = response.text[:500].replace("\n", " ")
            log.warning("No images found. Page snippet: %s", snippet)
            raise RuntimeError(
                f"No images found for '{chapter.title}'. "
                "The page selector may have changed — check logs for details."
            )

        # ── Step 2: write CBZ ────────────────────────────────────────
        series_dir = output_dir / _safe_name(series.title)
        series_dir.mkdir(parents=True, exist_ok=True)
        cbz_path = series_dir / f"{_chapter_filename(chapter)}.cbz"

        total = len(image_urls)
        with zipfile.ZipFile(cbz_path, "w", zipfile.ZIP_STORED) as zf:
            for idx, url in enumerate(image_urls, start=1):
                if on_progress:
                    on_progress(idx, total)

                log.debug("Downloading image %d/%d: %s", idx, total, url)
                img_data = self._fetch_image(url)
                log.debug("Image %d size: %d bytes", idx, len(img_data))

                if len(img_data) < 1000:
                    log.warning(
                        "Image %d suspiciously small (%d bytes), URL: %s",
                        idx, len(img_data), url
                    )

                ext = _image_ext(url)
                zf.writestr(f"{idx:03d}{ext}", img_data)

        final_size = cbz_path.stat().st_size
        log.debug("CBZ written: %s (%d bytes)", cbz_path, final_size)
        return cbz_path

    def _parse_image_urls(self, html: str) -> list[str]:
        soup = BeautifulSoup(html, "html.parser")
        images = soup.select("div.reading-content div.page-break.no-gaps img")
        urls = []
        for img in images:
            src = (img.get("data-src") or img.get("src") or "").strip()
            if src:
                urls.append(src)
        return urls

    def _fetch_image(self, url: str) -> bytes:
        # Toonily's CDN requires a Referer from toonily.com or it returns
        # a tiny placeholder / 403. Send it on every image request.
        response = self.http.get_direct(
            url,
            headers={"Referer": "https://toonily.com/"},
        )
        response.raise_for_status()
        return response.content


def _safe_name(name: str) -> str:
    return re.sub(r'[\\/:*?"<>|]', "_", name).strip()


def _chapter_filename(chapter: Chapter) -> str:
    if chapter.is_extra:
        return _safe_name(chapter.title)
    num = chapter.number
    num_str = f"{int(num):04d}" if num == int(num) else f"{num:07.2f}".replace(".", "-")
    return f"Chapter_{num_str}"


def _image_ext(url: str) -> str:
    path = url.split("?")[0].rstrip("/")
    suffix = Path(path).suffix.lower()
    return suffix if suffix in {".jpg", ".jpeg", ".png", ".webp", ".gif"} else ".jpg"