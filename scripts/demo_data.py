"""
demo_data.py
------------
Offline sample data used only as a fallback when GitHub cannot be reached
(no network, no token, or an empty cache on the very first run). This lets
`python main.py` produce a working preview immediately after cloning the
repository, before any secrets or configuration are set up.

None of this data is ever used if a live or cached GitHub response is
available -- see the try/except in main.py.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Dict, List

from config import Config
from github import Profile, Repository

SAMPLE_LANGUAGES = ["Python", "C++", "JavaScript", "TypeScript", "Shell"]
SAMPLE_REPO_NAMES = [
    ("airport-management", "Airport Management", "Python"),
    ("linkedin-automation", "LinkedIn Automation", "Python"),
    ("hotel-management", "Hotel Management", "C++"),
    ("neoquantumforge", "NeoQuantumForge", "Python"),
    ("dotfiles", "Personal dotfiles", "Shell"),
]


def demo_profile(config: Config) -> Profile:
    return Profile(
        login=config.github.username,
        name=config.identity.display_name,
        bio=config.identity.tagline,
        followers=128,
        following=42,
        public_repos=len(SAMPLE_REPO_NAMES),
        location=config.identity.location,
        blog=config.identity.website,
        avatar_url="",
        html_url=f"https://github.com/{config.github.username}",
    )


def demo_repos() -> List[Repository]:
    repos = []
    for i, (slug, desc, lang) in enumerate(SAMPLE_REPO_NAMES):
        repos.append(
            Repository(
                name=slug,
                full_name=f"demo/{slug}",
                description=desc,
                stars=(len(SAMPLE_REPO_NAMES) - i) * 7,
                forks=(len(SAMPLE_REPO_NAMES) - i) * 2,
                language=lang,
                topics=[],
                license="MIT",
                updated_at=(date.today() - timedelta(days=i * 3)).isoformat(),
                html_url=f"https://github.com/demo/{slug}",
                is_fork=False,
                archived=False,
            )
        )
    return repos


def demo_calendar() -> Dict[str, Any]:
    """Builds a plausible 20-week contribution calendar so the heatmap
    renders something meaningful in offline/demo mode."""
    weeks = []
    today = date.today()
    start = today - timedelta(weeks=20)
    cursor = start - timedelta(days=start.weekday() + 1 if start.weekday() != 6 else 0)

    total = 0
    for _w in range(20):
        days = []
        for d in range(7):
            day_date = cursor + timedelta(days=d)
            # deterministic pseudo-random pattern, no external RNG needed
            seed = (day_date.toordinal() * 2654435761) % 2**32
            count = (seed >> 24) % 6 if day_date.weekday() < 5 else (seed >> 24) % 2
            total += count
            days.append({
                "date": day_date.isoformat(),
                "contributionCount": int(count),
                "weekday": day_date.weekday(),
            })
        weeks.append({"contributionDays": days})
        cursor += timedelta(days=7)

    return {"totalContributions": total, "weeks": weeks}
