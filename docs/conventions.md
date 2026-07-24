# 技能仓库约定

本文件是 `why_skills` 的结构与维护规则单一来源。README 面向使用者，AGENTS.md 只保留 Agent 必须立即遵守的约束；两者不重复本文件的细则。

## 分类与路径

所有技能使用 `skills/<category>/<skill-name>/` 两层目录。

| 分类 | 范围 |
|---|---|
| `ads` | Keysight ADS 的安装、环境、网表、仿真和后处理 |
| `eda-integration` | EDA GUI、CLI、MCP、IPC 与跨工具集成 |
| `engineering-practice` | 研究、调试、测试等通用工程方法 |
| `knowledge` | RAG MCP、帮助文档、代码/API 文档检索 |
| `document-processing` | PDF、HTML、Markdown 等内容抽取与转换 |
| `project-documentation` | 项目文档约定、站点和发布流程 |
| `project-planning` | 新工程的需求访谈、领域术语和架构决策 |

按主要使用场景分类。跨分类技能只保留一份，并在 README 中标明关联工作流。

## 技能规范

1. 目录名使用小写 kebab-case，且必须与 `SKILL.md` frontmatter 的 `name` 一致。
2. `description` 必须同时说明能力和触发条件；正文只保留执行时需要的流程和护栏。
3. 长资料放在 `references/`，可重复且需确定性的操作放在 `scripts/`，模板放在 `templates/` 或 `assets/`。
4. 新增或修改脚本后要实际运行代表性检查。不得提交二进制、下载缓存、向量索引或仿真结果。
5. EDA 专有语法或版本差异要以用户有权访问的对应版本文档为准；不得猜测命令或规避许可证控制。
6. 引入外部技能时，复制完整的技能目录与其所需资源，记录来源和许可证；不要只复制 `SKILL.md` 而遗漏模板、脚本或 `agents/` 配置。

## 结构变更清单

移动、重命名、添加或删除技能时：

1. 检查目录名、frontmatter `name` 和 `agents/openai.yaml` 默认提示是否仍一致。
2. 检查 `SKILL.md` 的相对链接、示例命令及脚本路径。
3. 同步更新根目录 `README.md` 的技能索引与工作流说明。
4. 运行技能结构校验；若没有统一校验器，至少确认每个 `SKILL.md` 含有效 YAML frontmatter、`name` 和 `description`。
5. 用 `git status --short` 确认重组仅包含预期文件，且没有误触用户未跟踪内容。

## 忽略规则

本仓库只保存可复用的技能源文件。`.gitignore` 必须忽略：Python 环境与缓存、日志与仿真数据集、可再生成的 RAG 索引、许可证、PDK、受限文档和本机绝对路径配置。
