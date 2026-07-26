"""GitHub 智能搜索 Web 应用。

启动: python web/app.py
打开: http://localhost:5000
"""

import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import requests
from flask import Flask, render_template_string, request, jsonify
from config import get_config

app = Flask(__name__)

DEEPSEEK_API = "https://api.deepseek.com/chat/completions"
GITHUB_API = "https://api.github.com/search/repositories"

# ── HTML 模板 ───────────────────────────────────────────

HTML = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>GitHub 智能搜索</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#0d1117;color:#c9d1d9;min-height:100vh}
.container{max-width:800px;margin:0 auto;padding:40px 20px}
h1{font-size:32px;color:#f0f6fc;text-align:center;margin-bottom:8px}
.sub{text-align:center;color:#8b949e;margin-bottom:32px;font-size:14px}
.search-box{display:flex;gap:10px;margin-bottom:8px}
.search-box input{flex:1;padding:14px 18px;border-radius:8px;border:1px solid #30363d;background:#161b22;color:#c9d1d9;font-size:16px;outline:none;transition:border-color .2s}
.search-box input:focus{border-color:#58a6ff}
.search-box input::placeholder{color:#484f58}
.search-box button{padding:14px 28px;border-radius:8px;border:none;background:#238636;color:#fff;font-size:16px;font-weight:600;cursor:pointer;transition:background .2s;white-space:nowrap}
.search-box button:hover{background:#2ea043}
.search-box button:disabled{background:#21262d;color:#484f58;cursor:not-allowed}
.hint{color:#484f58;font-size:12px;margin-bottom:24px}
.examples{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:32px}
.examples span{background:#21262d;color:#8b949e;padding:6px 14px;border-radius:16px;font-size:13px;cursor:pointer;transition:all .2s;border:1px solid #30363d}
.examples span:hover{background:#30363d;color:#f0f6fc;border-color:#58a6ff}
.meta{text-align:center;margin-bottom:24px;color:#8b949e;font-size:13px}
.meta strong{color:#f0f6fc}
.result{border:1px solid #21262d;border-radius:8px;padding:20px;margin-bottom:12px;background:#161b22;transition:border-color .2s}
.result:hover{border-color:#30363d}
.result h3{margin-bottom:4px;font-size:18px}
.result h3 a{color:#58a6ff;text-decoration:none}
.result h3 a:hover{text-decoration:underline}
.result .url{color:#8b949e;font-size:12px;margin-bottom:8px;word-break:break-all}
.result .reason{color:#c9d1d9;font-size:14px;line-height:1.5;margin-bottom:8px}
.result .tags{display:flex;gap:8px;flex-wrap:wrap}
.result .tag{font-size:11px;padding:2px 10px;border-radius:12px;background:#21262d;color:#8b949e}
.result .tag.stars{background:#1f2d1f;color:#7ee787}
.result .tag.score{background:#1f1a33;color:#d2a8ff}
.result .tag.lang{background:#1a2333;color:#79c0ff}
.loading{text-align:center;padding:60px 0;color:#8b949e}
.spinner{display:inline-block;width:32px;height:32px;border:3px solid #21262d;border-top-color:#58a6ff;border-radius:50%;animation:spin .8s linear infinite;margin-bottom:12px}
@keyframes spin{to{transform:rotate(360deg)}}
.error{text-align:center;padding:40px;color:#f85149;background:#161b22;border:1px solid #30363d;border-radius:8px}
.empty{text-align:center;padding:40px;color:#8b949e}
footer{text-align:center;padding:40px 0;color:#484f58;font-size:12px}
footer a{color:#58a6ff}
</style>
</head>
<body>
<div class="container">
  <h1>&#x1F50D; GitHub &#x667A;&#x80FD;&#x641C;&#x7D22;</h1>
  <p class="sub">&#x7528;&#x81EA;&#x7136;&#x8BED;&#x8A00;&#x63CF;&#x8FF0;&#xFF0C;AI &#x5E2E;&#x4F60;&#x627E;&#x5230;&#x6700;&#x5339;&#x914D;&#x7684;&#x5F00;&#x6E90;&#x9879;&#x76EE;</p>

  <div class="search-box">
    <input type="text" id="query" placeholder="&#x4F8B;&#x5982;&#xFF1A;&#x597D;&#x7528;&#x7684;&#x7EC8;&#x7AEF;&#x6587;&#x4EF6;&#x7BA1;&#x7406;&#x5668;..." autofocus>
    <button id="btn" onclick="search()">&#x641C;&#x7D22;</button>
  </div>
  <p class="hint">&#x2003;&#x7528; DeepSeek AI &#x8F6C;&#x5316;&#x4E3A;&#x5173;&#x952E;&#x8BCD;&#xFF0C;&#x641C; GitHub &#x540E;&#x518D;&#x7528; AI &#x91CD;&#x6392;&#x7ED3;&#x679C;</p>

  <div class="examples">
    <span onclick="searchFor('&#x7EC8;&#x7AEF;&#x6587;&#x4EF6;&#x7BA1;&#x7406;&#x5668;')">&#x7EC8;&#x7AEF;&#x6587;&#x4EF6;&#x7BA1;&#x7406;&#x5668;</span>
    <span onclick="searchFor('Python &#x5F02;&#x6B65; HTTP &#x6846;&#x67B6;')">Python &#x5F02;&#x6B65; HTTP &#x6846;&#x67B6;</span>
    <span onclick="searchFor('CLI JSON &#x5904;&#x7406;&#x5DE5;&#x5177;')">CLI JSON &#x5904;&#x7406;&#x5DE5;&#x5177;</span>
    <span onclick="searchFor('&#x6570;&#x636E;&#x53EF;&#x89C6;&#x5316;&#x56FE;&#x8868;&#x5E93;')">&#x6570;&#x636E;&#x53EF;&#x89C6;&#x5316;&#x56FE;&#x8868;&#x5E93;</span>
    <span onclick="searchFor('&#x8F7B;&#x91CF;&#x7EA7; markdown &#x7F16;&#x8F91;&#x5668;')">&#x8F7B;&#x91CF;&#x7EA7; Markdown &#x7F16;&#x8F91;&#x5668;</span>
  </div>

  <div id="meta" class="meta" style="display:none"></div>
  <div id="results"></div>

  <footer>
    &#x6570;&#x636E;&#x6765;&#x6E90;&#xFF1A;<a href="https://github.com">GitHub</a> |
    AI &#x9A71;&#x52A8;&#xFF1A;<a href="https://deepseek.com">DeepSeek</a> |
    <a href="https://github.com/sky-k111/gh-trending-digest">&#x9879;&#x76EE;&#x4ED3;&#x5E93;</a>
  </footer>
</div>

<script>
async function search() {
  const q = document.getElementById('query').value.trim()
  if (!q) return
  searchFor(q)
}

async function searchFor(q) {
  document.getElementById('query').value = q
  const btn = document.getElementById('btn')
  const meta = document.getElementById('meta')
  const results = document.getElementById('results')

  btn.disabled = true
  btn.textContent = '搜索中...'
  meta.style.display = 'none'
  results.innerHTML = '<div class="loading"><div class="spinner"></div><p>AI 分析中...</p></div>'

  try {
    const resp = await fetch(`/api/search?q=${encodeURIComponent(q)}`)
    const data = await resp.json()

    if (data.error) {
      results.innerHTML = `<div class="error">${data.error}</div>`
      return
    }

    meta.style.display = ''
    meta.innerHTML = `&#x641C;&#x7D22;&#x5173;&#x952E;&#x8BCD;&#xFF1A;<strong>${data.keywords}</strong> &#x00B7; &#x627E;&#x5230; <strong>${data.total}</strong> &#x4E2A;&#x7ED3;&#x679C;`

    if (!data.results.length) {
      results.innerHTML = '<div class="empty">&#x6CA1;&#x627E;&#x5230;&#x5339;&#x914D;&#x7684;&#x9879;&#x76EE; &#x1F3C4;</div>'
      return
    }

    results.innerHTML = data.results.map((r, i) => `
      <div class="result">
        <h3><a href="${r.html_url}" target="_blank">${i + 1}. ${r.full_name}</a></h3>
        <div class="url">${r.html_url}</div>
        <div class="reason">${r.reason || r.description || ''}</div>
        <div class="tags">
          ${r.stars ? `<span class="tag stars">&#x2B50; ${r.stars.toLocaleString()}</span>` : ''}
          ${r.language ? `<span class="tag lang">&#x1F527; ${r.language}</span>` : ''}
          ${r.score ? `<span class="tag score">&#x1F3AF; ${r.score}/5</span>` : ''}
        </div>
      </div>
    `).join('')

  } catch(e) {
    results.innerHTML = `<div class="error">&#x7F51;&#x7EDC;&#x9519;&#x8BEF;&#xFF1A;${e.message}</div>`
  } finally {
    btn.disabled = false
    btn.textContent = '搜索'
  }
}

document.getElementById('query').addEventListener('keydown', e => {
  if (e.key === 'Enter') search()
})
</script>
</body>
</html>"""


# ── 搜索逻辑 ───────────────────────────────────────────

def extract_keywords(query: str, api_key: str) -> str:
    prompt = f"""把用户的自然语言需求转成 GitHub 搜索关键词（英文）。

规则：
- 提取核心技术关键词，用空格分隔，最多 6 个词
- 排除"好用的""推荐""工具""项目"等修饰词
- 如果用户用中文，转到对应英文技术术语

只返回关键词，不要其他文字。

用户需求：{query}
关键词："""

    resp = requests.post(
        DEEPSEEK_API,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={"model": "deepseek-chat", "messages": [{"role": "user", "content": prompt}], "temperature": 0.1, "max_tokens": 50},
        timeout=15,
    )
    if resp.status_code != 200:
        raise Exception(f"DeepSeek API 错误: {resp.status_code}")
    return resp.json()["choices"][0]["message"]["content"].strip()


def search_github(keywords: str, github_token: str) -> list[dict]:
    headers = {"Accept": "application/vnd.github+json"}
    if github_token:
        headers["Authorization"] = f"Bearer {github_token}"

    resp = requests.get(
        GITHUB_API, headers=headers,
        params={"q": keywords, "sort": "stars", "order": "desc", "per_page": 20},
        timeout=15,
    )
    if resp.status_code != 200:
        raise Exception(f"GitHub API 错误: {resp.status_code}")

    return [
        {"id": item["id"], "full_name": item["full_name"],
         "description": item.get("description") or "",
         "html_url": item["html_url"], "stars": item["stargazers_count"],
         "language": item.get("language") or "", "topics": item.get("topics", [])[:5]}
        for item in resp.json().get("items", [])
    ]


def rank_results(query: str, repos: list[dict], api_key: str) -> list[dict]:
    if not repos:
        return []

    repo_text = "\n\n".join(
        f"{i}. [{r['full_name']}]({r['html_url']})\n"
        f"   ⭐ {r['stars']:,} | 🔧 {r['language']}\n"
        f"   描述: {r['description'][:300] or '无'}\n"
        f"   Topics: {', '.join(r['topics']) or '无'}"
        for i, r in enumerate(repos, 1)
    )

    prompt = f"""用户想找："{query}"

以下是 GitHub 搜索结果（{len(repos)} 个项目）：

{repo_text}

---
请按与用户需求的相关度排序，给每个项目打分（1-5，5=完美匹配）+ 一句中文说明。

只返回 JSON 数组，不要 markdown 标记、不要其他文字：
[
  {{"index": 1, "score": 5, "reason": "完美匹配你的需求，原因是..."}},
  ...
]"""

    resp = requests.post(
        DEEPSEEK_API,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={"model": "deepseek-chat", "messages": [{"role": "user", "content": prompt}], "temperature": 0.3, "max_tokens": 3000},
        timeout=30,
    )
    if resp.status_code != 200:
        raise Exception(f"DeepSeek 排序错误: {resp.status_code}")

    content = resp.json()["choices"][0]["message"]["content"].strip()
    if content.startswith("```"):
        content = "\n".join(content.split("\n")[1:])
    if content.endswith("```"):
        content = content.rsplit("```", 1)[0]

    scores = json.loads(content)
    result = []
    for s in scores:
        idx = s["index"] - 1
        if 0 <= idx < len(repos):
            r = repos[idx].copy()
            r["score"] = s["score"]
            r["reason"] = s["reason"]
            result.append(r)
    result.sort(key=lambda r: r.get("score", 0), reverse=True)
    return result


# ── 路由 ────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template_string(HTML)


@app.route("/api/search")
def api_search():
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify({"error": "请输入搜索内容"}), 400

    cfg = get_config()
    if not cfg["deepseek_api_key"]:
        return jsonify({"error": "服务端未配置 DEEPSEEK_API_KEY"}), 500

    try:
        keywords = extract_keywords(q, cfg["deepseek_api_key"])
        repos = search_github(keywords, cfg["github_token"])
        ranked = rank_results(q, repos, cfg["deepseek_api_key"])
        return jsonify({"keywords": keywords, "total": len(ranked), "results": ranked})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    print("\n  GitHub 智能搜索 已启动")
    print("  打开浏览器访问: http://localhost:5000\n")
    app.run(debug=False, host="127.0.0.1", port=5000)
