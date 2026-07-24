<#
.SYNOPSIS
    Create a Python virtual environment that mirrors the Keysight ADS 2025
    bundled Python environment.

.PARAMETER ADSPythonPath
    Path to the ADS Python folder. This is either:
      - The folder you copied from the ADS installation, or
      - The live ADS installation folder itself.
    Must contain python.exe and a wheelhouse\ sub-folder.
    Default: ads_offline_packages\python  (relative to project root)

.PARAMETER VenvName
    Name of the virtual environment to create.
    Default: ads_venv

.EXAMPLE
    # Use the bundled offline copy (default)
    .\setup_ads_venv.ps1

.EXAMPLE
    # Point directly at the ADS installation
    .\setup_ads_venv.ps1 -ADSPythonPath "C:\Program Files\Keysight\ADS2025_Update2\tools\python"

.EXAMPLE
    # Custom venv name
    .\setup_ads_venv.ps1 -ADSPythonPath "D:\MyADS\python" -VenvName "my_ads_env"
#>

param(
    [string]$ADSPythonPath = 'ads_offline_packages\python',
    [string]$VenvName      = 'ads_venv'
)

# Resolve to absolute path so behaviour is the same regardless of cwd
$ADS_PATH   = Resolve-Path $ADSPythonPath -ErrorAction SilentlyContinue
$ADS_PYTHON = if ($ADS_PATH) { Join-Path $ADS_PATH 'python.exe' } else { $null }
$WHEEL_DIR  = if ($ADS_PATH) { Join-Path $ADS_PATH 'wheelhouse' } else { $null }

Write-Host "--- ADS Python Virtual Environment Setup ---" -ForegroundColor Cyan
Write-Host "  ADS Python path : $ADSPythonPath"
Write-Host "  Venv name       : $VenvName"
Write-Host ""

# 1. Validate source folder
if (-not $ADS_PATH -or -not (Test-Path $ADS_PYTHON)) {
    Write-Host "ERROR: python.exe not found at: $ADSPythonPath" -ForegroundColor Red
    Write-Host "  Make sure you provide the correct path via -ADSPythonPath." -ForegroundColor Yellow
    exit 1
}

if (-not (Test-Path $WHEEL_DIR)) {
    Write-Host "ERROR: wheelhouse\ folder not found at: $WHEEL_DIR" -ForegroundColor Red
    exit 1
}

# 2. Create virtual environment
Write-Host "Step 1/3  Creating virtual environment [$VenvName]..." -ForegroundColor Yellow
& $ADS_PYTHON -m venv $VenvName
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Failed to create virtual environment." -ForegroundColor Red
    exit 1
}

$LOCAL_PIP = Join-Path (Get-Location) "$VenvName\Scripts\python.exe"

# 3. Install wheels from wheelhouse
Write-Host "`nStep 2/3  Installing wheels from wheelhouse..." -ForegroundColor Yellow
$wheels = Get-ChildItem -Path $WHEEL_DIR -Filter *.whl
$installed = 0; $skipped = 0

foreach ($wheel in $wheels) {
    Write-Host "  $($wheel.Name)..." -NoNewline
    $proc = Start-Process -FilePath $LOCAL_PIP `
        -ArgumentList "-m pip install `"$($wheel.FullName)`" --find-links `"$WHEEL_DIR`" --no-index --quiet" `
        -Wait -PassThru -NoNewWindow
    if ($proc.ExitCode -eq 0) {
        Write-Host " OK" -ForegroundColor Green
        $installed++
    } else {
        Write-Host " skipped" -ForegroundColor Gray
        $skipped++
    }
}

# 4. Summary
Write-Host "`nStep 3/3  Verification" -ForegroundColor Yellow
& $LOCAL_PIP -m pip list

Write-Host "`n--- Setup Complete ---" -ForegroundColor Green
Write-Host "  Installed : $installed wheel(s)"
Write-Host "  Skipped   : $skipped wheel(s)  (platform/version mismatch — expected)"
Write-Host ""
Write-Host "Activate with:"
Write-Host "  .\$VenvName\Scripts\activate" -ForegroundColor White
