"""
extract_docstrings.py — Python docstring extractor

Extracts docstrings and function/class signatures from .py and .pyi files
and writes structured Markdown files suitable for RAG indexing.

Output: one .md file per top-level sub-package (groups files by 2-3 level package path).
Each .md contains module docstring, class docs, and function/method signatures + docstrings.

Usage:
    # Extract from a Python package directory:
    python extract_docstrings.py --input raw_data/my_package --output processed/api

    # Extract from multiple source directories:
    python extract_docstrings.py --input raw_data/package_a --output processed/api
    python extract_docstrings.py --input raw_data/package_b --output processed/api

    # Flatten output (one .md per file instead of per package group):
    python extract_docstrings.py --input raw_data/scripts --output processed/api --flat

No external dependencies — uses only Python stdlib (ast module).
"""

import argparse
import ast
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# AST helpers
# ---------------------------------------------------------------------------

def _get_docstring(node) -> str:
    """Return the docstring of an AST node, or empty string."""
    if (
        isinstance(node, (ast.AsyncFunctionDef, ast.FunctionDef, ast.ClassDef, ast.Module))
        and node.body
        and isinstance(node.body[0], ast.Expr)
        and isinstance(node.body[0].value, ast.Constant)
        and isinstance(node.body[0].value.value, str)
    ):
        return node.body[0].value.value.strip()
    return ""


def _annotation_to_str(annotation) -> str:
    if annotation is None:
        return ""
    return ast.unparse(annotation)


def _args_to_str(args: ast.arguments) -> str:
    """Format function arguments with type annotations."""
    parts = []
    for a in args.posonlyargs:
        s = a.arg
        if a.annotation:
            s += f": {_annotation_to_str(a.annotation)}"
        parts.append(s)
    if args.posonlyargs:
        parts.append("/")

    defaults_offset = len(args.args) - len(args.defaults)
    for i, a in enumerate(args.args):
        s = a.arg
        if a.annotation:
            s += f": {_annotation_to_str(a.annotation)}"
        if i >= defaults_offset:
            default = args.defaults[i - defaults_offset]
            s += f" = {ast.unparse(default)}"
        parts.append(s)

    if args.vararg:
        s = f"*{args.vararg.arg}"
        if args.vararg.annotation:
            s += f": {_annotation_to_str(args.vararg.annotation)}"
        parts.append(s)
    elif args.kwonlyargs:
        parts.append("*")

    for i, a in enumerate(args.kwonlyargs):
        s = a.arg
        if a.annotation:
            s += f": {_annotation_to_str(a.annotation)}"
        if args.kw_defaults[i] is not None:
            s += f" = {ast.unparse(args.kw_defaults[i])}"
        parts.append(s)

    if args.kwarg:
        s = f"**{args.kwarg.arg}"
        if args.kwarg.annotation:
            s += f": {_annotation_to_str(args.kwarg.annotation)}"
        parts.append(s)

    return ", ".join(parts)


def _func_signature(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    prefix = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
    args = _args_to_str(node.args)
    ret = f" -> {_annotation_to_str(node.returns)}" if node.returns else ""
    return f"{prefix} {node.name}({args}){ret}"


# ---------------------------------------------------------------------------
# File extraction
# ---------------------------------------------------------------------------

def extract_file(py_path: Path) -> list[dict]:
    """
    Parse a .py or .pyi file and return a list of extracted items:
      { kind: module|class|function|method, name, signature, docstring, source_file }
    """
    items = []
    try:
        source = py_path.read_text(encoding="utf-8", errors="replace")
        tree   = ast.parse(source, filename=str(py_path))
    except SyntaxError as e:
        return [{
            "kind": "error", "name": py_path.name,
            "signature": "", "docstring": str(e), "source_file": str(py_path),
        }]

    mod_doc = _get_docstring(tree)
    if mod_doc:
        items.append({
            "kind": "module", "name": py_path.stem,
            "signature": "", "docstring": mod_doc, "source_file": str(py_path),
        })

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            doc = _get_docstring(node)
            items.append({
                "kind": "class", "name": node.name,
                "signature": f"class {node.name}",
                "docstring": doc, "source_file": str(py_path),
            })
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    method_doc = _get_docstring(child)
                    if method_doc or not child.name.startswith("_"):
                        items.append({
                            "kind": "method",
                            "name": f"{node.name}.{child.name}",
                            "signature": _func_signature(child),
                            "docstring": method_doc,
                            "source_file": str(py_path),
                        })
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            doc = _get_docstring(node)
            if doc or not node.name.startswith("_"):
                items.append({
                    "kind": "function", "name": node.name,
                    "signature": _func_signature(node),
                    "docstring": doc, "source_file": str(py_path),
                })

    return items


def items_to_markdown(module_name: str, items: list[dict]) -> str:
    """Render extracted items as a Markdown document."""
    lines = [f"# {module_name}\n"]
    for item in items:
        kind = item["kind"]
        name = item["name"]
        sig  = item["signature"]
        doc  = item["docstring"]
        src  = Path(item["source_file"]).name

        if kind == "module":
            lines.append(f"\n> *Source: `{src}`*\n")
            lines.append(f"\n{doc}\n")
        elif kind == "class":
            lines.append(f"\n## `{name}`\n")
            lines.append(f"*Source: `{src}`*\n")
            if doc:
                lines.append(f"\n{doc}\n")
        elif kind in ("function", "method"):
            lines.append(f"\n### `{name}`\n")
            if sig:
                lines.append(f"```python\n{sig}\n```\n")
            if doc:
                lines.append(f"\n{doc}\n")
        elif kind == "error":
            lines.append(f"\n> **Parse error in `{src}`**: {doc}\n")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Directory processing
# ---------------------------------------------------------------------------

def _group_key_for(py_path: Path, src_dir: Path, depth: int) -> str:
    """Compute the group key for a file (top N levels of package path)."""
    rel   = py_path.relative_to(src_dir)
    parts = rel.parts
    n     = min(depth, len(parts))
    return ".".join(parts[:n]).replace("\\", ".").rstrip(".py").rstrip(".pyi")


def process_directory_grouped(src_dir: Path, out_dir: Path, group_depth: int = 3) -> int:
    """
    Process all .py and .pyi files; group by top N package levels.
    Writes one .md per group.
    """
    py_files = sorted(src_dir.rglob("*.py")) + sorted(src_dir.rglob("*.pyi"))
    if not py_files:
        print(f"  No .py/.pyi files found in {src_dir}")
        return 0

    groups: dict[str, list[Path]] = {}
    for f in py_files:
        rel   = f.relative_to(src_dir)
        parts = rel.parts
        if len(parts) >= group_depth:
            key = ".".join(parts[:group_depth])
        elif len(parts) >= 2:
            key = ".".join(parts[:2])
        else:
            key = parts[0].replace(".py", "").replace(".pyi", "")
        groups.setdefault(key, []).append(f)

    count = 0
    for group_key, files in sorted(groups.items()):
        all_items = []
        for f in files:
            all_items.extend(extract_file(f))

        has_content = any(item["docstring"] for item in all_items)
        if not has_content and not all_items:
            continue

        md       = items_to_markdown(group_key, all_items)
        out_file = out_dir / f"{group_key}.md"
        out_file.parent.mkdir(parents=True, exist_ok=True)
        out_file.write_text(md, encoding="utf-8")
        count += 1

        n_with_doc = sum(1 for i in all_items if i["docstring"])
        print(
            f"  {group_key}: {len(files)} files, {len(all_items)} items, "
            f"{n_with_doc} with docstrings → {out_file.name}"
        )

    return count


def process_directory_flat(src_dir: Path, out_dir: Path) -> int:
    """
    Process all .py and .pyi files; write one .md per source file.
    Better for repositories where each file is a standalone module.
    """
    py_files = sorted(src_dir.rglob("*.py")) + sorted(src_dir.rglob("*.pyi"))
    if not py_files:
        print(f"  No .py/.pyi files found in {src_dir}")
        return 0

    count = 0
    for f in py_files:
        items = extract_file(f)
        has_content = any(item["docstring"] for item in items)
        if not has_content and not items:
            continue

        rel      = f.relative_to(src_dir)
        stem     = str(rel).replace("\\", ".").replace("/", ".").rstrip(".py").rstrip(".pyi")
        md       = items_to_markdown(stem, items)
        out_file = out_dir / rel.with_suffix(".md")
        out_file.parent.mkdir(parents=True, exist_ok=True)
        out_file.write_text(md, encoding="utf-8")
        count += 1

    print(f"  {count} .md files written from {len(py_files)} source files")
    return count


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract Python docstrings to Markdown for RAG indexing.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--input",  "-i", required=True, help="Source directory with .py/.pyi files")
    parser.add_argument("--output", "-o", required=True, help="Output directory for .md files")
    parser.add_argument(
        "--flat", action="store_true",
        help="Write one .md per source file instead of grouping by package (useful for script dirs)",
    )
    parser.add_argument(
        "--group-depth", type=int, default=3, metavar="N",
        help="Number of package path levels to group by (default: 3, e.g. keysight.ads.de)",
    )
    args = parser.parse_args()

    src_dir = Path(args.input)
    out_dir = Path(args.output)

    if not src_dir.exists():
        print(f"ERROR: input directory does not exist: {src_dir}", file=sys.stderr)
        sys.exit(1)

    out_dir.mkdir(parents=True, exist_ok=True)

    mode = "flat" if args.flat else f"grouped (depth={args.group_depth})"
    print(f"\n[extract_docstrings] {src_dir} → {out_dir}  (mode={mode})\n")

    if args.flat:
        count = process_directory_flat(src_dir, out_dir)
    else:
        count = process_directory_grouped(src_dir, out_dir, group_depth=args.group_depth)

    print(f"\n[extract_docstrings] Done. {count} .md files written to {out_dir}\n")


if __name__ == "__main__":
    main()
