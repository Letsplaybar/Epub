import re

import pytest

from conftest import read_zip
from epub import Chapter, Heading, Image, Meta, Paragraph, Run, SceneBreak, build_novel


def _chapters(tmp_path, image_factory):
    full = image_factory(tmp_path / "full.jpg", size=(80, 120))
    illu = image_factory(tmp_path / "illu.png", size=(40, 30), mode="RGBA", color=(0, 0, 255, 128))
    return [
        Chapter("Prolog", [
            Image(full, alt="Farbseite", full_page=True),
            Paragraph("Erster Absatz mit <Sonderzeichen> & Steuerzeichen\x0c."),
            Paragraph([Run("Kursiv", em=True), " und ", Run("fett", strong=True), " und ",
                       Run("漢字", ruby="かんじ"), "."]),
            SceneBreak(),
            Image(illu, alt="Illustration", caption="Bildunterschrift"),
            Heading(2, "Zwischentitel"),
            Paragraph("Zentriert", align="center"),
            Image(full, alt="Nochmal", full_page=True),
            Paragraph("Nach dem ganzseitigen Bild."),
        ]),
        Chapter("Kapitel 1", [Paragraph("Text.")]),
        Chapter("Nur Titel", []),
    ]


def test_novel_horizontal_valid(tmp_path, image_factory, epubcheck):
    cover = image_factory(tmp_path / "cover.jpg", size=(100, 150))
    meta = Meta("Light Novel", author="Autor", language="de", series="LN-Reihe", series_index="1.5")
    out = build_novel(_chapters(tmp_path, image_factory), tmp_path / "ln.epub", meta, cover=cover)
    epubcheck(out)
    files = read_zip(out)
    opf = files["OEBPS/content.opf"].decode()
    assert "rendition:layout" not in opf
    assert 'page-progression-direction="ltr"' in opf
    assert 'href="images/cover.jpg" media-type="image/jpeg" properties="cover-image"' in opf
    assert '<meta refines="#series" property="group-position">1.5</meta>' in opf
    # full_page image reused -> stored once
    assert sum(1 for n in files if n.startswith("OEBPS/images/")) == 3
    spine = re.findall(r'<itemref idref="([^"]+)"', opf)
    docs = [re.search(rf'id="{i}" href="([^"]+)"', opf).group(1) for i in spine]
    assert docs == ["cover.xhtml", "text/ch001_img01.xhtml", "text/ch001.xhtml",
                    "text/ch001_img02.xhtml", "text/ch001_2.xhtml", "text/ch002.xhtml",
                    "text/ch003.xhtml"]
    ch1 = files["OEBPS/text/ch001.xhtml"].decode()
    assert '<section class="chapter" epub:type="chapter" role="doc-chapter">' in ch1
    assert "<h1>Prolog</h1>" in ch1
    assert "&lt;Sonderzeichen&gt; &amp; Steuerzeichen." in ch1
    # inline markup must not get extra whitespace
    assert ("<p><em>Kursiv</em> und <strong>fett</strong> und "
            "<ruby>漢字<rp>(</rp><rt>かんじ</rt><rp>)</rp></ruby>.</p>") in ch1
    assert '<hr class="scene-break" />' in ch1
    assert '<figure class="illustration">' in ch1 and "<figcaption>Bildunterschrift</figcaption>" in ch1
    assert 'src="../images/' in ch1 and 'href="../css/style.css"' in ch1
    assert '<p class="center">Zentriert</p>' in ch1
    assert "<h1>" not in files["OEBPS/text/ch001_2.xhtml"].decode()
    css = files["OEBPS/css/style.css"].decode()
    for rule in ("text-indent: 1em", "hyphens: auto", "page-break-before: always", "max-width: 100%"):
        assert rule in css
    nav = files["OEBPS/nav.xhtml"].decode()
    assert 'href="text/ch001_img01.xhtml">Prolog' in nav and 'href="text/ch003.xhtml">Nur Titel' in nav
    assert 'epub:type="cover" href="cover.xhtml"' in nav


def test_novel_vertical_valid(tmp_path, image_factory, epubcheck):
    meta = Meta("縦書き", author="作者", language="ja")
    out = build_novel(_chapters(tmp_path, image_factory), tmp_path / "v.epub", meta, vertical=True)
    epubcheck(out)
    files = read_zip(out)
    opf = files["OEBPS/content.opf"].decode()
    assert 'page-progression-direction="rtl"' in opf
    assert '<meta name="primary-writing-mode" content="vertical-rl" />' in opf
    assert "writing-mode: vertical-rl" in files["OEBPS/css/vertical.css"].decode()
    assert 'href="../css/vertical.css"' in files["OEBPS/text/ch001.xhtml"].decode()
    assert 'xml:lang="ja"' in files["OEBPS/text/ch002.xhtml"].decode()


def test_novel_without_cover_or_images(tmp_path, epubcheck):
    out = build_novel([Chapter("Eins", [Paragraph("a")]), Chapter("Zwei", [Paragraph("b")])],
                      tmp_path / "plain.epub", Meta("Plain", language="en"))
    epubcheck(out)
    assert "cover-image" not in read_zip(out)["OEBPS/content.opf"].decode()


def test_novel_rejects_empty(tmp_path):
    with pytest.raises(ValueError):
        build_novel([], tmp_path / "x.epub", Meta("X"))
