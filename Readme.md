# Epub – EPUB 3 builder for Manga, Comics and Light Novels

Builds valid EPUB 3 files (checked with [epubcheck](https://github.com/w3c/epubcheck)):

* **Manga / comics** – fixed layout (`pre-paginated`), one image per page, right-to-left or
  left-to-right page progression, mixed jpg/png/webp/gif.
* **Light novels** – reflowable, one semantic XHTML file per chapter, illustrations,
  ruby (furigana), scene breaks, optional Japanese vertical writing.

Usable as a Python library or as the command line script `Epub.py` (the original CLI options still
work unchanged).

## Installation

Python ≥ 3.10, the only dependency is [Pillow](https://python-pillow.org/).

```bash
pip install "letsplaybar-epub @ git+https://github.com/Letsplaybar/Epub@v1.0.0"
```

This installs the `epub` package and the `Epub` command. Without installing you can also run
`python3 Epub.py …` from a checkout (Pillow required).

## Library API

```python
from pathlib import Path
from epub import Meta, build_manga, build_novel, Chapter, Heading, Paragraph, Run, Image, SceneBreak

meta = Meta(
    title="My Book Vol. 5",
    author="Some Author",            # str or list of str
    language="en",                   # BCP 47 (old aliases jp/kr/sc/tc/mx/por are mapped)
    publisher="Publisher",
    description="…",
    genres=["Action", "Comedy"],
    series="My Book",                # -> belongs-to-collection + calibre:series
    series_index=5,                  # -> group-position + calibre:series_index
    date="2024-01-31",               # optional dc:date
    identifier=None,                 # default: random urn:uuid
)
```

### Manga

```python
images = sorted(Path("pages").glob("*"))           # reading order, first image = cover
build_manga(images, Path("out/book.epub"), meta,
            markers=[(4, "Chapter 1"), (24, "Chapter 2")],  # (0-based page index, TOC title)
            rtl=True,                                         # Japanese reading direction
            spread="landscape")                              # rendition:spread
```

* Every image becomes an XHTML page with an SVG wrapper and a viewport of the image size.
* Image types are detected by content; formats outside the EPUB core types (BMP, TIFF, …)
  are converted to PNG/JPEG.
* A `Cover` TOC entry for page 0 is added if no marker points there.
* Nothing is written to the current directory; the source images are not modified.

### Light novel

```python
chapters = [
    Chapter("Prologue", [
        Image("color1.jpg", alt="Colour illustration", full_page=True),   # own page
        Paragraph("Plain text paragraph."),
        Paragraph([Run("Emphasis", em=True), " and ", Run("strong", strong=True), " and ",
                   Run("漢字", ruby="かんじ"), "."]),
        SceneBreak(),
        Image("illu.png", alt="Illustration", caption="Optional caption"),  # inline <figure>
        Heading(2, "Sub heading"),
        Paragraph("Centered line", align="center"),
    ]),
    Chapter("Chapter 1", [...]),
]
build_novel(chapters, Path("out/novel.epub"), meta, cover=Path("cover.jpg"), vertical=False)
```

* One XHTML per chapter (`<section epub:type="chapter">` with `<h1>` title), split around
  full-page images, which get a page of their own.
* `style.css`: paragraph indent, justified text with hyphenation, page break before chapters,
  `img { max-width: 100% }`.
* `vertical=True` adds `writing-mode: vertical-rl` and right-to-left page progression for
  Japanese light novels.
* Control characters (e.g. from PDF text extraction) are removed, everything is XML-escaped.

## Command line

```
Usage: Epub [options]

Options:
  --version             show program's version number and exit
  -h, --help            show this help message and exit
  -d, --debug           run program in debug mode, enable Logging messages
  -l LANG, --lang=LANG  de (default) / en / sc / tc / mx / es / it / por / fr
                        / jp / kr (or any BCP 47 tag)
  -t TITLE, --title=TITLE
                        Title of Epub
  -a AUTHOR, --author=AUTHOR
                        Author of Epub
  -g GENRE, --genre=GENRE
                        Genres of Epub
  -i MARKER_INDEX, --marker-index=MARKER_INDEX
                        page for table of contents
  -m MARKER_TITLE, --marker-title=MARKER_TITLE
                        name for page in table of contents
  -p PUBLISHER, --publisher=PUBLISHER
                        Publisher of Epub
  -D DESCRIPTION, --describtion=DESCRIPTION, --description=DESCRIPTION
                        Description of Epub
  -s SERIES, --series=SERIES
                        Series of Epub
  -n NUMBER, --number=NUMBER
                        Number of Epub in the series
  --jpg                 only use .jpg images (default: all png/jpg/jpeg/webp/gif images)
  --jpeg                only use .jpeg images (default: all png/jpg/jpeg/webp/gif images)
  --png                 only use .png images
  --ltr                 manga: left-to-right page progression (default right-to-left)
  --novel               build a reflowable novel from .md/.txt chapter files in the folder
  --vertical            novel: Japanese vertical writing (vertical-rl, right-to-left)
  --cover=COVER         novel: cover image (default: cover.* in the folder)
  --input=INPUT         source folder (default: ./<title>)
  -o OUTPUT, --output=OUTPUT
                        output file (default: ./<title>.epub)
```

The CLI reads the folder `./<title>/` and writes `./<title>.epub` in the current directory.
The source folder is no longer modified (folders already processed by older versions, with the
pages moved into `<title>/images/`, still work).

### Manga folder

```
Title of Book/
  000.png      <- first image (natural sort order) is the cover
  001.png
  002.jpg      <- mixed formats are fine unless --jpg/--jpeg/--png restricts them
  …
```

Example:

`Epub -l en -t "Trapped in a Dating Sim The World of Otome Games is Tough for Mobs Vol. 5" -a "Yomu Mishima" -g Sci-Fi -g Isekai -g Adventure -g Comedy -g Mecha -g "School Life" -g Action -g Harem -g Romance -g Drama -p "Seven Seas Entertainment" -s "Trapped in a Dating Sim: The World of Otome Games is Tough for Mobs" -n 5 -i 004.xhtml -m "The Harbinger of a Collapse" -i 024.xhtml -m "Vanquishment of the Sky Pirates 1" -i 074.xhtml -m "Vanquishment of the Sky Pirates 2" -i 112.xhtml -m "Vanquishment of the Sky Pirates 3" -i 134.xhtml -m "The Right Path" -D "Angelica wasbeen working to patch things up with Olivia, …"`

Always the n-th `-i` is assigned to the n-th `-m`. `-i` names the image file with `.xhtml`
instead of its image extension (`004.png` → `004.xhtml`):

| i | m |
|---|---|
| 000.xhtml | Cover (added automatically) |
| 004.xhtml | The Harbinger of a Collapse |
| 024.xhtml | Vanquishment of the Sky Pirates 1 |
| 074.xhtml | Vanquishment of the Sky Pirates 2 |
| 112.xhtml | Vanquishment of the Sky Pirates 3 |
| 134.xhtml | The Right Path |

### Novel folder (`--novel`)

```
Title of Book/
  cover.jpg             <- optional cover (or --cover path)
  01 - Prologue.md      <- one file per chapter, natural sort order
  02 - Chapter 1.txt
  illu1.png             <- images referenced from the chapter files
```

Chapter file syntax (Markdown subset):

| Syntax | Result |
|---|---|
| `# Title` (first line) | chapter title (otherwise the file name without number prefix) |
| `##` … `######` | sub headings |
| blank line | new paragraph (`.md`); in `.txt` every line is a paragraph |
| `*em*`, `_em_`, `**strong**`, `***both***` | emphasis |
| `{漢字\|かんじ}`, `\|漢字《かんじ》`, `漢字《かんじ》` | ruby / furigana |
| `***`, `---`, `* * *`, `◇◇◇` on a line | scene break |
| `![alt](image.jpg)` / `![alt](image.jpg "caption")` | inline illustration |
| `![alt](image.jpg){.full}` | full-page illustration |

```bash
Epub --novel -l jp --vertical -t "My Light Novel" -a "Author"
```

## Development

```bash
pip install -e ".[test]"   # pytest + epubcheck (needs Java)
pytest
```

The tests build manga and novel EPUBs from small generated fixtures and validate them with
epubcheck; CI runs them on GitHub Actions.

Epub support Apple Books, Kobo, Calibre and other EPUB 3 readers.
