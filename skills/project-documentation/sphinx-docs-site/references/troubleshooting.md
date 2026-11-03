# Sphinx 文档站常见问题

## 构建报 `ImportError`

`conf.py` 中 `sys.path.insert` 的路径不对，Sphinx 找不到你的包。检查相对路径是否正确指向包的父目录。

## API 页面是空的

检查：
1. `conf.py` 中 `extensions` 有 `'sphinx.ext.autodoc'`
2. `.rst` 中 `.. autofunction::` 的函数名正确（含完整模块路径或用 `.. currentmodule::`）
3. 函数确实存在于对应模块中

## .md 文件没有出现在网站上

检查：
1. `conf.py` 中 `extensions` 有 `'myst_parser'`
2. `source_suffix` 包含 `'.md': 'markdown'`
3. `.md` 文件在某个 `toctree` 中被引用

## 部署后 404

检查仓库 Settings → Pages → Source 是否设为 **"GitHub Actions"**（不是 branch 模式）。

## .nojekyll 是干什么的

Jekyll 是 GitHub 的默认静态站点生成器。加上 `.nojekyll` 文件告诉 GitHub 我们的 HTML 已经是 Sphinx 生成好的，不要用 Jekyll 再处理一遍。不加的话以 `_` 开头的目录（如 `_static`、`_images`）会被 Jekyll 忽略，导致 CSS 和图片 404。
