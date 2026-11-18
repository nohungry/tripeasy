# TripEasy

旅遊電商網站的重建專案（作品集）。原為 tripEasyCompany 團隊作品，本 repo 為總覽：docker compose、測試、文件、階段報告。

| Repo | 內容 |
|---|---|
| [tripeasy-backend](https://github.com/nohungry/tripeasy-backend) | Express API |
| [tripeasy-frontend](https://github.com/nohungry/tripeasy-frontend) | Vue 3 前端 |

## 快速開始

需要 Docker（含 Compose v2）和 [uv](https://docs.astral.sh/uv/)。若系統沒有 Python 3.13，uv 會依 `.python-version` 自動下載。

```bash
git clone https://github.com/nohungry/tripeasy.git && cd tripeasy
git clone -b "$(grep BACKEND_REF refs.env | cut -d= -f2)" https://github.com/nohungry/tripeasy-backend.git backend
git clone -b "$(grep FRONTEND_REF refs.env | cut -d= -f2)" https://github.com/nohungry/tripeasy-frontend.git frontend
scripts/ci.sh        # 啟動全部服務並跑測試
```

| 服務 | 網址 |
|---|---|
| 前端 | http://localhost:5173 |
| API | http://localhost:3000/api/v1/health |
| Mailpit（收信） | http://localhost:8025 |
| mock Google OAuth | http://localhost:8090/google/.well-known/openid-configuration |

## 版本對照

| 階段 | backend | frontend | 報告 |
|---|---|---|---|
| P0 地基 | `phase-0` | `phase-0` | [phase-0.md](docs/reports/phase-0.md) |
| P1 路由、seed、DB 契約 | `phase-1` | `phase-0` | [phase-1.md](docs/reports/phase-1.md) |
| P2 會員 | `phase-2` | `phase-2` | [phase-2.md](docs/reports/phase-2.md) |

## 文件

- [現況盤點](docs/inventory.md)
- [設計 spec](docs/superpowers/specs/2026-10-15-tripeasy-rebuild-design.md)
