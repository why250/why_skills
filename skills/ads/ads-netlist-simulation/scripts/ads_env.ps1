# Shared ADS runtime discovery and configuration.

function Get-AdsSkillConfigPath {
    param([string]$ConfigPath = "")
    if ($ConfigPath) { return [System.IO.Path]::GetFullPath($ConfigPath) }
    if ($env:LOCALAPPDATA) {
        return Join-Path $env:LOCALAPPDATA "Codex\ads-netlist-simulation\config.json"
    }
    return Join-Path $HOME ".codex\ads-netlist-simulation\config.json"
}

function Test-AdsInstallDir {
    param([string]$Path)
    if (-not $Path) { return $false }
    return Test-Path -LiteralPath (Join-Path $Path "bin\hpeesofsim.exe")
}

function Find-AdsInstallDir {
    param([string]$ConfigPath = "")

    $candidates = New-Object System.Collections.Generic.List[string]
    if ($env:HPEESOF_DIR) { $candidates.Add($env:HPEESOF_DIR) }

    $resolvedConfig = Get-AdsSkillConfigPath -ConfigPath $ConfigPath
    if (Test-Path -LiteralPath $resolvedConfig) {
        try {
            $saved = Get-Content -LiteralPath $resolvedConfig -Raw -Encoding UTF8 | ConvertFrom-Json
            if ($saved.ads_install_dir) { $candidates.Add([string]$saved.ads_install_dir) }
        }
        catch {
            throw "Invalid ADS config JSON: $resolvedConfig ($($_.Exception.Message))"
        }
    }

    foreach ($root in @($env:ProgramFiles, ${env:ProgramFiles(x86)})) {
        if (-not $root) { continue }
        $keysight = Join-Path $root "Keysight"
        if (Test-Path -LiteralPath $keysight) {
            Get-ChildItem -LiteralPath $keysight -Directory -Filter "ADS20*" -ErrorAction SilentlyContinue |
                Sort-Object Name -Descending |
                ForEach-Object { $candidates.Add($_.FullName) }
        }
    }

    foreach ($candidate in $candidates) {
        if (Test-AdsInstallDir -Path $candidate) {
            return (Resolve-Path -LiteralPath $candidate).Path
        }
    }
    return $null
}

function Save-AdsSkillConfig {
    param(
        [Parameter(Mandatory = $true)][string]$AdsInstallDir,
        [string]$ConfigPath = "",
        [string]$LicenseFile = ""
    )
    $path = Get-AdsSkillConfigPath -ConfigPath $ConfigPath
    $parent = Split-Path -Parent $path
    New-Item -ItemType Directory -Force -Path $parent | Out-Null
    $payload = [ordered]@{
        schema_version  = "ads-netlist-simulation/v1"
        ads_install_dir = $AdsInstallDir
        simarch         = "win32_64"
        ads_license_file = if ($LicenseFile) { $LicenseFile } else { $null }
        hpeesofsim      = Join-Path $AdsInstallDir "bin\hpeesofsim.exe"
        ads_exe         = Join-Path $AdsInstallDir "bin\ads.exe"
        ds_export       = Join-Path $AdsInstallDir "bin\ds_export.exe"
        dsdump          = Join-Path $AdsInstallDir "bin\dsdump.exe"
        updated_at      = (Get-Date -Format "o")
    }
    $utf8NoBom = New-Object System.Text.UTF8Encoding $false
    [System.IO.File]::WriteAllText($path, ($payload | ConvertTo-Json) + [Environment]::NewLine, $utf8NoBom)
    return $path
}

function Resolve-AdsRuntime {
    param(
        [string]$AdsInstallDir = "",
        [string]$ConfigPath = ""
    )
    $resolvedConfig = Get-AdsSkillConfigPath -ConfigPath $ConfigPath
    $saved = $null
    if (Test-Path -LiteralPath $resolvedConfig) {
        $saved = Get-Content -LiteralPath $resolvedConfig -Raw -Encoding UTF8 | ConvertFrom-Json
    }
    if (-not $AdsInstallDir) {
        $AdsInstallDir = Find-AdsInstallDir -ConfigPath $resolvedConfig
    }
    if (-not (Test-AdsInstallDir -Path $AdsInstallDir)) {
        throw "ADS runtime not found. Run initialize_ads.ps1 -AdsInstallDir <ADS-root>; if auto-discovery still fails, ask the user for the ADS install directory."
    }
    $AdsInstallDir = (Resolve-Path -LiteralPath $AdsInstallDir).Path
    $license = if ($env:ADS_LICENSE_FILE) { $env:ADS_LICENSE_FILE } elseif ($saved -and $saved.ads_license_file) { [string]$saved.ads_license_file } else { "" }
    return [pscustomobject]@{
        AdsInstallDir = $AdsInstallDir
        SimArch       = "win32_64"
        LicenseFile   = $license
        ConfigPath    = $resolvedConfig
    }
}

function Set-AdsRuntimeEnvironment {
    param([Parameter(Mandatory = $true)]$Runtime)
    if (-not $env:HOME -and $env:USERPROFILE) { $env:HOME = $env:USERPROFILE }
    $env:HPEESOF_DIR = $Runtime.AdsInstallDir
    $env:COMPL_DIR = $Runtime.AdsInstallDir
    $env:SIMARCH = $Runtime.SimArch
    if ($Runtime.LicenseFile) { $env:ADS_LICENSE_FILE = $Runtime.LicenseFile }
    $env:PATH = @(
        (Join-Path $Runtime.AdsInstallDir "bin"),
        (Join-Path $Runtime.AdsInstallDir "lib\$($Runtime.SimArch)"),
        (Join-Path $Runtime.AdsInstallDir "circuit\lib.$($Runtime.SimArch)"),
        (Join-Path $Runtime.AdsInstallDir "adsptolemy\lib.$($Runtime.SimArch)"),
        $env:PATH
    ) -join ";"
}
