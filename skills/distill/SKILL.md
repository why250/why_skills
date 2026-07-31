---
name: distill
description: >-
  Classifies and persists high-signal learnings from the current conversation into
  the correct chipBench slot (code, skill, rule, doc/ADR, or MEMORY). Use when the
  user says 沉淀, 固化本轮, 固化, distill, or /distill, or asks to capture/save
  session learnings after a discussion.
---

# /distill — 对话沉淀路由器

> 先分类、用户确认后再落盘。同内容只进一个主槽。不扫 transcript、不另建文档树。

## 何时激活

- 用户说「沉淀」「固化本轮」「固化」「distill」「/distill」
- 对话产生可复用流程、设计决策、踩坑、或可代码化逻辑，需要固化

## 元规则（最高优先级）

**能用代码解决的，坚决不写进 rule/文档。**  
优先级：**d 代码 > a skill > rule > b doc/ADR > c MEMORY**。

## 工作流程

### Phase 1: 扫描本轮高信号

从当前对话提取候选，忽略噪声：

| 候选类型 | 信号 |
|----------|------|
| 流程 | 多步、可重复、有清晰触发条件 |
| 决策 | 「为什么选 X 不选 Y」、影响 ≥2 模块 |
| 踩坑 | 症状 → 根因 → 修复，已验证 |
| 可代码化 | 可测、可 CLI、重复执行 |

**不沉淀**：本轮 diff 清单、checkpoint 状态、已存在于 skill/rule/代码的重复内容、未经验证的猜测。

### Phase 2: 分类表（必须先输出，停等确认）

**禁止在用户确认前创建/修改任何文件。** skill / rule / 代码尤其强制。

输出表格后停止，等用户勾选：

```markdown
| # | 类型 | 一句话 | 建议路径 | 新建/追加 | 备注 |
|---|------|--------|----------|-----------|------|
| 1 | d 代码 | … | packages/… 或 scripts/… | 新建 | |
| 2 | a skill | … | .cursor/skills/<name>/ | 新建 | |
| 3 | rule | … | .cursor/rules/<name>.mdc | 追加 | |
| 4 | b doc | … | projects/<chip>/…/doc/… | 新建 | |
| 5 | b ADR | … | doc/adr/ADR-NNN.md | 新建 | 走 adr skill |
| 6 | c MEMORY | … | …/MEMORY.md | 追加 | |
| — | （不写） | … | — | — | 过小 / 已有 / 未验证 |
```

用户可：全选、勾选子集、改路径、或「全部跳过」。

### Phase 3: 按确认项落盘

#### 路由表

| 类型 | 何时选 | 默认路径 |
|------|--------|----------|
| d 代码 | 可测、可 CLI、重复执行 | 相关 `packages/` 或项目 `scripts/`；优先 `--help` / `--explain`，不写长文档 |
| a skill | 多步流程 + 清晰触发 + 非显然约束 | `.cursor/skills/<name>/`；细节 `reference/`，脚本 `scripts/` |
| rule | 打开某路径就要生效的短纪律 | `.cursor/rules/*.mdc`（可带 globs） |
| b doc | 设计结构/思路，非操作步骤 | 会话所属项目 doc（如 `projects/rigel_driver/CP/tests/doc/`） |
| b ADR | 重大取舍、影响 ≥2 模块 | 走 `adr` skill → `doc/adr/` |
| c MEMORY | 症状→根因→修复 | 活动项目 MEMORY（Rigel CP：`projects/rigel_driver/CP/MEMORY.md`） |

#### 落盘纪律

**d 代码**

- 写可运行、可测的最小实现；能进现有包则不新开包
- 文档只补 `--help` / 常量 / 错误信息能表达的部分

**a skill**

- `SKILL.md`：YAML `name` + `description`（第三人称，含 WHAT + WHEN）
- 抽**最终可行做法**，不写失败尝试（除非 gotcha 本身有用）
- 泛化硬编码为占位符；SKILL.md 保持精炼（建议 <500 行）
- 细节进 `reference/`，可复用脚本进 `scripts/`

**rule**

- 短、可执行、带 globs（若仅某路径需要）
- 与 skill 分工：rule = always-on 纪律；skill = 按需流程

**b doc**

- 写「为什么 / 结构 / 约定」，不复述代码实现细节
- 追加时先读现有文，避免重复段落

**b ADR**

- 遵循 `.cursor/skills/adr/SKILL.md`（模板、编号、索引、用户确认）

**c MEMORY**

- 短条目，含日期：`### YYYY-MM-DD 标题` + 症状 / 根因 / 修复
- 不写长设计；长文进 doc

### Phase 4: 回报

落盘后输出：

```markdown
## 沉淀结果
- 已写：
  - [类型] path — 一句话
- 未写（用户未勾选 / 降级）：
  - …
- 刻意跳过：
  - …（原因）
```

## 与现有 skill 协作

| Skill | 关系 |
|-------|------|
| `adr` | 重大决策落盘时调用其流程与模板 |
| `checkpoint` | 不替代；checkpoint = 状态快照，distill = 知识固化 |
| create-skill（Cursor） | 新建 a skill 时遵循其 frontmatter / 目录规范 |

## 反例与边界

| 情况 | 做法 |
|------|------|
| 过小（一句话纪律） | 一行 MEMORY 或 rule bullet，不新建 skill |
| 多主题 | 拆多行分类表，或只沉淀用户指定主题 |
| 已有权威槽位 | 追加更新，不复制第三份 |
| 重复出现 ≥2–3 次的流程 | 可升 skill / rule；偶发先 MEMORY |
| 用户未确认 | **禁止**静默写 skill / rule / 代码 |

## 用法

```
用户：沉淀
AI：输出分类表 → 停
用户：1、3 确认；2 改成 MEMORY
AI：落盘 → 回报
```
