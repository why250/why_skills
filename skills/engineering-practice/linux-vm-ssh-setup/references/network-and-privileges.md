# VMware 网络与 Linux 权限分支

## 网络诊断：先链路、再地址、再路由

在 Linux VM 控制台执行：

```bash
ip -br link
ip -4 addr
ip -4 route
nmcli device status
nmcli connection show --active
```

- `NO-CARRIER` / `state DOWN`：先在 VMware Workstation → VM Settings → Network Adapter 检查 **Connected** 与 **Connect at power on**，并核验 VMnet8 NAT/指定 VMnet 设置。之后在控制台重新检查 `LOWER_UP`；不要先硬编码 IP 企图修复物理链路。
- `LOWER_UP` 但没有 IPv4：检查 NetworkManager 连接和 DHCP（`nmcli connection show`、`nmcli device connect <iface>`）。确认 NAT DHCP 服务、地址池和虚拟机网段。
- `virbr0` 的 `192.168.122.1/24` 通常由 libvirt 建立，与 VMware VMnet8 的客户端 SSH 地址无关。
- Windows VMware 宿主机通常可以访问 NAT Guest IP；跨互联网的笔记本不能直接路由到 `192.168.x.x`，应通过已建立连接的跳板或经过授权的 VPN/路由访问。
- 先验证 **Windows → VM IP:22**：`Test-NetConnection <guest-ip> -Port 22`；成功后再排查身份认证。该命令只能证明端口可达，不等于登录成功。

## DHCP 与静态 IP

默认继续 DHCP，VMware 通常给同一 MAC 续租同一地址，但不能保证永不变化。仅按需固定，且须先核对：VMnet8 子网和 DHCP 起止范围、网关、DNS、MAC、地址是否被占用；避免在 DHCP 池中直接设静态地址。

Rocky 8 NetworkManager 配置名 **不一定与网卡名相同**：

```bash
nmcli connection show --active
ip -4 route
nmcli device show <iface> | grep IP4.DNS
```

确认信息后才使用 `nmcli connection modify "<actual-profile>" ipv4.method manual ...`。连接重启可能断 SSH，优先在 VMware 控制台执行，保留回滚路径。

## sudo 错误（已验证案例）

`<user> is not in the sudoers file` 表明该会话没有 sudo 权限；在 Rocky/RHEL 控制台若 root 密码可用：

```bash
su -
usermod -aG wheel <user>
id <user>
exit
```

在 Ubuntu/Debian 用 `usermod -aG sudo <user>`（需已获得 root/其他管理员权限）。**务必保留 `-aG`** 以免覆盖其他附加组。然后注销用户会话并重新登录，确认 `id -nG` 包含目标组、`sudo whoami` 输出 `root`。

只执行 `exit` 离开 `su` 不会刷新原始用户会话的组列表。Rocky/RHEL 可以临时用 `newgrp wheel` 开一个新 shell，再用 `groups; sudo whoami` 验证；持久登录会话仍应完整重新登录。如果组已生效但 sudo 仍失败，由 root 用 `visudo` 核查 `%wheel ALL=(ALL) ALL`，不可直接粗暴覆盖 `/etc/sudoers`。

无法 `su -` 时，转向现有管理员账户或受授权的控制台恢复流程；不提供未经授权的提权操作。
