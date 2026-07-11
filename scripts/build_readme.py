"""
build_readme.py
----------------
Two responsibilities:

1. Renders boot.svg -- the "Initializing NeoQuantumForge..." sequence
   shown before the dashboard/terminal/heatmap appear, using the same
   svg_engine primitives as everything else.
2. Assembles the final README.md that embeds all generated SVGs in the
   layout described in the project spec, with a responsive (mobile
   degrading to single-column) table layout, footer, social links and
   tech stack badges.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List

from config import Config
from svg_engine import SVGDocument, animate, rect, text
from utils import get_logger

log = get_logger("build_readme")

BOOT_LINES = [
    "Initializing NeoQuantumForge...",
    "Loading Modules...",
    "Connecting to GitHub...",
    "Loading Profile...",
    "Loading Repositories...",
    "Loading Dashboard...",
    "Loading Terminal...",
    "Loading Heatmap...",
    "System Ready.",
]


def build_boot_svg(config: Config) -> str:
    width = config.layout.width
    height = 200
    doc = SVGDocument(width, height, font_family="monospace", background="#010409")
    doc.add(rect(0, 0, width, height, fill="none", stroke=config.theme.border, stroke_width=1, rx=10))

    step_ms = config.animation.boot_speed_ms / 1000.0
    y = 28
    t = 0.1
    for line in BOOT_LINES:
        color = config.theme.success if line == "System Ready." else config.theme.text_primary
        node = text(18, y, f"$ {line}", fill=color, font_size=12.5, font_family="monospace")
        node.attrs["opacity"] = 0
        node.add(animate("opacity", "0;1", "0.2s", begin=f"{t:.2f}s"))
        doc.add(node)
        t += step_ms
        y += 17

    # after boot completes, fade the whole boot panel out so the real UI can
    # take its place visually (GitHub renders everything statically stacked,
    # so we simply let it settle at reduced prominence)
    return doc.render()


def _social_badges(social_links: Dict[str, str]) -> str:
    icons = {
        "github": ("GitHub", "181717", "github"),
        "linkedin": ("LinkedIn", "0A66C2", "linkedin"),
        "twitter": ("Twitter", "1DA1F2", "twitter"),
        "website": ("Website", "58A6FF", "google-chrome"),
    }
    badges = []
    for key, url in social_links.items():
        if not url:
            continue
        label, color, logo = icons.get(key, (key.title(), "58A6FF", "internet-explorer"))
        badges.append(
            f'[![{label}](https://img.shields.io/badge/{label}-{color}?style=for-the-badge&'
            f'logo={logo}&logoColor=white)]({url})'
        )
    return "  \n".join(badges)


def _tech_stack_badges() -> str:
    stack = [
        ("Python", "3776AB", "python"),
        ("SVG", "FFB13B", "svg"),
        ("GitHub_Actions", "2088FF", "githubactions"),
        ("Pillow", "5C3EE8", "python"),
    ]
    return " ".join(
        f'![{name}](https://img.shields.io/badge/{name}-{color}?style=flat-square&logo={logo}&logoColor=white)'
        for name, color, logo in stack
    )


README_TEMPLATE = """<!--
  This README is generated automatically by NeoQuantumForge.
  Do not edit by hand -- run `python main.py` or wait for the daily
  GitHub Actions workflow. See scripts/build_readme.py.
-->

<div align="center">

<img src="assets/boot.svg" alt="boot sequence" width="100%"/>

</div>

<table>
<tr>
<td valign="top" width="42%">

<img src="assets/ascii.svg" alt="ascii portrait" width="100%"/>

</td>
<td valign="top" width="58%">

<img src="assets/dashboard.svg" alt="live dashboard" width="100%"/>

</td>
</tr>
</table>

<img src="assets/terminal.svg" alt="animated terminal" width="100%"/>

<img src="assets/heatmap.svg" alt="contribution heatmap" width="100%"/>

<div align="center">

### Connect

{social_badges}

### Built With

{tech_badges}

<sub>Last generated {last_updated} &middot; regenerated daily via GitHub Actions &middot;
powered by <a href="https://github.com/{username}/NeoQuantumForge">NeoQuantumForge</a></sub>

</div>
"""

MOBILE_NOTE = """
<!--
  Mobile degradation note: the <table> layout above collapses gracefully
  on narrow viewports because GitHub's mobile renderer stacks table cells
  vertically once the viewport drops below the table's natural width, and
  each embedded SVG uses width="100%" so it scales down rather than
  overflowing.
-->
"""


def build_readme(config: Config, username: str) -> str:
    from utils import utc_now_iso

    social = _social_badges(config.social_links)
    tech = _tech_stack_badges()
    content = README_TEMPLATE.format(
        social_badges=social or "_No social links configured_",
        tech_badges=tech,
        last_updated=utc_now_iso(),
        username=username,
    )
    return content + MOBILE_NOTE


def run(config: Config) -> Path:
    boot_svg = build_boot_svg(config)
    boot_path = config.assets_dir / "boot.svg"
    boot_path.write_text(boot_svg, encoding="utf-8")
    log.info("Wrote %s", boot_path)

    readme_content = build_readme(config, config.github.username)
    readme_path = Path(config.output.readme_path)
    if not readme_path.is_absolute():
        from config import REPO_ROOT
        readme_path = REPO_ROOT / readme_path
    readme_path.write_text(readme_content, encoding="utf-8")
    log.info("Wrote %s", readme_path)
    return readme_path


if __name__ == "__main__":
    from config import load_config
    run(load_config())
