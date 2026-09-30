---
name: ask-why
description: Route a situation to the smallest useful skill or workflow in why_skills.
disable-model-invocation: true
---

# Ask Why

这是 `why_skills` 的人工入口。用户不需要记住所有 Skill；只需要描述当前处境，由本 Skill 指出最小可用路线。

## Process

1. 读取仓库根 `README.md` 的当前技能索引。不要依赖记忆中的旧清单。
2. 用用户的**目标和当前状态**判断意图，而不是先按目录分类。
3. 如果候选不唯一，只读取最相关 Skill 的 frontmatter / 开头部分来区分调用边界。
4. 给出一个主路线；只有确实存在后续阶段时才给下一步。
5. 本 Skill 默认只路由，不修改文件、不复制其他 Skill 的正文。

## Common routes

- **不知道该用哪个 Skill** → 从 README 当前索引中选择最小匹配项。
- **ADS 原理图 / 网表仿真、指标评估或受限优化** → `ads-netlist-simulation`。
- **ADS 安装、许可证或多版本环境** → 根据操作系统和版本选择对应 ADS 配置 Skill。
- **EDA GUI 与 CLI / MCP / 原生脚本通信** → `eda-gui-async-bridge`。
- **难定位的脚本、环境或仿真故障** → `diagnosing-bugs`。
- **需要基于一手资料调查技术问题** → `research`。
- **PDF / Markdown 转换** → 先区分是否需要 Marker 的版面能力，再在文档处理 Skill 中选择。
- **从资料构建本地 RAG MCP** → `rag-mcp-builder`。
- **新项目需求还不清楚** → `grill-with-docs`；无工作目录时可用 `grill-me`。
- **本轮工作有值得长期复用的经验，想“沉淀 / 固化”** → 告诉用户运行 `distill`。
- **Skill 库开始重复、混乱、索引漂移或想做体检** → 告诉用户运行 `maintain-skills`。

## Output

保持简短，格式优先为：

```text
建议入口：<skill>

原因：<为什么它的调用边界最匹配>

后续（可选）：<只有确有下一阶段时才给>
```

如果没有现成 Skill，明确说“当前没有直接匹配项”，再判断是直接完成任务，还是在任务完成并验证后通过 `distill` 评估是否值得新增。不要因为“没有 Skill”就立即创建 Skill。
