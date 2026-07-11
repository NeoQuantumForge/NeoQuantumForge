"""build_dashboard.py -- generates assets/dashboard.svg from live GitHub data."""
from __future__ import annotations

from pathlib import Path
from typing import List

from config import Config
from dashboard_engine import build_dashboard_svg
from github import GitHubClient, Profile, Repository
from utils import get_logger

log = get_logger("build_dashboard")


def run(config: Config, client: GitHubClient, profile: Profile, repos: List[Repository],
        pinned_names: List[str]) -> Path:
    svg = build_dashboard_svg(
        profile=profile,
        repos=repos,
        pinned_names=pinned_names,
        identity=config.identity,
        dash_cfg=config.dashboard,
        theme=config.theme,
        width=config.layout.dashboard_panel_width,
        height=config.layout.terminal_height + config.layout.heatmap_height // 2,
        fade_duration_ms=config.animation.fade_duration_ms,
    )
    out_path = config.assets_dir / "dashboard.svg"
    out_path.write_text(svg, encoding="utf-8")
    log.info("Wrote %s", out_path)
    return out_path


if __name__ == "__main__":
    from config import load_config
    from fetch_profile import fetch_profile
    from fetch_repositories import fetch_repositories
    from fetch_activity import fetch_pinned_repositories
    from utils import JSONCache

    cfg = load_config()
    gh_client = GitHubClient(cfg.github, JSONCache(cfg.cache_dir))
    p = fetch_profile(gh_client)
    r = fetch_repositories(gh_client)
    pinned = fetch_pinned_repositories(gh_client)
    run(cfg, gh_client, p, r, pinned)
