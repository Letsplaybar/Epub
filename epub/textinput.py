"""Simple folder input for novels: one ``.md``/``.txt`` file per chapter plus images.

Supported syntax (Markdown subset):

* ``# Title`` on the first line sets the chapter title (else the file name is used)
* ``## …`` to ``###### …`` become sub-headings
* ``***``, ``---``, ``* * *``, ``◇◇◇`` … on their own line are scene breaks
* ``![alt](image.jpg)`` on its own line is an illustration; append ``{.full}``
  for a full-page image and ``"caption"`` as title for a caption
* inline: ``***both***``, ``**strong**``, ``*em*`` / ``_em_``, ruby as
  ``{漢字|かんじ}``, ``|漢字《かんじ》`` or ``漢字《かんじ》``
* ``.md``: paragraphs are separated by blank lines; ``.txt``: every non-empty line
  is a paragraph
"""

from __future__ import annotations

import re
from pathlib import Path

from .common import IMAGE_EXTENSIONS, natural_key
from .novel import Chapter, Heading, Image, Paragraph, Run, SceneBreak

_HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
_SCENE = re.compile(r"^\s*(?:([*\-_~=◇◆＊※・○●#])\s*){3,}$")
_IMAGE = re.compile(r'^\s*!\[(?P<alt>[^\]]*)\]\((?P<src>[^)\s]+)(?:\s+"(?P<cap>[^"]*)")?\)\s*'
                    r'(?P<attr>\{\s*\.?full\s*\})?\s*$')
_INLINE = re.compile(
    r"\*\*\*(?P<se>.+?)\*\*\*"
    r"|\*\*(?P<s>.+?)\*\*"
    r"|\*(?P<e>[^*\s](?:.*?[^*\s])??)\*"
    r"|(?<!\w)_(?P<e2>[^_\s](?:.*?[^_\s])??)_(?!\w)"
    r"|\{(?P<rb>[^{}|]+)\|(?P<rt>[^{}]+)\}"
    r"|[|｜](?P<rb2>[^|｜《]+)《(?P<rt2>[^》]+)》"
    r"|(?P<rb3>[㐀-鿿豈-﫿々〆ヶ]+)《(?P<rt3>[^》]+)》"
)
_CHAPTER_PREFIX = re.compile(r"^\d+[\s._-]*")


def parse_inline(text: str) -> list[Run]:
    runs: list[Run] = []
    pos = 0
    for m in _INLINE.finditer(text):
        if m.start() > pos:
            runs.append(Run(text[pos:m.start()]))
        g = m.groupdict()
        if g["se"] is not None:
            runs.append(Run(g["se"], em=True, strong=True))
        elif g["s"] is not None:
            runs.append(Run(g["s"], strong=True))
        elif g["e"] is not None or g["e2"] is not None:
            runs.append(Run(g["e"] if g["e"] is not None else g["e2"], em=True))
        elif g["rb"] is not None:
            runs.append(Run(g["rb"], ruby=g["rt"]))
        elif g["rb2"] is not None:
            runs.append(Run(g["rb2"], ruby=g["rt2"]))
        else:
            runs.append(Run(g["rb3"], ruby=g["rt3"]))
        pos = m.end()
    if pos < len(text):
        runs.append(Run(text[pos:]))
    return runs


def parse_chapter(path: Path) -> Chapter:
    path = Path(path)
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    markdown = path.suffix.lower() == ".md"
    title = None
    blocks = []
    para: list[str] = []

    def flush():
        if para:
            blocks.append(Paragraph(parse_inline(" ".join(s.strip() for s in para))))
            para.clear()

    for i, raw in enumerate(lines):
        line = raw.rstrip()
        stripped = line.strip()
        if not stripped:
            flush()
            continue
        h = _HEADING.match(stripped)
        img = _IMAGE.match(stripped)
        if h and len(h.group(1)) == 1 and title is None and not blocks and not para:
            title = h.group(2)
        elif h:
            flush()
            blocks.append(Heading(len(h.group(1)), h.group(2)))
        elif img:
            flush()
            src = (path.parent / img.group("src")).resolve()
            blocks.append(Image(src, alt=img.group("alt"), full_page=bool(img.group("attr")),
                                caption=img.group("cap")))
        elif _SCENE.match(stripped):
            flush()
            blocks.append(SceneBreak())
        elif markdown:
            para.append(stripped)
        else:
            blocks.append(Paragraph(parse_inline(stripped)))
    flush()
    if title is None:
        title = _CHAPTER_PREFIX.sub("", path.stem).strip() or path.stem
    return Chapter(title, blocks)


def load_novel_folder(folder: Path | str) -> tuple[list[Chapter], Path | None]:
    """Read all ``.md``/``.txt`` chapter files (natural order) and find a ``cover.*`` image."""
    folder = Path(folder)
    files = sorted((p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in (".md", ".txt")),
                   key=lambda p: natural_key(p.name))
    chapters = [parse_chapter(p) for p in files]
    cover = next((p for p in sorted(folder.iterdir())
                  if p.is_file() and p.stem.lower() == "cover" and p.suffix.lower() in IMAGE_EXTENSIONS), None)
    return chapters, cover
