"""
ascii_engine.py
----------------
Converts a photo into a monochrome ASCII-art SVG portrait that draws
itself line-by-line (top to bottom) using SMIL animation.

Pipeline:
  1. Load image, convert to grayscale
  2. Optionally remove background (simple luminance/edge based matting --
     no heavy ML dependency, keeps the project install-light)
  3. Adaptive local-contrast enhancement
  4. Gamma + brightness adjustment
  5. Downsample to a character grid sized by `columns`
  6. Map each cell's brightness to a character in the configured charset
  7. Emit an SVG <text> line per row, each with a staggered fade/opacity
     reveal animation so the portrait appears to draw itself top-to-bottom
"""

from __future__ import annotations

from pathlib import Path
from typing import List

from PIL import Image, ImageEnhance, ImageFilter, ImageOps

from config import AsciiConfig, ThemeConfig
from svg_engine import SVGDocument, animate, group, rect, text
from utils import get_logger

log = get_logger("ascii_engine")


def _remove_background(img: Image.Image) -> Image.Image:
    """Lightweight background suppression: builds a soft mask from edge
    density + center-weighted luminance so the subject (usually centered,
    higher local contrast) is favored over flat background regions. This
    avoids pulling in heavy segmentation models for a text-art pipeline
    where perfect masking isn't required."""
    gray = img.convert("L")
    edges = gray.filter(ImageFilter.FIND_EDGES)
    edges = edges.filter(ImageFilter.GaussianBlur(radius=3))

    w, h = gray.size
    center_weight = Image.new("L", (w, h), 0)
    cx, cy = w / 2, h / 2
    max_dist = (cx ** 2 + cy ** 2) ** 0.5
    px = center_weight.load()
    for y in range(h):
        for x in range(w):
            dist = ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5
            px[x, y] = int(255 * (1 - min(dist / max_dist, 1.0)) ** 0.6)

    mask = Image.blend(edges, center_weight, alpha=0.55)
    mask = mask.point(lambda v: 255 if v > 40 else v)
    mask = mask.filter(ImageFilter.GaussianBlur(radius=2))

    background = Image.new("L", gray.size, 0)
    composited = Image.composite(gray, background, mask)
    return composited


def _adaptive_contrast(img: Image.Image) -> Image.Image:
    """CLAHE-like local contrast boost without external deps: unsharp mask
    plus a global autocontrast pass."""
    img = ImageOps.autocontrast(img, cutoff=1)
    img = img.filter(ImageFilter.UnsharpMask(radius=2, percent=120, threshold=2))
    return img


def _apply_gamma(img: Image.Image, gamma: float) -> Image.Image:
    if gamma == 1.0:
        return img
    inv_gamma = 1.0 / max(gamma, 0.01)
    lut = [min(255, int((i / 255.0) ** inv_gamma * 255)) for i in range(256)]
    return img.point(lut)


def load_and_process_image(photo_path: Path, cfg: AsciiConfig) -> Image.Image:
    if not photo_path.exists():
        raise FileNotFoundError(
            f"Photo not found at {photo_path}. Set 'photo.path' in profile.json "
            "and add the image to the assets/ directory."
        )
    img = Image.open(photo_path).convert("RGB")
    gray = img.convert("L")

    if cfg.remove_background:
        gray = _remove_background(img)

    gray = _adaptive_contrast(gray)
    gray = ImageEnhance.Contrast(gray).enhance(cfg.contrast)
    gray = ImageEnhance.Brightness(gray).enhance(cfg.brightness)
    gray = _apply_gamma(gray, cfg.gamma)
    return gray


def image_to_ascii_grid(img: Image.Image, cfg: AsciiConfig) -> List[str]:
    """Downsamples the image to a character grid. Character cells are
    roughly 2x taller than wide visually, so we compress row count to
    keep portrait proportions correct."""
    charset = cfg.charset
    columns = max(cfg.columns, 10)

    aspect = img.height / img.width
    # monospace glyphs are ~0.55x as wide as tall; compensate row count
    rows = max(int(columns * aspect * 0.55), 10)

    small = img.resize((columns, rows), Image.LANCZOS)
    pixels = small.load()

    n_chars = len(charset)
    lines: List[str] = []
    for y in range(rows):
        row_chars = []
        for x in range(columns):
            brightness = pixels[x, y] / 255.0
            # charset is ordered dense ("@") -> sparse (" "), and a darker
            # pixel should render as a denser character, so a low brightness
            # value must map to a low index.
            idx = int(brightness * (n_chars - 1))
            idx = max(0, min(n_chars - 1, idx))
            row_chars.append(charset[idx])
        lines.append("".join(row_chars))
    return lines


def render_ascii_svg(lines: List[str], cfg: AsciiConfig, theme: ThemeConfig,
                      width: int, height: int) -> str:
    doc = SVGDocument(width, height, font_family="monospace", background=theme.panel_background)

    doc.add(rect(0, 0, width, height, fill="none", stroke=theme.border, stroke_width=1, rx=10))

    portrait_group = group(id="ascii-portrait")
    doc.add(portrait_group)

    top_pad = 16
    left_pad = 14
    line_height = cfg.line_height
    font_size = cfg.font_size
    reveal_step = cfg.reveal_speed_ms / 1000.0

    for i, line in enumerate(lines):
        y = top_pad + i * line_height
        if y > height - 8:
            break
        node = text(left_pad, y, line, fill=theme.text_primary, font_size=font_size,
                     font_family="monospace")
        node.attrs["opacity"] = 0
        delay = i * reveal_step
        node.add(animate("opacity", "0;1", "0.35s", begin=f"{delay:.3f}s"))
        portrait_group.add(node)

    caption = text(left_pad, height - 10, "// ascii_engine.render()", fill=theme.text_secondary,
                    font_size=9, font_family="monospace")
    caption.attrs["opacity"] = 0
    total_delay = len(lines) * reveal_step
    caption.add(animate("opacity", "0;1", "0.6s", begin=f"{total_delay:.3f}s"))
    doc.add(caption)

    return doc.render()


def build_ascii_svg(photo_path: Path, cfg: AsciiConfig, theme: ThemeConfig,
                     width: int, height: int) -> str:
    log.info("Processing portrait: %s", photo_path)
    img = load_and_process_image(photo_path, cfg)
    grid = image_to_ascii_grid(img, cfg)
    svg = render_ascii_svg(grid, cfg, theme, width, height)
    log.info("ASCII portrait generated: %d cols x %d rows", cfg.columns, len(grid))
    return svg
