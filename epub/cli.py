"""Command line interface, backwards compatible with the original ``Epub.py`` script.

Legacy usage (manga, default)::

    Epub -t "Title" -a Author -l en -i 004.xhtml -m "Chapter 1"

reads the images in ``./Title/`` and writes ``./Title.epub``. Markers keep the
old ``<image name>.xhtml`` format. Unlike the old script the source folder is
left untouched; folders already processed by the old script (images moved into
``Title/images/``) are still accepted.
"""

from __future__ import annotations

import sys
from optparse import OptionParser
from pathlib import Path

from . import __version__
from .common import IMAGE_EXTENSIONS, Meta, natural_key, normalize_language
from .manga import build_manga
from .novel import build_novel
from .textinput import load_novel_folder


def _parser() -> OptionParser:
    parser = OptionParser(usage="Usage: %prog [options]", version="%prog " + __version__)
    parser.add_option("-d", "--debug", action="store_true", dest="debug", default=False,
                      help="run program in debug mode, enable Logging messages")
    parser.add_option("-l", "--lang", action="store", dest="lang", default="de",
                      help="de (default) / en / sc / tc / mx / es / it / por / fr / jp / kr (or any BCP 47 tag)")
    parser.add_option("-t", "--title", action="store", dest="title", default=False, help="Title of Epub")
    parser.add_option("-a", "--author", action="store", dest="author", default=False, help="Author of Epub")
    parser.add_option("-g", "--genre", action="append", dest="genre", default=[], help="Genres of Epub")
    parser.add_option("-i", "--marker-index", action="append", dest="marker_index", default=[],
                      help="page for table of contents")
    parser.add_option("-m", "--marker-title", action="append", dest="marker_title", default=[],
                      help="name for page in table of contents")
    parser.add_option("-p", "--publisher", action="store", dest="publisher", default=False,
                      help="Publisher of Epub")
    parser.add_option("-D", "--describtion", "--description", action="store", dest="description",
                      default=False, help="Description of Epub")
    parser.add_option("-s", "--series", action="store", dest="series", default=False, help="Series of Epub")
    parser.add_option("-n", "--number", action="store", dest="number", default=False,
                      help="Number of Epub in the series")
    parser.add_option("--jpg", action="store_const", dest="format", default=None, const="jpg",
                      help="only use .jpg images (default: all png/jpg/jpeg/webp/gif images)")
    parser.add_option("--jpeg", action="store_const", dest="format", default=None, const="jpeg",
                      help="only use .jpeg images (default: all png/jpg/jpeg/webp/gif images)")
    parser.add_option("--png", action="store_const", dest="format", default=None, const="png",
                      help="only use .png images")
    parser.add_option("--ltr", action="store_false", dest="rtl", default=True,
                      help="manga: left-to-right page progression (default right-to-left)")
    parser.add_option("--novel", action="store_true", dest="novel", default=False,
                      help="build a reflowable novel from .md/.txt chapter files in the folder")
    parser.add_option("--vertical", action="store_true", dest="vertical", default=False,
                      help="novel: Japanese vertical writing (vertical-rl, right-to-left)")
    parser.add_option("--cover", action="store", dest="cover", default=None,
                      help="novel: cover image (default: cover.* in the folder)")
    parser.add_option("--input", action="store", dest="input", default=None,
                      help="source folder (default: ./<title>)")
    parser.add_option("-o", "--output", action="store", dest="output", default=None,
                      help="output file (default: ./<title>.epub)")
    return parser


def collect_images(folder: Path, fmt: str | None = None) -> list[Path]:
    """Page images of a manga folder in natural order (old-script layout aware)."""
    def images_in(d: Path) -> list[Path]:
        if not d.is_dir():
            return []
        exts = {"." + fmt} if fmt else IMAGE_EXTENSIONS
        return [p for p in d.iterdir() if p.is_file() and p.suffix.lower() in exts
                and "Cover" not in p.name and not p.name.startswith(".")]

    # The old script moved pages into <title>/images/ and left a Cover.* copy behind.
    found = images_in(folder / "images") or images_in(folder)
    return sorted(found, key=lambda p: natural_key(p.name))


def _resolve_markers(images: list[Path], indexes: list[str], titles: list[str]) -> list[tuple[int, str]]:
    by_stem = {p.stem: i for i, p in enumerate(images)}
    by_name = {p.name: i for i, p in enumerate(images)}
    markers = []
    for ref, title in zip(indexes, titles):
        stem = ref[:-6] if ref.endswith(".xhtml") else ref[:-5] if ref.endswith(".html") else ref
        idx = by_stem.get(stem, by_name.get(ref))
        if idx is None:
            print(f"warning: marker {ref!r} ({title}) does not match any image, skipped", file=sys.stderr)
            continue
        markers.append((idx, title))
    return markers


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    options, _args = parser.parse_args(argv)
    if len(options.marker_index) != len(options.marker_title):
        print("same amount of marker-index and marker-title requiered!")
        return -1
    if not options.title:
        parser.print_usage(sys.stderr)
        return 0

    folder = Path(options.input) if options.input else Path(".") / options.title
    out = Path(options.output) if options.output else Path(".") / (options.title + ".epub")
    meta = Meta(
        title=options.title,
        author=options.author or None,
        language=normalize_language(options.lang),
        publisher=options.publisher or None,
        description=options.description or None,
        genres=options.genre,
        series=options.series or None,
        series_index=options.number or None,
    )
    if not folder.is_dir():
        print(f"error: folder {str(folder)!r} not found", file=sys.stderr)
        return 1

    if options.novel:
        chapters, cover = load_novel_folder(folder)
        if options.cover:
            cover = Path(options.cover)
        if not chapters:
            print(f"error: no .md/.txt chapter files in {str(folder)!r}", file=sys.stderr)
            return 1
        build_novel(chapters, out, meta, cover=cover, vertical=options.vertical)
    else:
        images = collect_images(folder, options.format)
        if not images:
            print(f"error: no images found in {str(folder)!r}", file=sys.stderr)
            return 1
        markers = _resolve_markers(images, options.marker_index, options.marker_title)
        build_manga(images, out, meta, markers=markers, rtl=options.rtl)
    print(options.title + " competed!")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
