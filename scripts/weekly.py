"""Weekly GitHub trending summary — aggregate and send."""
import sys
import os
from datetime import datetime, timedelta
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config import get_config
from src.template import build_weekly_email
from src.sender import send_email
from src.store import get_history_for_period


def main():
    cfg = get_config()
    today = datetime.now().strftime("%Y-%m-%d")
    week_start = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

    print(f"[weekly] Gathering history from {week_start} to {today}...")

    entries = get_history_for_period(days=7)
    daily_entries = [e for e in entries if e.get("type") == "daily"]

    if not daily_entries:
        print("[weekly] No daily entries this week, nothing to summarize")
        return

    # Collect all repos from this week
    all_repos = []
    for entry in daily_entries:
        all_repos.extend(entry.get("repos", []))

    # Deduplicate by id
    seen_ids = set()
    unique_repos = []
    for r in all_repos:
        rid = r.get("id")
        if rid and rid not in seen_ids:
            seen_ids.add(rid)
            unique_repos.append(r)

    # Sort by score desc, then stars desc
    unique_repos.sort(key=lambda r: (r.get("score", 0), r.get("stars", 0)), reverse=True)

    # Top 10 for weekly highlight
    top = unique_repos[:10]

    # Stats
    languages = Counter(r.get("language", "Unknown") for r in all_repos if r.get("language"))

    stats = {
        "total_this_week": len(unique_repos),
        "top_languages": dict(languages.most_common(5)),
    }

    html = build_weekly_email(top, f"{week_start} ~ {today}", stats)

    ok = send_email(
        html,
        f"📅 GitHub 周报 — {week_start} ~ {today}",
        cfg["qq_smtp_user"],
        cfg["qq_smtp_pass"],
    )

    status = "✅ sent" if ok else "⚠️ built but send failed"
    print(f"[weekly] Done: {len(unique_repos)} repos this week, top {len(top)} highlighted, {status}")


if __name__ == "__main__":
    main()
