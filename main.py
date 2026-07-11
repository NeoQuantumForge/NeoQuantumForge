#!/usr/bin/env python3
"""
main.py
-------
Single entry point for NeoQuantumForge. Running this script:

  1. Loads profile.json
  2. Fetches (or reuses cached) GitHub data: profile, repositories,
     pinned repos, languages, contribution calendar
  3. Regenerates every SVG asset (boot, ascii, dashboard, terminal, heatmap)
  4. Regenerates README.md

Usage:
    python main.py                 # full run, using cache where fresh
    python main.py --no-cache      # force-refresh all GitHub data
    python main.py --skip-ascii    # skip the (slower) portrait rebuild

This is also exactly what .github/workflows/update-profile.yml runs daily.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "scripts"))

from config import load_config  # noqa: E402
from github import GitHubClient  # noqa: E402
from utils import JSONCache, get_logger  # noqa: E402

import build_ascii  # noqa: E402
import build_dashboard  # noqa: E402
import build_heatmap  # noqa: E402
import build_terminal  # noqa: E402
import build_readme  # noqa: E402
import fetch_activity  # noqa: E402
import fetch_contributions  # noqa: E402
import fetch_profile  # noqa: E402
import fetch_repositories  # noqa: E402
import fetch_languages  # noqa: E402

log = get_logger("main")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the NeoQuantumForge animated profile.")
    parser.add_argument("--no-cache", action="store_true", help="Force-refresh all GitHub data.")
    parser.add_argument("--skip-ascii", action="store_true", help="Skip ASCII portrait rebuild.")
    parser.add_argument("--config", type=str, default=None, help="Path to profile.json.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    start = time.time()

    config_path = Path(args.config) if args.config else None
    config = load_config(config_path)
    use_cache = not args.no_cache

    log.info("=== NeoQuantumForge build starting (user=%s) ===", config.github.username)

    cache = JSONCache(config.cache_dir, ttl_seconds=6 * 3600)
    client = GitHubClient(config.github, cache)

    # -- fetch phase (parallelizable network calls are independent) -----
    # If GitHub is unreachable (no network, no token, offline dev, first-ever
    # run with an empty cache) the build still succeeds using clearly-marked
    # demo data instead of crashing -- this keeps `python main.py` usable
    # immediately after cloning, before any secrets/config are set up.
    try:
        profile = fetch_profile.fetch_profile(client, use_cache=use_cache)
        repos = fetch_repositories.fetch_repositories(client, use_cache=use_cache)
        pinned = fetch_activity.fetch_pinned_repositories(client, use_cache=use_cache)
        calendar = fetch_contributions.fetch_contributions(client, use_cache=use_cache)
        top_langs = fetch_languages.top_languages(client, repos, config.dashboard.max_top_languages)
    except Exception as exc:  # noqa: BLE001
        log.error("Live GitHub fetch failed (%s). Falling back to demo data.", exc)
        from demo_data import demo_profile, demo_repos, demo_calendar
        profile = demo_profile(config)
        repos = demo_repos()
        pinned = [r.name for r in repos[:3]]
        calendar = demo_calendar()
        top_langs = fetch_languages.top_languages(client, repos, config.dashboard.max_top_languages)

    log.info(
        "Fetched profile for %s: %d repos, %d followers, %d pinned",
        profile.login, len(repos), profile.followers, len(pinned),
    )

    # -- build phase ------------------------------------------------------
    if not args.skip_ascii:
        try:
            build_ascii.run(config)
        except FileNotFoundError as exc:
            log.warning("Skipping ASCII portrait: %s", exc)
    else:
        log.info("Skipping ASCII portrait (--skip-ascii)")

    build_dashboard.run(config, client, profile, repos, pinned)
    build_terminal.run(config, repos, pinned, top_langs)
    build_heatmap.run(config, calendar)
    build_readme.run(config)

    elapsed = time.time() - start
    log.info("=== Build complete in %.2fs ===", elapsed)
    if elapsed > 10:
        log.warning("Build exceeded the 10s performance target (%.2fs).", elapsed)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
