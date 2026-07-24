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

```python
import os
import sys
sys.path.insert(0, os.path.abspath('../../src'))  # 让 Sphinx 能 import 你的包

project = 'MyProject'
copyright = '2026'
author = 'Me'
version = release = '0.1.0'

extensions = [
    'sphinx.ext.autodoc',         # ★ 从 docstring 自动生成 API 文档
    'sphinx.ext.napoleon',        # ★ 支持 Google/NumPy 风格 docstring
    'sphinx.ext.viewcode',        # 源码链接
    'sphinx.ext.mathjax',         # 数学公式
    'sphinx.ext.autosummary',     # 摘要表格
    'myst_parser',                # ★ .md 文件支持
    'sphinx_copybutton',          # 代码块复制按钮
    'sphinx_design',              # 卡片、网格等现代布局
]

# 同时支持 .rst 和 .md 源文件
source_suffix = {'.rst': 'restructuredtext', '.md': 'markdown'}

# 主题
html_theme = 'pydata_sphinx_theme'

# Napoleon 设置 — 解析 docstring
napoleon_google_docstring = True
napoleon_numpy_docstring = True

# Autodoc 默认 — 列出所有 public 成员
autodoc_default_options = {
    'members': True,
    'undoc-members': True,
    'show-inheritance': True,
}

# 自动生成摘要 stub 文件
autosummary_generate = True
```

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

创建 `.github/workflows/docs.yml`：

```yaml
name: Build and Deploy Documentation

on:
  push:
    branches: [main]
    paths:
      - 'docs/**'               # 文档源文件
      - 'src/**/*.py'           # 源码 docstring
      - '.github/workflows/docs.yml'
  workflow_dispatch:            # 允许手动触发

permissions:
  contents: read
  pages: write
  id-token: write

concurrency:
  group: "pages"
  cancel-in-progress: false

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6

      - uses: actions/setup-python@v6
        with:
          python-version: '3.11'
          cache: 'pip'

      - name: Install dependencies
        run: |
          pip install --upgrade pip
          pip install -e .
          pip install sphinx pydata-sphinx-theme myst-parser sphinx-design sphinx-copybutton

      - name: Build docs
        run: |
          cd docs
          python -m sphinx -b html source build/html
          touch build/html/.nojekyll     # ★ 必须 — 禁止 Jekyll 处理

      - uses: actions/upload-pages-artifact@v5
        with:
          path: docs/build/html

  deploy:
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    runs-on: ubuntu-latest
    needs: build
    steps:
      - uses: actions/deploy-pages@v5
```

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

### 构建报 `ImportError`

`conf.py` 中 `sys.path.insert` 的路径不对，Sphinx 找不到你的包。检查相对路径是否正确指向包的父目录。

### API 页面是空的

检查：
1. `conf.py` 中 `extensions` 有 `'sphinx.ext.autodoc'`
2. `.rst` 中 `.. autofunction::` 的函数名正确（含完整模块路径或用 `.. currentmodule::`）
3. 函数确实存在于对应模块中

### .md 文件没有出现在网站上

检查：
1. `conf.py` 中 `extensions` 有 `'myst_parser'`
2. `source_suffix` 包含 `'.md': 'markdown'`
3. `.md` 文件在某个 `toctree` 中被引用

### 部署后 404

检查仓库 Settings → Pages → Source 是否设为 **"GitHub Actions"**（不是 branch 模式）。

### .nojekyll 是干什么的

Jekyll 是 GitHub 的默认静态站点生成器。加上 `.nojekyll` 文件告诉 GitHub 我们的 HTML 已经是 Sphinx 生成好的，不要用 Jekyll 再处理一遍。不加的话以 `_` 开头的目录（如 `_static`、`_images`）会被 Jekyll 忽略，导致 CSS 和图片 404。
