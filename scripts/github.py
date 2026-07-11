"""
github.py
---------
A thin, resilient GitHub API client used by every ``fetch_*`` module.

Design goals:
  * Never crash the whole build because of one flaky request -> retries + cache fallback.
  * Respect rate limits (checks remaining quota, backs off if low).
  * Keep GitHub-specific logic in exactly one place (no duplicated requests
    code anywhere else in the project, per the project's SVG/engine rules).
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import requests

from config import GitHubConfig
from utils import JSONCache, get_logger, retry

log = get_logger("github")

API_ROOT = "https://api.github.com"
GRAPHQL_ROOT = "https://api.github.com/graphql"


@dataclass
class Repository:
    name: str
    full_name: str
    description: str = ""
    stars: int = 0
    forks: int = 0
    language: Optional[str] = None
    topics: List[str] = field(default_factory=list)
    license: Optional[str] = None
    is_pinned: bool = False
    updated_at: Optional[str] = None
    html_url: str = ""
    is_fork: bool = False
    archived: bool = False


@dataclass
class Profile:
    login: str
    name: str
    bio: str = ""
    followers: int = 0
    following: int = 0
    public_repos: int = 0
    location: str = ""
    blog: str = ""
    avatar_url: str = ""
    html_url: str = ""


class GitHubClient:
    """Wraps REST + GraphQL calls, with a JSON cache used both to reduce
    calls and as a graceful fallback if GitHub is unreachable."""

    def __init__(self, config: GitHubConfig, cache: JSONCache):
        self.config = config
        self.cache = cache
        self._session = requests.Session()
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "NeoQuantumForge-ProfileBot",
        }
        if self.config.token:
            headers["Authorization"] = f"Bearer {self.config.token}"
        self._session.headers.update(headers)

    # -- low level -----------------------------------------------------

    @retry(times=3, delay_seconds=2.0, exceptions=(requests.RequestException,))
    def _get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        url = path if path.startswith("http") else f"{API_ROOT}{path}"
        resp = self._session.get(url, params=params, timeout=15)
        self._check_rate_limit(resp)
        resp.raise_for_status()
        return resp.json()

    @retry(times=3, delay_seconds=2.0, exceptions=(requests.RequestException,))
    def _graphql(self, query: str, variables: Dict[str, Any]) -> Any:
        resp = self._session.post(
            GRAPHQL_ROOT, json={"query": query, "variables": variables}, timeout=20
        )
        self._check_rate_limit(resp)
        resp.raise_for_status()
        payload = resp.json()
        if "errors" in payload:
            raise RuntimeError(f"GraphQL error: {payload['errors']}")
        return payload["data"]

    @staticmethod
    def _check_rate_limit(resp: requests.Response) -> None:
        remaining = resp.headers.get("X-RateLimit-Remaining")
        if remaining is not None and int(remaining) < 5:
            reset = int(resp.headers.get("X-RateLimit-Reset", time.time() + 60))
            wait = max(0, reset - int(time.time()))
            log.warning("GitHub rate limit nearly exhausted, sleeping %ss", wait)
            time.sleep(min(wait, 120))

    # -- cached fetchers, one per data type ------------------------------

    def _cached(self, key: str, ttl_ok: bool, fetch_fn) -> Any:
        if ttl_ok:
            cached = self.cache.get(key)
            if cached is not None:
                log.info("cache hit: %s", key)
                return cached
        try:
            data = fetch_fn()
            self.cache.set(key, data)
            return data
        except requests.RequestException as exc:
            log.error("live fetch failed for %s (%s); falling back to stale cache", key, exc)
            stale = self.cache.get(key, allow_stale=True)
            if stale is not None:
                return stale
            raise

    def get_profile(self, use_cache: bool = True) -> Profile:
        data = self._cached(
            "profile", use_cache, lambda: self._get(f"/users/{self.config.username}")
        )
        return Profile(
            login=data.get("login", self.config.username),
            name=data.get("name") or data.get("login", self.config.username),
            bio=data.get("bio") or "",
            followers=data.get("followers", 0),
            following=data.get("following", 0),
            public_repos=data.get("public_repos", 0),
            location=data.get("location") or "",
            blog=data.get("blog") or "",
            avatar_url=data.get("avatar_url", ""),
            html_url=data.get("html_url", ""),
        )

    def get_repositories(self, use_cache: bool = True) -> List[Repository]:
        def fetch_all() -> List[Dict[str, Any]]:
            repos: List[Dict[str, Any]] = []
            page = 1
            while True:
                batch = self._get(
                    f"/users/{self.config.username}/repos",
                    params={"per_page": 100, "page": page, "sort": "updated"},
                )
                if not batch:
                    break
                repos.extend(batch)
                if len(batch) < 100:
                    break
                page += 1
                if page > 10:  # hard safety cap (>1000 repos)
                    break
            return repos

        raw = self._cached("repositories", use_cache, fetch_all)
        repos = [
            Repository(
                name=r["name"],
                full_name=r["full_name"],
                description=r.get("description") or "",
                stars=r.get("stargazers_count", 0),
                forks=r.get("forks_count", 0),
                language=r.get("language"),
                topics=r.get("topics", []) or [],
                license=(r.get("license") or {}).get("spdx_id") if r.get("license") else None,
                updated_at=r.get("updated_at"),
                html_url=r.get("html_url", ""),
                is_fork=r.get("fork", False),
                archived=r.get("archived", False),
            )
            for r in raw
        ]
        return repos

    def get_pinned_repositories(self, use_cache: bool = True) -> List[str]:
        """Pinned repos require GraphQL; REST has no endpoint for this."""
        query = """
        query($login: String!) {
          user(login: $login) {
            pinnedItems(first: 6, types: [REPOSITORY]) {
              nodes {
                ... on Repository { name }
              }
            }
          }
        }
        """

        def fetch() -> List[str]:
            if not self.config.token:
                return []
            data = self._graphql(query, {"login": self.config.username})
            nodes = data["user"]["pinnedItems"]["nodes"]
            return [n["name"] for n in nodes]

        return self._cached("pinned", use_cache, fetch)

    def get_contribution_calendar(self, use_cache: bool = True) -> Dict[str, Any]:
        """Returns the last 52 weeks of contribution counts via GraphQL."""
        query = """
        query($login: String!) {
          user(login: $login) {
            contributionsCollection {
              contributionCalendar {
                totalContributions
                weeks {
                  contributionDays { date contributionCount weekday }
                }
              }
            }
          }
        }
        """

        def fetch() -> Dict[str, Any]:
            if not self.config.token:
                return {"totalContributions": 0, "weeks": []}
            data = self._graphql(query, {"login": self.config.username})
            return data["user"]["contributionsCollection"]["contributionCalendar"]

        return self._cached("contributions", use_cache, fetch)

    def get_language_totals(self, repos: List[Repository]) -> Dict[str, int]:
        """Aggregate primary languages across repos (byte-accurate language
        breakdown would need one extra call per repo; primary language per
        repo is a good, cheap approximation used here)."""
        totals: Dict[str, int] = {}
        for r in repos:
            if r.language and not r.is_fork:
                totals[r.language] = totals.get(r.language, 0) + 1
        return dict(sorted(totals.items(), key=lambda kv: kv[1], reverse=True))
