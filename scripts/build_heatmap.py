"""build_heatmap.py -- generates assets/heatmap.svg from the contribution calendar."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from config import Config
from heatmap_engine import build_heatmap_svg
from utils import get_logger

log = get_logger("build_heatmap")


def run(config: Config, calendar: Dict[str, Any]) -> Path:
    svg = build_heatmap_svg(
        calendar=calendar,
        theme=config.theme,
        width=config.layout.width,
        height=config.layout.heatmap_height,
        reveal_speed_ms=config.animation.heatmap_reveal_speed_ms,
    )
    out_path = config.assets_dir / "heatmap.svg"
    out_path.write_text(svg, encoding="utf-8")
    log.info("Wrote %s", out_path)
    return out_path


if __name__ == "__main__":
    from config import load_config
    from fetch_contributions import fetch_contributions
    from github import GitHubClient
    from utils import JSONCache

    cfg = load_config()
    gh_client = GitHubClient(cfg.github, JSONCache(cfg.cache_dir))
    cal = fetch_contributions(gh_client)
    run(cfg, cal)
