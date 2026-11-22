"""Reflowable EPUB 3 for light novels: semantic XHTML per chapter plus illustrations."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Sequence, Union
from xml.etree import ElementTree as ET

from .common import (EpubBuilder, Meta, PreparedImage, clean_text, prepare_image, svg_image,
                     xhtml_document, xml_bytes)


# --- content model -----------------------------------------------------------

@dataclass
class Run:
    """A piece of inline text. ``ruby`` adds a reading annotation (furigana) above ``text``."""

    text: str
    em: bool = False
    strong: bool = False
    ruby: str | None = None


@dataclass
class Heading:
    level: int
    text: str


@dataclass
class Paragraph:
    """A paragraph made of runs (plain strings are allowed). ``align``: None/center/right."""

    runs: Sequence[Union[Run, str]] | str = field(default_factory=list)
    align: str | None = None

    def __post_init__(self):
        if isinstance(self.runs, str):
            self.runs = [self.runs]
        self.runs = [Run(r) if isinstance(r, str) else r for r in self.runs]


@dataclass
class Image:
    """An illustration. ``full_page`` images get a page of their own."""

    path: Path | str
    alt: str = ""
    full_page: bool = False
    caption: str | None = None


@dataclass
class SceneBreak:
    pass


Block = Union[Heading, Paragraph, Image, SceneBreak]


@dataclass
class Chapter:
    title: str
    blocks: list[Block] = field(default_factory=list)


# --- styling -----------------------------------------------------------------

STYLE_CSS = """@charset "utf-8";
html, body { margin: 0; padding: 0; }
body { line-height: 1.5; widows: 2; orphans: 2; }
p {
  margin: 0;
  text-indent: 1em;
  text-align: justify;
  -webkit-hyphens: auto;
  -epub-hyphens: auto;
  hyphens: auto;
}
h1 + p, h2 + p, h3 + p, h4 + p, h5 + p, h6 + p,
hr.scene-break + p, figure + p, p.center, p.right { text-indent: 0; }
p.center { text-align: center; }
p.right { text-align: right; }
h1, h2, h3, h4, h5, h6 {
  line-height: 1.25;
  text-align: center;
  -webkit-hyphens: none;
  -epub-hyphens: none;
  hyphens: none;
  page-break-after: avoid;
  break-after: avoid;
}
h1 { font-size: 1.6em; margin: 2em 0 1.5em; }
h2 { font-size: 1.3em; margin: 1.5em 0 1em; }
h3 { font-size: 1.15em; margin: 1.2em 0 0.8em; }
h4, h5, h6 { font-size: 1em; margin: 1em 0 0.5em; }
section.chapter { page-break-before: always; break-before: page; }
hr.scene-break {
  border: 0;
  border-top: 1px solid currentColor;
  width: 30%;
  margin: 1.5em auto;
  opacity: 0.6;
}
figure {
  margin: 1em 0;
  text-align: center;
  text-indent: 0;
  page-break-inside: avoid;
  break-inside: avoid;
}
img { max-width: 100%; height: auto; }
figure img { max-height: 95vh; }
figcaption { font-size: 0.9em; font-style: italic; margin-top: 0.3em; }
rt { font-size: 0.5em; }
body.fullpage, body.cover { margin: 0; padding: 0; text-align: center; }
div.fullpage { margin: 0; padding: 0; height: 100%; text-align: center; }
div.fullpage svg { display: block; margin: 0 auto; width: 100%; height: 100%; }
"""

VERTICAL_CSS = """@charset "utf-8";
html {
  -epub-writing-mode: vertical-rl;
  -webkit-writing-mode: vertical-rl;
  writing-mode: vertical-rl;
}
p { text-align: start; }
hr.scene-break { width: auto; height: 30%; border-top: 0; border-right: 1px solid currentColor; margin: auto 1.5em; }
img { max-height: 100%; max-width: none; width: auto; }
figure img { max-height: 95vh; }
body.fullpage, body.cover { writing-mode: horizontal-tb; -epub-writing-mode: horizontal-tb; -webkit-writing-mode: horizontal-tb; }
"""


# --- rendering ---------------------------------------------------------------

def _append_text(parent: ET.Element, text: str) -> None:
    text = clean_text(text)
    if not text:
        return
    if len(parent):
        last = parent[-1]
        last.tail = (last.tail or "") + text
    else:
        parent.text = (parent.text or "") + text


def _render_run(parent: ET.Element, run: Run) -> None:
    target = parent
    if run.strong:
        target = ET.SubElement(target, "strong")
    if run.em:
        target = ET.SubElement(target, "em")
    if run.ruby:
        ruby = ET.SubElement(target, "ruby")
        ruby.text = clean_text(run.text)
        ET.SubElement(ruby, "rp").text = "("
        ET.SubElement(ruby, "rt").text = clean_text(run.ruby)
        ET.SubElement(ruby, "rp").text = ")"
    elif target is parent:
        _append_text(parent, run.text)
    else:
        target.text = clean_text(run.text)


class _NovelBuilder:
    def __init__(self, meta: Meta, vertical: bool):
        self.meta = meta
        self.book = EpubBuilder(meta)
        self.css = ["css/style.css"] + (["css/vertical.css"] if vertical else [])
        self.book.add("css/style.css", "text/css", data=STYLE_CSS, id="css")
        if vertical:
            self.book.add("css/vertical.css", "text/css", data=VERTICAL_CSS, id="css-vertical")
        self._images: dict[Path, tuple[str, PreparedImage]] = {}
        self._doc_count = 0

    def image(self, path: Path | str, cover: bool = False) -> tuple[str, PreparedImage]:
        key = Path(path).resolve()
        if key not in self._images:
            prepared = prepare_image(key)
            stem = "images/cover" if cover else f"images/img{len(self._images) + 1:04d}"
            href = self.book.add_image(stem, prepared, properties="cover-image" if cover else None,
                                       id="cover-image" if cover else None)
            self._images[key] = (href, prepared)
        return self._images[key]

    def _doc(self, href: str, html: ET.Element, svg: bool = False, id: str | None = None,
             linear: bool = True) -> str:
        item_id = self.book.add(href, "application/xhtml+xml", data=xml_bytes(html, "<!DOCTYPE html>"),
                                properties="svg" if svg else None, id=id)
        self.book.add_spine(item_id, linear=linear)
        return href

    def image_page(self, href: str, img: Image | Path, title: str, epub_type: str = "bodymatter",
                   cover: bool = False) -> str:
        path = img.path if isinstance(img, Image) else img
        alt = img.alt if isinstance(img, Image) else title
        img_href, prepared = self.image(path, cover=cover)
        up = "../" * href.count("/")
        cls = "cover" if cover else "fullpage"
        html, body = xhtml_document(title, self.meta.lang, [up + c for c in self.css],
                                    body_attrs={"class": cls, "epub:type": epub_type})
        div = ET.SubElement(body, "div", {"class": "fullpage"})
        svg_image(div, up + img_href, prepared.width, prepared.height, alt=alt)
        if isinstance(img, Image) and img.caption:
            # Keep captions accessible for screen readers without breaking the page layout.
            ET.SubElement(div, "p", {"class": "center"}).text = clean_text(img.caption)
        return self._doc(href, html, svg=True, id="cover" if cover else None)

    def text_page(self, href: str, title: str, show_title: bool, blocks: list[Block]) -> str:
        up = "../" * href.count("/")
        html, body = xhtml_document(title or self.meta.title, self.meta.lang, [up + c for c in self.css],
                                    body_attrs={"epub:type": "bodymatter"})
        section = ET.SubElement(body, "section", {"class": "chapter", "epub:type": "chapter",
                                                  "role": "doc-chapter"})
        if show_title and title:
            ET.SubElement(section, "h1").text = clean_text(title)
        for block in blocks:
            if isinstance(block, Heading):
                level = min(max(int(block.level), 1), 6)
                ET.SubElement(section, f"h{level}").text = clean_text(block.text)
            elif isinstance(block, Paragraph):
                attrs = {"class": block.align} if block.align in ("center", "right") else {}
                p = ET.SubElement(section, "p", attrs)
                for run in block.runs:
                    _render_run(p, run)
            elif isinstance(block, SceneBreak):
                ET.SubElement(section, "hr", {"class": "scene-break"})
            elif isinstance(block, Image):
                img_href, _ = self.image(block.path)
                fig = ET.SubElement(section, "figure", {"class": "illustration"})
                ET.SubElement(fig, "img", {"src": up + img_href, "alt": clean_text(block.alt or "")})
                if block.caption:
                    ET.SubElement(fig, "figcaption").text = clean_text(block.caption)
            else:
                raise TypeError(f"unknown block type: {type(block).__name__}")
        return self._doc(href, html)

    def chapter(self, number: int, chapter: Chapter) -> str | None:
        """Render a chapter into one or more spine documents; returns the first href."""
        first: str | None = None
        part, img_no = 1, 0
        pending: list[Block] = []
        title_shown = False

        def flush():
            nonlocal part, first, title_shown
            if not pending:
                return
            href = f"text/ch{number:03d}.xhtml" if part == 1 else f"text/ch{number:03d}_{part}.xhtml"
            self.text_page(href, chapter.title, not title_shown, list(pending))
            title_shown = True
            first = first or href
            part += 1
            pending.clear()

        for block in chapter.blocks:
            if isinstance(block, Image) and block.full_page:
                flush()
                img_no += 1
                href = self.image_page(f"text/ch{number:03d}_img{img_no:02d}.xhtml", block,
                                       block.alt or chapter.title)
                first = first or href
            else:
                pending.append(block)
        flush()
        if first is None and chapter.title:
            # Title-only chapter: still give it a page so the TOC entry has a target.
            first = self.text_page(f"text/ch{number:03d}.xhtml", chapter.title, True, [])
        return first


def build_novel(chapters: Sequence[Chapter], out: Path | str, meta: Meta,
                cover: Path | str | None = None, vertical: bool = False) -> Path:
    """Build a reflowable EPUB 3 from chapters.

    Each chapter becomes one XHTML file (split around full-page illustrations).
    ``cover`` is an optional cover image shown as first page and flagged as
    ``cover-image``. ``vertical`` enables Japanese vertical writing
    (``writing-mode: vertical-rl``) with right-to-left page progression.
    """
    if not chapters:
        raise ValueError("build_novel needs at least one chapter")
    nb = _NovelBuilder(meta, vertical)
    book = nb.book
    if cover:
        cover_href = nb.image_page("cover.xhtml", Path(cover), meta.title, epub_type="cover", cover=True)
        book.landmarks.append(("cover", cover_href, "Cover"))

    for number, chapter in enumerate(chapters, 1):
        href = nb.chapter(number, chapter)
        if href:
            book.toc.append((href, chapter.title or f"{number}"))
    if not book.toc:
        raise ValueError("chapters contain no content")
    book.landmarks.append(("bodymatter", book.toc[0][0], "Start"))

    extra = {"primary-writing-mode": "vertical-rl"} if vertical else {}
    return book.write(out, ppd="rtl" if vertical else "ltr", nav_css=nb.css, extra_meta=extra)
