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
