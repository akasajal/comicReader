from abc import ABC, abstractmethod

from src.models.series import Series


class WebsiteParser(ABC):
    """Base class for per-website series/chapter parsers.

    Concrete parsers are expected to accept a shared
    `src.services.http.HttpClient` in their constructor so that all
    parsers reuse the same session (cookies, headers, connection pool)
    owned by the `Analyzer`.
    """

    @abstractmethod
    def supports(self, url: str) -> bool:
        """Return True if this parser supports the given URL."""
        raise NotImplementedError

    @abstractmethod
    def analyze(self, url: str) -> Series:
        """Analyze the series and return its metadata."""
        raise NotImplementedError