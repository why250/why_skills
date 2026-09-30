# Skill Library Lifecycle

`why_skills` 不是静态的 Skill 清单，而是一个持续演化的个人工程方法库。生命周期的目标是：**能沉淀、能找到、能维护，同时尽量避免重复、漂移和遗忘。**

## 四个职责

| 职责 | 入口 | 默认行为 | 不负责 |
|---|---|---|---|
| 路由 | `ask-why` | 根据当前情境指出最小可用 Skill 或 flow | 不复制 README，不修改 Skill |
| 沉淀 | `distill` | 从已验证经验中判断“更新 / 新建 / 文档 / 不写”并按授权落盘 | 不把每次经验都升级成 Skill |
| 维护 | `maintain-skills` | 审计重复、漂移、过时、索引和调用边界，先报告后修改 | 不凭相似名称直接删除或合并 |
| 验证 | `maintain-skills/scripts/validate_skills.py` | 做目录、frontmatter、索引和调用配置等机械检查 | 不做语义上的 merge / split 判断 |

机械问题交给 validator；需要工程判断的问题交给 maintainer。

## 生命周期

```text
工作中出现需求或问题
        |
        v
   ask-why 路由
        |
        v
复用已有 Skill / flow
        |
        v
完成工作并获得已验证经验
        |
        v
     distill
        |
        +--> 更新已有 Skill / reference / script
        +--> 新建 Skill（只有独立调用边界成立时）
        +--> 写 doc / ADR / rule / code
        +--> 不沉淀
        |
        v
     validate
        |
        v
定期 maintain-skills
        |
        +--> keep
        +--> update
        +--> merge
        +--> split
        +--> retire
        |
        +--------------------> 回到可复用的 Skill Library
```

## 新建 Skill 前的判断

优先复用和更新，只有出现**独立的调用边界**时才新增 Skill。

| 情况 | 首选动作 |
|---|---|
| 触发情境和执行过程都与现有 Skill 相同 | 更新现有 Skill |
| 同一任务只是多了一个环境或版本分支 | 给现有 Skill 增加 branch / reference |
| 只是事实、解释或长资料 | 放入已有 reference / docs |
| 可重复、确定、适合自动执行 | 优先实现 script / check，再由 Skill 编排 |
| 有独立触发条件、独立流程、可单独复用 | 新建 Skill |
| 一次性进度、未验证猜测、仅本轮有用 | 不沉淀为 Skill |

## 路由原则

Router 按**用户当前处境**而不是仓库分类来思考。用户通常记得“我要解决什么”，而不是“这个 Skill 属于哪个 category”。

Router 应先读取根 `README.md` 的当前技能索引，在必要时再读取候选 Skill 的 description。它只给出最小路线，不维护第二份完整索引。

## 沉淀原则

Distill 先查重，再决定落点。对 `why_skills` 本身进行沉淀时：

1. 先读 `README.md`、`docs/conventions.md` 和本文件。
2. 搜索同主题 Skill 和相近触发条件。
3. 优先更新已有权威来源。
4. 新建 Skill 时同时更新索引并通过 validator。
5. 未经验证或无法形成稳定流程的内容，不为了“有沉淀”而创建 Skill。

## 维护原则

维护是**审计**，不是自动大扫除。默认先给出证据和建议：

- **Keep**：边界清晰，无需改动。
- **Update**：内容有效，但索引、版本、链接、触发条件或实现需要更新。
- **Merge**：两个 Skill 的触发条件和核心流程实质重叠。
- **Split**：一个 Skill 包含多个可以独立触发的流程，且拆分能降低上下文或维护成本。
- **Retire**：已被其他权威来源完全覆盖，或长期失效。

删除、移动、重命名会影响路径稳定性，只有收益明确时才执行，并同步修复 README、相对链接和调用配置。

## 维护节奏

不需要人为规定固定周期。出现以下信号时运行 `maintain-skills`：

- 找 Skill 越来越依赖记忆；
- 新 Skill 与旧 Skill 难以区分；
- README 与目录结构不一致；
- 同类版本 Skill 越来越多；
- 某个 SKILL.md 明显膨胀；
- 多次出现“这个规则到底写在哪”的问题；
- 一次较大的 Skill 新增或重组完成后。

