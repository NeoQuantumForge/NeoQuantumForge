"""fetch_repositories.py -- thin wrapper: retrieves all public repositories."""
from __future__ import annotations
from typing import List
from github import GitHubClient, Repository


def fetch_repositories(client: GitHubClient, use_cache: bool = True) -> List[Repository]:
    return client.get_repositories(use_cache=use_cache)
