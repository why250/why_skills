#Requires -Version 5.1
[CmdletBinding()]
param(
    [string]$AdsInstallDir = "",
    [string]$ConfigPath = "",
    [string]$LicenseFile = "",
    [switch]$Force
)

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
. (Join-Path $scriptDir "ads_env.ps1")

$config = Get-AdsSkillConfigPath -ConfigPath $ConfigPath
if ((Test-Path -LiteralPath $config) -and -not $Force -and -not $AdsInstallDir) {
    $runtime = Resolve-AdsRuntime -ConfigPath $config
}
else {
    if (-not $AdsInstallDir) { $AdsInstallDir = Find-AdsInstallDir -ConfigPath $config }
    if (-not (Test-AdsInstallDir -Path $AdsInstallDir)) {
        throw "Could not auto-detect ADS. Re-run with -AdsInstallDir <ADS-root>."
    }
    $AdsInstallDir = (Resolve-Path -LiteralPath $AdsInstallDir).Path
    $config = Save-AdsSkillConfig -AdsInstallDir $AdsInstallDir -ConfigPath $config -LicenseFile $LicenseFile
    $runtime = Resolve-AdsRuntime -ConfigPath $config
}

$required = @("ads.exe", "hpeesofsim.exe", "ds_export.exe", "dsdump.exe")
$missing = @($required | Where-Object { -not (Test-Path -LiteralPath (Join-Path $runtime.AdsInstallDir "bin\$_")) })
if ($missing.Count -gt 0) { throw "ADS install is incomplete; missing: $($missing -join ', ')" }

Set-AdsRuntimeEnvironment -Runtime $runtime
Write-Host "ADS runtime ready"
Write-Host "Install : $($runtime.AdsInstallDir)"
Write-Host "Config  : $($runtime.ConfigPath)"
Write-Host "License : $(if ($runtime.LicenseFile) { $runtime.LicenseFile } else { '(environment/default)' })"
if (-not $runtime.LicenseFile) {
    Write-Warning "ADS_LICENSE_FILE is not set. This is valid only if site licensing is configured elsewhere; a real simulation is the license check."
}
Write-Host "Simulator: $(Join-Path $runtime.AdsInstallDir 'bin\hpeesofsim.exe')"
Write-Host "ADS/AEL  : $(Join-Path $runtime.AdsInstallDir 'bin\ads.exe')"
Write-Host "Exporter : $(Join-Path $runtime.AdsInstallDir 'bin\ds_export.exe')"
exit 0
