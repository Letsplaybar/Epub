"""Fixed-layout EPUB 3 for manga/comics: one image per page."""

from __future__ import annotations

from pathlib import Path
from typing import Sequence
from xml.etree import ElementTree as ET

from .common import EpubBuilder, Meta, prepare_image, svg_image, xhtml_document, xml_bytes

MANGA_CSS = """@charset "utf-8";
html, body { margin: 0; padding: 0; width: 100%; height: 100%; overflow: hidden; }
div.page { margin: 0; padding: 0; width: 100%; height: 100%; text-align: center; }
svg { margin: 0; padding: 0; display: block; width: 100%; height: 100%; }
"""


def build_manga(images: Sequence[Path | str], out: Path | str, meta: Meta,
                markers: Sequence[tuple[int, str]] | None = None, rtl: bool = False,
                spread: str = "landscape") -> Path:
    """Build a pre-paginated EPUB with one page per image.

    ``images`` are page images in reading order (jpg/png/webp/gif, mixed; other
    formats Pillow can read are converted). The first image is the cover.
    ``markers`` are ``(page_index, title)`` pairs (0-based) for the table of
    contents; a "Cover" entry for page 0 is added when none points there.
    ``rtl`` sets right-to-left page progression (Japanese manga).
    ``spread`` is the ``rendition:spread`` value (none/landscape/both/auto).
    """
    images = [Path(p) for p in images]
    if not images:
        raise ValueError("build_manga needs at least one image")
    lang = meta.lang
    book = EpubBuilder(meta)
    book.add("css/manga.css", "text/css", data=MANGA_CSS, id="css")

    width_digits = max(4, len(str(len(images))))
    pages: list[str] = []
    for index, src in enumerate(images):
        num = str(index + 1).zfill(width_digits)
        img = prepare_image(src)
        is_cover = index == 0
        img_href = book.add_image(f"images/{'cover' if is_cover else 'p' + num}", img,
                                  properties="cover-image" if is_cover else None,
                                  id="cover-image" if is_cover else f"img{num}")

        def viewport(head, w=img.width, h=img.height):
            ET.SubElement(head, "meta", {"name": "viewport", "content": f"width={w}, height={h}"})

        title = meta.title if is_cover else f"{meta.title} – {index + 1}"
        html, body = xhtml_document(title, lang, ["css/manga.css"], extra_head=viewport,
                                    body_attrs={"epub:type": "cover" if is_cover else "bodymatter"})
        div = ET.SubElement(body, "div", {"class": "page"})
        svg_image(div, img_href, img.width, img.height, alt=meta.title if is_cover else "")
        page_href = "cover.xhtml" if is_cover else f"p{num}.xhtml"
        item_id = book.add(page_href, "application/xhtml+xml",
                           data=xml_bytes(html, "<!DOCTYPE html>"), properties="svg",
                           id="cover" if is_cover else f"page{num}")
        pages.append(page_href)

        if is_cover:
            props = "rendition:page-spread-center"
        else:
            # Pages after the cover form spreads; the first page of a spread sits on the
            # right for RTL books and on the left for LTR books.
            first_of_spread = (index - 1) % 2 == 0
            side = ("right" if first_of_spread else "left") if rtl else \
                ("left" if first_of_spread else "right")
            props = f"page-spread-{side}"
        book.add_spine(item_id, props)

    toc = sorted({i: t for i, t in (markers or []) if 0 <= i < len(images)}.items())
    if not toc or toc[0][0] != 0:
        toc.insert(0, (0, "Cover"))
    book.toc = [(pages[i], t) for i, t in toc]
    book.landmarks = [("cover", pages[0], "Cover")]
    body_index = next((i for i, _ in toc if i > 0), 1 if len(pages) > 1 else 0)
    book.landmarks.append(("bodymatter", pages[body_index], "Start"))

    return book.write(out, rendition={
        "rendition:layout": "pre-paginated",
        "rendition:orientation": "auto",
        "rendition:spread": spread,
    }, ppd="rtl" if rtl else "ltr", extra_meta={"book-type": "comic", "fixed-layout": "true"})
