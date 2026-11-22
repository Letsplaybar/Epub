"""Build EPUB 3 files from manga page images or light-novel chapters."""

__version__ = "1.0.0"

from .common import Meta  # noqa: E402
from .manga import build_manga  # noqa: E402
from .novel import Chapter, Heading, Image, Paragraph, Run, SceneBreak, build_novel  # noqa: E402

__all__ = ["Meta", "build_manga", "build_novel", "Chapter", "Heading", "Paragraph", "Run", "Image",
           "SceneBreak", "__version__"]
