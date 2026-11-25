#!/usr/bin/env bash
# 本機與 CI 共用：啟動整套服務 → 等待就緒 → 跑 pytest
set -euo pipefail
cd "$(dirname "$0")/.."

[ -f .env ] || cp .env.example .env

wait_for() {
  local name=$1 url=$2
  for _ in $(seq 1 90); do
    if curl -fsS -o /dev/null "$url"; then
      echo "✅ $name"
      return 0
    fi
    sleep 2
  done
  echo "❌ $name 未就緒：$url"
  docker compose ps -a
  docker compose logs --tail=100
  return 1
}

docker compose up -d --build --renew-anon-volumes

wait_for backend    http://localhost:3000/api/v1/health
wait_for frontend   http://localhost:5173/
wait_for mailpit    http://localhost:8025/api/v1/info
wait_for mock-oauth http://localhost:8090/google/.well-known/openid-configuration
wait_for mock-newebpay http://localhost:8095/health

uv sync --frozen
if [ -n "${CI:-}" ]; then
  uv run playwright install --with-deps chromium
else
  uv run playwright install chromium
fi
uv run pytest -v
