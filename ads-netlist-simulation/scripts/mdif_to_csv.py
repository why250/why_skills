"""Convert ADS gmdif (generic MDIF) text to per-varblock CSV files.

Uses only the Python standard library — no keysight packages.
"""

from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import Any

_VAR_RE = re.compile(
    r"^VAR\s+(?P<name>[^\s(]+)\s*\((?P<type>[^)]+)\)\s*=\s*(?P<value>.+?)\s*$"
)
_BEGIN_RE = re.compile(r"^BEGIN\s+(?P<name>\S+)\s*$")
_HEADER_RE = re.compile(r"^%\s*(?P<body>.+?)\s*$")
_COL_RE = re.compile(r"([^\s(]+)\(([^)]+)\)")


def _parse_number(token: str) -> float:
    return float(token)


def _strip_col_name(raw: str) -> tuple[str, str]:
    """Return (name, type) from 'VCE(real)' or 'IC.i(complex)'."""
    match = _COL_RE.fullmatch(raw.strip())
    if not match:
        return raw.strip(), "real"
    return match.group(1), match.group(2).lower()


def parse_mdif_blocks(text: str) -> dict[str, dict[str, Any]]:
    """Parse gmdif text into {block_name: {columns, rows}}."""
    blocks: dict[str, dict[str, Any]] = {}
    outer_vars: dict[str, float] = {}
    pending_vars: dict[str, float] = {}

    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        i += 1
        if not line or line.startswith("!"):
            continue

        var_match = _VAR_RE.match(line)
        if var_match:
            pending_vars[var_match.group("name")] = _parse_number(var_match.group("value"))
            continue

        begin_match = _BEGIN_RE.match(line)
        if not begin_match:
            if line.upper() == "END":
                continue
            continue

        block_name = begin_match.group("name")
        outer_vars = dict(pending_vars)
        pending_vars = {}

        if i >= len(lines):
            break
        header_line = lines[i].strip()
        i += 1
        header_match = _HEADER_RE.match(header_line)
        if not header_match:
            raise ValueError(f"Expected % header after BEGIN {block_name}, got: {header_line!r}")

        col_specs = [_strip_col_name(part) for part in header_match.group("body").split()]
        columns: list[str] = list(outer_vars.keys())
        for name, typ in col_specs:
            if typ == "complex":
                columns.extend([f"{name}_re", f"{name}_im"])
            else:
                columns.append(name)

        rows: list[list[float]] = []
        while i < len(lines):
            data_line = lines[i].strip()
            i += 1
            if not data_line:
                continue
            if data_line.upper() == "END":
                break
            if _BEGIN_RE.match(data_line) or _VAR_RE.match(data_line):
                # Defensive: unexpected; push back conceptually by stopping.
                i -= 1
                break

            tokens = data_line.split()
            values: list[float] = [outer_vars[k] for k in outer_vars]
            token_idx = 0
            for _name, typ in col_specs:
                if typ == "complex":
                    values.append(_parse_number(tokens[token_idx]))
                    values.append(_parse_number(tokens[token_idx + 1]))
                    token_idx += 2
                else:
                    values.append(_parse_number(tokens[token_idx]))
                    token_idx += 1
            rows.append(values)

        if block_name not in blocks:
            blocks[block_name] = {"columns": columns, "rows": rows}
        else:
            existing = blocks[block_name]
            if existing["columns"] != columns:
                raise ValueError(
                    f"Column mismatch for block {block_name}: "
                    f"{existing['columns']} vs {columns}"
                )
            existing["rows"].extend(rows)

    return blocks


def _safe_filename(block_name: str) -> str:
    return re.sub(r"[^\w.\-]+", "_", block_name)


def convert_mdif_to_csv(mdif_path: Path, output_dir: Path | None = None) -> list[Path]:
    """Convert a .mdf/.mdif file to one CSV per BEGIN block. Returns written paths."""
    mdif_path = Path(mdif_path)
    output_dir = Path(output_dir) if output_dir is not None else mdif_path.parent
    output_dir.mkdir(parents=True, exist_ok=True)

    text = mdif_path.read_text(encoding="utf-8", errors="replace")
    blocks = parse_mdif_blocks(text)
    stem = mdif_path.stem
    written: list[Path] = []

    for block_name, payload in blocks.items():
        out_path = output_dir / f"{stem}_{_safe_filename(block_name)}.csv"
        with out_path.open("w", encoding="utf-8", newline="") as fh:
            writer = csv.writer(fh)
            writer.writerow(payload["columns"])
            writer.writerows(payload["rows"])
        written.append(out_path)

    return written


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Convert ADS gmdif (.mdf) to CSV files.")
    parser.add_argument("mdif_path", type=Path)
    parser.add_argument("-o", "--output-dir", type=Path, default=None)
    args = parser.parse_args(argv)

    paths = convert_mdif_to_csv(args.mdif_path, args.output_dir)
    for path in paths:
        print(path)
    return 0 if paths else 1


if __name__ == "__main__":
    raise SystemExit(main())
