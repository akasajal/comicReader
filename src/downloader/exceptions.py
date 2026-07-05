class DownloaderError(Exception):
    """Base downloader exception."""


class UnsupportedWebsiteError(DownloaderError):
    """Raised when no parser supports the supplied URL."""


class InvalidSeriesError(DownloaderError):
    """Raised when the supplied URL is not a valid series page."""