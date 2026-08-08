---
name: configure-ads2025-linux
description: Configure Keysight ADS2025 on Linux after manual installation via SETUP.SH. Covers FlexNet license server setup, PathWave patcher, environment variables, LSB compatibility fix, SELinux labels for systemd lmgrd, systemd auto-start, and PATH configuration. Use when the user has installed ADS2025 and needs to complete post-install configuration, or when ADS reports "ADS License not available", or when lmgrd/agileesofd needs to be set up, or when ads-lmgrd.service fails with status=203/EXEC.
---

# ADS2025 Linux Post-Install Configuration

## Official README (PathWaveLinuxPatcher v24.08/ReadMe.txt)

The patcher ships with a 5-step README. Each step is reproduced below with expanded explanation based on real-world issues encountered on RHEL/Rocky Linux.

```
1. Install Keysight PathWare license manager and application
2. Set environment variable for your program
3. Copy FlexNetLicensePatcher to your need patch folder, and run it with ./FlexNetLicensePatcher -y
4. Use lmgrd to start your license server
5. All done
```

---

## Step 1 — Install PathWare License Manager and Application

> *README: "Install Keysight PathWare license manager and application"*

The user runs `SETUP.SH` manually to install ADS2025. Confirm the installation directory (e.g. `/home/userone/eda/agilent/ADS2025`) and set `INSTALL_DIR` for the remaining steps.

**Verify installation:**
```bash
ls $INSTALL_DIR/bin/ads          # ADS launcher script
ls $INSTALL_DIR/Licensing/2024.06/linux_x86_64/bin/lmgrd   # license server
```

**Linux compatibility fix — LSB interpreter:**
ADS FlexNet binaries (`lmgrd`, `agileesofd`) require `/lib64/ld-lsb-x86-64.so.3` which is absent on modern RHEL/Rocky. Create the symlink:
```bash
ln -sf /lib64/ld-linux-x86-64.so.2 /lib64/ld-lsb-x86-64.so.3
```
Without this, lmgrd fails with `No such file or directory` even though the binary exists.

**Fix empty libstdc++ placeholder:**
The installer leaves a 0-byte `libstdc++.so.6.0.29` in `Licensing/bin/`. Replace it:
```bash
LICDIR=$INSTALL_DIR/Licensing/2024.06/linux_x86_64/bin
cp /usr/lib64/libstdc++.so.6.0.29 $LICDIR/libstdc++.so.6.0.29
```
Without this, `FlexNetLicensePatcher` crashes with `libstdc++.so.6: file too short`.

---

## Step 2 — Set Environment Variables

> *README: "Set environment variable for your program — export ADS_LICENSE_FILE=27009@localhost"*

`27009@localhost` tells ADS to contact the FlexNet license server on port 27009 of the local machine. Add to `/etc/profile.d/ads2025.sh` (applies to all users including root):

```bash
# ADS2025
export HPEESOF_DIR=<INSTALL_DIR>
export PATH=$HPEESOF_DIR/bin:$HPEESOF_DIR/Licensing/2024.06/linux_x86_64/bin:$PATH
export ADS_LICENSE_FILE=27009@localhost
export LD_LIBRARY_PATH=/usr/lib64${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}
```

Also append to `/root/.bashrc` so root shells auto-load it:
```bash
echo 'source /etc/profile.d/ads2025.sh' >> /root/.bashrc
```

The README also lists variables for other Keysight tools (EMPRO, GENESYS, ICCAP, etc.) — add them only if those products are installed.

**Deploy the license file:**
```bash
mkdir -p $INSTALL_DIR/licenses
cp "/tmp/PathWaveLinuxPatcher v24.08/License/agileesofd.lic" \
   $INSTALL_DIR/licenses/agileesofd.lic

# Replace placeholder hostname with actual hostname
sed -i "s/^SERVER this_host /SERVER $(hostname) /" \
   $INSTALL_DIR/licenses/agileesofd.lic

# Verify
grep "^SERVER" $INSTALL_DIR/licenses/agileesofd.lic
# Expected: SERVER <hostname> ANY 27009
```

---

## Step 3 — Run FlexNetLicensePatcher

> *README: "Copy FlexNetLicensePatcher to your need patch folder, and run it with ./FlexNetLicensePatcher -y"*

The patcher binary-patches FlexNet components to accept the `SIGN=0` license file. It scans the **current directory** for known binaries (`lmgrd`, `lmutil`, `libagsl.so.2024.06`, `agileesofd`) and patches each one found.

**"Your need patch folder" means every directory containing these files.** For ADS2025, three directories need patching:

```bash
PATCHER="/tmp/PathWaveLinuxPatcher v24.08/FlexNetLicensePatcher"
LICDIR=$INSTALL_DIR/Licensing/2024.06/linux_x86_64/bin

# 1. Licensing/bin — patches lmgrd, lmutil, libagsl, agileesofd (server side)
cp "$PATCHER" $LICDIR/
chmod +x $LICDIR/FlexNetLicensePatcher
cd $LICDIR
LD_LIBRARY_PATH=/usr/lib64:$LICDIR ./FlexNetLicensePatcher -y

# 2. lib/linux_x86_64 — patches libagsl loaded by ADS GUI (client side)
cd $INSTALL_DIR/lib/linux_x86_64
LD_LIBRARY_PATH=/usr/lib64 $LICDIR/FlexNetLicensePatcher -y

# 3. fem/edb — patches libagsl used by FEM simulator
cd $INSTALL_DIR/fem/2025.00/linux_x86_64/bin/edb
LD_LIBRARY_PATH=/usr/lib64 $LICDIR/FlexNetLicensePatcher -y
```

Expected output per run: `Patch point at: 0x... File: ./libagsl.so.2024.06` and `Total N files changed`.

> **Why `LD_LIBRARY_PATH=/usr/lib64`?** The 0-byte placeholder in `Licensing/bin` causes the patcher to crash. Prepending `/usr/lib64` makes the linker load the real system `libstdc++` instead.

> **Why must `lib/linux_x86_64` be patched separately?** ADS's main binary (`hpeesofde`) loads `libagsl.so.2024.06` from `lib/linux_x86_64/`, NOT from `Licensing/bin/`. If only `Licensing/bin/` is patched, ADS still shows "ADS License not available" because the client-side license check in `lib/linux_x86_64/libagsl.so.2024.06` is unpatched.

**What the patch does:** Changes a conditional jump (`JNZ 0x0F 0x85`) to an unconditional jump (`NOP + JMP 0x90 0xE9`) at offset `0x11BA8B` in `libagsl`, bypassing the license signature verification that would reject `SIGN=0` licenses.

---

## Step 4 — Start License Server with lmgrd

> *README: "Use lmgrd to start your license server"*

lmgrd is the FlexNet license manager daemon. It reads the `.lic` file, spawns the vendor daemon `agileesofd`, and serves checkout requests on port 27009.

**Manual start (one-time):**
```bash
LICDIR=$INSTALL_DIR/Licensing/2024.06/linux_x86_64/bin
LD_LIBRARY_PATH=/usr/lib64:$LICDIR \
$LICDIR/lmgrd \
  -c $INSTALL_DIR/licenses/agileesofd.lic \
  -l /var/log/ads_lmgrd.log &
```

> **Why `LD_LIBRARY_PATH=/usr/lib64:$LICDIR`?** lmgrd requires its own directory (`$LICDIR`) in the library path to locate its dependencies. Without `$LICDIR`, lmgrd starts but immediately fails with "Failed to open the TCP port number in the license".

**SELinux labels (required on RHEL/Rocky when ADS lives under `/home`):**

On SELinux **Enforcing** systems, files extracted/installed under `/home` are often `unlabeled_t`. systemd cannot execute them → `ads-lmgrd.service` fails with `status=203/EXEC` even though the binary runs fine when started manually by a user. Apply a persistent `bin_t` context **before** enabling the unit:

```bash
LICDIR=$INSTALL_DIR/Licensing/2024.06/linux_x86_64/bin
# Persist across restorecon / reboot
semanage fcontext -a -t bin_t "$LICDIR(/.*)?" 2>/dev/null || \
  semanage fcontext -m -t bin_t "$LICDIR(/.*)?"
restorecon -Rv "$LICDIR"
# Confirm key binaries
ls -Z $LICDIR/lmgrd $LICDIR/agileesofd $LICDIR/lmutil
# Expected: ... system_u:object_r:bin_t:s0 ... (or unconfined_u:...:bin_t:s0)
```

Without this step, the service may appear enabled but crash-loops after reboot; ADS then shows `ADS License not available` because nothing is listening on `27009@localhost`.

**Auto-start via systemd (recommended):**

Create `/etc/systemd/system/ads-lmgrd.service` (prefer single-line `ExecStart`/`ExecStop`):

```ini
[Unit]
Description=ADS2025 FlexNet License Server (lmgrd)
After=network.target

[Service]
Type=forking
Environment=LD_LIBRARY_PATH=/usr/lib64:<INSTALL_DIR>/Licensing/2024.06/linux_x86_64/bin
ExecStart=<INSTALL_DIR>/Licensing/2024.06/linux_x86_64/bin/lmgrd -c <INSTALL_DIR>/licenses/agileesofd.lic -l /var/log/ads_lmgrd.log
ExecStop=<INSTALL_DIR>/Licensing/2024.06/linux_x86_64/bin/lmutil lmdown -c <INSTALL_DIR>/licenses/agileesofd.lic -q
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Enable with a clean environment (ADS's `libcrypto.so.3` conflicts with systemctl):
```bash
env -i PATH=/usr/bin:/usr/sbin:/bin:/sbin HOME=/root systemctl daemon-reload
env -i PATH=/usr/bin:/usr/sbin:/bin:/sbin HOME=/root systemctl enable ads-lmgrd
env -i PATH=/usr/bin:/usr/sbin:/bin:/sbin HOME=/root systemctl start ads-lmgrd
```

**Verify the server is UP:**
```bash
LICDIR=$INSTALL_DIR/Licensing/2024.06/linux_x86_64/bin
LD_LIBRARY_PATH=/usr/lib64:$LICDIR \
  $LICDIR/lmutil lmstat -a -c 27009@localhost | grep -E "UP|agileesofd"
# Expected: xunipc: license server UP (MASTER) v11.19.2
#           agileesofd: UP v11.19.2
systemctl is-active ads-lmgrd   # expected: active
```

**One-shot repair script** (repo root): `fix-ads-lmgrd.sh` — stops crash-loop + user lmgrd, applies SELinux `bin_t`, rewrites the unit, restarts, and checks `lmstat`. Run as root: `sudo bash fix-ads-lmgrd.sh`.

---

## Step 5 — Launch ADS

> *README: "All done"*

```bash
source /etc/profile.d/ads2025.sh
ads &
```

ADS requires a graphical desktop session (X11 or Wayland with XWayland). Run from a terminal inside the desktop, not from an SSH session without `DISPLAY`.

`lsb_release: not found` during startup is a harmless warning on minimal RHEL images; it is **not** the license failure.

---

## Diagnosis — "It worked before, now ADS License not available"

When ADS previously launched and suddenly fails with `ADS License not available`, check the **license server first** (not the patcher):

```bash
# 1. Is anything serving licenses?
ps aux | grep -E 'lmgrd|agileesofd' | grep -v grep
LICDIR=$HPEESOF_DIR/Licensing/2024.06/linux_x86_64/bin
LD_LIBRARY_PATH=/usr/lib64:$LICDIR $LICDIR/lmutil lmstat -c 27009@localhost | head -20

# 2. systemd unit health
systemctl status ads-lmgrd --no-pager
# Crash-loop with status=203/EXEC → SELinux unlabeled_t (see Step 4)
# inactive/dead after reboot → start/repair unit

# 3. Confirm env still points at local server
echo "ADS_LICENSE_FILE=$ADS_LICENSE_FILE"   # expect 27009@localhost
grep '^SERVER' $HPEESOF_DIR/licenses/agileesofd.lic
```

| Symptom | Likely cause | Action |
|---|---|---|
| No `lmgrd` process; `lmstat` cannot connect | Server never started / died | `systemctl start ads-lmgrd` or run `fix-ads-lmgrd.sh` |
| Unit enabled but `203/EXEC` | SELinux blocks exec of `unlabeled_t` under `/home` | Step 4 SELinux `bin_t` + restart unit |
| Unit fails; log "Cannot open ... ads_lmgrd.log" | Non-root start writing `/var/log` | Start via systemd as root, or use `$HOME/.ads_lmgrd.log` for manual start |
| Server UP but ADS still no license | Client `libagsl` unpatched | Step 3: patch `lib/linux_x86_64` |

Temporary workaround **without root** (until systemd is fixed):

```bash
LICDIR=$HPEESOF_DIR/Licensing/2024.06/linux_x86_64/bin
LD_LIBRARY_PATH=/usr/lib64:$LICDIR $LICDIR/lmgrd \
  -c $HPEESOF_DIR/licenses/agileesofd.lic \
  -l $HOME/.ads_lmgrd.log
```

---

## Known Issues Quick Reference

| Error | Cause | Fix |
|---|---|---|
| `libstdc++.so.6: file too short` | 0-byte placeholder in Licensing/bin | Step 1: copy real libstdc++ |
| `lmgrd: No such file or directory` | Missing LSB interpreter | Step 1: create ld-lsb symlink |
| `Failed to open the TCP port` | lmgrd already running, or missing `$LICDIR` in LD_LIBRARY_PATH | Kill old lmgrd; ensure `$LICDIR` in LD_LIBRARY_PATH |
| `ADS License not available` (server down) | lmgrd not running after reboot / crash | Diagnosis section; start `ads-lmgrd` |
| `ADS License not available` (server UP) | `lib/linux_x86_64/libagsl.so` not patched | Step 3: patch all three directories |
| `ads-lmgrd` `status=203/EXEC` | SELinux `unlabeled_t` on binaries under `/home` | Step 4: `semanage fcontext` + `restorecon` to `bin_t` |
| `ads: command not found` | PATH not loaded (root shell) | `source /etc/profile.d/ads2025.sh` |
| systemctl fails with `OPENSSL_3.4.0 not found` | ADS libcrypto conflicts with systemd | Use `env -i` wrapper for systemctl commands |
| `lsb_release: not found` | Optional LSB tools missing | Ignore; not a license blocker |
