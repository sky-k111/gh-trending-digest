# GitHub Trending Digest Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a GitHub Actions cron job that fetches trending repos via GitHub Search API, filters them with DeepSeek AI, and sends HTML digests to QQ email daily/weekly/monthly.

**Architecture:** Single Python project with 5 core modules (fetcher, filter, sender, template, store), 3 entry scripts (daily/weekly/monthly), 3 GitHub Actions workflows. All config via environment variables from GitHub Secrets. JSON files for lightweight dedup and history storage.

**Tech Stack:** Python 3.11+, requests, smtplib, DeepSeek API, QQ SMTP, GitHub Actions

## Global Constraints

- Python 3.11+, dependency: `requests` only (+ `python-dotenv` for local dev)
- All config from environment variables, no hardcoded secrets
- Single-file modules < 200 lines each
- HTML emails: inline CSS, no external resources
- Partially-failing: one module fails doesn't block others (skip instead of crash)
- DeepSeek API failure → fallback to star-sort top 10
- GitHub API failure after 3 retries → skip that day's send
- QQ SMTP failure → log error, don't crash

---

### Task 1: Project Scaffolding

**Files:**
- Create: `D:\Projects\gh-trending-digest\requirements.txt`
- Create: `D:\Projects\gh-trending-digest\config.py`
- Create: `D:\Projects\gh-trending-digest\.gitignore`
- Create: `D:\Projects\gh-trending-digest\.env.example`
- Create: `D:\Projects\gh-trending-digest\data\.gitkeep`

**Interfaces:**
- Produces: `config.py` with `get_config() -> dict` returning `{github_token, deepseek_api_key, qq_smtp_user, qq_smtp_pass}`

- [ ] **Step 1: Create requirements.txt**

```txt
requests>=2.31.0
python-dotenv>=1.0.0
```

- [ ] **Step 2: Create config.py**

```python
"""Load configuration from environment variables."""
import os


def get_config():
    """Return all config values from environment.
    
    Tries .env file first via python-dotenv if available.
    Returns dict with all config keys.
    """
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    return {
        "github_token": os.getenv("GITHUB_TOKEN", ""),
        "deepseek_api_key": os.getenv("DEEPSEEK_API_KEY", ""),
        "qq_smtp_user": os.getenv("QQ_SMTP_USER", ""),
        "qq_smtp_pass": os.getenv("QQ_SMTP_PASS", ""),
    }
```

- [ ] **Step 3: Create .gitignore**

```
.env
data/*.log
__pycache__/
*.pyc
error.log
```

- [ ] **Step 4: Create .env.example**

```
GITHUB_TOKEN=ghp_xxxxxxxxxxxx
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxx
QQ_SMTP_USER=1503794397@qq.com
QQ_SMTP_PASS=xxxxxxxxxxxx
```

- [ ] **Step 5: Create data/ directory with .gitkeep**

```bash
mkdir -p data && touch data/.gitkeep
```

- [ ] **Step 6: Init git and commit**

```bash
cd D:/Projects/gh-trending-digest
git init
git add -A
git commit -m "chore: project scaffolding with config and deps"
```

---

### Task 2: store.py — JSON Data Store

**Files:**
- Create: `D:\Projects\gh-trending-digest\src\store.py`
- Create: `D:\Projects\gh-trending-digest\tests\test_store.py`

**Interfaces:**
- Produces:
  - `load_seen() -> dict[str, dict]` — load `data/seen.json`, return empty dict if missing
  - `save_seen(data: dict[str, dict]) -> None`
  - `is_seen(repo_id: int) -> bool`
  - `mark_seen(repo_id: int, score: int, source: str = "daily") -> None`
  - `load_history() -> list[dict]`
  - `add_history_entry(entry: dict) -> None`
  - `get_history_for_period(days: int) -> list[dict]`

- [ ] **Step 1: Create test file**

```python
"""Tests for store module."""
import json
import os
import sys
import tempfile
import pytest

# Ensure src/ is on path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from store import (
    load_seen, save_seen, is_seen, mark_seen,
    load_history, add_history_entry, get_history_for_period,
)


@pytest.fixture
def temp_data_dir(monkeypatch):
    """Redirect DATA_DIR to a temp directory."""
    with tempfile.TemporaryDirectory() as tmp:
        data_dir = os.path.join(tmp, "data")
        os.makedirs(data_dir, exist_ok=True)
        import store
        monkeypatch.setattr(store, "DATA_DIR", data_dir)
        yield data_dir


class TestSeen:
    def test_load_seen_empty(self, temp_data_dir):
        assert load_seen() == {}

    def test_save_and_load_seen(self, temp_data_dir):
        data = {"123": {"score": 4, "pushed_at": "2026-07-21", "source": "daily"}}
        save_seen(data)
        assert load_seen() == data

    def test_is_seen_true(self, temp_data_dir):
        save_seen({"456": {"score": 5, "pushed_at": "2026-07-21", "source": "daily"}})
        assert is_seen(456) is True

    def test_is_seen_false(self, temp_data_dir):
        assert is_seen(999) is False

    def test_mark_seen_adds_entry(self, temp_data_dir):
        mark_seen(789, score=4, source="daily")
        data = load_seen()
        assert "789" in data
        assert data["789"]["score"] == 4
        assert data["789"]["source"] == "daily"


class TestHistory:
    def test_load_history_empty(self, temp_data_dir):
        assert load_history() == []

    def test_add_and_load_history(self, temp_data_dir):
        entry = {"date": "2026-07-22", "type": "daily", "repos": []}
        add_history_entry(entry)
        assert load_history() == [entry]

    def test_get_history_for_period(self, temp_data_dir):
        old = {"date": "2026-07-10", "type": "daily", "repos": []}
        recent = {"date": "2026-07-22", "type": "daily", "repos": []}
        add_history_entry(old)
        add_history_entry(recent)
        result = get_history_for_period(days=7)
        assert len(result) == 1
        assert result[0]["date"] == "2026-07-22"

    def test_data_dir_auto_create(self, temp_data_dir):
        import store
        import shutil
        shutil.rmtree(temp_data_dir)
        # Should not raise
        result = load_seen()
        assert result == {}
```

- [ ] **Step 2: Run tests to verify failure**

```bash
cd D:/Projects/gh-trending-digest
pip install pytest
pytest tests/test_store.py -v
```
Expected: All fail (ImportError or similar)

- [ ] **Step 3: Implement store.py**

```python
"""JSON file store for seen repos and push history."""
import json
import os
import fcntl
from datetime import datetime, timedelta

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")


def _ensure_data_dir():
    os.makedirs(DATA_DIR, exist_ok=True)


def _read_json(filename):
    """Read JSON file, return default if missing or corrupt."""
    _ensure_data_dir()
    path = os.path.join(DATA_DIR, filename)
    default: dict | list = {} if filename == "seen.json" else []
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def _write_json(filename, data):
    """Atomically write JSON file."""
    _ensure_data_dir()
    path = os.path.join(DATA_DIR, filename)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


# --- Seen repos ---

def load_seen() -> dict:
    return _read_json("seen.json")


def save_seen(data: dict) -> None:
    _write_json("seen.json", data)


def is_seen(repo_id: int) -> bool:
    return str(repo_id) in load_seen()


def mark_seen(repo_id: int, score: int, source: str = "daily") -> None:
    data = load_seen()
    data[str(repo_id)] = {
        "score": score,
        "pushed_at": datetime.now().strftime("%Y-%m-%d"),
        "source": source,
    }
    save_seen(data)


# --- History ---

def load_history() -> list:
    return _read_json("history.json")


def add_history_entry(entry: dict) -> None:
    history = load_history()
    history.append(entry)
    _write_json("history.json", history)


def get_history_for_period(days: int) -> list:
    """Return history entries from the last `days` days."""
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    return [e for e in load_history() if e.get("date", "") >= cutoff]
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_store.py -v
```
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add src/store.py tests/test_store.py data/
git commit -m "feat: add store module for JSON-based dedup and history"
```

---

### Task 3: fetcher.py — GitHub Search API

**Files:**
- Create: `D:\Projects\gh-trending-digest\src\fetcher.py`

**Interfaces:**
- Consumes: `config["github_token"]` (str, optional)
- Produces: `fetch_trending(date_since: str, github_token: str = "") -> list[dict]`
  - `date_since` format: `"2026-07-21"`
  - Returns `[{id, full_name, description, html_url, stars, language, topics, created_at}]`

- [ ] **Step 1: Implement fetcher.py**

```python
"""Fetch trending repositories from GitHub Search API."""
import time
import requests


GITHUB_API = "https://api.github.com"
MAX_RETRIES = 3


def _build_query(date_since: str) -> str:
    """Build GitHub search query for repos created after date_since."""
    return f"created:>{date_since} stars:>10"


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
```

- [ ] **Step 2: Quick smoke test**

```bash
cd D:/Projects/gh-trending-digest
python -c "from src.fetcher import fetch_trending; r = fetch_trending('2026-07-20'); print(f'Fetched {len(r)} repos')"
```
Expected: Prints number of repos (may be 0 if no token, should not crash)

- [ ] **Step 3: Commit**

```bash
git add src/fetcher.py
git commit -m "feat: add fetcher module for GitHub Search API"
```

---

### Task 4: filter.py — DeepSeek AI Filter

**Files:**
- Create: `D:\Projects\gh-trending-digest\src\filter.py`

**Interfaces:**
- Consumes: `config["deepseek_api_key"]` (str), `store.is_seen()` from Task 2
- Produces:
  - `filter_with_ai(repos: list[dict], api_key: str) -> list[dict]`
  - `filter_by_stars(repos: list[dict], top_n: int = 10) -> list[dict]` — fallback

- [ ] **Step 1: Implement filter.py**

```python
"""Filter repos with DeepSeek AI, fallback to star-sort."""
import json
import requests
from datetime import datetime

DEEPSEEK_API = "https://api.deepseek.com/chat/completions"


def _build_prompt(repos: list[dict]) -> str:
    """Build prompt asking AI to score each repo."""
    repo_list = []
    for i, r in enumerate(repos, 1):
        desc = r["description"][:200] if r["description"] else "无描述"
        topics = ", ".join(r["topics"][:5]) if r["topics"] else "无"
        repo_list.append(
            f"{i}. [{r['full_name']}]({r['html_url']})\n"
            f"   描述: {desc}\n"
            f"   语言: {r['language']} | Stars: {r['stars']} | Topics: {topics}"
        )

    joined = "\n\n".join(repo_list)
    return f"""你是GitHub工具审核专家。以下{len(repos)}个GitHub仓库，请筛选出真正实用的开发者工具。

评分标准（1-5分）：
- 5分：非常实用，开发者必备
- 4分：有价值，值得关注
- 3分：一般，可用但非必需
- 2分：不太实用，或文档不全
- 1分：低质量/纯宣传/教程合集

排除以下类型：面试题合集、教程文档、XX大全、Awesome-list、空壳项目。

只返回JSON数组，不要markdown代码块，不要其他文字：
[
  {{"index": 1, "score": 4, "reason": "简洁的一句中评语"}},
  ...
]

以下是仓库列表：

{joined}"""


def filter_with_ai(repos: list[dict], api_key: str) -> list[dict]:
    """Score repos with DeepSeek, return those scoring >= 4.
    
    Args:
        repos: List of repo dicts from fetcher
        api_key: DeepSeek API key
    
    Returns:
        Scored repos with added 'score' and 'reason' fields, sorted by score desc
    """
    if not repos:
        return []
    if not api_key:
        print("[filter] No DeepSeek API key, falling back to star-sort")
        return filter_by_stars(repos)

    prompt = _build_prompt(repos)

    try:
        resp = requests.post(
            DEEPSEEK_API,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "deepseek-chat",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
                "max_tokens": 2000,
            },
            timeout=30,
        )

        if resp.status_code != 200:
            print(f"[filter] DeepSeek API error {resp.status_code}: {resp.text[:200]}")
            return filter_by_stars(repos)

        content = resp.json()["choices"][0]["message"]["content"]
        scores = _parse_scores(content)

    except (requests.RequestException, KeyError, json.JSONDecodeError) as e:
        print(f"[filter] AI filter failed: {e}, falling back to star-sort")
        return filter_by_stars(repos)

    # Merge scores back into repos
    scored = []
    for s in scores:
        idx = s["index"] - 1  # 1-based to 0-based
        if 0 <= idx < len(repos) and s["score"] >= 4:
            r = repos[idx].copy()
            r["score"] = s["score"]
            r["reason"] = s["reason"]
            scored.append(r)

    scored.sort(key=lambda r: r["score"], reverse=True)
    print(f"[filter] AI scored {len(scores)} repos, {len(scored)} passed (>=4)")
    return scored


def filter_by_stars(repos: list[dict], top_n: int = 10) -> list[dict]:
    """Fallback: take top N repos by star count."""
    sorted_repos = sorted(repos, key=lambda r: r["stars"], reverse=True)[:top_n]
    for r in sorted_repos:
        r["score"] = 0
        r["reason"] = "Star排名自动入选（AI未评分）"
    return sorted_repos


def _parse_scores(content: str) -> list[dict]:
    """Parse AI response. Handle markdown code blocks if present."""
    content = content.strip()
    # Strip markdown code fences if AI wrapped it
    if content.startswith("```"):
        lines = content.split("\n")
        content = "\n".join(lines[1:]) if lines[0].startswith("```") else content
        if content.endswith("```"):
            content = content.rsplit("```", 1)[0]
    return json.loads(content)
```

- [ ] **Step 2: Verify syntax and imports**

```bash
cd D:/Projects/gh-trending-digest
python -c "from src.filter import filter_by_stars; print('filter module OK')"
```

- [ ] **Step 3: Commit**

```bash
git add src/filter.py
git commit -m "feat: add filter module with DeepSeek AI scoring and star fallback"
```

---

### Task 5: template.py — HTML Email Templates

**Files:**
- Create: `D:\Projects\gh-trending-digest\src\template.py`

**Interfaces:**
- Produces:
  - `build_daily_email(repos: list[dict], date_str: str) -> str` — HTML string
  - `build_weekly_email(repos: list[dict], date_str: str, stats: dict) -> str`
  - `build_monthly_email(repos: list[dict], date_str: str, stats: dict) -> str`

- [ ] **Step 1: Implement template.py**

```python
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
```

- [ ] **Step 2: Verify module**

```bash
cd D:/Projects/gh-trending-digest
python -c "
from src.template import build_daily_email
html = build_daily_email([{'full_name':'test/repo','html_url':'https://github.com/test/repo','description':'test','stars':100,'language':'Python','score':5,'reason':'good'}], '2026-07-22')
print(f'Generated {len(html)} chars of HTML')
assert 'test/repo' in html
print('OK')
"
```

- [ ] **Step 3: Commit**

```bash
git add src/template.py
git commit -m "feat: add HTML email templates for daily/weekly/monthly"
```

---

### Task 6: sender.py — QQ SMTP Sender

**Files:**
- Create: `D:\Projects\gh-trending-digest\src\sender.py`

**Interfaces:**
- Consumes: `config["qq_smtp_user"]`, `config["qq_smtp_pass"]`
- Produces: `send_email(html_content: str, subject: str, smtp_user: str, smtp_pass: str, to_addr: str = "") -> bool`

- [ ] **Step 1: Implement sender.py**

```python
"""Send HTML emails via QQ SMTP."""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header

SMTP_HOST = "smtp.qq.com"
SMTP_PORT = 465  # SSL


def send_email(
    html_content: str,
    subject: str,
    smtp_user: str,
    smtp_pass: str,
    to_addr: str = "",
) -> bool:
    """Send HTML email via QQ SMTP.
    
    Args:
        html_content: Full HTML email body
        subject: Email subject line
        smtp_user: QQ email address (also used as from_addr)
        smtp_pass: QQ SMTP authorization code (NOT QQ password)
        to_addr: Recipient address (defaults to smtp_user = send to self)
    
    Returns:
        True if sent successfully, False otherwise
    """
    if not smtp_user or not smtp_pass:
        print("[sender] Missing SMTP credentials, skipping send")
        return False

    to_addr = to_addr or smtp_user

    msg = MIMEMultipart("alternative")
    msg["Subject"] = Header(subject, "utf-8")
    msg["From"] = smtp_user
    msg["To"] = to_addr
    msg.attach(MIMEText(html_content, "html", "utf-8"))

    try:
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=15) as server:
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_user, [to_addr], msg.as_string())
        print(f"[sender] Email sent: {subject}")
        return True
    except smtplib.SMTPException as e:
        print(f"[sender] SMTP error: {e}")
        return False
    except OSError as e:
        print(f"[sender] Connection error: {e}")
        return False
```

- [ ] **Step 2: Verify syntax**

```bash
cd D:/Projects/gh-trending-digest
python -c "from src.sender import send_email; print('sender module OK')"
```

- [ ] **Step 3: Commit**

```bash
git add src/sender.py
git commit -m "feat: add sender module for QQ SMTP email delivery"
```

---

### Task 7: scripts/daily.py — Daily Digest Entry Point

**Files:**
- Create: `D:\Projects\gh-trending-digest\scripts\daily.py`

**Interfaces:**
- Consumes: all modules from Tasks 1-6
- Side effect: fetches, filters, sends email, updates store

- [ ] **Step 1: Implement daily.py**

```python
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

    status = "✅ sent" if ok else "⚠️ built but send failed"
    print(f"[daily] Done: {len(picks)} repos, {status}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Create scripts/__init__.py (empty)**

```bash
touch D:/Projects/gh-trending-digest/scripts/__init__.py
```

- [ ] **Step 3: Verify dry-run (will fail on SMTP without real creds, but shouldn't crash)**

```bash
cd D:/Projects/gh-trending-digest
python -c "
import os; os.environ['QQ_SMTP_USER']=''; os.environ['QQ_SMTP_PASS']=''
os.environ['DEEPSEEK_API_KEY']=''
from scripts.daily import main; main()
"
```
Expected: Runs without crashing (may print "No repos found" or "skipping send")

- [ ] **Step 4: Commit**

```bash
git add scripts/daily.py scripts/__init__.py
git commit -m "feat: add daily digest entry script"
```

---

### Task 8: scripts/weekly.py — Weekly Summary

**Files:**
- Create: `D:\Projects\gh-trending-digest\scripts\weekly.py`

- [ ] **Step 1: Implement weekly.py**

```python
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
```

- [ ] **Step 2: Verify syntax**

```bash
cd D:/Projects/gh-trending-digest
python -c "import ast; ast.parse(open('scripts/weekly.py').read()); print('OK')"
```

- [ ] **Step 3: Commit**

```bash
git add scripts/weekly.py
git commit -m "feat: add weekly summary entry script"
```

---

### Task 9: scripts/monthly.py — Monthly Report

**Files:**
- Create: `D:\Projects\gh-trending-digest\scripts\monthly.py`

- [ ] **Step 1: Implement monthly.py**

```python
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
```

- [ ] **Step 2: Verify syntax**

```bash
cd D:/Projects/gh-trending-digest
python -c "import ast; ast.parse(open('scripts/monthly.py').read()); print('OK')"
```

- [ ] **Step 3: Commit**

```bash
git add scripts/monthly.py
git commit -m "feat: add monthly report entry script"
```

---

### Task 10: GitHub Actions Workflows

**Files:**
- Create: `D:\Projects\gh-trending-digest\.github\workflows\daily.yml`
- Create: `D:\Projects\gh-trending-digest\.github\workflows\weekly.yml`
- Create: `D:\Projects\gh-trending-digest\.github\workflows\monthly.yml`

- [ ] **Step 1: Create daily.yml**

```yaml
name: Daily Digest

on:
  schedule:
    - cron: "0 1 * * *"  # UTC 1:00 = 北京时间 9:00
  workflow_dispatch:  # Manual trigger for testing

jobs:
  digest:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install deps
        run: pip install -r requirements.txt

      - name: Run daily digest
        env:
          GITHUB_TOKEN: ${{ secrets.GH_TOKEN }}
          DEEPSEEK_API_KEY: ${{ secrets.DEEPSEEK_API_KEY }}
          QQ_SMTP_USER: ${{ secrets.QQ_SMTP_USER }}
          QQ_SMTP_PASS: ${{ secrets.QQ_SMTP_PASS }}
        run: python scripts/daily.py

      - name: Commit updated data files
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add data/
          git diff --staged --quiet || git commit -m "data: update seen and history [skip ci]"
          git push
```

- [ ] **Step 2: Create weekly.yml**

```yaml
name: Weekly Digest

on:
  schedule:
    - cron: "0 1 * * 0"  # UTC 1:00 Sunday = 北京时间周日 9:00
  workflow_dispatch:

jobs:
  digest:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install deps
        run: pip install -r requirements.txt

      - name: Run weekly summary
        env:
          QQ_SMTP_USER: ${{ secrets.QQ_SMTP_USER }}
          QQ_SMTP_PASS: ${{ secrets.QQ_SMTP_PASS }}
        run: python scripts/weekly.py
```

- [ ] **Step 3: Create monthly.yml**

```yaml
name: Monthly Digest

on:
  schedule:
    - cron: "0 1 1 * *"  # UTC 1:00 on 1st = 北京时间每月1日 9:00
  workflow_dispatch:

jobs:
  digest:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install deps
        run: pip install -r requirements.txt

      - name: Run monthly report
        env:
          QQ_SMTP_USER: ${{ secrets.QQ_SMTP_USER }}
          QQ_SMTP_PASS: ${{ secrets.QQ_SMTP_PASS }}
        run: python scripts/monthly.py
```

- [ ] **Step 4: Commit**

```bash
git add .github/
git commit -m "feat: add GitHub Actions cron workflows for daily/weekly/monthly"
```

---

### Task 11: README & GitHub Setup

**Files:**
- Create: `D:\Projects\gh-trending-digest\README.md`

- [ ] **Step 1: Create README.md**

```markdown
# GitHub Trending Digest

定时推送 GitHub 好用的开源工具到 QQ 邮箱。

- **每日**：精选 5-10 个新项目，AI 打分筛选
- **每周（周日）**：本周 Top 10 总结
- **每月（1日）**：月度报告，语言分布

## 工作方式

GitHub Actions 定时触发 → 调 GitHub Search API 拉取 trending repo → DeepSeek AI 筛选 → QQ SMTP 发邮件

## 配置

在 GitHub 仓库 Settings → Secrets and variables → Actions 添加以下 Secrets：

| Secret | 说明 |
|--------|------|
| `GH_TOKEN` | GitHub Personal Access Token (可选) |
| `DEEPSEEK_API_KEY` | DeepSeek API Key |
| `QQ_SMTP_USER` | QQ 邮箱地址 |
| `QQ_SMTP_PASS` | QQ 邮箱 SMTP 授权码 |

## 本地运行

```bash
cp .env.example .env
# 编辑 .env 填入真实值
pip install -r requirements.txt
python scripts/daily.py
```

## 手动触发

GitHub Actions → 选择工作流 → Run workflow
```

- [ ] **Step 2: Final commit and push**

```bash
git add README.md
git commit -m "docs: add README with setup instructions"
```

---

## Plan Self-Review

**Spec coverage:**
- ✅ 3. Project structure → Tasks 1-10 implement all files
- ✅ 4.1 fetcher → Task 3
- ✅ 4.2 filter → Task 4
- ✅ 4.3 sender → Task 6
- ✅ 4.4 template → Task 5
- ✅ 4.5 store → Task 2
- ✅ 5. Cron strategy → Task 10
- ✅ 6. Config management → Task 1 (config.py) + Task 10 (GitHub Secrets)
- ✅ 7. Error handling → Every module has try/except with fallback
- ✅ 8. Non-functional → Single-file < 200 lines each, inline CSS, < 60s runtime

**Placeholder scan:** No TBD, TODO, or vague descriptions found.

**Type consistency:**
- `get_config() -> dict` — used across all entry scripts ✓
- `fetch_trending(date_since: str, token: str) -> list[dict]` — consumed by daily.py ✓
- `filter_with_ai(repos: list[dict], api_key: str) -> list[dict]` — consumed by daily.py ✓
- `send_email(html: str, subject: str, user: str, pass: str, to: str) -> bool` — consumed by all scripts ✓
- `build_daily_email(repos: list[dict], date: str) -> str` — consumed by daily.py ✓
- `mark_seen(repo_id: int, score: int, source: str) -> None` — consumed by daily.py ✓
- `get_history_for_period(days: int) -> list[dict]` — consumed by weekly/monthly ✓
