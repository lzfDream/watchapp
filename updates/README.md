# 更新记录

每次对某台机器做软件检查/升级后，在 `updates/` 下新建 `YYYY-MM-DD.md`，记录**做了什么、为什么、结果、怎么回滚**。

## 1. 更新策略

| 策略 | 含义 | 默认动作 |
|---|---|---|
| `p0` | 尽快处理（安全修复、关键开发工具大版本落后） | 进入 `update --all` |
| `p1` | 正常跟进（常用工具、周更软件） | 进入 `update --all` |
| `p2` | 可选（低频工具、大版本有迁移成本） | 需显式指定 ID 或 `--policy p0,p1,p2` |
| `observe` | 仅观察上游（OS、语言运行时） | 不更新；只记录上游变化 |
| `hold` | 不跟进（不常用、公司管控、上游停更） | 不更新；除非用户明确要求 |

状态字段与策略是两件事：`status` 描述"装没装/用不用"，`policy` 描述"跟不跟版本"。

## 2. 记录模板

```markdown
# YYYY-MM-DD 更新记录

- 机器：
- 平台：Windows / WSL / macOS
- 触发：例行检查 / 安全修复 / 用户要求
- 数据源：catalog/software.toml @ <日期>

## 执行

| 软件 | 前 | 后 | 方式 | 结果 |
|---|---|---|---|---|

## 验证

- 版本复核：
- 功能复核：

## 未执行 / 仅观察

| 软件 | 原因 |
|---|---|

## 回滚点

| 路径 | 内容 |
|---|---|

## 经验

- 
```

## 3. 操作规则

1. **先检查再执行**：`check` → 看 P0/P1 → 确认清单；不要直接 `--apply`。
2. **默认 dry-run**：`install` / `update` 不加 `--apply` 只打印命令。
3. **改前留回滚点**：便携软件复制一份 `.bak-<旧版本>`；系统级安装依赖官方安装器的回滚/卸载。
4. **公司管控软件不动**：Zabbix Agent、Office 2019、飞书、OneDrive、域策略分发的软件。
5. **大版本先评估**：比如 TortoiseSVN 1.14 → 1.15、Docker Desktop 跨度 50+ 版本、CC Switch 4.0 有配置迁移成本。
6. **升级后复核版本**：用软件自带 `--version` 或文件版本信息，确认不是"安装器成功但实际未替换"。
7. **记录脱敏**：不写账号、密码、公司名、域名、主机名、内网 IP、具体地址、具体安装路径；机器用「公司机 / 家用机」。
8. **记录但不提交**：本仓库当前约定是不自动 `git commit` / `git push`，由用户自行审阅提交。

## 4. 命令入口

```bash
# 检查（只读）
python3 scripts/watchapp.py check --os wsl --scenario company

# Windows 侧（必须用 Windows Python 才能调用 winget）
python.exe scripts\watchapp.py check --os windows --scenario company

# 生成待执行清单（不执行）
python3 scripts/watchapp.py update --all --os wsl --scenario company

# 执行
python3 scripts/watchapp.py update --all --os wsl --apply
python.exe scripts\watchapp.py update --all --os windows --apply
```

## 5. 历史记录

| 日期 | 机器 | 摘要 |
|---|---|---|
| 2026-11-03 | 公司机 | 首次全量扫描；11 项升级；仅观察 7 项运行时；P2 5 项 |
| 2026-11-03 | 公司机 | 上游版本快照（本机 vs 上游），见 `2026-11-03-radar.md` |
| 2026-11-05 | 公司机 / 家用机 | 清单调整：移除 19 条、家用机新增 9 条、P0 调整 9 条；实际卸载 6 项（Docker Desktop 保留） |
