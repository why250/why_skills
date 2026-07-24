#Requires -Version 5.1
<#
.SYNOPSIS
  Run an ADS netlist with hpeesofsim.exe (no GUI).

.DESCRIPTION
  Writes simulator artifacts under:
    <OutputRoot>/runs/<RunId>/01_sim/

  Dataset name comes from Options TopDesignName in the netlist
  (lib:cell:view -> <cell>.ds in the working directory).

  By default the working netlist copy gets ASCII_Rawfile=yes so spectra.raw
  is fully text. Pass -BinaryRawfile to keep binary MDS payload.

.PARAMETER OutputDir
  Explicit sim directory (01_sim). If empty, a new run layout is created
  under <current-directory>/example/<design-name>/output/runs/<timestamp>/01_sim.

.PARAMETER ProjectRoot
  Original caller directory captured before accessing the ADS workspace. When
  OutputRoot and OutputDir are empty, use ProjectRoot instead of the process's
  possibly changed current directory.

.PARAMETER RunDir
  Existing or new run root (.../runs/<id>). Sim goes to RunDir/01_sim.

.PARAMETER RunId
  Optional run id when creating under the default output root.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$NetlistPath,
    [string]$AdsInstallDir = "",
    [string]$ConfigPath = "",
    [string]$ProjectRoot = "",
    [string]$OutputRoot = "",
    [string]$OutputDir = "",
    [string]$RunDir = "",
    [string]$RunId = "",
    [string]$RawfileName = "spectra.raw",
    [switch]$BinaryRawfile
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
. (Join-Path $scriptDir "run_layout.ps1")
. (Join-Path $scriptDir "ads_env.ps1")

if (-not (Test-Path -LiteralPath $NetlistPath)) {
    throw "Netlist not found: $NetlistPath"
}
$netlistText = [System.IO.File]::ReadAllText($NetlistPath)
$runtime = Resolve-AdsRuntime -AdsInstallDir $AdsInstallDir -ConfigPath $ConfigPath
$AdsInstallDir = $runtime.AdsInstallDir
Set-AdsRuntimeEnvironment -Runtime $runtime

if ($OutputDir) {
    $simDir = [System.IO.Path]::GetFullPath($OutputDir)
    New-Item -ItemType Directory -Force -Path $simDir | Out-Null
    $layout = $null
}
else {
    if (-not $OutputRoot) {
        $OutputRoot = Get-AdsCliOutputRoot -NetlistPath $NetlistPath -BaseDirectory $ProjectRoot
    }
    $outputRoot = [System.IO.Path]::GetFullPath($OutputRoot)
    $layout = Resolve-AdsCliRunLayout -OutputRoot $outputRoot -RunDir $RunDir -RunId $RunId -CreateIfMissing
    $simDir = $layout.SimDir
}

# Working netlist copy (optionally patched for ASCII rawfile). UTF-8 without BOM.
$netlistCopy = Join-Path $simDir "netlist.log"
$asciiEnabled = -not $BinaryRawfile
if ($asciiEnabled) {
    if ($netlistText -match '(?m)^Options\b' -and $netlistText -notmatch '(?i)\bASCII_Rawfile\s*=') {
        $netlistText = [regex]::Replace(
            $netlistText,
            '(?m)^(Options\b)',
            'Options ASCII_Rawfile=yes',
            1
        )
    }
    elseif ($netlistText -match '(?i)\bASCII_Rawfile\s*=\s*no\b') {
        $netlistText = [regex]::Replace(
            $netlistText,
            '(?i)\bASCII_Rawfile\s*=\s*no\b',
            'ASCII_Rawfile=yes',
            1
        )
    }
}
$utf8NoBom = New-Object System.Text.UTF8Encoding $false
[System.IO.File]::WriteAllText($netlistCopy, $netlistText, $utf8NoBom)

$simExe = Join-Path $AdsInstallDir "bin\hpeesofsim.exe"
$logFile = Join-Path $simDir "hpeesofsim_stdout.log"

Write-Host "ADS install : $AdsInstallDir"
Write-Host "Netlist     : $NetlistPath"
if ($layout) {
    Write-Host "Run dir     : $($layout.RunDir)"
}
Write-Host "Sim dir     : $simDir"
Write-Host "ASCII raw   : $asciiEnabled"
Write-Host "Command     : hpeesofsim -r `"$RawfileName`" `"$netlistCopy`""
Write-Host ""

Push-Location $simDir
try {
    # Windows PowerShell 5.1 wraps native stderr lines as ErrorRecord objects.
    # Do not let those records terminate the process before its real exit code is read.
    $previousErrorActionPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        & $simExe -r $RawfileName $netlistCopy 2>&1 |
            ForEach-Object { "$_" } |
            Tee-Object -FilePath $logFile
        $exitCode = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $previousErrorActionPreference
    }
}
finally {
    Pop-Location
}

Write-Host ""
Write-Host "Exit code   : $exitCode"
Write-Host "Stdout log  : $logFile"

$datasets = Get-ChildItem -LiteralPath $simDir -Filter "*.ds" -ErrorAction SilentlyContinue
if ($datasets) {
    Write-Host "Datasets    :"
    $datasets | ForEach-Object { Write-Host "  $($_.FullName)" }
}
else {
    Write-Host "Datasets    : (none found - check log for errors)"
    if ($exitCode -eq 0) {
        [Console]::Error.WriteLine("hpeesofsim returned 0 but produced no ADS dataset")
        $exitCode = 3
    }
}

$rawPath = Join-Path $simDir $RawfileName
if (Test-Path -LiteralPath $rawPath) {
    Write-Host "Rawfile     : $rawPath ($((Get-Item -LiteralPath $rawPath).Length) bytes)"
}

# Emit run paths for callers (closed loop).
if ($layout) {
    Write-Host "RUN_DIR=$($layout.RunDir)"
    Write-Host "SIM_DIR=$($layout.SimDir)"
    Write-Host "DATA_DIR=$($layout.DataDir)"
    Write-Host "LOOP_DIR=$($layout.LoopDir)"
}

exit $exitCode
