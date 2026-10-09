#!/usr/bin/env bash
# Read-only diagnostics. Run from a Linux VM console: bash inspect-linux.sh
set -u

section() { printf '\n== %s ==\n' "$1"; }
run() {
  if command -v "$1" >/dev/null 2>&1; then
    "$@" 2>&1 || true
  else
    printf '%s not installed\n' "$1"
  fi
}

section 'Identity and distribution'
run id
if [[ -r /etc/os-release ]]; then
  # Only show non-sensitive distribution identifiers.
  grep -E '^(ID|VERSION_ID|PRETTY_NAME)=' /etc/os-release || true
fi

section 'Links, IPv4 and routes'
run ip -br link
run ip -4 addr
run ip -4 route

section 'NetworkManager'
if command -v nmcli >/dev/null 2>&1; then
  run nmcli device status
  run nmcli connection show --active
else
  echo 'nmcli not installed (possible alternate network manager)'
fi

section 'SSH daemon'
if command -v systemctl >/dev/null 2>&1; then
  run systemctl is-active sshd
  run systemctl is-active ssh
else
  echo 'systemctl unavailable'
fi
if command -v ss >/dev/null 2>&1; then
  run ss -ltn
fi

section 'Firewall service (read-only)'
if command -v firewall-cmd >/dev/null 2>&1; then
  run firewall-cmd --state
  run firewall-cmd --query-service=ssh
else
  echo 'firewall-cmd not installed; inspect the active firewall separately'
fi

echo
echo 'Diagnostic only: no configuration was changed.'
