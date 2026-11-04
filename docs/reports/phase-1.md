# Phase 1：路由、seed、DB 契約、views／functions
> 2026-11-04（定稿） · backend tag `phase-1`（merge commit `e4dfeb4`；分支最後一個 commit `b0fa46c`） · frontend 維持 `phase-0`（P1 沒有改 frontend，不打 tag，`FRONTEND_REF` 仍是 `phase-0`）
>
> P1 分兩段：P1a（路由修正、seed 改寫成 Flyway repeatable、DB 契約）與 P1b（seed 主鍵與資料量、21 個 view／function、三層測試、CI）。本報告涵蓋兩段。

## 0. 摘要

P1 的目標：讓全新的本機環境 `docker compose up` 之後，seed 帳號能登入、各 API 有資料可回，且 backend 依賴的 21 個 view／function 都存在、行為有契約與測試保護。原本的資料庫只有 V1／V2 兩支 migration（25 張表與 trigger），backend 程式碼引用了 21 個從未建立的 view／function，所以多數 API 一打就 500。

| 項目 | 結果 |
|---|---|
| 測試數量 | P0 結束 13 passed + 1 xfailed → P1 結束 **195 passed + 2 xfailed**（兩個 xfail 都是 `strict=True`：P0 的 `provider_token` 欄位長度，以及 P1b 的 `GET /admin/product` 一律 500） |
| 紅燈 → 綠燈 | 路由 1 組、P1a seed 2 組、P1b seed 2 組、views／functions 3 組，共 8 個紅燈 commit，對應 8 個綠燈或修正 commit（細節見 §1）。P1b Task 7（API 冒煙）依計畫沒有紅燈 commit |
| 新增物件 | 21 個 view／function（backend `migrations/R__views_functions.sql`，760 行）；seed 由 `db/seed-build/build_seed.py` 從 `db/seed-build/tripeasy_fakedata.sql` 加 `extra_seed.sql` 產生 `db/seed/R__seed.sql` |
| 契約 | `docs/db-contract.md`：21 個物件的欄位、語意、邊界；§4.1 49 題語意確認、§4.2 a–i 與「不需決定」清單 |
| CI 結果 | 本機 `scripts/ci.sh` 乾淨狀態（`down -v`）：195 passed, 2 xfailed，exit 0（2.78 秒）；保留 volume 再跑一次：195 passed, 2 xfailed，exit 0（2.55 秒）（spec P1 完成標準：seed 連續 `up` 兩次不出錯；第二次 Flyway 看到 `R__` 檔 checksum 沒變，不會重跑，重跑安全性的證據見 §3.3）；GitHub Actions [run 41806061105](https://github.com/nohungry/tripeasy/actions/runs/41806061105)：195 passed, 2 xfailed |
| backend 變更 | 4 檔 +796 −23（`main..phase-1`） |
| frontend 變更 | 無 |
| 總覽 repo 變更 | 36 檔 +15254 −8（`main..a4182c1`，不含本報告與 CI 升級的 commit；含 seed、測試、契約、計畫與證據檔） |
| 升級 Opus 實作 | 無（沒有任何 Task 連續兩次修不好） |

Commit 範圍（`git log main..phase-1`）：

- 總覽 repo：`0d98047`（開始 P1，含此 commit）→ `a4182c1`，共 48 個 commit（不含報告 commit）。
- backend：`52e5034`（路由）、`8d08e0d` / `f1b561c`（A 組）、`46e6710`（B 組）、`4423756` / `b0fa46c`（C 組），共 6 個 commit。
- 這兩段的 backend 都是**綠燈在 backend repo、紅燈在總覽 repo**（沿用 P0）：測試放總覽 repo，所以每個紅燈 commit 只有測試與證據，修正的程式碼在 backend。
- 一個誠實的說明：`ba201e8`（seed 日期測試改以載入日為基準）是 review 後修正測試本身，**沒有獨立的紅燈 commit**——問題是測試的基準日寫錯，會在 2026-11-02 之後讓保留 volume 的環境變紅，不是 seed 資料壞掉，所以沒有「修之前真的是壞的」可以存證。

## 1. 問題與修正

行號皆為修正前（`main`）的原始碼。紅燈輸出存在 `docs/reports/evidence/phase-1/`。

### 1.1 路由順序的兩個 bug（P1a Task 1）

backend 的 `routes/product.js` 同時掛在 `/api/v1/user/product/search`（`server.js:92`）與 `/api/v1/admin/product`（`server.js:113`），裡面混了管理者與公開的路由。

**Bug A：訪客被管理者的 `auth` 擋成 401。** `routes/product.js:17`（`GET /`）與 `:20`（`GET /:tour_id`）先宣告成「管理者」版本，先註冊就先吃到請求，所以訪客呼叫公開的行程列表與詳情會回 401「請先登入」，公開版的 `GET /`（`:33`）與 `GET /:tour_id`（`:36`）永遠走不到。

**Bug B：`PATCH /status` 被 `PATCH /:tour_id` 吃掉。** `routes/product.js:23` 的 `PATCH /:tour_id` 宣告在 `:26` 的 `PATCH /status` 之前，所以「上架／下架」的請求被當成 `tour_id = "status"`，永遠進不到 `patch_tourStatus`。

**紅燈輸出**（[task1-routes-red.txt](evidence/phase-1/task1-routes-red.txt)，6 個測試 5 failed 1 passed）：

```
tests/test_product_routes.py::test_guest_can_reach_public_tour_detail FAILED
E       AssertionError: {"status":"failed","message":"請先登入"}
E       assert 401 == 404
...
========================= 5 failed, 1 passed in 0.28s ==========================
```

**修正**（backend `52e5034`，3 檔 +36 −23）：把 router 拆成 `routes/product.js`（公開）與新檔 `routes/product_admin.js`（管理者），`server.js` 把兩個前綴分別掛不同的 router：

```
 src/routes/product.js       | 23 +----------------------
 src/routes/product_admin.js | 33 +++++++++++++++++++++++++++++++++
 src/server.js               |  3 ++-
```

**綠燈**：`test_product_routes.py` 6 個測試通過（P1b Task 7 再補 admin `PATCH /:tour_id` 可達的測試，現為 7 個）；同時讓「管理者路由不會出現在 user 前綴、公開路由不會出現在 admin 前綴」成為回歸測試。

### 1.2 seed 的四類問題

來源是原專案留下的 `tripeasy_fakedata.sql`（P0 時是一個沒被 Flyway 載入的檔案）。P1a 先讓它進 Flyway 並可重跑，再修以下四類。

#### 1.2.1 先決條件：本機 DB 沒有任何 seed、重跑會讓資料加倍（P1a Task 2）

**現象**：新環境 `docker compose up` 後各表都是空的。

**紅燈**（[task2-seed-red.txt](evidence/phase-1/task2-seed-red.txt)，overview `79b1373`，3 failed）：`test_flyway_applied_seed`、`test_seed_loaded_every_table`、`test_seed_is_rerunnable`。

**綠燈**（`eed1730`）：`build_seed.py` 把 fakedata 改寫成 Flyway repeatable migration `db/seed/R__seed.sql`（每個 INSERT 加 `ON CONFLICT DO NOTHING`）。

**實作過程中發現的計畫缺陷**：implementer 的 `test_seed_is_rerunnable` 紅燈不是預期原因——`review`、`hidden_play`、`region`、`favorite` 的主鍵來源是 `uuid_generate_v4()`（110 處），`ON CONFLICT` 永遠不會觸發，所以重跑一次這四張表的資料就加倍。計畫的原型只驗過「重跑不報錯」，沒驗列數。裁定：`build_seed.py` 加 `fix_generated_ids()`，把這 110 處改成確定性 id。這個修正後來在 P1b 又被取代（見 1.2.5）。

#### 1.2.2 假的密碼 hash（P1a Task 3）

**現象**：seed 的使用者不能登入。**根因**：來源檔的 `password` 欄位是不合格式的假 hash，`bcrypt.compare` 永遠為 false。**修正**：重新產生真的 bcrypt hash（明文 `Tripeasy123`，見 `.env.example`）。測試 `test_seed_user_can_login`。

#### 1.2.3 角色大小寫不符 `authorizeRoles`

**現象**：seed 的一般會員（alice、carol）呼叫 `authRole('User')` 的 API（收藏、已購買）會被擋成 403。**根因**：來源檔把一般會員的角色寫成小寫 `user`，而 `routes/collection.js:11` 等比對的是 `User`；bob 的 `admin` 本來就對。**修正**：`build_seed.py` 的 `fix_roles()` 把 `user` 改成 `User`（2 筆）。測試 `test_seed_roles_match_authorize_roles`、`test_seed_admin_passes_authorize_roles`；後者在紅燈時失敗是因為 admin 登入 401（假 hash，見 1.2.2），不是角色問題。

#### 1.2.4 日期已過期、圖片是外部假網址

**現象**：seed 的促銷與行程日期全都在過去（來源檔基準日 2025-05-20），列表被日期條件篩光；圖片網址指向外部不存在的網址。**修正**：`build_seed.py` 以載入日為基準平移日期；圖片改指本機 `db/seed-images/` 的 SVG 佔位圖，由 backend `/uploads` 提供（網址前綴 `IMAGE_BASE` 目前寫死，見附錄；`docker-compose.yml` 把 `db/seed-images` 掛進 backend 的 `uploads/seed`）。測試 `test_seed_dates_are_relative_to_load_day`、`test_seed_uses_local_placeholder_images`。

**紅燈**（[task3-seed-data-red.txt](evidence/phase-1/task3-seed-data-red.txt)，overview `d92488a`，5 failed 4 passed）：登入、角色（兩個）、日期、圖片各一。**綠燈** `806e60a`。

**review 抓到的 Important（兩邊獨立發現）**：綠燈版本的日期測試拿 `CURRENT_DATE` 比對，但 seed 日期在載入時就固定，保留 volume 的環境從 2026-11-02 起（`SPRING20` = 載入日 +11 天）會變紅。修正 `ba201e8`：測試改以 `flyway_schema_history` 的 `R__seed.sql` 安裝時間為基準。**這一步沒有獨立紅燈**（見 §0 說明）。

#### 1.2.5 主鍵不是 uuidv4、優惠卷代碼不合格、購物車重複（P1b Task 2）

P1a 寫契約時發現（契約 §4.2 a、d2、d3），P1b 修正。

**現象**：seed 的 `tour`（10 筆）、`coupon`（5 筆）、使用者與 `country`、`region.country_id` 的主鍵是手寫的 `11111111-aaaa-…` 之類，不是 v4。購物車、結帳、折扣、已購買的驗證器只接受 `uuid({version:'uuidv4'})`（`utils/Validator/cart_Validator.js:84,92`、`checkout_Vaildator.js:4,12,71`、`discounts_Validatior.js:29` 等），所以 seed 的行程加不進購物車、優惠卷不能預覽。優惠卷代碼只有 `VIP300` 符合 `^[A-Z0-9]{6}$`（`discounts_Validatior.js:9–13`）；每位使用者有 2 個購物車，但 `controllers/cart.js:47–50` 的 `UPDATE ... WHERE user_id = $1` 會一起更新。

**紅燈**（[p1b-task2-seed-ids-red.txt](evidence/phase-1/p1b-task2-seed-ids-red.txt)，overview `63abda7`，7 failed 1 passed 10 errors）。**誠實的說明**：10 個 DB 測試是 `psycopg.OperationalError`（connection refused）的 ERROR，不是斷言失敗——當時 Docker Desktop 的 WSL 整合失效，**沒有在舊 seed 上真的觀察到這些 DB 測試的紅燈**。7 個 FAILED 的成因各不相同：`test_build_seed.py` 3 個是 `AttributeError`（新函式還沒寫）、需要 API 的 3 個（登入、admin、圖片）是 `ConnectionError`，只有 `test_seed_source_ids_are_all_remapped` 是真的斷言失敗（`R__seed.sql` 仍含來源 id）。綠燈（`d20cf86`）後使用者 `down -v` + `scripts/ci.sh` 得 37 passed 1 xfailed。

**修正**（`d20cf86`）：`build_seed.py` 改為**由自然鍵決定性產生 v4 id**（`tour:<title>`、`user:<email>`、`coupon:<code>`、`country:<name>`…，每張表各自的鍵），舊 id 對照**依欄位所屬的表**建立，不對字面值整份取代（因為來源檔同一個手寫字面值是至少 6 張表的主鍵）；優惠卷代碼改成 6 碼大寫英數；購物車每人 1 個。取代 1.2.1 的位置序號 `seed-row-{i}`，因為日後增刪 seed 列 id 才不會整批漂移，且 uuid5 產生的是 v5，會被 v4 驗證器擋下。

**因為 id 變了**：Flyway repeatable 在保留的 volume 上重跑會讓舊列與新列並存（V1 的 email、coupon.code 沒有 unique）。使用者 2026-10-23 決定**不寫 migrate guard**，改為：由使用者自己跑 `docker compose down -v`、seed 測試改成 exact count 並檢查 seed email 無重複，讓重複的 volume 直接失敗（`test_seed_natural_keys_are_not_duplicated` 等）。

#### 1.2.6 seed 資料量與資料目標（P1b Task 3）

契約 §0.1「seed 目標值（定案）」把數值先寫成具體值，測試與 seed 都只引用該節。**紅燈**（[p1b-task3-seed-data-red.txt](evidence/phase-1/p1b-task3-seed-data-red.txt)，overview `8e03f8c`，15 failed 19 passed）：每頁足夠的資料量、排名不同分、促銷期間內外都有、`payment` 各狀態、點數與訂單相符（1 點折 0.8 元、10% 回饋，§4.1 #3）、首頁好評等。**綠燈** `45db408`：新增 `db/seed-build/extra_seed.sql`（13 個新行程、20 筆訂單等），刪除來源檔的 `orders`／`order_item`／`point_record` 後重建。

### 1.3 21 個 view／function（P1b Task 4–6）

backend 的 controller 呼叫 12 個 view 與 9 個 function，V1／V2 都沒建。分三組，每組先在總覽 repo 寫契約測試（欄位名集合與個數、型別，不比欄位順序；以及行為）並存紅燈，再在 backend 寫 SQL：

| 組 | 物件 | 紅燈 | 綠燈 |
|---|---|---|---|
| A 商品與首頁（9） | `tour_base`、`tour_travel`、`tour_travel_popular`、`tour_travel_most_favorited`、`tour_tour_detail`、`tour_hotel`、`tour_restaurant`、`user_user_level`、`user_level_review_forHome` | [p1b-task4-views-a-red.txt](evidence/phase-1/p1b-task4-views-a-red.txt)（`3d6bf97`，32 failed 3 passed） | backend `8d08e0d`、`f1b561c` |
| B 購物車、訂位、折扣、結帳（8） | `user_cartList`、`hotel_booking`、`restaurant_booking`、`restaurant_isClosed`、`restaurant_business_parsed`、`user_couponList`、`user_level_point_coupon`、`user_orderList` | [p1b-task5-views-b-red.txt](evidence/phase-1/p1b-task5-views-b-red.txt)（`09d6a9d`，38 failed 20 passed） | backend `46e6710` |
| C 會員與後台（4） | `user_favorite`、`user_orders`、`user_order_item`、`user_adminList` | [p1b-task6-views-c-red.txt](evidence/phase-1/p1b-task6-views-c-red.txt)（`5f4c796`，20 failed 37 passed） | backend `4423756`、`b0fa46c` |

（12 個 view／9 個 function 的分類在 P1a 契約寫作時依 inventory 為準；P1a Task 4 發現 `tour_tour_detail`／`tour_hotel`／`tour_restaurant` 是以 `($2)` 呼叫的 function，最後在 P1a Task 7 交叉核對。）

每個紅燈證據裡「passed」那幾個是先存在的基準（例如 migration 檔存在、seed 基準測試），不是漏掉的測試。測試設計見 §3。

A 組（backend `f1b561c`）和 C 組（`b0fa46c`）的 SQL 在 review 後調整過；B 組的 review 修正只動契約與測試（`d51bf01`）。幾個值得一提的契約定案（選項與後果在契約 §4.1）：

- 優惠卷 `coupon.discount` 定為**折抵金額（NT$）**（#1 選 B）。後果：`controllers/discounts.js:38`、`checkout.js:155` 的乘法在金額語意下是錯的，記為 P4 要修的 controller bug，seed 只改 `TRAVEL10P` 的描述。
- `restaurant_isClosed` 照契約 #19（只看該星期有沒有 `restaurant_business` 列，不存在回 false）；計畫表格「時段外 true」是計畫筆誤，以契約為準。
- 購買數＝`order_item` 列數、不乘 `quantity`（controller 裁決，契約 §1 `tour_travel_popular`；兩種算法在 seed 名次相同）。

### 1.4 API 冒煙（P1b Task 7）：走得通原本 500／400 的 API

`tests/test_api_smoke.py`（25 個測試函式，`--collect-only` 共 35 個案例；其中首頁等測試有參數化）用 seed 帳號打過去，驗證 P1a 之前會 500／400 的 API 現在能回正確的資料。**依計畫明示的例外，這個 Task 沒有紅燈 commit**（冒煙測試驗的是前面各 Task 已完成的成果，單獨拿掉任一個都會紅，沒有「修之前」的單一狀態可存證）。

發現兩個契約以外、也不在 P1 範圍的 controller bug，都已記錄在契約 §4.2「不需決定」清單：

1. `GET /api/v1/admin/product` 一律 500：`middlewares/product/index.js:296` 從 `req.user` 解構 `tour_ids`，但 JWT 只有 `{ id, role }`（`controllers/userinfo.js:96,208`），`:312` 對 `undefined` 呼叫 `map` 丟 TypeError；`:312–315` 另有第二個獨立 bug。測試標 `xfail(strict=True)`，這就是第 2 個 xfail。
2. `GET /api/v1/user/product/search/:tour_id/hidden-shares` 的回應永遠沒有 `title`：`controllers/product.js:574` 寫 `title: row.type`，但 `hidden_play` 沒有 `type` 欄。冒煙測試不斷言 `title`。

## 2. Vibe coding 工作流

### 2.1 使用的 skill

| 階段 | Skill | 產出 |
|---|---|---|
| 計畫 | `superpowers:writing-plans` | `docs/superpowers/plans/2026-10-20-p1a-routes-seed-contract.md`、`docs/superpowers/plans/2026-10-23-p1b-views-seed-tests.md` |
| 執行 | `superpowers:subagent-driven-development` | 每個 Task：Sonnet implementer + Fable／Opus 雙 reviewer |

流程與 P0 相同（見 `docs/reports/phase-0.md` §2.2）：controller 產生 brief 檔 → Sonnet 實作並寫 report → controller 打包 diff → Fable 與 Opus 平行 review（Critical／Important／Minor）→ 需要修就 resume 同一個 implementer → Opus 範圍限定的 re-review。使用者逐 Task 確認才往下。

P1 新增的做法：

- **契約先行**：P1a 的 Task 4–7 不寫任何 SQL，只從 controller 的呼叫處反推 21 個物件的欄位、語意與邊界，寫成 `docs/db-contract.md`，把「無法由程式碼決定的語意」整理成待確認題，由使用者決定後才進 P1b 寫 SQL。這樣 SQL 作者不必自己選語意。
- **使用者確認**：Task 7 彙整成 §4.1 49 題 + §4.2 7 題（a、b、c、d1–d4）。2026-10-22 使用者回覆「全部採用建議，但 #1 選 B」。final review 之後 2026-10-23 又定 4 題：(d1) 前端核對沒有證據時，#11 的 5 個 view 以契約的「推測」欄位表為定案；(a) 的範圍擴及 `country` 與 `region.country_id`；保留 volume 的處理（不寫 migrate guard，改由 `down -v`＋exact count 測試）；#3 點數調成 0.8／10% 規則。2026-11-01 再定 §4.2 e–i（全部採建議 A）與兩個 view 欄位細節。
- **計畫 pre-flight 掃描**：每份計畫先對 Task 之間「產出 vs 消費」做一次掃描，P1b 的掃描確認各 Task 的產出與消費一致，只產生一個裁定（`test_build_seed.py` 的表名字串以來源檔寫法為準）。P1b Task 1（契約補齊 seed 目標值）則來自 P1a final review 的遺留裁定「殘留項目併入 P1b 第一步」，開工時就已寫進計畫。
- **紅燈證據存檔**：紅燈輸出存 `docs/reports/evidence/phase-1/`；P1b Task 3 的存證起試用 `--tb=short` 縮短輸出（Task 4–6 仍是完整 traceback）。

### 2.2 Fable vs Opus review 對照

| Task | Fable | Opus | 備註 |
|---|---|---|---|
| P1a-1 路由 | Approved（3 minor） | Approved（4 minor） | 訪客 `GET` 的測試只斷言「不是 401／403」，P1b 冒煙要求 200 |
| P1a-2 seed 改寫 | Approved（4 minor） | Approved（3 minor） | 兩邊都指出全域 uuid5 位置序號脆弱（已接受，P1b 改自然鍵） |
| P1a-3 seed 資料 | **Needs fixes**（Important） | **Needs fixes**（同一個 Important） | 兩邊獨立發現：日期測試拿 `CURRENT_DATE` 比對，保留 volume 11 天後變紅 → `ba201e8` |
| P1a-4 契約 A | Needs fixes（1 I：`tour_base` 解讀 B 的後果寫錯，`patch_tourStatus` 其實直接 UPDATE `tour`） | Needs fixes（1 I：報告宣稱 3 個 controller bug，文件只記 1 個） | 雙方都指出漏記的 controller bug |
| P1a-5 契約 B | Needs fixes（2 I：`coupon.discount` 寫入端缺漏；「點數只經過 view」不實） | Needs fixes（2 I：同一個「點數」錯誤；`PATCH /preview` 不受影響不實） | 兩個「點數」Important 是獨立發現；Opus 的第二個讓 controller 查出 seed 主鍵不是 v4（全案最重要的發現之一） |
| P1a-6 契約 C | Needs fixes（1 I：`PATCH /admin/members/roles` 缺 `authRole('admin')` 被淹沒） | Approved（0 I） | **只有 Fable 抓到提權**；controller 驗證 `routes/admin.js:26` 屬實 |
| P1a-7 契約 §4（Step 4 定案文件另由兩邊各自 Approved，0/0/4 minor） | Needs fixes（2 I：#43 丟掉 A／B／C 選項；#9 範圍漏 3 個 function） | Needs fixes（1 I：#9 選項 B 被誤寫成 controller 不用改） | #9 兩邊獨立命中；re-review 再抓到 1 個 Important（#10 同類錯誤） |
| P1a final | With fixes（2 I：frontend 沒有讀取證據；kept-volume 重複） | With fixes（4 I：v4 驗證器清單不全、kept-volume、契約不夠自足、公開的 admin 密碼） | kept-volume 兩邊獨立命中 |
| P1b-1 契約補齊 | Needs fixes（2 I） | Needs fixes（1 I） | 逐表重建／保留的處理方式（Important）；re-review 另補 1 個 Minor：訂單時間早於促銷期間，違反 #13 |
| P1b-2 seed 主鍵 | Approved（9 minor；逐格比對 476 個 PK／FK、0 錯） | Approved（6 minor） | |
| P1b-3 seed 資料 | Needs fixes（1 I） | Needs fixes（1 I） | 兩邊的 Important 都是「契約文字與 seed 實際不符」 |
| P1b-4 A 組 | Approved（8 minor） | Needs fixes（1 I：LEFT JOIN 缺測試） | 只有 Opus 抓到 |
| P1b-5 B 組 | Approved（5 minor） | Approved（6 minor） | |
| P1b-6 C 組 | Approved（4 minor） | Needs fixes（2 I：#22 最新 `user_level` 測試太弱、#45 ORDER BY 測試靠 heap 順序） | 只有 Opus 抓到，修正 `799b2a1` |
| P1b-7 冒煙 | Needs fixes（1 I） | Needs fixes（1 I） | 兩邊獨立發現：優惠卷斷言形同虛設（alice 的優惠卷 `status = 1`，view 回全 NULL 佔位列，斷言永遠成立） |
| P1b final | With fixes（0 C／1 I／8 M） | With fixes（0 C／2 I／5 M） | 兩邊都是 0 Critical，修正全是文件（本報告與契約），沒有程式碼變更；遺留 minor 沒有必須在合併前處理的。Important 兩項：報告對保留 volume 重跑與契約測試的描述都寫過頭（Opus 兩項、Fable 一項，後者與前者重疊），已在 `docs: P1 報告與契約依 final review 修正` 修正 |

觀察：雙 review 的互補價值在 P1 非常明顯——Task 6（契約 C）的提權與 P1b Task 4／6 的測試強度，都只有一邊抓到；而 #9、點數、kept-volume 重複、日期測試與優惠卷斷言這五個，則是兩邊獨立命中，等於交叉驗證。

### 2.3 升級 Opus 實作的紀錄

無。各 Task 的 fix round 都由原 Sonnet implementer 在 1–2 輪內完成；P1a final review 之後的修正（`a5dda73`）由新派的 Sonnet agent 完成；行號與文字類的小修由 controller 直接 commit（`c288c85`、`4d64224`、`4bc7c15`、`dd098b4`、`c057903`、`25c26ae`）；`a4182c1` 是 controller 補一個測試斷言（carol 優惠卷的 `user_id`）並修契約行號、補 §4.2 一行。

### 2.4 AI 出錯 / 人介入紀錄

- **計畫缺陷（P1a Task 2）**：計畫的 seed 重跑原型只驗證「不報錯」，沒驗列數，110 處 `uuid_generate_v4()` 讓四張表在重跑時加倍。implementer 的測試抓到，controller 裁定加 `fix_generated_ids()`。
- **計畫缺陷（P1a Task 3）**：計畫指令 `compose wait flyway` 在容器已結束時會失敗，改成 `compose run --rm flyway`。
- **`down -v` 一律由使用者執行**：P1a Task 2 時 agent 的 `down -v` 被權限分類器擋下；P1b 計畫把它寫成 Global Constraint 6，Task 2／3 依計畫停點請使用者跑，不由 agent 代行。
- **契約錯誤斷言被兩個 reviewer 抓到（P1a Task 4–7）**：「點數只經過這個 view」、「`PATCH /preview` 用 `coupon_id` 不受影響」、#9 選項 B「controller 不用改」都是 implementer 寫了沒驗證的斷言；controller 每次查原始碼確認後才裁定修正。
- **前端核對找不到證據（(d1)）**：契約 #11 的 5 個 view 沒有 controller 證據，原計畫要靠 frontend `phase-0` 實際讀取的 key。final review 查證後發現 frontend `phase-0` 的 `api.js` 只讀 `/auth/userinfo` 與 `/user/userinfo`，其他 view 沒有任何讀取者（`HomeView.vue:410` 是靜態資料）。controller 不自己選，交給使用者決定，使用者選「契約推測欄位表當定案」。
- **P1b Task 2 沒有在舊 seed 上觀察到 DB 測試紅燈**：Docker WSL 整合失效，見 §1.2.5。
- **controller 少跑 re-review**：以下修正由 controller 自己 diff 或逐項核對、沒再派 reviewer：P1a Task 7 fix round 2（`a380c72`，3 行）與 Step 4 小修（`dd098b4`）、P1b Task 1 fix round 2（`4c678a3`，4 行）、P1b Task 3 文字修正（`c057903`）、P1b Task 4 fix round 2（`5ee3fe9`）、P1b Task 5 修正輪（`d51bf01`）。風險是文字殘留的小錯到 final review 才會被抓到。
- **計畫與現況不符**：計畫 Task 8 預期「只有 P0 的 1 個 xfail」，但 Task 7 發現 `GET /admin/product` 500，所以預期改為 2 個。
- **action 版本只查了最新版、沒查 tag 是否存在（P1b Task 8）**：Task 8 查證「最新 release 是 v10.3.3」後寫成 `setup-uv@v10`，兩位 reviewer 也只核對了版本號，結果 `v10` 這個浮動 tag 不存在，push 後 CI 在 Set up job 失敗（run [41803860348](https://github.com/nohungry/tripeasy/actions/runs/41803860348)）。教訓：升級 action 時要確認寫進 workflow 的 ref 本身存在（`gh api repos/<owner>/<repo>/git/matching-refs/tags/<ref>`），不是只看最新版號；本機 `ci.sh` 不跑 workflow 檔，抓不到這類錯誤。
- **人工確認節奏**：使用者全程逐 Task 確認（「繼續」）才往下。

### 2.5 刻意延後的 minor（見各 Task 的 review 紀錄）

- `restaurant_business_parsed` 不處理 `24:00` 與非 `00:00` 結束的跨午夜時段（§4.2 i，選 A 維持現狀）。
- `tour_hotel`／`tour_restaurant` 的 INNER JOIN 與 `status = 1` 篩選（§4.2 e、f，選 A）。
- `parse_inserts` 會靜默丟掉非 INSERT 敘述（由 INSERT_COUNT 守）；`VALUES` 內的 `--` 註解被丟掉（`emit` 由解析後的值重新產生，只影響產出檔的註解）；紅燈存證過長。
- **「購買數 = `order_item` 列數」是 controller 裁決**（#4 只定「只算已付款」，沒定計數方式；兩種算法在 seed 名次相同）。**P3 商品開工前要變成使用者明確決定**（也記在契約 §4.2）。
- final review 的建議（未採納，無須合併前處理）：seed 的 23 個行程 `created_at` 全是同一個 `CURRENT_TIMESTAMP`，管理者端 `ORDER BY 建立時間 DESC LIMIT/OFFSET` 分頁在並列時順序不穩（契約沒定這些欄位；之後調 seed 時可給新行程錯開時間）；`test_views_c.py` 的 `EXPLAIN` 測試綁定 PG 15 的計畫節點名稱、`test_points_level_carol_has_usable_coupon` 在 volume 超過約 133 天後會變紅、`test_db_contract.py` 的參數檢查只比型別不比名稱。

## 3. 測試方法

### 3.1 三層測試

| 層 | 內容 | 檔案 |
|---|---|---|
| 1. 契約測試 | 21 個物件存在且識別字正確；view 的欄位名集合與個數、function 的參數型別與順序，與機器可讀的 `tests/db_contract.py` 一致（不比 view 的欄位順序）。`db_contract.py` 是人工從 `docs/db-contract.md` 抄錄的，沒有測試比對兩者文字，只有 `test_contract_lists_all_21_objects` 檢查物件數量（21／12／9） | `tests/db_contract.py`、`tests/test_db_contract.py`、`tests/test_migrations.py` |
| 2. 行為測試 | 在 transaction 內用 `tests/dbfactory.py` 插入情境資料，直接查 view／function，驗證 JOIN、`LEFT JOIN` 保留、期間邊界、`ORDER BY`、NULL 處理等 | `tests/test_views_a.py`、`test_views_b.py`、`test_views_c.py` |
| 3. API 冒煙 | 用 seed 帳號從 HTTP 打 API，驗證原本會 500／400 的路徑現在走得通 | `tests/test_api_smoke.py`、`tests/test_product_routes.py`、`tests/test_seed.py` |

另有 `tests/test_build_seed.py`（seed 產生器的單元測試）。P0 的 `test_health.py`、`test_storage.py`、`test_mail.py`、`test_async_errors.py`、`test_oauth_spike.py`、`test_frontend.py` 維持不動。

全部測試仍是 Python 從外部打 HTTP 與 DB、不 import backend，所以 P2 以後重寫 backend 時同一份測試繼續使用。

### 3.2 技巧

- **`tx` fixture：不自動 commit 的連線，結束一律 rollback**（`tests/conftest.py`）。行為測試在 `tx` 裡插入情境資料再查 view，結束後什麼都不留，所以不需要 `delete_user` 的 FK 順序清理，也不會污染 seed 的 exact count 測試。
- **契約抄錄成 `db_contract.py`**：契約的欄位表是給人讀的 Markdown；為了讓 view 的欄位能被測試比對，把它抄成 Python 資料結構（key 為 `pg_class.relname`／`pg_proc.proname`，所以 `restaurant_isClosed` 的 key 是小寫），抄錄是人工做的，每個 Task 的 review 以人工核對；`test_db_contract.py` 只檢查物件數量（21／12／9），不比對契約文字，所以 P2 起改 view 時要手動同步兩邊（見附錄 B）。
- **突變驗證**：implementer 故意改壞 SQL 確認測試會失敗：B 組 29 個、C 組 16 個突變全數殺死（implementer 回報；A 組在 review 後補強欄位錯位、最新通知等突變偵測）。review 後補的測試也要求能區分「SUM 與 MAX」（5 vs 3）這類易混淆的實作。
- **自然鍵 v4 id**：見 §1.2.5。`tests/test_build_seed.py` 驗證 id 決定性、跨表同一字面值不會被誤取代。
- **repeatable migration**：seed 與 views／functions 都是 `R__` 檔（`db/seed/R__seed.sql`、backend `migrations/R__views_functions.sql`）。views／functions 以 `DROP … IF EXISTS` + `CREATE` 寫成，改內容後 Flyway 依 checksum 自動重跑，不必加 V3 版本號；seed 重跑靠 `ON CONFLICT DO NOTHING`，exact count 測試保證沒有加倍。
- **seed 日期以載入日為基準**：見 §1.2.4，測試以 Flyway 的 `installed_on` 當基準日。

### 3.3 測試數量與 CI 結果

| 里程碑（逐 Task 回報的數字） | passed | xfailed |
|---|---|---|
| P0 結束 | 13 | 1 |
| P1a Task 1（路由） | 19 | 1 |
| P1a Task 3（seed） | 28 | 1 |
| P1b Task 2（seed 主鍵） | 37 | 1 |
| P1b Task 3（seed 資料） | 53 | 1 |
| P1b Task 4（A 組）／Task 5（B 組）／Task 6（C 組） | 98／138／160 | 1 |
| P1b Task 7（冒煙，含 review 修正） | 195 | 2 |
| **P1 最終** | **195** | **2** |

本機驗證（Task 8 Step 2，使用者先執行 `docker compose down -v`）：

- 乾淨狀態：195 passed, 2 xfailed，exit 0（2.78 秒）
- 保留 volume 再跑一次：195 passed, 2 xfailed，exit 0（2.55 秒）（這證明的是在既有 volume 上啟動不報錯，exact count 與 email 不重複測試通過；Flyway 只在 `R__` 檔 checksum 改變時才重跑，所以這一次並沒有重跑它們。重跑安全性的證據是 `test_seed_is_rerunnable` 與 `test_views_functions_file_is_rerunnable`（在 transaction 內重複執行檔案），以及 Task 4–6 在既有 DB 上用 `docker compose run --rm flyway` 套用修改後的 SQL）
- GitHub Actions：[run 41806061105](https://github.com/nohungry/tripeasy/actions/runs/41806061105) 綠燈，195 passed, 2 xfailed（2.50 秒），沒有 Node 20 deprecated 的 annotation，只有 `ubuntu-latest` 將遷移到 Ubuntu 26 的通知（`.github/workflows/ci.yml` 已升級 action 版本：`actions/checkout@v7`（3 處）、`actions/upload-artifact@v7`、`astral-sh/setup-uv@v10.3.3`；ci.yml 用到的 `with:` 輸入（`repository`／`ref`／`path`、`name`／`path`）在這幾個 major 之間沒有改名，`setup-uv` 沒有傳任何輸入）。第一次 push 的 run [41803860348](https://github.com/nohungry/tripeasy/actions/runs/41803860348) 在 Set up job 就失敗：`Unable to resolve action astral-sh/setup-uv@v10`——`setup-uv` 從 v8 起不再發布浮動 major tag（最後一個是 `v7`），只能寫完整版號，因此改成 `@v10.3.3`（見 §2.4）。

## 4. 操作指南

### 4.1 切到這個版本並啟動

```bash
git clone https://github.com/nohungry/tripeasy.git && cd tripeasy
git clone -b "$(grep BACKEND_REF refs.env | cut -d= -f2)" https://github.com/nohungry/tripeasy-backend.git backend
git clone -b "$(grep FRONTEND_REF refs.env | cut -d= -f2)" https://github.com/nohungry/tripeasy-frontend.git frontend
scripts/ci.sh        # 啟動全部服務並跑測試
```

（clone 指令要等 Task 9 push 之後才能使用。）需要 Docker（含 Compose v2）與 [uv](https://docs.astral.sh/uv/)；服務網址同 `docs/reports/phase-0.md` §4.1。

### 4.2 seed 帳號

`db/seed/R__seed.sql` 載入三個帳號，**明文密碼見 `.env.example` 檔頭**（同為 `Tripeasy123`）：

| 帳號 | 角色 |
|---|---|
| `alice@example.com` | `User`（有訂單、收藏、購物車、優惠卷） |
| `bob@example.com` | `admin` |
| `carol@example.com` | `User` |

登入範例：

```bash
curl -s -X POST http://localhost:3000/api/v1/auth/userinfo/login/email \
  -H 'Content-Type: application/json' \
  -d '{"email":"alice@example.com","password":"Tripeasy123"}'
```

這些帳號只供本機與展示用；展示環境不得沿用公開的 admin 密碼（見附錄）。

### 4.3 `down -v` 的時機

- **seed 主鍵（或自然鍵規則）改變後必須跑一次** `docker compose down -v`，由**使用者自己**執行。原因：Flyway 的 repeatable seed 靠主鍵 `ON CONFLICT DO NOTHING`，V1 的 email、`coupon.code` 沒有 unique，舊主鍵的列不會被覆蓋，會與新列並存。這次 P1b 的 Task 2 與 Task 3 都需要。
- 日常重跑（沒改主鍵）保留 volume 即可，`scripts/ci.sh` 兩種情況都會綠燈。若 seed 測試因筆數或 email 重複而變紅，通常就是漏跑 `down -v`。
- 疑難排解：若 `docker` 指令一開始就報 `docker could not be found in this WSL 2 distro`，是 Docker Desktop 沒啟動（或 WSL 整合失效），啟動後再跑即可（P1b 驗證時遇到兩次）。
- agent 不代跑 `down -v`（資料會被清掉，由使用者決定時機）。

## 附錄

### A. 變更檔案清單

**總覽 repo**（`git diff --stat main..a4182c1`：36 檔 +15254 −8；不含本報告與 `.github/workflows/ci.yml` 的升級），主要部分：

- 測試：`tests/test_product_routes.py`、`test_seed.py`、`test_build_seed.py`、`test_db_contract.py`、`test_views_a.py`／`b.py`／`c.py`、`test_api_smoke.py`、`db_contract.py`、`dbfactory.py`，並修改 `conftest.py`、`test_migrations.py`
- seed：`db/seed/R__seed.sql`、`db/seed-build/build_seed.py`、`db/seed-build/extra_seed.sql`、`db/seed-build/tripeasy_fakedata.sql`、`db/seed-images/*.svg`
- 契約、計畫與設計文件：`docs/superpowers/specs/2026-10-15-tripeasy-rebuild-design.md`（加入「重構規則」；§3.1 步驟 4 的 view／function 檔改寫成 repeatable `R__views_functions.sql`）、`docs/db-contract.md`、`docs/superpowers/plans/2026-10-20-p1a-routes-seed-contract.md`、`docs/superpowers/plans/2026-10-23-p1b-views-seed-tests.md`
- 設定：`docker-compose.yml`、`.env.example`、`refs.env`、`.github/workflows/ci.yml`（Task 8 升級 action，不在上列統計內）
- 證據：`docs/reports/evidence/phase-1/*.txt`

**backend**（`main..phase-1`：4 檔 +796 −23）：`src/routes/product.js`、`src/routes/product_admin.js`（新增）、`src/server.js`、`migrations/R__views_functions.sql`（新增，760 行）。

### B. 已知限制

以下都是 P1 發現、依計畫**沒有在 P1 修**的問題，已全部記錄在 `docs/db-contract.md` §4.2 與各物件的「邊界」。

**安全項目（修好之前不對外開放）**

- **權限提升**：`routes/admin.js:26` 的 `authRole('admin')` 被註解掉，`PATCH /api/v1/admin/members/roles` 只剩 `auth`；任何已登入帳號都能把任何註冊帳號（含自己，目標 id 須為 v4／v5）改成 `admin`（`controllers/admin.js:59` 原樣 UPDATE `user.role`）。**P2 之前不對外開放。**
- **已購買明細的擁有者檢查（IDOR）**：`GET /api/v1/user/purchases/info/:order_item_id` 的 `middlewares/purchases/index.js:31` 與 `controllers/purchases.js:59` 只用 `order_item_id` 查，沒有 `user_id` 條件，任何登入的 `User` 都能讀任何 `order_item`（清單端點已限定本人）。**P5 之前不對外開放。**
- **展示環境的 seed admin 密碼公開（P7）**：`bob@example.com`（`admin`）的 `Tripeasy123` 公開在 `.env.example:1–3`，但 seed 會在本機與展示環境載入。公開展示前要改成由環境變數注入，或展示環境不載入 seed 管理者。

**功能項目**

- **優惠卷金額運算錯誤（P4）**：`coupon.discount` 定為折抵金額（§4.1 #1 選 B），但 `controllers/discounts.js:38`、`controllers/checkout.js:155` 做 `total_price * discount`，會算出數百倍金額（例：3576.74 × 100.0 = 357,674）。要改成 `total_price - discount`。
- **`IMAGE_BASE` 寫死（P7）**：seed 圖片網址的前綴 `db/seed-build/build_seed.py` 的 `IMAGE_BASE`（`:90`）是 `http://localhost:3000/uploads/seed`，部署到非本機環境時圖片會壞，需與展示環境的 seed 管理者一併處理。
- **`GET /api/v1/admin/product` 一律 500**：兩個獨立 bug（`middlewares/product/index.js:296`、`:312–315`），冒煙測試以 `xfail(strict=True)` 標記，修好會 XPASS 提醒移除。
- **隱藏玩法回應沒有 `title`**：`controllers/product.js:574` 寫 `row.type`，應為 `row.title`（P3）。

**契約 §4.2「不需決定」清單**（摘要；完整內容與行號見 `docs/db-contract.md` §4.2「契約已記錄、不需決定的問題」）：

- 首頁沒帶 `type` 時整個回 500（`middlewares/home/index.js:7`、`home.js:86`）；詳情頁找不到行程、已下架時回 500 而非 404（`product.js:178–202`、`:209`）。
- 餐廳額滿檢查第 1 個參數恆為 `NULL`（`middlewares/cart/index.js:73,208`）。
- 購物車：`cart.js:47–50` 更新使用者所有購物車；`cart.total_price` 與 `summary.total_price` 各自計算；list 不輸出 `cart_item_id`。
- 結帳：只有購物車第一個項目進入 `order_item`（`checkout.js:20–33,42–56`）；付款 `newebpay.js:82,213` 對 `order_item` 寫不存在的 `payment` 欄位，交易 ROLLBACK。
- 優惠卷與點數：沒有任何程式把 `user_coupon.status` 設成 1、增加點數或把 `減少_確認中` 轉成 `減少`；`used_point` 驗證器沒有 `.integer()`。
- 角色大小寫：管理者降權成 `user` 後通不過 `authRole('User')`（`routes/collection.js:11`、`routes/purchases.js:11,17`）。
- 收藏：`GET /collection/info/all` 每次送兩次回應；`POST` 的 `tour_id` 不驗 UUID。
- 優惠卷代碼格式前後台不一致（後台不限格式，消費者只接受 `^[A-Z0-9]{6}$`）。
- 是否補唯一約束（`notification`、`user_level`、`favorite`、`coupon.code`，§4.2 d4）；P1 選 A 不補。
- 契約 §4.2 e–i（`tour_hotel`／`tour_restaurant` 的 `status = 1` 篩選與 INNER JOIN、促銷期間 `now()` 與 naive timestamp 的時區、B 組的 booking_count 算法、`24:00` 時段）：使用者 2026-11-01 全部選 A（維持現狀）。

- **`R__views_functions.sql` 的 DROP 清單是寫死的（P2／P7）**：函式簽章若日後改變，必須同時保留舊簽章的 `DROP` 行，否則舊的 overload 會留在 DB（`test_object_exists_with_exact_identifier` 在保留 volume 上會抓到，CI 的全新 DB 抓不到）；DROP 用 `CASCADE`，P2 以後若有物件依賴這些 view，下次 migrate 會被默默一併刪除；P7 若用原專案的 DB 當基礎，裡面手工建立的同名物件（簽章或引號不同）這支檔不會清掉。
- **`tests/db_contract.py` 與 `docs/db-contract.md` 沒有自動比對（P2 起）**：改 view 或 function 時，要同時更新兩邊（對應 spec 的重構規則）；可選的補強是寫一個小 parser 比對「輸出欄位」表。

**P0 遺留**：`delete_user` 只清 3 張子表、未知 Origin 仍回 500、`provider_token VARCHAR(255)`（P2 改 `TEXT`）等，見 `docs/reports/phase-0.md` 附錄。
