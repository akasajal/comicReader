import requests


DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/137.0.0.0 Safari/537.36"
    )
}


class HttpClient:
    def __init__(self, flaresolverr_url: str | None = None):
        self.session = requests.Session()
        self.session.headers.update(DEFAULT_HEADERS)
        self._flaresolverr_url = flaresolverr_url.rstrip("/") if flaresolverr_url else None

    # ── FlareSolverr ─────────────────────────────────────────────────

    def _solve(self, url: str) -> requests.Response:
        """Fetch *url* via FlareSolverr and return a synthesised Response."""
        payload = {
            "cmd": "request.get",
            "url": url,
            "maxTimeout": 60_000,
        }
        proxy_resp = requests.post(
            f"{self._flaresolverr_url}/v1",
            json=payload,
            timeout=90,
        )
        proxy_resp.raise_for_status()

        data = proxy_resp.json()
        if data.get("status") != "ok":
            raise requests.HTTPError(
                f"FlareSolverr error: {data.get('message', 'unknown')}"
            )

        solution = data["solution"]

        fake = requests.Response()
        fake.status_code = solution.get("status", 200)
        fake.url = solution.get("url", url)
        fake._content = solution.get("response", "").encode("utf-8")
        fake.encoding = "utf-8"

        # Replay cookies into the session so direct requests to the same
        # domain (images, HEAD checks) are already authenticated.
        for cookie in solution.get("cookies", []):
            self.session.cookies.set(
                cookie["name"],
                cookie["value"],
                domain=cookie.get("domain", ""),
            )

        return fake

    # ── Public interface ──────────────────────────────────────────────

    def get(self, url: str, **kwargs) -> requests.Response:
        """Fetch a page, routing through FlareSolverr when configured."""
        if self._flaresolverr_url:
            try:
                return self._solve(url)
            except Exception:
                pass  # fall back to direct

        response = self.session.get(url, timeout=30, **kwargs)
        response.raise_for_status()
        return response

    def get_direct(self, url: str, **kwargs) -> requests.Response:
        """Fetch a URL directly, bypassing FlareSolverr.

        Use for CDN assets (cover images, manga page images) that aren't
        behind a Cloudflare JS challenge — session cookies set by a prior
        FlareSolverr solve are still sent, so auth works fine.
        """
        response = self.session.get(url, timeout=30, **kwargs)
        response.raise_for_status()
        return response

    def head(self, url: str, **kwargs) -> requests.Response:
        """HEAD request for Content-Length checks — always direct."""
        response = self.session.head(url, timeout=30, allow_redirects=True, **kwargs)
        response.raise_for_status()
        return response