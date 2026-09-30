# 技能仓库约定

本文件是 `why_skills` 的结构与维护规则单一来源。README 面向使用者，AGENTS.md 只保留 Agent 必须立即遵守的约束；两者不重复本文件的细则。Skill 的“路由 → 使用 → 沉淀 → 验证 → 维护”流程见 [skill-lifecycle.md](skill-lifecycle.md)。

## 分类与路径

标准技能使用 `skills/<category>/<skill-name>/` 两层目录。历史遗留的顶层 Skill 属于维护债务，可以在保持路径稳定的前提下择机迁移，但不得作为新增 Skill 的先例。

| 分类 | 范围 |
|---|---|
| `skill-management` | Skill 库自身的路由、沉淀、验证与维护 |
| `ads` | Keysight ADS 的安装、环境、网表、仿真和后处理 |
| `eda-integration` | EDA GUI、CLI、MCP、IPC 与跨工具集成 |
| `engineering-practice` | 研究、调试、测试等通用工程方法 |
| `knowledge` | RAG MCP、帮助文档、代码/API 文档检索 |
| `document-processing` | PDF、HTML、Markdown 等内容抽取与转换 |
| `project-documentation` | 项目文档约定、站点和发布流程 |
| `project-planning` | 新工程的需求访谈、领域术语和架构决策 |

按主要使用场景分类。跨分类技能只保留一份，并在 README 或 Router 工作流中标明关联关系。

## 技能规范

1. 目录名使用小写 kebab-case，且必须与 `SKILL.md` frontmatter 的 `name` 一致。
2. `description` 必须说明能力和触发条件；user-invoked Skill 可使用简短的人类可读摘要，正文只保留执行时需要的流程和护栏。
3. 长资料放在 `references/`，可重复且需确定性的操作放在 `scripts/`，模板放在 `templates/` 或 `assets/`。
4. 新增或修改脚本后要实际运行代表性检查。不得提交二进制、下载缓存、向量索引或仿真结果。
5. EDA 专有语法或版本差异要以用户有权访问的对应版本文档为准；不得猜测命令或规避许可证控制。
6. 引入外部技能时，复制完整的技能目录与其所需资源，记录来源和许可证；不要只复制 `SKILL.md` 而遗漏模板、脚本或 `agents/` 配置。
7. 新建 Skill 前必须查找相近触发条件；若已有 Skill 能吸收该经验，优先更新，不建立平行权威来源。
8. user-invoked Skill 的宿主配置应保持一致：例如 Claude/Codex 同时禁止隐式调用；model-invoked Skill 的 description 应包含足够的触发信息。

## Skill 生命周期

职责边界：

- `ask-why` 负责路由，不修改库内容；
- `distill` 负责从已验证经验中判断更新、新建或不沉淀；
- `maintain-skills` 负责全库审计，默认先报告后修改；
- validator 负责机械一致性，不做语义 merge / split 决策。

详细判断标准见 [skill-lifecycle.md](skill-lifecycle.md)。

## 结构变更清单

移动、重命名、添加或删除技能时：

1. 检查目录名、frontmatter `name` 和 `agents/openai.yaml` 调用策略是否仍一致。
2. 检查 `SKILL.md` 的相对链接、示例命令及脚本路径。
3. 同步更新根目录 `README.md` 的技能索引与工作流说明。
4. 运行：

   ```bash
   python skills/skill-management/maintain-skills/scripts/validate_skills.py
   ```

5. 对 validator 的 warning 做人工判断；warning 不等于必须修改。
6. 用 `git status --short` 确认重组仅包含预期文件，且没有误触用户未跟踪内容。

## 维护原则

- 机械错误用 validator 或脚本解决，避免把确定性检查写成长篇提示词。
- 合并两个 Skill 前需要证明调用边界和核心流程实质重叠；名称相似不足以作为依据。
- 拆分 Skill 只有在产生独立调用边界、减少上下文负担或显著改善维护性时才值得。
- 移动、重命名和删除优先考虑路径稳定性；必要时在 PR 中明确迁移影响。
- Maintainer 默认输出审计报告；大范围自动重构必须有用户明确授权。

## 忽略规则

本仓库只保存可复用的技能源文件。`.gitignore` 必须忽略：Python 环境与缓存、日志与仿真数据集、可再生成的 RAG 索引、许可证、PDK、受限文档和本机绝对路径配置。
