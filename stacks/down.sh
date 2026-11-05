#!/usr/bin/env bash
# 停止自建容器栈；不删除数据目录。
set -euo pipefail

root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
command -v docker >/dev/null 2>&1 || { echo "未找到 docker" >&2; exit 1; }

for stack in notes navbook; do
  if [[ -f "$root/$stack/compose.yaml" ]]; then
    echo "== $stack"
    docker compose -f "$root/$stack/compose.yaml" down
  fi
done
