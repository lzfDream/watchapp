# watchapp

收集关注的软件，按**使用场景**（公司机 / 家用机）整理，并提供安装、更新检查与更新记录。

- 软件目录：`catalog/software.toml`（唯一数据源）→ `catalog/software.md`（自动生成）
- 机器基线：`machines/company.md`、`machines/home.md`
- 更新记录：`updates/`
- 自建容器栈：`stacks/`（navbook + notes，一键启动）
- 服务命令：`scripts/watchapp.py`
- Agent 协作：`AGENTS.md` + `.agents/skills/watchapp-software-ops/SKILL.md`

## 场景

| 场景 | 机器 | 状态 |
|---|---|---|
| 公司机 | Windows 11 25H2 + WSL Ubuntu 24.04（已加域） | 已采集（2026-11-03） |
| 家用机 | 未确认（旧清单偏 macOS） | **待采集**，catalog 中为草案 |

详见 [machines/company.md](machines/company.md)、[machines/home.md](machines/home.md)。

## 目录

```
watchapp/
├── AGENTS.md                  # 项目级 agent 规则
├── catalog/
│   ├── software.toml          # 软件数据源（手工维护）
│   ├── software.md            # 生成物（不入 git，勿手改）
│   ├── watchlist.md           # 关注但未安装
│   └── README.md              # 字段与管理器说明
├── machines/
│   ├── company.md             # 公司机基线
│   └── home.md                # 家用机采集指引（草案）
├── updates/
│   ├── README.md              # 更新策略与记录规范
│   ├── 2026-11-03.md          # 首次集中升级记录
│   └── 2026-11-03-radar.md    # 上游版本快照（本机 vs 上游）
├── scripts/
│   └── watchapp.py            # list / show / stats / scan / check / install / update / render / validate / privacy
├── stacks/                    # 自建容器栈（compose + 起停脚本）
│   ├── navbook/compose.yaml   # 端口 5556；数据在 navbook/data
│   ├── notes/compose.yaml     # 端口 40001；数据在 notes/books
│   ├── up.sh / down.sh / status.sh
│   └── README.md
├── .env.example               # 本地隐私目录模板（.env 已忽略）
└── .agents/skills/watchapp-software-ops/SKILL.md
```

## 快速开始

在 WSL / Linux 上：

```bash
python3 scripts/watchapp.py validate                 # 校验数据
python3 scripts/watchapp.py stats                    # 软件统计
python3 scripts/watchapp.py list --scenario company  # 看清单
python3 scripts/watchapp.py check --os wsl --scenario company
python3 scripts/watchapp.py install vscode           # 只打印命令
python3 scripts/watchapp.py install --all --scenario company --os wsl  # 场景补装清单（dry-run）
python3 scripts/watchapp.py update --all --os wsl    # 只打印 p0/p1 更新命令
python3 scripts/watchapp.py privacy                   # 敏感信息扫描
python3 scripts/watchapp.py scan                      # 按白名单扫描机器目录

./stacks/up.sh                                       # 启动自建容器栈（navbook + notes）
./stacks/status.sh                                   # 查看容器栈状态
```

在 Windows 上（必须用 Windows Python，才能调用 winget）：

```powershell
python.exe scripts\watchapp.py check --os windows --scenario company
python.exe scripts\watchapp.py update --all --os windows   # dry-run
python.exe scripts\watchapp.py update --all --os windows --apply
```

> 默认 **dry-run**：不加 `--apply` 只打印命令。`--apply` 才会执行。
> `update --all` 只纳入 `check` 实际发现可更新的 P0/P1 条目；`observe` / `hold` 默认跳过。

## 工作流

1. **采集/新增**：在 `catalog/software.toml` 加条目（字段见 [catalog/README.md](catalog/README.md)）。
2. **校验与生成**：`validate` → `render`。
3. **检查**：`check` 拉取 winget / apt / npm 的真实可更新列表。
4. **预演**：`install <id>` 或 `update --all` 看命令；确认影响范围。
5. **执行**：加 `--apply`；公司管控软件、`hold` 条目不动。
6. **验证**：软件内版本 / 文件版本复核。
7. **记录**：在 `updates/YYYY-MM-DD.md` 写前→后、方式、验证、回滚点、经验。

## 个人安装习惯

- **便携优先**：优先选 portable / zip / 解压即用版本，避免安装器往注册表、AppData、Program Files 到处写文件；只有驱动、系统组件、必须注册的软件才用安装包。
- **Windows 目录**：新装统一放在 `D:\software\<领域>\<软件>`（如游戏类、终端类各占一个领域目录）；已有安装保持原路径、不强制迁移。具体安装路径属于隐私数据，只放本地 `.env` 或本地笔记，不写进 catalog / 文档 / 对话。
- **开发环境在 WSL**：apt / npm / uv 为主；Windows 侧只放编辑器、终端、浏览器、办公与系统工具，不在 Windows 再装一套开发链。
- 便携软件升级先留 `.bak-<旧版本>`；配置尽量留在软件目录内，便于整目录迁移。

## 约定

- **不自动提交**：本仓库当前不执行 `git commit` / `git push`，改动留给用户审阅后自行提交。
- **先检查后执行**：任何安装/更新先 dry-run；大版本、卸载、删备份需用户确认。
- **公司机边界**：公司维护的软件与系统组件（含域策略分发的）不擅自升级；Docker 只用 WSL 原生引擎，不启用 Docker Desktop。
- **回滚点**：便携软件升级前保留 `.bak-<旧版本>`。
- **状态与策略分离**：`status` 表示装没装/用不用，`policy` 表示跟不跟版本，两者都在 catalog 里。

## 隐私与脱敏

具体安装路径、账号、密码、token、公司名、域名、主机名、内网 IP、具体地址、用户名路径都属于隐私数据，不进仓库、不进记录、不进对话。

- **安装路径**：catalog / 文档只写 `D:\software\<领域>\<软件>` 模板；实际路径只放本地 `.env` 或本地笔记。
- **机器**：只写「公司机 / 家用机」；加域机器只写「已加域」。
- **软件来源**：只写官方包 ID / 官方下载地址，不写内部源、内部地址或凭据。
- **本地隐私目录**：复制 `.env.example` 为 `.env`，在 `WATCHAPP_PRIVATE_DIRS` 中配置（分号/逗号分隔）；`.env` 已被 `.gitignore` 忽略。
- **扫描白名单**：`WATCHAPP_ALLOWED_DIRS` 配置允许扫描的机器目录（Windows/WSL 绝对路径，分号分隔；Windows 盘符在 WSL 下自动转 `/mnt/<盘>`）。`scan` 只遍历这些目录，`privacy` 仍扫描仓库文本；留空则不扫描机器目录。
- **扫描**：`python3 scripts/watchapp.py privacy` 会读取 `.env` 中的私有目录并扫描仓库（邮箱 / 私有 IP / 内部域名 / 用户目录 / 凭据 / 私有路径），只报文件与行号、不回显值；`.env` 自身不参与扫描。`.env` 未被忽略时会直接报错。
- **Agent 约束**：不读取、不粘贴 `.env` 内容，也不主动读取 `WATCHAPP_PRIVATE_DIRS` 下的目录；需要路径时由用户提供。

```bash
cp .env.example .env      # 然后在本机编辑 .env（不要提交、不要贴进对话）
python3 scripts/watchapp.py privacy
```

## 数据来源

- 2026-11-04 用 `watchapp check` 对公司机做了实时复核（WSL 与 Windows 两侧）。
