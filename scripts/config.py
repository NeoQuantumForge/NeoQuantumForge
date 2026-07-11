"""
config.py
---------
Typed configuration loading for NeoQuantumForge.

Everything the system needs is described in ``profile.json`` at the
repository root. This module parses that file into strongly typed
dataclasses so the rest of the codebase never touches raw dictionaries.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PROFILE_PATH = REPO_ROOT / "profile.json"


@dataclass
class GitHubConfig:
    username: str
    token_env_var: str = "GITHUB_TOKEN"

    @property
    def token(self) -> Optional[str]:
        return os.environ.get(self.token_env_var)


@dataclass
class IdentityConfig:
    display_name: str
    role: str
    tagline: str = ""
    location: str = ""
    website: str = ""
    current_focus: str = ""


@dataclass
class PhotoConfig:
    path: str = "assets/photo.jpg"

    def resolve(self) -> Path:
        p = Path(self.path)
        return p if p.is_absolute() else REPO_ROOT / p


@dataclass
class ThemeConfig:
    name: str = "neoquantum-dark"
    background: str = "#0d1117"
    panel_background: str = "#161b22"
    border: str = "#30363d"
    text_primary: str = "#c9d1d9"
    text_secondary: str = "#8b949e"
    accent: str = "#58a6ff"
    accent_dim: str = "#1f6feb"
    success: str = "#3fb950"
    font_family: str = "'JetBrains Mono', 'Fira Code', 'Consolas', monospace"


@dataclass
class AnimationConfig:
    boot_speed_ms: int = 220
    typing_speed_ms: int = 55
    ascii_reveal_speed_ms: int = 18
    heatmap_reveal_speed_ms: int = 12
    fade_duration_ms: int = 600


@dataclass
class DashboardConfig:
    widgets: List[str] = field(default_factory=list)
    pinned_repositories: List[str] = field(default_factory=list)
    featured_repositories: List[str] = field(default_factory=list)
    max_top_languages: int = 5


@dataclass
class AsciiConfig:
    charset: str = "@#%*+=-:. "
    columns: int = 70
    font_size: int = 6
    line_height: int = 7
    contrast: float = 1.25
    gamma: float = 1.0
    brightness: float = 1.05
    remove_background: bool = True
    reveal_speed_ms: int = 18


@dataclass
class TerminalCommand:
    cmd: str
    output: Any  # list[str] or "auto:<source>"


@dataclass
class TerminalConfig:
    prompt: str = "NeoQuantumForge@github:~$"
    typing_speed_ms: int = 45
    commands: List[TerminalCommand] = field(default_factory=list)


@dataclass
class LayoutConfig:
    width: int = 900
    ascii_panel_width: int = 360
    dashboard_panel_width: int = 500
    terminal_height: int = 260
    heatmap_height: int = 180
    mobile_breakpoint: int = 600


@dataclass
class OutputConfig:
    assets_dir: str = "assets"
    readme_path: str = "README.md"


@dataclass
class Config:
    github: GitHubConfig
    identity: IdentityConfig
    photo: PhotoConfig
    social_links: Dict[str, str]
    theme: ThemeConfig
    animation: AnimationConfig
    dashboard: DashboardConfig
    ascii: AsciiConfig
    terminal: TerminalConfig
    layout: LayoutConfig
    output: OutputConfig

    @property
    def assets_dir(self) -> Path:
        p = Path(self.output.assets_dir)
        d = p if p.is_absolute() else REPO_ROOT / p
        d.mkdir(parents=True, exist_ok=True)
        return d

    @property
    def cache_dir(self) -> Path:
        d = REPO_ROOT / "cache"
        d.mkdir(parents=True, exist_ok=True)
        return d

    @property
    def data_dir(self) -> Path:
        d = REPO_ROOT / "data"
        d.mkdir(parents=True, exist_ok=True)
        return d


def _build_terminal(raw: Dict[str, Any]) -> TerminalConfig:
    commands = [
        TerminalCommand(cmd=c["cmd"], output=c.get("output", []))
        for c in raw.get("commands", [])
    ]
    return TerminalConfig(
        prompt=raw.get("prompt", "NeoQuantumForge@github:~$"),
        typing_speed_ms=raw.get("typing_speed_ms", 45),
        commands=commands,
    )


def load_config(path: Optional[Path] = None) -> Config:
    """Load and validate profile.json into a Config object."""
    path = path or DEFAULT_PROFILE_PATH
    if not path.exists():
        raise FileNotFoundError(
            f"Configuration file not found at {path}. "
            "Copy profile.json.example or create profile.json first."
        )

    with open(path, "r", encoding="utf-8") as fh:
        raw = json.load(fh)

    try:
        cfg = Config(
            github=GitHubConfig(**raw["github"]),
            identity=IdentityConfig(**raw["identity"]),
            photo=PhotoConfig(**raw.get("photo", {})),
            social_links=raw.get("social_links", {}),
            theme=ThemeConfig(**raw.get("theme", {})),
            animation=AnimationConfig(**raw.get("animation", {})),
            dashboard=DashboardConfig(**raw.get("dashboard", {})),
            ascii=AsciiConfig(**raw.get("ascii", {})),
            terminal=_build_terminal(raw.get("terminal", {})),
            layout=LayoutConfig(**raw.get("layout", {})),
            output=OutputConfig(**raw.get("output", {})),
        )
    except KeyError as exc:
        raise ValueError(f"profile.json is missing required key: {exc}") from exc
    except TypeError as exc:
        raise ValueError(f"profile.json has an invalid field: {exc}") from exc

    return cfg
