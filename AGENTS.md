# why_skills agent guide

这是一个 Agent Skills 仓库。修改时优先保持技能可发现、路径稳定、说明可验证。

## 文件地图

| 路径 | 作用 |
|---|---|
| `README.md` | 面向使用者的仓库入口与所有技能索引 |
| `docs/conventions.md` | 分类、命名、移动、验证和提交约定的单一来源 |
| `skills/<category>/<skill-name>/SKILL.md` | 单个技能的入口 |
| `skills/<category>/<skill-name>/references/` | 按需读取的说明资料 |
| `skills/<category>/<skill-name>/scripts/` | 可直接执行并需实际测试的辅助脚本 |

## 修改规则

- 新增、移动、重命名或删除技能前，先阅读 `docs/conventions.md`。
- 所有技能必须位于 `skills/<category>/<skill-name>/`，且目录名与 `SKILL.md` 的 `name` 一致。
- 更新任何技能路径后，同步更新 `README.md`；检查技能内的相对链接和脚本路径。
- 仅在真实需要时添加 `references/`、`scripts/` 或 `templates/`；不要添加无用途的 README、安装指南或构建产物。
- 不提交 PDK、许可证、私有帮助文档、仿真输出、向量数据库、模型缓存或机密配置。
- 保留用户已有的未跟踪文件，除非用户明确要求处理它们。

> 分类、命名、验证清单和 Git 忽略规则见 [docs/conventions.md](docs/conventions.md)。读取或调整仓库结构前必须先读取该文件。
