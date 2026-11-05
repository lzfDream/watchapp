# 家用机基线（草案 · 待采集）

> 状态：**未采集**。本文件是家用机场景的占位与采集指引，不是实际基线。
> 最后更新：2026-11-05
> 家用机软件条目见 [catalog/software.md](../catalog/software.md) 的「家用机」与「共用」两节。

## 1. 已知线索

- 旧清单 `tools-config/software.md` 里有一组 macOS 工具（iTerm2、Keka、Hidden Bar、Maccy、Skim、VMware Fusion、Pixea 等）。
- 2026-11-05 用户把多款 **Windows** 工具纳入家用机（WSL、Windows Terminal、PowerShell、winget、Everything、7-Zip、Snow Shot、PicView、dsh），并把 zsh 纳入家用机 WSL；因此家用机至少承担 Windows 开发/日常用途；是同一台 Windows 还是 Windows + Mac 双机，待确认。
- 家用机的系统版本、已装软件、包管理器均未采集。家用机专属条目（`scenarios = ["home"]`）目前一律为 `status = watch`（关注中）；两台共用条目沿用公司机事实标为 `active`，不代表家用机已安装。

## 2. 采集步骤

在**家用机上**执行，结果人工整理进 `catalog/software.toml`（只读命令，不改软件）。

### macOS

```bash
sw_vers
system_profiler SPHardwareDataType | head -20
brew --version && brew list --versions
ls /Applications
# 如装有 mas（App Store CLI）
mas list
```

### Windows

```powershell
Get-ComputerInfo | Select-Object WindowsProductName, WindowsVersion, OsBuildNumber
winget list
winget upgrade --include-unknown
Get-AppxPackage | Where-Object { -not $_.IsFramework } | Select-Object Name, Version
```

### WSL / Linux

```bash
cat /etc/os-release
apt-mark showmanual
npm ls -g --depth=0
uv tool list
```

## 3. 家用机 profile（草案）

以下条目是"关注/可能使用"，未确认安装。采集后按实际结果改写 `status`、`latest` 与 `manager`。

| 软件 | 平台 | 用途 | 状态 |
|---|---|---|---|
| iTerm2 | macOS | 终端（主题 midnight-in-mojave） | 关注中 |
| Hidden Bar | macOS | 状态栏图标管理 | 关注中 |
| Keka | macOS | 压缩/解压 | 关注中 |
| Homebrew | macOS | 包管理 | 关注中 |
| Skim | macOS | PDF 阅读 | 关注中 |
| Maccy | macOS | 剪贴板历史管理 | 关注中 |
| ITraffic | macOS | 状态栏网速监控 | 关注中 |
| VMware Fusion | macOS | 虚拟机 | 关注中 |
| Pixea | macOS | 图片查看器 | 关注中 |
| IrfanView | Windows | 看图（待确认） | 关注中 |

补充关注项（终端美化、跨平台小工具等）见 [catalog/watchlist.md](../catalog/watchlist.md)。

### 3.1 2026-11-05 纳入的 Windows / WSL 工具

这些条目已改为「公司机 + 家用机」共用；`status` 为公司机侧的在用状态，家用机侧是否已安装待采集确认。

| 软件 | 用途 | 策略 |
|---|---|---|
| App Installer (winget) | Windows 包管理器 | P1 |
| Everything | 快速文件搜索 | P0 |
| 7-Zip | 压缩/解压 | P0 |
| zsh | 默认 shell（WSL） | P0 |
| PowerShell 7 | 默认 shell | P0 |
| Windows Terminal | 主力终端 | P0 |
| WSL | Windows 上的 Linux 开发环境 | P0 |
| dsh | 本地 AI agent harness | P0 |
| Snow Shot | 截图/贴图 | P0 |
| PicView | 看图 | P0 |

## 4. 待确认

1. 家用机是 Windows 还是 macOS？是否同时有 Windows + Mac 两台？
2. 家用机主要用途：开发、游戏、影音、办公，还是混合？
3. 是否与公司机共用同一套开发环境（VS Code / Git / Node / Python / Docker）？
4. 家用机是否加域/受公司管控？（应无）是否需要与公司机完全隔离的软件清单？
5. 是否保留 macOS 专属清单，还是只用跨平台工具？

确认后：

```bash
# 改写 catalog 后重新生成文档并校验
python3 scripts/watchapp.py validate
python3 scripts/watchapp.py render
```

## 5. 边界

- 公司机条目**不要直接复制**到家用机：公司机的飞书、TortoiseSVN、域管控软件等是环境绑定项。
- 家用机采集前，不把任何条目写成 `active`；`watch` 只表示关注。
