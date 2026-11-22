from conftest import FIXTURES
from epub.novel import Heading, Image, Paragraph, Run, SceneBreak
from epub.textinput import load_novel_folder, parse_inline


def test_parse_inline():
    runs = parse_inline("a *b* **c** ***d*** _e_ {漢字|かんじ} |東京《とうきょう》 魔法《まほう》 snake_case")
    assert Run("b", em=True) in runs
    assert Run("c", strong=True) in runs
    assert Run("d", em=True, strong=True) in runs
    assert Run("e", em=True) in runs
    assert Run("漢字", ruby="かんじ") in runs
    assert Run("東京", ruby="とうきょう") in runs
    assert Run("魔法", ruby="まほう") in runs
    assert runs[-1] == Run(" snake_case")


def test_load_fixture_folder():
    chapters, cover = load_novel_folder(FIXTURES / "novel")
    assert cover is None
    assert [c.title for c in chapters] == ["Prolog", "Kapitel_Eins"]
    pro = chapters[0].blocks
    assert isinstance(pro[0], Image) and pro[0].full_page and pro[0].alt == "Farbillustration"
    assert isinstance(pro[1], Paragraph)
    assert "Diese Zeile gehört noch zum ersten Absatz." in "".join(r.text for r in pro[1].runs)
    assert any(isinstance(b, SceneBreak) for b in pro)
    img = next(b for b in pro if isinstance(b, Image) and not b.full_page)
    assert img.caption == "Eine Bildunterschrift"
    assert Heading(2, "Zwischenüberschrift") in pro
    txt = chapters[1].blocks
    assert len([b for b in txt if isinstance(b, Paragraph)]) == 3
    assert isinstance(txt[2], SceneBreak)
