#!/usr/bin/env python3
"""watchapp - 软件目录、安装与更新服务。

数据源: catalog/software.toml
生成物: catalog/software.md（勿手改，用 render 重新生成）

用法示例:
  python scripts/watchapp.py list --scenario company
  python scripts/watchapp.py check --scenario company
  python scripts/watchapp.py install vscode          # 只打印命令
  python scripts/watchapp.py install vscode --apply  # 真正执行
  python scripts/watchapp.py update --all            # 只打印 p0/p1 的更新命令
  python scripts/watchapp.py render
"""

from __future__ import annotations

import argparse
import json
import platform
import re
import shutil
import subprocess
import sys
import tomllib
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CATALOG_PATH = ROOT / "catalog" / "software.toml"
GENERATED_PATH = ROOT / "catalog" / "software.md"

STATUS_LABEL = {
    "active": "在用",
    "watch": "关注中",
    "unused": "不常用",
    "stopped": "上游停更",
}
POLICY_LABEL = {
    "p0": "P0 尽快",
    "p1": "P1 正常",
    "p2": "P2 可选",
    "observe": "仅观察",
    "hold": "不跟进",
}
POLICY_ORDER = {"p0": 0, "p1": 1, "p2": 2, "observe": 3, "hold": 4}
MANAGERS = {"winget", "apt", "npm", "uv", "brew", "manual"}
PLATFORMS = ("windows", "wsl", "macos")
SCENARIOS = ("company", "home")
SCENARIO_LABEL = {"company": "公司机", "home": "家用机"}
SCENARIO_SHORT = {"company": "公司", "home": "家用"}
PLATFORM_LABEL = {"windows": "Windows", "wsl": "WSL", "macos": "macOS"}
CATEGORY_ORDER = [
    "系统与终端",
    "编辑器",
    "开发工具",
    "语言运行时",
    "容器",
    "数据库与 API",
    "压缩",
    "截图与看图",
    "文件与磁盘",
    "AI 工具",
    "办公与日常",
    "监控与调试",
    "命令行工具",
    "家用机 · macOS",
    "家用机 · Windows",
]


def load_catalog() -> dict:
    with CATALOG_PATH.open("rb") as f:
        return tomllib.load(f)


def resolve_os(value: str) -> str:
    if value != "auto":
        return value
    system = platform.system()
    if system == "Windows":
        return "windows"
    if system == "Darwin":
        return "macos"
    return "wsl"


def run(cmd: list[str], timeout: int = 180) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )


def platform_table(entry: dict, os_name: str) -> dict | None:
    table = entry.get(os_name)
    return table if isinstance(table, dict) else None


def manager_of(table: dict) -> str:
    return str(table.get("manager", ""))


def package_names(table: dict) -> list[str]:
    packages = table.get("packages")
    if isinstance(packages, list) and packages:
        return [str(p) for p in packages]
    package = table.get("package")
    return [str(package)] if package else []


def build_commands(table: dict, action: str) -> list[str] | None:
    """返回可执行命令；manual 返回 None。"""
    manager = manager_of(table)
    if manager == "winget":
        package = table.get("package")
        if not package:
            return None
        verb = "install" if action == "install" else "upgrade"
        cmd = [
            "winget",
            verb,
            "--id",
            str(package),
            "--exact",
            "--accept-source-agreements",
            "--accept-package-agreements",
            "--disable-interactivity",
        ]
        if action == "install" and table.get("scope"):
            cmd += ["--scope", str(table["scope"])]
        return cmd
    if manager == "apt":
        packages = package_names(table)
        if not packages:
            return None
        if action == "install":
            return ["sudo", "apt-get", "install", "-y", *packages]
        return ["sudo", "apt-get", "install", "--only-upgrade", "-y", *packages]
    if manager == "npm":
        package = table.get("package")
        if not package:
            return None
        return ["npm", "install", "-g", str(package) if action == "install" else f"{package}@latest"]
    if manager == "uv":
        package = table.get("package")
        if not package:
            return None
        verb = "install" if action == "install" else "upgrade"
        return ["uv", "tool", verb, str(package)]
    if manager == "brew":
        package = table.get("package")
        if not package:
            return None
        return ["brew", "install" if action == "install" else "upgrade", str(package)]
    return None


def command_text(table: dict, action: str) -> str:
    cmd = build_commands(table, action)
    if cmd:
        return " ".join(cmd)
    if action == "install":
        return str(table.get("command") or "（手动安装，见说明）")
    return str(table.get("command") or "（手动更新，见说明）")


def entry_matches(entry: dict, args) -> bool:
    if args.scenario and args.scenario not in entry.get("scenarios", []):
        return False
    if getattr(args, "status", None) and entry.get("status") not in args.status:
        return False
    if getattr(args, "policy", None) and entry.get("policy") not in args.policy:
        return False
    if getattr(args, "os", None) and getattr(args, "os") not in ("auto",):
        if platform_table(entry, args.os) is None:
            return False
    return True


def entry_versions(entry: dict) -> str:
    parts = []
    for name in PLATFORMS:
        table = platform_table(entry, name)
        if table and table.get("latest"):
            parts.append(f"{PLATFORM_LABEL[name]} {table['latest']}")
    return "；".join(parts) if parts else "—"


def display_width(text: str) -> int:
    """终端显示宽度：CJK 宽字符按 2 列计算。"""
    total = 0
    for ch in str(text):
        if unicodedata.combining(ch):
            continue
        total += 2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1
    return total


def truncate_display(text: str, width: int) -> str:
    """按显示宽度截断，超出部分用 ... 表示。"""
    text = str(text)
    if display_width(text) <= width:
        return text
    if width <= 3:
        return "." * width
    target = width - 3
    kept: list[str] = []
    used = 0
    for ch in text:
        w = 2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1
        if used + w > target:
            break
        kept.append(ch)
        used += w
    return "".join(kept) + "..."


def pad_display(text: str, width: int) -> str:
    return str(text) + " " * max(0, width - display_width(text))


def print_table(headers: list[str], rows: list[list[str]], widths: list[int | None] | None = None) -> None:
    resolved: list[int] = []
    for i, header in enumerate(headers):
        auto = max([display_width(header)] + [display_width(row[i]) for row in rows])
        fixed = widths[i] if widths else None
        resolved.append(auto if fixed is None else fixed)
    print("  ".join(pad_display(h, resolved[i]) for i, h in enumerate(headers)))
    print("  ".join("-" * w for w in resolved))
    for row in rows:
        print("  ".join(pad_display(cell, resolved[i]) for i, cell in enumerate(row)))


# ---------------------------------------------------------------------------
# list / show
# ---------------------------------------------------------------------------


def cmd_list(args) -> int:
    catalog = load_catalog()
    entries = [e for e in catalog["software"] if entry_matches(e, args)]
    entries.sort(key=lambda e: (POLICY_ORDER.get(e["policy"], 9), e["id"]))
    if args.json:
        print(json.dumps(entries, ensure_ascii=False, indent=2))
        return 0
    name_width, purpose_width, version_width = 18, 30, 30
    rows = []
    for entry in entries:
        rows.append(
            [
                truncate_display(entry["name"], name_width),
                truncate_display(entry.get("purpose", "—"), purpose_width),
                "/".join(SCENARIO_SHORT.get(s, s) for s in entry["scenarios"]),
                truncate_display(entry_versions(entry), version_width),
                POLICY_LABEL.get(entry["policy"], entry["policy"]),
                STATUS_LABEL.get(entry["status"], entry["status"]),
            ]
        )
    print_table(
        ["名称", "说明", "场景", "版本", "策略", "状态"],
        rows,
        widths=[name_width, purpose_width, None, version_width, None, None],
    )
    print(f"\n共 {len(entries)} 条。")
    return 0


def cmd_show(args) -> int:
    catalog = load_catalog()
    entry = next((e for e in catalog["software"] if e["id"] == args.id), None)
    if entry is None:
        print(f"找不到条目: {args.id}", file=sys.stderr)
        return 1
    print(f"{entry['name']} ({entry['id']})")
    print(f"  类别: {entry['category']}")
    print(f"  场景: {', '.join(SCENARIO_LABEL.get(s, s) for s in entry['scenarios'])}")
    print(f"  用途: {entry.get('purpose', '—')}")
    print(f"  状态: {STATUS_LABEL.get(entry['status'], entry['status'])}")
    print(f"  策略: {POLICY_LABEL.get(entry['policy'], entry['policy'])}")
    if entry.get("docs"):
        print(f"  文档: {', '.join(entry['docs'])}")
    for os_name in PLATFORMS:
        table = platform_table(entry, os_name)
        if not table:
            continue
        print(f"  [{PLATFORM_LABEL[os_name]}] 版本 {table.get('latest', '—')} / {manager_of(table)}")
        if table.get("note"):
            print(f"    备注: {table['note']}")
        if manager_of(table) == "manual":
            print(f"    安装: {table.get('command', '—')}")
        else:
            print(f"    安装: {command_text(table, 'install')}")
            print(f"    更新: {command_text(table, 'update')}")
    if entry.get("notes"):
        print(f"  说明: {entry['notes']}")
    return 0


# ---------------------------------------------------------------------------
# check
# ---------------------------------------------------------------------------


def parse_winget_upgrades(text: str) -> dict[str, tuple[str, str]]:
    """解析 winget 表格。

    不能按“2 个以上空格”切分（单元格刚好填满列宽时只有 1 个空格），
    也不能按字符下标切片（中文名为双宽字符，winget 按显示宽度补空格）。
    做法：以表头 Id 列位置为锚点，找最近的“含点号 token”作为包 ID，
    再把其后的 token 从右往左解析为 Source / Available / Version。
    """
    lines = text.splitlines()
    header = next(
        (line for line in lines if "Version" in line and "Available" in line and line.lstrip().startswith("Name")),
        None,
    )
    if header is None:
        return {}
    id_column = header.find("Id")
    if id_column < 0:
        return {}

    result: dict[str, tuple[str, str]] = {}
    for line in lines:
        if not line.strip() or line.startswith("-") or line.lstrip().startswith("Name"):
            continue
        if "upgrades available" in line.lower():
            continue
        best = None
        for match in re.finditer(r"\S+", line):
            token = match.group()
            if "." not in token:
                continue
            distance = abs(match.start() - id_column)
            if distance > 20:
                continue
            if best is None or distance < best[0]:
                best = (distance, match)
        if best is None:
            continue
        match = best[1]
        tail = [m.group() for m in re.finditer(r"\S+", line[match.end():])]
        if len(tail) < 3:
            continue
        source = tail[-1]
        available = tail[-2]
        version = " ".join(tail[:-2])
        result[match.group()] = (version, available)
    return result


def parse_apt_upgrades(text: str) -> dict[str, tuple[str, str]]:
    result: dict[str, tuple[str, str]] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if "/" not in line or line.startswith("Listing"):
            continue
        left, _, rest = line.partition(" ")
        package = left.split("/")[0].split(":")[0]
        version = rest.split()[0] if rest.split() else "?"
        found = re.search(r"\[upgradable from: ([^\]]+)\]", line)
        current = found.group(1) if found else "?"
        result[package] = (current, version)
    return result


def parse_npm_outdated(text: str) -> dict[str, tuple[str, str]]:
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return {}
    result = {}
    for package, info in data.items():
        if isinstance(info, dict):
            result[package] = (
                str(info.get("current", "?")),
                str(info.get("latest", info.get("wanted", "?"))),
            )
    return result


def gather_available(os_name: str) -> tuple[dict[str, tuple[str, str]], list[str]]:
    """收集当前平台各包管理器报告的可更新包。"""
    available: dict[str, tuple[str, str]] = {}
    managers: list[str] = []

    if os_name == "windows":
        if shutil.which("winget"):
            proc = run(["winget", "upgrade", "--include-unknown", "--disable-interactivity"], timeout=240)
            available = parse_winget_upgrades(proc.stdout)
            managers.append("winget")
    elif os_name == "wsl":
        if shutil.which("apt"):
            proc = run(["apt", "list", "--upgradable"], timeout=120)
            available.update(parse_apt_upgrades(proc.stdout))
            managers.append("apt")
        if shutil.which("npm"):
            proc = run(["npm", "outdated", "-g", "--json"], timeout=120)
            available.update(parse_npm_outdated(proc.stdout))
            managers.append("npm")
    elif os_name == "macos":
        if shutil.which("brew"):
            proc = run(["brew", "outdated", "--json=v2"], timeout=120)
            try:
                data = json.loads(proc.stdout)
                for formula in data.get("formulae", []):
                    available[formula["name"]] = (
                        ", ".join(formula.get("installed_versions", ["?"])),
                        formula["current_version"],
                    )
                for cask in data.get("casks", []):
                    available[cask["name"]] = (
                        ", ".join(cask.get("installed_versions", ["?"])),
                        cask["current_version"],
                    )
                managers.append("brew")
            except (json.JSONDecodeError, KeyError):
                pass
    return available, managers


def cmd_check(args) -> int:
    catalog = load_catalog()
    os_name = resolve_os(args.os)
    available, managers_checked = gather_available(os_name)
    if not managers_checked:
        print(f"平台 {PLATFORM_LABEL[os_name]} 上没有可用的包管理器。", file=sys.stderr)
        return 1

    details = []
    skipped_manual = 0
    checked_count = 0
    for entry in catalog["software"]:
        if not entry_matches(entry, args):
            continue
        table = platform_table(entry, os_name)
        if not table:
            continue
        manager = manager_of(table)
        if manager == "manual":
            skipped_manual += 1
            continue
        checked_count += 1
        hit = next((available[pkg] for pkg in package_names(table) if pkg in available), None)
        if hit is None:
            continue
        current, latest = hit
        details.append(
            {
                "id": entry["id"],
                "name": entry["name"],
                "manager": manager,
                "current": current,
                "available": latest,
                "policy": entry["policy"],
                "scenarios": entry["scenarios"],
            }
        )

    details.sort(key=lambda d: (POLICY_ORDER.get(d["policy"], 9), d["id"]))

    if args.json:
        print(
            json.dumps(
                {
                    "os": os_name,
                    "managers": managers_checked,
                    "updates": details,
                    "checked_entries": checked_count,
                    "skipped_manual": skipped_manual,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    print(f"平台: {PLATFORM_LABEL[os_name]} | 检查方式: {', '.join(managers_checked)}")
    if not details:
        print("没有发现可更新的条目（或对应包未安装）。")
    else:
        rows = [
            [
                d["id"],
                d["name"],
                d["current"],
                d["available"],
                POLICY_LABEL.get(d["policy"], d["policy"]),
                "/".join(SCENARIO_LABEL.get(s, s) for s in d["scenarios"]),
            ]
            for d in details
        ]
        print_table(["ID", "名称", "当前", "可更新", "策略", "场景"], rows)
        p0p1 = [d for d in details if d["policy"] in ("p0", "p1")]
        print(f"\n共 {len(details)} 项可更新；其中 P0/P1 {len(p0p1)} 项。")
    print(f"已检查 {checked_count} 个自动管理条目；{skipped_manual} 个手动条目未纳入自动检查。")
    print("提示: 仅观察/不跟进条目默认不进入 update --all。")
    return 0


# ---------------------------------------------------------------------------
# install / update
# ---------------------------------------------------------------------------


def find_entry(catalog: dict, entry_id: str) -> dict:
    entry = next((e for e in catalog["software"] if e["id"] == entry_id), None)
    if entry is None:
        raise SystemExit(f"找不到条目: {entry_id}")
    return entry


def apply_command(cmd: list[str]) -> int:
    print(f"  $ {' '.join(cmd)}")
    proc = subprocess.run(cmd)
    if proc.returncode != 0:
        print(f"  失败，退出码 {proc.returncode}", file=sys.stderr)
    return proc.returncode


def cmd_install(args) -> int:
    catalog = load_catalog()
    os_name = resolve_os(args.os)

    if args.all:
        if not args.scenario:
            print("install --all 需要指定 --scenario company|home。", file=sys.stderr)
            return 1
        targets = []
        for entry in catalog["software"]:
            if args.scenario not in entry["scenarios"]:
                continue
            if entry["status"] != "active":
                continue
            if entry["policy"] == "hold":
                continue
            table = platform_table(entry, os_name)
            if table:
                targets.append((entry, table))
        if not targets:
            print(f"场景 {SCENARIO_LABEL[args.scenario]} 在 {PLATFORM_LABEL[os_name]} 上没有可安装条目。")
            return 0
        failures = 0
        for entry, table in targets:
            manager = manager_of(table)
            print(f"- {entry['name']} [{manager}]")
            if manager == "manual":
                print(f"  手动: {table.get('command', '—')}")
                continue
            cmd = build_commands(table, "install")
            if not cmd:
                print("  无法生成安装命令，跳过", file=sys.stderr)
                failures += 1
                continue
            if args.apply:
                failures += 1 if apply_command(cmd) != 0 else 0
            else:
                print(f"  $ {' '.join(cmd)}")
        if args.apply:
            print(f"\n执行完成；失败 {failures} 项。")
        else:
            print(f"\n共 {len(targets)} 项；未执行（加 --apply 执行）。")
        return 1 if failures else 0

    entry = find_entry(catalog, args.id)
    table = platform_table(entry, os_name)
    if table is None:
        print(f"{entry['name']} 没有 {PLATFORM_LABEL[os_name]} 平台的安装信息。", file=sys.stderr)
        return 1
    print(f"{entry['name']} ({entry['id']}) · {STATUS_LABEL.get(entry['status'], entry['status'])} · {POLICY_LABEL.get(entry['policy'], entry['policy'])}")
    if entry["status"] == "stopped" and not args.force:
        print(f"警告: 该条目状态为「{STATUS_LABEL.get(entry['status'])}」，如确需安装请加 --force。", file=sys.stderr)
        return 2
    manager = manager_of(table)
    if manager == "manual":
        print(f"  手动方式: {table.get('command', '—')}")
        if table.get("note"):
            print(f"  说明: {table['note']}")
        if args.apply:
            print("  手动条目不会自动执行。", file=sys.stderr)
            return 1
        return 0
    cmd = build_commands(table, "install")
    if not cmd:
        print("  无法生成安装命令。", file=sys.stderr)
        return 1
    print(f"  安装命令: {' '.join(cmd)}")
    if not args.apply:
        print("  （未执行；加 --apply 执行）")
        return 0
    return apply_command(cmd)


def select_for_update(
    catalog: dict, args, os_name: str, available: dict[str, tuple[str, str]]
) -> list[tuple[dict, dict]]:
    selected = []
    allowed_policies = set(args.policy.split(",")) if args.policy else {"p0", "p1"}
    for entry in catalog["software"]:
        if args.scenario and args.scenario not in entry["scenarios"]:
            continue
        if entry["status"] in ("stopped", "watch", "unused"):
            continue
        if entry["policy"] not in allowed_policies:
            continue
        table = platform_table(entry, os_name)
        if not table or manager_of(table) == "manual":
            continue
        if not any(pkg in available for pkg in package_names(table)):
            continue
        selected.append((entry, table))
    return selected


def cmd_update(args) -> int:
    catalog = load_catalog()
    os_name = resolve_os(args.os)
    if args.ids:
        targets = []
        for entry_id in args.ids:
            entry = find_entry(catalog, entry_id)
            table = platform_table(entry, os_name)
            if table is None:
                print(f"{entry['name']} 没有 {PLATFORM_LABEL[os_name]} 平台的更新信息。", file=sys.stderr)
                return 1
            if entry["policy"] in ("hold", "observe") and not args.force:
                print(
                    f"{entry['name']} 的策略是「{POLICY_LABEL[entry['policy']]}」，如确需更新请加 --force。",
                    file=sys.stderr,
                )
                return 2
            targets.append((entry, table))
    else:
        if not args.all:
            print("请指定条目 ID，或用 --all 更新全部 P0/P1。", file=sys.stderr)
            return 1
        available, managers_checked = gather_available(os_name)
        if not managers_checked:
            print(f"平台 {PLATFORM_LABEL[os_name]} 上没有可用的包管理器。", file=sys.stderr)
            return 1
        targets = select_for_update(catalog, args, os_name, available)

    if not targets:
        print(f"没有符合条件的可更新条目（平台 {PLATFORM_LABEL[os_name]}）。")
        return 0

    failures = 0
    for entry, table in targets:
        manager = manager_of(table)
        if manager == "manual":
            print(f"- {entry['name']}: 手动更新 → {table.get('command', '—')}")
            continue
        cmd = build_commands(table, "update")
        if not cmd:
            print(f"- {entry['name']}: 无法生成更新命令，跳过", file=sys.stderr)
            failures += 1
            continue
        print(f"- {entry['name']} [{manager}]")
        if args.apply:
            failures += 1 if apply_command(cmd) != 0 else 0
        else:
            print(f"  $ {' '.join(cmd)}")
    if not args.apply:
        print(f"\n共 {len(targets)} 项；未执行（加 --apply 执行）。")
    else:
        print(f"\n执行完成；失败 {failures} 项。")
    return 1 if failures else 0


# ---------------------------------------------------------------------------
# render / validate
# ---------------------------------------------------------------------------


def md_cell(text: str) -> str:
    return str(text).replace("|", "\\|").replace("\n", " ")


def render_commands(table: dict) -> tuple[str, str]:
    """表格里用短命令，实际执行由 build_commands 补全静默/接受协议等参数。"""
    manager = manager_of(table)
    packages = package_names(table)
    package = packages[0] if packages else ""
    if manager == "winget":
        return f"`winget install --id {package}`", f"`winget upgrade --id {package}`"
    if manager == "apt":
        joined = " ".join(packages)
        return f"`sudo apt install -y {joined}`", f"`sudo apt install --only-upgrade -y {joined}`"
    if manager == "npm":
        return f"`npm i -g {package}`", f"`npm i -g {package}@latest`"
    if manager == "uv":
        return f"`uv tool install {package}`", f"`uv tool upgrade {package}`"
    if manager == "brew":
        return f"`brew install {package}`", f"`brew upgrade {package}`"
    return str(table.get("command", "—")), "—"


def render_entry_row(entry: dict, table: dict) -> list[str]:
    install, update = render_commands(table)
    return [
        md_cell(entry["category"]),
        md_cell(entry["name"]),
        md_cell(entry.get("purpose", "—")),
        md_cell(table.get("latest", "—")),
        md_cell(POLICY_LABEL.get(entry["policy"], entry["policy"])),
        md_cell(STATUS_LABEL.get(entry["status"], entry["status"])),
        md_cell(install),
        md_cell(update),
    ]


def render_section(title: str, entries: list[dict]) -> list[str]:
    platforms = [p for p in PLATFORMS if any(platform_table(e, p) for e in entries)]
    if not platforms:
        return []
    lines = [f"## {title}", ""]
    for os_key in platforms:
        subset = [e for e in entries if platform_table(e, os_key)]
        if not subset:
            continue
        subset.sort(key=lambda e: (CATEGORY_ORDER.index(e["category"]) if e["category"] in CATEGORY_ORDER else 99, e["name"]))
        lines.append(f"### {PLATFORM_LABEL[os_key]}")
        lines.append("")
        lines.append("| 类别 | 软件 | 用途 | 版本 | 策略 | 状态 | 安装 | 更新 |")
        lines.append("|---|---|---|---|---|---|---|---|")
        for entry in subset:
            lines.append("| " + " | ".join(render_entry_row(entry, platform_table(entry, os_key))) + " |")
        lines.append("")
    return lines


def build_markdown(catalog: dict) -> str:
    entries = catalog["software"]
    shared = [e for e in entries if set(e["scenarios"]) == set(SCENARIOS)]
    company_only = [e for e in entries if e["scenarios"] == ["company"]]
    home_only = [e for e in entries if e["scenarios"] == ["home"]]

    lines = [
        "# 软件清单",
        "",
        "> 本文件由 `scripts/watchapp.py render` 从 [`catalog/software.toml`](software.toml) 生成，请勿手改。",
        f"> 数据更新：{catalog.get('updated', '—')}；来源：{catalog.get('source', '—')}",
        "",
        "> 安装偏好：便携优先；Windows 目标 `" + str(catalog.get("preferences", {}).get("windows_layout", "D:\\software\\<领域>\\<软件>")) + "`；开发环境以 WSL 为主。",
        "",
        "状态：" + " · ".join(f"{k} = {v}" for k, v in STATUS_LABEL.items()),
        "",
        "策略：" + " · ".join(f"{k} = {v}" for k, v in POLICY_LABEL.items()),
        "",
    ]
    lines += render_section("共用（公司机 + 家用机）", shared)
    lines += render_section("公司机", company_only)
    lines += render_section("家用机", home_only)
    lines.append("## 说明")
    lines.append("")
    lines.append("- 「安装」「更新」列是当前平台上的推荐命令；进入 `scripts/watchapp.py` 执行时还会补上静默/接受协议等参数。")
    lines.append("- 手动条目（`manager = manual`）不会自动执行，只给出来源与操作方式。")
    lines.append("- 家用机条目为草案（`status = watch`），等家用机采集后改为实际状态。")
    lines.append("")
    return "\n".join(lines)


def cmd_render(args) -> int:
    catalog = load_catalog()
    content = build_markdown(catalog)
    if args.check:
        if not GENERATED_PATH.exists():
            print("catalog/software.md 未生成（生成物不入 git）；需要时运行: python scripts/watchapp.py render")
            return 0
        existing = GENERATED_PATH.read_text(encoding="utf-8")
        if existing != content:
            print("catalog/software.md 与数据源不一致，请运行: python scripts/watchapp.py render", file=sys.stderr)
            return 1
        print("catalog/software.md 已是最新。")
        return 0
    GENERATED_PATH.write_text(content, encoding="utf-8", newline="\n")
    print(f"已生成 {GENERATED_PATH.relative_to(ROOT)}")
    return 0


PRIVACY_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("email", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")),
    ("private-ip", re.compile(r"\b(?:10(?:\.\d{1,3}){3}|192\.168(?:\.\d{1,3}){2}|172\.(?:1[6-9]|2\d|3[01])(?:\.\d{1,3}){2})\b")),
    ("internal-domain", re.compile(r"\b[A-Za-z0-9-]+\.(?:local|internal|corp|lan)\b")),
    ("windows-user-path", re.compile(r'[A-Za-z]:\\Users\\[^\\\s"\']+')),
    ("unix-home-path", re.compile(r"/(?:home|Users)/[A-Za-z0-9._-]+")),
    ("credential", re.compile(r'(?i)\b(?:password|passwd|pwd|secret|token|api[_-]?key)\b\s*[:=]\s*["\'][^"\']{4,}["\']')),
    ("credential-cn", re.compile(r"(?:账号|帐号|密码|口令|密钥)\s*[:：]\s*\S+")),
]
PRIVACY_TEXT_SUFFIXES = {".md", ".toml", ".py", ".ps1", ".sh", ".json", ".yaml", ".yml", ".txt"}
PRIVACY_SKIP = {"git@github.com", "env.local"}


def load_dotenv(path: Path) -> dict[str, str]:
    """读取 .env（仅键值；不打印、不回显内容）。"""
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError):
        return values
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        values[key.strip()] = val.strip().strip('"').strip("'")
    return values


def private_roots(env: dict[str, str]) -> list[str]:
    """WATCHAPP_PRIVATE_DIRS 支持分号/逗号/换行分隔；也接受 WATCHAPP_PRIVATE_PATHS 别名。"""
    raw = env.get("WATCHAPP_PRIVATE_DIRS") or env.get("WATCHAPP_PRIVATE_PATHS") or ""
    return [part.strip() for part in re.split(r"[;,\n]", raw) if part.strip()]


def scan_roots(env: dict[str, str]) -> tuple[list[Path], int, int]:
    """WATCHAPP_ALLOWED_DIRS：允许扫描的机器目录（Windows/WSL 绝对路径）。

    返回 (存在的根, 不存在的个数, 无效条目数)。留空表示未配置白名单。
    Windows 盘符路径在 WSL 下自动转成 /mnt/<drive>/...；~ 会展开。
    """
    raw = env.get("WATCHAPP_ALLOWED_DIRS") or env.get("WATCHAPP_ALLOWED_PATHS") or ""
    if not raw.strip():
        return [], 0, 0
    roots: list[Path] = []
    missing = 0
    invalid = 0
    for part in re.split(r"[;,\n]", raw):
        part = part.strip()
        if not part:
            continue
        win = re.match(r"^([A-Za-z]):[\\/](.*)$", part)
        if win and platform.system() != "Windows":
            path = Path(f"/mnt/{win.group(1).lower()}/{win.group(2).replace(chr(92), '/')}")
        else:
            path = Path(part).expanduser()
        if not path.is_absolute():
            invalid += 1
            continue
        if path.exists():
            roots.append(path)
        else:
            missing += 1
    return roots, missing, invalid


def privacy_patterns(roots: list[str]) -> list[tuple[str, re.Pattern[str]]]:
    patterns = list(PRIVACY_PATTERNS)
    for root in roots:
        normalized = root.replace("/", "\\").rstrip("\\")
        if not normalized:
            continue
        # 只匹配根目录下的具体路径；`<领域>` / `%VAR%` / `*` 等模板不算泄露。
        patterns.append(
            (
                "private-path",
                re.compile(re.escape(normalized) + r'[\\/](?![<>%{$*])[^\s|`"\'<>]+', re.I),
            )
        )
    return patterns


def cmd_privacy(args) -> int:
    env_file = ROOT / ".env"
    env = load_dotenv(env_file)
    roots = private_roots(env)
    scan_root_list, missing_roots, invalid_roots = scan_roots(env)
    patterns = privacy_patterns(roots)
    hits: list[tuple[str, int, str]] = []
    scanned = 0

    for path in sorted(ROOT.rglob("*")):
        if not path.is_file() or ".git" in path.parts:
            continue
        # .env 是本地隐私配置，本身不参与扫描，也不能被回显。
        if path.name in {".env", ".env.local"}:
            continue
        if path.suffix.lower() not in PRIVACY_TEXT_SUFFIXES and path.name != ".gitignore":
            continue
        if path.stat().st_size > 1_000_000:
            continue
        scanned += 1
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (UnicodeDecodeError, OSError):
            continue
        for lineno, line in enumerate(lines, 1):
            for name, pattern in patterns:
                for match in pattern.finditer(line):
                    if match.group() in PRIVACY_SKIP:
                        continue
                    if name == "private-ip" and not all(
                        0 <= int(part) <= 255 for part in match.group().split(".")
                    ):
                        # 形如 10.0.6.906 的版本号不是合法 IPv4
                        continue
                    if name == "private-path" and any(ch in match.group() for ch in "<>{}*%"):
                        # 模板/变量/通配符不是具体路径
                        continue
                    hits.append((str(path.relative_to(ROOT)), lineno, name))

    # .env 必须被 git 忽略，否则隐私目录会被提交。
    if env_file.exists():
        ignore_file = ROOT / ".gitignore"
        ignored = False
        if ignore_file.is_file():
            entries = {line.strip() for line in ignore_file.read_text(encoding="utf-8").splitlines()}
            ignored = ".env" in entries
        if not ignored:
            hits.append((".env", 0, "env-not-ignored"))

    if args.json:
        print(
            json.dumps(
                {
                    "scanned": scanned,
                    "private_roots_configured": len(roots),
                    "allowed_roots_configured": len(scan_root_list),
                    "allowed_roots_missing": missing_roots,
                    "allowed_roots_invalid": invalid_roots,
                    "hits": [{"file": f, "line": n, "pattern": p} for f, n, p in hits],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 1 if hits else 0

    whitelist = f"{len(scan_root_list)} 个可用根目录" if (scan_root_list or missing_roots or invalid_roots) else "未配置"
    print(f"隐私检查：扫描 {scanned} 个文本文件；私有目录 {len(roots)} 个；扫描白名单 {whitelist}（只报数量，不回显路径）")
    if missing_roots:
        print(f"提示：白名单有 {missing_roots} 个目录不存在。", file=sys.stderr)
    if invalid_roots:
        print(f"警告：白名单有 {invalid_roots} 个条目不是绝对路径，已忽略。", file=sys.stderr)
    if not env_file.exists():
        print("提示：未找到 .env。可复制 .env.example 并配置 WATCHAPP_PRIVATE_DIRS。")
    if not hits:
        print("未发现邮箱、私有 IP、内部域名、用户目录、凭据赋值、私有安装路径等敏感信息。")
        return 0
    print(f"发现 {len(hits)} 处可疑内容（只显示位置与类型，不回显原文）：", file=sys.stderr)
    for filename, lineno, name in hits:
        print(f"  {filename}:{lineno} [{name}]", file=sys.stderr)
    print("请改为通用模板/描述，或把具体路径留在本地 .env / 本地笔记。", file=sys.stderr)
    return 1


def cmd_scan(args) -> int:
    """只扫描 WATCHAPP_ALLOWED_DIRS 白名单中的机器目录；输出名称/计数，不输出完整路径。"""
    env = load_dotenv(ROOT / ".env")
    roots, missing, invalid = scan_roots(env)
    if not roots:
        print("未配置可扫描的白名单目录（WATCHAPP_ALLOWED_DIRS）。", file=sys.stderr)
        return 1

    result = []
    for index, root in enumerate(roots, 1):
        try:
            entries = sorted(root.iterdir(), key=lambda item: item.name.lower())
        except OSError:
            print(f"根 {index}: 无法读取（权限或路径问题）", file=sys.stderr)
            continue
        items = [{"name": entry.name, "type": "dir" if entry.is_dir() else "file"} for entry in entries]
        result.append({"index": index, "count": len(items), "entries": items[: args.limit]})
        print(f"根 {index}: {len(items)} 项")
        for item in items[: args.limit]:
            print(f"  [{'目录' if item['type'] == 'dir' else '文件'}] {item['name']}")
        if len(items) > args.limit:
            print(f"  ... 还有 {len(items) - args.limit} 项")

    if args.json:
        print(json.dumps({"roots": result, "missing": missing, "invalid": invalid}, ensure_ascii=False, indent=2))
    elif missing:
        print(f"另有 {missing} 个白名单目录不存在。")
    return 0


def cmd_stats(args) -> int:
    from collections import Counter

    catalog = load_catalog()
    entries = catalog["software"]
    scenario = Counter()
    status = Counter()
    policy = Counter()
    category = Counter()
    platforms = Counter()
    managers = Counter()
    auto_entries = 0

    for entry in entries:
        names = set(entry["scenarios"])
        if names == set(SCENARIOS):
            scenario["shared"] += 1
        elif names == {"company"}:
            scenario["company"] += 1
        elif names == {"home"}:
            scenario["home"] += 1
        status[entry["status"]] += 1
        policy[entry["policy"]] += 1
        category[entry["category"]] += 1
        has_auto = False
        for os_name in PLATFORMS:
            table = platform_table(entry, os_name)
            if table:
                platforms[os_name] += 1
                managers[manager_of(table)] += 1
                if manager_of(table) != "manual":
                    has_auto = True
        if has_auto:
            auto_entries += 1

    company_side = scenario["company"] + scenario["shared"]
    home_side = scenario["home"] + scenario["shared"]
    data = {
        "total": len(entries),
        "scenarios": {
            "company_only": scenario["company"],
            "home_only": scenario["home"],
            "shared": scenario["shared"],
            "company_side": company_side,
            "home_side": home_side,
        },
        "status": dict(status),
        "policy": dict(policy),
        "category": dict(category),
        "platforms": {k: platforms[k] for k in PLATFORMS},
        "managers": dict(managers),
        "auto_managed_entries": auto_entries,
        "manual_only_entries": len(entries) - auto_entries,
    }

    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return 0

    print(f"软件总数: {len(entries)}")
    print(f"场景: 公司机专属 {scenario['company']} · 家用机专属 {scenario['home']} · 共用 {scenario['shared']}")
    print(f"      公司机侧可见 {company_side} · 家用机侧可见 {home_side}")
    print("状态: " + " · ".join(f"{STATUS_LABEL[k]} {v}" for k, v in status.most_common()))
    print("策略: " + " · ".join(f"{POLICY_LABEL[k]} {v}" for k, v in sorted(policy.items(), key=lambda kv: POLICY_ORDER.get(kv[0], 9))))
    print("平台（条目数）: " + " · ".join(f"{PLATFORM_LABEL[k]} {platforms[k]}" for k in PLATFORMS))
    print("管理方式（平台条目）: " + " · ".join(f"{k} {v}" for k, v in sorted(managers.items(), key=lambda kv: (-kv[1], kv[0]))))
    print(f"可自动管理: {auto_entries} 条 · 纯手动: {len(entries) - auto_entries} 条")
    print("类别: " + " · ".join(f"{k} {v}" for k, v in category.most_common()))
    return 0


def cmd_validate(args) -> int:
    catalog = load_catalog()
    errors: list[str] = []
    seen: set[str] = set()
    for entry in catalog.get("software", []):
        entry_id = entry.get("id")
        if not entry_id:
            errors.append("存在缺少 id 的条目")
            continue
        if entry_id in seen:
            errors.append(f"{entry_id}: id 重复")
        seen.add(entry_id)
        for key in ("name", "category", "status", "policy", "scenarios"):
            if not entry.get(key):
                errors.append(f"{entry_id}: 缺少 {key}")
        if entry.get("status") not in STATUS_LABEL:
            errors.append(f"{entry_id}: 非法 status {entry.get('status')}")
        if entry.get("policy") not in POLICY_LABEL:
            errors.append(f"{entry_id}: 非法 policy {entry.get('policy')}")
        scenarios = entry.get("scenarios", [])
        if not scenarios or any(s not in SCENARIOS for s in scenarios):
            errors.append(f"{entry_id}: 非法 scenarios {scenarios}")
        platforms_found = [p for p in PLATFORMS if platform_table(entry, p)]
        if not platforms_found:
            errors.append(f"{entry_id}: 没有任何平台信息")
        for os_name in platforms_found:
            table = platform_table(entry, os_name)
            manager = manager_of(table)
            if manager not in MANAGERS:
                errors.append(f"{entry_id}/{os_name}: 非法 manager {manager}")
            if manager in ("winget", "npm", "uv", "brew") and not table.get("package"):
                errors.append(f"{entry_id}/{os_name}: {manager} 缺少 package")
            if manager == "apt" and not package_names(table):
                errors.append(f"{entry_id}/{os_name}: apt 缺少 package/packages")
            if manager == "manual" and not (table.get("command") or table.get("note")):
                errors.append(f"{entry_id}/{os_name}: manual 缺少 command/note")

    if errors:
        print(f"发现 {len(errors)} 个问题：", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1
    print(f"校验通过：{len(catalog['software'])} 条，ID 唯一，字段与 manager 合法。")
    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--scenario", choices=SCENARIOS, help="只看某个场景")
    parser.add_argument("--os", choices=("auto", *PLATFORMS), default="auto", help="目标平台，默认按当前系统判断")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="watchapp", description="软件目录与安装/更新服务")
    sub = parser.add_subparsers(dest="command", required=True)

    p_list = sub.add_parser("list", help="列出软件")
    add_common(p_list)
    p_list.add_argument("--status", nargs="+", choices=tuple(STATUS_LABEL))
    p_list.add_argument("--policy", nargs="+", choices=tuple(POLICY_LABEL))
    p_list.add_argument("--json", action="store_true")
    p_list.set_defaults(func=cmd_list)

    p_show = sub.add_parser("show", help="查看单个条目")
    p_show.add_argument("id")
    p_show.set_defaults(func=cmd_show)

    p_check = sub.add_parser("check", help="检查本机可更新的条目")
    add_common(p_check)
    p_check.add_argument("--json", action="store_true")
    p_check.set_defaults(func=cmd_check)

    p_install = sub.add_parser("install", help="安装某个条目或某个场景的全部条目（默认只打印命令）")
    p_install.add_argument("id", nargs="?")
    p_install.add_argument("--all", action="store_true", help="安装该场景下所有 active 条目")
    p_install.add_argument("--scenario", choices=SCENARIOS, help="配合 --all 使用")
    p_install.add_argument("--os", choices=("auto", *PLATFORMS), default="auto")
    p_install.add_argument("--apply", action="store_true", help="真正执行")
    p_install.add_argument("--force", action="store_true", help="允许安装上游停更条目")
    p_install.set_defaults(func=cmd_install)

    p_update = sub.add_parser("update", help="更新条目（默认只打印命令）")
    p_update.add_argument("ids", nargs="*")
    p_update.add_argument("--all", action="store_true", help="更新全部符合条件的条目")
    p_update.add_argument("--scenario", choices=SCENARIOS)
    p_update.add_argument("--os", choices=("auto", *PLATFORMS), default="auto")
    p_update.add_argument("--policy", default="p0,p1", help="--all 时纳入的策略，默认 p0,p1")
    p_update.add_argument("--apply", action="store_true", help="真正执行")
    p_update.add_argument("--force", action="store_true", help="允许更新 hold/observe 条目")
    p_update.set_defaults(func=cmd_update)

    p_render = sub.add_parser("render", help="生成 catalog/software.md")
    p_render.add_argument("--check", action="store_true", help="只检查是否与数据源一致")
    p_render.set_defaults(func=cmd_render)

    p_validate = sub.add_parser("validate", help="校验 catalog")
    p_validate.set_defaults(func=cmd_validate)

    p_privacy = sub.add_parser("privacy", help="扫描仓库中的敏感信息（邮箱/私有 IP/内部域名/用户目录/凭据/私有路径）")
    p_privacy.add_argument("--json", action="store_true")
    p_privacy.set_defaults(func=cmd_privacy)

    p_stats = sub.add_parser("stats", help="统计当前管理的软件")
    p_stats.add_argument("--json", action="store_true")
    p_stats.set_defaults(func=cmd_stats)

    p_scan = sub.add_parser("scan", help="按白名单扫描允许的机器目录（只输出名称/计数）")
    p_scan.add_argument("--json", action="store_true")
    p_scan.add_argument("--limit", type=int, default=50, help="每个根目录最多显示多少项")
    p_scan.set_defaults(func=cmd_scan)

    args = parser.parse_args(argv)
    if args.command == "install" and not args.all and not args.id:
        parser.error("install 需要 id，或用 --all --scenario <场景>")
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
