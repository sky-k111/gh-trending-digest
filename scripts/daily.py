"""Daily GitHub trending digest — fetch, filter, send."""
import sys
import os
from datetime import datetime, timedelta

# Allow running from project root: python scripts/daily.py
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config import get_config
from src.fetcher import fetch_trending
from src.filter import filter_with_ai
from src.template import build_daily_email
from src.sender import send_email
from src.store import load_seen, mark_seen, add_history_entry


def main():
    cfg = get_config()
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    today = datetime.now().strftime("%Y-%m-%d")

    print(f"[daily] Fetching repos created after {yesterday}...")

    # 1. Fetch
    repos = fetch_trending(yesterday, cfg["github_token"])
    print(f"[daily] Fetched {len(repos)} repos")

    if not repos:
        print("[daily] No repos found, exiting without sending")
        return

    # 2. Dedup — filter out already-seen repos
    seen = load_seen()
    fresh_repos = [r for r in repos if str(r["id"]) not in seen]
    skipped = len(repos) - len(fresh_repos)
    if skipped:
        print(f"[daily] Skipped {skipped} already-seen repos, {len(fresh_repos)} remaining")

    if not fresh_repos:
        print("[daily] All repos already seen, exiting")
        return

    # 3. AI filter
    picks = filter_with_ai(fresh_repos, cfg["deepseek_api_key"])

    if not picks:
        print("[daily] No repos passed filter, exiting")
        return

    # 4. Mark as seen
    for r in picks:
        mark_seen(r["id"], r.get("score", 0), source="daily")

    # 5. Build email
    html = build_daily_email(picks, today)

    # 6. Send
    ok = send_email(
        html,
        f"🚀 GitHub 每日精选 — {today}",
        cfg["qq_smtp_user"],
        cfg["qq_smtp_pass"],
    )

    # 7. Record history (even if send failed, we want to remember picks)
    add_history_entry({
        "date": today,
        "type": "daily",
        "count": len(picks),
        "repos": [
            {
                "id": r["id"],
                "full_name": r["full_name"],
                "html_url": r["html_url"],
                "stars": r["stars"],
                "score": r.get("score", 0),
                "reason": r.get("reason", ""),
            }
            for r in picks
        ],
    })

    status = "[OK] sent" if ok else "[WARN] built but send failed"
    print(f"[daily] Done: {len(picks)} repos, {status}")


if __name__ == "__main__":
    main()
