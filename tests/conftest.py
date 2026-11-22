import json
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest
from PIL import Image as PILImage

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _epubcheck_jar():
    try:
        from epubcheck.const import EPUBCHECK
    except ImportError:
        return os.environ.get("EPUBCHECK_JAR")
    return EPUBCHECK


@pytest.fixture(scope="session")
def epubcheck():
    """Return a function that validates an EPUB with epubcheck and asserts no errors/warnings."""
    jar = _epubcheck_jar()
    if not jar or not shutil.which("java"):
        if os.environ.get("EPUBCHECK_REQUIRED"):
            pytest.fail("epubcheck (java + jar) required but not available")
        pytest.skip("epubcheck/java not available")

    def check(path: Path):
        report = path.with_suffix(".epubcheck.json")
        proc = subprocess.run(["java", "-jar", jar, str(path), "--json", str(report)],
                              capture_output=True, text=True)
        data = json.loads(report.read_text(encoding="utf-8"))
        problems = [f"{m['severity']} {m['ID']}: {m['message']} @ "
                    f"{[l.get('path') for l in m.get('locations', [])]}"
                    for m in data["messages"] if m["severity"] in ("FATAL", "ERROR", "WARNING")]
        assert not problems and proc.returncode == 0, "\n".join(problems) or proc.stdout + proc.stderr
        return data

    return check


def make_image(path: Path, size=(60, 90), color=(200, 30, 30), mode="RGB"):
    path.parent.mkdir(parents=True, exist_ok=True)
    fmt = {".jpg": "JPEG", ".jpeg": "JPEG", ".png": "PNG", ".webp": "WEBP", ".gif": "GIF",
           ".bmp": "BMP", ".tif": "TIFF"}[path.suffix.lower()]
    PILImage.new(mode, size, color).save(path, fmt)
    return path


@pytest.fixture
def image_factory():
    return make_image


def read_zip(path: Path) -> dict[str, bytes]:
    with zipfile.ZipFile(path) as zf:
        return {n: zf.read(n) for n in zf.namelist()}
