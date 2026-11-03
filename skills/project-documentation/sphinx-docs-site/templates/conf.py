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
