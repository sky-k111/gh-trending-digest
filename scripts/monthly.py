"""Monthly GitHub trending report — aggregate and send."""
import sys
import os
from datetime import datetime, timedelta
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config import get_config
from src.template import build_monthly_email
from src.sender import send_email
from src.store import get_history_for_period


def main():
    cfg = get_config()
    today = datetime.now().strftime("%Y-%m-%d")
    month_start = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

    print(f"[monthly] Gathering history from {month_start} to {today}...")

    entries = get_history_for_period(days=30)
    daily_entries = [e for e in entries if e.get("type") == "daily"]

    if not daily_entries:
        print("[monthly] No daily entries this month, nothing to summarize")
        return

    all_repos = []
    for entry in daily_entries:
        all_repos.extend(entry.get("repos", []))

    # Deduplicate
    seen_ids = set()
    unique_repos = []
    for r in all_repos:
        rid = r.get("id")
        if rid and rid not in seen_ids:
            seen_ids.add(rid)
            unique_repos.append(r)

    unique_repos.sort(key=lambda r: (r.get("score", 0), r.get("stars", 0)), reverse=True)

    # Top 15 for monthly highlight
    top = unique_repos[:15]

    # Stats
    languages = Counter(r.get("language", "Unknown") for r in all_repos if r.get("language"))

    # Average score
    scores = [r.get("score", 0) for r in unique_repos if r.get("score")]
    avg_score = sum(scores) / len(scores) if scores else 0

    stats = {
        "total_this_month": len(unique_repos),
        "top_languages": dict(languages.most_common(8)),
        "avg_score": round(avg_score, 1),
        "daily_count": len(daily_entries),
    }

    html = build_monthly_email(top, month_start, stats)

    ok = send_email(
        html,
        f"📊 GitHub 月度报告 — {datetime.now().strftime('%Y年%m月')}",
        cfg["qq_smtp_user"],
        cfg["qq_smtp_pass"],
    )

    status = "✅ sent" if ok else "⚠️ built but send failed"
    print(f"[monthly] Done: {len(unique_repos)} repos this month, avg score {avg_score:.1f}, {status}")


if __name__ == "__main__":
    main()
