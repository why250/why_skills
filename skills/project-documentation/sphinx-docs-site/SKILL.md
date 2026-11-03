---
name: sphinx-docs-site
description: >
  Build a static documentation website for any Python project using Sphinx +
  GitHub Pages. Use this skill when the user wants to set up, update, or fix
  a documentation site from Python docstrings, .md, or .rst sources,
  deployed via GitHub Actions to GitHub Pages (default or custom domain).
  Covers the full pipeline: Sphinx config, autodoc API generation, MyST
  Markdown, CI/CD workflow, and one-time GitHub Pages setup.
---

# Sphinx + GitHub Pages 文档站搭建

完整指南：从零搭建自动部署的 Python 项目文档网站。

## 架构

```
.py源码/docstrings  ──→  Sphinx autodoc  ──→  静态HTML  ──→  GitHub Pages
.md/.rst 手写文档   ──→  MyST/Sphinx    ──→              ──→  (免费域名)
```

## 一、依赖安装

```bash
pip install sphinx pydata-sphinx-theme myst-parser sphinx-design sphinx-copybutton
```

在 `pyproject.toml` 中声明（推荐）：

```toml
[project.optional-dependencies]
docs = [
    "sphinx>=7.0.0",
    "pydata-sphinx-theme>=0.16.0",
    "myst-parser>=2.0.0",
    "sphinx-design>=0.6.0",
    "sphinx-copybutton>=0.5.2",
]
```

## 二、初始化文档目录

```bash
cd <项目根目录>
mkdir docs
cd docs
sphinx-quickstart  # 交互式创建，基本一路回车
```

生成结构：

```
docs/
├── source/
│   ├── conf.py          # ★ 核心配置
│   └── index.rst        # ★ 首页
├── Makefile
└── make.bat
```

## 三、配置 conf.py

以 [templates/conf.py](templates/conf.py) 为起点，复制到 `docs/source/conf.py` 后修改 `project`、`sys.path` 等项目字段。

### 关键配置项说明

| 配置 | 作用 | 不配的后果 |
|------|------|-----------|
| `sys.path.insert(0, '...')` | Sphinx 能 `import` 你的包 | autodoc 报 `ImportError` |
| `sphinx.ext.autodoc` | `.. autofunction::` 生效 | API 页全是空白 |
| `myst_parser` | 能直接写 `.md` 文件 | .md 文件被忽略 |
| `napoleon_*` | 解析 Google/NumPy docstring | 参数列表渲染成乱码 |

## 四、编写网站内容

### 4a. 首页 `index.rst` — 用 toctree 定义导航

```rst
MyProject 文档
==============

.. toctree::
   :maxdepth: 2
   :caption: 使用指南

   installation
   quickstart
   api/index
   changelog
```

- **`toctree`** 是 Sphinx 的核心指令 —— 只有出现在 toctree 中的页面才会被构建并出现在导航中。
- **`:caption:`** 是导航栏中的分组标题。

### 4b. API 文档 — 半自动维护

为每个模块建一个 `.rst` 文件，放在 `api/` 子目录：

**`api/index.rst`**（API 导航）：

```rst
API 参考
========

.. toctree::
   :maxdepth: 2

   core
   utils
```

**`api/core.rst`**（具体模块的 API）：

```rst
核心模块
========

.. currentmodule:: myproject.core

信号处理
--------

.. autofunction:: process_signal
.. autofunction:: filter_noise

数据加载
--------

.. autoclass:: DataLoader
   :members:
```

### 4c. 手写教程 — 直接用 .md

在 `source/` 下放 `.md` 文件，在 toctree 中引用即可：

```markdown
# 快速开始

## 安装

pip install myproject

## 第一个例子

import myproject
result = myproject.process_signal(data)
```

### 4d. 中英文双语文档（可选）

1. 在 `conf.py` 中配置：

```python
locale_dirs = ['locale']
gettext_compact = False
```

2. 生成翻译模板：

```bash
cd docs
sphinx-build -b gettext source build/gettext
sphinx-intl update -p build/gettext -l zh_CN
```

3. 翻译 `locale/zh_CN/LC_MESSAGES/` 下的 `.po` 文件

4. 在 workflow 中单独构建：

```bash
python -m sphinx -b html -D language=zh_CN source build/html/zh_CN
```

## 五、本地预览

```bash
cd docs
make html
# 或: python -m sphinx -b html source build/html
# 打开 build/html/index.html
```

## 六、GitHub Actions 部署

复制 [templates/docs.yml](templates/docs.yml) 到 `.github/workflows/docs.yml`，再按下表调整路径。构建步骤必须在输出目录 `touch .nojekyll`，否则 `_static` 等目录会 404。

### 路径映射（重要 — 根据项目结构调整）

| 项目布局 | docs.yml 中对应路径 |
|----------|-------------------|
| `docs/` 在项目根目录 | `cd docs` + `path: docs/build/html` |
| `python/docs/` （monorepo） | `cd python/docs` + `path: python/docs/build/html` |
| 源码在 `src/` | `sys.path.insert(0, os.path.abspath('../../src'))` |
| 源码就在根目录 | `sys.path.insert(0, os.path.abspath('../..'))` |

## 七、启用 GitHub Pages（只需一次的仓库设置）

在 GitHub 网页操作：

1. 仓库 → **Settings** → **Pages**
2. **Source** 下拉选择 **"GitHub Actions"**
3. 保存

推送代码后，网站自动部署到：

```
https://<用户名>.github.io/<仓库名>/
```

### 自定义域名（可选）

如需绑定自己的域名：

1. 在 workflow 中写入 CNAME 文件：

```yaml
- name: Write CNAME
  run: echo "docs.myproject.com" > docs/build/html/CNAME
```

2. 在域名 DNS 服务商处添加记录：
   - CNAME 记录指向 `<用户名>.github.io`
   - 或 A 记录指向 GitHub Pages 的 IP（`185.199.108.153` 等）

3. 删除 CNAME 文件即可恢复到默认 `github.io` 域名。

## 八、日常维护

| 你做的事 | 网站效果 | 是否需要改配置文件 |
|----------|----------|-------------------|
| 修改已有函数的 docstring | ✅ push 后自动更新 | 不需要 |
| 修改 `.rst` / `.md` 源文件 | ✅ push 后自动更新 | 不需要 |
| **新增一个函数/类** | ⚠️ 需要在 `.rst` 中加 `.. autofunction::` | 要补 API stub |
| **新增一个 Python 模块** | ⚠️ 要新建 `api/xxx.rst` + 加入 toctree | 要补两个文件 |
| **新增一篇教程 .md** | ⚠️ 需要加入 toctree | 要补 toctree 条目 |
| 修改 conf.py（主题/扩展） | ✅ 整站重建 | 这是配置文件本身 |

### AI 辅助维护

可以向 AI 提以下请求来自动化维护：

- "检查源码中有哪些公开函数漏了在 API 文档里"
- "在 `api/xxx.rst` 里加上新增函数的 autofunction 条目"
- "把这个新模块加入 api/index.rst 的 toctree"

## 九、常见问题

构建报 `ImportError`、API 页为空、`.md` 未出现、部署后 404、`.nojekyll` 用途：见 [references/troubleshooting.md](references/troubleshooting.md)。
