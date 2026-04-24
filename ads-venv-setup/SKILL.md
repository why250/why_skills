---
name: ads-venv-setup
description: >-
  Set up a Python virtual environment that exactly mirrors the Keysight ADS 2025
  bundled Python environment (Python 3.12 + ADS-specific wheels). Use when the
  user wants to initialize the ADS Python environment, create ads_venv, set up
  the project virtual environment, or provides a path to their ADS 2025 Python
  folder. The agent should ask for the ADS Python folder path and then run the
  setup script automatically.
---

# ADS 2025 Python Virtual Environment Setup

## Agent workflow

When this skill is triggered, follow these steps in order:

### Step 1 — Collect the ADS Python folder path

Ask the user:

> "请提供你的 ADS 2025 Python 文件夹路径。
> 常见路径示例：
> - 离线拷贝（已在项目中）：`ads_offline_packages\python`（直接按回车使用默认值）
> - ADS 安装目录：`C:\Program Files\Keysight\ADS2025_Update2\tools\python`
> - 自定义拷贝位置：如 `D:\MyADS\python`"

If the user already provided the path in their message, skip this step.

### Step 2 — Validate the path contains required files

Before running the script, verify:
1. `<provided_path>\python.exe` exists
2. `<provided_path>\wheelhouse\` folder exists

If either is missing, tell the user and stop.

### Step 3 — Run the setup script

Execute from the **project root** (`d:\Users\Documents\GitHub\ADS_Python_SOA_Check`):

```powershell
# Default (offline copy already in project)
.\.agents\skills\ads-venv-setup\scripts\setup_ads_venv.ps1

# Custom path provided by user
.\.agents\skills\ads-venv-setup\scripts\setup_ads_venv.ps1 -ADSPythonPath "<user_path>"

# Custom venv name (optional)
.\.agents\skills\ads-venv-setup\scripts\setup_ads_venv.ps1 -ADSPythonPath "<user_path>" -VenvName "ads_venv"
```

Use `Shell` tool to run the command and capture output.

### Step 4 — Report results

After the script finishes, show the user:
- How many wheels were installed / skipped
- The activation command: `.\ads_venv\Scripts\activate`
- Suggest running `python -m pip list` to verify `keysight.ads.*` packages are present

---

## Script reference

**Script**: `scripts/setup_ads_venv.ps1`

| Parameter | Default | Description |
|-----------|---------|-------------|
| `-ADSPythonPath` | `ads_offline_packages\python` | Path to ADS Python folder (must contain `python.exe` + `wheelhouse\`) |
| `-VenvName` | `ads_venv` | Name of the virtual environment to create |

What the script does internally:
1. Resolves the path and validates `python.exe` + `wheelhouse\` exist
2. Runs `python -m venv <VenvName>` using the ADS interpreter
3. Installs every `.whl` from `wheelhouse\` via `pip install --no-index --find-links`; incompatible wheels are silently skipped
4. Prints installed package list and summary

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `python.exe not found` | Check the path; copy the folder from ADS installation |
| `wheelhouse\ not found` | The source folder is incomplete — re-copy from ADS |
| Activation fails | Run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` |
| Antivirus blocks `python.exe` | Whitelist the ADS Python folder |
| `[skipped]` wheels | Expected — platform/version mismatch, not an error |

---

## Re-running from scratch

```powershell
Remove-Item -Recurse -Force ads_venv
.\.agents\skills\ads-venv-setup\scripts\setup_ads_venv.ps1 -ADSPythonPath "<path>"
```
