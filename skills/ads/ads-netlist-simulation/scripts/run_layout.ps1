# Shared run-directory layout for hpeesofsim_netlist_cli.
# Dot-source: . "$PSScriptRoot\run_layout.ps1"

function New-AdsCliRunId {
    return (Get-Date -Format "yyyyMMdd_HHmmss")
}

function Get-AdsDesignNameFromNetlist {
    param(
        [Parameter(Mandatory = $true)]
        [string]$NetlistPath
    )

    if (-not (Test-Path -LiteralPath $NetlistPath -PathType Leaf)) {
        throw "Netlist not found: $NetlistPath"
    }
    $text = [System.IO.File]::ReadAllText($NetlistPath)
    $match = [regex]::Match(
        $text,
        '(?im)\bTopDesignName\s*=\s*"[^":]+:(?<cell>[^":]+):[^"]+"'
    )
    if (-not $match.Success) {
        throw "Cannot infer design name because TopDesignName library:cell:view is missing in $NetlistPath. Pass -OutputRoot explicitly."
    }
    return $match.Groups["cell"].Value
}

function ConvertTo-AdsCliSafeName {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Name
    )
    $safe = [regex]::Replace($Name, '[^0-9A-Za-z_.-]+', '_').Trim('_')
    if (-not $safe) { throw "Design name has no filesystem-safe characters: $Name" }
    return $safe
}

function Get-AdsCliOutputRoot {
    param(
        [Parameter(Mandatory = $true)]
        [string]$NetlistPath,

        [string]$BaseDirectory = ""
    )

    $designName = Get-AdsDesignNameFromNetlist -NetlistPath $NetlistPath
    $safeDesignName = ConvertTo-AdsCliSafeName -Name $designName
    $currentRoot = if ($BaseDirectory) {
        [System.IO.Path]::GetFullPath($BaseDirectory)
    }
    else {
        [System.IO.Path]::GetFullPath((Get-Location).Path)
    }
    return Join-Path $currentRoot (Join-Path "example" (Join-Path $safeDesignName "output"))
}

function New-AdsCliRunLayout {
    <#
    .SYNOPSIS
      Create output/runs/<run_id>/{01_sim,02_data,03_loop} and return paths.
    #>
    param(
        [Parameter(Mandatory = $true)]
        [string]$OutputRoot,

        [string]$RunId = "",

        [string]$RunDir = ""
    )

    if ($RunDir) {
        $runRoot = [System.IO.Path]::GetFullPath($RunDir)
        $RunId = Split-Path -Leaf $runRoot
    }
    else {
        if (-not $RunId) { $RunId = New-AdsCliRunId }
        $runRoot = Join-Path $OutputRoot (Join-Path "runs" $RunId)
    }

    $simDir = Join-Path $runRoot "01_sim"
    $dataDir = Join-Path $runRoot "02_data"
    $loopDir = Join-Path $runRoot "03_loop"

    foreach ($d in @($runRoot, $simDir, $dataDir, $loopDir)) {
        New-Item -ItemType Directory -Force -Path $d | Out-Null
    }

    $latest = @{
        schema_version = "ads-cli-run/v1"
        run_id         = $RunId
        run_dir        = $runRoot
        sim_dir        = $simDir
        data_dir       = $dataDir
        loop_dir       = $loopDir
        updated_at     = (Get-Date -Format "o")
    }
    $latestPath = Join-Path $runRoot "latest.json"
    $latest | ConvertTo-Json | Set-Content -LiteralPath $latestPath -Encoding UTF8

    $pointerDir = Join-Path $OutputRoot "runs"
    New-Item -ItemType Directory -Force -Path $pointerDir | Out-Null
    $latest | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $pointerDir "latest.json") -Encoding UTF8

    return [pscustomobject]@{
        RunId    = $RunId
        RunDir   = $runRoot
        SimDir   = $simDir
        DataDir  = $dataDir
        LoopDir  = $loopDir
        LatestJson = $latestPath
    }
}

function Resolve-AdsCliRunLayout {
    <#
    .SYNOPSIS
      Resolve an existing run dir (or create a new one under OutputRoot).
    #>
    param(
        [string]$OutputRoot,
        [string]$RunDir = "",
        [string]$RunId = "",
        [switch]$CreateIfMissing
    )

    if ($RunDir) {
        if (-not (Test-Path -LiteralPath $RunDir)) {
            if ($CreateIfMissing) {
                return New-AdsCliRunLayout -OutputRoot $OutputRoot -RunDir $RunDir
            }
            throw "RunDir not found: $RunDir"
        }
        return New-AdsCliRunLayout -OutputRoot $OutputRoot -RunDir $RunDir
    }

    if ($RunId) {
        $candidate = Join-Path $OutputRoot (Join-Path "runs" $RunId)
        if ((Test-Path -LiteralPath $candidate) -or $CreateIfMissing) {
            return New-AdsCliRunLayout -OutputRoot $OutputRoot -RunId $RunId
        }
        throw "RunId not found: $candidate"
    }

    if ($CreateIfMissing) {
        return New-AdsCliRunLayout -OutputRoot $OutputRoot
    }
    throw "Specify -RunDir / -RunId or -CreateIfMissing"
}
