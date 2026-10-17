# P0 地基 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 一行 `docker compose up` 就能啟動 postgres、flyway、backend、frontend、mailpit、mock-oauth，全部健康；外部服務都有本機替身；pytest 骨架和 CI 都是綠燈。

**Architecture:** 總覽 repo（`~/project/tripeasy`）放 compose、`.env.example`、pytest 測試、CI，用 `refs.env` 綁定 backend / frontend 兩個獨立 repo 的版本。backend 只做最小改動：把 Firebase、SendGrid、Google OAuth 收到 adapter 或環境變數後面，再補上 async 錯誤處理。測試全部用 Python 從外部打 HTTP 和 DB。

**Tech Stack:** Docker Compose v2、PostgreSQL 15、Flyway 10.20.1、Node 22.14.0（Express 4.21 / Vite 6）、Mailpit v1.20、navikt/mock-oauth2-server 2.1.10、Python 3.10+ / uv / pytest 8.3.3 / requests / psycopg 3 / PyJWT、GitHub Actions。

**Spec:** `docs/superpowers/specs/2026-10-15-tripeasy-rebuild-design.md`（第 1、2 節為本計畫範圍）

## Global Constraints

- 所有 Node 容器一律使用 `node:22.14.0`（`backend/.nvmrc`）。
- **沿用既有程式碼**：只改本計畫列出的檔案和行數，不重構、不清掉沒用到的套件。
- 新增的 npm 套件只有兩個：`nodemailer`（Task 5）、`express-async-errors`（Task 6）。
- adapter 的程式預設值維持原本的行為：`STORAGE_DRIVER` 預設 `firebase`、`MAIL_DRIVER` 預設 `sendgrid`、OAuth 網址預設 Google。本機的值都寫在根目錄的 `.env.example`。
- 環境變數只有一個來源：根目錄的 `.env`（由 `.env.example` 複製），compose 用 `env_file` 注入給 backend。
- 分支：backend 從 `main`、frontend 從 `dev`、總覽 repo 從 `main`，三個 repo 都開 `phase-0` 分支。**總覽 repo 的 main 必須維持全綠**，紅燈只會出現在 `phase-0` 上。
- commit 規則：紅燈測試單獨一個 commit（`test: ... 🔴`），修正另外一個 commit（`fix:/feat: ... 🟢`）。每個紅燈 commit 都要把 pytest 的失敗輸出存到 `docs/reports/evidence/phase-0/<task>-red.txt`，供報告引用。
- commit 訊息結尾要加上 `Co-Authored-By` 行，註明實際執行的模型。
- **不 push、不建立 GitHub repo、不碰 upstream**。這些對外動作要在 Task 10 先問使用者。
- 模型分工：每個 Task 由 Sonnet 實作。同一個 Task 連續修兩次還是紅燈，就升級 Opus。每個 Task 的 review 由 Fable 和 Opus 平行進行，再比對兩邊的結果。
- 所有指令都在總覽 repo 根目錄 `/home/nohungry/project/tripeasy` 執行，除非步驟另有註明。

## Review Focus

1. **第二次 `docker compose up`（volume 保留著）**：Flyway 應該判斷沒有新 migration 而不做事，所有服務照樣健康，測試照樣綠燈。→ Task 9 Step 4
2. **沒有 Firebase 金鑰，但 `STORAGE_DRIVER=firebase`**：backend 應該能正常開機，只有在真的上傳時才失敗，而不是一載入就 crash。→ Task 4 Step 6
3. **上傳檔名包含 `../`、空白、中文**：檔案不能寫到 `UPLOAD_DIR` 之外，回傳的 URL 要能正常存取。→ Task 4 測試 `test_upload_filename_cannot_escape_upload_dir`
4. **在 `try` 外面發生、沒被接住的 rejection**：該請求要回 500，**而且 server 要繼續活著**，不能讓整個 process 掛掉。→ Task 6 測試
5. **不在白名單裡的 Origin**：response 不能帶 `Access-Control-Allow-Origin`，server 也不能因此出問題。→ Task 8 測試 `test_cors_rejects_unknown_origin`

## 不在 P0 修的已知問題（遇到時只記錄，寫進報告附錄）

| 問題 | 歸屬 |
|---|---|
| `forgetpw` 收到不存在的 email 會回 500（`userinfo.js:253`，`user` 是 undefined） | P2 |
| 重設密碼信的連結 `${FRONTEND_PATH}/admin/resetpw` 沒有考慮前端是 hash 路由 | P2 |
| `socialLogin.provider_token` 是 VARCHAR(255)，可能放不下 mock 或真實的 JWT access token | P2（見 Task 7） |
| Google 的 redirect 回到首頁，`loginPage.vue:108` 讀取 `location.search` 的流程在 hash 路由下走不到 | P2 |
| fakedata 的角色是 `user` / `admin`，但程式用 `authRole('User')`，大小寫不一致 | P1 seed |
| 不在白名單的 Origin 會讓 CORS callback 丟出 Error，最後回 500 | P2 |

---

## 檔案結構

```
~/project/tripeasy/                       （總覽 repo）
├── .gitignore                            Task 1
├── refs.env                              Task 1：BACKEND_REF / FRONTEND_REF
├── README.md                             Task 1 骨架，Task 10 完成
├── .env.example                          Task 3：全部環境變數（本機值）
├── docker-compose.yml                    Task 3 建立；Task 5、7、8 各追加一個服務
├── pyproject.toml / uv.lock              Task 3
├── scripts/ci.sh                         Task 9：本機和 CI 共用
├── .github/workflows/ci.yml              Task 9
├── tests/
│   ├── conftest.py                       Task 3：api / db / make_user / auth_header
│   ├── test_health.py                    Task 3（紅）→ Task 4（綠）
│   ├── test_migrations.py                Task 3
│   ├── test_storage.py                   Task 4
│   ├── test_mail.py                      Task 5
│   ├── test_async_errors.py              Task 6
│   ├── test_oauth_spike.py               Task 7
│   └── test_frontend.py                  Task 8
└── docs/reports/
    ├── evidence/phase-0/*.txt            每個紅燈的輸出
    └── phase-0.md                        Task 10

backend/（分支 phase-0）
├── .gitignore                            Task 2：拿掉 package-lock.json
├── .dockerignore                         Task 2
├── package-lock.json                     Task 2 產生；Task 5、6 更新
├── Dockerfile                            Task 2：base / dev / prod 三個 stage
├── docker-compose.yml, docker-compose.dev.yml   Task 2：healthcheck 路徑、拿掉固定 IP
├── src/config/firebase.js                Task 4：改成 getBucket() 延遲初始化
├── src/utils/storage/index.js            Task 4：依 STORAGE_DRIVER 分派
├── src/utils/storage/local.js            Task 4
├── src/utils/storage/firebase.js         Task 4
├── src/utils/firebaseUpload.js           Task 4：改用 storage（匯出的名稱不變）
├── src/controllers/userProfile.js        Task 4：:3、:90-125
├── src/server.js                         Task 4（/uploads 靜態檔）、Task 6（async errors）
├── src/utils/mailer.js                   Task 5
├── src/controllers/userinfo.js           Task 5：:3、:259-275
└── src/middlewares/userinfo/index.js     Task 7：:146、:163

frontend/（分支 phase-0）
├── .env.development                      Task 8
├── .env.production                       Task 8
├── .env.example                          Task 8
└── src/views/admin/loginPage.vue         Task 8：:153-160
```

---

### Task 1: 總覽 repo 初始化與分支

**Files:**
- Create: `.gitignore`, `refs.env`, `README.md`
- 既有內容一起 commit：`docs/inventory.md`、`docs/superpowers/specs/*`、`docs/superpowers/plans/*`

**Interfaces:**
- Produces: `refs.env` 的格式為 `KEY=value`，不加空白和引號，CI 會直接 `cat refs.env >> $GITHUB_ENV`。鍵名是 `BACKEND_REF`、`FRONTEND_REF`。

- [ ] **Step 1: 確認現況**

Run:
```bash
cd /home/nohungry/project/tripeasy
git rev-parse --is-inside-work-tree 2>&1 | head -1   # 預期：fatal: not a git repository
git -C backend status --short | wc -l                 # 預期：0
git -C frontend status --short | wc -l                # 預期：0
git -C backend branch --show-current                  # 預期：main
git -C frontend branch --show-current                 # 預期：dev
```
如果 backend 或 frontend 有未 commit 的修改，**停下來回報**，不要繼續。

- [ ] **Step 2: 建立 `.gitignore`**

```gitignore
# 獨立 repo，由 refs.env 綁定版本
backend/
frontend/

# 本機環境變數（範本是 .env.example）
.env

# Python
.venv/
__pycache__/
.pytest_cache/
```

- [ ] **Step 3: 建立 `refs.env`**

```
BACKEND_REF=phase-0
FRONTEND_REF=phase-0
```

- [ ] **Step 4: 建立 `README.md` 骨架**

```markdown
# TripEasy

旅遊電商網站的重建專案（作品集）。原為 tripEasyCompany 團隊作品，本 repo 為總覽：docker compose、測試、文件、階段報告。

| Repo | 內容 |
|---|---|
| [tripeasy-backend](https://github.com/nohungry/tripeasy-backend) | Express API |
| [tripeasy-frontend](https://github.com/nohungry/tripeasy-frontend) | Vue 3 前端 |

## 快速開始

（P0 完成後補上）

## 文件

- [現況盤點](docs/inventory.md)
- [設計 spec](docs/superpowers/specs/2026-10-15-tripeasy-rebuild-design.md)
```

- [ ] **Step 5: 初始化 repo、commit，開出三個 `phase-0` 分支**

```bash
git init -b main
git add .gitignore refs.env README.md docs/
git status --short        # 確認沒有 backend/、frontend/
git commit -m "chore: 建立總覽 repo（盤點、spec、P0 計畫）"
git switch -c phase-0
git -C backend switch -c phase-0
git -C frontend switch -c phase-0
```
預期：`git status --short` 裡沒有 `backend/` 和 `frontend/`。三個 repo 的 `git branch --show-current` 都是 `phase-0`。

---

### Task 2: backend 的 lockfile、Dockerfile、舊 compose 修正

**Files:**
- Modify: `backend/.gitignore`（刪除 `package-lock.json` 那一行）
- Create: `backend/package-lock.json`, `backend/.dockerignore`
- Modify: `backend/Dockerfile`（整份重寫）
- Modify: `backend/docker-compose.yml`, `backend/docker-compose.dev.yml`

**Interfaces:**
- Produces: Dockerfile 有 `dev` 和 `prod` 兩個 target。`dev` 會把 node_modules 裝在 image 的 `/usr/backend/node_modules`，然後執行 `npm run dev`（nodemon）。Task 3 的 compose 會使用 `target: dev`。

- [ ] **Step 1: 寫出驗證指令，先確認目前是失敗的**

Run:
```bash
docker build --target prod -t tripeasy-backend:prod backend
```
預期：FAIL。現在的 Dockerfile 沒有名為 `prod` 的 stage（`target stage "prod" could not be found`）。

- [ ] **Step 2: 讓 lockfile 進版控，用 Node 22.14.0 產生**

把 `backend/.gitignore` 裡的 `package-lock.json` 那一行刪掉（`yarn.lock` 保留）。

```bash
docker run --rm -u "$(id -u):$(id -g)" -e npm_config_cache=/tmp/.npm \
  -v "$PWD/backend":/app -w /app node:22.14.0 npm install --package-lock-only
test -f backend/package-lock.json && echo OK
```

- [ ] **Step 3: 建立 `backend/.dockerignore`**

```
node_modules
pgdb-data
uploads
.git
.env
.env.*
!.env.example
```

- [ ] **Step 4: 重寫 `backend/Dockerfile`**

```dockerfile
# base：共用的 Node 版本與依賴清單
FROM node:22.14.0 AS base
WORKDIR /usr/backend
COPY package.json package-lock.json ./

# dev：含 devDependencies（nodemon），原始碼由 compose bind mount
FROM base AS dev
RUN npm ci
COPY . .
EXPOSE 3000
CMD ["npm", "run", "dev"]

# prod：只裝 production 依賴
FROM base AS prod
ENV NODE_ENV=production
RUN npm ci --omit=dev
COPY . .
EXPOSE 3000
CMD ["node", "src/server.js"]
```

- [ ] **Step 5: 修正 backend 自己的舊 compose 檔**

`backend/docker-compose.yml`：
- 把 `api` 的 healthcheck 改成 `test: ['CMD', 'curl', '-f', 'http://localhost:${PORT}/api/v1/health']`
- 刪除兩個服務底下的 `networks: tripeasy_net: ipv4_address: ...`，改成 `networks: [tripeasy_net]`
- 頂層的 `networks.tripeasy_net` 只保留 `driver: bridge`，刪掉 `ipam` 整段

`backend/docker-compose.dev.yml`：`migrate` 底下的 `ipv4_address` 一樣改成 `networks: [tripeasy_net]`。

- [ ] **Step 6: 驗證**

```bash
docker build --target dev  -t tripeasy-backend:dev  backend
docker build --target prod -t tripeasy-backend:prod backend
docker run --rm tripeasy-backend:prod node -e "require('express'); console.log('prod ok')"
docker compose -f backend/docker-compose.yml -f backend/docker-compose.dev.yml --env-file backend/.env.example config -q && echo "compose ok"
```
預期：兩個 build 都成功，最後依序印出 `prod ok` 和 `compose ok`。

- [ ] **Step 7: Commit（backend repo）**

```bash
git -C backend add .gitignore .dockerignore package-lock.json Dockerfile docker-compose.yml docker-compose.dev.yml
git -C backend commit -m "build: 加入 lockfile、Dockerfile 分 dev/prod、修正 compose healthcheck 與固定 IP"
```

---

### Task 3: 總覽 compose、`.env.example`、pytest 骨架（health 紅燈）

**Files:**
- Create: `.env.example`, `docker-compose.yml`, `pyproject.toml`, `uv.lock`（由 uv 產生）
- Create: `tests/conftest.py`, `tests/test_migrations.py`, `tests/test_health.py`
- Create: `docs/reports/evidence/phase-0/task3-health-red.txt`

**Interfaces:**
- Consumes: Task 2 的 Dockerfile `dev` target。
- Produces（之後所有測試都會用到）：
  - 常數 `API_BASE`、`FRONTEND_BASE`、`MAILPIT_BASE`、`MOCK_OAUTH_BASE`：`str`，可以用環境變數 `TEST_*` 覆寫
  - fixture `api`：`Api(requests.Session)`，路徑以 `/` 開頭時自動加上 `API_BASE`，預設 timeout 10 秒
  - fixture `db`：`psycopg.Connection`（autocommit）
  - fixture `make_user(role="User", email=None) -> dict{user_id, email, role}`，測試結束後自動刪除
  - 函式 `auth_header(user: dict) -> dict`：回傳 `{"Authorization": "Bearer <HS256 JWT {id, role}>"}`
  - 函式 `delete_user(db, user_id: str) -> None`
  - compose 的服務名稱：`postgres`、`flyway`、`backend`，volume 名稱：`pgdata`、`uploads`

- [ ] **Step 1: 建立 `.env.example`**

這份檔案一次列出整個 P0 會用到的變數，後面的 Task 不需要再改它。

```bash
# TripEasy 本機環境變數（複製成 .env 使用）
# 注意：這裡全部是本機用的假值，部署時用平台的環境變數覆寫

# ── 執行環境 ──
NODE_ENV=development
PORT=3000
FRONTEND_PATH=http://localhost:5173

# ── PostgreSQL ──
POSTGRES_VERSION=15
POSTGRES_DB_HOST=postgres
POSTGRES_DB_PORT=5432
POSTGRES_DB_USER=tripeasy_admin001
POSTGRES_DB_PASSWORD=tripeasy_pw001
POSTGRES_DB_NAME=tripeasy_db001
POSTGRES_DB_SSL=false

# ── JWT ──
JWT_SECRET=local-dev-secret-change-me
JWT_EXPIRES_DAY=30d

# ── 第三方登入（本機指向 mock-oauth 容器）──
DEFAULT_OAUTH_PASSWORD=local-oauth-default-pw
GOOGLE_CLIENT_ID=tripeasy-local
GOOGLE_CLIENT_SECRET=tripeasy-local-secret
GOOGLE_REDIRECT_URI=http://localhost:5173/
GOOGLE_TOKEN_URL=http://mock-oauth:8080/google/token
GOOGLE_USERINFO_URL=http://mock-oauth:8080/google/userinfo

# ── 圖片儲存（local | firebase）──
STORAGE_DRIVER=local
UPLOAD_DIR=/usr/backend/uploads
STORAGE_PUBLIC_BASE_URL=http://localhost:3000
FIREBASE_SERVICE_ACCOUNT=
FIREBASE_STORAGE_BUCKET=

# ── 寄信（smtp | sendgrid）──
MAIL_DRIVER=smtp
SMTP_HOST=mailpit
SMTP_PORT=1025
MAIL_FROM=no-reply@tripeasy.local
SENDGRID_API_KEY=
SENDGRID_FROM_EMAIL=

# ── 藍新金流（測試環境）──
MerchantID=
HASHKEY=
HASHIV=
Version=2.0
RespondType=JSON
ReturnUrl=
NotifyUrl=
PayGateWay=https://ccore.newebpay.com/MPG/mpg_gateway
```

```bash
cp .env.example .env
```

- [ ] **Step 2: 建立 `docker-compose.yml`**

```yaml
name: tripeasy

services:
  postgres:
    image: postgres:${POSTGRES_VERSION:-15}
    environment:
      POSTGRES_DB: ${POSTGRES_DB_NAME}
      POSTGRES_USER: ${POSTGRES_DB_USER}
      POSTGRES_PASSWORD: ${POSTGRES_DB_PASSWORD}
    ports:
      - '5432:5432'
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ['CMD-SHELL', 'pg_isready -U ${POSTGRES_DB_USER} -d ${POSTGRES_DB_NAME}']
      interval: 5s
      retries: 10

  flyway:
    image: flyway/flyway:10.20.1
    depends_on:
      postgres:
        condition: service_healthy
    command:
      - '-url=jdbc:postgresql://postgres:5432/${POSTGRES_DB_NAME}'
      - '-user=${POSTGRES_DB_USER}'
      - '-password=${POSTGRES_DB_PASSWORD}'
      - '-locations=filesystem:/flyway/sql'
      - '-connectRetries=10'
      - 'migrate'
    volumes:
      - ./backend/migrations:/flyway/sql:ro

  backend:
    build:
      context: ./backend
      target: dev
    env_file: .env
    depends_on:
      flyway:
        condition: service_completed_successfully
    ports:
      - '${PORT:-3000}:${PORT:-3000}'
    volumes:
      - ./backend:/usr/backend
      - /usr/backend/node_modules
      - uploads:/usr/backend/uploads
    healthcheck:
      test: ['CMD', 'curl', '-fsS', 'http://localhost:${PORT:-3000}/api/v1/health']
      interval: 5s
      retries: 20

volumes:
  pgdata:
  uploads:
```

- [ ] **Step 3: 建立 `pyproject.toml`，安裝依賴**

```toml
[project]
name = "tripeasy-tests"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = [
  "pytest==8.3.3",
  "requests==2.32.3",
  "psycopg[binary]==3.2.3",
  "PyJWT==2.9.0",
  "python-dotenv==1.0.1",
]

[tool.uv]
package = false

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-ra"
```

```bash
uv sync
```

- [ ] **Step 4: 建立 `tests/conftest.py`**

```python
"""共用 fixture：API session、DB 連線、測試使用者、JWT。"""
import os
import uuid
from pathlib import Path

import jwt
import psycopg
import pytest
import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

API_BASE = os.getenv("TEST_API_BASE", "http://localhost:3000")
FRONTEND_BASE = os.getenv("TEST_FRONTEND_BASE", "http://localhost:5173")
MAILPIT_BASE = os.getenv("TEST_MAILPIT_BASE", "http://localhost:8025")
MOCK_OAUTH_BASE = os.getenv("TEST_MOCK_OAUTH_BASE", "http://localhost:8090")
DEFAULT_TIMEOUT = 10


class Api(requests.Session):
    """路徑以 / 開頭時自動接上 base，並一律帶 timeout（避免卡住的請求讓測試無限等待）。"""

    def __init__(self, base: str):
        super().__init__()
        self.base = base

    def request(self, method, url, *args, **kwargs):
        kwargs.setdefault("timeout", DEFAULT_TIMEOUT)
        if url.startswith("/"):
            url = self.base + url
        return super().request(method, url, *args, **kwargs)


@pytest.fixture(scope="session")
def api():
    session = Api(API_BASE)
    yield session
    session.close()


@pytest.fixture(scope="session")
def db():
    conn = psycopg.connect(
        host=os.getenv("TEST_DB_HOST", "localhost"),
        port=int(os.getenv("TEST_DB_PORT", "5432")),
        user=os.environ["POSTGRES_DB_USER"],
        password=os.environ["POSTGRES_DB_PASSWORD"],
        dbname=os.environ["POSTGRES_DB_NAME"],
        autocommit=True,
    )
    yield conn
    conn.close()


def delete_user(db, user_id: str) -> None:
    """依 FK 順序刪除使用者和它的附屬資料。"""
    for table in ('"socialLogin"', "point_record", "user_level"):
        db.execute(f"DELETE FROM {table} WHERE user_id = %s", (user_id,))
    db.execute('DELETE FROM "user" WHERE user_id = %s', (user_id,))


@pytest.fixture
def make_user(db):
    created: list[str] = []

    def _make(role: str = "User", email: str | None = None) -> dict:
        email = email or f"p0-{uuid.uuid4().hex[:8]}@example.com"
        (user_id,) = db.execute(
            'INSERT INTO "user" (name, email, role, password, preference1, preference2, preference3) '
            "VALUES (%s, %s, %s, %s, 1, 2, 3) RETURNING user_id",
            ("P0 測試", email, role, "not-a-real-hash"),
        ).fetchone()
        created.append(str(user_id))
        return {"user_id": str(user_id), "email": email, "role": role}

    yield _make
    for user_id in created:
        delete_user(db, user_id)


def auth_header(user: dict) -> dict:
    """跟 backend 登入時簽發的 payload 一樣：{id, role}。"""
    token = jwt.encode(
        {"id": user["user_id"], "role": user["role"]},
        os.environ["JWT_SECRET"],
        algorithm="HS256",
    )
    return {"Authorization": f"Bearer {token}"}
```

注意：Python 3.10 支援 `str | None` 和 `list[str]` 這兩種寫法。

- [ ] **Step 5: 建立 `tests/test_migrations.py`**

```python
"""確認 Flyway 已套用 V1、V2，並且 V1 的 25 張表都存在。"""

EXPECTED_TABLES = {
    "user", "socialLogin", "user_level", "coupon", "user_coupon", "point_record",
    "tour", "tour_detail", "restaurant", "restaurant_business", "restaurant_menu",
    "hotel", "hotel_room", "notification", "country", "region",
    "cart", "cart_item", "orders", "order_item", "payment",
    "review", "hidden_play", "auto_setting", "favorite",
}


def test_flyway_applied_v1_and_v2(db):
    rows = db.execute(
        "SELECT version, success FROM flyway_schema_history "
        "WHERE version IS NOT NULL ORDER BY installed_rank"
    ).fetchall()
    assert rows == [("1", True), ("2", True)]


def test_all_v1_tables_exist(db):
    names = {
        r[0]
        for r in db.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_type = 'BASE TABLE'"
        )
    }
    missing = EXPECTED_TABLES - names
    assert not missing, f"缺少資料表：{sorted(missing)}"
```

- [ ] **Step 6: 建立 `tests/test_health.py`**

```python
def test_health_ok(api):
    r = api.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
```

- [ ] **Step 7: 啟動 compose，確認 migration 測試綠燈、health 測試紅燈**

```bash
docker compose up -d --build
sleep 20
docker compose ps -a
docker compose logs backend --tail=30
uv run pytest tests/test_migrations.py -v
uv run pytest tests/test_health.py -v 2>&1 | tee docs/reports/evidence/phase-0/task3-health-red.txt
```
（`docs/reports/evidence/phase-0/` 不存在的話先 `mkdir -p`。）

預期：
- `flyway` 的狀態是 `Exited (0)`
- `test_migrations.py` 兩個測試都 PASS
- backend 的 log 出現 `Missing FIREBASE_SERVICE_ACCOUNT environment variable`，nodemon 顯示 `app crashed`
- `test_health.py` FAIL，錯誤是 `requests.exceptions.ConnectionError`（或 `ConnectionResetError`）

如果 health **意外通過**，**停下來回報**，表示盤點時的假設跟實際狀況不符。

- [ ] **Step 8: Commit（總覽 repo，紅燈）**

```bash
git add .env.example docker-compose.yml pyproject.toml uv.lock tests/ docs/reports/evidence/
git commit -m "test: 🔴 compose 骨架 + health 測試（backend 因 firebase 缺金鑰在載入時 crash）"
```

---

### Task 4: Storage adapter + Firebase 延遲初始化（health 轉綠）

**Files:**
- Modify: `backend/src/config/firebase.js`（整份重寫）
- Create: `backend/src/utils/storage/index.js`, `backend/src/utils/storage/local.js`, `backend/src/utils/storage/firebase.js`
- Modify: `backend/src/utils/firebaseUpload.js`（:1-58 的 `uploadImageToFirebase`、:150-171 的 `deleteImageFromFirebase`、:2 的 require）
- Modify: `backend/src/controllers/userProfile.js:3`、`:90-125`
- Modify: `backend/src/server.js`（`express.static` 那一行附近）
- Test: `tests/test_storage.py`

**Interfaces:**
- Consumes: `.env` 的 `STORAGE_DRIVER`、`UPLOAD_DIR`、`STORAGE_PUBLIC_BASE_URL`；conftest 的 `api`、`db`、`make_user`、`auth_header`、`API_BASE`。
- Produces:
  - `require('./utils/storage')` → `{ upload(buffer: Buffer, key: string, contentType: string): Promise<string /* 公開 URL */>, remove(url: string): Promise<boolean> }`
  - `require('./config/firebase')` → `{ getBucket(): Bucket }`（第一次呼叫才初始化）
  - `require('./utils/storage/local').UPLOAD_DIR`：絕對路徑
  - local 的 URL 格式：`${STORAGE_PUBLIC_BASE_URL}/uploads/<encodeURIComponent 過的路徑>`
  - `firebaseUpload.js` 匯出的四個函式名稱和簽名**不變**，`controllers/product.js` 不需要改

- [ ] **Step 1: 寫失敗的測試 `tests/test_storage.py`**

```python
"""本機 storage adapter：頭像上傳後存在 volume，經由 /uploads 提供存取。"""
from urllib.parse import unquote, urlparse

import requests

from conftest import API_BASE, auth_header

PNG = b"\x89PNG\r\n\x1a\n" + b"tripeasy-p0-avatar"


def _upload_avatar(api, user, filename):
    return api.patch(
        "/api/v1/user/userinfo/avatar",
        headers=auth_header(user),
        files={"image": (filename, PNG, "image/png")},
    )


def test_avatar_upload_stored_locally(api, db, make_user):
    user = make_user()

    r = _upload_avatar(api, user, "avatar.png")

    assert r.status_code == 200, r.text
    url = r.json()["data"]["avatar_url"]
    assert url.startswith(f"{API_BASE}/uploads/userProfile/")
    got = requests.get(url, timeout=10)
    assert got.status_code == 200
    assert got.content == PNG
    (db_url,) = db.execute(
        'SELECT avatar_url FROM "user" WHERE user_id = %s', (user["user_id"],)
    ).fetchone()
    assert db_url == url


def test_upload_filename_cannot_escape_upload_dir(api, make_user):
    user = make_user()

    r = _upload_avatar(api, user, "../../../evil 圖.png")

    assert r.status_code == 200, r.text
    url = r.json()["data"]["avatar_url"]
    path = unquote(urlparse(url).path)
    assert path.startswith("/uploads/userProfile/")
    assert ".." not in path.split("/")
    assert requests.get(url, timeout=10).content == PNG
```

- [ ] **Step 2: 確認測試失敗**

Run: `uv run pytest tests/test_storage.py tests/test_health.py -v`
預期：全部 FAIL，錯誤是 ConnectionError，因為 backend 還在 crash 狀態。

- [ ] **Step 3: Commit 紅燈**

```bash
uv run pytest tests/test_storage.py -v 2>&1 | tee docs/reports/evidence/phase-0/task4-storage-red.txt
git add tests/test_storage.py docs/reports/evidence/phase-0/task4-storage-red.txt
git commit -m "test: 🔴 本機 storage 頭像上傳、檔名路徑穿越"
```

- [ ] **Step 4: 實作**

`backend/src/config/firebase.js`（整份取代）：
```js
// firebase.js：第一次用到才初始化，缺少金鑰時不會讓整個 server 在載入時 crash
const admin = require('firebase-admin');

let bucket;

function getBucket() {
  if (bucket) return bucket;

  if (!process.env.FIREBASE_SERVICE_ACCOUNT) {
    throw new Error('Missing FIREBASE_SERVICE_ACCOUNT environment variable');
  }

  let serviceAccount;
  try {
    serviceAccount = JSON.parse(process.env.FIREBASE_SERVICE_ACCOUNT);
  } catch (err) {
    throw new Error('FIREBASE_SERVICE_ACCOUNT is not valid JSON');
  }

  admin.initializeApp({
    credential: admin.credential.cert(serviceAccount),
    storageBucket: process.env.FIREBASE_STORAGE_BUCKET,
  });
  bucket = admin.storage().bucket();
  return bucket;
}

module.exports = { getBucket };
```

`backend/src/utils/storage/index.js`：
```js
// storage adapter：依 STORAGE_DRIVER 切換 local / firebase（預設 firebase，維持原本行為）
const drivers = {
  local: () => require('./local'),
  firebase: () => require('./firebase'),
};

function driver() {
  const name = process.env.STORAGE_DRIVER || 'firebase';
  const load = drivers[name];
  if (!load) throw new Error(`Unknown STORAGE_DRIVER: ${name}`);
  return load();
}

module.exports = {
  upload: (buffer, key, contentType) => driver().upload(buffer, key, contentType),
  remove: (url) => driver().remove(url),
};
```

`backend/src/utils/storage/local.js`：
```js
// 本機儲存：寫入 UPLOAD_DIR，由 server.js 的 /uploads 提供靜態檔
const fs = require('fs/promises');
const path = require('path');

const UPLOAD_DIR = path.resolve(process.env.UPLOAD_DIR || path.join(__dirname, '../../../uploads'));

// 每一段路徑只保留安全字元，並移除 . 和 ..，避免寫到 UPLOAD_DIR 之外
function safeKey(key) {
  return key
    .split(/[\\/]+/)
    .map((part) => part.replace(/[^\w.\-一-龥]/g, '_'))
    .filter((part) => part && part !== '.' && part !== '..')
    .join('/');
}

function resolveInside(rel) {
  const full = path.join(UPLOAD_DIR, rel);
  if (!full.startsWith(UPLOAD_DIR + path.sep)) throw new Error('非法的檔案路徑');
  return full;
}

async function upload(buffer, key) {
  const rel = safeKey(key);
  const full = resolveInside(rel);
  await fs.mkdir(path.dirname(full), { recursive: true });
  await fs.writeFile(full, buffer);

  const base = process.env.STORAGE_PUBLIC_BASE_URL || `http://localhost:${process.env.PORT || 3000}`;
  return `${base}/uploads/${rel.split('/').map(encodeURIComponent).join('/')}`;
}

async function remove(url) {
  const marker = '/uploads/';
  const i = url.indexOf(marker);
  if (i < 0) return false;
  const rel = safeKey(decodeURIComponent(url.slice(i + marker.length).split('?')[0]));
  try {
    await fs.unlink(resolveInside(rel));
    return true;
  } catch (err) {
    return false;
  }
}

module.exports = { upload, remove, UPLOAD_DIR };
```

`backend/src/utils/storage/firebase.js`：
```js
// Firebase Storage：沿用原本 firebaseUpload.js 的上傳方式與 URL 格式
const { getBucket } = require('../../config/firebase');

async function upload(buffer, key, contentType) {
  const bucket = getBucket();
  const blob = bucket.file(key);

  await new Promise((resolve, reject) => {
    const stream = blob.createWriteStream({
      metadata: {
        contentType,
        metadata: { firebaseStorageDownloadTokens: new Date().toISOString() },
      },
    });
    stream.on('error', reject);
    stream.on('finish', resolve);
    stream.end(buffer);
  });

  return `https://firebasestorage.googleapis.com/v0/b/${bucket.name}/o/${encodeURIComponent(key)}?alt=media`;
}

async function remove(url) {
  const parts = url.split('/o/');
  if (parts.length < 2) throw new Error('無效的 Firebase Storage URL');
  const filePath = decodeURIComponent(parts[1].split('?')[0]);
  await getBucket().file(filePath).delete();
  return true;
}

module.exports = { upload, remove };
```

`backend/src/utils/firebaseUpload.js`：
- 第 2 行 `const bucket = require('../config/firebase');` 改成 `const storage = require('./storage');`
- `uploadImageToFirebase` 整個函式（:11-58）換成：
```js
async function uploadImageToFirebase(file, folder = 'uploads', prefix = '') {
  const timestamp = new Date().toISOString();
  const filename = `${folder}/${prefix}${timestamp}-${file.originalname}`;
  try {
    const url = await storage.upload(file.buffer, filename, file.mimetype);
    console.log(`✅ 圖片上傳成功: ${filename}`);
    return url;
  } catch (error) {
    console.error('❌ 圖片上傳錯誤:', error);
    throw new Error(`圖片上傳失敗: ${error.message}`);
  }
}
```
- `deleteImageFromFirebase` 的函式本體換成：
```js
async function deleteImageFromFirebase(fileUrl) {
  try {
    const ok = await storage.remove(fileUrl);
    if (ok) console.log(`✅ 檔案刪除成功: ${fileUrl}`);
    return ok;
  } catch (error) {
    console.error('❌ 檔案刪除失敗:', error);
    return false;
  }
}
```
- `uploadProductImages`、`uploadUserAvatar`、`module.exports` **都不要動**

`backend/src/controllers/userProfile.js`：
- 第 3 行換成 `const storage = require('../utils/storage');`
- `patch_userProfile_Photo` 裡，從 `const filename = ...` 到 `blobStream.on('finish', async () => { ... });` 結束為止，整段換成：
```js
    const filename = `userProfile/${new Date().toISOString()}-${file.originalname}`;
    const publicUrl = await storage.upload(file.buffer, filename, file.mimetype);

    await pool.query('update public."user" set avatar_url = $1 where user_id = $2', [
      publicUrl,
      user.id,
    ]);

    // [HTTP 200] 呈現資料
    resStatus({
      res: res,
      status: 200,
      message: '更新成功',
      dbdata: {
        avatar_url: publicUrl,
      },
    });
```
（外層的 `try { const user = req.user; const file = req.file; ... } catch` 保持原樣。）

`backend/src/server.js`：在 `app.use(express.static(path.join(__dirname, 'public')));` 下一行加上：
```js
app.use('/uploads', express.static(require('./utils/storage/local').UPLOAD_DIR));
```

- [ ] **Step 5: 確認測試通過**

```bash
docker compose restart backend && sleep 8
uv run pytest tests/test_health.py tests/test_storage.py -v
```
預期：3 個測試全部 PASS。

- [ ] **Step 6: Review Focus #2，確認選了 firebase driver 但沒有金鑰時，模組載入不會 crash**

```bash
docker compose exec -e STORAGE_DRIVER=firebase backend node -e "
require('./src/controllers/userProfile');
require('./src/utils/firebaseUpload');
const s = require('./src/utils/storage');
s.upload(Buffer.from('x'), 'a.png', 'image/png').then(() => console.log('UNEXPECTED'), (e) => console.log('rejected:', e.message));
"
```
預期輸出：`rejected: Missing FIREBASE_SERVICE_ACCOUNT environment variable`，而且沒有出現 uncaught exception。

- [ ] **Step 7: Commit 綠燈**

```bash
git -C backend add src/config/firebase.js src/utils/storage src/utils/firebaseUpload.js src/controllers/userProfile.js src/server.js
git -C backend commit -m "feat: 🟢 storage adapter（local/firebase），firebase 改為延遲初始化"
```

---

### Task 5: Mailer adapter + Mailpit

**Files:**
- Modify: `docker-compose.yml`（新增 `mailpit` 服務，並加進 backend 的 `depends_on`）
- Create: `backend/src/utils/mailer.js`
- Modify: `backend/src/controllers/userinfo.js:3`、`:259-275`
- Modify: `backend/package.json`、`backend/package-lock.json`（加入 nodemailer）
- Test: `tests/test_mail.py`

**Interfaces:**
- Consumes: `.env` 的 `MAIL_DRIVER`、`SMTP_HOST`、`SMTP_PORT`、`MAIL_FROM`；conftest 的 `api`、`make_user`、`MAILPIT_BASE`。
- Produces: `require('./utils/mailer')` → `{ send({ to, subject, html }): Promise<void> }`。compose 的服務名稱 `mailpit`（SMTP :1025，Web / API :8025）。

- [ ] **Step 1: 在 `docker-compose.yml` 加上 mailpit**

`services:` 底下新增：
```yaml
  mailpit:
    image: axllent/mailpit:v1.20
    ports:
      - '8025:8025'
      - '1025:1025'
```
在 backend 的 `depends_on` 加上：
```yaml
      mailpit:
        condition: service_started
```

- [ ] **Step 2: 寫失敗的測試 `tests/test_mail.py`**

```python
"""忘記密碼的信要寄到 Mailpit（本機替代 SendGrid）。"""
import time

import requests

from conftest import MAILPIT_BASE


def _messages_to(address):
    r = requests.get(
        f"{MAILPIT_BASE}/api/v1/search", params={"query": f"to:{address}"}, timeout=10
    )
    r.raise_for_status()
    return r.json()["messages"]


def _wait_for_messages(address, timeout=10):
    deadline = time.time() + timeout
    while time.time() < deadline:
        messages = _messages_to(address)
        if messages:
            return messages
        time.sleep(0.5)
    return []


def test_forget_password_sends_reset_mail(api, make_user):
    user = make_user()

    r = api.post("/api/v1/auth/userinfo/forgetpw", json={"email": user["email"]})

    assert r.status_code == 200, r.text
    messages = _wait_for_messages(user["email"])
    assert len(messages) == 1
    assert messages[0]["Subject"] == "TripEasy 密碼重設連結"
    detail = requests.get(
        f"{MAILPIT_BASE}/api/v1/message/{messages[0]['ID']}", timeout=10
    ).json()
    assert "resetpw?token=" in detail["HTML"]
```

- [ ] **Step 3: 確認測試失敗，然後 commit 紅燈**

```bash
docker compose up -d mailpit
uv run pytest tests/test_mail.py -v 2>&1 | tee docs/reports/evidence/phase-0/task5-mail-red.txt
```
預期：FAIL。response 是 500，因為 SendGrid 的 API key 是空的，`sgMail.send` 會丟出錯誤。

```bash
git add docker-compose.yml tests/test_mail.py docs/reports/evidence/phase-0/task5-mail-red.txt
git commit -m "test: 🔴 忘記密碼信應寄到 Mailpit"
```

- [ ] **Step 4: 安裝 nodemailer（只更新 lockfile，用 Node 22.14.0）**

```bash
docker run --rm -u "$(id -u):$(id -g)" -e npm_config_cache=/tmp/.npm \
  -v "$PWD/backend":/app -w /app node:22.14.0 npm install nodemailer@^6.9.16 --package-lock-only
grep '"nodemailer"' backend/package.json
```

- [ ] **Step 5: 建立 `backend/src/utils/mailer.js`**

```js
// mailer adapter：依 MAIL_DRIVER 切換 smtp（本機 Mailpit）/ sendgrid（預設，維持原本行為）
const nodemailer = require('nodemailer');
const sgMail = require('@sendgrid/mail');

let transporter;

async function send({ to, subject, html }) {
  const driver = process.env.MAIL_DRIVER || 'sendgrid';
  const from = process.env.MAIL_FROM || process.env.SENDGRID_FROM_EMAIL;

  if (driver === 'smtp') {
    transporter =
      transporter ||
      nodemailer.createTransport({
        host: process.env.SMTP_HOST,
        port: Number(process.env.SMTP_PORT || 1025),
        secure: false,
      });
    await transporter.sendMail({ from, to, subject, html });
    return;
  }

  if (driver === 'sendgrid') {
    sgMail.setApiKey(process.env.SENDGRID_API_KEY);
    await sgMail.send({ to, from, subject, html });
    return;
  }

  throw new Error(`Unknown MAIL_DRIVER: ${driver}`);
}

module.exports = { send };
```

- [ ] **Step 6: 修改 `backend/src/controllers/userinfo.js`**

- 第 3 行 `const sgMail = require('@sendgrid/mail');` 換成 `const mailer = require('../utils/mailer');`
- `post_user_forgetPW` 裡刪掉 `sgMail.setApiKey(process.env.SENDGRID_API_KEY);`
- 把 `await sgMail.send({ to: email, from: process.env.SENDGRID_FROM_EMAIL, subject: ..., html: ... });` 換成下面這段，subject 和 html 的內容照原樣保留：
```js
    await mailer.send({
      to: email,
      subject: 'TripEasy 密碼重設連結',
      html: `
                <p>您好，親愛的用戶 : </p><br>
                <p>請於 15 分鐘內點擊以下連結以重設密碼：</p><br>
                <a href="${resetUrl}">連結 : ${resetUrl}</a>
                <p>若您未曾申請重設密碼，請忽略此信件，謝謝。</p>
            `,
    });
```
- 確認檔案裡沒有其他地方用到 `sgMail`：`grep -n sgMail backend/src/controllers/userinfo.js` 應該沒有輸出

- [ ] **Step 7: 重建 backend（node_modules 在 image 裡），確認測試通過**

```bash
docker compose up -d --build --renew-anon-volumes backend && sleep 10
uv run pytest tests/test_mail.py tests/test_health.py -v
```
預期：PASS。

- [ ] **Step 8: Commit 綠燈**

```bash
git -C backend add package.json package-lock.json src/utils/mailer.js src/controllers/userinfo.js
git -C backend commit -m "feat: 🟢 mailer adapter（smtp/sendgrid），本機寄到 Mailpit"
```

---

### Task 6: async 錯誤處理

**Files:**
- Modify: `backend/src/server.js`（第 1 行之後）
- Modify: `backend/package.json`、`backend/package-lock.json`（加入 express-async-errors）
- Test: `tests/test_async_errors.py`

**Interfaces:**
- Consumes: conftest 的 `api`、`make_user`、`auth_header`。
- Produces: 任何 async route handler 拋出的錯誤（包括在 `try` 外面發生的）都會交給 `server.js` 既有的 500 error handler，回傳 `{"status": "error", "message": "伺服器錯誤"}`。

- [ ] **Step 1: 寫失敗的測試 `tests/test_async_errors.py`**

```python
"""在 try 外面 reject 的 async handler，要回 500，而且 server 不能掛掉。

案例：POST /user/newebpay/payment 帶空的 body，
newebpay.js:59 在 try 外面執行 order_items.reduce，會拋出 TypeError。
"""
from conftest import auth_header


def test_rejection_outside_try_returns_500_and_server_survives(api, make_user):
    user = make_user()

    r = api.post(
        "/api/v1/user/newebpay/payment", headers=auth_header(user), json={}, timeout=5
    )

    assert r.status_code == 500
    assert r.json()["status"] == "error"
    assert api.get("/api/v1/health").status_code == 200
```

- [ ] **Step 2: 確認測試失敗，然後 commit 紅燈**

```bash
uv run pytest tests/test_async_errors.py -v 2>&1 | tee docs/reports/evidence/phase-0/task6-async-red.txt
docker compose logs backend --tail=20
```
預期：FAIL，錯誤是 `ReadTimeout` 或 `ConnectionError`。log 裡會看到 `TypeError: Cannot read properties of undefined (reading 'reduce')`，nodemon 顯示 `app crashed`。

紅燈之後 backend 已經掛掉了，要先重啟：`docker compose restart backend`

```bash
git add tests/test_async_errors.py docs/reports/evidence/phase-0/task6-async-red.txt
git commit -m "test: 🔴 try 外的 async rejection 會讓 server crash"
```

- [ ] **Step 3: 安裝套件，修改 server.js**

```bash
docker run --rm -u "$(id -u):$(id -g)" -e npm_config_cache=/tmp/.npm \
  -v "$PWD/backend":/app -w /app node:22.14.0 npm install express-async-errors@^3.1.1 --package-lock-only
```

在 `backend/src/server.js` 的第 1 行 `const express = require('express');` 下面加上：
```js
// Express 4 不會接住 async handler 的 rejection；這個套件把它導到既有的 error handler
require('express-async-errors');
```

- [ ] **Step 4: 重建，確認測試通過**

```bash
docker compose up -d --build --renew-anon-volumes backend && sleep 10
uv run pytest tests/ -v
```
預期：到目前為止的測試全部 PASS。

- [ ] **Step 5: Commit 綠燈**

```bash
git -C backend add package.json package-lock.json src/server.js
git -C backend commit -m "fix: 🟢 async handler 的 rejection 導向 error handler，不再讓 server crash"
```

---

### Task 7: Google OAuth 網址可設定 + mock-oauth2-server 可行性測試

這個 Task 是 **spike**。目標是對「本機能不能用 mock-oauth2-server 替代 Google」得出結論，不要求整條登入流程都綠燈。

**Files:**
- Modify: `docker-compose.yml`（新增 `mock-oauth` 服務）
- Modify: `backend/src/middlewares/userinfo/index.js:146`、`:163`
- Test: `tests/test_oauth_spike.py`
- Create: `docs/reports/evidence/phase-0/task7-oauth-spike.md`（結論）

**Interfaces:**
- Consumes: `.env` 的 `GOOGLE_TOKEN_URL`、`GOOGLE_USERINFO_URL`、`GOOGLE_CLIENT_ID`、`GOOGLE_CLIENT_SECRET`、`GOOGLE_REDIRECT_URI`；conftest 的 `api`、`db`、`delete_user`、`MOCK_OAUTH_BASE`。
- Produces: compose 的服務名稱 `mock-oauth`（容器內 :8080，host 端 :8090），issuer id 為 `google`。mock 使用者的 email 是 `mock.user@example.com`，name 是 `Mock 使用者`，sub 是 `mock-google-001`。

- [ ] **Step 1: 在 `docker-compose.yml` 加上 mock-oauth**

```yaml
  mock-oauth:
    image: ghcr.io/navikt/mock-oauth2-server:2.1.10
    ports:
      - '8090:8080'
    environment:
      JSON_CONFIG: >-
        {"interactiveLogin": false,
         "tokenCallbacks": [{"issuerId": "google", "tokenExpiry": 3600,
           "requestMappings": [{"requestParam": "grant_type", "match": "*",
             "claims": {"sub": "mock-google-001", "email": "mock.user@example.com",
                        "name": "Mock 使用者", "picture": "https://example.com/mock.png"}}]}]}
```
在 backend 的 `depends_on` 加上 `mock-oauth: { condition: service_started }`。

- [ ] **Step 2: 寫測試 `tests/test_oauth_spike.py`**

```python
"""Spike：mock-oauth2-server 能不能替代 Google，讓 backend 的 Google 登入流程在本機跑通。"""
import os
from urllib.parse import parse_qs, urlparse

import pytest
import requests

from conftest import MOCK_OAUTH_BASE, delete_user

MOCK_EMAIL = "mock.user@example.com"


def _get_code():
    r = requests.get(
        f"{MOCK_OAUTH_BASE}/google/authorize",
        params={
            "client_id": os.environ["GOOGLE_CLIENT_ID"],
            "redirect_uri": os.environ["GOOGLE_REDIRECT_URI"],
            "response_type": "code",
            "scope": "openid email profile",
            "state": "p0",
        },
        allow_redirects=False,
        timeout=10,
    )
    assert r.status_code == 302, r.text
    return parse_qs(urlparse(r.headers["Location"]).query)["code"][0]


@pytest.fixture
def clean_mock_user(db):
    def _clean():
        row = db.execute('SELECT user_id FROM "user" WHERE email = %s', (MOCK_EMAIL,)).fetchone()
        if row:
            delete_user(db, str(row[0]))

    _clean()
    yield
    _clean()


def test_mock_oauth_issues_google_like_claims():
    code = _get_code()
    token = requests.post(
        f"{MOCK_OAUTH_BASE}/google/token",
        data={
            "grant_type": "authorization_code",
            "code": code,
            "client_id": os.environ["GOOGLE_CLIENT_ID"],
            "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
            "redirect_uri": os.environ["GOOGLE_REDIRECT_URI"],
        },
        timeout=10,
    )
    assert token.status_code == 200, token.text

    info = requests.get(
        f"{MOCK_OAUTH_BASE}/google/userinfo",
        headers={"Authorization": f"Bearer {token.json()['access_token']}"},
        timeout=10,
    ).json()

    assert info["sub"] == "mock-google-001"
    assert info["email"] == MOCK_EMAIL
    assert info["name"] == "Mock 使用者"


def test_backend_google_login_via_mock(api, db, clean_mock_user):
    code = _get_code()

    r = api.post("/api/v1/auth/userinfo/login/google", json={"code": code})

    assert r.status_code == 200, r.text
    row = db.execute(
        'SELECT name, login_method FROM "user" WHERE email = %s', (MOCK_EMAIL,)
    ).fetchone()
    assert row == ("Mock 使用者", 2)
```

- [ ] **Step 3: 確認失敗，然後 commit 紅燈**

```bash
docker compose up -d mock-oauth && sleep 5
uv run pytest tests/test_oauth_spike.py -v 2>&1 | tee docs/reports/evidence/phase-0/task7-oauth-red.txt
```
預期：
- `test_mock_oauth_issues_google_like_claims` PASS。如果這個測試 FAIL，代表 mock 的設定有問題，先修 `JSON_CONFIG`。修兩次都不行的話，升級 Opus。
- `test_backend_google_login_via_mock` FAIL。backend 還在打真的 Google，會拿到 400 或 500。

```bash
git add docker-compose.yml tests/test_oauth_spike.py docs/reports/evidence/phase-0/task7-oauth-red.txt
git commit -m "test: 🔴 Google 登入改走 mock-oauth2-server（spike）"
```

- [ ] **Step 4: 讓 backend 的 OAuth 網址可以設定**

`backend/src/middlewares/userinfo/index.js`：
- :146 `'https://oauth2.googleapis.com/token',` 換成 `process.env.GOOGLE_TOKEN_URL || 'https://oauth2.googleapis.com/token',`
- :163 `axios.get('https://www.googleapis.com/oauth2/v3/userinfo', {` 換成 `axios.get(process.env.GOOGLE_USERINFO_URL || 'https://www.googleapis.com/oauth2/v3/userinfo', {`

```bash
docker compose up -d backend && sleep 8
uv run pytest tests/test_oauth_spike.py -v
docker compose logs backend --tail=40
```

- [ ] **Step 5: 判斷 spike 結果（三種情況擇一）**

- **A. 兩個測試都 PASS**：結論是「可行」。
- **B. 第二個測試 FAIL，而且 backend 的 log 有 `value too long for type character varying(255)`**：mock 的 access token 是 JWT，長度超過 `socialLogin.provider_token` 的 VARCHAR(255)。這是 schema 的問題，不是 mock 不可行。**P0 不改 schema**（歸到 P2），在第二個測試加上：
  ```python
  @pytest.mark.xfail(strict=True, reason="socialLogin.provider_token 為 VARCHAR(255)，放不下 JWT access token；P2 以 migration 修正")
  ```
  結論是「可行，但有已知的 schema 限制」。
- **C. 其他錯誤**（例如 token 交換失敗、issuer 不符、userinfo 回 401）：照 systematic-debugging 的流程查。修兩次還是不行，就升級 Opus。最後還是不行的話，結論寫「不可行」，**停下來回報使用者**，討論改用免費的 Google 測試 client。

把結論寫進 `docs/reports/evidence/phase-0/task7-oauth-spike.md`，包含：
- 結果是 A、B、C 的哪一種
- 關鍵的 log 片段
- 對 P2 的影響

- [ ] **Step 6: Commit**

```bash
git -C backend add src/middlewares/userinfo/index.js
git -C backend commit -m "feat: 🟢 Google OAuth token/userinfo 網址可由環境變數設定"
git add tests/test_oauth_spike.py docs/reports/evidence/phase-0/task7-oauth-spike.md
git commit -m "docs: mock-oauth2-server 可行性結論"
```

---

### Task 8: frontend 進 compose、API base 和 Google 設定改讀環境變數、CORS

**Files:**
- Modify: `docker-compose.yml`（新增 `frontend` 服務）
- Modify: `frontend/.env.development`, `frontend/.env.production`, `frontend/.env.example`
- Modify: `frontend/src/views/admin/loginPage.vue:153-160`
- Test: `tests/test_frontend.py`

**Interfaces:**
- Consumes: conftest 的 `api`、`FRONTEND_BASE`；`.env` 的 `FRONTEND_PATH=http://localhost:5173`（Task 3）。
- Produces: compose 的服務名稱 `frontend`（:5173）。前端的環境變數有 `VITE_API_BASE`、`VITE_Redirect_BASE`、`VITE_GOOGLE_CLIENT_ID`、`VITE_GOOGLE_AUTH_URL`。

- [ ] **Step 1: 在 `docker-compose.yml` 加上 frontend**

```yaml
  frontend:
    image: node:22.14.0
    working_dir: /app
    command: sh -c "npm ci && npm run dev -- --host 0.0.0.0 --port 5173"
    ports:
      - '5173:5173'
    volumes:
      - ./frontend:/app
      - frontend_node_modules:/app/node_modules
    depends_on:
      backend:
        condition: service_healthy
    healthcheck:
      test: ['CMD', 'curl', '-fsS', 'http://localhost:5173/']
      interval: 5s
      retries: 60
```
在頂層的 `volumes:` 加上 `frontend_node_modules:`。

- [ ] **Step 2: 寫測試 `tests/test_frontend.py`**

```python
"""前端 dev server 可以存取、API base 已經注入、CORS 只允許前端的 origin。"""
import requests

from conftest import FRONTEND_BASE


def test_frontend_dev_server_serves_app():
    r = requests.get(f"{FRONTEND_BASE}/", timeout=10)
    assert r.status_code == 200
    assert 'id="app"' in r.text


def test_frontend_api_base_points_to_backend():
    # Vite dev server 會把 import.meta.env 換成實際的值，直接看轉譯後的 api.js
    r = requests.get(f"{FRONTEND_BASE}/src/utils/api.js", timeout=10)
    assert r.status_code == 200
    assert "http://localhost:3000" in r.text


def test_cors_allows_frontend_origin(api):
    r = api.options(
        "/api/v1/health",
        headers={
            "Origin": FRONTEND_BASE,
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "authorization,content-type",
        },
    )
    assert r.status_code == 204
    assert r.headers["Access-Control-Allow-Origin"] == FRONTEND_BASE
    assert r.headers["Access-Control-Allow-Credentials"] == "true"


def test_cors_rejects_unknown_origin(api):
    r = api.get("/api/v1/health", headers={"Origin": "http://evil.example.com"})
    assert "Access-Control-Allow-Origin" not in r.headers
    assert api.get("/api/v1/health").status_code == 200
```

- [ ] **Step 3: 確認失敗，然後 commit 紅燈**

```bash
docker compose up -d frontend
# 第一次要 npm ci，最多等 3 分鐘
for i in $(seq 1 90); do curl -fsS -o /dev/null http://localhost:5173/ && break; sleep 2; done
uv run pytest tests/test_frontend.py -v 2>&1 | tee docs/reports/evidence/phase-0/task8-frontend-red.txt
```
預期：`test_frontend_api_base_points_to_backend` FAIL，因為 `VITE_API_BASE` 還沒設定。另外三個 PASS，它們是回歸釘，保護既有的行為。

```bash
git add docker-compose.yml tests/test_frontend.py docs/reports/evidence/phase-0/task8-frontend-red.txt
git commit -m "test: 🔴 前端 VITE_API_BASE 未設定"
```

- [ ] **Step 4: 修改前端的環境變數**

`frontend/.env.development`（整份）：
```
VITE_BASE_URL=/
VITE_API_BASE=http://localhost:3000
VITE_Redirect_BASE=http://localhost:5173/
VITE_GOOGLE_CLIENT_ID=tripeasy-local
VITE_GOOGLE_AUTH_URL=http://localhost:8090/google/authorize
```

`frontend/.env.production`：在原本的 `VITE_BASE_URL=/frontend/` 後面加上下面這行，維持目前正式環境的行為。部署的其他變數等 P7 再決定。
```
VITE_GOOGLE_CLIENT_ID=148755362421-us8l17s3ukf88mj23kbs5vj2i8lgu8nk.apps.googleusercontent.com
```

`frontend/.env.example`：在最後加上：
```
VITE_GOOGLE_CLIENT_ID=google_client_id
VITE_GOOGLE_AUTH_URL=https://accounts.google.com/o/oauth2/v2/auth
```

- [ ] **Step 5: `loginPage.vue` 的 `GoogleAPI()` 改讀環境變數**

把 `frontend/src/views/admin/loginPage.vue` 的 `GoogleAPI()` 函式本體（:153-160）換成：
```js
    async GoogleAPI() {
      const googleClientId = import.meta.env.VITE_GOOGLE_CLIENT_ID;
      const redirectUri = import.meta.env.VITE_Redirect_BASE;
      const authUrl =
        import.meta.env.VITE_GOOGLE_AUTH_URL || 'https://accounts.google.com/o/oauth2/v2/auth';

      const url = `${authUrl}?client_id=${encodeURIComponent(googleClientId)}&redirect_uri=${encodeURIComponent(redirectUri)}&response_type=code&scope=openid%20email%20profile`;
      window.location.href = url;
    },
```
確認 client_id 已經不寫死在程式碼裡：`grep -n "148755362421" frontend/src -r` 應該沒有輸出。

- [ ] **Step 6: 確認測試通過**

```bash
docker compose restart frontend
for i in $(seq 1 60); do curl -fsS -o /dev/null http://localhost:5173/ && break; sleep 2; done
uv run pytest tests/ -v
```
預期：全部 PASS。如果 Task 7 走的是情況 B，`test_backend_google_login_via_mock` 會顯示 XFAIL。

- [ ] **Step 7: Commit 綠燈（frontend repo）**

```bash
git -C frontend add .env.development .env.production .env.example src/views/admin/loginPage.vue
git -C frontend commit -m "feat: 🟢 API base 與 Google OAuth 設定改讀環境變數"
```

---

### Task 9: `scripts/ci.sh` 與 GitHub Actions

**Files:**
- Create: `scripts/ci.sh`, `.github/workflows/ci.yml`

**Interfaces:**
- Consumes: `refs.env`（Task 1）、整份 compose、`tests/`。
- Produces: `scripts/ci.sh`。本機和 CI 執行的是同一份腳本，結束碼就是 pytest 的結果。

- [ ] **Step 1: 建立 `scripts/ci.sh`**

```bash
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

uv sync --frozen
uv run pytest -v
```

```bash
chmod +x scripts/ci.sh
```

- [ ] **Step 2: 建立 `.github/workflows/ci.yml`**

```yaml
name: ci

on:
  push:
  pull_request:
  workflow_dispatch:

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: 讀取 refs.env
        run: cat refs.env >> "$GITHUB_ENV"

      - uses: actions/checkout@v4
        with:
          repository: nohungry/tripeasy-backend
          ref: ${{ env.BACKEND_REF }}
          path: backend

      - uses: actions/checkout@v4
        with:
          repository: nohungry/tripeasy-frontend
          ref: ${{ env.FRONTEND_REF }}
          path: frontend

      - uses: astral-sh/setup-uv@v3

      - name: 啟動服務並測試
        run: scripts/ci.sh

      - name: 收集 compose log
        if: failure()
        run: docker compose logs --no-color > compose-logs.txt

      - uses: actions/upload-artifact@v4
        if: failure()
        with:
          name: compose-logs
          path: compose-logs.txt
```

- [ ] **Step 3: 本機從乾淨的狀態跑一次**

```bash
docker compose down -v
scripts/ci.sh 2>&1 | tail -40
```
預期：四個服務都印出 `✅`，pytest 全部 PASS（可能有 1 個 XFAIL），結束碼是 0。

- [ ] **Step 4: Review Focus #1，保留 volume 再跑一次**

```bash
docker compose down        # 不加 -v
scripts/ci.sh 2>&1 | tail -20
docker compose logs flyway | grep -i "up to date\|No migration necessary"
```
預期：pytest 全部 PASS，Flyway 的 log 顯示 schema 已是最新版（`Schema ... is up to date. No migration necessary.`）。

- [ ] **Step 5: Commit**

```bash
git add scripts/ci.sh .github/workflows/ci.yml
git commit -m "ci: 本機與 GitHub Actions 共用的 ci.sh（依 refs.env checkout 三個 repo）"
```

---

### Task 10: 階段收尾：README、P0 報告、合併與 tag

**Files:**
- Modify: `README.md`
- Create: `docs/reports/phase-0.md`
- Modify: `refs.env`（改成指向 tag）

- [ ] **Step 1: 補完 `README.md` 的「快速開始」**

把「（P0 完成後補上）」換成：
````markdown
需要 Docker（含 Compose v2）和 [uv](https://docs.astral.sh/uv/)。

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
````

- [ ] **Step 2: 寫 `docs/reports/phase-0.md` 初稿**

照 spec 第 5 節的範本，資料來源如下：
- **摘要**：`git log --oneline main..phase-0`（三個 repo 各跑一次），加上 pytest 的測試數量（P0 開始前是 0）
- **1. 問題與修正**：Task 3、4、5、6、7、8 的每個紅燈各寫一小節，內容依序是現象、根因（附原始碼行號）、紅燈輸出（引用 `evidence/phase-0/*-red.txt`）、修正 diff（`git -C backend show <sha> --stat` 加上關鍵片段）、綠燈結果
- **2. Vibe coding 工作流**：用了哪些 skill，包括 brainstorming、writing-plans、subagent-driven-development。另外寫 Fable vs Opus 每個 Task 的 review 對照表，以及升級 Opus 的紀錄，沒有就寫「無」
- **3. 測試方法**：conftest 的設計（`Api` 為什麼要預設 timeout、`make_user` 怎麼清理資料、`auth_header`）、紅燈和綠燈分開 commit 的做法、`ci.sh` 本機和 CI 共用一份
- **4. 操作指南**：README 的快速開始，再加上手動體驗的步驟：
  - 打開 Mailpit 看忘記密碼信
  - 打開 `/uploads` 的圖片
  - 看 mock-oauth 的 discovery 文件
- **附錄**：變更檔案清單，以及本計畫「不在 P0 修的已知問題」整張表，再加上 Task 7 的 spike 結論

- [ ] **Step 3: 請使用者審閱報告**

**停下來**，請使用者閱讀 `docs/reports/phase-0.md`，依回饋修改，直到使用者確認定稿。

- [ ] **Step 4: 合併、打 tag（只在本機）**

```bash
git -C backend switch main && git -C backend merge --no-ff phase-0 -m "Merge phase-0: P0 地基"
git -C backend branch -d phase-0 && git -C backend tag phase-0
git -C frontend switch dev && git -C frontend merge --no-ff phase-0 -m "Merge phase-0: P0 地基"
git -C frontend branch -d phase-0 && git -C frontend tag phase-0
```
先刪掉 `phase-0` 分支再打同名的 tag，這樣 `phase-0` 這個名字就不會有歧義。`refs.env` 的內容不用改，`phase-0` 現在會解析成 tag。確認：
```bash
git -C backend rev-parse --verify refs/tags/phase-0 && git -C frontend rev-parse --verify refs/tags/phase-0
scripts/ci.sh 2>&1 | tail -5
git add README.md docs/reports/ refs.env
git commit -m "docs: P0 階段報告與版本對照"
git switch main && git merge --no-ff phase-0 -m "Merge phase-0: P0 地基"
```
預期：`ci.sh` 全綠之後，才 merge 回總覽 repo 的 main。

- [ ] **Step 5: 詢問使用者對外的動作**

**停下來詢問使用者**，得到明確同意後才執行：
1. 在 GitHub 建立 `nohungry/tripeasy` repo（public 或 private？）
2. push backend 的 `main` 和 tag `phase-0` 到 fork `origin`
3. push frontend 的 `dev` 和 tag `phase-0` 到 fork `origin`
4. push 總覽 repo，確認 GitHub Actions 是綠燈。CI 需要 backend 和 frontend 這兩個 fork 是 public，或另外設定 token

---

## P0 完成標準（對照 spec 2 節）

- [ ] `scripts/ci.sh` 從乾淨狀態（`down -v`）和保留 volume 兩種情況都是全綠 → Task 9
- [ ] `/health`、CORS 測試是綠的 → Task 4、Task 8
- [ ] mock OAuth 的可行性有結論 → Task 7
- [ ] P0 報告由使用者確認定稿 → Task 10
- [ ] 每個 Task 都經過 Fable 和 Opus 的雙 review，沒有還沒處理的 Critical 或 Important 問題
