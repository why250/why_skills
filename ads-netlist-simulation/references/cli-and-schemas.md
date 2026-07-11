# CLI and schema reference

Read this file when invoking the bundled scripts or defining metrics and plots.

## Runtime configuration

`initialize_ads.ps1` writes `config.json` under `%LOCALAPPDATA%\Codex\ads-netlist-simulation` by default. Pass `-ConfigPath` to keep configuration elsewhere. The saved file records the ADS root, simulator architecture, optional license setting, and resolved CLI tools. Rerun with `-Force` after an ADS upgrade.

All PowerShell entrypoints accept `-AdsInstallDir` and `-ConfigPath`. An explicit install directory takes priority over the saved value.

## Run layout

When OutputRoot is omitted, read the cell name from the netlist TopDesignName
field and use `ProjectRoot/example/design-name/output`. Capture ProjectRoot
from `$PWD` before accessing the ADS workspace and pass `-ProjectRoot` to
run_netlist.ps1 or run_closed_loop.ps1. This prevents an execution wrapper that
changes its working directory to the ADS workspace from redirecting outputs.
If ProjectRoot is omitted, fall back to the process's current working directory.
Passing OutputRoot keeps working as an explicit override, and run_netlist.ps1
OutputDir remains the most specific override.

Each run uses:

```text
output/runs/<run-id>/
  01_sim/   netlist copy, hpeesofsim log, .ds, rawfile
  02_data/  CSV or other dataset exports
  03_loop/  working netlist, verdicts, parameter proposals, summary
```

`output/runs/latest.json` points to the newest run. Pass `-RunId` for reproducible names or `-RunDir` to resume a run.

## Dataset export

Use `export_ds.ps1` with `csv` (default), `gmdif`, `citifile`, `touchstone`, `smatrixio`, or `dsdump`. CSV conversion uses `ds_export -t gmdif` followed by the standard-library `mdif_to_csv.py`. Keep MDIF with `-KeepMdif` when its block structure matters.

## Metric specification

Use `sim-metrics/v1` JSON:

```json
{
  "schema_version": "sim-metrics/v1",
  "csv_globs": {"dc": "*_DC1.DC.csv"},
  "metrics": [
    {"id": "ic_max", "source": "dc", "op": "max", "column": "IC.i", "max": 0.02, "priority": "must"}
  ],
  "allowed_params": ["IBB_Stop"],
  "param_units": {"IBB_Stop": "uA"}
}
```

Supported operations are `max`, `min`, `mean`, `last`, `abs_max`, `magnitude_max`, and the example-specific `gm_max`. `magnitude_max` requires `real_column` and `imag_column`. A metric can contain `min`, `max`, or both. Only failed metrics with `priority: "must"` fail the verdict.

Keep each metric deterministic. Translate DDS equations explicitly into Python when the built-ins are insufficient. Do not evaluate arbitrary Python expressions from JSON.

`allowed_params` is a security and correctness boundary. `metrics.py apply` ignores every proposed key outside it and only edits simple top-level `Name=value` lines.

The bundled BJT example separates purposes: `specs.json` is a baseline multi-metric check, while `specs-loop.json` demonstrates a one-parameter `ic_max <= 0.018 A` optimization loop.

## Plot specification

Add `plots` to the same JSON or use a separate file that repeats `csv_globs`:

```json
{
  "csv_globs": {"dc": "*_Sweep1.DC1.DC.csv"},
  "plots": [
    {
      "source": "dc",
      "x": "VCE",
      "group_by": "IBB",
      "series": [{"y": "IC.i", "label": "Ic"}],
      "title": "BJT output characteristics",
      "x_label": "VCE (V)",
      "y_label": "IC (A)",
      "output": "bjt_iv.png"
    }
  ]
}
```

For a complex trace, use `{"real": "S[2,1]_re", "imag": "S[2,1]_im", "label": "|S21|"}`. Supported plot controls include `x_scale`, `y_scale`, `figsize`, `dpi`, `marker`, and `legend`. Install matplotlib only when plotting is requested.
