---
name: configure-ads-linux
description: Install and configure Keysight ADS 2025/2026+ on RHEL/Rocky Linux. Covers root SSH install preference, silent SETUP.SH, FlexNet patcher, multi-version layout, ADS_ACTIVE switching, decoupled license servers (27009/27010), ads-licensure.sh, SELinux, and troubleshooting. Use when installing ADS, switching versions, ADS License not available, License Server/Client Mismatch, ads-lmgrd failures, or terminal polkit password prompts.
---

# Keysight ADS Linux — Install & Multi-Version Configuration

Covers **ADS2025, ADS2026**, and future releases using the same patterns.

**Automation scripts:**
- [`ADS2025/Linux/install_ads2025_as_root.sh`](../../ADS2025/Linux/install_ads2025_as_root.sh)
- [`ADS2026/Linux/install_ads2026_as_root.sh`](../../ADS2026/Linux/install_ads2026_as_root.sh)

**On-host operator reference:** `/opt/eda/agilent/README-ADS.md`

---

## Prerequisites — Install as root (strongly recommended)

**Recommend the user SSH to the server as `root`** (or `su -` to root) before running install scripts.

| Approach | Pros | Cons |
|----------|------|------|
| **SSH as root** (recommended) | No sudo/password prompts; systemd, `/opt`, `/etc/profile.d`, SELinux, license wrappers all work in one session | Requires root SSH allowed on site policy |
| SSH as regular user + sudo | Works if `sudo -n` or password available | Polkit popups, `ADS_ACTIVE` lost through sudo, install may halt mid-way |

If the user must use a non-root account:
1. Run `sudo -v` before long installs (SETUP.SH takes 10–30 min)
2. Add `/etc/sudoers.d/ads-licensure` for passwordless license switching (see Step 4)
3. Expect manual intervention for systemctl / `/opt` writes

**Agent default:** run install and system config commands as root unless the user explicitly forbids root SSH.

---

## Version Matrix (this host)

| Item | ADS2025 | ADS2026 |
|------|---------|---------|
| Install dir | `/opt/eda/agilent/ADS2025` | `/opt/eda/agilent/ADS2026` |
| Media / tar | `ads_2025_shp_linux_x64` | `ads_2026_update1_shp_linux_x64` (tar may extract into `Linux/` directly) |
| LICDIR | `Licensing/2024.06/linux_x86_64/bin` | `Licensing/2025.4/linux_x86_64/bin` |
| FEM patch dir | `fem/2025.00/linux_x86_64/bin/edb` | `fem/2026.10/linux_x86_64/bin/edb` |
| Patcher zip | `PathWaveLinuxPatcher v24.08` | `PathWaveLinuxPatcher v25.07` |
| Profile | `/etc/profile.d/ads2025.sh` | `/etc/profile.d/ads2026.sh` |
| `ADS_LICENSE_FILE` | `27009@localhost` | `27010@localhost` |
| systemd | `ads-lmgrd-2025.service` | `ads-lmgrd-2026.service` |
| lmgrd version | v11.19.2 | v11.19.7 |
| Log | `/var/log/ads_lmgrd_2025.log` | `/var/log/ads_lmgrd_2026.log` |
| Extra GUI dep | — | `dnf install libglvnd-opengl` |

Discover paths dynamically when version numbers differ:

```bash
LICDIR=$(dirname "$(find "$INSTALL_DIR/Licensing" -name lmgrd -type f | head -1)")
FEM_EDB=$(find "$INSTALL_DIR/fem" -path '*/bin/edb' -type d 2>/dev/null | head -1)
```

---

## Standard Layout

```
/opt/eda/agilent/ADS2025/   ADS2026/          # isolated install trees
/etc/profile.d/ads2025.sh ads2026.sh ads-select.sh
/usr/local/bin/ads-lmgrd-2025-start.sh  ads-lmgrd-2026-start.sh  ads-licensure.sh
/etc/systemd/system/ads-lmgrd-2025.service  ads-lmgrd-2026.service
/etc/sudoers.d/ads-licensure                # optional: NOPASSWD for userone
~/.bashrc: ADS_ACTIVE=2025|2026              # single-line version switch
```

---

## Install Flow (both versions)

PathWave patcher README:

```
1. Install Keysight PathWare license manager and application
2. Set environment variable for your program
3. Copy FlexNetLicensePatcher to patch folder, run ./FlexNetLicensePatcher -y
4. Use lmgrd to start license server
5. All done
```

### Step 1 — Silent SETUP.SH

```bash
# As root:
cd /path/to/Linux/media
./SETUP.SH -i silent -f installer.properties
# installer.properties: USER_INSTALL_DIR=/opt/eda/agilent/ADS<YYYY>
```

**Compatibility fixes (idempotent):**

```bash
ln -sf /lib64/ld-linux-x86-64.so.2 /lib64/ld-lsb-x86-64.so.3
cp /usr/lib64/libstdc++.so.6.0.29 "$LICDIR/libstdc++.so.6.0.29"  # if placeholder is 0 bytes
```

Or run the version-specific `install_ads<YYYY>_as_root.sh`.

### Step 2 — Environment & version switching

**Per-version profiles** (`ads2025.sh`, `ads2026.sh`) — only version-specific `HPEESOF_DIR`, `PATH`, `ADS_LICENSE_FILE`. No switching logic inside.

**Shared selector** `/etc/profile.d/ads-select.sh` — reads `ADS_ACTIVE` from `~/.bashrc`, sources the matching profile, calls license switch if needed.

**User `~/.bashrc`:**

```bash
# Top of file:
ADS_ACTIVE=2025   # change to 2026 to switch
export ADS_ACTIVE

# Bottom (after Cadence/Mentor blocks):
source /etc/profile.d/ads-select.sh

# Wrapper — ensures license matches before launch:
ads() {
  case "${ADS_ACTIVE:-2025}" in
    2026) _ap='lmgrd -c /opt/eda/agilent/ADS2026/' ;;
    *)    _ap='lmgrd -c /opt/eda/agilent/ADS2025/' ;;
  esac
  if ! pgrep -f "$_ap" >/dev/null 2>&1; then
    /usr/local/bin/ads-licensure.sh "${ADS_ACTIVE:-2025}"
    sleep 2
  fi
  unset _ap
  "${HPEESOF_DIR:?}/bin/ads" "$@"
}
```

After changing `ADS_ACTIVE`: `source ~/.bashrc`. Launch: `ads &` (same command for both versions).

### Step 3 — Deploy license & strip CRLF

```bash
cp "/tmp/PathWaveLinuxPatcher vXX.XX/License/agileesofd.lic" "$INSTALL_DIR/licenses/"
sed -i "s/^SERVER this_host /SERVER $(hostname) /" "$INSTALL_DIR/licenses/agileesofd.lic"
# ADS2026 only — use separate port:
sed -i "s/^SERVER $(hostname) ANY 27009/SERVER $(hostname) ANY 27010/" "$INSTALL_DIR/licenses/agileesofd.lic"
sed -i 's/\r$//' "$INSTALL_DIR/licenses/agileesofd.lic"   # REQUIRED — see pitfalls
grep '^SERVER' "$INSTALL_DIR/licenses/agileesofd.lic"
```

### Step 4 — FlexNetLicensePatcher (three directories per version)

```bash
# 1. $LICDIR — server: lmgrd, lmutil, agileesofd, libagsl
# 2. $INSTALL_DIR/lib/linux_x86_64 — client libagsl (ADS GUI)
# 3. $FEM_EDB — FEM simulator libagsl

cd "$LICDIR" && LD_LIBRARY_PATH=/usr/lib64:$LICDIR ./FlexNetLicensePatcher -y
cd "$INSTALL_DIR/lib/linux_x86_64" && LD_LIBRARY_PATH=/usr/lib64 "$LICDIR/FlexNetLicensePatcher" -y
cd "$FEM_EDB" && LD_LIBRARY_PATH=/usr/lib64 "$LICDIR/FlexNetLicensePatcher" -y
```

> Patching only `Licensing/bin` → server UP but ADS shows "ADS License not available".

### Step 5 — License server (decoupled, mutually exclusive)

**One `agileesofd` per host** — FlexNet lock `/var/tmp/lockagileesofd`. ADS2025 and ADS2026 **cannot run license servers simultaneously**. Use separate ports and switch with `ADS_ACTIVE`.

**Wrapper scripts** (lmgrd **must** `cd` to `$LICDIR` before start):

- `/usr/local/bin/ads-lmgrd-2025-start.sh` / `-stop.sh`
- `/usr/local/bin/ads-lmgrd-2026-start.sh` / `-stop.sh`
- systemd: `Type=oneshot`, `RemainAfterExit=yes`

**Switch script** `/usr/local/bin/ads-licensure.sh`:

```bash
# Usage: ads-licensure.sh [2025|2026]
# Pass version as argument — sudo strips ADS_ACTIVE from environment!
ads-licensure.sh 2026
```

**Passwordless sudo for desktop users** (optional):

```
# /etc/sudoers.d/ads-licensure
userone ALL=(root) NOPASSWD: /usr/local/bin/ads-licensure.sh
```

Boot: enable only `ads-lmgrd-2025` by default; `ads-licensure.sh` switches when user sets `ADS_ACTIVE=2026`.

**SELinux (Enforcing):**

```bash
semanage fcontext -a -t bin_t "$LICDIR(/.*)?" 2>/dev/null || \
  semanage fcontext -m -t bin_t "$LICDIR(/.*)?"
restorecon -Rv "$LICDIR"
```

**Verify:**

```bash
lmutil lmstat -c 27009@localhost | grep -E "UP|agileesofd"   # 2025
lmutil lmstat -c 27010@localhost | grep -E "UP|agileesofd"   # 2026
```

Use `env -i PATH=/usr/bin:/usr/sbin:/bin:/sbin HOME=/root systemctl ...` if OPENSSL conflicts.

### Step 6 — Launch ADS

Requires graphical desktop (X11 / XWayland). `lsb_release: not found` is harmless.

```bash
source ~/.bashrc
echo "$ADS_VERSION $HPEESOF_DIR $ADS_LICENSE_FILE"
ads &
```

---

## Pitfalls (learned from real installs)

| Issue | Symptom | Fix |
|-------|---------|-----|
| Non-root install | sudo prompts, polkit popups, mid-install halt | **SSH as root** for install |
| License CRLF | `Failed to open the TCP port` | `sed -i 's/\r$//' *.lic` |
| lmgrd wrong cwd | systemd crash-loop, status=35 | Use wrapper scripts; `cd $LICDIR` |
| Shared license server | ADS2026 "License Server/Client Mismatch" | Decouple: 2026 on 27010 with v11.19.7 lmgrd |
| Two agileesofd at once | `lockagileesofd` conflict, one vendor dies | Mutual exclusive switch via `ads-licensure.sh` |
| `sudo` drops `ADS_ACTIVE` | Wrong lmgrd after switch | Pass version arg: `ads-licensure.sh 2026` |
| License switch every terminal | Polkit password loop | Only switch when pgrep mismatch; NOPASSWD sudoers |
| ADS2026 GUI | `libOpenGL.so.0 not found` | `dnf install libglvnd-opengl` |
| 2026 tar layout | SETUP.SH not in expected subdir | Media may be `Linux/SETUP.SH` after extract |
| Wrong patcher version | Patch fails or license rejected | v24.08 for 2025, v25.07 for 2026 |

---

## Diagnosis — "ADS License not available"

```bash
echo "ADS_ACTIVE=$ADS_ACTIVE ADS_LICENSE_FILE=$ADS_LICENSE_FILE HPEESOF_DIR=$HPEESOF_DIR"
pgrep -af 'lmgrd|agileesofd'
# Check the port matching ADS_LICENSE_FILE:
lmutil lmstat -c 27009@localhost | head -15   # 2025
lmutil lmstat -c 27010@localhost | head -15   # 2026
```

| Symptom | Cause | Action |
|---------|-------|--------|
| `ADS_LICENSE_FILE=27010` but only 27009 listening | License not switched | `ads-licensure.sh 2026` or `source ~/.bashrc` |
| Server UP, ADS still no license | Client `libagsl` unpatched | Step 4: patch `lib/linux_x86_64` |
| `ads: command not found` | `ads-select.sh` not in `.bashrc` | Source `ads-select.sh`; use `ads()` wrapper |
| Version mismatch warning | 2026 client + 2025 lmgrd | Switch to `ads-lmgrd-2026@27010` |

---

## Checklist — Adding ADS2027+

1. Install to `/opt/eda/agilent/ADS<YYYY>` (never overwrite existing)
2. Copy/adapt `install_ads<YYYY>_as_root.sh`; new Patcher zip version
3. Create `/etc/profile.d/ads<YYYY>.sh` with unique `ADS_LICENSE_FILE` port
4. Add `case` branch in `ads-select.sh` and `ads-licensure.sh`
5. Patch three directories; deploy `.lic` with hostname + CRLF strip
6. Create `ads-lmgrd-<YYYY>.service` + start/stop wrappers
7. Add row to Version Matrix; update `/opt/eda/agilent/README-ADS.md`

---

## Design Principles

1. **Install as root** — simplest path; avoid sudo friction during 30-min SETUP.SH
2. **One install dir per version** under `/opt/eda/agilent/`
3. **One profile per version** + shared `ads-select.sh` — user flips one line `ADS_ACTIVE`
4. **Decoupled license ports** — matching lmgrd binary version per ADS release
5. **Mutually exclusive license servers** — one `agileesofd` per host
6. **Pass version to licensure explicitly** — never rely on env through `sudo`
7. **SKILL = agent manual**; **README-ADS.md = on-host cheat sheet**; **install scripts = automation**
