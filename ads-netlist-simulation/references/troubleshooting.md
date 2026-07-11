# Troubleshooting

## Classify before editing

| Evidence | State | Next action |
| --- | --- | --- |
| ADS already running | Session safety | Save work and close interactive ADS before running the AEL generator |
| ERROR_DESIGN | Physical/logical name mapping | Pass the logical ADS cell name with -CellName |
| AEL netlisting timeout | ADS startup/context | Check ADS startup logs, workspace validity, PDK loading, and stale ADS processes |
| Executable missing | Environment | Rerun `initialize_ads.ps1`; pass the ADS root if discovery fails |
| License/codeword message | License | Verify `ADS_LICENSE_FILE` or site licensing; do not edit the circuit |
| Parse error / no simulation component | Netlist syntax | Check `hpeesofsim_stdout.log`, BOM, continuations, controller syntax, and ADS Help RAG |
| Nonconvergence | Numerical/model | Retrieve controller-specific convergence guidance; change one justified option at a time |
| Exit 0 but no `.ds` | Output configuration | Check `TopDesignName`, current working directory, controller presence, and log |
| Dataset exists but CSV does not | Export | Run `dsdump`; verify `ds_export.exe` and MDIF blocks |
| Metrics fail | Design/specification | Inspect `verdict.json`; update only allowed parameters |

## High-value checks

- Keep `netlist.log` UTF-8 without BOM.
- Expect hpeesofsim to require at least a Linear Simulator feature; other analyses can require additional features. A tool-path check alone cannot prove license availability.
- Resolve relative `#include` paths from the simulator working directory or use absolute paths.
- Confirm engineering suffixes and verify ambiguous units in generated netlists or ADS Help.
- Use `ASCII_Rawfile=yes` only for text inspection; CSV remains easier for structured calculations.
- Keep `TopDesignName="library:cell:view"` because the cell name drives the dataset filename.
- Search ADS Help RAG with the exact first error line plus the controller token.
