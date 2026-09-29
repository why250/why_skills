---
name: configure-ads-linux
description: Install and configure Keysight ADS 2025/2026/2027+ on RHEL/Rocky Linux. Covers root SSH install preference, silent SETUP.SH, FlexNet patcher, multi-version layout, ADS_ACTIVE switching, decoupled license servers (27009/27010/27011), ads-licensure.sh, ads-lmgrd-start.sh, SELinux, post-reboot license recovery, and troubleshooting. Use when installing ADS, switching versions, ADS won't open after reboot, ADS License not available, License Server/Client Mismatch, agileesofd lock conflicts, ads-lmgrd failures, or terminal polkit password prompts.
---

# Keysight ADS Linux — Install & Multi-Version Configuration

Covers **ADS2025, ADS2026, ADS2027**, and future releases using the same patterns.

**Automation scripts:**
- [`ADS2025/Linux/install_ads2025_as_root.sh`](../../ADS2025/Linux/install_ads2025_as_root.sh)
- [`ADS2026/Linux/install_ads2026_as_root.sh`](../../ADS2026/Linux/install_ads2026_as_root.sh)
- [`ADS2027_tar/Linux/install_ads2027_as_root.sh`](../../ADS2027_tar/Linux/install_ads2027_as_root.sh)

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
2. Add `/etc/sudoers.d/ads-licensure` for passwordless license switching (see Step 5)
3. Expect manual intervention for systemctl / `/opt` writes

**Agent default:** run install and system config commands as root unless the user explicitly forbids root SSH.

---

## Version Matrix (this host)

| Item | ADS2025 | ADS2026 | ADS2027 |
|------|---------|---------|---------|
| Install dir | `/opt/eda/agilent/ADS2025` | `/opt/eda/agilent/ADS2026` | `/opt/eda/agilent/ADS2027` |
| Media / tar | `ads_2025_shp_linux_x64` | `ads_2026_update1_shp_linux_x64` | `ads_2027_shp_linux_x64` |
| LICDIR | `Licensing/2024.06/linux_x86_64/bin` | `Licensing/2025.4/linux_x86_64/bin` | `Licensing/2026.3/linux_x86_64/bin` |
| FEM patch dir | `fem/2025.00/linux_x86_64/bin/edb` | `fem/2026.10/linux_x86_64/bin/edb` | `fem/2027.00/linux_x86_64/bin/edb` |
| Patcher zip | `PathWaveLinuxPatcher v24.08` | `PathWaveLinuxPatcher v25.07` | `PathWaveLinuxPatcher v26.08` |
| Profile | `/etc/profile.d/ads2025.sh` | `/etc/profile.d/ads2026.sh` | `/etc/profile.d/ads2027.sh` |
| `ADS_LICENSE_FILE` | `27009@localhost` | `27010@localhost` | `27011@localhost` |
| systemd | `ads-lmgrd-2025.service` | `ads-lmgrd-2026.service` | `ads-lmgrd-2027.service` |
| lmgrd version | v11.19.2 | v11.19.7 | v11.19.8 |
| Log | `/var/log/ads_lmgrd_2025.log` | `/var/log/ads_lmgrd_2026.log` | `/var/log/ads_lmgrd_2027.log` |
| Boot enable | **yes** (only this one) | **no** | **no** |
| Extra GUI dep | — | `dnf install libglvnd-opengl` | `dnf install libglvnd-opengl` |

Discover paths dynamically when version numbers differ:

```bash
LICDIR=$(dirname "$(find "$INSTALL_DIR/Licensing" -name lmgrd -type f | head -1)")
FEM_EDB=$(find "$INSTALL_DIR/fem" -path '*/bin/edb' -type d 2>/dev/null | head -1)
```

---

## Standard Layout

```
/opt/eda/agilent/
├── ADS2025/  ADS2026/  ADS2027/          # isolated install trees

/etc/profile.d/
├── ads2025.sh  ads2026.sh  ads2027.sh     # per-version env only
└── ads-select.sh                           # reads ADS_ACTIVE, calls ads-licensure.sh

/usr/local/bin/
├── ads-lmgrd-start.sh                      # shared start helper (env -i + retry)
├── ads-lmgrd-2025-start.sh  …-stop.sh
├── ads-lmgrd-2026-start.sh  …-stop.sh
├── ads-lmgrd-2027-start.sh  …-stop.sh
└── ads-licensure.sh                        # mutual-exclusive switch [2025|2026|2027]

/etc/systemd/system/
├── ads-lmgrd-2025.service   (enabled)      # ONLY this one at boot
├── ads-lmgrd-2026.service   (disabled)
└── ads-lmgrd-2027.service   (disabled)

/etc/sudoers.d/ads-licensure                # optional: NOPASSWD for userone
~/.bashrc: ADS_ACTIVE=2025|2026|2027
```

---

## Install Flow

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
cd /path/to/Linux          # directory containing SETUP.SH
# installer.properties MUST also be copied to the VM subdir:
cp installer.properties linux_x86_64/Linux/Disk1/InstData/VM/
./SETUP.SH -i silent -f installer.properties
# installer.properties: USER_INSTALL_DIR=/opt/eda/agilent/ADS<YYYY>
```

> SETUP.SH delegates to `linux_x86_64/Linux/Disk1/InstData/VM/ads_install.bin`, which resolves `-f installer.properties` relative to **its own directory**, not the SETUP.SH directory. Missing copy → `Valid properties/response file not specified`.

**Compatibility fixes (idempotent):**

```bash
ln -sf /lib64/ld-linux-x86-64.so.2 /lib64/ld-lsb-x86-64.so.3
cp /usr/lib64/libstdc++.so.6.0.29 "$LICDIR/libstdc++.so.6.0.29"  # if placeholder is 0 bytes
```

Or run the version-specific `install_ads<YYYY>_as_root.sh` (skips SETUP.SH if already installed).

### Step 2 — Environment & version switching

**Per-version profiles** (`ads2025.sh`, `ads2026.sh`, `ads2027.sh`) — only version-specific `HPEESOF_DIR`, `PATH`, `ADS_LICENSE_FILE`. No switching logic inside.

**Shared selector** `/etc/profile.d/ads-select.sh` — reads `ADS_ACTIVE` from `~/.bashrc`, sources the matching profile, **always calls `ads-licensure.sh`** (which no-ops if license already healthy).

**User `~/.bashrc`:**

```bash
# Top of file:
ADS_ACTIVE=2025   # change to 2026 or 2027 to switch
export ADS_ACTIVE

# Bottom (after Cadence/Mentor blocks):
source /etc/profile.d/ads-select.sh

# Wrapper — ensures license matches before launch:
ads() {
  sudo -n /usr/local/bin/ads-licensure.sh "${ADS_ACTIVE:-2025}" 2>/dev/null || true
  sleep 1
  "${HPEESOF_DIR:?}/bin/ads" "$@"
}
```

After changing `ADS_ACTIVE`: `source ~/.bashrc`. Launch: `ads &` (same command for all versions).

> **Do NOT** use `pgrep -f lmgrd` to decide whether license is healthy. lmgrd can be listening while `agileesofd` is dead (common after reboot conflict). Always delegate to `ads-licensure.sh`.

### Step 3 — Deploy license & strip CRLF

```bash
cp "/tmp/PathWaveLinuxPatcher vXX.XX/License/agileesofd.lic" "$INSTALL_DIR/licenses/"
sed -i "s/^SERVER this_host /SERVER $(hostname) /" "$INSTALL_DIR/licenses/agileesofd.lic"
# Assign unique port per version (increment from 27009):
#   ADS2025 → 27009 (default in patcher zip)
#   ADS2026 → 27010
#   ADS2027 → 27011
sed -i "s/^SERVER $(hostname) ANY 27009/SERVER $(hostname) ANY 27XXX/" "$INSTALL_DIR/licenses/agileesofd.lic"
sed -i 's/\r$//' "$INSTALL_DIR/licenses/agileesofd.lic"   # REQUIRED — see pitfalls
grep '^SERVER' "$INSTALL_DIR/licenses/agileesofd.lic"
```

### Step 4 — FlexNetLicensePatcher (three directories per version)

```bash
# 1. $LICDIR — server: lmgrd, lmutil, agileesofd, libagsl
# 2. $INSTALL_DIR/lib/linux_x86_64 — client libagsl (ADS GUI)
# 3. $FEM_EDB — FEM simulator libagsl

cp "$PATCH_TMP/FlexNetLicensePatcher-R1.3" "$LICDIR/FlexNetLicensePatcher"
chmod +x "$LICDIR/FlexNetLicensePatcher"
cd "$LICDIR" && LD_LIBRARY_PATH=/usr/lib64:$LICDIR ./FlexNetLicensePatcher -y
cd "$INSTALL_DIR/lib/linux_x86_64" && LD_LIBRARY_PATH=/usr/lib64 "$LICDIR/FlexNetLicensePatcher" -y
cd "$FEM_EDB" && LD_LIBRARY_PATH=/usr/lib64 "$LICDIR/FlexNetLicensePatcher" -y
```

> Patching only `Licensing/bin` → server UP but ADS shows "ADS License not available".

### Step 5 — License server (decoupled, mutually exclusive)

**One `agileesofd` per host** — FlexNet lock `/var/tmp/lockagileesofd`. All ADS versions **cannot run license servers simultaneously**. Use separate ports and switch with `ADS_ACTIVE` + `ads-licensure.sh`.

#### 5a. Shared start helper — `/usr/local/bin/ads-lmgrd-start.sh`

All per-version start scripts delegate to this helper. It enforces two critical requirements:

1. **`env -i`** — run lmgrd/lmutil with a clean environment. Cadence/Mentor `LD_LIBRARY_PATH` / `OPENSSL_*` in the parent shell causes `Failed to open the TCP port number in the license`.
2. **Retry + health check** — up to 5 attempts; success = `agileesofd: UP` in lmstat (not merely lmgrd process exists). Handles port `TIME_WAIT` after rapid restarts.

```bash
# Usage: ads-lmgrd-start.sh <LICDIR> <LICFILE> <LOG> <PORT>
# Per-version wrappers are thin exec lines, e.g.:
exec /usr/local/bin/ads-lmgrd-start.sh \
  /opt/eda/agilent/ADS2025/Licensing/2024.06/linux_x86_64/bin \
  /opt/eda/agilent/ADS2025/licenses/agileesofd.lic \
  /var/log/ads_lmgrd_2025.log 27009
```

Stop scripts also use `env -i` when calling `lmutil lmdown`.

#### 5b. systemd units

```ini
[Unit]
Description=ADS20XX FlexNet License Server (lmgrd)
After=network.target
Conflicts=ads-lmgrd-2025.service ads-lmgrd-2026.service ads-lmgrd-2027.service

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/usr/local/bin/ads-lmgrd-20XX-start.sh
ExecStop=/usr/local/bin/ads-lmgrd-20XX-stop.sh
```

`Conflicts=` prevents systemd from starting multiple ADS license services in parallel.

#### 5c. Boot enable policy — CRITICAL

```bash
systemctl enable  ads-lmgrd-2025    # ONLY this one
systemctl disable ads-lmgrd-2026    # never enable at boot
systemctl disable ads-lmgrd-2027    # never enable at boot
```

**Never `systemctl enable` more than one `ads-lmgrd-*` service.** On reboot, two services starting simultaneously race for `/var/tmp/lockagileesofd`; one `agileesofd` wins, the other dies. Symptom: lmgrd listening but `agileesofd: No socket connection` → all ADS versions fail to open.

When adding a new ADS version: create and `daemon-reload` the new unit, but **do not enable it**. Users switch via `ads-licensure.sh`.

#### 5d. Switch script — `/usr/local/bin/ads-licensure.sh`

```bash
# Usage: ads-licensure.sh [2025|2026|2027]
# Pass version as argument — sudo strips ADS_ACTIVE from environment!
ads-licensure.sh 2027
```

Health check (must pass before no-op exit):

```bash
env -i PATH=/usr/bin:/usr/sbin:/bin:/sbin HOME=/root \
  LD_LIBRARY_PATH="/usr/lib64:$LICDIR" \
  "$LICDIR/lmutil" lmstat -c <PORT>@localhost | grep -q 'agileesofd: UP'
```

If unhealthy: stop all three services → kill residual lmgrd/agileesofd → remove lock file → start target service.

**Passwordless sudo for desktop users** (optional):

```
# /etc/sudoers.d/ads-licensure
userone ALL=(root) NOPASSWD: /usr/local/bin/ads-licensure.sh
```

#### 5e. SELinux (Enforcing)

```bash
semanage fcontext -a -t bin_t "$LICDIR(/.*)?" 2>/dev/null || \
  semanage fcontext -m -t bin_t "$LICDIR(/.*)?"
restorecon -Rv "$LICDIR"
```

#### 5f. Verify

```bash
# Use env -i when calling lmutil from a polluted shell (Cadence/Mentor loaded):
env -i PATH=/usr/bin:/bin HOME=/root LD_LIBRARY_PATH=/usr/lib64:$LICDIR \
  $LICDIR/lmutil lmstat -c 27009@localhost | grep -E "UP|agileesofd"   # 2025
# Repeat for 27010 (2026), 27011 (2027)
```

Success requires **both** lines:
```
xunipc: license server UP (MASTER) v11.19.x
agileesofd: UP v11.19.x
```

### Step 6 — Launch ADS

Requires graphical desktop (X11 / XWayland). `lsb_release: not found` is harmless.

```bash
source ~/.bashrc
echo "$ADS_VERSION $HPEESOF_DIR $ADS_LICENSE_FILE"
ads &
```

---

## Post-Reboot Recovery

**Symptom:** ADS worked yesterday, all versions fail after reboot.

**Diagnose:**

```bash
systemctl is-enabled ads-lmgrd-2025 ads-lmgrd-2026 ads-lmgrd-2027
pgrep -af 'lmgrd|agileesofd'
for p in 27009 27010 27011; do
  echo "=== port $p ==="
  lmutil lmstat -c ${p}@localhost 2>&1 | grep -E 'UP|agileesofd|Error' | head -3
done
tail -5 /var/log/ads_lmgrd_2025.log    # look for lockagileesofd / MULTIPLE agileesofd
```

**Typical root cause:** multiple `ads-lmgrd-*` services enabled → boot race → `agileesofd` dead.

**Fix:**

```bash
systemctl disable ads-lmgrd-2026 ads-lmgrd-2027   # leave only 2025 enabled
/usr/local/bin/ads-licensure.sh 2025              # or matching ADS_ACTIVE
# user:
source ~/.bashrc && ads &
```

---

## Pitfalls (learned from real installs)

| Issue | Symptom | Fix |
|-------|---------|-----|
| Non-root install | sudo prompts, polkit popups, mid-install halt | **SSH as root** for install |
| `installer.properties` not in VM dir | `Valid properties/response file not specified` | Copy to `linux_x86_64/Linux/Disk1/InstData/VM/` |
| License CRLF | `Failed to open the TCP port` | `sed -i 's/\r$//' *.lic` |
| lmgrd wrong cwd | systemd crash-loop, status=35 | Use wrapper scripts; `cd $LICDIR` |
| Shared license server | ADS2026 "License Server/Client Mismatch" | Decouple: unique port per version |
| **Multiple services enabled at boot** | After reboot: lmgrd UP, `agileesofd` dead, all ADS fail | **Enable only `ads-lmgrd-2025`**; add `Conflicts=` to units |
| Two agileesofd at once | `lockagileesofd` / `MULTIPLE agileesofd` in log | `ads-licensure.sh` stops all before start |
| **`pgrep lmgrd` false positive** | Script thinks license OK, ADS has no license | Check `agileesofd: UP` via lmstat, not process grep |
| **OPENSSL / LD_LIBRARY_PATH pollution** | `Failed to open the TCP port` from systemd | Start scripts use `env -i`; only set `LD_LIBRARY_PATH=/usr/lib64:$LICDIR` |
| Port TIME_WAIT after rapid restart | Intermittent bind failure on 27009 | `ads-lmgrd-start.sh` retries up to 5× with cleanup |
| `sudo` drops `ADS_ACTIVE` | Wrong lmgrd after switch | Pass version arg: `ads-licensure.sh 2027` |
| License switch every terminal | Polkit password loop | `ads-licensure.sh` no-ops when healthy; NOPASSWD sudoers |
| ADS2026/2027 GUI | `libOpenGL.so.0 not found` | `dnf install libglvnd-opengl` |
| Tar layout varies | SETUP.SH not in expected subdir | Media may be `Linux/SETUP.SH` after extract |
| Wrong patcher version | Patch fails or license rejected | Match patcher zip to ADS release (see Version Matrix) |
| Accidentally `enable` new version service | Recurring post-reboot failures | After adding ADS20XX: `systemctl disable ads-lmgrd-20XX` |

---

## Diagnosis — "ADS License not available"

```bash
echo "ADS_ACTIVE=$ADS_ACTIVE ADS_LICENSE_FILE=$ADS_LICENSE_FILE HPEESOF_DIR=$HPEESOF_DIR"
systemctl is-enabled ads-lmgrd-2025 ads-lmgrd-2026 ads-lmgrd-2027
pgrep -af 'lmgrd|agileesofd'
# Check the port matching ADS_LICENSE_FILE (use env -i if lmutil fails):
lmutil lmstat -c 27009@localhost | head -15   # 2025
lmutil lmstat -c 27010@localhost | head -15   # 2026
lmutil lmstat -c 27011@localhost | head -15   # 2027
```

| Symptom | Cause | Action |
|---------|-------|--------|
| `license server UP` but `agileesofd: No socket connection` | Boot race or stale lmgrd | `ads-licensure.sh <version>` |
| `ADS_LICENSE_FILE=27011` but only 27009 listening | License not switched | `ads-licensure.sh 2027` or `source ~/.bashrc` |
| Server UP, ADS still no license | Client `libagsl` unpatched | Step 4: patch `lib/linux_x86_64` |
| `ads: command not found` | `ads-select.sh` not in `.bashrc` | Source `ads-select.sh`; use `ads()` wrapper |
| Version mismatch warning | 2027 client + 2025 lmgrd | Switch to matching version via `ads-licensure.sh` |
| All versions broken after reboot | Multiple `ads-lmgrd-*` enabled | Disable all except 2025; run `ads-licensure.sh 2025` |
| `Failed to open the TCP port` in log | CRLF, port conflict, or env pollution | Strip CRLF; `ads-licensure.sh`; verify `env -i` in start scripts |

---

## Checklist — Adding ADS20XX+

1. Install to `/opt/eda/agilent/ADS<YYYY>` (never overwrite existing)
2. Copy `installer.properties` to VM subdir; run/adapt `install_ads<YYYY>_as_root.sh`
3. Create `/etc/profile.d/ads<YYYY>.sh` with unique `ADS_LICENSE_FILE` port (next free: 27012…)
4. Add `case` branch in `ads-select.sh` and `ads-licensure.sh` (`_ads_license_healthy`)
5. Patch three directories; deploy `.lic` with hostname + unique port + CRLF strip
6. Create thin `ads-lmgrd-<YYYY>-start.sh` (exec `ads-lmgrd-start.sh …`) and `-stop.sh`
7. Create `ads-lmgrd-<YYYY>.service` with `Conflicts=` for all other ADS lmgrd units
8. **`systemctl daemon-reload && systemctl disable ads-lmgrd-<YYYY>`** — do NOT enable at boot
9. Add `2027` branch to `ads()` in `~/.bashrc`
10. Add row to Version Matrix; update `/opt/eda/agilent/README-ADS.md`
11. Verify: `ads-licensure.sh <YYYY>` → `agileesofd: UP`; switch back to 2025

---

## Design Principles

1. **Install as root** — simplest path; avoid sudo friction during 30-min SETUP.SH
2. **One install dir per version** under `/opt/eda/agilent/`
3. **One profile per version** + shared `ads-select.sh` — user flips one line `ADS_ACTIVE`
4. **Decoupled license ports** — matching lmgrd binary version per ADS release
5. **Mutually exclusive license servers** — one `agileesofd` per host
6. **Only one service enabled at boot** — `ads-lmgrd-2025` only; all others `disabled`
7. **Health = `agileesofd: UP`** — never trust `pgrep lmgrd` alone
8. **Clean environment for lmgrd** — `env -i` in all start/stop/health-check paths
9. **Pass version to licensure explicitly** — never rely on env through `sudo`
10. **SKILL = agent manual**; **README-ADS.md = on-host cheat sheet**; **install scripts = automation**
