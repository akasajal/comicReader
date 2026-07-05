# Roadmap

> Long-term roadmap for Comic Reader.

---

# v0.1 — Foundation ✅

* [x] Project structure
* [x] Theme system
* [x] Cherry Blossom theme
* [x] Main window
* [x] Downloader page UI
* [x] Settings loader
* [x] Analyzer skeleton
* [x] Downloader skeleton
* [x] Models
* [x] Utility modules

---

# v0.2 — Series Analysis ✅

Goal:

> Successfully analyze a supported series URL.

### Cloudflare bypass

* [x] FlareSolverr integration — routes protected URLs through a local browser solver
* [x] Session cookie replay — subsequent direct requests reuse the solved session
* [x] Graceful fallback — falls back to direct request if FlareSolverr is unavailable

### Metadata

* [x] Detect supported website
* [x] Fetch HTML via FlareSolverr
* [x] Parse title
* [x] Parse author / writer
* [x] Parse cover (CDN direct fetch)
* [x] Parse status
* [x] Parse genres
* [x] Parse description
* [x] Parse chapter count

### UI

* [x] Non-blocking analysis (QThread worker)
* [x] Live activity log with elapsed timer and step updates
* [x] Populate Series Information card
* [x] Display cover image
* [x] Scrollable description (fixed-height, no card overflow)
* [x] Enable Download button on success

---

# v0.3 — Chapter Discovery ✅

Goal:

> Build an accurate chapter list.

* [x] Parse chapter URLs
* [x] Parse chapter names
* [x] Handle decimal chapters (e.g. "Chapter 2.5" sorts between 2 and 3)
* [x] Handle extras/specials — flagged via `Chapter.is_extra`, sorted after numbered chapters
* [x] Sort chapters correctly — numbered ascending, extras after, ties preserve upload order
* [x] Estimate download size — samples 3 pages from latest chapter, extrapolates; skips second FlareSolverr solve by reusing session cookies

---

# v0.4 — Download Engine ✅

Goal:

> Download selected chapters as CBZ archives.

* [x] Chapter selection dialog — checklist with select-all, live counter
* [x] Folder picker — native file explorer before download starts
* [x] Fetch chapter page (direct, session cookies from FlareSolverr solve)
* [x] Extract image URLs from reading page
* [x] Download images with correct Referer header
* [x] Package as CBZ (ZIP of numbered images)
* [x] Background download worker (QThread, non-blocking UI)
* [x] Per-chapter + per-page live progress in Activity log
* [x] Cancel download — button flips to "Cancel Download" mid-run, finishes current chapter cleanly
* [x] Download summary — "N chapter(s) downloaded · M failed"
* [x] Debug logging to stdout and `comic_reader.log`

---

# v0.5 — Reader 🔜

Goal:

> Read downloaded CBZ chapters in-app.

* [x] "Switch to Reader" button (top-right header)
* [x] `QStackedWidget` to swap between Downloader and Reader pages
* [x] Folder picker to load a CBZ directory
* [x] Chapter list from CBZ files in folder
* [x] CBZ renderer — unzip + display pages as QPixmap
* [x] Fit Width / Fit Height / Original zoom modes
* [x] Smooth scrolling
* [x] Keyboard navigation (arrow keys, Page Up/Down)
* [x] Mouse navigation

---

# v0.6 — Image Processing

Goal:

> Produce a seamless offline chapter.

* [x] Validate downloaded images (detect placeholder/error images by size)
* [x] Preserve page order
* [x] Stitch pages vertically (optional long-strip mode)
* [x] Remove tiny gaps between stitched pages
* [x] Optimize image size
* [x] Retry failed image downloads

---

# v0.7 — Library

Goal:

> Store and browse downloaded series.

* [ ] Library structure on disk
* [ ] Metadata storage (JSON sidecar per series)
* [ ] Cover caching
* [ ] Chapter indexing
* [ ] Read progress tracking
* [ ] Last opened tracking

---

# v0.8 — Library Management

* [ ] Library page UI
* [ ] Search
* [ ] Sort (by title, date, progress)
* [ ] Delete series
* [ ] Refresh metadata
* [ ] Open folder in explorer

---

# v0.9 — Polish

* [ ] Settings page (FlareSolverr URL, download directory, theme)
* [ ] Theme switching UI
* [ ] Better error messages (distinguish network vs parse vs CF errors)
* [ ] Parallel image downloads (per chapter)
* [ ] Resume interrupted downloads
* [ ] Performance optimization

---

# v1.0 — First Stable Release

## Downloader

* [ ] Multi-site support (Asura Scans, MangaDex, MangaSee)
* [ ] Extendable parser architecture
* [ ] Parallel chapter downloads
* [ ] Download queue management

## Reader

* [ ] Reading history
* [ ] Continue reading
* [ ] Bookmarks
* [ ] Favorite series

## Library

* [ ] Automatic metadata loading
* [ ] Cover thumbnails
* [ ] Storage statistics

## Quality

* [ ] Unit tests
* [ ] Documentation
* [ ] Packaging / Windows executable

---

# Future Ideas

* [ ] Automatic update checker
* [ ] Download missing chapters
* [ ] Batch downloads across series
* [ ] Plugin system for parsers
* [ ] Custom themes
* [ ] PDF / EPUB export
* [ ] Multiple language support
* [ ] Reading statistics
* [ ] Cross-device sync