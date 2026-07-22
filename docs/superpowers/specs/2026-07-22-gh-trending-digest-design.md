# GitHub Trending Digest — 设计文档

**日期：** 2026-07-22
**状态：** 待审核

---

## 1. 项目目标

定时推送 GitHub 上最新好用的工具/项目到 QQ 邮箱。每日推送新项目，每周日发送周总结，每月1日发送月度报告。

## 2. 技术选型

| 组件 | 选择 | 理由 |
|------|------|------|
| 语言 | Python 3.11+ | requests+smtplib 内置，零重型依赖 |
| 数据源 | GitHub Search API | 官方 API，无需爬虫，稳定 |
| AI 筛选 | DeepSeek API (Chat) | 便宜（¥1/百万token），中文理解好 |
| 邮件 | QQ SMTP (SSL) | smtp.qq.com:465，用户已有授权码 |
| 存储 | JSON 文件 | 轻量，Git 版本控制自带备份 |
| 调度 | GitHub Actions cron | 免费，无需服务器 |

## 3. 项目结构

```
gh-trending-digest/
├── .github/workflows/
│   ├── daily.yml          # cron: 0 9 * * *
│   ├── weekly.yml         # cron: 0 10 * * 0
│   └── monthly.yml        # cron: 0 10 1 * *
├── src/
│   ├── fetcher.py          # GitHub Search API 调用
│   ├── filter.py           # DeepSeek AI 打分筛选
│   ├── sender.py           # QQ SMTP 发送 HTML 邮件
│   ├── template.py         # HTML 邮件模板生成
│   └── store.py            # JSON 读写 + 去重 + 历史
├── scripts/
│   ├── daily.py            # 每日推送入口
│   ├── weekly.py           # 每周总结入口
│   └── monthly.py          # 月度报告入口
├── data/
│   ├── seen.json           # { "repo_id": { "score": 4, "pushed_at": "..." } }
│   └── history.json        # [{ "date": "...", "repos": [...], "type": "daily" }]
├── requirements.txt
├── config.py               # 环境变量读取，本地 .env 支持
└── README.md
```

## 4. 核心模块设计

### 4.1 fetcher.py — 数据获取

调用 GitHub Search API：
```
GET /search/repositories
  ?q=created:>{date} stars:>10
  &sort=stars
  &order=desc
  &per_page=30
```

- 认证：`GITHUB_TOKEN` 环境变量（可选，不加限速 60次/h，加了 5000次/h）
- 返回结构化数据：`[{id, full_name, description, html_url, stars, language, topics, created_at}]`
- 重试逻辑：3 次，指数退避 1s/2s/4s
- 异常时返回空列表，不崩溃

### 4.2 filter.py — AI 筛选

调用 DeepSeek API：
- 模型：`deepseek-chat`
- Prompt：输入 30 个 repo 列表，要求对每个打分（1-5）+ 一行中文推荐理由，返回 JSON
- 筛选：≥4 分入选，预计每日 5-10 个
- 入参去重：先和 `seen.json` 比对，已推送的不再送 AI
- Token 估算：~5000 input + ~1000 output，每次不到 1 分钱
- 失败降级：AI API 挂了就用 star 数排序取 top 10，不筛

### 4.3 sender.py — 邮件发送

- SMTP：`smtp.qq.com:465`，SSL 加密
- 认证：`QQ_SMTP_USER` / `QQ_SMTP_PASS` 环境变量
- 内容类型：`text/html; charset=utf-8`
- 发送失败：写 error.log，不中断流程

### 4.4 template.py — HTML 模板

每日邮件结构：
- 标题：🚀 GitHub 每日精选 — YYYY-MM-DD
- 每条 repo：序号 + 名称 + star 数 + AI 推荐理由 + 链接
- 底部：推送数量统计 + 退订提示

每周/月总结：
- 本周/月 top 10 排行
- 新增 repo 数量统计
- 技术语言分布

### 4.5 store.py — 数据存储

- `seen.json`：`{repo_id: {score, pushed_at, source}}` — 去重库，简单 dict
- `history.json`：`[{date, type, repos: [...]}]` — 推送历史，供周/月总结读取
- 读写加文件锁防并发（GitHub Actions 理论上不会并发，但防患）

## 5. 定时策略

| 工作流 | Cron | 做什么 |
|--------|------|--------|
| daily.yml | `0 1 * * *` (北京时间 9:00) | 拉昨日新建 repo → AI筛 → 发邮件 |
| weekly.yml | `0 1 * * 0` (北京时间周日 9:00) | 读本周 history → 生成总结 → 发邮件 |
| monthly.yml | `0 1 1 * *` (北京时间每月1日 9:00) | 读本月 history → 生成月度报告 → 发邮件 |

注意：GitHub Actions cron 是 UTC 时间，北京时间 = UTC+8。北京时间 9:00 = UTC 1:00。

## 6. 配置管理

所有配置走环境变量，通过 GitHub Secrets 注入：

| 变量 | 说明 | 必需 |
|------|------|------|
| `GITHUB_TOKEN` | GitHub Personal Access Token | 否（但建议） |
| `DEEPSEEK_API_KEY` | DeepSeek API Key | 是 |
| `QQ_SMTP_USER` | QQ 邮箱地址 | 是 |
| `QQ_SMTP_PASS` | QQ 邮箱 SMTP 授权码 | 是 |

本地开发用 `.env` 文件（.gitignore 排除）。

## 7. 错误处理

| 场景 | 策略 |
|------|------|
| GitHub API 限速/故障 | 重试 3 次，仍失败则跳过当日推送 |
| DeepSeek API 故障 | 降级为纯 star 排序，不 AI 筛选 |
| QQ SMTP 发送失败 | 记录日志，GitHub Actions 显示警告 |
| data/ 目录不存在 | 自动创建 |
| JSON 文件损坏 | 备份 + 重置 |

核心原则：**部分失败不阻塞**。宁可少发一条，不发空内容、不发重复内容。

## 8. 非功能需求

- 每次运行 < 60 秒（GitHub Actions 免费额度充裕）
- 单文件 < 200 行（保持可维护）
- AI 调用单次覆盖 30 个 repo，不逐条调用
- HTML 邮件内联 CSS，不依赖外部资源

## 9. 后续扩展（不做，仅记录）

- 支持多邮箱订阅
- Web 端查看历史推送
- 按 topic 分类过滤
- Slack/钉钉/飞书推送渠道
- GitHub Trending 爬虫作为补充数据源
