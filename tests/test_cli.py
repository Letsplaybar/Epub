import os
import shutil
import subprocess
import sys

from conftest import FIXTURES, ROOT, make_image, read_zip


def run_cli(cwd, *args, module=False):
    cmd = [sys.executable, "-m", "epub"] if module else [sys.executable, str(ROOT / "Epub.py")]
    env = dict(os.environ, PYTHONPATH=str(ROOT))
    return subprocess.run(cmd + list(args), cwd=cwd, capture_output=True, text=True, env=env)


LEGACY_ARGS = ["-l", "en", "-t", "My Manga Vol. 5", "-a", "Some Author", "-g", "Action", "-g", "Comedy",
               "-p", "Publisher", "-s", "My Manga", "-n", "5", "-D", "A description",
               "-i", "002.xhtml", "-m", "Chapter 1", "-i", "004.xhtml", "-m", "Chapter 2"]


def _legacy_folder(tmp_path, ext="png", n=6):
    folder = tmp_path / "My Manga Vol. 5"
    for i in range(n):
        make_image(folder / f"{i:03d}.{ext}", color=(i * 30, 0, 0))
    return folder


def test_legacy_cli_unchanged_usage(tmp_path, epubcheck):
    folder = _legacy_folder(tmp_path)
    before = sorted(p.name for p in folder.iterdir())
    proc = run_cli(tmp_path, *LEGACY_ARGS)
    assert proc.returncode == 0, proc.stderr
    out = tmp_path / "My Manga Vol. 5.epub"
    epubcheck(out)
    assert sorted(p.name for p in folder.iterdir()) == before  # source folder untouched
    files = read_zip(out)
    opf = files["OEBPS/content.opf"].decode()
    for snippet in ("<dc:title id=\"title\">My Manga Vol. 5</dc:title>", "<dc:language>en</dc:language>",
                    ">Some Author</dc:creator>", "<dc:subject>Comedy</dc:subject>",
                    "<dc:publisher>Publisher</dc:publisher>", "A description",
                    'belongs-to-collection" id="series">My Manga<', 'group-position">5<',
                    'page-progression-direction="rtl"'):
        assert snippet in opf
    nav = files["OEBPS/nav.xhtml"].decode()
    assert 'href="cover.xhtml">Cover' in nav
    assert 'href="p0003.xhtml">Chapter 1' in nav and 'href="p0005.xhtml">Chapter 2' in nav


def test_legacy_cli_jpg_and_lang_alias(tmp_path, epubcheck):
    folder = _legacy_folder(tmp_path, ext="jpg", n=3)
    make_image(folder / "stray.png")  # ignored with --jpg like the old script
    proc = run_cli(tmp_path, "-t", folder.name, "--jpg", "-l", "jp", module=True)
    assert proc.returncode == 0, proc.stderr
    out = tmp_path / f"{folder.name}.epub"
    epubcheck(out)
    opf = read_zip(out)["OEBPS/content.opf"].decode()
    assert "<dc:language>ja</dc:language>" in opf
    assert opf.count('media-type="image/jpeg"') == 3 and "image/png" not in opf


def test_legacy_cli_accepts_folder_processed_by_old_script(tmp_path, epubcheck):
    folder = tmp_path / "Old"
    for i in range(3):
        make_image(folder / "images" / f"{i:03d}.png")
    shutil.copy(folder / "images" / "000.png", folder / "Cover.png")
    (folder / "000.xhtml").write_text("<html/>")
    proc = run_cli(tmp_path, "-t", "Old")
    assert proc.returncode == 0, proc.stderr
    epubcheck(tmp_path / "Old.epub")
    names = read_zip(tmp_path / "Old.epub")
    assert len([n for n in names if n.startswith("OEBPS/images/")]) == 3


def test_legacy_cli_marker_mismatch(tmp_path):
    proc = run_cli(tmp_path, "-t", "X", "-i", "001.xhtml")
    assert proc.returncode == 255
    assert "same amount of marker-index and marker-title" in proc.stdout


def test_cli_novel(tmp_path, epubcheck):
    src = tmp_path / "Meine Novel"
    shutil.copytree(FIXTURES / "novel", src)
    make_image(src / "full.jpg", size=(80, 120))
    make_image(src / "illu.png", size=(40, 30))
    make_image(src / "cover.jpg", size=(100, 150))
    proc = run_cli(tmp_path, "--novel", "-t", "Meine Novel", "-a", "Autor", "-l", "de", "-s", "Reihe", "-n", "2")
    assert proc.returncode == 0, proc.stderr
    out = tmp_path / "Meine Novel.epub"
    epubcheck(out)
    files = read_zip(out)
    assert "OEBPS/cover.xhtml" in files and "OEBPS/text/ch002.xhtml" in files
    assert "<ruby>東京" in files["OEBPS/text/ch002.xhtml"].decode()


def test_cli_novel_vertical_with_output(tmp_path, epubcheck):
    src = tmp_path / "src"
    src.mkdir()
    (src / "1.txt").write_text("吾輩《わがはい》は猫である。\n名前はまだ無い。\n", encoding="utf-8")
    proc = run_cli(tmp_path, "--novel", "--vertical", "-t", "猫", "-l", "jp", "--input", "src",
                   "-o", "out/neko.epub")
    assert proc.returncode == 0, proc.stderr
    epubcheck(tmp_path / "out" / "neko.epub")
