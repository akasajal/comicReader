from dataclasses import dataclass, field


@dataclass(slots=True)
class Series:
    title: str
    url: str
    cover_url: str | None = None

    total_chapters: int = 0
    estimated_size: int | None = None

    chapters: list["Chapter"] = field(default_factory=list)

    author: str | None = None
    description: str | None = None
    cover_path: str | None = None

    status: str | None = None
    genres: list[str] = field(default_factory=list)