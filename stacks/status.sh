#!/usr/bin/env bash
# 查看自建容器栈状态。
set -euo pipefail

root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
command -v docker >/dev/null 2>&1 || { echo "未找到 docker" >&2; exit 1; }

for stack in navbook notes; do
  echo "== $stack"
  if [[ -f "$root/$stack/compose.yaml" ]]; then
    docker compose -f "$root/$stack/compose.yaml" ps -a
  else
    echo "缺少 $root/$stack/compose.yaml"
  fi
done
