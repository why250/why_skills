#Requires -Version 5.1
<#
.SYNOPSIS
  Convert an ADS .ds dataset to a Python-friendly format via ADS CLI + plain Python.

.DESCRIPTION
  Default Format=csv writes under the run's 02_data/ folder when the .ds lives
  in 01_sim/ (sibling detection). Otherwise CSV is written next to the .ds
  unless -OutputPath is set.

.PARAMETER OutputPath
  Explicit output file (non-csv) or directory (csv).
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$DatasetPath,

    [ValidateSet("csv", "gmdif", "citifile", "touchstone", "smatrixio", "dsdump")]
    [string]$Format = "csv",

    [string]$AdsInstallDir = "",

    [string]$ConfigPath = "",

    [string]$OutputPath = "",

    [switch]$KeepMdif
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $DatasetPath)) {
    throw "Dataset not found: $DatasetPath"
}

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
. (Join-Path $scriptDir "ads_env.ps1")
$runtime = Resolve-AdsRuntime -AdsInstallDir $AdsInstallDir -ConfigPath $ConfigPath
$AdsInstallDir = $runtime.AdsInstallDir
Set-AdsRuntimeEnvironment -Runtime $runtime
$bin = Join-Path $AdsInstallDir "bin"

$ds = (Resolve-Path -LiteralPath $DatasetPath).Path
$dir = Split-Path -Parent $ds
$stem = [System.IO.Path]::GetFileNameWithoutExtension($ds)

# If .ds is under .../01_sim, default exports go to sibling .../02_data.
$defaultOutDir = $dir
if ((Split-Path -Leaf $dir) -eq "01_sim") {
    $siblingData = Join-Path (Split-Path -Parent $dir) "02_data"
    New-Item -ItemType Directory -Force -Path $siblingData | Out-Null
    $defaultOutDir = $siblingData
}

$pythonCandidates = @(
    (Join-Path (Get-Location) ".venv\Scripts\python.exe"),
    "python"
)

function Get-Python {
    foreach ($candidate in $pythonCandidates) {
        if ($candidate -eq "python") { return "python" }
        if (Test-Path -LiteralPath $candidate) { return $candidate }
    }
    return "python"
}

switch ($Format) {
    "dsdump" {
        if (-not $OutputPath) { $OutputPath = Join-Path $defaultOutDir "$stem.dsdump.txt" }
        $exe = Join-Path $bin "dsdump.exe"
        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $OutputPath) | Out-Null
        cmd /c "`"$exe`" `"$ds`" > `"$OutputPath`" 2>&1"
        if (-not (Test-Path -LiteralPath $OutputPath) -or (Get-Item $OutputPath).Length -eq 0) {
            throw "dsdump produced no output"
        }
        Write-Host "Format : dsdump"
        Write-Host "Input  : $ds"
        Write-Host "Output : $OutputPath"
        Write-Host "Size   : $((Get-Item -LiteralPath $OutputPath).Length) bytes"
    }
    "csv" {
        $csvOutDir = if ($OutputPath) { $OutputPath } else { $defaultOutDir }
        New-Item -ItemType Directory -Force -Path $csvOutDir | Out-Null
        $mdifPath = Join-Path $csvOutDir "$stem.mdf"

        $exe = Join-Path $bin "ds_export.exe"
        & $exe $mdifPath -t gmdif -d $ds -e | Out-Null
        if (-not (Test-Path -LiteralPath $mdifPath)) {
            throw "ds_export did not create: $mdifPath"
        }

        $py = Get-Python
        $converter = Join-Path $scriptDir "mdif_to_csv.py"
        $csvPaths = & $py $converter $mdifPath -o $csvOutDir
        if (-not $csvPaths) {
            throw "mdif_to_csv.py produced no CSV files"
        }

        if (-not $KeepMdif) {
            Remove-Item -LiteralPath $mdifPath -Force
        }

        Write-Host "Format : csv (via gmdif)"
        Write-Host "Input  : $ds"
        Write-Host "Outputs:"
        $csvPaths | ForEach-Object { Write-Host "  $_" }
        if ($KeepMdif) {
            Write-Host "MDIF   : $mdifPath"
        }
    }
    default {
        $ext = @{
            gmdif      = ".mdf"
            citifile   = ".cit"
            touchstone = ".s2p"
            smatrixio  = ".sio"
        }[$Format]
        if (-not $OutputPath) { $OutputPath = Join-Path $defaultOutDir "$stem$ext" }
        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $OutputPath) | Out-Null
        $exe = Join-Path $bin "ds_export.exe"
        & $exe $OutputPath -t $Format -d $ds -e | Out-Null
        if (-not (Test-Path -LiteralPath $OutputPath)) {
            throw "ds_export did not create: $OutputPath"
        }
        Write-Host "Format : $Format"
        Write-Host "Input  : $ds"
        Write-Host "Output : $OutputPath"
        Write-Host "Size   : $((Get-Item -LiteralPath $OutputPath).Length) bytes"
    }
}
