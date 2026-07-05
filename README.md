# Comic Reader

A desktop app (PySide6) for downloading and reading Toonily(as of now) chapters as local CBZ archives.

## Features

- **Downloader** — paste a series URL, analyze it, pick chapters, and download them as CBZ files
  - Cloudflare bypass via [FlareSolverr](https://github.com/FlareSolverr/FlareSolverr), with automatic fallback to direct requests
  - Live activity log with elapsed timer and step-by-step status
  - Chapter selection dialog with select-all and live counter
  - Download size estimation before committing
  - Cancel mid-download; finishes the current chapter cleanly
- **Reader** — read downloaded CBZ chapters in-app
  - Fit Width / Fit Height / Original zoom modes
  - Smooth scrolling between pages
- **Themes** — configurable UI theme (Cherry Blossom included)

See [ROADMAP.md](ROADMAP.md) for the full feature history and what's planned next.

## Requirements

- Python 3.14+
- [FlareSolverr](https://github.com/FlareSolverr/FlareSolverr) running locally (optional, but required for Cloudflare-protected sources)

## Setup

Create a virtual environment and install dependencies:

```bash
python -m venv .venv
.venv\Scripts\activate      # Windows
source .venv/bin/activate   # macOS/Linux

pip install -r requirements.txt
```

Run the app:

```bash
python main.py
```

## Configuration

Settings live in `data/settings.json` (created on first run if missing), including:

| Key | Description |
|---|---|
| `library_path` | Where downloaded CBZ files are stored |
| `theme` | Active UI theme |
| `fit_mode` | Default reader zoom mode (`width`, `height`, `original`) |
| `smooth_scrolling` | Enable/disable smooth page scrolling |
| `preload_chapters` | Number of chapters to preload in the reader |
| `flaresolverr_url` | URL of a running FlareSolverr instance (default `http://localhost:8191`) |

## Project Structure

```
comicReader/
├── assets/            # Icons, fonts, themes
├── data/              # Local library and settings (gitignored)
├── src/
│   ├── downloader/    # Site analyzers + download engine
│   ├── library/       # Local library management
│   ├── models/        # Data models (Series, Chapter, Settings)
│   ├── reader/        # CBZ loading/rendering
│   ├── services/      # Filesystem, HTTP, settings services
│   ├── ui/            # Windows, pages, dialogs
│   └── utils/         # Formatting, theming, URL helpers
├── tests/             # Unit tests + fixtures
├── main.py
└── requirements.txt
```

## Testing

```bash
pytest
```

## Supported Sites

- [Toonily](https://toonily.com)

More sources can be added by implementing a new parser under `src/downloader/websites/`.

## License

See LICENSE for terms. Code changes/contributions require permission — contact the maintainer before submitting modifications.