"""fetch_activity.py -- thin wrapper: retrieves pinned repositories (used as
'recent activity / featured work' since GitHub's events API is noisy and
rate-limit heavy for a daily profile refresh)."""
from __future__ import annotations
from typing import List
from github import GitHubClient


def fetch_pinned_repositories(client: GitHubClient, use_cache: bool = True) -> List[str]:
    return client.get_pinned_repositories(use_cache=use_cache)
