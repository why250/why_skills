---
name: maintain-skills
description: Audit the why_skills library for duplication, drift, stale content, broken structure, and unclear invocation boundaries.
disable-model-invocation: true
---

# Maintain Skills

对整个 Skill Library 做体检。目标不是追求目录整齐，而是让 Skill **可发现、边界清晰、单一事实源、可验证、可继续演化**。

默认是 **report first**：先给证据和建议；只有用户明确要求应用修改时才执行重命名、移动、合并、拆分或删除。

## 1. Read the rules

先读取：

- 根 `AGENTS.md`
- `docs/conventions.md`
- `docs/skill-lifecycle.md`
- 根 `README.md`
- 与候选问题直接相关的 Skill

不要一开始通读所有 Skill 正文。先用目录、frontmatter 和索引建立 inventory，再对异常候选深入读取。

## 2. Run mechanical validation

在仓库根运行：

```bash
python skills/skill-management/maintain-skills/scripts/validate_skills.py
```

机械检查负责发现：

- frontmatter 缺失或 `name` 与目录名不一致；
- skill name 重复；
- README 漏索引；
- legacy 顶层 Skill 路径；
- user-invoked Skill 与 `agents/openai.yaml` 策略不一致；
- SKILL.md 中明显失效的本地相对链接。

Validator 的 warning 是维护候选，不等于必须修改。

## 3. Audit semantics

围绕以下问题做判断：

### Duplication

- 两个 Skill 是否由相同情境触发？
- 是否执行几乎相同的主流程，只是名字不同？
- 同一规则或说明是否存在两个权威来源？
- 某个版本专用 Skill 是否已经被通用 Skill 完全覆盖？

### Invocation

- Skill 是否真的需要独立调用？
- user-invoked / model-invoked 的选择是否合理？
- description 是否准确描述“什么时候用”，而不是重复正文？
- Router 是否能从用户自然描述稳定找到它？

### Shape

- 一个 Skill 是否包含多个独立触发的 branch，值得 split？
- 内容是否只是长 reference，应该从 SKILL.md 下沉？
- 是否存在 no-op、过时 workaround 或已经失效的版本说明？
- scripts / references / templates 是否被引用并仍有用途？

### Discoverability

- README 是否反映真实目录？
- 分类是否仍能解释 Skill 的主要使用场景？
- 常见工作是否需要记住太多 Skill 名称，而应该补 Router flow？

## 4. Report

用一张表给出维护建议：

```markdown
| Skill / path | Action | Evidence | Proposed change | Risk |
|---|---|---|---|---|
| ... | Keep / Update / Merge / Split / Retire | ... | ... | low / medium / high |
```

排序优先级：

1. 会导致错误调用或失效的结构问题；
2. 重复与单一事实源冲突；
3. 索引和 discoverability 漂移；
4. 内容膨胀、no-op、可读性问题。

没有足够证据时标记为 `Review`，不要强行归类成 Merge 或 Retire。

## 5. Apply only when authorized

用户要求应用修改时：

- 小步修改，优先一个主题一个 PR；
- 移动 / 重命名同时更新 README、相对链接和调用配置；
- 合并前明确新的单一事实源；
- 删除前确认没有仍需保留的独立触发条件、脚本或 reference；
- 修改后重新运行 validator；
- 用 diff 确认没有把无关 Skill 卷入重构。

## Relationship to other meta skills

- `ask-why`：解决“现在该用什么”。
- `distill`：解决“这次经验该不该、该在哪里长期保存”。
- `maintain-skills`：解决“整个库现在是否健康”。

三者的共同约定见 `docs/skill-lifecycle.md`。
