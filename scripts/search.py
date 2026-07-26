"""GitHub 智能搜索 — 自然语言输入，AI 帮你找工具。

用法：python scripts/search.py "你想找的东西"
示例：python scripts/search.py "好用的终端文件管理器"
"""

import sys
import os
import json
import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import get_config

DEEPSEEK_API = "https://api.deepseek.com/chat/completions"
GITHUB_API = "https://api.github.com/search/repositories"


def extract_keywords(query: str, api_key: str) -> str:
    """用 DeepSeek 把自然语言转成 GitHub 搜索关键词。"""
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
        print(f"[search] DeepSeek 关键词提取失败: {resp.status_code}")
        return query

    keywords = resp.json()["choices"][0]["message"]["content"].strip()
    print(f"🔍 搜索关键词: {keywords}\n")
    return keywords


def search_github(keywords: str, github_token: str) -> list[dict]:
    """调 GitHub Search API 搜索仓库。"""
    headers = {"Accept": "application/vnd.github+json"}
    if github_token:
        headers["Authorization"] = f"Bearer {github_token}"

    resp = requests.get(
        GITHUB_API,
        headers=headers,
        params={"q": keywords, "sort": "stars", "order": "desc", "per_page": 15},
        timeout=15,
    )

    if resp.status_code != 200:
        print(f"[search] GitHub API 错误: {resp.status_code} {resp.text[:200]}")
        return []

    return [
        {
            "id": item["id"],
            "full_name": item["full_name"],
            "description": item.get("description") or "",
            "html_url": item["html_url"],
            "stars": item["stargazers_count"],
            "language": item.get("language") or "?",
            "topics": item.get("topics", [])[:5],
        }
        for item in resp.json().get("items", [])
    ]


def rank_results(query: str, repos: list[dict], api_key: str) -> list[dict]:
    """用 DeepSeek 重排结果，给每个仓库写中文推荐理由。"""
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
        json={"model": "deepseek-chat", "messages": [{"role": "user", "content": prompt}], "temperature": 0.3, "max_tokens": 2000},
        timeout=30,
    )

    if resp.status_code != 200:
        print(f"[search] DeepSeek 排序失败: {resp.status_code}")
        return repos

    content = resp.json()["choices"][0]["message"]["content"].strip()
    if content.startswith("```"):
        content = "\n".join(content.split("\n")[1:])
    if content.endswith("```"):
        content = content.rsplit("```", 1)[0]

    try:
        scores = json.loads(content)
    except json.JSONDecodeError:
        print("[search] AI 返回格式异常，用原始排序")
        return repos

    # Merge scores back
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


def main():
    if len(sys.argv) < 2:
        print("用法: python scripts/search.py \"你想找的东西\"")
        print("示例: python scripts/search.py \"好用的终端文件管理器\"")
        sys.exit(1)

    query = " ".join(sys.argv[1:])
    cfg = get_config()

    if not cfg["deepseek_api_key"]:
        print("❌ 需要 DEEPSEEK_API_KEY")
        sys.exit(1)

    print(f"\n{'='*60}")
    print(f"  GitHub 智能搜索")
    print(f"  搜索: {query}")
    print(f"{'='*60}\n")

    # Step 1: 提取关键词
    keywords = extract_keywords(query, cfg["deepseek_api_key"])

    # Step 2: 搜索
    repos = search_github(keywords, cfg["github_token"])
    if not repos:
        print("❌ 没搜到结果")
        sys.exit(0)

    print(f"✅ 找到 {len(repos)} 个相关仓库\n")

    # Step 3: AI 重排
    ranked = rank_results(query, repos, cfg["deepseek_api_key"])

    # Step 4: 输出
    print(f"{'='*60}")
    print(f"  📊 分析结果")
    print(f"{'='*60}\n")

    for i, r in enumerate(ranked, 1):
        stars = f"⭐ {r['stars']:,}" if r["stars"] else ""
        lang = f"🔧 {r['language']}"
        score = f"🎯 {r.get('score', '?')}/5" if r.get("score") else ""

        print(f"{i}. {r['full_name']}")
        print(f"   {r['html_url']}")
        print(f"   {stars}  {lang}  {score}")
        if r.get("reason"):
            print(f"   💬 {r['reason']}")
        if r.get("description") and r.get("description") != r.get("reason", ""):
            desc = r["description"][:150]
            print(f"   📝 {desc}")
        print()


if __name__ == "__main__":
    main()
