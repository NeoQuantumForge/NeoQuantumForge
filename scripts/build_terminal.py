"""build_terminal.py -- generates assets/terminal.svg."""
from __future__ import annotations

from pathlib import Path
from typing import List

from config import Config
from github import Repository
from terminal_engine import build_terminal_svg
from utils import get_logger

log = get_logger("build_terminal")


def run(config: Config, repos: List[Repository], pinned_names: List[str],
        top_languages: List[str]) -> Path:
    svg = build_terminal_svg(
        term_cfg=config.terminal,
        identity=config.identity,
        repos=repos,
        pinned_names=pinned_names,
        top_languages=top_languages,
        theme=config.theme,
        width=config.layout.width,
        height=config.layout.terminal_height,
    )
    out_path = config.assets_dir / "terminal.svg"
    out_path.write_text(svg, encoding="utf-8")
    log.info("Wrote %s", out_path)
    return out_path


if __name__ == "__main__":
    from config import load_config
    from fetch_repositories import fetch_repositories
    from fetch_activity import fetch_pinned_repositories
    from fetch_languages import top_languages as get_top_languages
    from github import GitHubClient
    from utils import JSONCache

    cfg = load_config()
    gh_client = GitHubClient(cfg.github, JSONCache(cfg.cache_dir))
    r = fetch_repositories(gh_client)
    pinned = fetch_pinned_repositories(gh_client)
    langs = get_top_languages(gh_client, r, cfg.dashboard.max_top_languages)
    run(cfg, r, pinned, langs)
