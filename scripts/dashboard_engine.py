"""
dashboard_engine.py
--------------------
Renders dashboard.svg: a panel of live GitHub statistics (followers,
stars, repo count, top languages, pinned/featured projects, etc.)
using the shared svg_engine primitives. Rows fade in with a staggered
delay to match the boot-sequence feel described in the project spec.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from config import DashboardConfig, IdentityConfig, ThemeConfig
from github import Profile, Repository
from svg_engine import SVGDocument, animate, group, line, rect, text
from utils import format_count, get_logger, truncate, utc_now_iso

log = get_logger("dashboard_engine")


@dataclass
class DashboardRow:
    label: str
    value: str


def _total_stars(repos: List[Repository]) -> int:
    return sum(r.stars for r in repos if not r.is_fork)


def _top_languages(repos: List[Repository], max_n: int) -> List[str]:
    totals: Dict[str, int] = {}
    for r in repos:
        if r.language and not r.is_fork:
            totals[r.language] = totals.get(r.language, 0) + 1
    ranked = sorted(totals.items(), key=lambda kv: kv[1], reverse=True)
    return [lang for lang, _ in ranked[:max_n]]


def _latest_repository(repos: List[Repository]) -> Optional[Repository]:
    non_forks = [r for r in repos if not r.is_fork and not r.archived]
    pool = non_forks or repos
    if not pool:
        return None
    return max(pool, key=lambda r: r.updated_at or "")


def build_dashboard_rows(profile: Profile, repos: List[Repository], pinned_names: List[str],
                          identity: IdentityConfig, dash_cfg: DashboardConfig) -> List[DashboardRow]:
    top_langs = _top_languages(repos, dash_cfg.max_top_languages)
    latest = _latest_repository(repos)
    pinned = pinned_names or dash_cfg.pinned_repositories
    featured = dash_cfg.featured_repositories or pinned[:3]

    field_map = {
        "name": DashboardRow("name", profile.name or identity.display_name),
        "role": DashboardRow("role", identity.role),
        "followers": DashboardRow("followers", format_count(profile.followers)),
        "stars": DashboardRow("total stars", format_count(_total_stars(repos))),
        "public_repos": DashboardRow("public repos", format_count(profile.public_repos)),
        "pinned_projects": DashboardRow("pinned", ", ".join(pinned) if pinned else "\u2014"),
        "featured_projects": DashboardRow("featured", ", ".join(featured) if featured else "\u2014"),
        "top_languages": DashboardRow("top languages", ", ".join(top_langs) if top_langs else "\u2014"),
        "latest_repository": DashboardRow("latest repo", latest.name if latest else "\u2014"),
        "current_focus": DashboardRow("current focus", identity.current_focus or "\u2014"),
        "website": DashboardRow("website", identity.website or "\u2014"),
        "location": DashboardRow("location", profile.location or identity.location or "\u2014"),
        "last_updated": DashboardRow("last updated", utc_now_iso()),
    }

    rows: List[DashboardRow] = []
    for key in dash_cfg.widgets:
        if key in field_map:
            rows.append(field_map[key])
    return rows


def render_dashboard_svg(rows: List[DashboardRow], theme: ThemeConfig, width: int,
                          height: int, fade_duration_s: float = 0.5) -> str:
    doc = SVGDocument(width, height, font_family=theme.font_family, background=theme.panel_background)
    doc.add(rect(0, 0, width, height, fill="none", stroke=theme.border, stroke_width=1, rx=10))

    header = group(id="dashboard-header")
    header_text = text(18, 26, "LIVE DASHBOARD", fill=theme.accent, font_size=12,
                        font_weight="bold", letter_spacing=1.5)
    header.add(header_text)
    doc.add(header)
    doc.add(line(18, 36, width - 18, 36, stroke=theme.border, stroke_width=1))

    row_height = max((height - 56) / max(len(rows), 1), 18)
    row_height = min(row_height, 26)

    label_x = 18
    value_x = int(width * 0.42)
    start_y = 58

    row_group = group(id="dashboard-rows")
    doc.add(row_group)

    for i, row in enumerate(rows):
        y = start_y + i * row_height
        if y > height - 10:
            break
        delay = 0.15 + i * 0.08

        r_group = group(opacity=0)
        r_group.add(animate("opacity", "0;1", f"{fade_duration_s}s", begin=f"{delay:.2f}s"))

        label_node = text(label_x, y, row.label.upper(), fill=theme.text_secondary,
                           font_size=10.5, letter_spacing=0.5, font_family=theme.font_family)
        value_node = text(value_x, y, truncate(row.value, 34), fill=theme.text_primary,
                           font_size=11.5, font_family=theme.font_family)

        r_group.add(label_node)
        r_group.add(value_node)
        row_group.add(r_group)

    return doc.render()


def build_dashboard_svg(profile: Profile, repos: List[Repository], pinned_names: List[str],
                         identity: IdentityConfig, dash_cfg: DashboardConfig,
                         theme: ThemeConfig, width: int, height: int,
                         fade_duration_ms: int = 500) -> str:
    rows = build_dashboard_rows(profile, repos, pinned_names, identity, dash_cfg)
    svg = render_dashboard_svg(rows, theme, width, height, fade_duration_ms / 1000.0)
    log.info("Dashboard generated with %d rows", len(rows))
    return svg
