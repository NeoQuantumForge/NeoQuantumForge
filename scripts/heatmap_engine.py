"""
heatmap_engine.py
------------------
Renders heatmap.svg: a GitHub-style contribution graph built from real
contribution-calendar data, revealed week-by-week, plus streak stats and
a color legend.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any, Dict, List

from config import ThemeConfig
from svg_engine import SVGDocument, animate, group, rect, text
from utils import get_logger

log = get_logger("heatmap_engine")

CELL_SIZE = 11
CELL_GAP = 3
LEVEL_COLORS_DARK = ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"]


@dataclass
class Streaks:
    current: int
    longest: int
    total: int


def _levels_from_counts(days: List[Dict[str, Any]]) -> List[int]:
    counts = [d["contributionCount"] for d in days]
    max_count = max(counts) if counts else 0
    if max_count == 0:
        return [0] * len(counts)
    thresholds = [0, max(1, max_count * 0.25), max(1, max_count * 0.5), max(1, max_count * 0.75)]
    levels = []
    for c in counts:
        if c == 0:
            levels.append(0)
        elif c <= thresholds[1]:
            levels.append(1)
        elif c <= thresholds[2]:
            levels.append(2)
        elif c <= thresholds[3]:
            levels.append(3)
        else:
            levels.append(4)
    return levels


def compute_streaks(weeks: List[Dict[str, Any]]) -> Streaks:
    all_days: List[Dict[str, Any]] = []
    for w in weeks:
        all_days.extend(w.get("contributionDays", []))
    all_days.sort(key=lambda d: d["date"])

    total = sum(d["contributionCount"] for d in all_days)
    longest = current = 0
    running = 0
    today = date.today()

    for d in all_days:
        if d["contributionCount"] > 0:
            running += 1
            longest = max(longest, running)
        else:
            running = 0

    # current streak: count back from most recent day with contributions
    running = 0
    for d in reversed(all_days):
        d_date = datetime.strptime(d["date"], "%Y-%m-%d").date()
        if d["contributionCount"] > 0:
            running += 1
        else:
            if d_date == today:
                continue  # today with 0 contributions doesn't break the streak yet
            break
    current = running

    return Streaks(current=current, longest=longest, total=total)


def render_heatmap_svg(calendar: Dict[str, Any], theme: ThemeConfig, width: int, height: int,
                        reveal_step_s: float = 0.012) -> str:
    weeks = calendar.get("weeks", [])
    doc = SVGDocument(width, height, font_family=theme.font_family, background=theme.panel_background)
    doc.add(rect(0, 0, width, height, fill="none", stroke=theme.border, stroke_width=1, rx=10))

    doc.add(text(18, 24, "CONTRIBUTION ACTIVITY", fill=theme.accent, font_size=12,
                  font_weight="bold", letter_spacing=1.5))

    grid_group = group(id="heatmap-grid")
    doc.add(grid_group)

    grid_x = 18
    grid_y = 40
    cell_span = CELL_SIZE + CELL_GAP

    delay = 0.0
    for wi, week in enumerate(weeks):
        days = week.get("contributionDays", [])
        levels = _levels_from_counts(days)
        for di, (day, level) in enumerate(zip(days, levels)):
            x = grid_x + wi * cell_span
            y = grid_y + di * cell_span
            color = LEVEL_COLORS_DARK[level]
            cell = rect(x, y, CELL_SIZE, CELL_SIZE, fill=color, rx=2)
            cell.attrs["opacity"] = 0
            cell.add(animate("opacity", "0;1", "0.25s", begin=f"{delay:.3f}s"))
            grid_group.add(cell)
        delay += reveal_step_s * 7  # stagger by week for a left-to-right sweep

    streaks = compute_streaks(weeks)
    stats_y = height - 34
    stats_group = group(opacity=0)
    stats_group.add(animate("opacity", "0;1", "0.6s", begin=f"{delay + 0.2:.2f}s"))
    doc.add(stats_group)

    stats_text = (
        f"Current streak: {streaks.current}d   \u2022   "
        f"Longest streak: {streaks.longest}d   \u2022   "
        f"Total: {streaks.total}"
    )
    stats_group.add(text(18, stats_y, stats_text, fill=theme.text_secondary, font_size=11))

    # legend
    legend_x = width - 150
    legend_y = stats_y
    legend_group = group(opacity=0)
    legend_group.add(animate("opacity", "0;1", "0.6s", begin=f"{delay + 0.3:.2f}s"))
    doc.add(legend_group)

    legend_group.add(text(legend_x - 34, legend_y + 4, "Less", fill=theme.text_secondary, font_size=9))
    for i, color in enumerate(LEVEL_COLORS_DARK):
        legend_group.add(rect(legend_x + i * 13, legend_y - 8, 10, 10, fill=color, rx=2))
    legend_group.add(text(legend_x + len(LEVEL_COLORS_DARK) * 13 + 4, legend_y + 4, "More",
                           fill=theme.text_secondary, font_size=9))

    return doc.render()


def build_heatmap_svg(calendar: Dict[str, Any], theme: ThemeConfig, width: int, height: int,
                       reveal_speed_ms: int = 12) -> str:
    svg = render_heatmap_svg(calendar, theme, width, height, reveal_speed_ms / 1000.0)
    n_weeks = len(calendar.get("weeks", []))
    log.info("Heatmap generated with %d weeks", n_weeks)
    return svg
