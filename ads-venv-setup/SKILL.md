---
name: ads-venv-setup
description: >-
  Set up a Python virtual environment that exactly mirrors the Keysight ADS 2025
  bundled Python environment (Python 3.12 + ADS-specific wheels), using the
  offline Python interpreter and wheelhouse copied from the ADS installation.
  Use when the user asks to initialize the ADS Python environment, create a
  virtual environment for this project, set up ads_venv, or run the
  install_ads_venv.ps1 script.
---

# ADS 2025 Python Virtual Environment Setup

Creates `ads_venv` from the bundled ADS 2025 Python 3.12 interpreter and
offline wheel packages — no internet or ADS installation required.

## Prerequisites

| Item | Location |
|------|----------|
| ADS Python 3.12 interpreter | `ads_offline_packages/python/python.exe` |
| Offline wheel files | `ads_offline_packages/python/wheelhouse/*.whl` |
| Setup script | `ads_offline_packages/install_ads_venv.ps1` |

The `ads_offline_packages/python/` folder is copied from:
`C:\Program Files\Keysight\ADS2025_Update2\tools\python`

## Setup Steps

### 1. Run the setup script from the project root

Open PowerShell in `d:\Users\Documents\GitHub\ADS_Python_SOA_Check` and run:

```powershell
.\ads_offline_packages\install_ads_venv.ps1
```

The script performs these actions automatically:
1. Verifies `ads_offline_packages/python/python.exe` exists
2. Creates `ads_venv/` using the ADS Python interpreter (`python -m venv ads_venv`)
3. Iterates every `.whl` in `ads_offline_packages/python/wheelhouse/` and installs
   each one via `python -m pip install <wheel> --find-links . --no-index`
   — wheels that are incompatible with the platform are silently skipped
4. Prints the full list of installed packages on completion

### 2. Activate the environment

```powershell
.\ads_venv\Scripts\activate
```

### 3. Verify

```powershell
python --version          # should print Python 3.12.x
python -m pip list        # should show keysight.ads.* packages
```

## What Gets Installed

- **Python 3.12** (same build as ADS 2025 internal interpreter)
- All `.whl` files in `wheelhouse/` — includes `keysight-ads-*` packages and
  their dependencies (numpy, pandas, etc.) pre-built for the ADS runtime

## Troubleshooting

| Problem | Cause | Fix |
|---------|-------|-----|
| `ERROR: ADS Python not found` | `ads_offline_packages/python/` folder missing | Re-copy from ADS install or a colleague's machine |
| Package shows `[SKIPPED]` | Wheel platform/Python version mismatch | Expected — those wheels target a different OS/arch |
| `python.exe` blocked by antivirus | Corporate policy | Whitelist `ads_offline_packages/python/` folder |
| Activation fails | PowerShell execution policy | Run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` |

## Key Variables in the Script

```powershell
$ADS_PATH   = 'ads_offline_packages\python'   # source interpreter + wheelhouse
$VENV_NAME  = 'ads_venv'                       # output venv name (project root)
```

To rename the venv, edit `$VENV_NAME` before running.

## Re-running / Updating

To rebuild from scratch, delete `ads_venv/` first:

```powershell
Remove-Item -Recurse -Force ads_venv
.\ads_offline_packages\install_ads_venv.ps1
```
