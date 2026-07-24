"""Plot ADS CSV sweep results from a declarative JSON specification."""

from __future__ import annotations

import argparse
import csv
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any


def load_numeric_rows(path: Path) -> list[dict[str, float]]:
    """Load a CSV table and convert populated cells to floats."""
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return [
            {key: float(value) for key, value in row.items() if value not in (None, "")}
            for row in reader
        ]


def resolve_table(data_dir: Path, pattern: str) -> Path:
    """Return the first deterministic CSV match for a configured glob."""
    matches = sorted(data_dir.glob(pattern))
    if not matches:
        raise FileNotFoundError(f"No CSV matching {pattern!r} under {data_dir}")
    return matches[0]


def series_value(row: dict[str, float], series: dict[str, Any]) -> float:
    """Evaluate a safe built-in series mapping for one row."""
    if "y" in series:
        return row[series["y"]]
    if "real" in series and "imag" in series:
        return math.hypot(row[series["real"]], row[series["imag"]])
    raise ValueError("Each series needs either 'y' or both 'real' and 'imag'")


def render_plots(specs_path: Path, data_dir: Path, output_dir: Path) -> list[Path]:
    """Render every configured plot and return the image paths."""
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError as exc:
        raise RuntimeError("matplotlib is required: python -m pip install matplotlib") from exc

    specs = json.loads(specs_path.read_text(encoding="utf-8-sig"))
    csv_globs = specs.get("csv_globs") or {}
    output_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []

    for index, plot in enumerate(specs.get("plots") or [], start=1):
        source = plot["source"]
        table_path = resolve_table(data_dir, csv_globs[source])
        rows = load_numeric_rows(table_path)
        if not rows:
            raise ValueError(f"No rows in {table_path}")

        group_column = plot.get("group_by")
        grouped: dict[float | None, list[dict[str, float]]] = defaultdict(list)
        for row in rows:
            grouped[row[group_column] if group_column else None].append(row)

        figure, axis = plt.subplots(figsize=tuple(plot.get("figsize", [8, 5])))
        x_column = plot["x"]
        sort_key = lambda item: (item[0] is not None, item[0])
        for group_value, group_rows in sorted(grouped.items(), key=sort_key):
            ordered = sorted(group_rows, key=lambda row: row[x_column])
            for series in plot["series"]:
                base_label = (
                    series.get("label")
                    or series.get("y")
                    or f"|{series['real']}+j{series['imag']}|"
                )
                label = (
                    f"{base_label}, {group_column}={group_value:g}"
                    if group_column
                    else base_label
                )
                axis.plot(
                    [row[x_column] for row in ordered],
                    [series_value(row, series) for row in ordered],
                    label=label,
                    marker=series.get("marker"),
                )

        axis.set_title(plot.get("title", ""))
        axis.set_xlabel(plot.get("x_label", x_column))
        axis.set_ylabel(plot.get("y_label", ""))
        axis.set_xscale(plot.get("x_scale", "linear"))
        axis.set_yscale(plot.get("y_scale", "linear"))
        axis.grid(True, which="both", alpha=0.3)
        if plot.get("legend", True):
            axis.legend(fontsize="small")
        figure.tight_layout()

        output_name = plot.get("output", f"plot_{index}.png")
        output_path = output_dir / output_name
        figure.savefig(output_path, dpi=int(plot.get("dpi", 150)))
        plt.close(figure)
        written.append(output_path)
    return written


def main(argv: list[str] | None = None) -> int:
    """Run the plot CLI."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--specs", type=Path, required=True)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    for path in render_plots(args.specs, args.data_dir, args.output_dir):
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
