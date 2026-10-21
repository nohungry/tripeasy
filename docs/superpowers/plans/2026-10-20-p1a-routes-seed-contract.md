# P1a 路由修正、Seed、DB 契約 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修好 product router 的兩個路由順序 bug；把團隊留下的 fakedata 變成可重跑、能真的登入的 Flyway seed；從程式碼反推出 21 個缺少的 DB 物件，寫成 `docs/db-contract.md`，經雙模型審核和使用者確認語意後定案。

**Architecture:** P1 拆成兩份計畫。本計畫（P1a）做完時，契約已經定案，但還沒有任何 view 或函式。下一份計畫（P1b）會依照定案的契約寫 `V3__views_functions.sql`、三層測試和補資料，最後合併、打 tag、push。拆開的原因是 spec 3.1 規定契約要先審核、確認語意，才能寫 SQL；SQL 計畫要等契約定案後才寫得出完整的程式碼。P1a 和 P1b 共用同一組 `phase-1` 分支，P1a 結束時**不合併**。

**Tech Stack:** Express 4.21、PostgreSQL 15、Flyway 10.20.1（repeatable migration）、Python 3.13 / uv / pytest 8.3.3 / requests / psycopg 3 / PyJWT。

**Spec:** `docs/superpowers/specs/2026-10-15-tripeasy-rebuild-design.md`（第 3.0、3.1、3.2 節為本計畫範圍；3.1 第 4 步、3.2 的「補資料量」「補 payment」、3.3 留給 P1b）

## Global Constraints

- 所有 Node 容器一律使用 `node:22.14.0`（`backend/.nvmrc`）。
- **沿用既有程式碼**：只改本計畫列出的檔案；只做本計畫列出的重構（Task 1 的 router 拆分），其他重構和清掉沒用到的套件都不做（重構規則見 spec §0）。本計畫不新增任何 npm 或 Python 套件。
- **controller 不改**（spec 3.1 第 4 步）。本計畫只動 `routes/` 和 `server.js` 的路由掛載。
- seed **只在本機和展示環境載入**：compose 的 Flyway 用 `-locations=filesystem:/flyway/sql,filesystem:/flyway/seed`；正式環境只給 migrations。
- 環境變數只有一個來源：根目錄的 `.env`（由 `.env.example` 複製）。
- 分支：backend 從 `main`、總覽 repo 從 `main`，各開 `phase-1`。frontend 在 P1a 不動，`refs.env` 的 `FRONTEND_REF` 維持 `phase-0`。**總覽 repo 的 main 必須維持全綠**，紅燈只會出現在 `phase-1` 上。
- commit 規則：紅燈測試單獨一個 commit（`test: ... 🔴`），修正另外一個 commit（`fix:/feat: ... 🟢`）。每個紅燈 commit 都要把 pytest 的失敗輸出存到 `docs/reports/evidence/phase-1/<task>-red.txt`，存檔前把本機絕對路徑換成相對路徑（指令裡的 `sed "s#$PWD/##g; s#$PWD#.#g"`）。
- commit 訊息結尾要加上 `Co-Authored-By` 行，註明實際執行的模型。
- **不 push、不合併、不打 tag**。這些在 P1b 結尾先問使用者。
- 模型分工：每個 Task 由 Sonnet 實作。同一個 Task 連續修兩次還是紅燈，或遇到設計層級的問題，就升級 Opus。每個 Task 的 review 由 Fable 和 Opus 平行進行，再比對兩邊的結果。
- 所有指令都在總覽 repo 根目錄 `/home/nohungry/project/tripeasy` 執行，除非步驟另有註明。只用明確路徑 `git add`，不用 `git add .` / `-A`；`.claude/` 不 commit。

## Review Focus

1. **DB volume 還在，`R__seed.sql` 內容又改過**：Flyway 會重跑 seed，所有 INSERT 都撞到既有資料。這時只能略過，不能讓 migrate 失敗，整套服務也不能因此起不來。→ Task 2 測試 `test_seed_is_rerunnable`
2. **用 seed 帳號真的登入**：seed 的密碼 hash 必須是真的 bcrypt，用 `.env.example` 註解寫的明文密碼要能登入成功。→ Task 3 測試 `test_seed_user_can_login`
3. **seed 的 admin 打 admin API**：角色要跟 `authRole('admin')` / `authRole('User')` 的大小寫一致，不能因為 fakedata 的 `'user'` 被擋成 403。→ Task 3 測試 `test_seed_admin_passes_authorize_roles`
4. **拆開 router 之後的前綴交叉**：admin 的路由不能再出現在 `/user/product/search` 底下，公開的路由也不能出現在 `/admin/product` 底下。→ Task 1 測試 `test_admin_routes_not_exposed_under_user_prefix`、`test_public_routes_not_exposed_under_admin_prefix`
5. **seed 載入的那一天就是「今天」**：行程日期和優惠券期限要以今天為基準，落在未來，不能一載入就是過期資料，否則訂購和折扣的流程根本走不到。→ Task 3 測試 `test_seed_dates_are_relative_to_today`

---

## 檔案結構

| 檔案 | 責任 | Task |
|---|---|---|
| `backend/src/routes/product.js` | 只留公開的商品路由（編號 22–25） | 1 |
| `backend/src/routes/product_admin.js`（新） | 管理者的商品路由（編號 46–51），`PATCH /status` 排在 `/:tour_id` 之前 | 1 |
| `backend/src/server.js:16`、`:113` | `/admin/product` 改掛 admin router | 1 |
| `tests/test_product_routes.py`（新） | 路由修正的測試 | 1 |
| `db/seed-build/tripeasy_fakedata.sql`（新） | fakedata 原檔（只把 CRLF 轉成 LF），記錄來源 | 2 |
| `db/seed-build/build_seed.py`（新） | 把原檔轉成 seed 的腳本，每個轉換都 assert 次數 | 2、3 |
| `db/seed/R__seed.sql`（新，由腳本產生） | Flyway repeatable migration；`db/seed/` 只放這一個檔 | 2、3 |
| `db/seed-images/*.svg`（新） | 5 張本機佔位圖 | 3 |
| `docker-compose.yml` | Flyway 多一個 seed location；backend 掛上佔位圖 | 2、3 |
| `.env.example` | seed 帳號和明文密碼的註解 | 3 |
| `tests/conftest.py` | 新增 `tx` fixture（不 commit、結束一律 rollback） | 2 |
| `tests/test_seed.py`（新） | seed 的載入、重跑、資料修正測試 | 2、3 |
| `docs/db-contract.md`（新） | 21 個物件的契約 | 4、5、6、7 |

---

### Task 1: product router 拆成 admin / public（spec 3.0）

**Files:**
- Create: `backend/src/routes/product_admin.js`
- Modify: `backend/src/routes/product.js`（整份）
- Modify: `backend/src/server.js:16`、`:113`
- Modify: `refs.env`
- Test: `tests/test_product_routes.py`

**Interfaces:**
- Consumes: conftest 的 `api`、`make_user(role=...)`、`auth_header`。backend 既有的 404 handler 回 `{"status": "false", "message": "找不到此網站"}`。
- Produces:
  - 公開路由：`/api/v1/user/product/search`（`GET /`、`GET /:tour_id`、`GET /:tour_id/reviews`、`GET /:tour_id/hidden-shares`）。
  - 管理者路由：`/api/v1/admin/product`（`POST /add`、`GET /`、`PATCH /status`、`GET /:tour_id`、`PATCH /:tour_id`、`DELETE /`）。

- [ ] **Step 1: 開分支、`refs.env` 指向 phase-1**

```bash
git switch -c phase-1
git -C backend switch -c phase-1
```

`refs.env` 改成：
```
BACKEND_REF=phase-1
FRONTEND_REF=phase-0
```
```bash
git add refs.env docs/superpowers/plans/2026-10-20-p1a-routes-seed-contract.md
git commit -m "chore: 開始 P1，refs.env 指向 backend phase-1"
```

- [ ] **Step 2: 寫失敗的測試 `tests/test_product_routes.py`**

```python
"""spec 3.0：product router 同時掛在 user 和 admin 兩個前綴，造成兩個路由順序 bug。

- admin 的 GET / 和 GET /:tour_id 宣告在公開版前面 → 訪客查商品拿到 401
- PATCH /:tour_id 宣告在 PATCH /status 前面 → 上架 API 永遠走不到
"""
import uuid

from conftest import auth_header

PUBLIC = "/api/v1/user/product/search"
ADMIN = "/api/v1/admin/product"
NOT_FOUND_ROUTE = "找不到此網站"  # server.js 的 404 handler


def test_guest_can_reach_public_tour_detail(api):
    # detailsSchema 規定 lang 必填
    r = api.get(f"{PUBLIC}/{uuid.uuid4()}", params={"lang": "zh-TW"})
    # 走到公開版的 middleware：查無此行程，而不是被 admin 的 auth 擋成 401
    assert r.status_code == 404, r.text
    assert r.json()["message"] == "查無此旅遊項目"


def test_guest_tour_list_is_not_blocked_by_admin_auth(api):
    r = api.get(PUBLIC)
    # P1a 還沒有 tour_base view，所以這裡可能是 500；P1b 的冒煙測試會要求 200
    assert r.status_code not in (401, 403), r.text


def test_admin_status_route_is_reachable(api, make_user):
    admin = make_user(role="admin")
    r = api.patch(
        f"{ADMIN}/status",
        headers=auth_header(admin),
        json={"tour_ids": [str(uuid.uuid4())], "tour_status": "1"},
    )
    # 走到 patch_tourStatus：tour_ids 都不存在 → 404，而不是被 /:tour_id 當成 tour_id='status'
    assert r.status_code == 404, r.text
    assert r.json()["message"] == "查無此項目"


def test_admin_detail_still_requires_admin(api, make_user):
    user = make_user(role="User")
    assert api.get(f"{ADMIN}/{uuid.uuid4()}").status_code == 401
    assert api.get(f"{ADMIN}/{uuid.uuid4()}", headers=auth_header(user)).status_code == 403


def test_admin_routes_not_exposed_under_user_prefix(api, make_user):
    admin = make_user(role="admin")
    r = api.post(f"{PUBLIC}/add", headers=auth_header(admin))
    assert r.status_code == 404, r.text
    assert r.json()["message"] == NOT_FOUND_ROUTE


def test_public_routes_not_exposed_under_admin_prefix(api):
    r = api.get(f"{ADMIN}/{uuid.uuid4()}/reviews")
    assert r.status_code == 404, r.text
    assert r.json()["message"] == NOT_FOUND_ROUTE
```

- [ ] **Step 3: 確認測試失敗，然後 commit 紅燈**

```bash
mkdir -p docs/reports/evidence/phase-1
uv run pytest tests/test_product_routes.py -v 2>&1 | sed "s#$PWD/##g; s#$PWD#.#g" | tee docs/reports/evidence/phase-1/task1-routes-red.txt
```
預期 5 個 FAIL、1 個 PASS：
- `test_guest_can_reach_public_tour_detail`：401
- `test_guest_tour_list_is_not_blocked_by_admin_auth`：401
- `test_admin_status_route_is_reachable`：500（`'status'` 被當成 UUID 拿去查 DB）
- `test_admin_routes_not_exposed_under_user_prefix`：400（請提供以下圖片…）
- `test_public_routes_not_exposed_under_admin_prefix`：400（公開版 reviews 的驗證：page、limit、lang 必填），不是 404「找不到此網站」
- `test_admin_detail_still_requires_admin`：PASS（回歸釘，修正後也要維持）

```bash
git add tests/test_product_routes.py docs/reports/evidence/phase-1/task1-routes-red.txt
git commit -m "test: 🔴 product router 的路由順序讓訪客拿到 401、上架 API 走不到"
```

- [ ] **Step 4: 建立 `backend/src/routes/product_admin.js`**

```js
const express = require('express');
const router = express.Router();
const controller = require('../controllers/product');

// middleware 的內容
const mw = require('../middlewares/product/index');
const auth = require('../middlewares/auth');
const authRole = require('../middlewares/authorizeRoles');

// 掛在 /api/v1/admin/product。公開的商品路由在 routes/product.js

// [POST] 編號 46 : 管理者新增旅遊項目
router.post('/add', auth, authRole('admin'), mw.productImageUpload(), mw.post_Product, controller.post_admin_product);
// X [POST] 46 : 管理者新增旅遊項目
// router.post('/add', auth, authRole('admin'),/* mw.,*/ controller.post_Touradd);

// [GET] 47 : 管理者查看刊登的旅遊項目
router.get('/', auth, authRole('admin'), mw.get_tourSearch, controller.get_tourSearch);

// [PATCH] 50 : 管理者上架刊登旅遊項目
// 必須宣告在 PATCH /:tour_id 之前，否則 "status" 會被當成 tour_id
router.patch('/status', auth, authRole('admin'), mw.patch_tourStatus, controller.patch_tourStatus);

// [GET] 48 : 管理者查看旅遊項目詳細內容
router.get('/:tour_id', auth, authRole('admin'), mw.get_admin_tourDetail, controller.get_tourDetail);

// [PATCH] 49 : 管理者修改旅遊項目細項內容
router.patch('/:tour_id', auth, authRole('admin'), mw.patch_admin_tourDetail, controller.patch_tourInfo);

// [DELETE] 51 : 管理者刪除旅遊項目
router.delete('/', auth, authRole('admin'), mw.delete_tourProduct, controller.delete_tourProduct);

module.exports = router;
```

- [ ] **Step 5: `backend/src/routes/product.js` 只留公開路由（整份換成下面的內容）**

```js
const express = require('express');
const router = express.Router();
const controller = require('../controllers/product');

// middleware 的內容
const mw = require('../middlewares/product/index');
const auth_not_manda = require('../middlewares/auth_not_mandatory');

// 掛在 /api/v1/user/product/search。管理者的商品路由在 routes/product_admin.js

// [GET] 編號 22 : 使用者查詢旅遊項目
router.get('/', auth_not_manda, mw.get_tourData, controller.get_tourData);

// [GET] 編號 23 : 使用者查看旅遊項目詳細資料
router.get('/:tour_id', auth_not_manda, mw.get_tourDetail, controller.get_tourDetails);

// [GET] 編號 24 : 使用者查看細項資料好評分數、評論
router.get('/:tour_id/reviews', auth_not_manda, mw.get_tourReview, controller.get_tourReview);

// [GET] 編號 25 : 使用者查看細項資料隱藏玩法
router.get(
  '/:tour_id/hidden-shares',
  auth_not_manda,
  mw.get_tourHiddenPlay,
  controller.get_tourHiddenPlay
);

module.exports = router;
```

- [ ] **Step 6: `backend/src/server.js` 改掛 admin router**

在 :16 `const productRouter = require('./routes/product');` 的下一行加上：
```js
const productAdminRouter = require('./routes/product_admin');
```
把 :113（加了上面那行之後變成 :114）的
```js
app.use(`/api/${version}/admin/product`, productRouter);
```
換成
```js
app.use(`/api/${version}/admin/product`, productAdminRouter);
```

- [ ] **Step 7: 確認測試通過**

nodemon 會自動重新載入。
```bash
sleep 3
uv run pytest tests/test_product_routes.py -v
uv run pytest -q
```
預期：`test_product_routes.py` 6 個 PASS；完整測試 19 passed、1 xfailed。

- [ ] **Step 8: Commit 綠燈（backend repo）**

```bash
git -C backend add src/routes/product.js src/routes/product_admin.js src/server.js
git -C backend commit -m "fix: 🟢 product router 拆成 admin / public，修正路由順序造成的 401 與上架 API 走不到"
```

---

### Task 2: fakedata 變成可重跑的 Flyway seed（spec 3.2）

**Files:**
- Create: `db/seed-build/tripeasy_fakedata.sql`（來源檔，CRLF 轉 LF）
- Create: `db/seed-build/build_seed.py`
- Create: `db/seed/R__seed.sql`（腳本產生）
- Modify: `docker-compose.yml`（flyway 服務）
- Modify: `tests/conftest.py`（新增 `tx` fixture）
- Test: `tests/test_seed.py`

**Interfaces:**
- Consumes: conftest 的 `db`、`ROOT`。
- Produces:
  - `db/seed-build/build_seed.py`：`build(text: str) -> str`，以及 `uv run python db/seed-build/build_seed.py` 重新產生 `db/seed/R__seed.sql`。
  - conftest 的 `tx` fixture：一條不自動 commit 的 psycopg 連線，測試結束一律 rollback。P1b 的行為測試會用到。
  - `tests/test_seed.py` 的 `SEED_COUNTS`：fakedata 每張表的筆數。

- [ ] **Step 1: 把 fakedata 原檔放進 repo**

原檔在使用者的 Windows 下載資料夾。只把 CRLF 轉成 LF，內容不改：
```bash
mkdir -p db/seed-build db/seed
tr -d '\r' < /mnt/c/Users/nohungry5656/Downloads/tripeasy_fakedata.sql > db/seed-build/tripeasy_fakedata.sql
wc -l db/seed-build/tripeasy_fakedata.sql
```
預期：917 行。

- [ ] **Step 2: 在 `tests/conftest.py` 加上 `tx` fixture**

把 `db` fixture 換成下面這段（連線參數抽成 `_db_params()`，`db` 的行為不變），並加上 `tx`：
```python
def _db_params() -> dict:
    return dict(
        host=os.getenv("TEST_DB_HOST", "localhost"),
        port=int(os.getenv("TEST_DB_PORT", "5432")),
        user=os.environ["POSTGRES_DB_USER"],
        password=os.environ["POSTGRES_DB_PASSWORD"],
        dbname=os.environ["POSTGRES_DB_NAME"],
    )


@pytest.fixture(scope="session")
def db():
    conn = psycopg.connect(**_db_params(), autocommit=True)
    yield conn
    conn.close()


@pytest.fixture
def tx():
    """不自動 commit 的連線。測試結束一律 rollback，不留下任何資料。"""
    conn = psycopg.connect(**_db_params())
    try:
        yield conn
    finally:
        conn.rollback()
        conn.close()
```

- [ ] **Step 3: 寫失敗的測試 `tests/test_seed.py`**

```python
"""spec 3.2：fakedata 改寫成 Flyway repeatable migration，可以重複執行。"""
from conftest import ROOT

SEED = ROOT / "db" / "seed" / "R__seed.sql"

# fakedata（2025-05）每張表的筆數。測試可能另外新增資料，所以檢查「至少」
SEED_COUNTS = {
    "user": 3, "socialLogin": 3, "user_level": 3, "coupon": 5,
    "tour": 10, "tour_detail": 6, "restaurant": 2, "restaurant_business": 14,
    "restaurant_menu": 6, "hotel": 2, "hotel_room": 4, "notification": 4,
    "country": 37, "region": 87, "cart": 6, "cart_item": 10,
    "orders": 5, "order_item": 10, "review": 10, "hidden_play": 6,
    "auto_setting": 4, "favorite": 7, "point_record": 2, "user_coupon": 4,
}


def _counts(conn) -> dict:
    return {
        t: conn.execute(f'SELECT count(*) FROM "{t}"').fetchone()[0] for t in SEED_COUNTS
    }


def test_flyway_applied_seed(db):
    row = db.execute(
        "SELECT success FROM flyway_schema_history "
        "WHERE script = 'R__seed.sql' ORDER BY installed_rank DESC LIMIT 1"
    ).fetchone()
    assert row == (True,)


def test_seed_loaded_every_table(db):
    counts = _counts(db)
    short = {t: (counts[t], n) for t, n in SEED_COUNTS.items() if counts[t] < n}
    assert not short, f"（實際, 預期至少）：{short}"


def test_seed_is_rerunnable(tx):
    # 模擬「volume 還在、seed 內容改過」：Flyway 會把整份 seed 再跑一次
    before = _counts(tx)
    tx.execute(SEED.read_text(encoding="utf-8"))
    assert _counts(tx) == before
```

- [ ] **Step 4: 確認測試失敗，然後 commit 紅燈**

```bash
uv run pytest tests/test_seed.py -v 2>&1 | sed "s#$PWD/##g; s#$PWD#.#g" | tee docs/reports/evidence/phase-1/task2-seed-red.txt
```
預期 3 個 FAIL：
- `test_flyway_applied_seed`：`None == (True,)`
- `test_seed_loaded_every_table`：每張表都是 0
- `test_seed_is_rerunnable`：`FileNotFoundError`（`db/seed/R__seed.sql` 還不存在）

```bash
git add tests/conftest.py tests/test_seed.py db/seed-build/tripeasy_fakedata.sql docs/reports/evidence/phase-1/task2-seed-red.txt
git commit -m "test: 🔴 本機 DB 沒有任何 seed 資料"
```

- [ ] **Step 5: 建立 `db/seed-build/build_seed.py`**

```python
"""把團隊留下的 fakedata 轉成可重複執行的 Flyway seed。

來源：db/seed-build/tripeasy_fakedata.sql（2025-05，使用者提供；依序跑 V1 → V2 → 本檔沒有錯誤）
產出：db/seed/R__seed.sql（Flyway repeatable migration，只在本機與展示環境載入）
執行：uv run python db/seed-build/build_seed.py

每個轉換都 assert 次數：來源檔一旦跟預期不同，就停下來，而不是默默產生錯的 seed。
"""
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "tripeasy_fakedata.sql"
TARGET = HERE.parent / "seed" / "R__seed.sql"

DATA_MARKER = "/* ------------------ 產生假資料"
INSERT_COUNT = 24

HEADER = """\
-- 本檔由 db/seed-build/build_seed.py 產生，請勿手動修改；要改請改腳本後重新產生。
-- 來源：db/seed-build/tripeasy_fakedata.sql
-- 只在本機與展示環境載入（compose 的 Flyway -locations 加上 db/seed），正式環境不載入。
-- 每個 INSERT 都是 ON CONFLICT DO NOTHING：重跑時既有的資料不會被更新。
-- 改了既有資料列的內容，要 docker compose down -v 重建 DB 才看得到。

"""


def drop_delete_block(text: str) -> str:
    _, marker, data = text.partition(DATA_MARKER)
    assert marker, "找不到「產生假資料」區段"
    return marker + data


def add_on_conflict(text: str) -> str:
    lines = text.split("\n")
    n = 0
    for i, line in enumerate(lines):
        if line.rstrip().endswith(";"):
            lines[i] = line.rstrip()[:-1] + "\nON CONFLICT DO NOTHING;"
            n += 1
    assert n == INSERT_COUNT, f"INSERT 數量 {n}，預期 {INSERT_COUNT}"
    return "\n".join(lines)


def build(text: str) -> str:
    text = text.replace("\r\n", "\n")
    text = drop_delete_block(text)
    text = add_on_conflict(text)
    assert "${" not in text, "Flyway 會把 ${...} 當成 placeholder"
    return HEADER + text


if __name__ == "__main__":
    TARGET.write_text(build(SOURCE.read_text(encoding="utf-8")), encoding="utf-8")
    print(f"wrote {TARGET.relative_to(HERE.parent.parent)}")
```

產生 seed：
```bash
uv run python db/seed-build/build_seed.py
grep -c "ON CONFLICT DO NOTHING;" db/seed/R__seed.sql
```
預期：印出 `wrote db/seed/R__seed.sql`，grep 結果是 `24`。

- [ ] **Step 6: `docker-compose.yml` 的 flyway 加上 seed location**

把 flyway 服務的
```yaml
      - '-locations=filesystem:/flyway/sql'
```
換成
```yaml
      - '-locations=filesystem:/flyway/sql,filesystem:/flyway/seed'
```
並在它的 `volumes:` 加上第二行：
```yaml
    volumes:
      - ./backend/migrations:/flyway/sql:ro
      - ./db/seed:/flyway/seed:ro
```

- [ ] **Step 7: 重跑 Flyway，確認測試通過**

```bash
docker compose up -d flyway
docker compose logs flyway --tail=5
uv run pytest tests/test_seed.py -v
uv run pytest -q
```
預期：
- Flyway log 有 `Migrating schema "public" with repeatable migration "seed"` 和 `Successfully applied 1 migration`。
- `test_seed.py` 3 個 PASS。
- 完整測試 22 passed、1 xfailed。

- [ ] **Step 8: Review Focus #1，保留 volume 再跑一次 ci.sh**

```bash
docker compose down        # 不加 -v
scripts/ci.sh 2>&1 | tail -5
```
預期：4 個服務都 ✅，22 passed、1 xfailed。

- [ ] **Step 9: Commit 綠燈（總覽 repo）**

```bash
git add db/seed-build/build_seed.py db/seed/R__seed.sql docker-compose.yml
git commit -m "feat: 🟢 fakedata 改寫成可重跑的 Flyway repeatable seed"
```

---

### Task 3: seed 的資料修正：bcrypt、角色、日期、本機圖片（spec 3.2）

**Files:**
- Modify: `db/seed-build/build_seed.py`（整份，見 Step 4）
- Modify: `db/seed/R__seed.sql`（重新產生）
- Create: `db/seed-images/tour.svg`、`feature.svg`、`hidden.svg`、`badge.svg`、`avatar.svg`
- Modify: `docker-compose.yml`（backend 的 volumes）
- Modify: `.env.example`
- Test: `tests/test_seed.py`（加測試）

**Interfaces:**
- Consumes: Task 1 的 `PATCH /api/v1/admin/product/status`（unknown UUID → 404「查無此項目」）；Task 2 的 `build()`、`tests/test_seed.py` 的 `SEED`。
- Produces:
  - seed 帳號：`alice@example.com`（User）、`bob@example.com`（admin）、`carol@example.com`（User），密碼都是 `Tripeasy123`。
  - 佔位圖網址：`http://localhost:3000/uploads/seed/{tour,feature,hidden,badge,avatar}.svg`。
  - 日期基準：fakedata 的每個日期都加上 `CURRENT_DATE - DATE '2025-05-20'` 天。

- [ ] **Step 1: 在 `tests/test_seed.py` 加上失敗的測試**

檔案開頭的 import 區改成：
```python
"""spec 3.2：fakedata 改寫成 Flyway repeatable migration，可以重複執行。"""
import re
import uuid

import jwt

from conftest import ROOT
```

在檔案最後加上：
```python
SEED_PASSWORD = "Tripeasy123"  # 跟 .env.example 的註解一致
SEED_USERS = {"alice@example.com": "User", "bob@example.com": "admin", "carol@example.com": "User"}
IMAGE_NAMES = ("tour", "feature", "hidden", "badge", "avatar")


def _login(api, email):
    return api.post(
        "/api/v1/auth/userinfo/login/email", json={"email": email, "password": SEED_PASSWORD}
    )


def test_seed_user_can_login(api):
    r = _login(api, "alice@example.com")
    assert r.status_code == 200, r.text


def test_seed_roles_match_authorize_roles(db):
    rows = db.execute(
        'SELECT email, role FROM "user" WHERE email = ANY(%s)', (list(SEED_USERS),)
    ).fetchall()
    assert dict(rows) == SEED_USERS


def test_seed_admin_passes_authorize_roles(api):
    r = _login(api, "bob@example.com")
    assert r.status_code == 200, r.text
    token = r.json()["data"]["token"]  # resStatus 把 dbdata 放在 data 底下
    claims = jwt.decode(token, options={"verify_signature": False})
    assert claims["role"] == "admin"

    r = api.patch(
        "/api/v1/admin/product/status",
        headers={"Authorization": f"Bearer {token}"},
        # UUIDField 只接受 v4 / v5，不能用全 0 的 UUID
        json={"tour_ids": [str(uuid.uuid4())], "tour_status": "1"},
    )
    assert r.status_code == 404, r.text  # 過了 authRole('admin')，走到「查無此項目」


def test_seed_dates_are_relative_to_today(db):
    (past_tours,) = db.execute(
        "SELECT count(*) FROM tour WHERE tour_start_date < CURRENT_DATE"
    ).fetchone()
    (expired_coupons,) = db.execute(
        "SELECT count(*) FROM coupon WHERE expire_date < CURRENT_DATE"
    ).fetchone()
    assert (past_tours, expired_coupons) == (0, 0)


def test_seed_uses_local_placeholder_images(api):
    text = SEED.read_text(encoding="utf-8")
    assert not re.search(r"https://example\.com/(images|avatar|badges|feature|hidden)/", text)
    for name in IMAGE_NAMES:
        r = api.get(f"/uploads/seed/{name}.svg")
        assert r.status_code == 200, name
        assert r.headers["Content-Type"].startswith("image/svg+xml")
```

- [ ] **Step 2: 確認測試失敗，然後 commit 紅燈**

```bash
uv run pytest tests/test_seed.py -v 2>&1 | sed "s#$PWD/##g; s#$PWD#.#g" | tee docs/reports/evidence/phase-1/task3-seed-data-red.txt
```
預期：Task 2 的 3 個 PASS，新的 5 個 FAIL：
- `test_seed_user_can_login`：假的 hash，登入失敗（不是 200）
- `test_seed_roles_match_authorize_roles`：alice、carol 是 `'user'`
- `test_seed_admin_passes_authorize_roles`：登入失敗
- `test_seed_dates_are_relative_to_today`：日期都在 2025 年
- `test_seed_uses_local_placeholder_images`：seed 裡還是 `https://example.com/images/...`

```bash
git add tests/test_seed.py docs/reports/evidence/phase-1/task3-seed-data-red.txt
git commit -m "test: 🔴 seed 帳號無法登入、角色大小寫不符、日期已過期、圖片是外部假網址"
```

- [ ] **Step 3: 建立 5 張佔位圖**

`db/seed-images/tour.svg`：
```xml
<svg xmlns="http://www.w3.org/2000/svg" width="800" height="600" viewBox="0 0 800 600"><rect width="800" height="600" fill="#cfe3f5"/><text x="400" y="315" font-family="sans-serif" font-size="56" text-anchor="middle" fill="#35618a">TripEasy 行程</text></svg>
```
`db/seed-images/feature.svg`：
```xml
<svg xmlns="http://www.w3.org/2000/svg" width="800" height="600" viewBox="0 0 800 600"><rect width="800" height="600" fill="#d9f0e1"/><text x="400" y="315" font-family="sans-serif" font-size="56" text-anchor="middle" fill="#2f6b45">TripEasy 特色</text></svg>
```
`db/seed-images/hidden.svg`：
```xml
<svg xmlns="http://www.w3.org/2000/svg" width="800" height="600" viewBox="0 0 800 600"><rect width="800" height="600" fill="#f5e6cf"/><text x="400" y="315" font-family="sans-serif" font-size="56" text-anchor="middle" fill="#7a5a2b">TripEasy 隱藏玩法</text></svg>
```
`db/seed-images/badge.svg`：
```xml
<svg xmlns="http://www.w3.org/2000/svg" width="128" height="128" viewBox="0 0 128 128"><circle cx="64" cy="64" r="60" fill="#f2c94c"/><text x="64" y="76" font-family="sans-serif" font-size="32" text-anchor="middle" fill="#6b4e00">LV</text></svg>
```
`db/seed-images/avatar.svg`：
```xml
<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200" viewBox="0 0 200 200"><rect width="200" height="200" fill="#e0e0e0"/><circle cx="100" cy="80" r="40" fill="#9e9e9e"/><rect x="40" y="135" width="120" height="50" rx="25" fill="#9e9e9e"/></svg>
```

- [ ] **Step 4: `db/seed-build/build_seed.py` 加上資料修正（整份換成下面的內容）**

```python
"""把團隊留下的 fakedata 轉成可重複執行的 Flyway seed。

來源：db/seed-build/tripeasy_fakedata.sql（2025-05，使用者提供；依序跑 V1 → V2 → 本檔沒有錯誤）
產出：db/seed/R__seed.sql（Flyway repeatable migration，只在本機與展示環境載入）
執行：uv run python db/seed-build/build_seed.py

每個轉換都 assert 次數：來源檔一旦跟預期不同，就停下來，而不是默默產生錯的 seed。
"""
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "tripeasy_fakedata.sql"
TARGET = HERE.parent / "seed" / "R__seed.sql"

DATA_MARKER = "/* ------------------ 產生假資料"
INSERT_COUNT = 24

# 明文 Tripeasy123（寫在 .env.example 的註解）。bcrypt cost 10，跟 backend 註冊時相同
SEED_PASSWORD_HASH = "$2b$10$9Bd0v0X7eLfhzEL5BC8pROe7OWUfOq4rFDMi.8K/Gg7prMuyn8OKi"
FAKE_HASHES = (
    "$2b$10$abcd1234abcd1234abcd12",
    "$2b$10$efgh5678efgh5678efgh56",
    "$2b$10$ijkl9012ijkl9012ijkl90",
)

# fakedata 的資料大約建立在 2025-05-20。所有日期平移成「以今天為基準」，
# 讓行程、優惠券在 seed 載入的那一天都還在未來
DATE_ANCHOR = "2025-05-20"
DATE_LITERAL = re.compile(r"'(\d{4}-\d{2}-\d{2}(?: \d{2}:\d{2}:\d{2})?)'")
DATE_COUNT = 53

IMAGE_BASE = "http://localhost:3000/uploads/seed"
IMAGE_URL = re.compile(r"'https://example\.com/(images|avatar|badges|feature|hidden)/[^']*'")
IMAGE_FILE = {"images": "tour", "feature": "feature", "hidden": "hidden", "badges": "badge", "avatar": "avatar"}
IMAGE_COUNT = 103

HEADER = """\
-- 本檔由 db/seed-build/build_seed.py 產生，請勿手動修改；要改請改腳本後重新產生。
-- 來源：db/seed-build/tripeasy_fakedata.sql
-- 只在本機與展示環境載入（compose 的 Flyway -locations 加上 db/seed），正式環境不載入。
-- 每個 INSERT 都是 ON CONFLICT DO NOTHING：重跑時既有的資料不會被更新。
-- 改了既有資料列的內容，要 docker compose down -v 重建 DB 才看得到。

"""


def drop_delete_block(text: str) -> str:
    _, marker, data = text.partition(DATA_MARKER)
    assert marker, "找不到「產生假資料」區段"
    return marker + data


def add_on_conflict(text: str) -> str:
    lines = text.split("\n")
    n = 0
    for i, line in enumerate(lines):
        if line.rstrip().endswith(";"):
            lines[i] = line.rstrip()[:-1] + "\nON CONFLICT DO NOTHING;"
            n += 1
    assert n == INSERT_COUNT, f"INSERT 數量 {n}，預期 {INSERT_COUNT}"
    return "\n".join(lines)


def fix_roles(text: str) -> str:
    # 程式用 authRole('User') / authRole('admin')，fakedata 寫的是 'user'
    text, n = re.subn(r"^(\s*)'user',(\s*)$", r"\1'User',\2", text, flags=re.M)
    assert n == 2, f"角色 'user' 有 {n} 個，預期 2"
    return text


def fix_password_hashes(text: str) -> str:
    for fake in FAKE_HASHES:
        assert text.count(f"'{fake}'") == 1, fake
        text = text.replace(f"'{fake}'", f"'{SEED_PASSWORD_HASH}'")
    return text


def shift_dates(text: str) -> str:
    text, n = DATE_LITERAL.subn(
        lambda m: f"(TIMESTAMP '{m.group(1)}' + (CURRENT_DATE - DATE '{DATE_ANCHOR}') * INTERVAL '1 day')",
        text,
    )
    assert n == DATE_COUNT, f"日期 {n} 個，預期 {DATE_COUNT}"
    return text


def use_local_images(text: str) -> str:
    text, n = IMAGE_URL.subn(lambda m: f"'{IMAGE_BASE}/{IMAGE_FILE[m.group(1)]}.svg'", text)
    assert n == IMAGE_COUNT, f"圖片網址 {n} 個，預期 {IMAGE_COUNT}"
    return text


def build(text: str) -> str:
    text = text.replace("\r\n", "\n")
    text = drop_delete_block(text)
    text = add_on_conflict(text)
    text = fix_roles(text)
    text = fix_password_hashes(text)
    text = shift_dates(text)
    text = use_local_images(text)
    assert "${" not in text, "Flyway 會把 ${...} 當成 placeholder"
    return HEADER + text


if __name__ == "__main__":
    TARGET.write_text(build(SOURCE.read_text(encoding="utf-8")), encoding="utf-8")
    print(f"wrote {TARGET.relative_to(HERE.parent.parent)}")
```

重新產生：
```bash
uv run python db/seed-build/build_seed.py
```

- [ ] **Step 5: backend 掛上佔位圖，`.env.example` 寫上 seed 帳號**

`docker-compose.yml` 的 backend `volumes:` 在 `uploads:/usr/backend/uploads` 下一行加上：
```yaml
      - ./db/seed-images:/usr/backend/uploads/seed:ro
```
唯讀掛載：使用者換頭像時，`storage/local.js` 的 `remove()` 刪不到佔位圖（失敗會回 `false`，不會拋錯）。

`.env.example` 的第一行之前加上：
```
# seed 帳號（只在本機與展示環境，來自 db/seed/R__seed.sql）：
#   alice@example.com（User）、bob@example.com（admin）、carol@example.com（User）
#   密碼都是 Tripeasy123
```

- [ ] **Step 6: 重建 DB，確認測試通過**

seed 用 `ON CONFLICT DO NOTHING`，既有資料列不會被更新，所以這一步要清掉 volume：
```bash
docker compose down -v
scripts/ci.sh 2>&1 | tail -5
uv run pytest tests/test_seed.py -v
```
預期：4 個服務都 ✅；`test_seed.py` 8 個 PASS；完整測試 27 passed、1 xfailed。

- [ ] **Step 7: 保留 volume 再跑一次**

```bash
docker compose down        # 不加 -v
scripts/ci.sh 2>&1 | tail -5
```
預期：27 passed、1 xfailed。

- [ ] **Step 8: Commit 綠燈（總覽 repo）**

```bash
git add db/seed-build/build_seed.py db/seed/R__seed.sql db/seed-images/tour.svg db/seed-images/feature.svg db/seed-images/hidden.svg db/seed-images/badge.svg db/seed-images/avatar.svg docker-compose.yml .env.example
git commit -m "feat: 🟢 seed 改用真的 bcrypt、角色對齊 authRole、日期以今天為基準、圖片改本機佔位圖"
```

---

## 契約（Task 4–7）

Task 4、5、6 各負責一組物件，寫進同一份 `docs/db-contract.md`。三個 Task 都依照下面的「反推方法」和「物件模板」。

### 反推方法（每個物件都要做）

1. `grep -rnw '<物件名>' backend/src` 找出所有使用位置。每一處都記錄 `檔案:行號`，並把完整的 SQL 字串原文貼進契約。
2. 從 SQL 推出：
   - **參數**：函式呼叫時傳入的值，型別從呼叫端的變數來源判斷（例如 `req.params.tour_id` 經過 UUID 驗證 → `uuid`）。
   - **一定要存在的欄位**：`WHERE`、`ORDER BY`、`GROUP BY` 用到的欄位，以及 `SELECT` 明確列出的欄位。
3. 從 JS 推出：controller 怎麼讀查詢結果。例如 `row.旅遊編號`、`row['價錢']`、解構、`.map(...)` 裡取的 key，以及這些值被放進 response 的哪個欄位。`SELECT *` 的時候，**JS 讀到的每個 key 都是輸出欄位**。
4. 對照 V1 的資料表（`backend/migrations/V1__tripeasy_sql.sql`），找出每個輸出欄位最可能的來源欄位或計算方式，並寫出型別。
5. 有兩種以上合理解讀的地方，不要自己選，寫進該物件的「待確認」，附上每種解讀的後果。
6. 只讀程式碼，不改任何檔案（`docs/db-contract.md` 除外），也不碰 DB。

### 物件模板

````markdown
### `<物件名>`

- **種類**：view ／ function（`<名稱>(<參數> <型別>, ...) RETURNS TABLE`）
- **使用位置**：
  - `controllers/home.js:132`（API：`GET /api/v1/user/home/search/...`）
    ```sql
    <SQL 原文>
    ```
- **參數**（function 才有）：

  | 參數 | 型別 | 來源 | 語意 |
  |---|---|---|---|

- **輸出欄位**：

  | 欄位（中文） | 型別 | 來源（表.欄位 或計算式） | 讀取位置 | 依據 |
  |---|---|---|---|---|
  | 旅遊編號 | uuid | `tour.tour_id` | `controllers/home.js:140` | WHERE 條件 + response.tour_id |

- **列的語意**：一列代表什麼（例如「每個上架中的行程一列」）、包含哪些資料（例如 `status = 1`）、預設排序。
- **邊界**：沒有評論時平均分數是 `NULL` 還是 `0`、`LEFT` 還是 `INNER JOIN` 等等，以及程式碼裡的依據。
- **信心**：確定 ／ 推測（寫出理由）。
- **待確認**：沒有就寫「無」。
````

---

### Task 4: 契約 A 組：商品與首頁（9 個物件）

**Files:**
- Create: `docs/db-contract.md`

**Interfaces:**
- Consumes: 本節的「反推方法」和「物件模板」。
- Produces: `docs/db-contract.md` 的 §0（說明）、§1（A 組）。後面的 Task 會接著寫 §2、§3、§4，標題要跟下面的一字不差。

物件：`tour_base`、`tour_travel(uuid)`、`tour_travel_popular`、`tour_travel_most_favorited`、`tour_tour_detail`、`tour_hotel`、`tour_restaurant`、`user_user_level`、`user_level_review_forHome`。

- [ ] **Step 1: 建立 `docs/db-contract.md` 的骨架**

```markdown
# TripEasy DB 契約（V3 views / functions）

> 狀態：草稿 · 依據 spec 3.1 · 從 backend 程式碼反推（四份既有 SQL 都沒有這些物件）

## 0. 說明

- 範圍：程式碼查詢了、但 migration 沒有建立的 21 個物件（12 個 view、9 個 function）。
- 反推方法：見 `docs/superpowers/plans/2026-10-20-p1a-routes-seed-contract.md` 的「反推方法」。
- 原則：V3 照程式碼期待的中文欄位名建立，**controller 不改**。
- 行號以 backend `phase-1` 分支、P1a Task 1 完成後的版本為準。

## 1. A 組：商品與首頁

## 2. B 組：購物車、訂位、折扣、結帳

## 3. C 組：會員與後台

## 4. 待使用者確認
```

- [ ] **Step 2: 依照「反推方法」和「物件模板」寫完 A 組 9 個物件**

寫在 `## 1. A 組：商品與首頁` 底下，每個物件一個 `###` 小節，順序照上面的物件清單。

- [ ] **Step 3: 自我檢查**

```bash
for o in tour_base tour_travel tour_travel_popular tour_travel_most_favorited tour_tour_detail tour_hotel tour_restaurant user_user_level user_level_review_forHome; do
  printf "%-28s 小節:%s  使用位置(grep):%s\n" "$o" "$(grep -c "^### \`$o\`" docs/db-contract.md)" "$(grep -rlw "$o" backend/src | wc -l)"
done
```
預期：每個物件的「小節」都是 1。另外人工確認：grep 找到的每個檔案，都出現在該物件的「使用位置」裡。

- [ ] **Step 4: Commit**

```bash
git add docs/db-contract.md
git commit -m "docs: DB 契約 A 組（商品與首頁，9 個物件）"
```

---

### Task 5: 契約 B 組：購物車、訂位、折扣、結帳（8 個物件）

**Files:**
- Modify: `docs/db-contract.md`（只寫 §2）

**Interfaces:**
- Consumes: Task 4 建立的骨架；本節的「反推方法」和「物件模板」。
- Produces: `docs/db-contract.md` §2。

物件：`user_cartList`、`hotel_booking`、`restaurant_booking`、`restaurant_isClosed`、`restaurant_business_parsed`、`user_couponList`、`user_level_point_coupon`、`user_orderList`。

這組有 spec 3.1 已知的兩個待確認語意，要寫進對應物件的「待確認」，並且查清楚所有相關的程式碼位置：
- **點數的累積和扣抵規則**：`controllers/checkout.js:159`、`controllers/discounts.js:66` 的 `point * 0.8`。要寫出：點數存在哪個欄位、什麼時候增加或扣除（找出所有寫入 `point_record`、`user_level.travel_point` 的地方）、`0.8` 是「1 點折 0.8 元」還是別的意思。
- **`coupon.discount` 是折扣倍率還是折抵金額**：`controllers/discounts.js:38`。要寫出：程式拿它做了什麼運算，以及 seed（`db/seed/R__seed.sql` 的 coupon 區段）裡實際的值長什麼樣子。

- [ ] **Step 1: 依照「反推方法」和「物件模板」寫完 B 組 8 個物件**

寫在 `## 2. B 組：購物車、訂位、折扣、結帳` 底下，順序照上面的物件清單。

- [ ] **Step 2: 自我檢查**

```bash
for o in user_cartList hotel_booking restaurant_booking restaurant_isClosed restaurant_business_parsed user_couponList user_level_point_coupon user_orderList; do
  printf "%-28s 小節:%s  使用位置(grep):%s\n" "$o" "$(grep -c "^### \`$o\`" docs/db-contract.md)" "$(grep -rlw "$o" backend/src | wc -l)"
done
grep -n "point \* 0.8\|\.discount" backend/src/controllers/checkout.js backend/src/controllers/discounts.js
```
預期：每個物件的「小節」都是 1；第二個 grep 找到的每一行，都出現在契約的「待確認」裡。

- [ ] **Step 3: Commit**

```bash
git add docs/db-contract.md
git commit -m "docs: DB 契約 B 組（購物車、訂位、折扣、結帳，8 個物件）"
```

---

### Task 6: 契約 C 組：會員與後台（4 個物件）

**Files:**
- Modify: `docs/db-contract.md`（只寫 §3）

**Interfaces:**
- Consumes: Task 4 建立的骨架；本節的「反推方法」和「物件模板」。
- Produces: `docs/db-contract.md` §3。

物件：`user_favorite`、`user_orders`、`user_order_item`、`user_adminList`。

- [ ] **Step 1: 依照「反推方法」和「物件模板」寫完 C 組 4 個物件**

寫在 `## 3. C 組：會員與後台` 底下，順序照上面的物件清單。

- [ ] **Step 2: 自我檢查**

```bash
for o in user_favorite user_orders user_order_item user_adminList; do
  printf "%-28s 小節:%s  使用位置(grep):%s\n" "$o" "$(grep -c "^### \`$o\`" docs/db-contract.md)" "$(grep -rlw "$o" backend/src | wc -l)"
done
grep -c '^### `' docs/db-contract.md
```
預期：每個物件的「小節」都是 1；全部的物件小節共 21 個。

- [ ] **Step 3: Commit**

```bash
git add docs/db-contract.md
git commit -m "docs: DB 契約 C 組（會員與後台，4 個物件）"
```

---

### Task 7: 待確認彙整、跨組一致性，以及使用者確認

**Files:**
- Modify: `docs/db-contract.md`（§4，以及因一致性修正而改到的 §1–§3）

**Interfaces:**
- Consumes: Task 4–6 的 §1–§3。
- Produces: 定案的 `docs/db-contract.md`，狀態改成「定案」。P1b 會依照它寫 V3 SQL 和契約測試。

- [ ] **Step 1: 跨組一致性檢查**

同一個概念在不同物件裡，要用同一個中文欄位名和同一個型別。例如「旅遊編號」在 `tour_base` 和 `user_cartList` 裡都要是 `uuid`。

列出所有物件的輸出欄位，找出同名但型別或來源不同的欄位。每一個都要修正到一致，或寫進 §4 待確認。

- [ ] **Step 2: 寫 §4「待使用者確認」**

把 §1–§3 每個物件的「待確認」集中成一張表：

| # | 物件 | 問題 | 選項與後果 | 建議 | 使用者的決定 |
|---|---|---|---|---|---|

- 「建議」要寫理由，以程式碼現有的行為為準：選讓 controller 不用改就能正確運作的那個。
- 「使用者的決定」先留白，Step 4 填入。

- [ ] **Step 3: Commit**

```bash
git add docs/db-contract.md
git commit -m "docs: DB 契約待確認彙整與跨組一致性"
```

- [ ] **Step 4: 停下來，請使用者確認 §4 的每一題**

**停下來**。把 §4 的每一題連同選項、建議和程式碼依據交給使用者，等使用者逐題回答。

收到回答後：
- 把決定填進 §4「使用者的決定」。
- 依決定更新對應物件的輸出欄位、語意和邊界。
- 把檔頭狀態改成「定案（YYYY-MM-DD 使用者確認）」。

```bash
git add docs/db-contract.md
git commit -m "docs: DB 契約定案（使用者確認待確認語意）"
```

---

## P1a 完成標準（對照 spec 第 3 節）

- [ ] 3.0 的兩個路由 bug 都已修正，紅燈和綠燈分開 commit → Task 1
- [ ] seed 可以重跑，用 seed 帳號能登入，角色、日期、圖片都已修正 → Task 2、3
- [ ] 21 個物件的契約寫完，通過 Fable 和 Opus 雙審 → Task 4–7
- [ ] 契約中待確認的語意已經由使用者確認 → Task 7 Step 4
- [ ] 每個 Task 都經過 Fable 和 Opus 的雙 review，沒有還沒處理的 Critical 或 Important 問題

## 接著：P1b（契約定案後另寫一份計畫）

- `migrations/V3__views_functions.sql`：照定案的契約建立 21 個物件，controller 不改。
- 三層測試：契約（`information_schema`、`pg_proc`）、行為（用 `tx` fixture 自己塞資料、rollback）、API 冒煙（原本 500 的 API 改成 200，`test_guest_tour_list_is_not_blocked_by_admin_auth` 收緊成 200）。
- `test_migrations.py` 的 `[("1", True), ("2", True)]` 要加上 V3。
- seed 補資料量（搜尋篩選、分頁、熱門排行要有東西可看）和 `payment` 資料，需要的資料形狀以契約為準。
- `delete_user` 擴充成依 FK 順序清 11 張表（P0 parked，P1b 第一個寫入 cart / orders / favorite 等表的測試之前）。
- CI：`actions/checkout`、`actions/upload-artifact` 升到 v7、`astral-sh/setup-uv` 升到 v10，消除 Node 20 的提醒。push 後才驗證得到，所以放在 P1b 結尾。
- P1 報告、合併、打 tag，push 前先問使用者。
