---
name: linux-vm-ssh-setup
description: >-
  Set up or repair SSH access from Windows/VS Code to a new Linux VM, including
  VMware networking, sudo permissions, sshd, key-based login, and optional
  Tailscale/ProxyJump. Use when onboarding a Linux VM or fixing SSH login.
---

# Linux VM SSH setup

目标：从新装的 Linux 虚拟机到 **Windows OpenSSH + VS Code Remote-SSH 的非交互密钥登录**。默认最小改动；每一步通过可观察结果验收。优先检查仓库已有配置，复用既有 SSH 密钥和 Host 条目。

## 1. 探测（只读）

- 在 **Linux VM 控制台**：运行 `bash scripts/inspect-linux.sh`（路径相对于本 Skill 目录），或执行 `cat /etc/os-release; whoami; id; ip -4 addr; ip -4 route; nmcli connection show --active`。
- 在 **Windows 客户端**：确认 `ssh -V`、`$env:USERPROFILE\.ssh\config`、公钥是否存在，以及访问位置（Windows VMware 宿主机 / 同一局域网 / Tailscale 外部笔记本）。
- 确定真正的虚拟机网卡及其 IPv4；`virbr0` 的 `192.168.122.1` 往往是 libvirt 私有网桥，不是 VM 的 SSH 地址。只有 `UP,LOWER_UP` 且有可达地址，才进入 SSH 配置。
- 收集：Linux 发行版、用户名、SSH 别名、实际 IP、是否具备 sudo、是否已安装 sshd、Windows 公钥路径。**不要把示例 IP 当真实 IP。**

网络或权限异常时按 [network-and-privileges.md](references/network-and-privileges.md) 分支处理；问题未解决前不要继续修改远端服务。

## 2. 最小化开通 Linux SSH

1. 检查 `id -nG` 和 `sudo -n true`（后者失败也可能只是需要输入密码）。没有管理员权限时走 root/控制台恢复路径；**不要伪装成能远程提升权限**。
2. 检查 `command -v sshd` 和 `systemctl is-active sshd`。缺少时按发行版安装：Rocky/RHEL 用 `sudo dnf install -y openssh-server`；Ubuntu/Debian 用 `sudo apt install -y openssh-server`（先确认仓库可用）。已有包则跳过安装。
3. Rocky/RHEL: `sudo systemctl enable --now sshd`；Ubuntu/Debian: `sudo systemctl enable --now ssh`（有的发行版服务也叫 `sshd`，以 `systemctl list-unit-files` 为准）。
4. 若 firewalld **已运行**，用 `sudo firewall-cmd --query-service=ssh` 检查；未放行时执行 `sudo firewall-cmd --permanent --add-service=ssh && sudo firewall-cmd --reload`。其他防火墙按实际状态处理，不关闭防火墙或 SELinux。
5. 验收：SSH 服务 `active`，端口有监听（`ss -ltn | grep ':22 '`，如服务使用自定义端口则相应替换），客户端能通过用户名/密码或既有密钥进行初次登录。初次接受 host key 前核验指纹。

## 3. Windows 客户端配置与密钥注册

读取 [windows-openssh.md](references/windows-openssh.md)，遵循 **备份 → 增量修改 → 首次连接 → 复用/生成公钥 → 追加公钥（去重）→ 验收**。沿用已有 Windows 私钥；不得复制私钥到 VM 或覆盖现有 `authorized_keys`。不要打开 root SSH 登录，也不要先关闭密码认证。

## 4. 按需配置远程跳板与 IDE

- 仅当客户端无法直接访问 VMware NAT 子网、且已验证有可访问的 Windows/Tailscale 跳板时，在**客户端**新增单独的 Host Alias 和 `ProxyJump <jump-alias>`，不要让两个别名互相循环跳转。
- 在 VS Code 选择 `Remote-SSH: Connect to Host`，选与网络位置匹配的别名。图形应用需要 X server / DISPLAY 等额外依赖；`ForwardX11 yes` 本身不能保证 Virtuoso GUI 显示。
- 默认保留 DHCP：租约通常稳定但**不保证**永久固定。只有用户明确要求固定 IP 且核验 VMnet DHCP 池、网关、DNS、地址冲突后才修改网络；网络变更要在 VM 控制台完成。

## 5. 验收与记录

从 Windows PowerShell 执行（替换别名）：

```powershell
ssh -o BatchMode=yes -o PreferredAuthentications=publickey IC_Analog "whoami; hostname"
ssh -G IC_Analog | Select-String "^(hostname|user|proxyjump|identityfile) "
```

第一条必须无需交互且退出码为 0；含口令密钥须先在本机 ssh-agent 解锁。随后实际测试 VS Code Remote-SSH。若失败，用 `ssh -vvv IC_Analog` 定位哪一层失败，参照 [windows-openssh.md](references/windows-openssh.md)。

向用户报告：OS、用户名、IP（DHCP/静态）、连接别名、连接路径、sshd/防火墙状态、密钥验证结果、VS Code 状态、尚未验证项。**不要将“命令已执行”写成“验证通过”**；不能访问 Windows/VM 时明确说明需要用户在对应机器执行哪些命令。
