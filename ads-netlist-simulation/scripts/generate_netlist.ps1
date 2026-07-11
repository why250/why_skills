#Requires -Version 5.1
<#
.SYNOPSIS
  Generate workspace/netlist.log from an ADS schematic path using AEL.

.DESCRIPTION
  Launches ADS with ads.exe -m generate_netlist.ael. No Python packages are
  used. ADS Design Environment still starts in the background because OA
  schematic netlisting requires a DesignContext.

.PARAMETER DesignPath
  Absolute physical path: <workspace>/<library>/<cell>/<view>.

.PARAMETER CellName
  Optional logical ADS cell name. Use this when the physical OA directory name
  cannot be decoded by removing percent escape markers.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$DesignPath,
    [string]$CellName = "",
    [string]$OutputPath = "",
    [string]$AdsInstallDir = "",
    [string]$ConfigPath = "",
    [ValidateRange(10, 600)]
    [int]$TimeoutSec = 120
)

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
. (Join-Path $scriptDir "ads_env.ps1")

if (-not [System.IO.Path]::IsPathRooted($DesignPath)) {
    throw "DesignPath must be absolute: $DesignPath"
}
if (-not (Test-Path -LiteralPath $DesignPath -PathType Container)) {
    throw "Design directory not found: $DesignPath"
}

$design = Get-Item -LiteralPath $DesignPath
$viewName = $design.Name
if ($viewName.ToLowerInvariant() -ne "schematic") {
    throw "DesignPath must end with a schematic directory: $DesignPath"
}
$cellDirectory = $design.Parent
$libraryDirectory = $cellDirectory.Parent
$workspaceDirectory = $libraryDirectory.Parent
if (-not $workspaceDirectory) { throw "Cannot infer workspace from: $DesignPath" }

$libraryName = $libraryDirectory.Name
if (-not $CellName) {
    # OA physical names commonly prefix escaped/case-sensitive characters with %.
    # Example: %B%J%T_%I%V_%Gm_%Power%Calcs -> BJT_IV_Gm_PowerCalcs.
    $CellName = [regex]::Replace($cellDirectory.Name, '%(?=.)', '')
}
if (-not $OutputPath) { $OutputPath = Join-Path $workspaceDirectory.FullName "netlist.log" }
$OutputPath = [System.IO.Path]::GetFullPath($OutputPath)
$outputParent = Split-Path -Parent $OutputPath
New-Item -ItemType Directory -Force -Path $outputParent | Out-Null

$runtime = Resolve-AdsRuntime -AdsInstallDir $AdsInstallDir -ConfigPath $ConfigPath
Set-AdsRuntimeEnvironment -Runtime $runtime
$adsExe = Join-Path $runtime.AdsInstallDir "bin\ads.exe"
$aelScript = Join-Path $scriptDir "generate_netlist.ael"
if (-not (Test-Path -LiteralPath $adsExe)) { throw "ads.exe not found: $adsExe" }
if (-not (Test-Path -LiteralPath $aelScript)) { throw "AEL generator not found: $aelScript" }
$existingAds = @(Get-Process -Name "hpeesofde" -ErrorAction SilentlyContinue)
$existingAdsIds = @($existingAds | ForEach-Object { $_.Id })
$existingPidTokens = "|{0}|" -f (($existingAdsIds | ForEach-Object { $_.ToString() }) -join "|")

$launcherTempRoot = [System.IO.Path]::GetFullPath(
    (Join-Path ([System.IO.Path]::GetTempPath()) "ads-netlist-simulation")
)
$launcherWorkingDir = Join-Path $launcherTempRoot ([guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Force -Path $launcherWorkingDir | Out-Null
$statusPath = Join-Path $launcherWorkingDir "netlist.status"
$env:CODEX_ADS_EXISTING_PIDS = $existingPidTokens
$env:CODEX_ADS_REQUIRE_ISOLATION = if ($existingAdsIds.Count -gt 0) { "1" } else { "0" }
$env:CODEX_ADS_WORKSPACE = $workspaceDirectory.FullName.Replace('\', '/')
$env:CODEX_ADS_LIBRARY = $libraryName
$env:CODEX_ADS_CELL = $CellName
$env:CODEX_ADS_VIEW = $viewName
$env:CODEX_ADS_NETLIST_OUTPUT = $OutputPath.Replace('\', '/')
$env:CODEX_ADS_NETLIST_STATUS = $statusPath.Replace('\', '/')

Write-Host "ADS install : $($runtime.AdsInstallDir)"
Write-Host "Workspace   : $($workspaceDirectory.FullName)"
Write-Host "Design      : $($libraryName):$($CellName):$($viewName)"
Write-Host "Netlist     : $OutputPath"
Write-Host "Launcher    : ads.exe -m generate_netlist.ael"
if ($existingAdsIds.Count -gt 0) {
    Write-Host "Protected   : existing hpeesofde PID $($existingAdsIds -join ', ')"
}

$process = $null
$newAdsIds = @()
try {
    $quotedAel = '"{0}"' -f $aelScript
    $process = Start-Process -FilePath $adsExe -ArgumentList @("-m", $quotedAel) `
        -WorkingDirectory $launcherWorkingDir -PassThru -WindowStyle Hidden
    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    while (-not (Test-Path -LiteralPath $statusPath)) {
        $observedIds = @(Get-Process -Name "hpeesofde" -ErrorAction SilentlyContinue |
            Where-Object { $existingAdsIds -notcontains $_.Id } |
            ForEach-Object { $_.Id })
        $newAdsIds = @($newAdsIds + $observedIds | Select-Object -Unique)
        if ((Get-Date) -ge $deadline) {
            if ($process -and -not $process.HasExited) {
                Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
            }
            throw "Timed out waiting for ADS AEL netlisting after $TimeoutSec seconds"
        }
        Start-Sleep -Milliseconds 250
    }

    $observedIds = @(Get-Process -Name "hpeesofde" -ErrorAction SilentlyContinue |
        Where-Object { $existingAdsIds -notcontains $_.Id } |
        ForEach-Object { $_.Id })
    $newAdsIds = @($newAdsIds + $observedIds | Select-Object -Unique)
    if ($newAdsIds.Count -gt 0) {
        Write-Host "Private ADS : hpeesofde PID $($newAdsIds -join ', ')"
    }

    $status = (Get-Content -LiteralPath $statusPath -Raw -Encoding Default).Trim()
    if ($status -eq "ERROR_REUSED_SESSION") {
        throw "ads.exe -m reused an existing ADS session. Netlisting stopped before opening or closing any workspace."
    }
    if ($status -eq "ERROR_PID_UNAVAILABLE") {
        throw "This ADS build cannot verify process isolation while another ADS session is running. Close ADS or use ADS 2022 Update 1 or newer."
    }
    if ($status -ne "OK") {
        throw "ADS AEL netlisting failed with status: $status"
    }
    if (-not (Test-Path -LiteralPath $OutputPath -PathType Leaf)) {
        throw "ADS reported success but netlist was not created: $OutputPath"
    }
    $netlistInfo = Get-Item -LiteralPath $OutputPath
    if ($netlistInfo.Length -eq 0) { throw "Generated netlist is empty: $OutputPath" }

    Write-Host "Generated   : $($netlistInfo.Length) bytes"
    Write-Host "NETLIST_PATH=$OutputPath"

    # The AEL writes status before de_exit(); wait only for this invocation's
    # private ADS process. Pre-existing interactive ADS processes are ignored.
    $exitDeadline = (Get-Date).AddSeconds(15)
    while ($newAdsIds.Count -gt 0 -and
        @(Get-Process -Id $newAdsIds -ErrorAction SilentlyContinue).Count -gt 0 -and
        (Get-Date) -lt $exitDeadline) {
        Start-Sleep -Milliseconds 250
    }
}
finally {
    foreach ($name in @(
        "CODEX_ADS_EXISTING_PIDS", "CODEX_ADS_REQUIRE_ISOLATION",
        "CODEX_ADS_WORKSPACE", "CODEX_ADS_LIBRARY", "CODEX_ADS_CELL",
        "CODEX_ADS_VIEW", "CODEX_ADS_NETLIST_OUTPUT", "CODEX_ADS_NETLIST_STATUS"
    )) {
        Remove-Item -LiteralPath "Env:$name" -ErrorAction SilentlyContinue
    }
    # A startup failure before de_exit() may leave only the newly-created ADS
    # instance alive. Never stop a PID that existed before this invocation.
    $remainingNewIds = if ($newAdsIds.Count -gt 0) {
        @(Get-Process -Id $newAdsIds -ErrorAction SilentlyContinue | ForEach-Object { $_.Id })
    }
    else { @() }
    foreach ($id in $remainingNewIds) {
        Stop-Process -Id $id -Force -ErrorAction SilentlyContinue
    }
    if ($process -and -not $process.HasExited) {
        Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
    }
    $resolvedLauncherDir = [System.IO.Path]::GetFullPath($launcherWorkingDir)
    $safeTempPrefix = $launcherTempRoot.TrimEnd('\') + '\'
    if ($resolvedLauncherDir.StartsWith($safeTempPrefix, [System.StringComparison]::OrdinalIgnoreCase) -and
        (Test-Path -LiteralPath $resolvedLauncherDir -PathType Container)) {
        $cleanupDeadline = (Get-Date).AddSeconds(15)
        do {
            Remove-Item -LiteralPath $resolvedLauncherDir -Recurse -Force -ErrorAction SilentlyContinue
            if (-not (Test-Path -LiteralPath $resolvedLauncherDir)) { break }
            Start-Sleep -Milliseconds 250
        } while ((Get-Date) -lt $cleanupDeadline)
        if (Test-Path -LiteralPath $resolvedLauncherDir) {
            Write-Warning "Could not remove ADS launcher temporary directory: $resolvedLauncherDir"
        }
    }
}
