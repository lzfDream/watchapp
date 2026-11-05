---
name: watchapp-software-ops
description: "在 watchapp 仓库中盘点、安装、更新本机软件，并生成更新记录（默认 dry-run、不自动提交）"
---

# watchapp 软件运维

## 何时适用

- 用户要求"装一下 X"、"升级 X"、"看看哪些软件该更新"、"整理这台机器的软件清单"。
- 需要按公司机 / 家用机场景区分软件，或需要生成/复核更新说明。

## 前置

- 工作目录是 watchapp 仓库（含 `catalog/software.toml`、`scripts/watchapp.py`）。
- 先确认场景（`company` / `home`）与平台（`windows` / `wsl` / `macos`）。
  - 当前机器已加域（主机名/域名不写入仓库）= 公司机。
  - 其他机器按 `AGENTS.md` 第 5 节确认。
- Windows 的 winget 检查必须用 Windows Python（`python.exe`），WSL 用 `python3`。
- 不读取、不粘贴 `.env`；不主动读取 `WATCHAPP_PRIVATE_DIRS` 下的目录。具体安装路径由用户提供或留本地。
- 机器目录扫描只走 `scan`，范围由 `.env` 的 `WATCHAPP_ALLOWED_DIRS` 白名单限制；`privacy` 扫描仓库文本。

## 步骤

1. `python3 scripts/watchapp.py validate`；若刚改过数据源，再 `render`；再跑 `privacy` 确认无私有路径泄露。
2. `python3 scripts/watchapp.py list --scenario <场景>` 找到目标；`show <id>` 看策略、状态、命令与备注。
3. 优先确认 portable / 解压即用版本；有则按 `D:\software\<领域>\<软件>` 落地；catalog 只记模板/描述，具体路径留本地；开发链优先放 WSL。
4. 先看策略：`observe` / `hold` 不进入默认更新；`p2` 需显式指定。`stopped`（上游停更）安装需 `--force` 和用户确认。
5. 检查更新：`check --os <平台> --scenario <场景>`（Windows 用 `python.exe`；winget 约 20–60 秒）。
6. 生成计划：`update --all --os <平台> --scenario <场景>`、`install <id>`，或整机补装 `install --all --scenario <场景>`（不含 hold），都不加 `--apply`。把完整命令清单展示给用户。
7. 涉及以下情况必须先得到用户确认，再执行：sudo、卸载、跨大版本、新软件、`--force`、修改 PATH/系统配置。
8. 执行：加 `--apply`。Windows 的手动安装器逐项执行；失败项记录后继续。
9. 验证：运行软件自带 `--version` 或读文件版本信息；必要时重启应用确认可用。不要只看安装器退出码。
10. 更新数据：把对应平台 `latest` 改为实际版本；`render`；若发生实际更新，写 `updates/YYYY-MM-DD.md`（前→后、方式、验证、回滚点、经验）。
11. 卸载：确认后卸载，**从 catalog 删除该条**（不保留已卸载状态），把卸载动作写进 `updates/YYYY-MM-DD.md`。
12. 收尾：`validate` + `render --check` + `privacy`；确认 `git status` 有改动但**未提交**，向用户报告文件清单与未提交状态。

## 检查点

- [ ] 场景与平台已确认，不是默认套用公司机策略。
- [ ] 未读取/回显 `.env`；具体安装路径未进仓库/记录/对话。
- [ ] 机器目录扫描（`scan`）范围与 `.env` 的 `WATCHAPP_ALLOWED_DIRS` 一致。
- [ ] 优先便携版；Windows 路径符合 `D:\software\<领域>\<软件>`；开发链在 WSL。
- [ ] `validate` 通过，`render --check` 无差异，`privacy` 无线索。
- [ ] 未自动更新 `observe` / `hold` 条目；未触碰公司管控软件与系统组件。
- [ ] 未启用 Docker Desktop，未擅自改 PATH，未安装 Visual Studio 实例。
- [ ] 升级前已留回滚点（便携软件 `.bak-<旧版本>`）。
- [ ] 更新后的版本已通过软件自身或文件版本验证。
- [ ] 实际更新已写入 `updates/` 记录。
- [ ] 没有执行 git add/commit/push。

## 成功判据

- 目标软件版本达到预期，且验证命令输出一致。
- 其他软件未被意外改动；公司管控软件保持原状。
- catalog 与生成文档一致（`render --check` 通过）。
- 用户收到"执行了什么 / 结果 / 回滚方式 / 未提交"的简要报告。

## 回滚

- 便携软件：用 `.bak-<旧版本>` 覆盖回去。
- winget：`winget install --id <id> --version <旧版>` 或卸载重装。
- apt：`sudo apt-get install <pkg>=<旧版本>`。
- npm：`npm install -g <pkg>@<旧版本>`。
- uv：`uv tool install <pkg>@<旧版本>`。
- 回滚后同样要验证版本，并在 `updates/` 记录里补一行。
