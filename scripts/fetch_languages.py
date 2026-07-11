"""fetch_languages.py -- thin wrapper: aggregates top languages from repositories."""
from __future__ import annotations
from typing import Dict, List
from github import GitHubClient, Repository


def fetch_languages(client: GitHubClient, repos: List[Repository]) -> Dict[str, int]:
    return client.get_language_totals(repos)


def top_languages(client: GitHubClient, repos: List[Repository], max_n: int = 5) -> List[str]:
    totals = fetch_languages(client, repos)
    return list(totals.keys())[:max_n]
