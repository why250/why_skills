# Windows OpenSSH → Linux 虚拟机免密登录

全部 Windows 代码块在 **PowerShell** 执行，Linux 端命令另行标明。地址、别名、用户名必须来自实际探测。

## 1. 本地配置（保留旧 Host）

```powershell
ssh -V
New-Item -ItemType Directory -Force "$env:USERPROFILE\.ssh" | Out-Null
$config = "$env:USERPROFILE\.ssh\config"
if (Test-Path $config) { Copy-Item $config "$config.bak" -Force }
notepad $config
```

在 config 中**只添加一个新的、不重复的 Host 块**（已有则编辑该块；不要重复追加）：

```sshconfig
Host IC_Analog
    HostName <actual-guest-ip>
    User <linux-user>
    IdentityFile ~/.ssh/id_ed25519
    ServerAliveInterval 60
    ServerAliveCountMax 3
```

- `IdentityFile` 应为客户端真实存在的私钥；若使用其他密钥，请替换。按需添加 `ForwardX11 yes`，但需要 Windows X server。
- 这只是直连配置。如果是经 Tailscale 到 Windows 宿主机的远程笔记本，应增加另一个 Host 块，并仅在那一块使用 `ProxyJump my-home-pc`；预先验证跳板别名可以单独 SSH 登录。
- 首次 `ssh IC_Analog` 之前，在 Linux VM 控制台执行 `ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub`（或实际启用的主机公钥），与 Windows 首次显示的 host-key 指纹核对。不要对未知或变更后的指纹盲目接受。
- 可先运行 `Test-NetConnection <actual-guest-ip> -Port 22`；远程跳板情形应测试跳板而非直接测试 NAT Guest IP。

## 2. 复用客户端密钥（不覆盖）

```powershell
$pub = "$env:USERPROFILE\.ssh\id_ed25519.pub"
Test-Path $pub
```

如返回 `False`，先检查 `Get-ChildItem "$env:USERPROFILE\.ssh\*.pub"`，优先复用现有合适密钥。确实没有时才生成：

```powershell
ssh-keygen -t ed25519 -f "$env:USERPROFILE\.ssh\id_ed25519"
```

密钥最好设置口令并结合 Windows ssh-agent 使用；绝不覆盖已有私钥，不把私钥上传或复制进 VM。

## 3. 安全追加公钥（可重复执行）

先确认 `ssh IC_Analog` 能通过可信的主机指纹和密码正常登录。下面命令从 Windows 把**公钥**发送到 Linux，在服务器端修复用户 SSH 目录权限、逐行去重并追加。不要用 `>` 覆盖已有 `authorized_keys`。

```powershell
$pub = "$env:USERPROFILE\.ssh\id_ed25519.pub"
if (-not (Test-Path $pub)) { throw "Missing public key: $pub" }
Get-Content $pub | ssh IC_Analog 'umask 077; mkdir -p "$HOME/.ssh"; chmod 700 "$HOME/.ssh"; touch "$HOME/.ssh/authorized_keys"; chmod 600 "$HOME/.ssh/authorized_keys"; while IFS= read -r key; do [ -n "$key" ] || continue; grep -qxF -- "$key" "$HOME/.ssh/authorized_keys" || printf "%s\n" "$key" >> "$HOME/.ssh/authorized_keys"; done'
if ($LASTEXITCODE -ne 0) { throw "Public key installation failed" }
```

注意：PowerShell 直接调用外部 `ssh`，远端 shell 将执行单引号字符串内的脚本。若远端 home/SSH 文件归属曾被 root 误改，须先从 VM 控制台核查 `ls -ld ~ ~/.ssh ~/.ssh/authorized_keys` 并由管理员修复归属；不能无条件 `chown`。

## 4. 验收及失败排查

```powershell
ssh -o BatchMode=yes -o PreferredAuthentications=publickey IC_Analog "whoami; hostname"
$LASTEXITCODE
```

退出码必须为 0，用户名符合预期，且无密码提示。若密钥含口令，先在 Windows ssh-agent 中加载/解锁，或使用已有 agent；`BatchMode=yes` 不会弹出解锁提示。

诊断：

- `Connection timed out / refused`：查 NAT 网段、跳板、`Test-NetConnection`、sshd、防火墙和监听地址。
- `Permission denied (publickey)`：查 `ssh -vvv IC_Analog`、`ssh -G IC_Analog`、实际提供的密钥、`authorized_keys` 内容与权限、`sshd_config` 的 `PubkeyAuthentication` / `AuthorizedKeysFile`，以及 SELinux 文件上下文（必要时由管理员 `restorecon -RFv ~/.ssh`）。
- `REMOTE HOST IDENTIFICATION HAS CHANGED`：先独立核对新指纹及是否更换 VM/MAC/IP，确认确实是可信新主机后才清理相应 known_hosts 条目。
- VS Code Remote-SSH 失败而终端 SSH 成功：检查 VS Code Remote-SSH 日志、远端 shell 启动脚本、系统兼容性与所需组件；不等同于密钥登录失败。
