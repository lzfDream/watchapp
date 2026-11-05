# 公司机基线

> 机器：公司机（已加域；主机名与域名不写入仓库）
> 基线日期：2026-11-03（全量扫描）· 复核：2026-11-04
> 原始记录：`~/toolchain-inventory/README.md`（578 行，含扫描方法与全部版本对照）
> 软件条目：见 [catalog/software.md](../catalog/software.md) 的「公司机」与「共用」两节
> 2026-11-05 清单调整：catalog 移除 19 条、新增 9 条家用机共用、9 条升 P0；实际卸载 6 项，Docker Desktop 保留。本文件保留 2026-11-03 装机事实，明细见 [updates/2026-11-05.md](../updates/2026-11-05.md)

## 1. 环境底座

| 项 | 值 |
|---|---|
| 宿主系统 | Windows 11 专业版 25H2，build 26200.8875 |
| CPU / 内存 | Intel Core i7-10700 @ 2.90 GHz / 32 GB |
| 系统盘 | C: 239 GB，已用 147 GB（62%） |
| 域 | 已加域（`PartOfDomain = True`；域名不记录） |
| WSL | 3.0.3.0，内核 6.18.54.1，Ubuntu-24.04.4 LTS，systemd |
| WSL 资源 | 8 vCPU / 10 GB 内存 / 8 GB swap；虚拟盘 1007 GB，已用 57 GB |
| WSL 网络 | `networkingMode=mirrored`、`dnsTunneling`、`hostAddressLoopback`；`/mnt/c` 走 VirtioFS |
| 包管理 | Windows：winget / Store / 便携目录；WSL：apt + npm + uv |

> 公司机的特殊性：加域、装有 Zabbix Agent 2、Office 2019、飞书、TortoiseSVN；
> 这些由公司环境统一维护，不按个人偏好升级（见第 5 节）。

## 2. 软件分布（数量口径）

| 来源 | 规模 | 说明 |
|---|---|---|
| Windows 注册应用 | 40 个 | 卸载注册表去重后；Git / Apifox / Tabby 新注册 |
| Windows Store / MSIX | 约 70 个 | 含系统组件 |
| 软件根目录 | 22 个目录 / 6.9 GB | 便携/绿色软件；647 个 exe（Git 312、Cygwin 260 占多数） |
| WSL dpkg 包 | 862 条 | 手动安装约 100 个 |
| WSL npm 全局 | 5 个 | Claude Code、Codex、dsh、ZCode、npm 自身 |
| WSL uv tool | 1 个 | browser-use |
| VS Code 扩展 | Windows 46 / WSL 8 | WSL 侧没有 clangd/cpptools/cmake-tools |
| 本仓库 catalog | 66 条 | 公司机 43 + 共用 13 + 家用机 10（2026-11-05） |

## 2.1 安装习惯与目录

- **便携优先**：能解压即用的软件优先 portable / zip 版本，避免安装器把配置写进注册表和 AppData。
- **目录约定**：新装按 `D:\software\<领域>\<软件>` 的模板放置（游戏类、终端类等各占一个领域目录）；已有安装保持原路径，不强制迁移。具体路径不入库，只放本地 `.env` / 本地笔记。
- **开发环境**：以 WSL 为主（apt / npm / uv），Windows 侧只保留编辑器、终端、浏览器、办公与系统工具。

## 3. 重点软件与版本

只列需要跟进的工具；完整安装方式与命令见 [catalog/software.md](../catalog/software.md)，上游差距见 [updates/2026-11-03-radar.md](../updates/2026-11-03-radar.md)。

| 软件 | 公司机版本 | 安装方式 | 策略 |
|---|---|---|---|
| Visual Studio Code | 1.144.0 | winget（User） | P0 |
| Windows Terminal | 1.25.2733.0 | winget / Store | P1 |
| PowerShell 7 | 7.6.9 | MSI | P1 |
| Git for Windows | 2.56.0.windows.4 | 便携安装（路径不入库），**未入 PATH** | P1 |
| TortoiseSVN | 1.14.9.29743 | winget / MSI | P2 |
| Node.js | 24.14.1（winget LTS） | winget | 仅观察 |
| Python | 3.14.4 + PyManager 26.1.240 | python.org / PyManager | 仅观察 |
| .NET Runtime | 10.0.9 | winget | 仅观察 |
| Docker Desktop | 4.43.0 | winget | 不跟进（不常用） |
| Zed | 1.26.2 | winget | P1 |
| 7-Zip | 26.05 | winget + 便携 | P0 |
| WinRAR | 7.23 | winget | P1 |
| Everything | 1.4.1.1032 | winget + 便携 | P1 |
| Apifox | 2.8.52 | 便携安装（路径不入库） | P1 |
| Snow Shot | 1.4.4 | 便携安装（路径不入库） | P1 |
| WSL Docker Engine | 29.8.1 + Compose v5.5.1 | Docker 官方 apt 源 | P1 |
| Neovim (WSL) | 0.12.6 | 官方 tar 到 `~/.local/opt/nvim-0.12.6` | P1 |
| Claude Code | 2.1.278 | `npm -g` | P1 |
| Codex CLI | 0.154.0 | `npm -g` | P1 |
| dsh | 0.2.1-rc.5 | `npm -g` | P1 |
| browser-use | 0.13.10 | `uv tool` | P2 |

## 4. 停更 / 残留

| 软件 | 状态 | 说明 |
|---|---|---|
| WezTerm | 上游停更（正式版） | 20240203 之后只有夜版 |
| WindTerm | 上游停更 | 2025-03 后无发布 |
| Elyterminal | 上游停更 | 无公开文档/发布记录 |
| Navicat / CC Switch / SpaceSniffer / DiskGenius / HiBit / Docker Desktop | 不常用 · 停更跟踪 | 本机不再跟进版本，不代表上游停更 |
| 残留目录 | 目录残留 | `x64/bin` 为空；实际在用户级 Programs 目录 |
| 7-Zip / TortoiseSVN / 微信 | 并存 | 注册表版与便携版各一份，升级时留意两份 |

## 5. 公司机约束

- **加域机器**：公司统一管理的软件（Zabbix Agent 2、Office 2019、飞书、OneDrive 等）不要擅自升级或改配置。
- **Zabbix Agent 2**：监控代理，版本与配置跟随公司 Zabbix 服务端，不进入个人更新计划。
- **Docker**：WSL 内使用原生 `dockerd`；Docker Desktop 与它抢 `/var/run/docker.sock`，保持不启用。
- **Git**：Windows 侧 Git 未加入 PATH，日常版本控制走 TortoiseSVN + WSL git；不要因为 PATH 缺失就重装。
- **不要装 Visual Studio 实例**：只有 Installer，C/C++ 编译在 WSL 侧完成。
- **便携软件**：升级便携软件前先保留 `.bak-<版本>` 回滚点（已有 apifox、tabby、everything、snowshot 备份，约 1.6 GB）。
- **PowerShell**：默认用 `pwsh.exe`（7.x），不要用 `powershell.exe`（5.1）；从 WSL 调用时先设 UTF-8 输出编码。

## 6. 采集与复核

原始扫描口径见 `~/toolchain-inventory/README.md` 第 7 节。常用只读命令：

```powershell
# Windows：注册表 + Store + 可升级版本
winget list
winget upgrade --include-unknown
Get-AppxPackage | Where-Object { -not $_.IsFramework } | Select-Object Name, Version

# 软件根目录：一层目录 + 深度 2 的 exe 版本
Get-ChildItem '<软件根目录>' -Directory | ForEach-Object {
  Get-ChildItem $_.FullName -Filter *.exe -Depth 2 -File -ErrorAction SilentlyContinue
} | ForEach-Object { $_.VersionInfo | Select-Object FileName, ProductVersion }
```

```bash
# WSL：包数据库 + 语言生态
apt-mark showmanual
npm ls -g --depth=0
uv tool list
ls ~/.local/bin
```

```bash
# 本仓库的实时更新检查（不修改任何东西）
python3 scripts/watchapp.py check --os wsl --scenario company
# Windows 侧用 Windows Python 跑，才能调用 winget：
python.exe scripts\watchapp.py check --os windows --scenario company
```

## 7. 已知盲区

- 只扫了软件根目录，其他盘符的绿色软件与浏览器扩展未扫描。
- 飞书 / Unity Hub / Waves / WPS 只有目录、版本号未注册，未纳入版本对比。
- winget 源可能滞后于厂商官网（例如 VS Code 源显示 1.143，官网已发 1.144）。
- 版本以 2026-11-03 的 `--version` 与 winget 源为准；之后的变化以 `watchapp check` 为准。
