"""fetch_profile.py -- thin wrapper: retrieves the user's GitHub profile."""
from __future__ import annotations
from github import GitHubClient, Profile


def fetch_profile(client: GitHubClient, use_cache: bool = True) -> Profile:
    return client.get_profile(use_cache=use_cache)
