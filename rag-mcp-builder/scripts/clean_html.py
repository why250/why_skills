"""
clean_html.py — HTML to Markdown converter

Converts HTML documentation files (MadCap Flare or Sphinx) to clean Markdown.
Outputs one .md file per .html file, preserving the directory structure.

Supported formats:
  madcap  — MadCap Flare HTML (strips sidebars, breadcrumbs, navigation)
  sphinx  — Sphinx HTML (extracts main content div)
  auto    — (default) auto-detect based on HTML content

Usage:
    pip install beautifulsoup4 lxml

    # Single source directory:
    python clean_html.py --input raw_data/html_docs --output processed/docs

    # Specify format explicitly:
    python clean_html.py --input raw_data/madcap --output processed/docs --format madcap
    python clean_html.py --input raw_data/sphinx --output processed/api --format sphinx

    # Multiple source dirs (run the script once per directory):
    python clean_html.py --input raw_data/html/priority1 --output processed/docs/priority1
    python clean_html.py --input raw_data/html/priority2 --output processed/docs/priority2
"""

import argparse
import re
import sys
from pathlib import Path

try:
    from bs4 import BeautifulSoup, Comment, NavigableString, Tag
except ImportError:
    print("ERROR: beautifulsoup4 not installed. Run: pip install beautifulsoup4 lxml", file=sys.stderr)
    sys.exit(1)

_HEADING_MAP = {
    "h1": "#", "h2": "##", "h3": "###",
    "h4": "####", "h5": "#####", "h6": "######",
}


def _drop_unwanted(soup: BeautifulSoup) -> None:
    """Remove scripts, styles, navigation, and HTML comments."""
    for tag in soup.find_all(["script", "style", "noscript", "link", "nav", "footer"]):
        tag.decompose()
    for comment in soup.find_all(string=lambda t: isinstance(t, Comment)):
        comment.extract()
    # MadCap sidebar / breadcrumb divs
    for sel in [
        "div.MCBreadcrumbsBox_0", "div.MCRelationshipsProxy_0",
        "div.MCTopicToolbar_0", "div.footer", "div#mc-toc",
        "div.sidenav", "div.topic-toolbar",
    ]:
        for el in soup.select(sel):
            el.decompose()


def _node_to_md(node, depth: int = 0) -> str:
    """Recursively convert a BeautifulSoup node to Markdown text."""
    if isinstance(node, Comment):
        return ""
    if isinstance(node, NavigableString):
        return str(node)

    tag: Tag = node
    name = tag.name.lower() if tag.name else ""

    if name in _HEADING_MAP:
        inner = _node_to_md_children(tag, depth)
        return f"\n\n{_HEADING_MAP[name]} {inner.strip()}\n\n"

    if name == "pre":
        code = tag.get_text()
        lang = ""
        code_tag = tag.find("code")
        if code_tag:
            cls = code_tag.get("class", [])
            if cls:
                lang = cls[0].replace("language-", "").replace("lang-", "")
        return f"\n\n```{lang}\n{code.rstrip()}\n```\n\n"

    if name == "code" and tag.parent and tag.parent.name != "pre":
        return f"`{tag.get_text()}`"

    if name in ("p", "div", "section", "article"):
        inner = _node_to_md_children(tag, depth)
        stripped = inner.strip()
        if not stripped:
            return ""
        return f"\n\n{stripped}\n\n"

    if name in ("ul", "ol"):
        items = []
        for i, li in enumerate(tag.find_all("li", recursive=False)):
            bullet = f"{i+1}." if name == "ol" else "-"
            text = _node_to_md_children(li, depth + 1).strip()
            if text:
                items.append(f"{bullet} {text}")
        return "\n" + "\n".join(items) + "\n"

    if name == "li":
        return _node_to_md_children(tag, depth)

    if name == "table":
        rows = tag.find_all("tr")
        md_rows = []
        for r_idx, row in enumerate(rows):
            cells = row.find_all(["th", "td"])
            cell_texts = [
                _node_to_md_children(c, depth).strip().replace("\n", " ")
                for c in cells
            ]
            md_rows.append("| " + " | ".join(cell_texts) + " |")
            if r_idx == 0:
                md_rows.append("|" + "|".join(["---"] * len(cells)) + "|")
        return "\n\n" + "\n".join(md_rows) + "\n\n"

    if name in ("strong", "b"):
        inner = _node_to_md_children(tag, depth)
        return f"**{inner.strip()}**"
    if name in ("em", "i"):
        inner = _node_to_md_children(tag, depth)
        return f"*{inner.strip()}*"

    if name == "a":
        return _node_to_md_children(tag, depth)

    if name == "br":
        return "\n"

    if name == "hr":
        return "\n\n---\n\n"

    return _node_to_md_children(tag, depth)


def _node_to_md_children(tag: Tag, depth: int) -> str:
    return "".join(_node_to_md(child, depth) for child in tag.children)


def _clean_md(text: str) -> str:
    """Post-process Markdown: collapse blank lines, strip trailing whitespace."""
    text = re.sub(r"\n{3,}", "\n\n", text)
    lines = [line.rstrip() for line in text.splitlines()]
    return "\n".join(lines).strip() + "\n"


def _is_madcap(soup: BeautifulSoup) -> bool:
    """Detect if the HTML is MadCap Flare output."""
    return bool(
        soup.find("div", class_=re.compile(r"MC"))
        or soup.find("meta", {"name": "generator", "content": re.compile(r"MadCap", re.I)})
        or soup.find("div", class_="topic-content")
    )


def html_to_md_madcap(html_path: Path) -> str:
    """Parse a MadCap Flare HTML file and return clean Markdown."""
    try:
        raw = html_path.read_bytes()
        soup = BeautifulSoup(raw, "lxml")
    except Exception as e:
        return f"# ERROR reading {html_path.name}\n\n{e}\n"

    _drop_unwanted(soup)

    body = (
        soup.find("div", class_="topic-content")
        or soup.find("div", class_="MCBody")
        or soup.find("div", id="mc-main-content")
        or soup.find("body")
    )
    if body is None:
        return ""

    return _clean_md(_node_to_md(body))


def html_to_md_sphinx(html_path: Path) -> str:
    """Parse a Sphinx HTML file and return clean Markdown."""
    try:
        raw = html_path.read_bytes()
        soup = BeautifulSoup(raw, "lxml")
    except Exception as e:
        return f"# ERROR reading {html_path.name}\n\n{e}\n"

    _drop_unwanted(soup)

    body = (
        soup.find("div", role="main")
        or soup.find("div", class_="body")
        or soup.find("div", class_="document")
        or soup.find("body")
    )
    if body is None:
        return ""

    return _clean_md(_node_to_md(body))


def html_to_md_auto(html_path: Path) -> str:
    """Auto-detect MadCap vs Sphinx and parse accordingly."""
    try:
        raw = html_path.read_bytes()
        soup = BeautifulSoup(raw, "lxml")
    except Exception as e:
        return f"# ERROR reading {html_path.name}\n\n{e}\n"

    if _is_madcap(soup):
        _drop_unwanted(soup)
        body = (
            soup.find("div", class_="topic-content")
            or soup.find("div", class_="MCBody")
            or soup.find("body")
        )
    else:
        _drop_unwanted(soup)
        body = (
            soup.find("div", role="main")
            or soup.find("div", class_="body")
            or soup.find("div", class_="document")
            or soup.find("body")
        )

    if body is None:
        return ""
    return _clean_md(_node_to_md(body))


def process_directory(
    src_dir: Path,
    out_dir: Path,
    fmt: str,
    label: str,
) -> int:
    parsers = {
        "madcap": html_to_md_madcap,
        "sphinx": html_to_md_sphinx,
        "auto":   html_to_md_auto,
    }
    parser = parsers[fmt]

    html_files = list(src_dir.rglob("*.html"))
    count  = 0
    errors = 0
    for f in html_files:
        rel      = f.relative_to(src_dir)
        out_file = out_dir / rel.with_suffix(".md")
        out_file.parent.mkdir(parents=True, exist_ok=True)
        try:
            md = parser(f)
            if md.strip():
                out_file.write_text(md, encoding="utf-8")
                count += 1
        except Exception as e:
            errors += 1
            print(f"  ERROR {f.name}: {e}", file=sys.stderr)

    print(f"  [{label}] {count} .md files written ({errors} errors, {len(html_files)} total HTML)")
    return count


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert HTML documentation to Markdown for RAG indexing.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--input",  "-i", required=True, help="Source directory containing HTML files")
    parser.add_argument("--output", "-o", required=True, help="Output directory for .md files")
    parser.add_argument(
        "--format", "-f",
        choices=["madcap", "sphinx", "auto"],
        default="auto",
        help="HTML format (default: auto-detect)",
    )
    args = parser.parse_args()

    src_dir = Path(args.input)
    out_dir = Path(args.output)

    if not src_dir.exists():
        print(f"ERROR: input directory does not exist: {src_dir}", file=sys.stderr)
        sys.exit(1)

    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n[clean_html] {src_dir} → {out_dir}  (format={args.format})\n")
    count = process_directory(src_dir, out_dir, args.format, label=src_dir.name)
    print(f"\n[clean_html] Done. {count} .md files written to {out_dir}\n")


if __name__ == "__main__":
    main()
