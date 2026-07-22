"""HTML email templates for daily/weekly/monthly digests."""
from datetime import datetime


def _base_html(title: str, body: str) -> str:
    """Wrap body in a responsive, inline-CSS email template."""
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f5f5f5;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f5f5f5;padding:20px 0">
<tr><td align="center">
<table width="600" cellpadding="0" cellspacing="0" style="background:#fff;border-radius:8px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.08)">
  <tr><td style="background:linear-gradient(135deg,#1a1a2e,#16213e);padding:30px 40px;text-align:center">
    <h1 style="color:#fff;font-size:24px;margin:0">{title}</h1>
    <p style="color:#a0aec0;font-size:14px;margin:8px 0 0">{datetime.now().strftime("%Y-%m-%d")}</p>
  </td></tr>
  <tr><td style="padding:24px 40px">
    {body}
  </td></tr>
  <tr><td style="background:#fafafa;padding:16px 40px;text-align:center;border-top:1px solid #eee">
    <p style="color:#999;font-size:12px;margin:0">
      GitHub Trending Digest — 自动化推送<br>
      数据来源: <a href="https://github.com/trending" style="color:#667eea">GitHub Trending</a> |
      筛选: <a href="https://deepseek.com" style="color:#667eea">DeepSeek AI</a>
    </p>
  </td></tr>
</table>
</td></tr></table>
</body></html>"""


def _repo_card(repo: dict, index: int) -> str:
    """Render a single repo as an HTML card."""
    stars_badge = f"⭐ {repo['stars']:,}"
    lang_badge = f"🔧 {repo['language']}" if repo.get("language") else ""
    score_badge = f"📊 {repo.get('score', '?')}/5" if repo.get("score") else ""

    return f"""
    <div style="border-bottom:1px solid #eee;padding:16px 0;margin:0">
      <h3 style="margin:0 0 6px;font-size:16px">
        <span style="color:#999;font-weight:normal;margin-right:8px">#{index}</span>
        <a href="{repo['html_url']}" style="color:#1a1a2e;text-decoration:none">{repo['full_name']}</a>
      </h3>
      <p style="margin:4px 0;color:#555;font-size:14px;line-height:1.5">{repo.get('reason', repo.get('description', ''))}</p>
      <p style="margin:6px 0 0;color:#888;font-size:12px">
        {stars_badge} &nbsp; {lang_badge} &nbsp; {score_badge}
      </p>
    </div>"""


def build_daily_email(repos: list[dict], date_str: str) -> str:
    """Build daily digest HTML email."""
    if not repos:
        body = '<p style="color:#888;text-align:center;padding:40px">今日暂无新推荐项目 🏖️</p>'
    else:
        cards = "\n".join(_repo_card(r, i) for i, r in enumerate(repos, 1))
        body = f"""
          <p style="color:#666;font-size:14px;margin:0 0 16px">今日精选 <strong>{len(repos)}</strong> 个好用工具 👇</p>
          {cards}
        """

    return _base_html(f"🚀 GitHub 每日精选 — {date_str}", body)


def build_weekly_email(repos: list[dict], date_str: str, stats: dict) -> str:
    """Build weekly summary HTML email."""
    total = stats.get("total_this_week", len(repos))
    cards = "\n".join(_repo_card(r, i) for i, r in enumerate(repos, 1))
    body = f"""
      <p style="color:#666;font-size:14px;margin:0 0 16px">
        本周新收录 <strong>{total}</strong> 个工具，以下是精选 Top {len(repos)} 👇
      </p>
      {cards}
    """
    return _base_html(f"📅 GitHub 周报 — {date_str}", body)


def build_monthly_email(repos: list[dict], date_str: str, stats: dict) -> str:
    """Build monthly report HTML email."""
    total = stats.get("total_this_month", len(repos))
    langs = stats.get("top_languages", {})

    lang_html = ""
    if langs:
        items = "".join(
            f'<span style="display:inline-block;background:#667eea;color:#fff;padding:2px 10px;border-radius:12px;margin:3px;font-size:12px">{lang} ×{count}</span>'
            for lang, count in sorted(langs.items(), key=lambda x: x[1], reverse=True)[:8]
        )
        lang_html = f'<p style="margin:12px 0">{items}</p>'

    cards = "\n".join(_repo_card(r, i) for i, r in enumerate(repos, 1))
    body = f"""
      <p style="color:#666;font-size:14px;margin:0 0 16px">
        本月新收录 <strong>{total}</strong> 个工具，精选 Top {len(repos)} 👇
      </p>
      {lang_html}
      {cards}
    """
    return _base_html(f"📊 GitHub 月度报告 — {date_str}", body)
