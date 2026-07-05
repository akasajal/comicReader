from dataclasses import dataclass, field


@dataclass(slots=True)
class Chapter:
    number: float
    title: str
    url: str

    image_urls: list[str] = field(default_factory=list)

    downloaded: bool = False
    stitched: bool = False

    output_path: str | None = None

    local_path: str | None = None
    file_size: int = 0

    # True when this entry has no parseable chapter number (e.g. a
    # "Special Episode" or one-shot) rather than a genuine chapter 0.
    # `number` is left at 0.0 for these so existing numeric code paths
    # don't need to special-case None, but ordering logic should treat
    # is_extra=True entries as coming after all numbered chapters.
    is_extra: bool = False