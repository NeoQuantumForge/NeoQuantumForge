"""
Lightweight unit tests for NeoQuantumForge's core, non-network logic.
Run with:  python -m pytest tests/ -v
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import xml.etree.ElementTree as ET

from config import AsciiConfig, DashboardConfig, IdentityConfig, ThemeConfig
from github import Profile, Repository
from utils import format_count, truncate, xml_escape, clamp, JSONCache


# -- utils -------------------------------------------------------------

def test_format_count_small():
    assert format_count(42) == "42"


def test_format_count_thousands():
    assert format_count(1500) == "1.5k"


def test_format_count_millions():
    assert format_count(2_500_000) == "2.5M"


def test_truncate_short_text_unchanged():
    assert truncate("hello", 10) == "hello"


def test_truncate_long_text_gets_ellipsis():
    result = truncate("a very long string of text", 10)
    assert len(result) == 10
    assert result.endswith("\u2026")


def test_xml_escape():
    assert xml_escape('<a>&"\'') == "&lt;a&gt;&amp;&quot;&apos;"


def test_clamp():
    assert clamp(5, 0, 10) == 5
    assert clamp(-5, 0, 10) == 0
    assert clamp(50, 0, 10) == 10


def test_json_cache_roundtrip(tmp_path):
    cache = JSONCache(tmp_path, ttl_seconds=3600)
    cache.set("mykey", {"hello": "world"})
    assert cache.get("mykey") == {"hello": "world"}


def test_json_cache_miss_returns_none(tmp_path):
    cache = JSONCache(tmp_path, ttl_seconds=3600)
    assert cache.get("does-not-exist") is None


def test_json_cache_expired_returns_none(tmp_path):
    cache = JSONCache(tmp_path, ttl_seconds=-1)
    cache.set("mykey", {"a": 1})
    assert cache.get("mykey") is None
    assert cache.get("mykey", allow_stale=True) == {"a": 1}


# -- svg_engine ----------------------------------------------------------

def test_svg_document_renders_valid_xml():
    from svg_engine import SVGDocument, rect, text

    doc = SVGDocument(200, 100, background="#000")
    doc.add(rect(0, 0, 50, 50, fill="#fff"))
    doc.add(text(10, 10, "hello world"))
    svg_str = doc.render()

    # must parse as valid XML
    root = ET.fromstring(svg_str.split("?>", 1)[1])
    assert root.tag.endswith("svg")


def test_svg_animate_helper_produces_smil_only():
    from svg_engine import animate

    node = animate("opacity", "0;1", "0.5s", begin="1s")
    rendered = node.render()
    assert "<animate" in rendered
    assert "attributeName=\"opacity\"" in rendered


def test_svg_special_characters_are_escaped():
    from svg_engine import SVGDocument, text

    doc = SVGDocument(100, 100)
    doc.add(text(0, 0, "<script>alert(1)</script>"))
    svg_str = doc.render()
    assert "<script>" not in svg_str
    assert "&lt;script&gt;" in svg_str


# -- ascii_engine (pure logic, no image I/O) ------------------------------

def test_ascii_grid_mapping_dark_to_dense_char():
    from ascii_engine import image_to_ascii_grid
    from PIL import Image

    cfg = AsciiConfig(charset="@#%*+=-:. ", columns=4)
    # fully black image -> densest character everywhere
    img = Image.new("L", (40, 40), color=0)
    grid = image_to_ascii_grid(img, cfg)
    assert all(ch == "@" for line in grid for ch in line)


def test_ascii_grid_mapping_light_to_sparse_char():
    from ascii_engine import image_to_ascii_grid
    from PIL import Image

    cfg = AsciiConfig(charset="@#%*+=-:. ", columns=4)
    img = Image.new("L", (40, 40), color=255)
    grid = image_to_ascii_grid(img, cfg)
    assert all(ch == " " for line in grid for ch in line)


# -- dashboard_engine ------------------------------------------------------

def test_dashboard_rows_include_configured_widgets():
    from dashboard_engine import build_dashboard_rows

    profile = Profile(login="octocat", name="Octo Cat", followers=10, public_repos=3)
    repos = [
        Repository(name="a", full_name="octocat/a", stars=5, language="Python"),
        Repository(name="b", full_name="octocat/b", stars=2, language="Python"),
    ]
    identity = IdentityConfig(display_name="Octo Cat", role="Engineer")
    dash_cfg = DashboardConfig(widgets=["name", "followers", "top_languages"])

    rows = build_dashboard_rows(profile, repos, [], identity, dash_cfg)
    labels = [r.label for r in rows]
    assert "name" in labels
    assert "followers" in labels
    assert "top languages" in labels
    assert len(rows) == 3


def test_dashboard_total_stars_excludes_forks():
    from dashboard_engine import _total_stars

    repos = [
        Repository(name="a", full_name="x/a", stars=10, is_fork=False),
        Repository(name="b", full_name="x/b", stars=99, is_fork=True),
    ]
    assert _total_stars(repos) == 10


# -- heatmap_engine --------------------------------------------------------

def test_heatmap_streak_calculation():
    from datetime import date, timedelta
    from heatmap_engine import compute_streaks

    today = date.today()
    days = [
        {"date": (today - timedelta(days=2)).isoformat(), "contributionCount": 3, "weekday": 0},
        {"date": (today - timedelta(days=1)).isoformat(), "contributionCount": 1, "weekday": 1},
        {"date": today.isoformat(), "contributionCount": 2, "weekday": 2},
    ]
    weeks = [{"contributionDays": days}]
    streaks = compute_streaks(weeks)
    assert streaks.total == 6
    assert streaks.current == 3
    assert streaks.longest == 3


def test_heatmap_levels_from_counts_zero_max():
    from heatmap_engine import _levels_from_counts

    days = [{"contributionCount": 0}, {"contributionCount": 0}]
    assert _levels_from_counts(days) == [0, 0]
