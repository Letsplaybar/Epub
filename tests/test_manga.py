import re
import zipfile

import pytest

from conftest import read_zip
from epub import Meta, build_manga


def _pages(tmp_path, image_factory, exts=("png", "jpg", "webp", "png", "jpg"), sizes=None):
    out = []
    for i, ext in enumerate(exts):
        size = sizes[i] if sizes else (60 + i, 90)
        out.append(image_factory(tmp_path / "src" / f"{i:03d}.{ext}", size=size, color=(i * 40, 80, 160)))
    return out


def test_manga_mixed_formats_rtl_valid(tmp_path, image_factory, epubcheck):
    images = _pages(tmp_path, image_factory)
    meta = Meta("Manga <Test> & Co", author=["Autorin", "Zeichner"], language="ja",
                publisher="Verlag", description="Beschreibung", genres=["Action", "Comedy"],
                series="Reihe", series_index=3)
    out = build_manga(images, tmp_path / "out" / "manga.epub", meta,
                      markers=[(2, "Kapitel 1"), (4, "Kapitel 2")], rtl=True)
    epubcheck(out)

    files = read_zip(out)
    opf = files["OEBPS/content.opf"].decode()
    assert 'page-progression-direction="rtl"' in opf
    assert '<meta property="rendition:layout">pre-paginated</meta>' in opf
    assert '<meta property="rendition:spread">landscape</meta>' in opf
    assert 'properties="cover-image"' in opf
    assert '<meta property="belongs-to-collection" id="series">Reihe</meta>' in opf
    assert '<meta refines="#series" property="group-position">3</meta>' in opf
    assert '<meta name="calibre:series" content="Reihe" />' in opf
    assert '<meta name="calibre:series_index" content="3" />' in opf
    assert 'media-type="image/webp"' in opf and 'media-type="image/jpeg"' in opf
    # one XHTML page per image, each wrapping the image in SVG with its own viewport
    pages = sorted(n for n in files if re.match(r"OEBPS/(cover|p\d+)\.xhtml$", n))
    assert len(pages) == len(images)
    p2 = files["OEBPS/p0002.xhtml"].decode()
    assert 'content="width=61, height=90"' in p2 and "<svg" in p2 and 'viewBox="0 0 61 90"' in p2
    # spreads: cover centred, then right/left alternating for RTL
    spine = re.findall(r'<itemref idref="(\w+)"(?: properties="([^"]+)")?', opf)
    assert [p for _, p in spine] == ["rendition:page-spread-center", "page-spread-right",
                                    "page-spread-left", "page-spread-right", "page-spread-left"]
    nav = files["OEBPS/nav.xhtml"].decode()
    assert nav.index("Cover") < nav.index("Kapitel 1") < nav.index("Kapitel 2")
    assert 'href="p0003.xhtml">Kapitel 1' in nav
    assert "Manga &lt;Test&gt; &amp; Co" in opf


def test_manga_ltr_and_ocf_container(tmp_path, image_factory, epubcheck):
    images = _pages(tmp_path, image_factory, exts=("jpg", "jpg", "jpg"))
    out = build_manga(images, tmp_path / "ltr.epub", Meta("LTR"), rtl=False, spread="both")
    epubcheck(out)
    with zipfile.ZipFile(out) as zf:
        first = zf.infolist()[0]
        assert first.filename == "mimetype" and first.compress_type == zipfile.ZIP_STORED
        assert zf.read("mimetype") == b"application/epub+zip"
        opf = zf.read("OEBPS/content.opf").decode()
    assert 'page-progression-direction="ltr"' in opf
    assert "page-spread-left" in opf.split("page-spread-center")[1].split("page-spread-right")[0]
    assert "rendition:spread\">both" in opf


def test_manga_converts_other_formats_and_detects_by_content(tmp_path, image_factory, epubcheck):
    bmp = image_factory(tmp_path / "a.bmp")
    fake_jpg = image_factory(tmp_path / "b.png")  # real PNG...
    renamed = fake_jpg.rename(tmp_path / "b.jpg")  # ...with a misleading extension
    out = build_manga([bmp, renamed], tmp_path / "conv.epub", Meta("Conv"))
    epubcheck(out)
    names = read_zip(out)
    assert "OEBPS/images/cover.jpg" in names  # RGB BMP -> JPEG
    assert "OEBPS/images/p0002.png" in names


def test_manga_does_not_touch_cwd(tmp_path, image_factory, monkeypatch):
    images = _pages(tmp_path, image_factory, exts=("png",))
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    monkeypatch.chdir(cwd)
    build_manga(images, tmp_path / "x.epub", Meta("X"))
    assert list(cwd.iterdir()) == []
    assert (tmp_path / "x.epub").stat().st_mode & 0o044  # not left at mkstemp's 0600
    assert sorted(p.name for p in (tmp_path / "src").iterdir()) == ["000.png"]


def test_manga_requires_images(tmp_path):
    with pytest.raises(ValueError):
        build_manga([], tmp_path / "x.epub", Meta("X"))
