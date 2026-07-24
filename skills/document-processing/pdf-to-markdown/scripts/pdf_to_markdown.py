"""
PDF to Markdown Converter
使用 pymupdf4llm 将 PDF 转换为适合 LLM/AI 阅读的 Markdown 格式。

用法:
    python scripts/pdf_to_markdown.py <pdf_path> [选项]

示例:
    python scripts/pdf_to_markdown.py datasheet/"Infiniium UXR-Series Oscilloscopes.pdf"
    python scripts/pdf_to_markdown.py datasheet/some.pdf --output notes/some.md
    python scripts/pdf_to_markdown.py datasheet/some.pdf --pages 1-5
    python scripts/pdf_to_markdown.py datasheet/some.pdf --no-images
"""

import argparse
import sys
import time
from pathlib import Path


def parse_page_range(page_str: str, total_pages: int) -> list[int]:
    """解析页码范围字符串，如 '1-5,7,9-11'，返回 0-indexed 页码列表。"""
    pages = []
    for part in page_str.split(","):
        part = part.strip()
        if "-" in part:
            start, end = part.split("-", 1)
            pages.extend(range(int(start) - 1, min(int(end), total_pages)))
        else:
            page_num = int(part) - 1
            if 0 <= page_num < total_pages:
                pages.append(page_num)
    return sorted(set(pages))


def convert(
    pdf_path: Path,
    output_path: Path,
    pages: list[int] | None = None,
    show_progress: bool = True,
) -> None:
    try:
        import pymupdf4llm
        import pymupdf
    except ImportError:
        print("错误：缺少依赖，请运行：pip install pymupdf4llm")
        sys.exit(1)

    print(f"输入:  {pdf_path}")
    print(f"输出:  {output_path}")

    doc = pymupdf.open(str(pdf_path))
    total = doc.page_count
    doc.close()
    print(f"总页数: {total}")

    if pages:
        print(f"转换页码: {[p + 1 for p in pages]}")
    else:
        print("转换页码: 全部")

    t0 = time.time()

    md_text = pymupdf4llm.to_markdown(
        str(pdf_path),
        pages=pages,
        show_progress=show_progress,
        # 保留表格结构（pipe table 格式）
        table_strategy="lines_strict",
        # 保留页眉页脚信息
        page_chunks=False,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(md_text, encoding="utf-8")

    elapsed = time.time() - t0
    size_kb = output_path.stat().st_size / 1024
    print(f"\n完成！耗时 {elapsed:.1f}s，输出 {size_kb:.1f} KB → {output_path}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="将 PDF 转换为 Markdown（使用 pymupdf4llm）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("pdf", help="输入 PDF 文件路径")
    parser.add_argument(
        "--output", "-o",
        help="输出 Markdown 文件路径（默认：与 PDF 同目录，同名 .md）",
    )
    parser.add_argument(
        "--pages", "-p",
        help="指定页码范围，如 '1-5' 或 '1,3,5-10'（默认：全部）",
    )
    parser.add_argument(
        "--no-progress",
        action="store_true",
        help="不显示进度条",
    )
    args = parser.parse_args()

    pdf_path = Path(args.pdf).resolve()
    if not pdf_path.exists():
        print(f"错误：文件不存在：{pdf_path}")
        sys.exit(1)
    if pdf_path.suffix.lower() != ".pdf":
        print(f"错误：不是 PDF 文件：{pdf_path}")
        sys.exit(1)

    if args.output:
        output_path = Path(args.output).resolve()
        if output_path.is_dir():
            output_path = output_path / (pdf_path.stem + ".md")
    else:
        output_path = pdf_path.with_suffix(".md")

    pages = None
    if args.pages:
        try:
            import pymupdf
            doc = pymupdf.open(str(pdf_path))
            total = doc.page_count
            doc.close()
            pages = parse_page_range(args.pages, total)
            if not pages:
                print("错误：页码范围无效或超出文档范围")
                sys.exit(1)
        except Exception as e:
            print(f"错误：无法解析页码范围：{e}")
            sys.exit(1)

    convert(
        pdf_path=pdf_path,
        output_path=output_path,
        pages=pages,
        show_progress=not args.no_progress,
    )


if __name__ == "__main__":
    main()
