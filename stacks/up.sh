#!/usr/bin/env bash
# 一键启动自建容器栈（navbook + notes）。
set -euo pipefail

root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
pull=0
dry_run=0

usage() {
  cat <<'USAGE'
用法: stacks/up.sh [--pull] [--dry-run]

  --pull      启动前先拉取最新镜像（用于跟进上游版本）
  --dry-run   只打印命令，不创建目录、不启动容器
USAGE
}

for arg in "$@"; do
  case "$arg" in
    --pull) pull=1 ;;
    --dry-run) dry_run=1 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "未知参数: $arg" >&2; usage >&2; exit 2 ;;
  esac
done

command -v docker >/dev/null 2>&1 || {
  echo "未找到 docker，请先安装 Docker Engine / Docker Compose。" >&2
  exit 1
}
docker compose version >/dev/null 2>&1 || {
  echo "未找到 docker compose（Compose v2 插件）。" >&2
  exit 1
}

# 每个栈的宿主机数据目录；均为 gitignored，不随仓库提交。
data_dir_for() {
  case "$1" in
    navbook) echo "data" ;;
    notes) echo "books" ;;
    *) echo "" ;;
  esac
}

for stack in navbook notes; do
  dir="$root/$stack"
  [[ -f "$dir/compose.yaml" ]] || {
    echo "缺少 $dir/compose.yaml" >&2
    exit 1
  }

  data_dir="$(data_dir_for "$stack")"
  if [[ -z "$data_dir" ]]; then
    echo "未知栈: $stack" >&2
    exit 1
  fi

  if (( dry_run )); then
    echo "[dry-run] mkdir -p $dir/$data_dir"
    if (( pull )); then
      echo "[dry-run] docker compose -f $dir/compose.yaml pull"
    fi
    echo "[dry-run] docker compose -f $dir/compose.yaml up -d"
    continue
  fi

  mkdir -p "$dir/$data_dir"
  if (( pull )); then
    docker compose -f "$dir/compose.yaml" pull
  fi
  docker compose -f "$dir/compose.yaml" up -d
done

if (( ! dry_run )); then
  cat <<'URLS'
已启动：
  navbook  http://localhost:5556
  notes    http://localhost:40001
URLS
fi
