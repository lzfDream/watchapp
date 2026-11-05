# catalog 数据模型

| 文件 | 作用 |
|---|---|
| `software.toml` | **唯一数据源**，手工维护 |
| `software.md` | 由 `scripts/watchapp.py render` 生成，勿手改；生成物不入 git（已在 `.gitignore`） |
| `watchlist.md` | 关注但未安装/未落地的软件，人工维护 |

## 1. 条目字段

```toml
[[software]]
id = "vscode"                 # 必填，kebab-case，全局唯一
name = "Visual Studio Code"   # 必填，展示名
category = "编辑器"            # 必填，用于分组
scenarios = ["company", "home"] # 必填，company / home，至少一个
status = "active"             # 必填，见状态枚举
policy = "p0"                 # 必填，见策略枚举
purpose = "主力编辑器"         # 建议填
docs = ["https://..."]        # 建议填
notes = "..."                 # 可选，条目级说明

# 平台表，至少一个：windows / wsl / macos
[software.windows]
latest = "1.144.0"            # 最近一次记录的版本（不是上游实时版本）
manager = "winget"            # winget / apt / npm / uv / brew / manual
package = "Microsoft.VisualStudioCode" # 单包
# packages = ["a", "b"]       # 多包（apt 常用），与 package 二选一
scope = "user"                # 可选，winget 的 --scope
command = "..."               # manual 必填：人工操作方式/命令
note = "..."                  # 可选，平台级说明
```

## 2. 枚举

### status（描述了"装没装/用不用"）

| 值 | 含义 |
|---|---|
| `active` | 在用 |
| `watch` | 关注中，尚未确认安装（家用机草案常用） |
| `unused` | 不常用 · 停更跟踪 |
| `stopped` | 上游停更 |

> **卸载不留条目**：卸载软件后直接从 `software.toml` 删除该条，不保留"已卸载"状态；
> 卸载事实写进 `updates/YYYY-MM-DD.md`（历史记录），不在当前清单里重复出现。

### policy（描述了"跟不跟版本"）

| 值 | 含义 | 是否进入 `update --all` |
|---|---|---|
| `p0` | 尽快 | 是 |
| `p1` | 正常 | 是 |
| `p2` | 可选 | 否（需 `--policy p0,p1,p2` 或指定 ID） |
| `observe` | 仅观察上游 | 否 |
| `hold` | 不跟进 | 否（指定 ID 还需 `--force`） |

## 3. manager 与命令

| manager | 安装 | 更新 |
|---|---|---|
| `winget` | `winget install --id <package> --exact ...` | `winget upgrade --id <package> --exact ...` |
| `apt` | `sudo apt-get install -y <packages>` | `sudo apt-get install --only-upgrade -y <packages>` |
| `npm` | `npm install -g <package>` | `npm install -g <package>@latest` |
| `uv` | `uv tool install <package>` | `uv tool upgrade <package>` |
| `brew` | `brew install <package>` | `brew upgrade <package>` |
| `manual` | 只打印 `command` / 链接，不自动执行 | 同左 |

`scripts/watchapp.py` 会自动补上 winget 的 `--accept-source-agreements`、`--accept-package-agreements`、`--disable-interactivity` 等参数。

## 4. 新增/修改流程

1. 在 `software.toml` 追加条目；`id` 用英文 kebab-case。
2. 同一软件如果 Windows / WSL 策略不同（例如一个 P1 一个仅观察），**拆成两个条目**（`git`、`git-wsl`），因为 `policy` 是条目级字段。
3. 运行校验与渲染：

   ```bash
   python3 scripts/watchapp.py validate
   python3 scripts/watchapp.py render
   ```

4. 验证命令（不执行）：

   ```bash
   python3 scripts/watchapp.py install <id>          # WSL/Linux
   python.exe scripts\watchapp.py install <id>      # Windows（需 Windows Python）
   ```

5. 实际安装/更新后，把 `latest` 改成新版本，并在 `updates/YYYY-MM-DD.md` 记录。

## 5. 安装偏好（个人习惯）

`software.toml` 顶部有 `[preferences]`，记录跨条目的安装习惯：

```toml
[preferences]
prefer_portable = true
windows_root = 'D:\software'
windows_layout = 'D:\software\<领域>\<软件>'
dev_environment = "wsl"
```

落地方式：

- 有 portable / 解压即用版本时，用 `manager = "manual"`，`command` 只写模板或文字描述（如 `D:\software\<领域>\<软件>`）；**具体安装路径不入库**，本地操作时按实际路径执行。
- 只有安装器可用、或必须注册系统组件时，才用 `winget` / 安装包，并在 `note` 说明原因。
- 开发链（编译器、运行时、CLI）优先放 WSL，不占 Windows 安装位。
- 已有安装保持原路径，不为了统一规范而迁移；新装按上述约定。
- **具体安装路径不入库**：`command` 只写模板或文字描述，实际路径放本地 `.env` / 本地笔记；`privacy` 会拦截私有目录下的具体路径。

## 6. 约定

- `latest` 记录的是**本机确认过的目标版本**，不保证等于上游最新；上游变化由 `check` 实时发现或在更新记录里补充。
- 便携/手动软件用 `manual`，把路径与回滚方式写进 `command` / `note`，不要伪造 winget ID。
- 公司管控软件（如飞书）用 `manual` + `hold`，避免被自动更新；系统组件不纳入 catalog。
- 家用机条目在采集前一律 `status = "watch"`。
