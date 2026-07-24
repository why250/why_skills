---
name: ai-project-docs-structure
description: >-
  Sets up or refactors documentation into a three-layer structure for
  AI-assisted projects: README.md (user entry), AGENTS.md (Agent context,
  ~80 lines), docs/conventions.md (technical conventions, single source of
  truth). Use when project docs are redundant between README and AGENTS.md,
  when the user asks to organize or restructure documentation, when starting
  a new project's doc system, or when the user mentions "AGENTS.md 太长"、
  "文档重复"、"整理项目文档"、"docs structure"、"three-layer docs".
disable-model-invocation: true
---

# AI Project Docs Structure

Three-layer documentation architecture for projects with AI coding assistants.
Each piece of content lives in exactly one file; the others reference it.

## Layer Definitions

| File | Audience | Keep | Delete |
|---|---|---|---|
| `README.md` | Humans (GitHub, new users) | Project intro, install, API examples, result tables, links | Math formulas, internal data formats, validation numbers |
| `AGENTS.md` | AI Agent (injected context) | 1-line overview, file index, extension guide code snippets | Install cmds, topology diagrams, dependencies, long examples |
| `docs/conventions.md` | Both (via link/Read) | All math, data format specs, validation baselines, measurement conditions | — |

**Key constraint**: Agent can actively `Read` files when instructed, so AGENTS.md needs only a pointer to `docs/conventions.md`, not the content itself.

## Workflow

### Step 1 — Audit existing docs

Read all current documentation files:
- `README.md`
- `AGENTS.md`
- Any files under `docs/`

Identify every content block and which layer it belongs to (use the table above).

### Step 2 — Create `docs/conventions.md`

Move the following from AGENTS.md into `docs/conventions.md` as the single source of truth:

- Mathematical model description (topology, key formulas, algorithms)
- Data format conventions (tuple field definitions, unit conventions, variable naming)
- Validation / baseline data points (datasheet vs model comparison table)
- Measurement conditions referenced from product datasheets

Header for `docs/conventions.md`:
```markdown
# conventions.md — 技术规范参考

本文件是项目的技术规范单一来源（Single Source of Truth）。
README.md 和 AGENTS.md 均通过链接引用本文件，不重复内容。
```

### Step 3 — Trim AGENTS.md to ~80 lines

**Keep** (must be inline for Agent to work without extra reads):
1. One-sentence project overview
2. Key file index table (file path → class/function names + one-line purpose)
3. Explicit Read pointer:
   ```
   > 数学约定、数据格式、验证数据点见 [docs/conventions.md](docs/conventions.md)。
   > 需要时请使用 Read 工具读取该文件。
   ```
4. Extension guide with minimal code templates (e.g., how to add a new product spec)

**Delete** (already in README or moving to docs/conventions.md):
- Install / dependency table
- Common CLI commands
- Topology diagrams
- Long What-If analysis examples
- Datasheet measurement conditions

### Step 4 — Small edits to `README.md`

1. Add `docs/conventions.md` to the project file tree with a one-line description
2. At the end of the "data source" or "references" section, add:
   ```markdown
   > 详细测量条件和数学约定见 [docs/conventions.md](docs/conventions.md)。
   ```

No other changes to README — it is already user-facing and should stay complete.

## Content Allocation Quick Reference

When unsure where a piece of content belongs, apply these rules:

- **Would a new user need this to install and run the project?** → README
- **Would an Agent need this to write correct code without asking?** → AGENTS.md (inline)
- **Is it a formula, unit definition, data format spec, or validation number?** → docs/conventions.md
- **Is it a step-by-step user workflow or example output?** → README
- **Is it an invariant the Agent must not violate when modifying code?** → AGENTS.md or docs/conventions.md

## Verification Checklist

After restructuring:
- [ ] No content block exists in more than one file
- [ ] AGENTS.md is ≤ 100 lines
- [ ] AGENTS.md contains at least one explicit `Read docs/conventions.md` instruction
- [ ] README file tree includes `docs/conventions.md`
- [ ] README links to `docs/conventions.md` at the end of its data/reference section
- [ ] `docs/conventions.md` opens with a "Single Source of Truth" header
