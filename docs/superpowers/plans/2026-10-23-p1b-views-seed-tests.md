# P1b View／Function、Seed 重寫、三層測試 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 依定案的 `docs/db-contract.md` 建立 21 個 view／function；把 seed 改寫成主鍵都是 v4、資料量足以展示的版本；用契約、行為、API 冒煙三層測試證明；CI 升級後寫 P1 報告，經使用者同意後合併、打 tag、push。

**Architecture:** 21 個物件放在 backend 的 Flyway **repeatable migration** `backend/migrations/R__views_functions.sql`（理由見 Global Constraints 第 1 條）。seed 產生器 `build_seed.py` 改成「解析 INSERT → 以資料列為單位改寫 → 輸出」的流程，主鍵由各表的自然鍵決定性產生 v4 形狀的 id，外鍵依欄位名稱對應到被參照表的新舊 id 對照。測試分三層：契約（`pg_class`／`pg_proc`／欄位型別，對照 `tests/db_contract.py`）、行為（`tx` fixture 自己塞資料、rollback）、API 冒煙（用 seed 打原本 500 或 400 的 API）。

**Tech Stack:** Express 4.21、PostgreSQL 15、Flyway 10.20.1、Python 3.13 / uv / pytest 8.3.3 / requests / psycopg 3 / PyJWT。

**Spec:** `docs/superpowers/specs/2026-10-15-tripeasy-rebuild-design.md`（第 3.1 第 4 步、3.2 的補資料量與 `payment`、3.3、P1 完成標準）。契約：`docs/db-contract.md`（§0.1 是本計畫的待辦清單，§4 是使用者的決定）。前一份計畫：`docs/superpowers/plans/2026-10-20-p1a-routes-seed-contract.md`。

## Global Constraints

1. **21 個物件放在 `backend/migrations/R__views_functions.sql`（repeatable），不用 spec 3.1 寫的 `V3__views_functions.sql`。** 理由：versioned migration 套用後內容不能再改（Flyway validate 會失敗），開發中每次修 SQL 都要 `down -v`；P2 起的重構規則又要求動到 view 時同步更新。view／function 用 repeatable migration 是 Flyway 的慣例做法：內容一改，下次 `migrate` 就重新套用。檔案開頭先 `DROP ... IF EXISTS ... CASCADE` 全部 21 個物件，再依相依順序 `CREATE`。Task 1 會把 spec 3.1 第 4 步與契約標題改成這個寫法。
2. **controller、middleware、validator、route 一律不改**（spec 3.1 第 4 步、§0 重構規則）。已知的 controller bug 只記錄，不修。frontend 在 P1b 不動，`refs.env` 的 `FRONTEND_REF` 維持 `phase-0`。
3. 物件的識別字、欄位名稱、型別、列的語意，一律以 `docs/db-contract.md` 為準（§0「識別字對照」、各物件的「輸出欄位」與「列的語意」、§4 的決定）。契約和 SQL 不一致時，先停下來回報，不要自己選。
4. seed **只在本機和展示環境載入**（compose 的 Flyway `-locations` 含 `/flyway/seed`），`R__views_functions.sql` 在 `backend/migrations`，正式環境也會載入。
5. seed 的主鍵一律是 **v4 形狀**：`uuid5(SEED_ID_NAMESPACE, f"{table}:{key}")` 的位元組，把版本位設成 `4`、variant 設成 `10xx`。`key` 取自然鍵：`user` 用 `email`、`coupon` 用 `code`、`tour` 用 `title`、`country` 用 `name`、`region` 用 `所屬國家名稱/地區名稱`；來源檔手寫主鍵的其他表用舊主鍵字面值；來源檔用 `uuid_generate_v4()` 的表（`review`、`hidden_play`、`favorite`）用該表最小的唯一欄位組合，產生時 assert 唯一。**外鍵一律依欄位名稱對應被參照的表**（`tour_id` → `tour` 的新舊對照、`coupon_id` → `coupon` 的對照，以此類推），**絕不用字串整份取代舊 id**：同一個字面值在來源檔是好幾張表的主鍵（例如 `11111111-aaaa-bbbb-cccc-111111111111` 同時是一張優惠卷、一個行程、一個國家）。
6. **`docker compose down -v` 由使用者自己執行**（`! docker compose down -v`），agent 不代跑，遇到時停下來回報。
7. 不新增任何 npm 或 Python 套件。
8. commit 規則：紅燈測試單獨一個 commit（`test: ... 🔴`），修正另外一個 commit（`fix:/feat: ... 🟢`）。每個紅燈 commit 都要把 pytest 的失敗輸出存到 `docs/reports/evidence/phase-1/<task>-red.txt`，存檔前把本機絕對路徑換成相對路徑（`sed "s#$PWD/##g; s#$PWD#.#g"`）。commit 訊息結尾加 `Co-Authored-By` 行，註明實際執行的模型。
9. 分支：沿用 P1a 的 `phase-1`（總覽 repo 與 backend 各一）。**Task 9 之前不 push、不合併、不打 tag**；Task 9 的每個對外動作都要先取得使用者同意。
10. 只用明確路徑 `git add`，不用 `git add .`／`-A`；`.claude/`、`.superpowers/` 不 commit。所有指令在總覽 repo 根目錄 `/home/nohungry/project/tripeasy` 執行，除非步驟另有註明。
11. 模型分工：每個 Task 由 Sonnet 實作；同一個 Task 連續修兩次還是紅燈，或遇到設計層級的問題，升級 Opus。每個 Task 的 review 由 Fable 和 Opus 平行進行。
12. SQL 修改後重新套用：`docker compose run --rm flyway`（repeatable migration 的內容一改就會重跑）。backend 不需要重啟。

## Review Focus

1. **保留 P1a volume 時，主鍵改寫後的 seed 會在舊資料旁邊再插一份，而且 migrate 成功。** 使用者會在 Task 2 執行 `down -v`，但之後任何人保留舊 volume 都會遇到。→ Task 2 `test_seed_natural_keys_are_not_duplicated`（自然鍵各只有 1 列，重複就紅燈）。
2. **同一個字面值是多張表的主鍵，id 對照錯表會讓外鍵指到別的資料。** FK 約束只擋「指到不存在的 id」，擋不住「指到另一筆存在的資料」。→ Task 2 `test_seed_foreign_keys_follow_column_owner`（以自然鍵驗證：seed 裡每筆 `cart_item`、`order_item`、`favorite` 指到的行程標題跟來源檔相同）。
3. **促銷期間外**：`通知狀態` 仍是 `'促銷'`，`促銷價錢` 是 `NULL`（§4.1 #9、#10），購物車和詳情頁不能用到過期的促銷價。→ Task 4 `test_tour_base_promo_price_only_in_period`。
4. **識別字大小寫**：`"user_cartList"` 等混合大小寫的 view 必須加引號建立，`restaurant_isclosed` 不能加引號，否則 controller 查不到。→ Task 4 `test_object_exists_with_exact_identifier`（查 `pg_class.relname`／`pg_proc.proname` 的確切字串）。
5. **SQL 改過後在既有 DB 上重新套用**：repeatable migration 會在既有物件上重跑，物件之間有相依（`user_cartList` 依賴 `tour_base` 等），`DROP ... CASCADE` 的順序錯了會讓 migrate 失敗、整套服務起不來。→ Task 4 `test_views_functions_file_is_rerunnable`（在 `tx` 裡把整份檔案執行兩次）。

---

## 檔案結構

| 檔案 | 責任 | Task |
|---|---|---|
| `docs/db-contract.md` | 補 §0.1 的具體值、修 final review 留下的 3 項、改 repeatable 寫法、seed 錨點 | 1、3 |
| `docs/superpowers/specs/2026-10-15-tripeasy-rebuild-design.md:123` | 3.1 第 4 步改成 repeatable 檔名 | 1 |
| `db/seed-build/build_seed.py` | 改成「解析 → 資料列改寫 → 輸出」 | 2、3 |
| `db/seed-build/extra_seed.sql`（新） | 手寫的補充資料（行程、子表、訂單、`payment`、評論），格式同 fakedata | 3 |
| `db/seed/R__seed.sql` | 由腳本重新產生 | 2、3 |
| `tests/test_seed.py` | seed 測試（v4、自然鍵、外鍵、資料目標） | 2、3 |
| `tests/test_build_seed.py`（新） | 不需 DB 的產生器單元測試 | 2 |
| `tests/db_contract.py`（新） | 21 個物件的預期識別字、參數、輸出欄位與型別（從契約抄錄） | 4、5、6 |
| `tests/dbfactory.py`（新） | 行為測試用的 `insert()` 與各表預設值 | 4、5、6 |
| `tests/test_db_contract.py`（新） | 契約層測試 | 4 |
| `tests/test_views_a.py`／`_b.py`／`_c.py`（新） | 行為層測試 | 4／5／6 |
| `tests/test_migrations.py` | 加 `R__views_functions.sql` 已套用的檢查 | 4 |
| `backend/migrations/R__views_functions.sql`（新） | 21 個物件 | 4、5、6 |
| `tests/test_api_smoke.py`（新） | API 冒煙 | 7 |
| `tests/test_product_routes.py:23–26` | 訪客清單收緊成 200 | 7 |
| `.github/workflows/ci.yml` | action 升級 | 8 |
| `docs/reports/phase-1.md`（新） | P1 報告 | 8 |
| `refs.env`、`README.md` | 版本綁定、版本對照表 | 9 |

---

### Task 1: 契約補齊（§0.1 的具體值與 final review 遺留）

**Files:**
- Modify: `docs/db-contract.md`
- Modify: `docs/superpowers/specs/2026-10-15-tripeasy-rebuild-design.md:123`

**Interfaces:**
- Produces: 契約 §0.1 新增小節「seed 目標值（定案）」，列出 Task 2、3 的測試要 assert 的具體值。後續 Task 只引用這一節，不再自己決定數值。

- [ ] **Step 1: 修正 final review 遺留的 3 項，並補 1 條 §4.2 觀察**
  - §4.2「契約已記錄、不需決定的問題」加一條：優惠卷代碼格式前後台不一致，後台新增／修改（`coupon_Validator.js:34` 的 `coupon` 只是 `Joi.string()`，`controllers/coupon.js:10,107`）不限格式，消費者使用時（`discounts_Validatior.js:9–13`）只接受 `^[A-Z0-9]{6}$`，後台建立的非 6 碼代碼消費者永遠用不了；修法是兩邊同一條規則，統一成哪條由 P6 決定。seed 依 (d2) 改成 6 碼不受影響。
  - `user_orders` 輸出欄位表的 `促銷小計`（約 `:1286`）：標註改成「名稱於 2026-10-23 final review 修正時補上，非使用者決定」，不要寫成【定案 #11】。
  - `user_favorite`（約 `:1223`、`:1234`）：寫明 `建立時間` 取自 `favorite.created_at`，不帶入 `tour_base` 的 `建立時間`／`更新時間`；`旅遊編號` 只出現一次。
  - §0.1 第 5 點加一句：新舊 id 對照依欄位所屬的表建立，不可對字面值整份取代（理由同 Global Constraints 第 5 條，附 `R__seed.sql` 現行的 3 處行號）。

- [ ] **Step 2: 改成 repeatable migration 的寫法**
  - 契約標題「（V3 views / functions）」改成「（`backend/migrations/R__views_functions.sql`）」，§0 加一行說明理由（同 Global Constraints 第 1 條）。
  - spec `:123`（3.1 第 4 步）的 `migrations/V3__views_functions.sql` 改成 `backend/migrations/R__views_functions.sql`（repeatable migration），後面加括號註明「2026-10-23 P1b 計畫改用 repeatable，理由見該計畫 Global Constraints 第 1 條」。

- [ ] **Step 3: 寫 §0.1「seed 目標值（定案）」**

依 §4 的決定，把下列每一項寫成具體值（數字、日期相對載入日的天數、狀態值），並註明依據的 §4 題號：

| 項目 | 本計畫已定的值 | Task 1 要補的 |
|---|---|---|
| 優惠卷代碼（(d2)） | `WELCOME100`→`WEL100`、`SUMMER50`→`SUM050`、`TRAVEL10P`→`TRV010`、`SPRING20`→`SPR020`、`VIP300` 不變 | `TRV010` 的 `description` 改寫成折抵金額語意（#1 定案 B）的確切文字 |
| 購物車（(d3)） | 每位 seed 使用者 1 個 `cart`；被移除的 `cart` 底下的 `cart_item` 一起移除 | 保留哪個 `cart`（寫出來源檔的 `cart_id`） |
| 首頁區塊資料量 | 首頁每個區塊在 `limit=4` 下至少 2 頁：`home.js` 用到的每組 (大分類, 小分類) 至少 5 個 `status = 1` 的行程；促銷區塊至少 5 個促銷期間內的行程 | 列出 `home.js` 實際用到的每組 (大分類, 小分類) 與促銷區塊的條件（附行號） |
| 搜尋清單 | `status = 1` 的行程至少 11 個（`product_Validator.js:75` 預設 `limit` 10，要有第 2 頁）；保留至少 1 個 `status = 2` | — |
| 熱門與收藏排行 | 每個首頁排行區塊至少 3 個行程有不同的購買數（只計 `payment_status = 1`，#4）與收藏數 | 每個行程的目標購買數、收藏數 |
| 促銷日期（#9） | 至少一筆期間內、一筆未開始、一筆已結束 | 每筆的開始／結束日期（相對載入日的天數） |
| `cart_item.start_date` | 全部晚於載入日 | 每筆的天數 |
| 收藏時間（#43） | 同一使用者的收藏時間兩兩不同 | 每筆相對載入時間的偏移 |
| `payment_status` 與 `payment`（#4–#6） | `order_item.payment_status` 的 -1、0、1、2、3、4 各至少一筆；每個已付款（1）的訂單有 1 筆 `payment` | `payment` 各欄位的值（依 V1 `payment` 表與 §4 #4–#6） |
| 點數（#3） | `新增` ＝ 訂單 `total_price` 的 10% 取整（取整方式依 #3 定案）；`減少` 的點數 × 0.8 ＝ 該訂單 `total_price - discount_price`；`user_level.travel_point` 與 `point_record` 的關係依 #2 定案 | 每筆 `point_record` 與對應訂單的值 |
| 首頁好評（#48） | `review.type = 'web'` 至少 5 則 | — |

- [ ] **Step 4: 驗證**

```bash
grep -n "seed 目標值（定案）" docs/db-contract.md
grep -n "V3__views_functions" docs/db-contract.md docs/superpowers/specs/2026-10-15-tripeasy-rebuild-design.md
```
預期：第一個找到 1 行；第二個只剩 spec 裡加註的那一行（說明改名的括號），契約裡沒有。

- [ ] **Step 5: Commit**

```bash
git add docs/db-contract.md docs/superpowers/specs/2026-10-15-tripeasy-rebuild-design.md
git commit -m "docs: P1b 開工前補齊契約（seed 目標值、repeatable migration、final review 遺留）"
```

---

### Task 2: seed 主鍵改寫（(a)、(d2)、(d3)）

**Files:**
- Modify: `db/seed-build/build_seed.py`
- Regenerate: `db/seed/R__seed.sql`
- Create: `tests/test_build_seed.py`
- Modify: `tests/test_seed.py`

**Interfaces:**
- Consumes: 契約 §0.1「seed 目標值（定案）」的優惠卷代碼、購物車。
- Produces（`build_seed.py`，Task 3 會延用）：
  - `Insert`：`dataclass(table: str, columns: list[str], rows: list[list[str]])`，`rows` 的每個值是原樣的 SQL 字面值或運算式字串（`'abc'`、`NULL`、`CURRENT_TIMESTAMP`、`uuid_generate_v4()`）。
  - `parse_inserts(sql: str) -> list[Insert]`：處理單引號字串（含 `''` 跳脫）、巢狀括號、VALUES 之間的 `--` 註解。
  - `emit(inserts: list[Insert]) -> str`：每個 INSERT 輸出 `INSERT INTO <table> (<cols>) VALUES` 加每列一行，結尾 `ON CONFLICT DO NOTHING;`，前面保留來源檔的區段標題註解（`---- N. ...`）。
  - `seed_id(table: str, key: str) -> str`：Global Constraints 第 5 條的演算法。
  - `PK_COLUMN: dict[str, str]`（表 → 主鍵欄位，取自 V1）、`NATURAL_KEY: dict[str, Callable[[dict], str]]`（表 → 從一列取出 key）。
  - `remap_ids(inserts: list[Insert]) -> list[Insert]`：先算每張表的「舊值 → 新 id」對照，再把每個欄位名稱等於某張表主鍵欄位的值（外鍵）換成那張表的新 id；找不到對照時 assert 失敗（`NULL` 除外）。

- [ ] **Step 1: 寫不需 DB 的單元測試（`tests/test_build_seed.py`）**

```python
V4 = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")

def test_seed_id_is_deterministic_v4():
    a = build_seed.seed_id("tour", "北海道雪景 5 日深度遊")
    assert a == build_seed.seed_id("tour", "北海道雪景 5 日深度遊")
    assert V4.match(a)
    assert a != build_seed.seed_id("coupon", "北海道雪景 5 日深度遊")

def test_parse_inserts_round_trip():
    # 含 '' 跳脫、巢狀括號、VALUES 之間的 -- 註解
    sql = "INSERT INTO \"t\" (a, b) VALUES\n-- note\n('it''s', (1 + 2)),\n(NULL, now());"
    [ins] = build_seed.parse_inserts(sql)
    assert ins.table == '"t"' and ins.columns == ["a", "b"]
    assert ins.rows == [["'it''s'", "(1 + 2)"], ["NULL", "now()"]]

def test_remap_follows_column_owner():
    # 同一個字面值同時是 tour 和 coupon 的主鍵
    same = "'11111111-aaaa-bbbb-cccc-111111111111'"
    inserts = [
        build_seed.Insert('"coupon"', ["coupon_id", "code"], [[same, "'VIP300'"]]),
        build_seed.Insert('"tour"', ["tour_id", "title"], [[same, "'A'"]]),
        build_seed.Insert("cart_item", ["cart_item_id", "tour_id"], [["'x'", same]]),
    ]
    out = {i.table: i for i in build_seed.remap_ids(inserts)}
    assert out["cart_item"].rows[0][1] == f"'{build_seed.seed_id('tour', 'A')}'"
```

`build_seed` 以 `test_seed.py` 既有的 `importlib` 方式載入。測試用的資料表名稱與 `PK_COLUMN`、`NATURAL_KEY` 一致。

- [ ] **Step 2: 在 `tests/test_seed.py` 加 DB 測試**

```python
SEED_EMAILS = list(SEED_USERS)
COUPON_CODES = ["WEL100", "SUM050", "TRV010", "VIP300", "SPR020"]

def test_seed_primary_keys_are_v4(db): ...
    # 對 SEED_COUNTS 的每張表，以 PK_COLUMN 取主鍵，全部符合 V4（測試新增的資料用 uuid_generate_v4()，本來就是 v4）

def test_seed_natural_keys_are_not_duplicated(db): ...
    # "user".email 在 SEED_EMAILS、coupon.code 在 COUPON_CODES、tour.title、country.name 在 seed 的值裡：每個值恰好 1 列

def test_seed_coupon_codes_match_validator(db): ...
    # COUPON_CODES 全部存在，且每個 seed coupon.code 符合 ^[A-Z0-9]{6}$（discounts_Validatior.js:9–13）

def test_seed_one_cart_per_user(db): ...
    # SEED_EMAILS 每位使用者恰好 1 個 cart

def test_seed_foreign_keys_follow_column_owner(db): ...
    # 以 tour.title 驗證：seed 的每筆 cart_item、order_item、favorite 指到的行程標題，
    # 等於來源檔中該列舊 tour_id 對應的標題（用 build_seed.parse_inserts 讀來源檔取得舊對照）

def test_seed_source_ids_are_all_remapped():
    # 來源檔裡每個手寫的 UUID 字面值都不出現在 R__seed.sql
```

`test_seed_loaded_every_table` 的 `SEED_COUNTS` 依 (d3) 更新 `cart`、`cart_item` 的筆數。

- [ ] **Step 3: 確認測試失敗，存證，commit 紅燈**

```bash
uv run pytest tests/test_build_seed.py tests/test_seed.py -v 2>&1 | sed "s#$PWD/##g; s#$PWD#.#g" | tee docs/reports/evidence/phase-1/p1b-task2-seed-ids-red.txt
git add tests/test_build_seed.py tests/test_seed.py docs/reports/evidence/phase-1/p1b-task2-seed-ids-red.txt
git commit -m "test: seed 主鍵改寫的測試 🔴"
```
預期：`test_build_seed.py` 因為函式不存在而失敗；新的 DB 測試失敗（主鍵不是 v4、代碼不符、每人 2 個購物車）。

- [ ] **Step 4: 改寫 `build_seed.py`**

流程：讀來源 → `drop_delete_block` → `parse_inserts` → 資料列改寫（優惠卷代碼與 `TRV010` 的 `description`、每人 1 個購物車；每項改寫 assert 命中的列數）→ `remap_ids` → `emit` → 既有的文字層轉換（角色、密碼 hash、日期、圖片；各自的 assert 次數依新輸出調整）→ `${` 檢查 → 加 `HEADER`。
- 移除 `fix_generated_ids` 與 `GENERATED_ID_COUNT`（位置序號的 id 由 `remap_ids` 取代）。
- `HEADER` 加一行：主鍵由自然鍵決定；改了主鍵或自然鍵，保留舊 volume 重跑會讓資料重複，要 `down -v`。
- `emit` 後 assert 輸出裡沒有 `uuid_generate_v4()`。

- [ ] **Step 5: 重新產生 seed，跑單元測試**

```bash
uv run python db/seed-build/build_seed.py
uv run pytest tests/test_build_seed.py tests/test_seed.py::test_seed_file_is_generated_from_source tests/test_seed.py::test_seed_source_ids_are_all_remapped -v
```
預期：全部 PASS。

- [ ] **Step 6: 停下來，請使用者重建 DB**

主鍵改了，舊 volume 重跑會讓資料重複（Review Focus #1）。回報並請使用者執行 `! docker compose down -v`，接著 `! scripts/ci.sh`。等使用者執行完再繼續。

- [ ] **Step 7: 確認全部 seed 測試通過**

```bash
uv run pytest tests/test_seed.py -v
```
預期：全部 PASS，包含 P1a 的 `test_seed_user_can_login`、`test_seed_admin_passes_authorize_roles`、`test_seed_is_rerunnable`。

- [ ] **Step 8: Commit**

```bash
git add db/seed-build/build_seed.py db/seed/R__seed.sql
git commit -m "fix: seed 主鍵改成由自然鍵產生的 v4，優惠卷代碼與購物車符合驗證器 🟢"
```

---

### Task 3: seed 補資料與資料目標

**Files:**
- Create: `db/seed-build/extra_seed.sql`
- Modify: `db/seed-build/build_seed.py`
- Regenerate: `db/seed/R__seed.sql`
- Modify: `tests/test_seed.py`
- Modify: `docs/db-contract.md`（seed 錨點）

**Interfaces:**
- Consumes: Task 2 的 `parse_inserts`、`remap_ids`、`emit`；契約 §0.1「seed 目標值（定案）」的每一列。
- Produces: 符合「seed 目標值（定案）」的 `R__seed.sql`；`SEED_COUNTS` 的最終值。

- [ ] **Step 1: 寫資料目標的測試（`tests/test_seed.py`）**

每個測試 assert 的數字都直接取自契約「seed 目標值（定案）」：

```python
def test_seed_home_sections_have_two_pages(db): ...
def test_seed_search_list_has_two_pages(db): ...          # status=1 ≥ 11，且 status=2 ≥ 1
def test_seed_rankings_are_distinct(db): ...              # 每個排行區塊至少 3 個不同的購買數、收藏數
def test_seed_promotions_cover_in_and_out_of_period(db): ...  # 期間內、未開始、已結束各至少一筆
def test_seed_cart_items_start_in_future(db): ...
def test_seed_favorite_times_are_distinct(db): ...
def test_seed_payment_status_coverage(db): ...            # -1、0、1、2、3、4 各至少一筆；每個已付款訂單恰好 1 筆 payment
def test_seed_points_follow_rules(db): ...                # #3：新增 ＝ 10%；減少 × 0.8 ＝ total_price - discount_price（差 < 0.01）
def test_seed_web_reviews_for_home(db): ...               # type='web' ≥ 5
```

另外把 P1a 的 `test_seed_dates_are_relative_to_load_day` 收緊：除了「不早於載入日」，再 assert 契約定的確切偏移，例如 `min(coupon.expire_date)::date - load_day` 等於定案值（P1a 已記錄的 parked 項）。

- [ ] **Step 2: 確認測試失敗，存證，commit 紅燈**

```bash
uv run pytest tests/test_seed.py -v 2>&1 | sed "s#$PWD/##g; s#$PWD#.#g" | tee docs/reports/evidence/phase-1/p1b-task3-seed-data-red.txt
git add tests/test_seed.py docs/reports/evidence/phase-1/p1b-task3-seed-data-red.txt
git commit -m "test: seed 資料量與資料目標的測試 🔴"
```

- [ ] **Step 3: 寫 `extra_seed.sql` 並接進產生器**
  - 格式與 fakedata 相同（`INSERT INTO ... VALUES ...;`），只放來源檔沒有的列：補的行程與其子表（`tour_detail`、`hotel`／`hotel_room`、`restaurant`／`restaurant_business`／`restaurant_menu`、`notification`）、訂單與訂單項目、`payment`、`favorite`、`review`。
  - 手寫主鍵用可讀的佔位字面值（例如 `'extra-tour-01'`），外鍵可以指到來源檔的舊 id；`remap_ids` 會一起換掉（Global Constraints 第 5 條）。
  - 日期一律寫成 `2025-05-20` 基準的字面值，交給既有的 `shift_dates` 平移。
  - `build_seed.py` 的 `build()` 在 `parse_inserts` 後把 `extra_seed.sql` 的 INSERT 依表名併到來源檔的同一張表（沒有的表就附加在後），再做資料列改寫。對來源檔既有列的修改（促銷日期、`cart_item.start_date`、收藏時間、訂單狀態、點數）放在資料列改寫步驟，每項 assert 命中的列數。

- [ ] **Step 4: 重新產生 seed，請使用者重建 DB**

```bash
uv run python db/seed-build/build_seed.py
```
內容改了既有列，`ON CONFLICT DO NOTHING` 不會更新，所以停下來，請使用者執行 `! docker compose down -v` 與 `! scripts/ci.sh`。

- [ ] **Step 5: 確認測試通過**

```bash
uv run pytest tests/test_seed.py tests/test_build_seed.py -v
```
預期：全部 PASS。`SEED_COUNTS` 更新成最終筆數。

- [ ] **Step 6: 契約改用 seed 錨點（§0.1 第 4 點）**

契約裡每個 `db/seed/R__seed.sql:N` 行號與寫死的 seed 識別值，改成穩定的錨點：優惠卷用 `code`、使用者用 `email`、行程用 `title`，其他資料寫「`<錨點>` 的訂單／購物車」。數值描述改成新 seed 的值。驗證：

```bash
grep -nE "R__seed\.sql:[0-9]|[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}" docs/db-contract.md
```
預期：沒有輸出（§0.1 第 5 點說明舊 id 的那一句除外，那一句改寫成不引用行號）。

- [ ] **Step 7: Commit**

```bash
git add db/seed-build/extra_seed.sql db/seed-build/build_seed.py db/seed/R__seed.sql tests/test_seed.py docs/db-contract.md
git commit -m "feat: seed 補資料量、payment 與點數，契約改用 seed 錨點 🟢"
```

---

### Task 4: A 組 9 個物件（商品與首頁）＋ 契約測試骨架

**Files:**
- Create: `tests/db_contract.py`、`tests/dbfactory.py`、`tests/test_db_contract.py`、`tests/test_views_a.py`
- Modify: `tests/test_migrations.py`
- Create: `backend/migrations/R__views_functions.sql`

**Interfaces:**
- Consumes: `tx` fixture（`tests/conftest.py`）。契約 §0「識別字對照」與 §1 各物件。
- Produces:
  - `tests/db_contract.py`：`OBJECTS: dict[str, dict]`，key 是 `CREATE` 時的識別字（與 `pg_class.relname`／`pg_proc.proname` 相同，例如 `"user_cartList"` → `user_cartList`、`restaurant_isClosed` → `restaurant_isclosed`），值是 `{"kind": "view" | "function", "args": [(名稱, 型別)], "columns": [(名稱, 型別)]}`，型別用契約寫法（`uuid`、`varchar`、`text`、`integer`、`smallint`、`bigint`、`double precision`、`numeric`、`boolean`、`timestamp`、`timestamptz`、`time`）。Task 4 只放 A 組 9 個，Task 5、6 加入其餘。
  - `tests/dbfactory.py`：`insert(conn, table: str, **cols) -> dict`，用 `RETURNING *`（`dict_row`），沒給的 NOT NULL 欄位從 `DEFAULTS[table]` 補；`DEFAULTS: dict[str, dict]` 依 V1 每張表的 NOT NULL 欄位填合理值（`email` 等要唯一的欄位用 `uuid4` 產生）。
  - `tests/test_db_contract.py` 的 `normalize_type(s: str) -> str`：去掉 `(…)` 長度，`character varying` → `varchar`、`timestamp without time zone` → `timestamp`、`timestamp with time zone` → `timestamptz`、`time without time zone` → `time`。

- [ ] **Step 1: 寫契約測試**

```python
@pytest.mark.parametrize("name", sorted(OBJECTS))
def test_object_exists_with_exact_identifier(db, name):
    # view：pg_class.relname = name 且 relkind = 'v'；function：pg_proc.proname = name（public schema）

@pytest.mark.parametrize("name", views)
def test_view_columns_match_contract(db, name):
    # pg_attribute + format_type → [(attname, normalize_type(...))]，與 OBJECTS[name]["columns"] 比較（不比順序，比集合與個數）

@pytest.mark.parametrize("name", functions)
def test_function_signature_matches_contract(db, name):
    # 參數型別：information_schema.parameters 的 IN 參數依序；輸出：parameter_mode = 'OUT' 的欄位集合
    # （RETURNS TABLE 的欄位在 information_schema 是 OUT）

def test_views_functions_file_is_rerunnable(tx):
    # 在 tx 裡把 backend/migrations/R__views_functions.sql 執行兩次，不得出錯（Review Focus #5）
```

`OBJECTS` 的 A 組內容逐欄抄自契約 §1 各物件的「輸出欄位」表與「種類」行（含定案 #26 加入的欄位）。

- [ ] **Step 2: 寫行為測試（`tests/test_views_a.py`）**

每個測試用 `dbfactory.insert` 在 `tx` 裡自己塞資料，只查自己塞的列（以 id 篩選），不依賴 seed：

| 物件 | 測試 | 斷言（依據） |
|---|---|---|
| `tour_base` | `test_tour_base_includes_inactive_tours` | `status = 2` 的行程出現，`上下架狀態 = 2`（#7） |
| | `test_tour_base_without_notification_has_null_notice` | `通知狀態`、`促銷價錢` 為 `NULL`（LEFT JOIN） |
| | `test_tour_base_promo_price_only_in_period` | 已結束的促銷：`通知狀態 = '促銷'`、`促銷價錢 IS NULL`；期間內：`促銷價錢 = promo_price`（#9、#10） |
| | `test_tour_base_promo_and_change_in_one_row` | 同時有促銷與異動：恰好 1 列，`通知狀態 = '促銷'`，`異動通知內容 = change_desc`（#8、#26） |
| `tour_travel` | `test_tour_travel_active_only_with_favorite_flag` | 下架行程不出現；收藏者呼叫時 `收藏狀態` 為 true、他人為 false；傳 `NULL` 時的值依契約輸出欄位表 |
| `tour_travel_popular` | `test_popular_counts_paid_only_and_breaks_ties` | 只有 `payment_status = 1` 計入；沒有購買的排最後；並列依 `tour_id` 升冪；下架不出現（#4、#7、#23、#24） |
| `tour_travel_most_favorited` | `test_most_favorited_ranks_and_breaks_ties` | 同上規則，依收藏數 |
| `tour_tour_detail` | `test_tour_detail_one_row_active_only` | 上架行程恰好 1 列並帶 `tour_detail` 欄位；下架回 0 列 |
| `tour_hotel` | `test_tour_hotel_one_row_per_room` | 2 個房型 → 2 列，飯店層級欄位相同 |
| `tour_restaurant` | `test_tour_restaurant_rows_are_menu_xor_opening` | 列數 ＝ 菜單數 ＋ 營業時段數；每列只有一邊有值（#34） |
| `user_user_level` | `test_user_user_level_one_row_per_user` | 新使用者恰好 1 列 |
| `user_level_review_forHome` | `test_review_for_home_only_web` | `type = 'web'` 出現，`type = 'travel'` 不出現（#48） |

- [ ] **Step 3: 加 migration 檢查（`tests/test_migrations.py`）**

```python
def test_flyway_applied_views_functions(db):
    row = db.execute(
        "SELECT success FROM flyway_schema_history "
        "WHERE script = 'R__views_functions.sql' ORDER BY installed_rank DESC LIMIT 1"
    ).fetchone()
    assert row == (True,)
```
`test_flyway_applied_v1_and_v2` 不變（repeatable migration 的 `version` 是 `NULL`）。

- [ ] **Step 4: 確認測試失敗，存證，commit 紅燈**

```bash
uv run pytest tests/test_db_contract.py tests/test_views_a.py tests/test_migrations.py -v 2>&1 | sed "s#$PWD/##g; s#$PWD#.#g" | tee docs/reports/evidence/phase-1/p1b-task4-views-a-red.txt
git add tests/db_contract.py tests/dbfactory.py tests/test_db_contract.py tests/test_views_a.py tests/test_migrations.py docs/reports/evidence/phase-1/p1b-task4-views-a-red.txt
git commit -m "test: A 組 view／function 的契約與行為測試 🔴"
```
預期：物件不存在，契約與行為測試全部失敗；`test_flyway_applied_views_functions` 失敗。

- [ ] **Step 5: 寫 `backend/migrations/R__views_functions.sql` 的 A 組**
  - 檔案開頭：說明註解（依據 `docs/db-contract.md`、repeatable 的理由），接著 21 個物件的 `DROP VIEW IF EXISTS ... CASCADE`／`DROP FUNCTION IF EXISTS ...(<參數型別>) CASCADE`（先寫全部 21 個，B、C 組的物件還不存在也不會錯）。
  - 識別字照契約 §0 的表（混合大小寫加引號，`restaurant_isclosed` 不加）。
  - function 一律 `LANGUAGE sql STABLE`，`RETURNS TABLE(...)` 的欄位名稱與型別照契約；需要 `integer` 的排行用 `::integer`（`ROW_NUMBER()` 是 `bigint`）。
  - 每個物件前一行註解：`-- 契約：docs/db-contract.md <物件標題>`。

- [ ] **Step 6: 套用並確認測試通過**

```bash
docker compose run --rm flyway
uv run pytest tests/test_db_contract.py tests/test_views_a.py tests/test_migrations.py -v
```
預期：全部 PASS。

- [ ] **Step 7: Commit（backend）**

```bash
git -C backend add migrations/R__views_functions.sql
git -C backend commit -m "feat: 🟢 建立 A 組 view／function（商品與首頁）"
```

---

### Task 5: B 組 8 個物件（購物車、訂位、折扣、結帳）

**Files:**
- Modify: `tests/db_contract.py`（加 B 組）
- Create: `tests/test_views_b.py`
- Modify: `backend/migrations/R__views_functions.sql`

**Interfaces:**
- Consumes: Task 4 的 `OBJECTS`、`dbfactory.insert`、`DEFAULTS`、`normalize_type`；A 組的 `tour_base`（`user_cartList`、`user_orderList` 依賴它）。

- [ ] **Step 1: `OBJECTS` 加入 B 組 8 個物件**（逐欄抄自契約 §2），`test_db_contract.py` 的參數化會自動涵蓋。

- [ ] **Step 2: 寫行為測試（`tests/test_views_b.py`）**

| 物件 | 測試 | 斷言（依據） |
|---|---|---|
| `user_cartList` | `test_cartlist_row_per_item_with_owner` | 每個 `cart_item` 一列，帶 `cart.user_id`；促銷期間外的價格欄位照 #10 |
| `hotel_booking` | `test_hotel_booking_always_one_row` | 找不到 (行程, 房型) 時恰好 1 列、`0`／`0`（#18）；`booking_count` 只計 #5 定案的 `payment_status` |
| `restaurant_booking` | `test_restaurant_booking_counts_by_status` | 依 #5 定案計數；`reservation_limit` 取自餐廳 |
| `restaurant_isClosed` | `test_restaurant_isclosed_always_one_row` | 營業時段內 `false`、時段外 `true`，兩者都恰好 1 列 |
| `restaurant_business_parsed` | `test_business_hours_split_per_slot` | `'11:00~14:00, 17:00~21:00'` → 2 列，型別 `time` |
| `user_couponList` | `test_couponlist_keeps_used_and_expired` | `status` 非 0 與已過期的綁定都出現 |
| `user_level_point_coupon` | `test_point_coupon_only_usable_and_keeps_user` | 只列 `status = 0` 且未過期；沒有可用優惠卷的使用者仍有 1 列、優惠卷欄位 `NULL`（#39、#40） |
| `user_orderList` | `test_orderlist_total_count_and_unit_promo` | `total_count` ＝ 同訂單項目數；#13 的運算式在 `discount_price` 為 `0` 與 `NULL` 時的結果照契約 |

- [ ] **Step 3: 紅燈存證與 commit**

```bash
uv run pytest tests/test_db_contract.py tests/test_views_b.py -v 2>&1 | sed "s#$PWD/##g; s#$PWD#.#g" | tee docs/reports/evidence/phase-1/p1b-task5-views-b-red.txt
git add tests/db_contract.py tests/test_views_b.py docs/reports/evidence/phase-1/p1b-task5-views-b-red.txt
git commit -m "test: B 組 view／function 的契約與行為測試 🔴"
```
預期：B 組 8 個物件的測試失敗，A 組照舊 PASS。

- [ ] **Step 4: 在 `R__views_functions.sql` 加 B 組**（規則同 Task 4 Step 5），`docker compose run --rm flyway`。

- [ ] **Step 5: 確認通過**

```bash
uv run pytest tests/test_db_contract.py tests/test_views_a.py tests/test_views_b.py -v
```

- [ ] **Step 6: Commit（backend）**

```bash
git -C backend add migrations/R__views_functions.sql
git -C backend commit -m "feat: 🟢 建立 B 組 view／function（購物車、訂位、折扣、結帳）"
```

---

### Task 6: C 組 4 個物件（會員與後台）

**Files:**
- Modify: `tests/db_contract.py`（加 C 組）
- Create: `tests/test_views_c.py`
- Modify: `backend/migrations/R__views_functions.sql`

**Interfaces:**
- Consumes: 同 Task 5。
- Produces: `OBJECTS` 共 21 個（12 view、9 function）。

- [ ] **Step 1: `OBJECTS` 加入 C 組 4 個物件**（逐欄抄自契約 §3，含 #11 定案的欄位表、#47 的 `使用者編號`），另加：

```python
def test_contract_lists_all_21_objects():
    kinds = [o["kind"] for o in OBJECTS.values()]
    assert (len(OBJECTS), kinds.count("view"), kinds.count("function")) == (21, 12, 9)
```

- [ ] **Step 2: 寫行為測試（`tests/test_views_c.py`）**

| 物件 | 測試 | 斷言（依據） |
|---|---|---|
| `user_favorite` | `test_favorite_keeps_inactive_and_uses_favorite_time` | 下架行程的收藏出現；`建立時間 = favorite.created_at`（#41、#43） |
| `user_orders` | `test_orders_paid_only_newest_first` | 只有 `payment_status = 1`；依 `orders.created_at` 由新到舊（#6、#45） |
| `user_order_item` | `test_order_item_exactly_one_row_with_owner` | 恰好 1 列，帶 `使用者編號`（#46、#47） |
| `user_adminList` | `test_adminlist_one_row_latest_level` | 有 2 筆 `user_level` 時恰好 1 列，取最新一筆（#22） |

- [ ] **Step 3: 紅燈存證與 commit**

```bash
uv run pytest tests/test_db_contract.py tests/test_views_c.py -v 2>&1 | sed "s#$PWD/##g; s#$PWD#.#g" | tee docs/reports/evidence/phase-1/p1b-task6-views-c-red.txt
git add tests/db_contract.py tests/test_views_c.py docs/reports/evidence/phase-1/p1b-task6-views-c-red.txt
git commit -m "test: C 組 view 的契約與行為測試 🔴"
```

- [ ] **Step 4: 在 `R__views_functions.sql` 加 C 組**，`docker compose run --rm flyway`。

- [ ] **Step 5: 確認通過**

```bash
uv run pytest tests/test_db_contract.py tests/test_views_a.py tests/test_views_b.py tests/test_views_c.py tests/test_migrations.py -v
```

- [ ] **Step 6: Commit（backend）**

```bash
git -C backend add migrations/R__views_functions.sql
git -C backend commit -m "feat: 🟢 建立 C 組 view（會員與後台）"
```

---

### Task 7: API 冒煙

**Files:**
- Create: `tests/test_api_smoke.py`
- Modify: `tests/test_product_routes.py:23–26`

**Interfaces:**
- Consumes: conftest 的 `api`、`auth_header`；seed 使用者（`SEED_USERS`，從 `test_seed.py` 匯入或複製）、seed 行程與國家（用 `db` 以 `title`／`name` 查出 id）。
- 冒煙測試只做 GET，不寫入資料，所以 P0 parked 的 `delete_user` 擴充（只清 3/11 張表）**仍不需要**；第一個寫入 `cart`／`orders` 等表的測試出現時（P2 以後）再補。

- [ ] **Step 1: 收緊訪客清單測試**

`test_guest_tour_list_is_not_blocked_by_admin_auth` 改成 `assert r.status_code == 200, r.text`，刪掉「P1a 還沒有 tour_base」的註解。同檔再加 P1a parked 的 `test_admin_patch_tour_is_reachable`：admin 對 seed 行程打 `PATCH /api/v1/admin/product/:tour_id`，回應不是 404（路由走得到）。

- [ ] **Step 2: 寫冒煙測試**

每個讀取 view／function 的 API 至少一個測試：assert 200，`data`（或該 API 的資料欄位）非空，並且契約列出、`SELECT *` 原樣輸出的欄位名稱出現在第一筆資料裡。API 路徑與參數取自契約各物件的「使用位置」：

| 物件 | API（seed 身分） |
|---|---|
| `tour_base`、`tour_travel_popular`、`tour_travel_most_favorited` | 首頁 `products` 的每組 `type`／`item`（未登入），每組帶齊必要參數 |
| `tour_travel` | 同上（以 alice 登入） |
| `tour_tour_detail`、`tour_hotel`、`tour_restaurant` | 公開詳情頁，各取一個 travel、hotel、food 的 seed 行程（同時證明 seed 行程能過 v4 驗證器） |
| `user_level_review_forHome` | 首頁好評 |
| `user_user_level`、`user_level_point_coupon` | 會員等級與點數（alice） |
| `user_cartList` | 購物車清單（alice） |
| `user_couponList` | 優惠卷清單（alice） |
| `user_orderList` | 結帳摘要（alice 的未付款訂單） |
| `user_favorite` | 收藏清單（alice） |
| `user_orders`、`user_order_item` | 已購買清單與明細（alice） |
| `user_adminList` | 管理者會員詳情（bob 查 alice） |
| `tour_base`（admin） | 管理者商品清單、促銷清單、異動資訊（bob） |
| （v4 驗證器） | `GET /api/v1/web/filter/:country_id/region`（seed 國家） |

`hotel_booking`、`restaurant_booking`、`restaurant_isclosed`、`restaurant_business_parsed` 只在寫入購物車時呼叫，冒煙不涵蓋，由 Task 5 的行為測試負責。

**已知 controller bug 不納入冒煙**（契約 §4.2「不需決定」清單已記錄，P2 以後處理）：首頁沒帶 `type` 的 500、`GET /collection/info/all` 送兩次回應、結帳 `GET /summary` 對沒有項目的訂單 500 等。遇到契約沒記錄的 500，停下來回報，不要改 controller。

- [ ] **Step 3: 確認測試結果**

```bash
uv run pytest tests/test_api_smoke.py tests/test_product_routes.py -v
```
預期：全部 PASS。這個 Task 是驗證 Task 2–6 的成果，沒有紅燈 commit；若有失敗，是 view、seed 或契約的問題，回到對應的 Task 修正。

- [ ] **Step 4: Commit**

```bash
git add tests/test_api_smoke.py tests/test_product_routes.py
git commit -m "test: P1 API 冒煙（seed 走得通原本 500／400 的 API）"
```

---

### Task 8: CI 升級、全套驗證、P1 報告

**Files:**
- Modify: `.github/workflows/ci.yml`
- Create: `docs/reports/phase-1.md`

- [ ] **Step 1: 升級 action**

`actions/checkout@v4` → `@v7`（3 處）、`actions/upload-artifact@v4` → `@v7`、`astral-sh/setup-uv@v3` → `@v10`。

- [ ] **Step 2: 本機全套驗證（seed 連續 up 兩次）**

請使用者執行 `! docker compose down -v`，接著連續兩次 `! scripts/ci.sh`（第二次保留 volume）。預期：兩次都全部 PASS，只有 P0 的 1 個 xfail（spec P1 完成標準：seed 連續 `up` 兩次都不會出錯）。

- [ ] **Step 3: 寫 `docs/reports/phase-1.md`**

照 spec 第 5 節的範本（與 `docs/reports/phase-0.md` 相同結構），涵蓋 P1a 與 P1b：
- §1 問題與修正：路由順序 2 個 bug、seed 的 4 類修正（假 hash、角色大小寫、日期、主鍵 v4／代碼／購物車），每個附紅燈 evidence 檔。`ba201e8` 是 review 後修正測試、沒有獨立紅燈，照實寫。
- §2 工作流：契約先行與使用者確認的過程（§4 的 49 + 7 題、2026-10-23 再定的 4 題）、Fable vs Opus 對照表（含 final review）、AI 出錯與人介入紀錄（例如 (d1) 前端核對找不到證據）。
- §3 測試方法：三層測試、`tx` rollback、契約抄錄成 `db_contract.py`、自然鍵 v4 id、repeatable migration。
- §4 操作指南：seed 帳號（明文密碼見 `.env.example`）、`down -v` 的時機。
- 附錄「已知限制」：權限提升（`routes/admin.js:26`，P2 前不對外開放）、已購買明細 IDOR（P5，P5 前不對外開放）、優惠卷金額運算錯誤（P4）、展示環境的 seed admin 密碼公開（P7）、`IMAGE_BASE` 寫死（P7）、契約 §4.2「不需決定」清單。
- 報告裡的檔案路徑一律用相對路徑。

- [ ] **Step 4: Commit**

```bash
git add .github/workflows/ci.yml docs/reports/phase-1.md
git commit -m "docs: P1 報告；ci: action 升級到 checkout/upload-artifact v7、setup-uv v10"
```

- [ ] **Step 5: 停下來，請使用者審閱報告**

使用者確認報告後才進入 Task 9（spec 4.4）。

---

### Task 9: 合併、打 tag、push（每個對外動作先問使用者）

**Files:**
- Modify: `refs.env`、`README.md`（版本對照表）、`docs/reports/phase-1.md`（檔頭的 tag 與 SHA、CI 結果）

- [ ] **Step 1: backend 合併與 tag（本機）**

```bash
git -C backend checkout main
git -C backend merge --no-ff phase-1 -m "Merge phase-1: P1 DB 契約"
git -C backend branch -d phase-1
git -C backend tag phase-1
```
先刪 branch 再打同名 tag（同 P0：避免 `refs.env` 的 `phase-1` 同時指到 branch 與 tag）。frontend 在 P1 沒有變動，不打 tag，`FRONTEND_REF` 維持 `phase-0`。

- [ ] **Step 2: 總覽 repo 更新版本綁定與報告檔頭**

`refs.env` 的 `BACKEND_REF=phase-1`（現在指 tag）；`README.md` 版本對照表加 P1 一列（backend `phase-1`、frontend `phase-0`、報告連結，格式同 P0 那一列）；報告檔頭填 tag 與 SHA。commit 後 `scripts/ci.sh` 再跑一次確認全綠，再合併：

```bash
git add refs.env README.md docs/reports/phase-1.md
git commit -m "docs: P1 版本綁定與報告檔頭"
git checkout main
git merge --no-ff phase-1 -m "Merge phase-1: P1 DB 契約"
```

- [ ] **Step 3: 停下來，取得使用者同意後 push**

順序：backend 先（CI 會 checkout backend 的 `phase-1` tag），再總覽 repo：

```bash
git -C backend push origin main phase-1
git push origin main
```

- [ ] **Step 4: 確認 GitHub Actions**

```bash
gh run list --repo nohungry/tripeasy --limit 1
gh run watch --repo nohungry/tripeasy <run-id>
```
預期：綠燈，且沒有 Node 20 deprecated 的 annotation。把 run id 與結果補進報告，commit、push（同樣先問使用者）。

---

## P1 完成標準（對照 spec 3.3、P1 完成標準）

- [ ] 3.0 的兩個路由 bug 已修正 → P1a Task 1；Task 7 收緊成 200
- [ ] 21 個物件全部建好 → Task 4–6，`test_contract_lists_all_21_objects`
- [ ] 契約通過雙模型審核、待確認語意已由使用者確認 → P1a Task 4–7、final review
- [ ] 三層測試在 CI 上全綠 → Task 4–7、Task 9 Step 4
- [ ] seed 連續 `up` 兩次都不會出錯 → Task 8 Step 2
