# Workflow

## Vision

Build an offline-first comic reader that recreates the seamless web reading experience.

Instead of downloading hundreds of individual images, the application downloads an entire series, stitches each chapter into a single continuous image, and provides a smooth local reading experience.

---

# User Workflow

## 1. Find a Series

The user is reading a comic on a supported website.

Example:

```
https://toonily.com/webtoon/example-series/
```

The user wants to read it offline without downloading every panel manually.

---

## 2. Paste URL

The application opens with a simple input screen.

```
+-------------------------------------------+

Paste Series URL

[_______________________________________]

            [ Analyze ]

+-------------------------------------------+
```

The user pastes the series URL.

---

## 3. Analyze Series

The application fetches:

* Series title
* Cover image
* Available chapters
* Estimated download size
* Supported website validation

Example:

```
Series:
Solo Leveling

179 Chapters

Estimated Download:
2.6 GB
```

The user selects:

* Entire series
* Specific chapters
* Missing chapters only (future)

---

## 4. Download

For every selected chapter:

```
Chapter

↓

Extract image URLs

↓

Download images

↓

Stitch images

↓

Optimize

↓

Save
```

Progress is shown in real time.

Example:

```
Chapter 32

Downloading...
████████░░░ 82%

Stitching...

Saving...
```

---

## 5. Library

Completed downloads appear in the local library.

Example:

```
Solo Leveling

Chapter 001
Chapter 002
Chapter 003
...
```

No internet is required after download.

---

## 6. Read

Opening a chapter displays a single continuous image.

Instead of:

```
page1.png
page2.png
page3.png
...
```

The reader opens:

```
Chapter001.webp
```

Scrolling behaves exactly like reading on the original website.

No page breaks.

No cut speech bubbles.

No split artwork.

Just one uninterrupted reading experience.

---

# Reader Responsibilities

The reader should only focus on reading.

Features:

* Smooth scrolling
* Zoom
* Fit Width
* Fit Height
* Original Size
* Previous / Next Chapter
* Remember last reading position

Nothing more.

---

# Downloader Responsibilities

Responsible for everything before reading.

Tasks:

* Parse supported websites
* Discover chapters
* Extract image URLs
* Download images
* Stitch chapter images
* Optimize output
* Save metadata
* Resume interrupted downloads (future)

---

# Output Structure

```
Library/

└── Solo Leveling/
    │
    ├── cover.webp
    ├── metadata.json
    │
    ├── Chapter 001.webp
    ├── Chapter 002.webp
    ├── Chapter 003.webp
    └── ...
```

Each chapter is stored as one optimized image.

---

# Design Philosophy

The application should feel invisible.

It should not compete with comic websites.

It should preserve their reading experience while removing the dependency on an internet connection.

Every design decision should answer one question:

> "Does this make offline reading feel as effortless as reading online?"

If the answer is no, reconsider the feature.

---

# Future Features

* Resume interrupted downloads
* Update existing libraries with newly released chapters
* Multiple website support
* Chapter export
* Metadata editing
* Reading statistics
* Bookmarks
* Favorites
* Multiple stitch modes
* Batch downloads
* Plugin architecture
