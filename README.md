# why_skills

我的 Cursor Agent Skills 个人仓库，用于跨机器同步和持续积累 Agent 能力。

## 使用方式

克隆到本地后，在 Cursor 中配置 skill 路径指向对应的 `SKILL.md` 即可。

```bash
git clone https://github.com/why250/why_skills.git
```

## Skill 列表

| Skill | 说明 |
|-------|------|
| [rag-mcp-builder](./rag-mcp-builder/SKILL.md) | 从任意知识库构建本地 RAG MCP 服务（ChromaDB + BM25 + RRF 融合），支持 HTML 文档、Python 包、纯文本、代码示例 |
| [ads-venv-setup](./ads-venv-setup/SKILL.md) | ADS 2025 Python 虚拟环境配置，ADS2025 Python 文件夹可从 Release 下载解压 |

## 日常工作流

```bash
# 拉取最新 skill
git pull

# 本地写完新 skill 后上传
git add .
git commit -m "add: 新skill名称"
git push
```
