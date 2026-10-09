# why_skills

面向模拟 IC 工作流的个人 Agent Skills 仓库。这里收集可复用的 ADS、EDA 自动化、RAG 检索、文档处理与工程方法，并用“路由 → 使用 → 沉淀 → 验证 → 维护”的生命周期持续演化，供 Cursor、Codex 等兼容 Agent Skills 的工具使用。

## 仓库结构

```text
why_skills/
├── README.md                 # 人类入口与完整技能索引
├── AGENTS.md                 # Agent 修改本仓库时必须遵守的约定
├── docs/
│   ├── conventions.md        # 技能分类、命名、验证与维护规范
│   └── skill-lifecycle.md    # 路由、沉淀、验证、维护的生命周期
└── skills/
    ├── skill-management/     # Skill 库自身的路由、沉淀与维护
    ├── ads/                  # ADS 安装、Python 环境、网表仿真
    ├── eda-integration/      # EDA GUI 与 CLI/MCP 的集成模式
    ├── engineering-practice/ # 研究与故障诊断方法
    ├── knowledge/            # 本地 RAG MCP 与知识检索
    ├── document-processing/  # PDF/Markdown 文档转换
    ├── project-documentation/# 项目文档结构、发布与技能编写
    └── project-planning/     # 新工程需求澄清、术语与 ADR
```

每个标准技能目录以 `skills/<category>/<skill-name>/SKILL.md` 为入口。配置 Agent 时，按所用工具支持的 Skills 搜索路径配置，并通过下表定位所需的具体技能目录。

不知道该用哪个 Skill 时，从 [ask-why](./skills/skill-management/ask-why/SKILL.md) 开始；想把本轮经验长期保存时用 [distill](./skills/skill-management/distill/SKILL.md)；Skill 库出现重复、漂移或需要体检时用 [maintain-skills](./skills/skill-management/maintain-skills/SKILL.md)。

## 技能索引

| 分类 | Skill | 说明 |
|---|---|---|
| Skill 管理 | [ask-why](./skills/skill-management/ask-why/SKILL.md) | 根据当前处境找到最小可用 Skill 或工作流，避免依赖记忆所有 Skill 名称 |
| Skill 管理 | [distill](./skills/skill-management/distill/SKILL.md) | 从当前对话提炼可复用经验，查重后路由到 skill、代码、规则、文档、ADR 或 memory |
| Skill 管理 | [maintain-skills](./skills/skill-management/maintain-skills/SKILL.md) | 审计 Skill 库的重复、漂移、过时内容、索引和调用边界 |
| ADS | [ads-netlist-simulation](./skills/ads/ads-netlist-simulation/SKILL.md) | 从 ADS 原理图或网表执行文本优先的仿真、指标评估、绘图和受限优化 |
| ADS | [ads-venv-setup](./skills/ads/ads-venv-setup/SKILL.md) | 配置与 ADS 2025 打包 Python 环境匹配的虚拟环境 |
| ADS | [configure-ads-linux](./skills/ads/configure-ads-linux/SKILL.md) | 安装和维护 ADS 2025/2026/2027+ Linux 多版本环境与许可证服务 |
| ADS | [configure-ads-windows](./skills/ads/configure-ads-windows/SKILL.md) | 安装和维护 ADS 2022/2025/2027+ Windows 多版本环境与许可证配置 |
| ADS | [configure-ads2025-linux](./skills/ads/configure-ads2025-linux/SKILL.md) | ADS 2025 Linux 安装后的环境与许可证服务配置参考 |
| EDA 集成 | [eda-gui-async-bridge](./skills/eda-integration/eda-gui-async-bridge/SKILL.md) | 将 CLI/MCP 与 ADS、Virtuoso 等 EDA GUI 的原生启动脚本进行异步通信 |
| 工程实践 | [research](./skills/engineering-practice/research/SKILL.md) | 基于一手资料研究技术问题，并将带引用的结论沉淀到仓库 |
| 工程实践 | [diagnosing-bugs](./skills/engineering-practice/diagnosing-bugs/SKILL.md) | 为脚本、MCP、环境或仿真问题建立可复现的诊断闭环 |
| 工程实践 | [linux-vm-ssh-setup](./skills/engineering-practice/linux-vm-ssh-setup/SKILL.md) | 新 Linux 虚拟机网络、sudo、sshd、Windows SSH 密钥免密登录与 VS Code 连接配置 |
| 工程实践 | [pytest-windows-sandbox-temp](./skills/pytest-windows-sandbox-temp/SKILL.md) | 处理受控 Windows sandbox 中 pytest 临时目录 ACL / WinError 5 问题；当前为 legacy 顶层路径 |
| 知识检索 | [rag-mcp-builder](./skills/knowledge/rag-mcp-builder/SKILL.md) | 从 HTML、文本、代码等知识库构建本地 ChromaDB + BM25 RAG MCP 服务 |
| 文档处理 | [marker-pdf-to-md](./skills/document-processing/marker-pdf-to-md/SKILL.md) | 使用 Marker 将 PDF 转为 Markdown，并保留后续核验路径 |
| 文档处理 | [pdf-to-markdown](./skills/document-processing/pdf-to-markdown/SKILL.md) | 批量将 PDF 转为 Markdown 文本 |
| 项目文档 | [ai-project-docs-structure](./skills/project-documentation/ai-project-docs-structure/SKILL.md) | 为 AI 辅助项目建立可维护的三层文档结构 |
| 项目文档 | [sphinx-docs-site](./skills/project-documentation/sphinx-docs-site/SKILL.md) | 构建或维护 Sphinx 文档站点 |
| 项目文档 | [writing-great-skills](./skills/project-documentation/writing-great-skills/SKILL.md) | 编写和维护可预测、低冗余 Agent Skills 的参考框架 |
| 项目规划 | [grill-me](./skills/project-planning/grill-me/SKILL.md) | 对计划或设计逐题澄清，形成共同理解 |
| 项目规划 | [grill-with-docs](./skills/project-planning/grill-with-docs/SKILL.md) | 在需求澄清中同步建立术语表和 ADR |
| 项目规划 | [grilling](./skills/project-planning/grilling/SKILL.md) | `grill-me` 与 `grill-with-docs` 使用的逐题访谈核心流程 |
| 项目规划 | [domain-modeling](./skills/project-planning/domain-modeling/SKILL.md) | 维护项目术语、领域边界和关键架构决策 |

## 面向模拟 IC 的组合方式

```text
不知道从哪个 Skill 开始
  -> skills/skill-management/ask-why

ADS 网表仿真与优化
  -> skills/ads/ads-netlist-simulation

ADS 或 Virtuoso 的 GUI 自动化
  -> skills/eda-integration/eda-gui-async-bridge

ADS/Virtuoso 帮助文档与内部笔记检索
  -> skills/knowledge/rag-mcp-builder
  -> 为资料建立本地、合规的 RAG MCP 服务

新建长期维护的自动化工程
  -> skills/project-planning/grill-with-docs
  -> requirements、术语表与 ADR
  -> skills/engineering-practice/research 或 diagnosing-bugs

完成一次工作并获得可复用经验
  -> skills/skill-management/distill

Skill 库出现重复、漂移或索引不一致
  -> skills/skill-management/maintain-skills
```

Skill 的完整生命周期见 [docs/skill-lifecycle.md](./docs/skill-lifecycle.md)，结构与维护规则见 [docs/conventions.md](./docs/conventions.md)。引入的第三方技能及许可见 [THIRD_PARTY_NOTICES.md](./THIRD_PARTY_NOTICES.md)。
