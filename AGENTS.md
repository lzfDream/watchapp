# AGENTS.md — watchapp 协作规则

本文件约束在本仓库工作的 agent。用户指令优先于本文件；本文件优先于通用最佳实践。

## 1. 项目是什么

- 收集关注的软件，按场景（公司机 / 家用机）维护。
- 数据源：`catalog/software.toml`；生成物：`catalog/software.md`；记录：`updates/`。
- 服务：`scripts/watchapp.py`（list / show / stats / scan / check / install / update / render / validate / privacy）。
- 机器基线：`machines/company.md`（当前机器）、`machines/home.md`（待采集）。

## 2. 硬性规则（必须遵守）

1. **不自动提交**：不要执行 `git add`、`git commit`、`git push`、打 tag。改动留在工作区，由用户审阅后自行提交。用户明确说"提交/推送"时才例外。
2. **默认 dry-run**：`install` / `update` 不加 `--apply` 只打印命令。执行前把命令清单给用户看；涉及 sudo、卸载、大版本跳变、安装新软件时，等用户确认后再加 `--apply`。
3. **不动公司管控软件与系统组件**：域策略/IT 分发的软件、系统自带组件、未纳入 catalog 的软件，不纳入自动更新；即使 `check` 报可更新也不处理。
4. **Docker 只用 WSL 原生引擎**：不启用、不安装 Docker Desktop，避免抢 `/var/run/docker.sock`。
5. **不要擅自改环境**：Git for Windows 未加入 PATH 是既有选择；不要自动改 PATH、不要重装 Git、不要安装 Visual Studio 实例。
6. **升级前留回滚点**：便携软件先复制 `.bak-<旧版本>`；系统级安装依赖官方卸载/旧版安装包。
7. **必须验证**：安装/更新后运行软件自带版本命令或读文件版本信息，确认真的生效；不能只看"安装器退出码 0"。
8. **记录**：实际执行更新后，在 `updates/YYYY-MM-DD.md` 写前→后、方式、验证、回滚点、经验。只检查不执行时不需要新建记录。
9. **不写敏感信息**：账号、密码、token、公司名、域名、主机名、内网/具体地址一律不写入仓库或记录。机器只写「公司机 / 家用机」，加域机器只写「已加域」，不要写域名、主机名或用户名路径。
10. **卸载不留条目**：卸载后从 `catalog/software.toml` 删除该条，不保留"已卸载"状态；卸载事实写进 `updates/YYYY-MM-DD.md`，由历史记录承担追溯。
11. **便携优先**：软件优先选 portable / zip / 解压即用版本，避免安装器在注册表、AppData、Program Files 到处写文件；只有驱动、系统组件、必须注册的软件才用安装包。
12. **Windows 目录**：便携软件按 `D:\software\<领域>\<软件>` 的模板放置（如游戏类、终端类各占领域目录）。**具体安装路径是隐私数据**：只放本地 `.env` / 本地笔记，不写进 catalog、文档、记录或对话；catalog 只写模板或文字描述。
13. **开发环境用 WSL**：开发链（编译器、运行时、CLI、语言包）放 WSL；Windows 侧只放编辑器、终端、浏览器、办公/系统工具，不要为了"方便"在 Windows 再装一套。
14. **隐私目录、白名单与 .env**：私有安装目录在本地 `.env` 的 `WATCHAPP_PRIVATE_DIRS` 配置；机器目录扫描白名单在 `WATCHAPP_ALLOWED_DIRS` 配置（Windows/WSL 绝对路径）。`scan` 只遍历白名单目录，`privacy` 扫描仓库文本。禁止读取、打印或粘贴 `.env` 内容；不要主动读取私有目录，需要路径时让用户提供。`privacy` 只报位置与类型，不回显值。

## 3. 命令

### WSL / Linux（当前会话默认）

```bash
python3 scripts/watchapp.py validate
python3 scripts/watchapp.py list --scenario company
python3 scripts/watchapp.py show <id>
python3 scripts/watchapp.py check --os wsl --scenario company
python3 scripts/watchapp.py install <id>            # dry-run
python3 scripts/watchapp.py update --all --os wsl   # dry-run
python3 scripts/watchapp.py update --all --os wsl --apply
python3 scripts/watchapp.py render
python3 scripts/watchapp.py privacy             # 敏感信息扫描（必须通过）
python3 scripts/watchapp.py stats               # 统计当前管理的软件
python3 scripts/watchapp.py scan --limit 20     # 按白名单扫描机器目录（只输出名称/计数）
```

配置本地隐私目录（只在本机执行，不要提交 `.env`）：

```bash
cp .env.example .env
# 编辑 .env，设置 WATCHAPP_PRIVATE_DIRS
```

### Windows（winget）

必须用 **Windows 的 Python**（`python.exe`），否则调用不到 winget。从 WSL 调用时用 UNC 路径：

```bash
WIN=$(wslpath -w scripts/watchapp.py)
"/mnt/c/Program Files/PyManager/python.exe" "$WIN" check --os windows --scenario company
"/mnt/c/Program Files/PyManager/python.exe" "$WIN" update --all --os windows   # dry-run
```

`winget` 检查约 20–60 秒，命令超时给足（≥ 180s）。winget 输出可能夹带 `msstore` 源报错，忽略即可。

### macOS（家用机落地后）

`check --os macos` 依赖 `brew outdated --json=v2`；`install/update` 用 brew。

## 4. 工作流

### 查看与检查

1. `list --scenario <company|home>` 看条目、版本、策略、状态。
2. `show <id>` 看单条详情与命令。
3. `check --os <platform> --scenario <scenario>` 拉真实可更新列表；`--json` 便于程序处理。

### 安装

1. 优先确认是否有 portable / 解压即用版本；有就按 `D:\software\<领域>\<软件>` 落地。catalog 只记模板/描述，具体路径由用户本地提供。
2. `install <id>` 打印命令；确认包 ID、scope、来源。
3. 新软件先看 `status`：`stopped` 需 `--force` 且要用户确认。
4. 用户确认后 `install <id> --apply`。
5. 新机器/补装可用 `install --all --scenario <company|home> [--os ...]`（只含 active 且非 hold 的条目，默认 dry-run）；公司管控软件仍走人工/IT。
6. 验证版本；把 `latest` 更新为实际版本；`render`。

### 更新

1. `update --all --os <platform> --scenario <scenario>` 看 P0/P1 清单；默认只含 `check` 实际发现可更新的条目。
2. 需要 P2 时显式加 `--policy p0,p1,p2` 或指定 ID。
3. `observe` / `hold` 默认跳过；用户明确要求时加 `--force`。
4. 逐项或分批 `--apply`；失败项记录后继续，最后汇总。
5. 验证版本，更新 `latest`，`render`，写 `updates/` 记录。

### 新增软件

1. 在 `catalog/software.toml` 增加条目（字段见 `catalog/README.md`）。
2. `validate` → `render`。
3. 同一软件 Windows/WSL 策略不同就拆成两条（policy 是条目级）。
4. 不确定 winget ID 时先 `winget search --id <候选> --exact`，不要猜。

### 家用机采集

按 `machines/home.md` 的只读命令采集；采集前不要把任何家用机条目标为 `active`，保持 `watch`。

## 5. 场景判定

- 当前机器已加域（主机名/域名不写入仓库）= **公司机**。
- 其他机器先确认场景（`hostname`、是否加域、用户说明），不要默认套用公司机策略。
- 公司机与家用机不共享"已安装"事实；`scenarios` 为两台的条目只表示"两台都需要"，不代表版本相同。

## 6. 完成标准

- `python3 scripts/watchapp.py validate` 通过；`render --check` 无差异；`privacy` 无线索。
- 命令已打印或已执行，且执行结果经过版本验证。
- 涉及实际更新时，`updates/` 有对应记录。
- `git status` 显示改动但**未提交**，并在回复里说明改了哪些文件。
