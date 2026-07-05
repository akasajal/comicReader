from src.downloader.websites.base import WebsiteParser
from src.downloader.websites.toonily import ToonilyParser
from src.downloader.exceptions import UnsupportedWebsiteError
from src.services.http import HttpClient


class Analyzer:
    def __init__(self, flaresolverr_url: str | None = None):
        self.http = HttpClient(flaresolverr_url=flaresolverr_url)
        self.parsers: list[WebsiteParser] = []

        self.register(ToonilyParser(self.http))

    def register(self, parser: WebsiteParser) -> None:
        self.parsers.append(parser)

    def analyze(self, url: str):
        for parser in self.parsers:
            if parser.supports(url):
                return parser.analyze(url)

        raise UnsupportedWebsiteError(
            "This website is not supported."
        )