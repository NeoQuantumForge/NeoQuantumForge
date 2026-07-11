"""fetch_contributions.py -- thin wrapper: retrieves the contribution calendar."""
from __future__ import annotations
from typing import Any, Dict
from github import GitHubClient


def fetch_contributions(client: GitHubClient, use_cache: bool = True) -> Dict[str, Any]:
    return client.get_contribution_calendar(use_cache=use_cache)
