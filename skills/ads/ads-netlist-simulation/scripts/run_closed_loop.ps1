#Requires -Version 5.1
<#
.SYNOPSIS
  Closed loop: simulate netlist -> CSV -> metrics verdict -> optional param update -> repeat.

.DESCRIPTION
  Artifacts are separated under one run directory:

    output/runs/<RunId>/
      01_sim/    hpeesofsim outputs (.ds, spectra.raw, logs)
      02_data/   CSV (and optional export formats)
      03_loop/   verdict / params / working netlist / summary

.PARAMETER RunDir
  Existing run root. If empty, creates
  <current-directory>/example/<design-name>/output/runs/<timestamp>.

.PARAMETER ProjectRoot
  Original caller directory captured before accessing the ADS workspace. When
  OutputRoot is empty, use ProjectRoot instead of the process's possibly
  changed current directory.

.PARAMETER SkipSimulate
  Evaluate existing 02_data CSV only (no hpeesofsim). Requires CSVs present
  or flat legacy files that can be imported with -ImportLegacyFlat.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$NetlistPath,
    [string]$AdsInstallDir = "",
    [string]$ConfigPath = "",
    [string]$ProjectRoot = "",
    [string]$OutputRoot = "",
    [string]$RunDir = "",
    [string]$RunId = "",
    [string]$SpecsPath = "",
    [int]$MaxIterations = 3,
    [switch]$AutoSuggest,
    [switch]$SkipSimulate,
    [switch]$ImportLegacyFlat
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
. (Join-Path $scriptDir "run_layout.ps1")
. (Join-Path $scriptDir "ads_env.ps1")

if (-not (Test-Path -LiteralPath $NetlistPath -PathType Leaf)) {
    throw "Netlist not found: $NetlistPath"
}
$runtime = Resolve-AdsRuntime -AdsInstallDir $AdsInstallDir -ConfigPath $ConfigPath
$AdsInstallDir = $runtime.AdsInstallDir
if (-not $OutputRoot) {
    $OutputRoot = Get-AdsCliOutputRoot -NetlistPath $NetlistPath -BaseDirectory $ProjectRoot
}
$outputRoot = [System.IO.Path]::GetFullPath($OutputRoot)
if (-not $SpecsPath) { $SpecsPath = Join-Path $scriptDir "..\examples\bjt-gm\specs.json" }

$pythonCandidates = @(
    (Join-Path (Get-Location) ".venv\Scripts\python.exe"),
    "python"
)
function Get-Python {
    foreach ($c in $pythonCandidates) {
        if ($c -eq "python") { return "python" }
        if (Test-Path -LiteralPath $c) { return $c }
    }
    return "python"
}
$py = Get-Python
$metricsPy = Join-Path $scriptDir "metrics.py"
$runNetlist = Join-Path $scriptDir "run_netlist.ps1"
$exportDs = Join-Path $scriptDir "export_ds.ps1"

$layout = Resolve-AdsCliRunLayout -OutputRoot $outputRoot -RunDir $RunDir -RunId $RunId -CreateIfMissing
Write-Host "Run dir : $($layout.RunDir)"
Write-Host "  01_sim : $($layout.SimDir)"
Write-Host "  02_data: $($layout.DataDir)"
Write-Host "  03_loop: $($layout.LoopDir)"

$workNetlist = Join-Path $layout.LoopDir "loop_netlist.log"
if (-not (Test-Path -LiteralPath $workNetlist)) {
    Copy-Item -LiteralPath $NetlistPath -Destination $workNetlist -Force
}

if ($ImportLegacyFlat) {
    $legacyRoot = $outputRoot
    Get-ChildItem -LiteralPath $legacyRoot -Filter "*.csv" -File -ErrorAction SilentlyContinue |
        ForEach-Object { Copy-Item $_.FullName (Join-Path $layout.DataDir $_.Name) -Force }
    Write-Host "Imported legacy flat CSV files into $($layout.DataDir)"
}

$history = @()
$doSimulate = -not $SkipSimulate.IsPresent

for ($i = 1; $i -le $MaxIterations; $i++) {
    Write-Host "======== iteration $i / $MaxIterations ========"

    if ($doSimulate) {
        & powershell -ExecutionPolicy Bypass -File $runNetlist `
            -NetlistPath $workNetlist `
            -AdsInstallDir $AdsInstallDir `
            -ConfigPath $ConfigPath `
            -ProjectRoot $ProjectRoot `
            -OutputRoot $outputRoot `
            -RunDir $layout.RunDir
        if ($LASTEXITCODE -ne 0) { throw "Simulation failed at iteration $i (exit $LASTEXITCODE)" }

        $ds = Get-ChildItem -LiteralPath $layout.SimDir -Filter "*.ds" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
        if (-not $ds) { throw "No .ds produced in $($layout.SimDir)" }

        & powershell -ExecutionPolicy Bypass -File $exportDs -DatasetPath $ds.FullName -Format csv -AdsInstallDir $AdsInstallDir -ConfigPath $ConfigPath
        if ($LASTEXITCODE -ne 0) { throw "CSV export failed at iteration $i" }
    }

    $verdictPath = Join-Path $layout.LoopDir "verdict_iter$i.json"
    & $py $metricsPy evaluate `
        --specs $SpecsPath `
        --output-dir $layout.DataDir `
        --verdict $verdictPath `
        --suggest `
        --netlist $workNetlist
    $verdict = Get-Content -LiteralPath $verdictPath -Raw -Encoding UTF8 | ConvertFrom-Json
    $history += [pscustomobject]@{
        iteration  = $i
        all_passed = [bool]$verdict.all_passed
        failed     = @($verdict.failed)
        verdict    = $verdictPath
    }

    Write-Host ("all_passed={0} failed={1}" -f $verdict.all_passed, ($verdict.failed -join ","))

    if ($verdict.all_passed) {
        Write-Host "Closed loop SUCCESS at iteration $i"
        break
    }

    if (-not $AutoSuggest) {
        Write-Host "Metrics failed. Verdict written for LLM: $verdictPath"
        Write-Host "Edit allowed_params, apply via metrics.py apply, then re-run the loop with -RunDir `"$($layout.RunDir)`"."
        break
    }

    $suggestions = $verdict.suggested_params
    if (-not $suggestions -or (@($suggestions.PSObject.Properties).Count -eq 0)) {
        Write-Host "AutoSuggest enabled but no suggested_params; stopping."
        break
    }

    $paramsFile = Join-Path $layout.LoopDir "params_iter$i.json"
    $json = $suggestions | ConvertTo-Json -Compress
    $utf8NoBom = New-Object System.Text.UTF8Encoding $false
    [System.IO.File]::WriteAllText($paramsFile, $json, $utf8NoBom)
    Write-Host "Applying suggested params: $json"
    & $py $metricsPy apply --netlist $workNetlist --params $paramsFile --allowed $SpecsPath
    if ($LASTEXITCODE -ne 0) {
        Write-Host "No netlist params changed; stopping."
        break
    }

    $doSimulate = $true
}

$summaryPath = Join-Path $layout.LoopDir "loop_summary.json"
$summary = @{
    schema_version = "sim-loop-summary/v1"
    run_dir        = $layout.RunDir
    sim_dir        = $layout.SimDir
    data_dir       = $layout.DataDir
    loop_dir       = $layout.LoopDir
    history        = $history
    work_netlist   = $workNetlist
    specs          = $SpecsPath
}
$summary | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $summaryPath -Encoding UTF8
Write-Host "Summary: $summaryPath"

$finalVerdict = Join-Path $layout.LoopDir "verdict.json"
$last = $history | Select-Object -Last 1
if ($last) {
    Copy-Item -LiteralPath $last.verdict -Destination $finalVerdict -Force
    Write-Host "Latest verdict: $finalVerdict"
    Write-Host "RUN_DIR=$($layout.RunDir)"
    if (-not $last.all_passed) { exit 2 }
}
exit 0
