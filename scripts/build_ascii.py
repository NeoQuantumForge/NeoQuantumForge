"""build_ascii.py -- generates assets/ascii.svg from the configured photo."""
from __future__ import annotations

from pathlib import Path

from ascii_engine import build_ascii_svg
from config import Config
from utils import get_logger

log = get_logger("build_ascii")


def run(config: Config) -> Path:
    photo_path = config.photo.resolve()
    svg = build_ascii_svg(
        photo_path=photo_path,
        cfg=config.ascii,
        theme=config.theme,
        width=config.layout.ascii_panel_width,
        height=config.layout.terminal_height + config.layout.heatmap_height // 2,
    )
    out_path = config.assets_dir / "ascii.svg"
    out_path.write_text(svg, encoding="utf-8")
    log.info("Wrote %s", out_path)
    return out_path


if __name__ == "__main__":
    from config import load_config
    run(load_config())
