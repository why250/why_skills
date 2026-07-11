"""Evaluate simulation CSV outputs against specs; patch netlist whitelist params.

Stdlib only — no keysight packages.
"""

from __future__ import annotations

import csv
import json
import math
import re
from pathlib import Path
from typing import Any


def load_specs(path: Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_verdict(verdict: dict[str, Any], path: Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(verdict, indent=2) + "\n", encoding="utf-8")


def _read_csv_rows(path: Path) -> list[dict[str, float]]:
    with path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        rows: list[dict[str, float]] = []
        for row in reader:
            rows.append({k: float(v) for k, v in row.items() if v not in (None, "")})
        return rows


def _resolve_csv(output_dir: Path, pattern: str) -> Path:
    matches = sorted(output_dir.glob(pattern))
    if not matches:
        raise FileNotFoundError(f"No CSV matching {pattern!r} under {output_dir}")
    return matches[0]


def _metric_value(metric: dict[str, Any], tables: dict[str, list[dict[str, float]]], vac: float) -> float:
    source = metric["source"]
    rows = tables[source]
    if not rows:
        raise ValueError(f"No rows for source {source!r}")

    op = metric["op"]
    if op == "max":
        col = metric["column"]
        return max(r[col] for r in rows)
    if op == "min":
        col = metric["column"]
        return min(r[col] for r in rows)
    if op == "mean":
        col = metric["column"]
        return sum(r[col] for r in rows) / len(rows)
    if op == "last":
        return rows[-1][metric["column"]]
    if op == "abs_max":
        col = metric["column"]
        return max(abs(r[col]) for r in rows)
    if op == "magnitude_max":
        real_column = metric["real_column"]
        imag_column = metric["imag_column"]
        return max(math.hypot(r[real_column], r[imag_column]) for r in rows)
    if op == "gm_max":
        re_col = metric.get("re_column", "IC.i_re")
        im_col = metric.get("im_column", "IC.i_im")
        if vac <= 0:
            raise ValueError("vac_amplitude_v must be > 0")
        return max(math.hypot(r[re_col], r[im_col]) / vac for r in rows)
    raise ValueError(f"Unsupported metric op: {op!r}")


def _check_limits(value: float, metric: dict[str, Any]) -> tuple[bool, str]:
    reasons: list[str] = []
    passed = True
    if "min" in metric and value < float(metric["min"]):
        passed = False
        reasons.append(f"value {value} < min {metric['min']}")
    if "max" in metric and value > float(metric["max"]):
        passed = False
        reasons.append(f"value {value} > max {metric['max']}")
    return passed, "; ".join(reasons) if reasons else "ok"


def evaluate_specs(specs: dict[str, Any], output_dir: Path | str) -> dict[str, Any]:
    """Compute metrics from CSV files in output_dir and return a verdict dict."""
    output_dir = Path(output_dir)
    globs = specs.get("csv_globs") or {}
    tables: dict[str, list[dict[str, float]]] = {}
    csv_used: dict[str, str] = {}
    for key, pattern in globs.items():
        path = _resolve_csv(output_dir, pattern)
        tables[key] = _read_csv_rows(path)
        csv_used[key] = str(path)

    vac = float(specs.get("vac_amplitude_v", 0.001))
    results: list[dict[str, Any]] = []
    failed: list[str] = []

    for metric in specs.get("metrics") or []:
        value = _metric_value(metric, tables, vac)
        passed, reason = _check_limits(value, metric)
        entry = {
            "id": metric["id"],
            "description": metric.get("description", ""),
            "priority": metric.get("priority", "must"),
            "value": value,
            "min": metric.get("min"),
            "max": metric.get("max"),
            "passed": passed,
            "reason": reason,
        }
        results.append(entry)
        if not passed and entry["priority"] == "must":
            failed.append(metric["id"])

    all_passed = len(failed) == 0
    return {
        "schema_version": "sim-verdict/v1",
        "all_passed": all_passed,
        "failed": failed,
        "metrics": results,
        "csv_files": csv_used,
        "allowed_params": list(specs.get("allowed_params") or []),
        "llm_hint": (
            "Read failed metrics and propose new values only for allowed_params; "
            "then re-run simulation. Do not invent undocumented parameters."
            if not all_passed
            else "All must-metrics passed; stop or tighten specs."
        ),
    }


_PARAM_LINE_RE = re.compile(
    r"^(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*=\s*(?P<value>[^\n]*)$",
    re.MULTILINE,
)

_ADS_UNIT_SCALE = {
    "t": 1e12,
    "g": 1e9,
    "meg": 1e6,
    "k": 1e3,
    "m": 1e-3,
    "u": 1e-6,
    "n": 1e-9,
    "p": 1e-12,
    "f": 1e-15,
}


def parse_ads_scalar(text: str) -> float:
    """Parse ADS netlist scalars like '200 uA', '20e-6', '5'."""
    raw = text.strip()
    if not raw:
        raise ValueError("empty ADS scalar")
    # Drop trailing unit letters after a known engineering prefix token.
    parts = raw.replace("\t", " ").split()
    if len(parts) == 1:
        token = parts[0]
        # e.g. 200uA / 20e-6
        match = re.fullmatch(
            r"(?P<num>[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?)\s*(?P<unit>[A-Za-z]*)",
            token,
        )
        if not match:
            return float(token)
        num = float(match.group("num"))
        unit = match.group("unit").lower()
        if not unit:
            return num
        # strip physical unit suffix (a, v, hz, ohm, ...) keep engineering prefix
        for prefix, scale in sorted(_ADS_UNIT_SCALE.items(), key=lambda kv: -len(kv[0])):
            if unit.startswith(prefix):
                return num * scale
        return num

    num = float(parts[0])
    unit = parts[1].lower()
    for prefix, scale in sorted(_ADS_UNIT_SCALE.items(), key=lambda kv: -len(kv[0])):
        if unit.startswith(prefix):
            return num * scale
    return num


def format_ads_scalar(value_si: float, unit: str | None = None) -> str:
    """Format a SI value for netlist assignment; unit examples: 'uA', 'V'."""
    if not unit:
        return f"{value_si:.12g}"
    u = unit.strip()
    ul = u.lower()
    scale = 1.0
    eng = ""
    for prefix, pref_scale in sorted(_ADS_UNIT_SCALE.items(), key=lambda kv: -len(kv[0])):
        if ul.startswith(prefix):
            scale = pref_scale
            eng = prefix
            break
    display = value_si / scale if scale else value_si
    # Prefer compact integers when close
    if abs(display - round(display)) < 1e-9:
        display_s = str(int(round(display)))
    else:
        display_s = f"{display:.12g}"
    return f"{display_s} {u}"


def apply_netlist_params(
    netlist_path: Path | str,
    params: dict[str, Any],
    allowed: list[str] | None = None,
    param_units: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Update `Name=value` lines in a netlist for whitelist params only.

    Returns the dict of parameters actually changed (formatted values).
    """
    netlist_path = Path(netlist_path)
    text = netlist_path.read_text(encoding="utf-8")
    allowed_set = set(allowed) if allowed is not None else set(params)
    units = param_units or {}
    changed: dict[str, Any] = {}

    for name, value in params.items():
        if name not in allowed_set:
            continue
        pattern = re.compile(rf"^(?P<prefix>{re.escape(name)}\s*=\s*)(?P<val>[^\n]*)$", re.MULTILINE)
        if not pattern.search(text):
            continue
        if isinstance(value, str):
            written = value
        elif name in units:
            written = format_ads_scalar(float(value), units[name])
        else:
            written = format_ads_scalar(float(value))
        text = pattern.sub(rf"\g<prefix>{written}", text, count=1)
        changed[name] = written

    if changed:
        netlist_path.write_text(text, encoding="utf-8", newline="")
    return changed


def read_netlist_params(netlist_path: Path | str, names: list[str]) -> dict[str, float]:
    """Read simple Name=value assignments from a netlist as SI floats."""
    text = Path(netlist_path).read_text(encoding="utf-8")
    found: dict[str, float] = {}
    for name in names:
        match = re.search(rf"^{re.escape(name)}\s*=\s*([^\n]+)$", text, re.MULTILINE)
        if match:
            found[name] = parse_ads_scalar(match.group(1))
    return found


def suggest_param_updates(
    verdict: dict[str, Any],
    specs: dict[str, Any],
    current_params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Deterministic demo suggestions when metrics fail (not an LLM)."""
    allowed = set(verdict.get("allowed_params") or specs.get("allowed_params") or [])
    suggestions: dict[str, Any] = {}
    defaults = dict(specs.get("param_defaults") or {})
    if current_params:
        defaults.update({k: float(v) for k, v in current_params.items()})
    steps = specs.get("param_steps") or {}
    units = specs.get("param_units") or {}
    floors = specs.get("param_floors") or {}
    ceilings = specs.get("param_ceilings") or {}

    metrics_by_id = {m["id"]: m for m in (verdict.get("metrics") or [])}
    failed_ids = set(verdict.get("failed") or [])

    # Legacy VCE rule
    if failed_ids & {"gm_max"} and "VCE_Stop" in allowed and "IBB_Stop" not in allowed:
        base = float(defaults.get("VCE_Stop", 5.0))
        step = float(steps.get("VCE_Stop", 1.0))
        suggestions["VCE_Stop"] = base + abs(step)

    # IBB_Stop: decrease when ic_max exceeds max; increase when below min
    if "ic_max" in failed_ids and "IBB_Stop" in allowed:
        base = float(defaults.get("IBB_Stop", 200e-6))
        step = abs(float(steps.get("IBB_Stop", 20e-6)))
        metric = metrics_by_id.get("ic_max") or {}
        if metric.get("max") is not None and float(metric["value"]) > float(metric["max"]):
            nxt = base - step
        elif metric.get("min") is not None and float(metric["value"]) < float(metric["min"]):
            nxt = base + step
        else:
            nxt = base - step
        if "IBB_Stop" in floors:
            nxt = max(nxt, float(floors["IBB_Stop"]))
        if "IBB_Stop" in ceilings:
            nxt = min(nxt, float(ceilings["IBB_Stop"]))
        if abs(nxt - base) > 0:
            unit = units.get("IBB_Stop")
            suggestions["IBB_Stop"] = format_ads_scalar(nxt, unit) if unit else nxt

    return suggestions


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Evaluate sim CSV metrics / patch netlist params")
    sub = parser.add_subparsers(dest="cmd", required=True)

    ev = sub.add_parser("evaluate", help="Evaluate specs against CSV output dir")
    ev.add_argument("--specs", type=Path, required=True)
    ev.add_argument("--output-dir", type=Path, required=True)
    ev.add_argument("--verdict", type=Path, required=True)
    ev.add_argument("--suggest", action="store_true")
    ev.add_argument(
        "--netlist",
        type=Path,
        default=None,
        help="Optional netlist to read current allowed_params for suggestions",
    )

    ap = sub.add_parser("apply", help="Apply whitelist params to a netlist file")
    ap.add_argument("--netlist", type=Path, required=True)
    ap.add_argument("--params", type=Path, required=True, help="JSON object of Name->value")
    ap.add_argument(
        "--allowed",
        type=Path,
        required=True,
        help="JSON list or specs.json containing allowed_params",
    )

    args = parser.parse_args(argv)

    if args.cmd == "evaluate":
        specs = load_specs(args.specs)
        verdict = evaluate_specs(specs, args.output_dir)
        if args.suggest:
            current = None
            if args.netlist and Path(args.netlist).is_file():
                current = read_netlist_params(
                    args.netlist, list(specs.get("allowed_params") or [])
                )
            verdict["suggested_params"] = suggest_param_updates(verdict, specs, current)
            verdict["current_params"] = current or {}
        write_verdict(verdict, args.verdict)
        print(
            json.dumps(
                {
                    "all_passed": verdict["all_passed"],
                    "failed": verdict["failed"],
                    "suggested_params": verdict.get("suggested_params"),
                },
                indent=2,
            )
        )
        return 0 if verdict["all_passed"] else 2

    if args.cmd == "apply":
        params = json.loads(Path(args.params).read_text(encoding="utf-8-sig"))
        allowed_raw = json.loads(Path(args.allowed).read_text(encoding="utf-8-sig"))
        param_units = None
        if isinstance(allowed_raw, dict):
            allowed = list(allowed_raw.get("allowed_params") or [])
            param_units = allowed_raw.get("param_units")
        else:
            allowed = list(allowed_raw)
        changed = apply_netlist_params(
            args.netlist, params, allowed=allowed, param_units=param_units
        )
        print(json.dumps({"changed": changed}, indent=2))
        return 0 if changed else 1

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
