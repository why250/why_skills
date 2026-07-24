---
name: ads-netlist-simulation
description: Generate Keysight ADS netlists from schematic design paths through a cross-version AEL command-line launcher, then run text-first hpeesofsim workflows with logs, ADS datasets, CSV conversion, metric evaluation, plotting, and bounded parameter optimization. Use for ADS schematic directory paths, netlist.log or .ds work, AC/DC/SP/HB command-line simulation, DDS-to-Python metric translation, simulator diagnosis, and parameter iteration. Supports ADS 2022/2025 without keysight.ads.de or third-party Python packages for netlist generation.
---

# ADS Netlist Simulation

Treat ADS as a simulator backend: generate or edit text netlists, run deterministic scripts, inspect text logs and CSV, and change only explicit parameters. Prefer an ADS-generated working netlist over synthesizing a full design from memory.

## Run the workflow

1. Before inspecting or opening an ADS workspace, capture the user's current project directory once:

       $projectRoot = [System.IO.Path]::GetFullPath((Get-Location).Path)

   Keep this value unchanged for the entire workflow. Use absolute ADS design and netlist paths. Never change a tool call's working directory to the ADS workspace; if an execution wrapper requires another working directory, still pass `-ProjectRoot $projectRoot` to the bundled run scripts.
2. Initialize ADS once:

       powershell -ExecutionPolicy Bypass -File <skill-dir>\scripts\initialize_ads.ps1

   Let the script auto-discover ADS and save the result in the user-local config. If discovery fails, inspect likely Keysight install roots, then ask the user for the ADS install directory and rerun with -AdsInstallDir. Do not repeatedly search on later turns.

3. When the input is a schematic directory, generate the workspace netlist:

       powershell -ExecutionPolicy Bypass -File <skill-dir>\scripts\generate_netlist.ps1 -DesignPath "D:\ADS\demo_wrk\demo_lib\%MyCell\schematic"

   Default to workspace/netlist.log. Existing ADS sessions may remain open: the startup AEL verifies its PID before touching a workspace, and the launcher tracks only the newly-created ADS process. Read [references/ael-netlisting.md](references/ael-netlisting.md) when changing this path or supporting an unusual OA physical cell name. Pass -CellName when percent-marker decoding does not produce the logical ADS cell name.
4. Copy the source netlist before modifying it. Preserve UTF-8 without BOM because a BOM can break hpeesofsim parsing.
5. Establish a baseline:

       powershell -ExecutionPolicy Bypass -File <skill-dir>\scripts\run_netlist.ps1 -NetlistPath <workspace>\netlist.log -ProjectRoot $projectRoot

   Default outputs to the captured project directory: `$projectRoot/example/design-name/output/runs/RunId`. Require both a zero simulator exit code and a produced .ds file. Read hpeesofsim_stdout.log before changing the netlist after any failure.
6. Export the dataset to CSV:

       powershell -ExecutionPolicy Bypass -File <skill-dir>\scripts\export_ds.ps1 -DatasetPath <run>\01_sim\<cell>.ds

7. Define stable metrics and plot mappings in JSON. Read [references/cli-and-schemas.md](references/cli-and-schemas.md) when creating or changing these files. If the user provides a .dds, use its equations and traces as requirements, but implement them in Python rather than automating Data Display.
8. Run a bounded loop only after a baseline passes and the allowed parameter names are explicit:

       powershell -ExecutionPolicy Bypass -File <skill-dir>\scripts\run_closed_loop.ps1 -NetlistPath <workspace>\netlist.log -ProjectRoot $projectRoot -SpecsPath <design>\specs.json -MaxIterations 3

   Without -AutoSuggest, inspect the verdict and choose the next values. With -AutoSuggest, treat the bundled rules as demonstrations, not a general optimizer.
9. Stop when all required metrics pass, the iteration limit is reached, simulation fails, or no justified parameter change remains. Report the generated/source netlist, run directory, metric verdict, and plot paths.

## Use ADS Help RAG

Query the ads2025_help MCP search_docs tool when ADS syntax, controller options, model syntax, convergence settings, or dataset behavior is uncertain. Use category simulation for hpeesofsim, AC/DC/SP/HB, sweeps, and convergence. Search with the exact component or option token. Prefer retrieved examples or an ADS-generated netlist over guessed syntax.

Read [references/netlist-syntax.md](references/netlist-syntax.md) for common netlist patterns. Treat it as a routing guide, not a substitute for RAG or a generated netlist. Verify undocumented or version-sensitive syntax with ADS Help.

## Guardrails

- Change only parameters named in allowed_params; never let an optimizer rewrite arbitrary netlist text.
- Preserve the original netlist and create a run-specific working copy.
- Keep user formulas, units, sweep domains, and pass/fail direction explicit. Ask for missing design intent rather than inventing a metric.
- Use bounded sweeps and iterations.
- Use AEL startup netlisting only when the input is an ADS design path; keep simulation and post-processing outside the GUI.
- Verify AEL process isolation before workspace operations, and never stop a pre-existing ADS PID.
- Preserve the initial project directory in `-ProjectRoot`; never derive simulation output from the ADS workspace directory.
- Treat netlisting, license, parse, convergence, and failed-specification states separately.
- Read [references/troubleshooting.md](references/troubleshooting.md) for common failure signatures.

## Reuse bundled resources

- Execute scripts directly; do not paste their implementations into the conversation.
- Start from examples/bjt-gm when learning the file contracts. Copy it into the design workspace before editing.
- Extend metrics.py only when the requested metric cannot be represented by existing operations.
- Use plot_results.py with a plot specification instead of writing a new plotting program for ordinary XY, grouped sweep, or complex-magnitude plots.
