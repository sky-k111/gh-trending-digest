"""Fetch trending repositories from GitHub Search API."""
import time
import requests


GITHUB_API = "https://api.github.com"
MAX_RETRIES = 3


def _build_query(date_since: str) -> str:
    """Build GitHub search query for repos created after date_since."""
    return f"created:>{date_since} stars:>30"


def fetch_trending(date_since: str, github_token: str = "") -> list[dict]:
    """Fetch top 30 repos created after date_since, sorted by stars.

    Args:
        date_since: ISO date string, e.g. "2026-07-21"
        github_token: Optional GitHub PAT for higher rate limit

    Returns:
        List of repo dicts with keys: id, full_name, description,
        html_url, stars, language, topics, created_at
    """
    url = f"{GITHUB_API}/search/repositories"
    headers = {"Accept": "application/vnd.github+json"}
    if github_token:
        headers["Authorization"] = f"Bearer {github_token}"

    params = {
        "q": _build_query(date_since),
        "sort": "stars",
        "order": "desc",
        "per_page": 30,
    }

    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.get(url, headers=headers, params=params, timeout=15)
            if resp.status_code == 200:
                items = resp.json().get("items", [])
                return [_parse_item(item) for item in items]
            elif resp.status_code == 403:
                # Rate limited
                wait = 2 ** attempt
                print(f"[fetcher] Rate limited, retrying in {wait}s...")
                time.sleep(wait)
            elif resp.status_code == 422:
                print(f"[fetcher] Invalid query: {resp.json()}")
                return []
            else:
                print(f"[fetcher] HTTP {resp.status_code}, retrying...")
                time.sleep(2 ** attempt)
        except requests.RequestException as e:
            print(f"[fetcher] Request failed (attempt {attempt + 1}): {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(2 ** attempt)

    print("[fetcher] All retries exhausted, returning empty list")
    return []


def _parse_item(item: dict) -> dict:
    return {
        "id": item["id"],
        "full_name": item["full_name"],
        "description": item.get("description") or "",
        "html_url": item["html_url"],
        "stars": item["stargazers_count"],
        "language": item.get("language") or "Unknown",
        "topics": item.get("topics") or [],
        "created_at": item["created_at"],
    }
