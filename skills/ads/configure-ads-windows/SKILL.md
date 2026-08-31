---
name: configure-ads-windows
description: Install and configure Keysight ADS 2022/2025/2027+ on Windows Server. Covers silent setup.exe, PathWaveWindowsPatcher, shared EEsof_License_Tools, per-version agsl.dll patching, 27009@localhost licensing, launch scripts (no global default), multi-version isolation, and troubleshooting. Use when installing ADS on Windows, switching versions, license signature errors, agileesofd down, Patcher GUI pops up, or ADS2025 Python UI AssertionError.
---

# Keysight ADS Windows — Install & Multi-Version Configuration

Covers **ADS2022, ADS2025, ADS2027**, and future releases using the same patterns.

**Automation scripts (canonical after install):** `C:\Program Files\Keysight\ads-windows\`

**Double-click launchers:** `C:\Program Files\Keysight\ADS 2025.bat` (also 2022 / 2027)

**Dev / repo copy:** [`scripts/ads-windows/`](../../scripts/ads-windows/) — edit here, then redeploy:

```powershell
# Admin — copy scripts + create .bat launchers under Keysight
cd D:\sn06071\Keysight\scripts\ads-windows
.\install-ads-launchers.ps1
```

| Script | Purpose |
|--------|---------|
| `ADS 2025.bat` / `ADS 2027.bat` | **Double-click** in `C:\Program Files\Keysight\` |
| `ads2022.ps1` / `ads2025.ps1` / `ads2027.ps1` | Launch ADS (no admin, no global default) |
| `launch-ads.ps1` | Shared launcher — env, PATH, license preflight |
| `ensure-ads-license.ps1` | CRLF fix, lmgrd check, agsl marker validation |
| `patch-ads-license.ps1` | **Admin, one-time** — silent patch EELIC + per-version agsl |
| `fix-ads2025-python-ui.ps1` | **Admin** — deboot_gui assert fix + pyc cache clear |
| `install-ads-launchers.ps1` | **Admin** — deploy to `Keysight\ads-windows\` + root `.bat` files |

**Sister skill (Linux):** [configure-ads-linux](../configure-ads-linux/SKILL.md)

---

## Prerequisites — Install as Administrator

Writing to `C:\Program Files\Keysight` requires elevation. **Stop and ask the user** if permission is denied.

| Phase | Admin required? |
|-------|-----------------|
| Silent `setup.exe` install | Yes |
| `patch-ads-license.ps1` | Yes |
| `fix-ads2025-python-ui.ps1` | Yes (optional) |
| Daily `ads2025.ps1` / `ads2027.ps1` launch | **No** |

InstallAnywhere **must be launched from a local path** (not UNC). Extract zip to disk first.

---

## Version Matrix (reference host BJHCP021)

| Item | ADS2022 | ADS2025 | ADS2027 |
|------|---------|---------|---------|
| Install dir | `C:\Program Files\Keysight\ADS2022` | `...\ADS2025` | `...\ADS2027` |
| Registry key | `HKLM\...\ADS\5.50` | `...\6.10` | `...\6.50` |
| `agsl.dll` (client) | `ADS2022\bin\agsl.dll` | `ADS2025\bin\agsl.dll` | `ADS2027\bin\agsl.dll` |
| agsl size (approx) | version-specific | ~2.4 MB | ~2.7 MB (matches EELIC) |
| Patcher strategy | patch `bin\`, sync tree | patch `bin\`, sync tree | patch EELIC → copy to all `agsl.dll` |
| Patcher zip | site crack | site crack | `PathWaveWindowsPatcher v26.08` |
| Media | legacy installer | `ads_2025_shp_win_x64` | `ads_2027_shp_win_x64.zip` |

**Shared (all versions):**

| Item | Path |
|------|------|
| EEsof License Tools | `C:\Program Files\Keysight\EEsof_License_Tools` |
| License file | `C:\Program Files\Keysight\license.lic` |
| `ADS_LICENSE_FILE` (runtime) | `27009@localhost` — **not** the `.lic` file path |
| lmgrd / agileesofd | `EEsof_License_Tools\bin\` |
| EELIC version (post-2027) | `2026.3.1.1000` (registry `HPEESOF_LIC_VER`) |
| HOME (workspace) | `D:\home\project\ads_temp` |
| agsl markers | `scripts/ads-windows/.markers/ads{YYYY}.agsl.hash` |

Discover `agsl.dll` locations dynamically:

```powershell
Get-ChildItem "C:\Program Files\Keysight\ADS2027" -Recurse -Filter agsl.dll |
  Select-Object FullName, Length
```

> **Windows ≠ Linux:** client `agsl.dll` lives under `{ADS}\bin\`, not `lib\win32_64\` (that dir has `.lib` import libs only).

---

## Standard Layout

```
C:\Program Files\Keysight\
  ADS 2022.bat  ADS 2025.bat  ADS 2027.bat   # double-click launchers
  ADS-启动说明.txt
  ads-windows\                               # PowerShell scripts + .markers\
    launch-ads.ps1  ensure-ads-license.ps1  patch-ads-license.ps1  ...
  Patch\extracted\PathWaveWindowsPatcher.exe # optional, via install-ads-launchers.ps1
  ADS2022\  ADS2025\  ADS2027\               # isolated install trees
  EEsof_License_Tools\
  license.lic

D:\sn06071\Keysight\scripts\ads-windows\    # dev copy (sync via install-ads-launchers.ps1)
```

**No global default version** — do not rely on machine-level `ADS_DIR`. Use version-specific `.ps1` launchers.

---

## Install Flow (new ADS version)

### Step 1 — Extract media

```powershell
$media = "D:\sn06071\Keysight\ADS2027_tar\Windows\media"
Expand-Archive "...\ads_2027_shp_win_x64.zip" -DestinationPath $media
```

### Step 2 — Silent `setup.exe`

Create `installer.properties` (adapt from existing version's `installer_info.txt`):

```properties
INSTALLER_UI=silent
USER_INSTALL_DIR=C:\\Program Files\\Keysight\\ADS2027
CHOSEN_INSTALL_SET=Complete
CHOSEN_INSTALL_FEATURE_LIST=ADS,DGS,Examples,Manuals
USER_SELECTED_FOLDER=D:\\home\\project\\ads_temp
USER_STARTMENU_FOLDER=Advanced Design System 2027
```

```powershell
cd D:\sn06071\Keysight\ADS2027_tar\Windows\media
.\setup.exe -i silent -f "D:\sn06071\Keysight\ADS2027_tar\Windows\installer.properties"
```

- Takes **20–40 min**; `javaw.exe` in background is normal.
- Expect `REINSTALL_EELIC=true` — shared `EEsof_License_Tools` will be upgraded.
- Verify: `C:\Program Files\Keysight\ADS2027\bin\ads.exe` and `installer_info.txt` → `INSTALL_SUCCESS=SUCCESS`.
- Rollback: `C:\Program Files\Uninstall_ADS2027\uninstall.exe -i silent`

### Step 3 — Patch license (admin, one-time)

```powershell
cd D:\sn06071\Keysight\scripts\ads-windows
.\patch-ads-license.ps1 -Version All    # or -Version 2027
```

**PathWaveWindowsPatcher rules:**

1. Run **silently**: `Push-Location $dir; & $Patcher -y; Pop-Location`
2. **Never** use `Start-Process $Patcher` on launch — opens GUI and may require elevation.
3. **ADS2027:** patch `EEsof_License_Tools\bin`, then copy `agsl.dll` to every `ADS2027\**\agsl.dll`.
4. **ADS2025/2022:** patch `ADS{YYYY}\bin` only, then sync `bin\agsl.dll` → fem/Momentum/thermal copies.

### Step 4 — Strip CRLF from license files

```powershell
# Or let ensure-ads-license.ps1 do it on each launch
$files = @(
  'C:\Program Files\Keysight\license.lic',
  'C:\Program Files\Keysight\EEsof_License_Tools\bin\agileesofd.lic'
)
foreach ($f in $files) {
  $t = [IO.File]::ReadAllText($f) -replace "`r`n","`n" -replace "`r","`n"
  [IO.File]::WriteAllText($f, $t, [Text.UTF8Encoding]::new($false))
}
```

### Step 5 — Start / verify license server

```powershell
& 'C:\Program Files\Keysight\EEsof_License_Tools\bin\lmutil.exe' lmstat -c 27009@localhost
# Expect: license server UP v11.19.x  +  agileesofd: UP
```

Restart if vendor daemon down (admin):

```powershell
cd 'C:\Program Files\Keysight\EEsof_License_Tools\bin'
.\killlmgrd.exe
Start-Process .\lmgrd.exe -ArgumentList '-c','"C:\Program Files\Keysight\license.lic"','-l','lmgrd_restart.log','-z2' `
  -WorkingDirectory (Get-Location) -WindowStyle Hidden
```

lmgrd **must** start with working directory = `EEsof_License_Tools\bin`.

### Step 6 — Launch ADS (daily, no admin)

**Double-click:** `C:\Program Files\Keysight\ADS 2025.bat` (or 2027 / 2022)

**Or PowerShell:**

```powershell
& 'C:\Program Files\Keysight\ads-windows\ads2025.ps1'
# Dev copy still works:
# D:\sn06071\Keysight\scripts\ads-windows\ads2025.ps1
```

**One ADS GUI at a time.** `launch-ads.ps1` stops other `ADS20xx` processes before start.

---

## Runtime Environment (set by `launch-ads.ps1`)

```powershell
$env:HPEESOF_DIR = "C:\Program Files\Keysight\ADS$Version"
$env:ADS_DIR     = $env:HPEESOF_DIR
$env:ADS_LICENSE_FILE = '27009@localhost'   # NOT license.lic path
$env:HOME = 'D:\home\project\ads_temp'      # if unset
$env:PATH = "$HPEESOF_DIR\bin;EEsof_License_Tools\bin;..."  # strip other ADS20xx paths
```

Remove `PYTHONHOME` / `PYTHONPATH` before launch to avoid cross-version pollution.

---

## Pitfalls (learned from real installs)

| Issue | Symptom | Fix |
|-------|---------|-----|
| Patcher via `Start-Process` | GUI pops up; "requires elevation" | Use `& $Patcher -y` from target dir; only in `patch-ads-license.ps1` |
| Patcher on `lib\win32_64` | License still fails | Patch `bin\agsl.dll` (Windows client path) |
| `ADS_LICENSE_FILE=...\license.lic` | "License file signature is invalid" | Use `27009@localhost` |
| License CRLF | `Failed to open the TCP port`; agileesofd won't start | Strip `\r` from `.lic` files; restart lmgrd |
| Copy EELIC agsl → ADS2025 | ADS2025 won't start / wrong hash | Each version has **different** agsl size; patch per version |
| Compare agsl hash to EELIC for 2025 | False "not patched" on launch | Use `.markers/ads2025.agsl.hash` per version |
| EEsof upgraded by ADS2027 install | Older ADS license quirks | Re-run `patch-ads-license.ps1 -Version All` |
| Two ADS versions running | ADS2025 `deboot_gui.py` AssertionError | Close other ADS; launcher auto-stops other versions |
| Stale `deboot_gui.pyc` | AssertionError after source fix | Launcher clears `de\python\__pycache__`; run `fix-ads2025-python-ui.ps1` |
| Machine `ADS_DIR` → ADS2025 | Wrong version if env relied on | Use `ads{YYYY}.ps1` only; ignore global `ADS_DIR` |
| Install from UNC path | Silent install fails | Extract zip locally; `cd` into `media` before `setup.exe` |

---

## Diagnosis

### License server

```powershell
& 'C:\Program Files\Keysight\EEsof_License_Tools\bin\lmutil.exe' lmstat -c 27009@localhost
Get-Process lmgrd, agileesofd -ErrorAction SilentlyContinue |
  ForEach-Object { $_.Id; (Get-CimInstance Win32_Process -Filter "ProcessId=$($_.Id)").CommandLine }
```

| Symptom | Cause | Action |
|---------|-------|--------|
| lmgrd UP, agileesofd DOWN | CRLF / port / stale lmgrd | Strip CRLF; `killlmgrd` + restart from `EELIC\bin` |
| "signature is invalid" | File-based `ADS_LICENSE_FILE` | Set `27009@localhost` in launcher |
| Server UP, ADS no license | Client `bin\agsl.dll` unpatched | `patch-ads-license.ps1 -Version {YYYY}` |
| `b_ads_inclusive` missing in lmstat | agileesofd not serving | Fix vendor daemon first |

### agsl.dll per version

```powershell
foreach ($v in 2022,2025,2027) {
  $p = "C:\Program Files\Keysight\ADS$v\bin\agsl.dll"
  if (Test-Path $p) { Get-FileHash $p | Select-Object @{N='Ver';E={$v}}, Hash, @{N='Size';E={(Get-Item $p).Length}} }
}
Get-FileHash 'C:\Program Files\Keysight\EEsof_License_Tools\bin\agsl.dll'
```

ADS2027 `bin\agsl.dll` hash should match EELIC after patch. ADS2025/2022 will **differ** — that is expected.

### Python UI (ADS2025)

```
Failed to load python ui functionality
AssertionError: <EMPTY MESSAGE>  @ deboot_gui.py add_console_application_shortcut
```

Cause: `assert len(mainwindows) == 1` when 0 or 2+ Qt main windows (often another ADS instance running).

Fix: close other ADS versions; run `fix-ads2025-python-ui.ps1` (removes assert + clears `.pyc`).

---

## Checklist — Adding ADS2028+

1. Install to `C:\Program Files\Keysight\ADS<YYYY>` (never overwrite existing).
2. Add row to Version Matrix; note new `PathWaveWindowsPatcher vXX.XX` zip.
3. Update `installer.properties` template under `ADS<YYYY>_tar\Windows\`.
4. Run silent `setup.exe` as admin; verify `installer_info.txt` SUCCESS.
5. Admin: `.\patch-ads-license.ps1 -Version <YYYY>`.
6. Add `ads<YYYY>.ps1` wrapper → `launch-ads.ps1 -Version <YYYY>`.
7. Update `launch-ads.ps1` `ValidateSet` if needed.
8. If new agsl matches EELIC size → use 2027 copy strategy; else use 2025 bin-patch strategy.
9. Verify: `lmutil lmstat`, `.\ads<YYYY>.ps1`, confirm old versions still launch.
10. Document patcher version in this SKILL.

---

## Design Principles

1. **One install dir per version** under `C:\Program Files\Keysight\ADS{YYYY}`.
2. **Shared EEsof_License_Tools** — upgraded by newest installer; re-patch all versions after adding a release.
3. **Per-version `agsl.dll`** — never assume one client DLL fits all releases.
4. **`27009@localhost` at runtime** — shared license server; file path only for lmgrd `-c`.
5. **No global default** — version-specific `ads{YYYY}.ps1` launchers, not machine `ADS_DIR`.
6. **Patch once (admin), launch daily (user)** — never run Patcher GUI on every start.
7. **One GUI instance at a time** — stop sibling ADS processes before launch.
8. **SKILL = agent manual**; **`scripts/ads-windows/` = automation**; markers = idempotent patch state.
