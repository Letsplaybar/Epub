"""Shared EPUB 3 building blocks: metadata, OPF, nav/NCX, container and zip packaging."""

from __future__ import annotations

import io
import os
import re
import tempfile
import zipfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Sequence
from uuid import uuid4
from xml.etree import ElementTree as ET

from PIL import Image as PILImage

XHTML_NS = "http://www.w3.org/1999/xhtml"
EPUB_NS = "http://www.idpf.org/2007/ops"
SVG_NS = "http://www.w3.org/2000/svg"
XLINK_NS = "http://www.w3.org/1999/xlink"

OEBPS = "OEBPS"

# Pillow format name -> (media type, extension). These are EPUB 3.3 core media types.
_CORE_IMAGE_TYPES = {
    "JPEG": ("image/jpeg", "jpg"),
    "PNG": ("image/png", "png"),
    "WEBP": ("image/webp", "webp"),
    "GIF": ("image/gif", "gif"),
}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".tif", ".tiff"}

_INVALID_XML_CHARS = re.compile("[\x00-\x08\x0b\x0c\x0e-\x1f￾￿]")

# Old CLI language codes that are not valid BCP 47 tags.
LANGUAGE_ALIASES = {
    "jp": "ja",
    "kr": "ko",
    "sc": "zh-Hans",
    "tc": "zh-Hant",
    "mx": "es-MX",
    "por": "pt",
}


def clean_text(text: str) -> str:
    """Remove characters that are not allowed in XML (common in PDF-extracted text)."""
    return _INVALID_XML_CHARS.sub("", text)


def natural_key(text: str) -> list:
    return [int(c) if c.isdigit() else c.lower() for c in re.split(r"(\d+)", text)]


def normalize_language(lang: str | None) -> str:
    if not lang:
        return "en"
    return LANGUAGE_ALIASES.get(lang.lower(), lang)


@dataclass
class Meta:
    """Book metadata shared by manga and novel builds."""

    title: str
    author: str | Sequence[str] | None = None
    language: str = "en"
    publisher: str | None = None
    description: str | None = None
    genres: Sequence[str] = field(default_factory=list)
    series: str | None = None
    series_index: str | int | float | None = None
    date: str | None = None
    identifier: str | None = None
    modified: datetime | None = None

    @property
    def authors(self) -> list[str]:
        if not self.author:
            return []
        if isinstance(self.author, str):
            return [self.author]
        return [a for a in self.author if a]

    @property
    def lang(self) -> str:
        return normalize_language(self.language)


@dataclass
class PreparedImage:
    """An image ready to be stored in the EPUB (raw bytes or a source path)."""

    media_type: str
    ext: str
    width: int
    height: int
    source: Path | None = None
    data: bytes | None = None


def prepare_image(path: Path | str) -> PreparedImage:
    """Inspect an image by content (not extension); convert non-core formats to PNG/JPEG."""
    path = Path(path)
    with PILImage.open(path) as img:
        fmt = img.format
        width, height = img.size
        if fmt in _CORE_IMAGE_TYPES:
            media_type, ext = _CORE_IMAGE_TYPES[fmt]
            return PreparedImage(media_type, ext, width, height, source=path)
        buf = io.BytesIO()
        if img.mode in ("RGBA", "LA", "P", "1", "L"):
            img.save(buf, "PNG", optimize=True)
            media_type, ext = "image/png", "png"
        else:
            img.convert("RGB").save(buf, "JPEG", quality=92)
            media_type, ext = "image/jpeg", "jpg"
        return PreparedImage(media_type, ext, width, height, data=buf.getvalue())


# Elements whose content is text/inline markup: whitespace inside them would be visible.
_NO_INDENT = {"p", "h1", "h2", "h3", "h4", "h5", "h6", "figcaption", "title", "a", "text",
              "em", "strong", "ruby", "rt", "rp", "span", "dc:title", "dc:description", "meta"}


def _indent(elem: ET.Element, level: int = 0) -> None:
    if not len(elem) or elem.tag in _NO_INDENT or (elem.text and elem.text.strip()):
        return
    pad = "\n" + "  " * (level + 1)
    elem.text = pad
    for child in elem:
        _indent(child, level + 1)
        if not (child.tail and child.tail.strip()):
            child.tail = pad
    last = elem[-1]
    if not (last.tail and last.tail.strip()):
        last.tail = "\n" + "  " * level


def xml_bytes(root: ET.Element, doctype: str | None = None) -> bytes:
    _indent(root)
    body = ET.tostring(root, encoding="unicode")
    head = '<?xml version="1.0" encoding="UTF-8"?>\n'
    if doctype:
        head += doctype + "\n"
    return (head + body + "\n").encode("utf-8")


def xhtml_document(title: str, lang: str, css: Iterable[str] = (), *, extra_head=None,
                   body_attrs: dict | None = None) -> tuple[ET.Element, ET.Element]:
    """Create an XHTML5 skeleton; returns (html, body)."""
    html = ET.Element("html", {"xmlns": XHTML_NS, "xmlns:epub": EPUB_NS,
                               "xml:lang": lang, "lang": lang})
    head = ET.SubElement(html, "head")
    ET.SubElement(head, "meta", {"charset": "utf-8"})
    if extra_head:
        extra_head(head)
    ET.SubElement(head, "title").text = clean_text(title)
    for href in css:
        ET.SubElement(head, "link", {"rel": "stylesheet", "type": "text/css", "href": href})
    body = ET.SubElement(html, "body", body_attrs or {})
    return html, body


def svg_image(parent: ET.Element, href: str, width: int, height: int, alt: str = "") -> ET.Element:
    """Full-page image wrapped in SVG so it scales to the viewport keeping its aspect ratio."""
    svg = ET.SubElement(parent, "svg", {
        "xmlns": SVG_NS, "xmlns:xlink": XLINK_NS, "version": "1.1",
        "width": "100%", "height": "100%",
        "viewBox": f"0 0 {width} {height}", "preserveAspectRatio": "xMidYMid meet",
    })
    if alt:
        ET.SubElement(svg, "title").text = clean_text(alt)
    ET.SubElement(svg, "image", {"width": str(width), "height": str(height), "xlink:href": href})
    return svg


@dataclass
class _Item:
    id: str
    href: str
    media_type: str
    properties: str | None = None
    data: bytes | None = None
    source: Path | None = None


@dataclass
class _SpineRef:
    idref: str
    properties: str | None = None
    linear: bool = True


class EpubBuilder:
    """Collects files in memory (or by source path) and writes a valid EPUB 3 package.

    Nothing is written to the current working directory; the zip is written to a
    temporary file next to ``out`` and atomically moved into place.
    """

    def __init__(self, meta: Meta):
        self.meta = meta
        self.items: list[_Item] = []
        self.spine: list[_SpineRef] = []
        self.toc: list[tuple[str, str]] = []  # (href, title)
        self.landmarks: list[tuple[str, str, str]] = []  # (epub:type, href, title)
        self._ids: set[str] = set()
        self.uid = meta.identifier or f"urn:uuid:{uuid4()}"

    # -- manifest ---------------------------------------------------------
    def _unique_id(self, base: str) -> str:
        base = re.sub(r"[^A-Za-z0-9_.-]", "_", base)
        if not re.match(r"[A-Za-z_]", base):
            base = "id_" + base
        candidate, n = base, 1
        while candidate in self._ids:
            n += 1
            candidate = f"{base}_{n}"
        self._ids.add(candidate)
        return candidate

    def add(self, href: str, media_type: str, *, data: bytes | str | None = None,
            source: Path | None = None, properties: str | None = None, id: str | None = None) -> str:
        if isinstance(data, str):
            data = data.encode("utf-8")
        item_id = self._unique_id(id or Path(href).stem)
        self.items.append(_Item(item_id, href, media_type, properties, data, source))
        return item_id

    def add_image(self, href_stem: str, image: PreparedImage, properties: str | None = None,
                  id: str | None = None) -> str:
        """Add an image; returns its href (relative to the OPF)."""
        href = f"{href_stem}.{image.ext}"
        self.add(href, image.media_type, data=image.data, source=image.source,
                 properties=properties, id=id)
        return href

    def add_spine(self, item_id: str, properties: str | None = None, linear: bool = True) -> None:
        self.spine.append(_SpineRef(item_id, properties, linear))

    # -- generated documents ----------------------------------------------
    def _opf(self, rendition: dict[str, str], ppd: str | None, extra_meta: dict[str, str]) -> bytes:
        m = self.meta
        pkg = ET.Element("package", {"xmlns": "http://www.idpf.org/2007/opf", "version": "3.0",
                                     "unique-identifier": "uid", "xml:lang": m.lang})
        md = ET.SubElement(pkg, "metadata", {"xmlns:dc": "http://purl.org/dc/elements/1.1/",
                                             "xmlns:opf": "http://www.idpf.org/2007/opf"})
        ET.SubElement(md, "dc:identifier", {"id": "uid"}).text = self.uid
        ET.SubElement(md, "dc:title", {"id": "title"}).text = clean_text(m.title)
        ET.SubElement(md, "meta", {"refines": "#title", "property": "title-type"}).text = "main"
        ET.SubElement(md, "dc:language").text = m.lang
        for i, author in enumerate(m.authors, 1):
            ET.SubElement(md, "dc:creator", {"id": f"creator{i}"}).text = clean_text(author)
            ET.SubElement(md, "meta", {"refines": f"#creator{i}", "property": "role",
                                       "scheme": "marc:relators"}).text = "aut"
        if m.publisher:
            ET.SubElement(md, "dc:publisher").text = clean_text(m.publisher)
        if m.date:
            ET.SubElement(md, "dc:date").text = m.date
        for genre in m.genres:
            ET.SubElement(md, "dc:subject").text = clean_text(genre)
        if m.description:
            ET.SubElement(md, "dc:description").text = clean_text(m.description)
        modified = (m.modified or datetime.now(timezone.utc)).astimezone(timezone.utc)
        ET.SubElement(md, "meta", {"property": "dcterms:modified"}).text = \
            modified.strftime("%Y-%m-%dT%H:%M:%SZ")
        if m.series:
            ET.SubElement(md, "meta", {"property": "belongs-to-collection", "id": "series"}).text = \
                clean_text(m.series)
            ET.SubElement(md, "meta", {"refines": "#series", "property": "collection-type"}).text = "series"
            if m.series_index not in (None, ""):
                ET.SubElement(md, "meta", {"refines": "#series", "property": "group-position"}).text = \
                    str(m.series_index)
            ET.SubElement(md, "meta", {"name": "calibre:series", "content": clean_text(m.series)})
            if m.series_index not in (None, ""):
                ET.SubElement(md, "meta", {"name": "calibre:series_index", "content": str(m.series_index)})
        for prop, value in rendition.items():
            ET.SubElement(md, "meta", {"property": prop}).text = value
        cover = next((i for i in self.items if i.properties and "cover-image" in i.properties.split()), None)
        if cover:
            ET.SubElement(md, "meta", {"name": "cover", "content": cover.id})
        for name, content in extra_meta.items():
            ET.SubElement(md, "meta", {"name": name, "content": content})

        manifest = ET.SubElement(pkg, "manifest")
        for it in self.items:
            attrs = {"id": it.id, "href": it.href, "media-type": it.media_type}
            if it.properties:
                attrs["properties"] = it.properties
            ET.SubElement(manifest, "item", attrs)
        spine_attrs = {"toc": "ncx"}
        if ppd:
            spine_attrs["page-progression-direction"] = ppd
        spine = ET.SubElement(pkg, "spine", spine_attrs)
        for ref in self.spine:
            attrs = {"idref": ref.idref}
            if not ref.linear:
                attrs["linear"] = "no"
            if ref.properties:
                attrs["properties"] = ref.properties
            ET.SubElement(spine, "itemref", attrs)
        return xml_bytes(pkg)

    def _nav(self, css: Sequence[str]) -> bytes:
        html, body = xhtml_document(self.meta.title, self.meta.lang, css)
        nav = ET.SubElement(body, "nav", {"epub:type": "toc", "id": "toc", "role": "doc-toc"})
        ET.SubElement(nav, "h1").text = clean_text(self.meta.title)
        ol = ET.SubElement(nav, "ol")
        for href, title in self.toc:
            li = ET.SubElement(ol, "li")
            ET.SubElement(li, "a", {"href": href}).text = clean_text(title) or href
        if self.landmarks:
            lm = ET.SubElement(body, "nav", {"epub:type": "landmarks", "id": "landmarks", "hidden": "hidden"})
            ol = ET.SubElement(lm, "ol")
            for etype, href, title in self.landmarks:
                li = ET.SubElement(ol, "li")
                ET.SubElement(li, "a", {"epub:type": etype, "href": href}).text = clean_text(title)
        return xml_bytes(html, "<!DOCTYPE html>")

    def _ncx(self) -> bytes:
        root = ET.Element("ncx", {"xmlns": "http://www.daisy.org/z3986/2005/ncx/", "version": "2005-1",
                                  "xml:lang": self.meta.lang})
        head = ET.SubElement(root, "head")
        ET.SubElement(head, "meta", {"name": "dtb:uid", "content": self.uid})
        ET.SubElement(head, "meta", {"name": "dtb:depth", "content": "1"})
        ET.SubElement(head, "meta", {"name": "dtb:totalPageCount", "content": "0"})
        ET.SubElement(head, "meta", {"name": "dtb:maxPageNumber", "content": "0"})
        doc_title = ET.SubElement(root, "docTitle")
        ET.SubElement(doc_title, "text").text = clean_text(self.meta.title)
        nav_map = ET.SubElement(root, "navMap")
        for n, (href, title) in enumerate(self.toc, 1):
            point = ET.SubElement(nav_map, "navPoint", {"id": f"navpoint{n}", "playOrder": str(n)})
            label = ET.SubElement(point, "navLabel")
            ET.SubElement(label, "text").text = clean_text(title) or href
            ET.SubElement(point, "content", {"src": href})
        return xml_bytes(root)

    @staticmethod
    def _container() -> bytes:
        root = ET.Element("container", {"xmlns": "urn:oasis:names:tc:opendocument:xmlns:container",
                                        "version": "1.0"})
        files = ET.SubElement(root, "rootfiles")
        ET.SubElement(files, "rootfile", {"full-path": f"{OEBPS}/content.opf",
                                          "media-type": "application/oebps-package+xml"})
        return xml_bytes(root)

    # -- packaging ---------------------------------------------------------
    def write(self, out: Path | str, *, rendition: dict[str, str] | None = None, ppd: str | None = None,
              nav_css: Sequence[str] = (), extra_meta: dict[str, str] | None = None) -> Path:
        out = Path(out)
        if not self.spine:
            raise ValueError("EPUB needs at least one spine document")
        self.add("nav.xhtml", "application/xhtml+xml", data=self._nav(nav_css), properties="nav", id="nav")
        self.add("toc.ncx", "application/x-dtbncx+xml", data=self._ncx(), id="ncx")
        opf = self._opf(rendition or {}, ppd, extra_meta or {})

        out.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(prefix=".epub-", suffix=".tmp", dir=out.parent)
        os.close(fd)
        try:
            write_zip(Path(tmp_name), [
                ("META-INF/container.xml", self._container(), None),
                (f"{OEBPS}/content.opf", opf, None),
                *[(f"{OEBPS}/{it.href}", it.data, it.source) for it in self.items],
            ])
            umask = os.umask(0)
            os.umask(umask)
            os.chmod(tmp_name, 0o666 & ~umask)
            os.replace(tmp_name, out)
        except BaseException:
            Path(tmp_name).unlink(missing_ok=True)
            raise
        return out


def write_zip(path: Path, entries: Iterable[tuple[str, bytes | None, Path | None]]) -> None:
    """Write an OCF zip: uncompressed ``mimetype`` first, everything else deflated."""
    with zipfile.ZipFile(path, "w") as zf:
        info = zipfile.ZipInfo("mimetype", date_time=(1980, 1, 1, 0, 0, 0))
        info.compress_type = zipfile.ZIP_STORED
        zf.writestr(info, b"application/epub+zip")
        for arcname, data, source in entries:
            if data is None and source is not None:
                # Already-compressed images gain nothing from deflate.
                compress = zipfile.ZIP_STORED if source.suffix.lower() in {".jpg", ".jpeg", ".png",
                                                                          ".webp", ".gif"} \
                    else zipfile.ZIP_DEFLATED
                zf.write(source, arcname, compress_type=compress)
            else:
                zf.writestr(arcname, data or b"", compress_type=zipfile.ZIP_DEFLATED)
