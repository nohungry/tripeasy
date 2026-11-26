# P5 會員中心 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> 狀態：**已核准（2026-11-26 使用者核准）**（2026-11-26；R1–R4 與後續 R5–R7 已由主對話裁決，見「Ruling」；計畫階段的修訂已寫入 spec §12）

**Goal:** 會員中心從前端完整操作：我的訂單（全狀態、明細、繼續付款）、點數紀錄與等級、通知設定、收藏（愛心、收藏頁）；修掉越權讀取（契約 §4.2 (c)）、V6 補三個唯一約束、姓名規則統一、P4 留下的項目；最後寫 P5 報告。

**Architecture:** DB 用 versioned migration `V6` 補 `favorite`／`cart`／`auto_setting` 的唯一約束，`R__views_functions.sql` 的 4 個詳情／列表 function 多輸出 `收藏編號`。後端新增兩支唯讀 router（`/user/orders`、`/user/points`），金額一律呼叫 `utils/trade.js::computePayable`，期限與「付款進行中」的判斷從 `trade.js` 抽出共用片段；收藏、通知設定、已購買明細就地修正。新的共用模組：`utils/nameRule.js`（姓名規則）、`utils/Validator/paging_Validator.js`（分頁）、`utils/orderStatus.js`（狀態中文）。前端在 `userprofilePage.vue` 以 `?tab=` 切換四個分頁，新增共用元件 `FavoriteHeart.vue`。

**Tech Stack:** Express 4.21 + raw `pg` + Joi 17、PostgreSQL 15、Flyway 10.20.1、Vue 3 + vue-router（hash）+ axios + sweetalert2、Python 3.13 / uv / pytest 8.3.3 / requests / psycopg 3.2.3 / pytest-playwright 0.5.2。**不新增任何套件。**

**Spec:** `docs/superpowers/specs/2026-11-26-p5-member-center-design.md`（以下稱「spec」）；上位 `docs/superpowers/specs/2026-10-15-tripeasy-rebuild-design.md`（「總 spec」）。契約 `docs/db-contract.md`。上鎖順序 `docs/lock-order.md`。前一階段 `docs/reports/phase-4.md`（「P4 報告」）附錄 B。

## 與 spec 的差異（起草時讀碼，基準 backend `0e3b192`、frontend `bfd20f0`、總覽 `6716d6c`）

**起草時待裁決的項目（2026-11-26 主對話已裁決，以下方「Ruling」為準；表內括號是起草時的預設，已被 Ruling 取代）**

| # | 差異 | 證據 | 影響與預設 |
|---|---|---|---|
| R1 | **seed 的 `auto_setting` 有重複**（spec §12 第 1 點）：alice 兩列（`1111aaaa…` early 0／flexible 1／Japan／Tokyo／1200.5；`4444dddd…` early 1／flexible 0），`created_at` 相同。spec §3 對 cart／auto_setting 規定「有重複就停下回報、不自動合併」。 | `db/seed-build/tripeasy_fakedata.sql:842-889`；起草時 DB 查詢 `auto_dup = 1`、favorite／cart 無重複 | Flyway 順序是 V1–V5 → `R__seed` → `R__views`（`flyway_schema_history` rank 6、7），乾淨 volume 上 V6 先建約束、`R__seed` 再插入就會失敗，**seed 來源一定要改**。（預設：`build_seed.py` 新增改寫，保留 `1111aaaa…` 並設 `early_notify = 1`、刪 `4444dddd…`；`test_seed.py:23` 4 → 3；使用者 `down -v`。V6 對 cart／auto_setting 只做預檢、有重複就 `RAISE EXCEPTION`，不自動合併。） |
| R2 | **「P3 的地區資料」有兩個來源**：`country`／`region` 表是中文（日本／東京），`tour.country`／`region` 與 seed 的 `auto_setting` 是英文（Japan／Tokyo）。P3 N5 因此移除了搜尋的國家下拉。 | DB 查詢；`docs/reports/phase-3.md:388` | （預設 **B**：以 `country`／`region` 表為準，前端用既有的 `GET /web/filter/countries`、`/:country_id/region`，不新增 API；seed 的英文舊值仍可讀出，但重新存檔時必須改選清單中的值；`region` 表中芬蘭、義大利、德國等國沒有地區，這些國家無法開啟價格追蹤。中英對照留給 P6 的 N5。另一選項 A：以 `tour` 的 distinct (country, region) 為準，要新增一支唯讀 API 供下拉。） |
| R3 | **註冊與 Google 新會員都寫一筆 `新增`、`point = 0`、`order_id` NULL**，照 spec §4.3 的對應會顯示「購物回饋 +0」。 | `controllers/userinfo.js:37`、`:213` | （預設：點數紀錄 API 排除 `point = 0` 的列。） |
| R4 | **姓名規則的字元集**：spec §6 只規定長度；現行三處都另外禁止空白與符號（註冊、會員資料 2–5 字，結帳 2–10 字），Google 名字常含空白（測試用的 `Google 測試員` 也是）。 | `userInfo_Validator.js:4`、`userprofile_Validator.js:3`、`checkout_Vaildator.js:23`、`frontend/src/utils/function.js:29-41` | （預設：**只檢查長度**，去頭尾空白後 2–20 個 Unicode 字元，中間空白與符號都允許；否則 Google 名字截斷後仍過不了結帳。） |

**Ruling（2026-11-26 主對話裁決，具約束力）**

- **R1** Ruling: alice 的兩筆 `auto_setting` 在 seed 來源合併成一筆；每個開關欄位取 `updated_at` 較新那筆的值，`updated_at` 相同或沒有時取 `auto_setting_id` 較小那筆（seed 兩筆的時間相同，所以結果是 `1111aaaa…` 的值：early 0、flexible 1、Japan、Tokyo、1200.5，刪 `4444dddd…`）；同步改 `tests/test_seed.py:23`（4 → 3）與契約 — 理由：V6 的唯一約束與 Flyway 順序（V6 先於 `R__seed`）讓重複列無法存在，規則固定、可重現 — 若錯的代價：alice 的 `early_notify` 從 1 變 0，展示時「出發前提醒」顯示未勾選。Task 1 完成後**必須提醒使用者自己執行 `docker compose down -v`**，主對話不會代為執行。（Task 1）
- **R2** Ruling: 價格追蹤的 `country`／`region` 只接受前端選單實際會送出的值。起草時查證：P3 的搜尋篩選器已移除國家／地區下拉（frontend `84e36a9`；舊下拉是寫死的「台灣／台北市…」），搜尋 API 的 `country`／`region` 參數比對的是 `tour` 的 `所屬國家`／`所屬地區`（英文，`controllers/product.js:48-55`）；`automaticSetting.vue` 是空頁，不送任何值；seed 的 `auto_setting` 存英文（Japan／Tokyo、France／Paris，兩組都存在於上架行程）。兩邊是同一套 → **以上架行程（`tour.status = 1`）的 distinct `(country, region)` 為準**；新增唯讀 `GET /api/v1/user/automation/regions` 供下拉，驗證用同一段 SQL — 理由：選單與驗證同源、與 seed 及搜尋參數一致，P6 價格追蹤比對 `tour` 時不需中英對照 — 若錯的代價：多一支唯讀 API；`country`／`region` 中文表在本階段不使用。Task 0 Step 8 再查證一次，不符就停下回報。（Task 0、Task 6；spec §12 第 2、3 點）
- **R2a（地區下架）** Ruling: 讀取設定時，存著的國家或地區若已不在選單（沒有上架行程），表單仍把該值列為選項並維持選取，後面標註 `（目前沒有上架行程）`；寫入驗證改成「值在上架清單中，**或**與該會員目前存的值完全相同」就通過 — 理由：會員什麼都沒改，存檔卻被擋下，會讓人以為系統壞了 — 若錯的代價：已沒有上架行程的地區可能被長期保留，P6 的排程只是比對不到任何東西。（Task 6；spec §12 第 4 點）
- **R3** Ruling: 點數紀錄 API 在 SQL 就排除 `point = 0`，前端不另外過濾；測試含「新註冊會員的點數紀錄是空列表」 — 理由：註冊時寫的 `新增 0` 不是購物回饋，顯示出來會誤導 — 若錯的代價：真的 0 點紀錄（目前程式不會產生）也看不到。（Task 5）
- **R4** Ruling: 姓名只檢查長度：去頭尾空白後 2–20 個 Unicode 字元，不限字元種類（允許空格、英文、符號）；另外拒絕控制字元 `\p{Cc}`，訊息 `「姓名」不得包含控制字元`。Google 名字先移除 `\p{Cc}`，再套 spec §6 的截斷與後備規則 — 理由：Google 名字常含空格，限制字元種類會讓截斷後的名字仍過不了結帳；控制字元會破壞顯示與日誌 — 若錯的代價：名字可含 emoji、符號，前端版面要能容納。（Task 2；spec §12 第 6 點）
- **R5（審查）** Ruling: 全部 Task 都雙審（reviewer-opus＋reviewer-fable 平行）— 理由：使用者 `~/.claude/CLAUDE.md` 的門檻是「跨多檔，或動到 CI 設定」，Task 0 改 `refs.env`（CI 設定），其餘每個 Task 都跨多檔 — 若錯的代價：審查成本加倍。（GC19）
- **R6（負點數擴大範圍）** Ruling: `controllers/userinfo.js` 註冊 `:57`、Email 登入 `:123`、Google 登入 `:249`、`get_user_loginStatus` `:379` 回傳的 `points`（值為 `travel_point`）改成 `Math.max(0, …)`，DB 不變；Email 登入與 loginStatus 寫測試，註冊與 Google 登入只回新會員（不可能為負）讀碼確認 — 理由：spec 反目標「會員中心的任何地方都不顯示負點數」 — 若錯的代價：只多 4 處 clamp。（Task 5；spec §12 第 10 點）
- **R7（R__ 檔改 function 簽章）** Ruling: Task 7 依賴 `R__views_functions.sql:24-29` 的 `DROP FUNCTION IF EXISTS … CASCADE` 才能增加 `RETURNS TABLE` 的欄位；加一步在既有 volume（不 `down -v`）上跑 migration，確認 Flyway 重跑 R__ 檔且成功，被 CASCADE 一起刪掉的物件若沒有重建就停下回報。（Task 7；spec §12 第 7 點）

**Ruling F1–F26（2026-11-26 開工前衝突掃描，主對話裁決，具約束力）**

- **F1**：列表與明細多回 `can_continue_payment`（狀態 ∈ {-1, 0}、SQL `now() < deadline`、且非付款進行中）與 `is_overdue`（狀態 ∈ {-1, 0}、`now() >= deadline`、且非付款進行中）兩個布林；前端只讀這兩個布林，`deadline` 只顯示（GC17、spec §4.2 不讓前端算期限）。（Task 3、4、Review Focus 2）
- **F2**：R2a「與目前存的值相同就通過」也適用 `max_price`；seed 的 `1200.5` 保留。（Task 6）
- **F3**：舊 `/user/purchases/info*` 維持現有行為，只修越權與 `:34`；撤回「本人未付款回 404」（本人未付款仍回 200 `查無資料`）。Task 0 查證 `user_order_item` 的欄位與 `payment_status` 篩選。（Task 0、3）
- **F4／F5**：收藏列表不分頁，伺服器端上限 100 筆、新到舊，回 `{ data, total }`（`total` 為實際總數）；前端不做分頁 UI。記入 spec §12。（Task 7、8）
- **F6**：regions 是查找清單，不套用 `{ data, total }`（共用約定例外）。（Task 6）
- **F7**：automatic redirect 測試移到 Task 4，只斷言 URL 與 `tab` 參數。
- **F8、F11、F18、F19、F20、F22**：照掃描建議改計畫文字（F11：補 SWEEP_JS target，並把 `tests/test_member_auth.py` 列進 Files；F19：紅燈指令明列檔案；F20：補 `test_delete_bad_uuid_is_400`；F22：報告大綱列出全部 R、D、F 裁決）。
- **F9**：spec §12 記錄 §7.1 的理由已被 D7 改變（列表改讀 `computePayable`），決定本身（逾時／取消清空折扣欄位）維持。（Task 9）
- **F10**：補 tie-break 測試（`updated_at` 相同取 id 較小者），合併函式改通用名稱 `merge_duplicate_auto_settings`；回饋比例若 `pointslevel` 或其他 API 有回傳就從 API 讀（Task 0 查證），沒有則前端寫死 10%，並在 spec §12 記為偏離 spec。（Task 0、1、5）
- **F12**：Task 5 引用 `controllers/userinfo.js` 以函式名為錨點。
- **F13**：前端 `get_orders`、`get_point_records` 呼叫時明確傳 `limit: 10`；後端預設 4 不改。（Task 4、5）
- **F14／F15／F21**：掃描列出的查證項目全部併入 Task 0 Step 9；`isMemberApi` 若是前綴比對，Task 5、6 把新 URL 前綴加進去（起草時讀碼：`frontend/src/utils/api.js:32-42` 是 `startsWith` 前綴比對）。
- **F16**：檢查與移除各用一個 regex，檢查用的不加 `g`（避免 `lastIndex` 狀態）；補「會員資料存入去頭尾空白後的值」測試。（Task 2）
- **F17**：E2E 涵蓋輸入 21 字被擋（註冊、會員資料、結帳）。（Task 2）
- **F23**：mutation 驗證用 `git stash` 或 patch 檔，還原後 `git status --short` 必須乾淨。（Task 9）
- **F24**：負點數情境改由退款流程造成（沿用 P4 helper），不直接設 DB。（Task 5）
- **F25／F26**：紅燈步驟中的併發測試至少跑 10 次；10 次都沒紅，就在 evidence 照實記錄。（Task 1、6、7）

**已確認、計畫直接處理（不需裁決）**

| # | 差異 | 證據與處理 |
|---|---|---|
| D1 | Header 死連結：桌機會員選單 3 個是 `router-link to="#"`（不是 `href`）；手機選單的「購物車」也是 `to="#"`；沒有收藏頁連結。 | `HeaderComponent.vue:68-70`、`:119`。Task 4 全部接上（`HeaderReal.vue` 沒有被引用，不動）。 |
| D2 | spec 說「4 個 view」，實際是 4 個 SQL function（`tour_travel(uuid)`、`tour_tour_detail(uuid)`、`tour_hotel(uuid)`、`tour_restaurant(uuid)`），改 `RETURNS TABLE` 要靠檔頭既有的 `DROP FUNCTION`。搜尋 API 原樣輸出 function 的欄位（鍵是 `收藏狀態`，不是 `is_favorited`），所以搜尋卡片讀 `收藏編號`。 | `R__views_functions.sql:112,223,326,428`、`controllers/product.js:117-150`。Task 7。 |
| D3 | 加上 `cart UNIQUE(user_id)` 後，舊的「查不到就 INSERT」在併發首次加入時會撞約束回 500，所以 spec §7.2 的 `ON CONFLICT` 改寫**提前到 Task 1**，和 V6 一起交付。 | `controllers/cart.js:26-37` |
| D4 | 收藏 `POST` 找不到行程回 **400** `查無此項目`、重複收藏回 400；`DELETE` 非本人回 **400**。spec 要 404／200。 | `middlewares/collection/index.js:46-55`、`:68-80`、`:102-113`。Task 7。 |
| D5 | 前端沒有任何地方呼叫 `/user/purchases/*` 與 `/user/automation/*`。 | `grep` frontend `src`：無。spec「前端改用新 API」無事可改；SMALLINT → 布林的輸出改動沒有其他呼叫者。 |
| D6 | `test_async_errors.py` 的目的是「try 外 reject 要回 500」，收藏修好後該路由回 400，必須換一個仍在 try 外 reject 的路由；找不到就停下回報。 | `tests/test_async_errors.py:1-18`。Task 7。 |
| D7 | 訂單列表的折扣類型與金額改由 `computePayable` 回傳（spec §7.1 的理由說列表「直接顯示」欄位）；§7.1 的清空照做，但列表不依賴它。 | GC12 |
| D8 | 本計畫引用到的 spec 行號，起草時逐一讀過，與程式一致；`"user".name` 是 `varchar(255)`，20 字不需加寬；`paymentInProgress` 實際範圍是 `trade.js:147-158`；`userinfo.js:202` 是 INSERT 語句、參數在 `:203`；`docs/lock-order.md` 全部 `file:line` 與 backend `0e3b192` 一致（Task 0 Step 3 再核一次）。 | — |
| D9 | `/admin/personalOrder` 仍是空頁（spec 未提），本計畫不動，記入報告附錄 B。 | `router/index.js:128-131` |

## Global Constraints

1. **分支**：總覽、backend、frontend 都開 `phase-5`（總覽與 backend 從 `main`，frontend 從 `dev`）；`refs.env` 改 `BACKEND_REF=phase-5`、`FRONTEND_REF=phase-5`（Task 0）。每個 Task 的「Commit」寫明 repo。
2. **不 push、不合併、不打 tag**；這些由主對話另外詢問使用者。
3. **commit 規則**（總 spec §4.1）：紅燈測試單獨 commit（`test: … 🔴`，總覽 repo），修正另一個 commit（`fix:／feat: … 🟢`，backend 或 frontend；seed 與測試在總覽）。紅燈輸出存 `docs/reports/evidence/phase-5/task-N-red.txt`（多段 `task-N-red-<主題>.txt`），存檔前 `sed "s#$PWD/##g; s#$PWD#.#g"`，用 `--tb=short`。commit 結尾加 `Co-Authored-By`，寫實際執行的模型。標「回歸測試」者預期一開始就綠，commit 訊息註明。
4. **TDD 例外**：Task 0（查證）、Task 10（文件、報告）。
5. 只用明確路徑 `git add`；`.claude/`、`.superpowers/` 不 commit。ledger 在 `.superpowers/sdd/2026-11-26-p5-member-center/`。
6. 指令在 `/home/nohungry/project/tripeasy` 執行。服務 `docker compose up -d --build`；改 migration 後 `docker compose run --rm flyway`。
7. **`docker compose down -v` 由使用者執行**，agent 需要時 ⛔ 停下回報。
8. **不新增套件**（backend、frontend、Python 都是）。
9. **`.env` 不可修改**（只有使用者能改）。
10. **seed 帳號唯讀**：alice／bob／carol 不得用於任何寫入（含收藏 POST／DELETE、通知設定 PATCH、加購物車、建單、付款、summary）。本階段新增的 `GET /user/orders*`、`GET /user/points/records`、`GET /pointslevel`、`GET /allnotifi-settings`、`GET /collection/info/all` 是唯讀，可以對 seed 帳號呼叫。需要寫入的測試一律 `make_user`。
11. 動到 schema、seed、view／function 就同步更新 `docs/db-contract.md` 與 `tests/db_contract.py`、契約測試。
12. **應付金額只有一個實作**：`utils/trade.js::computePayable`（P4 GC12）。訂單列表、明細的 `total_price`、`promo_subtotal`、`discount_type`、`discount_amount`、`payable` 全部取自它，**不得讀 `orders.discount_price`**；列表對當頁每筆呼叫一次（`limit` 上限 50）。
13. **上鎖順序**以 `docs/lock-order.md` 為準（P4 GC14）。新增或修改任何開交易、或碰到其中表格的寫入路徑，同一個 Task 內更新該文件（鎖哪些表、什麼鎖、`file:line`、為什麼無環）。會員端的讀取 API **不開交易、不加鎖、不寫入**（不呼叫 `expireIfOverdue`）。
14. **驗證訊息**：新增或修改的 middleware 一律以 `utils/Validator/joiMessage.js::userMessage()` 取訊息，不得讀 `error.details`／`.message`；同一個 Task 把它加進 `tests/test_validator_sweep.py` 的兩份清單：`SWEEP_JS` 的 `targets`，以及 `test_middlewares_read_joi_errors_only_through_user_message` 的 parametrize（整檔或比照 `_search_handler_source` 切出單一 handler）。訊息不含參數名、不含 ASCII `"`。
15. **`authRole('User')`**：所有新增或修改的會員端點都在 `auth` 之後掛 `authRole('User')`；未登入 401 `請先登入`，admin 403 `您沒有權限進行此操作`。
16. **擁有者條件寫在 SQL**（`WHERE … AND user_id = $me`）；查無一律 404，不先查出再比對。
17. backend `TZ=UTC`（compose 設定，P4 R6）不動；期限與時間比較一律在 DB 用 `now()`。
18. **測試數以實際執行為準**：報告與 ledger 的 passed 數只抄 `pytest`／`scripts/ci.sh` 的輸出，不估算。
19. 審查（`~/.claude/CLAUDE.md`，R5）：**每個 Task（0–10）都雙審**：reviewer-opus 與 reviewer-fable 平行審、互不看對方結果，由主對話比對（依據：跨多檔，或動到 CI 設定 `refs.env`）。同一 Task 連續修兩次仍紅，先諮詢 advisor。
20. E2E 一律 `wait_until="domcontentloaded"`，不用 `wait_for_timeout`；等 API 用 `page.expect_response`。
21. **行號基準**：本計畫的 `file:line` 以起草基準（backend `0e3b192`、frontend `bfd20f0`、總覽 `6716d6c`）為準；前面的 Task 改過同一檔案後，以函式名或引用的文字為錨點。

### 共用約定（多個 Task 引用，值不得更改）

| 名稱 | 值 |
|---|---|
| migration | `backend/migrations/V6__p5_member_center.sql`；約束名 `favorite_user_tour_key`、`cart_user_id_key`、`auto_setting_user_id_key` |
| function 新欄 | `"收藏編號" uuid`（未收藏或未登入為 NULL），加在 `tour_travel`、`tour_tour_detail`、`tour_hotel`、`tour_restaurant` 的 `收藏狀態` 之後；詳情 API 輸出鍵 `favorite_id` |
| 新 API | `GET /api/v1/user/orders`、`GET /api/v1/user/orders/:order_id`、`GET /api/v1/user/points/records`、`GET /api/v1/user/automation/regions`（後者掛在既有 `routes/automation.js`；router `routes/orders.js`、`routes/points.js`，在 `server.js` 掛載） |
| 分頁 | `paging_Validator.js::pagingSchema`：`page` 預設 1、`limit` 預設 4、上限 50、`lang` 預設 `zh-TW`；訊息沿用 `cart_Validator.commonSchema`，加 `「每頁筆數」不可超過 50` |
| 列表回應 | `dbdata = { data: [...], total: number }`（物件包裝，空列表也帶 `data: []`；`resStatus` 對空陣列會省略 `data`）。適用訂單、點數紀錄、收藏（收藏不分頁、上限 100，F4／F5）。**例外**：`GET /user/automation/regions` 是查找清單，`dbdata` 直接是陣列（F6） |
| 訂單狀態中文 | `-1`、`0` → `待付款`；付款進行中 → `付款處理中`；`1` 已付款、`2` 已取消、`3` 已退款、`4` 已逾時 |
| 付款紀錄結果 | `payment_status = 1` → `成功`；`result_time` 不為 NULL → `失敗`；仍在交易時限內 → `處理中`；其他 → `未完成` |
| 點數原因 | `新增` 購物回饋、`減少` 點數折抵、`退款收回` 退款收回回饋、`退款退回` 退款退還折抵；其他原樣；`減少_確認中` 與 `point = 0` 在 SQL 排除（R3） |
| 姓名規則 | 去頭尾空白後 2–20 個 Unicode 字元（`[...s].length`），不限字元種類；含 `\p{Cc}` 拒絕（R4）；訊息：空白 `「姓名」不得為空白`、長度 `「姓名」需為 2 到 20 個字`、控制字元 `「姓名」不得包含控制字元`、缺少 `「姓名」為必填欄位`、型別 `「姓名」必須是文字` |
| Google 名字 | 先移除 `\p{Cc}`；去空白後 ≥ 2 字 → 取前 20 字；否則 email `@` 前段取前 20 字；前段仍 < 2 字 → `旅客` ＋ 前段 |
| 錯誤訊息（逐字） | 訂單非本人／不存在 404 `查無此訂單項目`（新明細與舊 `/purchases/info/:id` 共用）；收藏的行程不存在或下架 404 `查無此旅遊項目`；刪除非本人收藏 404 `查無此收藏項目`；收藏成功 201 `收藏成功`；重複收藏 200 `已收藏過此行程`；刪除收藏 200 `刪除成功`；UUID 錯 400 `「行程編號」必須是有效的 UUID 格式`／`「收藏編號」必須是有效的 UUID 格式`／`「訂單編號」必須是有效的 UUID 格式`；通知設定：`「旅遊提醒」必須是 true 或 false`、`開啟價格追蹤時「國家」為必填欄位`（「地區」「預算上限」同句型）、`「預算上限」必須是 0 以上的整數`、`「國家」與「地區」不是系統提供的選項` |
| 會員中心分頁 | `#/admin/userprofile?tab=info|level|preference|orders` 對應「會員資訊／會員等級／個人偏好設定／個人訂單查看」；未知或缺少 → `info` |
| 前端元件與 testid | `components/FavoriteHeart.vue`（`data-testid="favorite-heart"`、`aria-pressed`、`aria-label` 為 `加入收藏`／`取消收藏`）；`order-row`、`order-detail`、`point-record`、`favorite-card` |
| evidence | `docs/reports/evidence/phase-5/` |

## Review Focus

1. **Google 名字含 emoji 或組合字且超過 20 字**：必須以 code point 截斷，不留下半個 surrogate，存進 DB 後結帳頁能直接送出。→ Task 2 `test_google_emoji_name_truncated_by_code_point`。
2. **付款進行中的待付款訂單已超過訂單期限**：列表要顯示「付款處理中」，`can_continue_payment` 與 `is_overdue` 都是 false（F1），沒有「繼續付款」，也不被讀取轉成 4。→ Task 3 `test_order_list_in_progress_wins_over_deadline`；Task 4 `test_overdue_pending_order_has_no_continue_button`。
3. **同一行程連點兩次愛心（兩個 POST 同時到）**：只有一筆收藏，兩個回應都不是 500，`favorite_id` 相同。→ Task 7 `test_concurrent_favorite_same_tour_returns_same_id`。
4. **新註冊會員打開點數紀錄**：不應看到沒有訂單的「購物回饋 0」。→ Task 5 `test_point_records_hide_signup_zero_row`（R3）。
5. **取消收藏後頁面仍拿著舊的 `favorite_id`，或取消後再收藏**：舊 id 再刪回 404、不影響新的收藏；重新收藏拿到新 id。→ Task 7 `test_refavorite_after_delete_gets_new_id_and_old_id_404`。

---

## 檔案結構

| 檔案 | 責任 | Task |
|---|---|---|
| `refs.env`、`docs/reports/evidence/phase-5/task-0-verify.txt` | 分支、查證結果 | 0 |
| `backend/migrations/V6__p5_member_center.sql`、`tests/test_migrations.py` | 三個唯一約束 | 1 |
| `db/seed-build/build_seed.py`、`db/seed/R__seed.sql`（重產）、`tests/test_build_seed.py`、`tests/test_seed.py` | alice 的 auto_setting 併成一列 | 1 |
| `backend/src/controllers/cart.js` | 建購物車 `ON CONFLICT` | 1 |
| `backend/src/utils/nameRule.js`（新）、三個 validator、`middlewares/userinfo/index.js`、`middlewares/userProfile/index.js`、`controllers/userinfo.js`；`frontend/src/utils/function.js`、`views/front/pay.vue`、`views/admin/userprofilePage.vue` | 姓名規則 | 2 |
| `tests/test_name_rule.py`（新） | 姓名規則 API 測試 | 2 |
| `backend/src/utils/trade.js`、`utils/orderStatus.js`（新）、`utils/Validator/paging_Validator.js`（新）、`utils/Validator/orders_Validator.js`（新）、`routes/orders.js`、`controllers/orders.js`、`middlewares/orders/index.js`（新）、`server.js` | 我的訂單 API | 3 |
| `backend/src/middlewares/purchases/index.js`、`controllers/purchases.js`、`utils/Validator/purchases_Validator.js` | 越權讀取 | 3 |
| `tests/test_member_orders.py`（新） | 訂單 API、越權 | 3 |
| `frontend/src/utils/api.js`、`views/admin/userprofilePage.vue`、`components/HeaderComponent.vue`、`router/index.js` | 分頁切換、訂單分頁、Header | 4、5、6、8 |
| `e2e/test_member_center.py`（新）、`e2e/test_member_flow.py:368` | 會員中心 E2E | 4、5、6 |
| `backend/src/routes/points.js`、`controllers/points.js`、`middlewares/points/index.js`（新）、`controllers/userProfile.js:123-178` | 點數與等級 | 5 |
| `tests/test_member_points.py`（新）、`tests/test_api_smoke.py:282-291` | 點數 API | 5 |
| `backend/src/controllers/automation.js`、`middlewares/automation/index.js`、`utils/Validator/automation_Validator.js` | 通知設定 | 6 |
| `tests/test_member_notify.py`（新） | 通知設定 API | 6 |
| `backend/migrations/R__views_functions.sql`、`controllers/product.js:295,370,461`、`routes/collection.js`、`controllers/collection.js`、`middlewares/collection/index.js`、`utils/Validator/collection_Validator.js` | 收藏後端 | 7 |
| `tests/test_member_favorites.py`（新）、`tests/test_async_errors.py`、`tests/test_api_smoke.py:365-376`、`tests/db_contract.py:60,76`、`tests/test_views_a.py:266-274` | 收藏測試 | 7 |
| `frontend/src/components/FavoriteHeart.vue`（新）、`views/admin/collectPage.vue`、`views/front/searchPage.vue`、`views/front/tourPage.vue`、`views/HomeView.vue:159-161` | 收藏前端 | 8 |
| `e2e/test_favorite_flow.py`（新） | 收藏與 P5 主線 E2E | 8 |
| `backend/src/utils/trade.js`、`controllers/newebpay.js:159,174,187,193`、`tests/test_trade_checkout.py`、`tests/test_trade_payment.py:565-588`、P4 spec §5.5 | §7 清理 | 9 |
| `docs/reports/phase-5.md`（新）、`docs/lock-order.md`、`docs/db-contract.md`、`README.md` | 報告與文件 | 10 |

---

### Task 0: 開分支、refs.env、查證讀碼推定（雙審）

**Files:**
- Modify: `refs.env`
- Create: `docs/reports/evidence/phase-5/task-0-verify.txt`

每一項把「指令、實際輸出、與預期是否相符」寫進 `task-0-verify.txt`。**任何一項與預期不符，⛔ 停下回報，不得自行調整後續 Task。**

- [ ] **Step 1: 開分支**：`git switch -c phase-5 main`（總覽）；`git -C backend switch -c phase-5 main`；`git -C frontend switch -c phase-5 dev`；`refs.env` 改 `BACKEND_REF=phase-5`、`FRONTEND_REF=phase-5`。
- [ ] **Step 2: V6 版本號**：`ls backend/migrations` 與 `SELECT version, script FROM flyway_schema_history ORDER BY installed_rank`。預期最大 versioned 是 `5`，V6 可用；repeatable 排在 versioned 之後（`R__seed`、`R__views`）。
- [ ] **Step 3: lock-order 行號**（`docs/lock-order.md`「維護方式」）：`git -C backend rev-parse --short HEAD` 預期 `0e3b192`；逐條 `sed -n "<line>p"` 核對文件內每個 `file:line`。預期全部相符（起草時已核對）。結果另存報告 §1 用。
- [ ] **Step 4: seed 重複**：對 `favorite (user_id, tour_id)`、`cart (user_id)`、`auto_setting (user_id)` 各跑 `GROUP BY … HAVING count(*) > 1`。預期 favorite 0、cart 0、**auto_setting 1（alice，R1 已裁決合併）**。其他結果 ⛔ 停下。
- [ ] **Step 5: `point_record` 實際寫入值**：`SELECT type, count(*), min(point), max(point), count(*) FILTER (WHERE order_id IS NULL) FROM point_record GROUP BY type`，並 `grep -n "point_record" backend/src -r`。預期 seed 只有 `新增`（15）、`減少`（3）；程式寫入的值只有 `新增`、`減少`、`減少_確認中`、`退款退回`、`退款收回`（`trade.js:309,337,346,404,410`）與註冊的 `新增 0`（`userinfo.js:37,213`，R3）。
- [ ] **Step 6: Header 死連結**：`grep -n 'to="#"\|href="#"' frontend/src/components/HeaderComponent.vue`。預期 `:45-46`（旅遊神器、行事曆，不在範圍）、`:68-70`（會員等級、個人偏好設定、個人訂單查看）、`:117-119`（手機的旅遊神器、行事曆、購物車），以及 `:71`、`:125` 的登出 `href="#"`（有 handler，不是死連結）。
- [ ] **Step 7: `-1` 訂單進入 `pay.vue` 能填完收件資料**：`uv run pytest e2e/test_trade_flow.py::test_checkout_button_creates_order e2e/test_trade_flow.py::test_trade_main_flow -v`（`去結帳` 建出的就是 `-1` 訂單，主線在 `pay.vue` 填地址電話後送出）。預期 2 passed；再以 DB 確認主線那張訂單經 `-1 → 0 → 1`（測試內已斷言）。若不通過 ⛔ 停下。
- [ ] **Step 8: 價格追蹤的地區值（R2）**：(a) `grep -n "country\|region" frontend/src/views/front/searchPage.vue frontend/src/views/admin/manage/automaticSetting.vue` 預期兩頁都沒有國家／地區選單；(b) `controllers/product.js` 的 `buildDynamicTourSQL` 以 `"所屬國家"`／`"所屬地區"` 比對（`tour` 的英文值）；(c) `SELECT a.country, a.region, EXISTS (SELECT 1 FROM tour t WHERE t.status = 1 AND t.country = a.country AND t.region = a.region) FROM auto_setting a WHERE a.country IS NOT NULL` 預期 Japan／Tokyo、France／Paris 都是 `t`。任一項不符 ⛔ 停下回報。
- [ ] **Step 9: 開工前衝突掃描的查證（F3、F10、F14／F15／F21）**：每項寫「指令、輸出、預期」：
  (a) `\d+ user_order_item` 與 `R__views_functions.sql` 的定義：預期含 `使用者編號`、`WHERE oi.payment_status = 1`（F3）；
  (b) `pointslevel`、登入、loginStatus 的回應是否帶回饋比例：預期都沒有（F10；有就改從 API 讀）；
  (c) `frontend/src/utils/api.js` 的 `isMemberApi`：預期 `startsWith` 前綴比對（F14）；
  (d) `controllers/userinfo.js` 四個函式 `post_user_SignUp`、`post_user_LoginEmail`、`post_user_LoginGoogle`、`get_user_loginStatus` 回傳的點數鍵：預期 `level.points`（R6）；
  (e) `tests/conftest.py` 有 `ready_order`、`start_payment`、`notify`、`success_notify`，`tests/test_trade_refund.py` 有 `refund(api, admin, order_id)`（F24 要用）；
  (f) `tests/dbfactory.py` 的 `tour` 預設值含 `country`／`region`（Task 6 的 `p5land` 測試以 DB 改這兩欄）；
  (g) 前端現有的分頁 UI（`searchPage.vue:232-234` 的 `上一頁`／`下一頁`）可沿用。
  掃描原文若列了上述以外的查證項目，主對話把清單交給執行者時一併補進本步驟。任一項不符 ⛔ 停下回報。
- [ ] **Step 10: Commit**（總覽）：`git add refs.env docs/reports/evidence/phase-5/task-0-verify.txt`；`chore: refs.env 指向 phase-5、P5 讀碼推定查證結果`。

### Task 1: V6 唯一約束、seed 去重、建購物車不重複（雙審）

**Files:**
- Create: `backend/migrations/V6__p5_member_center.sql`
- Modify: `backend/src/controllers/cart.js:26-37`
- Modify: `db/seed-build/build_seed.py`（新增改寫函式並在 `build()` 呼叫）、Regenerate `db/seed/R__seed.sql`
- Modify: `tests/test_migrations.py`、`tests/test_build_seed.py`、`tests/test_seed.py:23`、`tests/test_trade_cart.py`
- Modify: `docs/db-contract.md`（新增「P5 表格約束（V6）」小節；§0.1 加 auto_setting 併列；§4.2 d4（`:1721`）改「P5 已加」並說明原因：重複收藏回原 id、併發只留一筆）、`docs/lock-order.md`（§9「新增」步驟 1、`已知問題` 標已解決）

**Interfaces:**
- Produces：共用約定的三個約束名；`build_seed.py::merge_duplicate_auto_settings(by_table: dict[str, Insert]) -> None`（F10：通用，處理任何 user_id 的重複；R1：同一 user_id 的列，每個欄位取 `updated_at` 較新者，相同或缺少時取 `auto_setting_id` 較小者；seed 結果為保留 `1111aaaa-2222-bbbb-3333-cccc4444dddd` 原值、刪 `4444dddd-5555-eeee-6666-ffff7777aaaa`；斷言改寫後每個 user_id 恰一列）。
- Produces（`cart.js` POST）：先 `INSERT INTO cart (user_id, total_price) VALUES ($1, 0) ON CONFLICT (user_id) DO NOTHING`，再 `SELECT cart_id FROM cart WHERE user_id = $1 FOR UPDATE`；其餘不變。

- [ ] **Step 1: 寫紅燈測試**
  - `tests/test_migrations.py`：`test_flyway_applied_v1_to_v6`（取代 `:16` 的 `_v1_to_v5`；集合 ⊇ `{"1",…,"6"}`，docstring 改 V1–V6；契約 `:1760`、`:1771`、`:1773` 的測試名同步改）；`test_favorite_user_tour_unique(tx)`（同 user、同 tour 插兩列 → `psycopg.errors.UniqueViolation`）；`test_cart_user_unique(tx)`；`test_auto_setting_user_unique(tx)`；三個都另斷言 `pg_constraint` 有對應名稱。
  - `tests/test_build_seed.py`：`test_alice_auto_settings_merged()`：以 `build()` 產生的文字解析 `auto_setting`，每個 user_id 一列；alice 那列 `auto_setting_id = '1111aaaa-2222-bbbb-3333-cccc4444dddd', early_notify = 0, flexible_notify = 1, country = 'Japan', region = 'Tokyo', price = 1200.5`；另 `test_merge_auto_settings_prefers_newer_updated_at()`：以兩列不同 `updated_at` 的假 `Insert` 呼叫 `merge_duplicate_auto_settings`，各欄取較新者；`test_merge_auto_settings_tie_takes_smaller_id()`（F10）：兩列 `updated_at` 相同 → 結果全部取 `auto_setting_id` 較小那列的值。
  - `tests/test_seed.py:23`：`"auto_setting": 4` → `3`。
  - `tests/test_trade_cart.py`：`test_first_add_concurrently_creates_one_cart(api, db, make_user, make_tour)`：新會員、兩個行程，`threading.Barrier(2)` 同時 `add_to_cart` → 兩個都 201、`cart` 1 列、`cart_item` 2 列。（V6 之前可能偶然綠；紅燈以前三項為準，commit 註明。）
- [ ] **Step 2: 跑紅燈**：`uv run pytest tests/test_migrations.py tests/test_build_seed.py tests/test_seed.py tests/test_trade_cart.py -v --tb=short`；併發測試另跑 10 次（F25）：`for i in $(seq 10); do uv run pytest tests/test_trade_cart.py::test_first_add_concurrently_creates_one_cart -q --tb=line; done`，每次結果都附進 evidence，10 次都沒紅就照實寫。存 `task-1-red.txt`，commit 總覽 `test: V6 唯一約束、seed auto_setting 一人一列、併發首次加入購物車 🔴`。
- [ ] **Step 3: 實作 V6**：開頭註解引用 spec §3。順序：(1) `DO $$` 預檢 cart、auto_setting 的重複，有就 `RAISE EXCEPTION 'V6：cart（或 auto_setting）有同一會員多列，請先手動處理（P5 spec §3）'`；(2) 刪 favorite 重複，同一 `(user_id, tour_id)` 保留 `(created_at, favorite_id)` 最小者；(3) 三個 `ALTER TABLE … ADD CONSTRAINT … UNIQUE`。
- [ ] **Step 4: 實作 seed 與 cart.js**：依 Interfaces；`uv run python db/seed-build/build_seed.py` 重產 `R__seed.sql`（不得手改）；`uv run pytest tests/test_build_seed.py -q` 綠。
- [ ] **Step 5: 重建 DB**：⛔ 停下，**提醒使用者自己執行** `! docker compose down -v`（主對話與 agent 都不代為執行，R1）；使用者完成後再 `docker compose up -d --build`。
- [ ] **Step 6: 綠燈**：`uv run pytest tests -q` 全綠。
- [ ] **Step 7: Commit**：backend `feat: V6 收藏、購物車、通知設定唯一約束；建購物車改 ON CONFLICT 🟢`；總覽 `fix: seed 的 alice 通知設定依 updated_at／id 規則併成一列 🟢`（`build_seed.py`、`R__seed.sql`）；總覽 `docs: 契約與上鎖順序記錄 V6`。

### Task 2: 共用姓名規則與 Google 名字（雙審）

**Files:**
- Create: `backend/src/utils/nameRule.js`、`tests/test_name_rule.py`
- Modify: `tests/test_google_login.py`
- Modify: `backend/src/utils/Validator/userInfo_Validator.js:4,10-14`、`userprofile_Validator.js:3,13-27`、`checkout_Vaildator.js:22-30`；`backend/src/middlewares/userinfo/index.js`（`postuserSignup`）、`middlewares/userProfile/index.js`（`patchuserprofileData`）改用 `userMessage`；`backend/src/controllers/userinfo.js:142,202-203`
- Modify: `frontend/src/utils/function.js:19-45`（`validateName`）、`frontend/src/views/front/pay.vue`（送出前檢查姓名）、`frontend/src/views/admin/userprofilePage.vue`（`updateUserInfo` 送出前檢查）
- Modify: `tests/test_member_auth.py:181`、`tests/test_validator_messages.py:247-248`、`tests/test_validator_sweep.py`、`e2e/test_member_flow.py`

**Interfaces:**
- Produces（`utils/nameRule.js`）：`NAME_MIN = 2`、`NAME_MAX = 20`；`nameLength(s: string) -> number`（`[...s].length`）；`HAS_CONTROL_CHAR = /\p{Cc}/u`（檢查用，不加 `g`）、`CONTROL_CHARS_G = /\p{Cc}/gu`（只給 `replace` 移除用）（F16）；`nameSchema() -> Joi.StringSchema`（`.trim()`，`.custom` 先以 `HAS_CONTROL_CHAR` 檢查 再檢查 code point 長度，不限其他字元，訊息見共用約定；呼叫端自行 `.required()`）；`googleDisplayName(name: string | undefined, email: string) -> string`（先以 `CONTROL_CHARS_G` 移除，再套共用約定「Google 名字」）。
- Produces（frontend `function.js`）：`nameError(value: string) -> string | null`（同規則與訊息，含控制字元檢查）；`validateName(nameTxt, errorTxt)` 改呼叫它。
- 註冊、會員資料、結帳三個 schema 的 `name` 都換成 `nameSchema()`；註冊與會員資料存入去空白後的值。

- [ ] **Step 1: 寫紅燈測試**（`tests/test_name_rule.py`；`BASE` 與 helper 沿用 `test_member_auth.py`、`conftest.preview`）
  - `test_signup_accepts_20_chars_and_spaces`（`"王" * 18 + " A"` → 201）；`test_signup_rejects_21_chars`（21 字 → 400 `「姓名」需為 2 到 20 個字`）；`test_signup_trims_name`（`"  小明  "` → DB `name == "小明"`）；`test_signup_blank_name`（`"   "` → 400 `「姓名」不得為空白`）。
  - `test_signup_counts_code_points`（10 個 emoji `"😀" * 10` → 201；21 個 → 400）。
  - `test_signup_allows_symbols_and_spaces`（`"Mary-Jane O'Neil"` → 201）；`test_signup_rejects_control_chars`（`"小明\u0007"`、`"小\n明"` → 400 `「姓名」不得包含控制字元`）；`test_profile_rejects_control_chars`、`test_checkout_rejects_control_chars`（同訊息）。
  - `test_profile_name_rules`（PATCH `/user/userinfo/info`：1 字 400、20 字 200、21 字 400，訊息同上）；`test_profile_saves_trimmed_name`（F16：`"  新名字  "` → 200、DB `name == "新名字"`）；`test_control_char_check_is_stateless`（F16：同一請求序列連續兩次送 `"小明\u0007"` 都 400）。
  - `test_checkout_name_rules`（`preview` 的 `user.name`：`"Google 測試員"` 200、21 字 400 `「姓名」需為 2 到 20 個字`）。
  - Google（放在 `tests/test_google_login.py`，沿用 `google` fixture）：`test_google_long_name_truncated`（`name = "A" * 25` → DB `name == "A" * 20`）；`test_google_short_name_uses_email`（`name = "王"` → `name == claims["email"].split("@")[0][:20]`）；`test_google_missing_name_uses_email`（claims 刪 `name`）；`test_google_name_control_chars_removed`（`name = "王\u0000小\u001f明"` → DB `name == "王小明"`）；`test_google_display_name_one_char_local_part`（測試 email 前綴不可能只有 1 字，改以 `docker compose exec -T backend node -e` 載入 `src/utils/nameRule.js`，斷言 `googleDisplayName(undefined, 'x@a.co') === '旅客x'`、`googleDisplayName('  ', 'ab@a.co') === 'ab'`）。
  - **Review Focus 1** `test_google_emoji_name_truncated_by_code_point`（同檔；`name = "😀" * 25` → DB `name == "😀" * 20`，Python `len()` 為 20；再以該會員建單並 `preview` 帶此名字 → 200）。
  - 改既有斷言：`test_member_auth.py:181` 的 `"六個字的名字喔"` 改 21 字、訊息 `「姓名」需為 2 到 20 個字`；`test_validator_messages.py:247-248` 改 `「姓名」為必填欄位`、`「姓名」必須是文字`。
  - `test_validator_sweep.py`：`SWEEP_JS` 加 `userInfo.register`、`userprofile.update` 兩個 target（`co.post` 已涵蓋結帳）；parametrize 加 `userinfo.postuserSignup`、`userProfile.patchuserprofileData`（比照 `_search_handler_source` 以函式名切片）。
- [ ] **Step 2: 跑紅燈**：`uv run pytest tests/test_name_rule.py tests/test_google_login.py tests/test_member_auth.py tests/test_validator_messages.py tests/test_validator_sweep.py -v --tb=short`。存 `task-2-red.txt`，commit 總覽 `test: 姓名 2 到 20 字共用規則、Google 名字截斷 🔴`。
- [ ] **Step 3: 實作後端**：依 Interfaces；`controllers/userinfo.js` 新會員 INSERT 用 `googleDisplayName(name, email)`（既有會員不改名）。
- [ ] **Step 4: 後端綠燈**：`uv run pytest tests -q`。commit backend `feat: 註冊、會員資料、結帳共用姓名規則（2 到 20 字），Google 名字截斷 🟢`。
- [ ] **Step 5: 前端紅燈**（`e2e/test_member_flow.py`；F17 三個表單都要有 21 字被擋的案例）：`test_pay_name_too_long_blocked`（`pay.vue` 全名填 21 字 → `「姓名」需為 2 到 20 個字` 可見、沒有送出 `/checkout/preview`）；`test_register_name_too_long_shows_message`（註冊頁填 21 字 → `「姓名」需為 2 到 20 個字` 可見、沒有送出 `/signup`）；`test_profile_name_too_long_shows_message`（`_edit_name(page, "名" * 21)` → 同訊息、DB 名字不變）；`test_google_long_name_can_checkout`（以 `mock_google_code` 打 `/login/google` 建 25 字的 Google 會員，取回 token 後 `add_init_script` 寫入；加購物車 → `pay.vue` 預填的全名為 20 字 → 填地址電話 → `確認並前往付款` → mock 付款頁可見）。存 `task-2-red-frontend.txt`，commit 總覽 `test: 前端姓名上下限 E2E 🔴`。
- [ ] **Step 6: 前端實作與綠燈**：`uv run pytest e2e -q`。commit frontend `feat: 註冊、會員資料、結帳表單的姓名改為 2 到 20 字 🟢`。

### Task 3: 我的訂單 API 與越權讀取（雙審）

**Files:**
- Create: `backend/src/utils/orderStatus.js`、`utils/Validator/paging_Validator.js`、`utils/Validator/orders_Validator.js`、`routes/orders.js`、`controllers/orders.js`、`middlewares/orders/index.js`、`tests/test_member_orders.py`
- Modify: `backend/src/utils/trade.js:135-158`、`server.js`（`app.use(\`/api/${version}/user/orders\`, ordersRouter)`）
- Modify: `backend/src/middlewares/purchases/index.js:11-46`、`controllers/purchases.js:55-61`、`utils/Validator/purchases_Validator.js`（訊息不含 `lang` 參數名）
- Modify: `tests/test_validator_sweep.py`、`docs/db-contract.md`（§4.2 (c) 標已修正，記 P5 commit）

**Interfaces:**
- Produces（`utils/trade.js`，既有行為不變）：
  - `orderTimeoutMinutes() -> number`（`envNumber('ORDER_PAYMENT_TIMEOUT_MINUTES', 60)`；`pastOrderDeadline` 改用它）。
  - `paymentInProgressSql(orderIdExpr: string, secsParam: string) -> string`：回傳 `EXISTS (SELECT 1 FROM public."payment" WHERE order_id = ${orderIdExpr} AND payment_status = 0 AND result_time IS NULL AND created_at + make_interval(secs => ${secsParam}) > now())`；`paymentInProgress` 改用它（`'$1'`, `'$2'`）。
- Produces（`utils/orderStatus.js`）：`orderStatusLabel(status: number, inProgress: boolean) -> string`（共用約定「訂單狀態中文」）；`paymentResultLabel(row: { payment_status, result_time, in_window: boolean }) -> string`（共用約定「付款紀錄結果」）。
- Produces（`paging_Validator.js`）：`pagingSchema`（共用約定）。`orders_Validator.js`：`orderIDSchema`（`order_id` UUIDv4，訊息 `「訂單編號」必須是有效的 UUID 格式`）。
- Produces（API）：
  - `GET /user/orders`（`auth`, `authRole('User')`, `mw.getOrders`, `controller.get_orders`）：一個 SQL 取本人訂單（`ORDER BY created_at DESC, order_id`、`LIMIT/OFFSET`），子查詢帶 `item_count`、第一個品項（`order_item.created_at, order_item_id` 最小）的 `title`、`cover_image`、`deadline = created_at + make_interval(mins => orderTimeoutMinutes())`、`payment_in_progress = paymentInProgressSql('o.order_id', …)`、`can_continue_payment`、`is_overdue`（F1，皆在 SQL 以 `now()` 與 `deadline` 比對）；再對每筆 `computePayable(pool, order_id)`。每筆輸出 `{ order_id, created_at, payment_status, status_label, payment_in_progress, can_continue_payment, is_overdue, deadline, total_price, promo_subtotal, payable, discount_type, discount_amount, item_count, first_item: { title, cover_image } }`；`dbdata = { data, total }`；訊息 `查詢成功`。
  - `GET /user/orders/:order_id`：`WHERE order_id = $1 AND user_id = $2`，查無 404 `查無此訂單項目`。輸出 `{ order_id, created_at, payment_status, status_label, payment_in_progress, can_continue_payment, is_overdue, deadline, shipping: { address, phone, payment_type }, money: computePayable 的 5 欄, items: [{ order_item_id, tour_id, title, cover_image, quantity, start_date, end_date, room_type, total_price, discount_price }], payments: [{ created_at, result_time, result }] }`（`payments` 依 `created_at` 新到舊，不含 `return_data`、`result_info`、`merchant_order_no`）。
  - 兩支都不開交易、不呼叫 `expireIfOverdue`（GC13）。
  - 舊 `GET /user/purchases/info/:order_item_id`（F3：只修越權與 `:34`，其餘行為不變）：middleware 驗證改走 `userMessage`；`:31` 的查詢改成擁有者檢查 `SELECT 1 FROM order_item oi JOIN orders o USING (order_id) WHERE oi.order_item_id = $1 AND o.user_id = $2`（基表沒有 `使用者編號`），0 列 → 404 `查無此訂單項目`（`:34` 改判 `rowCount === 0`，原本永遠不觸發）；controller `:58-61` 對 view `user_order_item` 的查詢加 `AND 使用者編號 = $2`。本人但未付款的項目通過擁有者檢查、view 查無 → 維持現有 200 `查無資料`。

- [ ] **Step 1: 寫紅燈測試**（`tests/test_member_orders.py`；`ORDERS = "/api/v1/user/orders"`）
  - 列表：`test_orders_list_all_statuses(api, db, make_user, make_tour, make_order)`（以 `make_order` 建 `-1, 0, 1, 2, 3, 4` 各一 → `total == 6`、`status_label` 集合為 `待付款, 已付款, 已取消, 已退款, 已逾時`）；`test_orders_list_newest_first_and_paging`（3 張、`limit=2` → 第 1 頁 2 筆、第 2 頁 1 筆，`created_at` 遞減）；`test_orders_list_default_limit_is_4`；`test_orders_limit_over_50_is_400`（`「每頁筆數」不可超過 50`）；`test_orders_list_empty`（新會員 → 200、`data == []`、`total == 0`）。
  - 金額：`test_orders_payable_from_compute_payable`（`ready_order` 套券 100 於 `live_promotion` 2 人 → 該筆 `payable == 1700`、`discount_type == 'coupon'`、`discount_amount == 100`；再以 DB 把 `orders.discount_price` 改成 1 → 列表仍 `1700`）。
  - 期限與進行中：`test_order_deadline_is_created_at_plus_timeout`（`deadline - created_at == 60 分鐘`）；`test_order_list_in_progress_label`（`start_payment` 後 → `付款處理中`、`payment_in_progress is True`、`can_continue_payment is False`、`is_overdue is False`）；`test_order_can_continue_payment_flags`（F1：期限內 -1 訂單 → `can_continue_payment is True`、`is_overdue is False`；已付款 → 兩者 False；明細回同樣的值）；**Review Focus 2** `test_order_list_in_progress_wins_over_deadline`（再把 `orders.created_at` 改成 61 分鐘前 → 仍 `付款處理中`、兩個布林都 False；DB `payment_status` 仍 0）；`test_order_list_does_not_expire_overdue`（`-1` 訂單 `created_at` 61 分鐘前 → 列表 `待付款`、`is_overdue is True`、`can_continue_payment is False`；DB 仍 -1）。
  - 明細：`test_order_detail_fields`（已付款訂單：`items` 筆數、`shipping.address == '台北市測試路1號'`、`payments[0].result == '成功'`、回應文字不含 `return_data`、`TradeInfo`）；`test_order_detail_failed_payment_result`（`MPG03009` notify 後 → `失敗`）。
  - 越權與權限：`test_other_users_order_detail_is_404`、`test_other_users_purchase_item_is_404`（B 讀 A 已付款的 `order_item_id` → 404 `查無此訂單項目`；改前會 200）、`test_purchase_item_unknown_is_404`、`test_own_unpaid_purchase_item_unchanged`（回歸測試，F3：本人 `-1` 訂單的項目 → 200 `查無資料`）、`test_orders_without_token_is_401`（`請先登入`）、`test_orders_admin_is_403`（`您沒有權限進行此操作`）、`test_order_detail_bad_uuid_is_400`（`「訂單編號」必須是有效的 UUID 格式`）。
  - 唯讀（放在 `tests/test_api_smoke.py`，`alice_h` fixture 定義在該檔 `:64`）：`test_seed_member_can_list_orders_readonly(api, alice_h, alice, db)`（alice 列表 200；呼叫前後 alice 所有訂單的 `payment_status`、`updated_at` 不變）。
  - `test_validator_sweep.py`：`SWEEP_JS` 加 `paging`、`orders.orderID`、`purchases.param`；parametrize 加 `orders`、`purchases`。
- [ ] **Step 2: 跑紅燈**：`uv run pytest tests/test_member_orders.py tests/test_validator_sweep.py -v --tb=short`。存 `task-3-red.txt`，commit 總覽 `test: 我的訂單列表與明細、已購買明細越權 🔴`。
- [ ] **Step 3: 實作**：依 Interfaces。
- [ ] **Step 4: 綠燈**：`uv run pytest tests -q`（含 `test_api_smoke.py::test_purchases_item_detail`、`test_trade_*`）。commit backend `feat: 我的訂單 API（全狀態、應付金額單一來源、期限）；fix: 已購買明細的擁有者檢查 🟢`；總覽 `docs: 契約 §4.2 (c) 已修正`。

### Task 4: 會員中心分頁切換、Header、訂單分頁（雙審）

**Files:**
- Modify: `frontend/src/utils/api.js`（`apiUrl_orders`、`isMemberApi`）、`views/admin/userprofilePage.vue`（`:46` 即將開放、`:191` tabs、`:291` `console.log`）、`components/HeaderComponent.vue:67-70,99-101,116-119`、`router/index.js`（`automatic` 改 redirect）
- Create: `e2e/test_member_center.py`
- Modify: `e2e/test_member_flow.py:368-376`

**Interfaces:**
- Consumes：Task 3 的 API 與回應鍵。
- Produces（`api.js`）：`get_orders({ page = 1, limit = 10 } = {}) -> Promise<{ data: Array, total: number }>`（呼叫端明確傳 `limit: 10`，F13）、`get_order(orderId) -> Promise<object>`；錯誤處理沿用 `tradeRequest`。
- Produces（`userprofilePage.vue`）：`TAB_KEYS = { info: '會員資訊', level: '會員等級', preference: '個人偏好設定', orders: '個人訂單查看' }`；`currentTab` 由 `$route.query.tab` 決定（`watch` query；點側欄改用 `router.replace({ query: { tab } })`）；缺少 `tab` 時不改寫 URL（既有 E2E 以 `**/#/admin/userprofile` 等待）。「個人訂單查看」：每筆 `data-testid="order-row"`，顯示訂單編號前 8 碼、建立時間、狀態文字、`NT$<payable>`、`<品項數> 項`、第一個品項名稱；按鈕 `明細`（展開 `data-testid="order-detail"`：品項、收件資料、折扣、付款紀錄）；`can_continue_payment` 為 true → 按鈕 `繼續付款`（`router.push({ name: 'pay', query: { order } })`）；`is_overdue` 為 true → 狀態顯示 `已逾時`、無按鈕；其餘顯示 `status_label`；前端不比對時間，`deadline` 只顯示為 `付款期限 <時間>`（F1）；空列表 `目前沒有訂單`；分頁沿用 `上一頁`／`下一頁`。
- Produces（Header）：桌機 `:68-70` 改 `/admin/userprofile?tab=level|preference|orders`，`:67` 加 `?tab=info`，新增 `收藏` → `/admin/collect`；手機 `:119` 購物車改 `/cart`，`:99-101` 後加同樣 5 個連結。
- Produces（router）：`automatic` 改 `{ path: 'automatic', redirect: { name: 'userprofile', query: { tab: 'preference' } } }`。

- [ ] **Step 1: 寫紅燈測試**（`e2e/test_member_center.py`；`_login(page, user)` 沿用 `e2e/test_trade_flow.py:14` 寫法）
  - `test_header_links_open_tabs(page, make_user)`：桌機 `.user-dropdown` 點 `個人訂單查看` → URL 含 `tab=orders`、側欄該項 `.active`；`會員等級`、`個人偏好設定` 同理；`收藏` → `**/#/admin/collect`。
  - `test_orders_tab_lists_paid_order_with_detail(page, db, make_user, make_tour, make_order)`：`make_tour(price=1000)` 的已付款訂單 → `order-row` 1 筆、含 `已付款`、`NT$1,000`；點 `明細` → `order-detail` 含行程標題。
  - `test_continue_payment_goes_to_pay_page(page, db, make_user, make_tour)`：`checkout` 建 `-1` 訂單 → `繼續付款` → URL `**/#/pay?order=<id>`；填地址、電話 → `確認並前往付款` → mock 付款頁 `付款成功` 按鈕可見（驗證 spec §4.2 讀碼推定）。
  - **Review Focus 2** `test_overdue_pending_order_has_no_continue_button`：`-1` 訂單 `created_at` 61 分鐘前 → 該列 `已逾時`、`繼續付款` 數量 0；DB 仍 -1。另一張 0 訂單有進行中的 payment 且 `created_at` 61 分鐘前 → `付款處理中`、無按鈕。
  - `test_orders_tab_empty(page, make_user)`：`目前沒有訂單`。
  - `test_admin_automatic_redirects_to_preference_tab(page, make_user)`（F7，自 Task 6 移入）：開 `#/admin/manage/automatic` → URL 含 `#/admin/userprofile` 與 `tab=preference`（只斷言 URL 與參數）。
  - `test_profile_tab_from_query(page, make_user)`：直接開 `#/admin/userprofile?tab=orders` → 訂單分頁；`?tab=xxx` → 會員資訊。
  - `e2e/test_member_flow.py:368` `test_coming_soon_tabs` 改為只檢查 `會員等級`、`個人偏好設定` 仍顯示 `即將開放`（Task 5、6 再縮減）。
- [ ] **Step 2: 跑紅燈**：`uv run pytest e2e/test_member_center.py e2e/test_member_flow.py -v --tb=short`。存 `task-4-red.txt`，commit 總覽 `test: 會員中心分頁、Header 連結、訂單分頁 E2E 🔴`。
- [ ] **Step 3: 實作**：依 Interfaces；刪除 `userprofilePage.vue:291` 的 `console.log(this.password.current)`。
- [ ] **Step 4: 綠燈**：`uv run pytest e2e -q`。commit frontend `feat: 會員中心以 ?tab= 切換、訂單分頁（明細、繼續付款）、Header 連結接上 🟢`。

### Task 5: 點數紀錄與會員等級（雙審）

**Files:**
- Create: `backend/src/routes/points.js`、`controllers/points.js`、`middlewares/points/index.js`、`tests/test_member_points.py`
- Modify: `backend/src/server.js`、`controllers/userProfile.js:123-178`、`controllers/userinfo.js` 的 `post_user_SignUp`、`post_user_LoginEmail`、`post_user_LoginGoogle`、`get_user_loginStatus`（R6；F12 以函式名為錨點）、`tests/test_member_auth.py`（F11）、`tests/conftest.py`（F24 helper）、`tests/test_api_smoke.py:282-291`、`tests/test_validator_sweep.py`
- Modify: `frontend/src/utils/api.js`、`views/admin/userprofilePage.vue`、`e2e/test_member_center.py`、`e2e/test_member_flow.py`

**Interfaces:**
- Consumes：Task 3 `pagingSchema`。
- Produces（API）：`GET /user/points/records`（`auth`, `authRole('User')`, `mw.getRecords`）：`WHERE user_id = $1 AND type <> '減少_確認中' AND point <> 0`（R3：在 SQL 排除，前端不過濾），`ORDER BY created_at DESC, point_id`（主鍵名 `point_id`）；每筆 `{ created_at, point, type, reason, order_id }`，`reason` 依共用約定（`controllers/points.js` 內 `POINT_REASON` 物件）；`dbdata = { data, total }`。
- Produces（`controllers/userinfo.js`，R6）：`post_user_SignUp`、`post_user_LoginEmail`、`post_user_LoginGoogle`、`get_user_loginStatus` 回應中 `level.points` 改 `Math.max(0, Number(值))`，DB 不變。
- Produces（`tests/conftest.py`，F24）：`negative_points_via_refund(api, db, make_user, make_tour) -> dict`：新會員付清 A 單（`price=1000`，回饋 100）→ 用 100 點付 B 單（`price=1000`，應付 920，回饋 92）→ admin（`make_user(role="admin")`）退款 A（收回 100）→ 回傳該會員，`travel_point == -8`；沿用 `ready_order`、`start_payment`、`success_notify`、`notify` 與 `test_trade_refund.py` 的 `refund` 寫法（搬到 conftest 共用）。
- Produces（`get_user_PointCoupon`）：`travel_point = Math.max(Number(值), 0)`；只在 `優惠卷編號 !== null` 時 push，無券時 `coupon: []`。
- Produces（`api.js`）：常數 `apiUrl_points = …/user/points` 加進 `isMemberApi`（F14）；`get_point_records({ page = 1, limit = 10 } = {})`（呼叫端明確傳 `limit: 10`，F13）、`get_member_level() -> Promise<{ level, level_name, badge_url, travel_point, coupons }>`（打 `pointslevel`）。
- Produces（「會員等級」分頁）：`目前等級 <level_name>`、`購物回饋比例 10%`（F10：Task 0 Step 9 (b) 確認 API 沒有回傳比例時，前端常數 `REWARD_RATE_TEXT = '10%'`，與 `settlePaidOrder` 的 `floor(payable × 0.1)` 一致，偏離 spec 記於 §12；API 若有回傳就改讀 API）、`點數餘額 <N> 點`、優惠券清單（代碼、說明、期限；無券 `目前沒有可用的優惠券`）、文字 `點數紀錄為明細，加總不一定等於目前餘額（初始點數沒有對應紀錄）`、`升級規則尚未開放`；紀錄每列 `data-testid="point-record"`：時間、原因、`+170`／`-100`、訂單編號前 8 碼。

- [ ] **Step 1: 寫紅燈測試**（`tests/test_member_points.py`；DB 直接 insert `point_record` 與設 `travel_point`）
  - `test_point_records_reasons_and_order(api, db, make_user, make_order, make_tour)`：插 `新增 170`、`減少 -100`、`退款收回 -170`、`退款退回 100`、`其他類型 5` → `reason` 依序對應、`其他類型` 原樣；新到舊。
  - `test_point_records_hide_pending_deduction`：`減少_確認中 -50` 不出現。
  - **Review Focus 4** `test_point_records_hide_signup_zero_row`（放在 `tests/test_member_auth.py`，沿用 `_signup_body`、`cleanup_email`）：以 `/signup` 註冊新會員（`val.` 前綴）→ DB 有 `新增 0` 一列，但點數紀錄 API `data == []`。
  - `test_point_records_paging`、`test_point_records_other_user_not_visible`（B 的紀錄不出現在 A）、`test_point_records_without_token_is_401`、`test_point_records_admin_is_403`、`test_point_records_limit_over_50_is_400`。
  - `test_pointslevel_negative_shows_zero`（F24：`negative_points_via_refund` → 回 `0`；DB 仍 -8）；`test_pointslevel_without_coupon_is_empty_list`（新會員 → `coupon == []`）。
  - R6（放在 `tests/test_member_auth.py`）：`test_login_email_negative_points_returns_zero`（F24：`negative_points_via_refund` 後 → `POST /auth/userinfo/login/email` 回應 `data.level.points == 0`；DB 仍 -8）；`test_login_status_negative_points_returns_zero`（同上，`GET /auth/userinfo/login/status` 回應 `data.level.points == 0`）。註冊與 Google 登入不寫測試，Step 3 完成後以 `grep -n "points:" backend/src/controllers/userinfo.js` 確認 4 處都已 clamp，結果寫 ledger。
  - 改 `test_api_smoke.py:282` 為 `test_points_level_alice_has_empty_coupon_list`：`me["coupon"] == []`，其餘斷言不變。
  - `test_validator_sweep.py`：parametrize 加 `points`；`SWEEP_JS` 加 `points.paging` target（F11；與 Task 3 的 `paging` 共用 schema，仍以 points middleware 實際引用的 schema 為準）。
  - E2E（`e2e/test_member_center.py`）：`test_level_tab_shows_points_and_records`（`travel_point = 170`、紀錄 `新增 170`、`減少 -100`、`減少_確認中 -50` → `點數餘額 170 點`、2 個 `point-record`、含 `購物回饋`、`+170`、`點數折抵`、`-100`，不含 `-50`；說明文字可見）；`test_level_tab_negative_points_shows_zero`（F24：`negative_points_via_refund` → `點數餘額 0 點`）。`test_coming_soon_tabs` 改為只檢查 `個人偏好設定`。
- [ ] **Step 2: 跑紅燈**（F19 明列檔案）：`uv run pytest tests/test_member_points.py tests/test_member_auth.py tests/test_api_smoke.py tests/test_validator_sweep.py e2e/test_member_center.py e2e/test_member_flow.py -v --tb=short`。存 `task-5-red.txt`，commit 總覽 `test: 點數紀錄、等級頁負點數顯示 0、無券回空陣列 🔴`。
- [ ] **Step 3: 實作後端與前端**：依 Interfaces。
- [ ] **Step 4: 綠燈**：`uv run pytest tests e2e -q`。commit backend `feat: 點數紀錄 API；pointslevel 與登入回應的負點數回 0、無券回空陣列 🟢`；frontend `feat: 會員等級分頁（等級、點數、優惠券、點數紀錄） 🟢`。

### Task 6: 通知設定（雙審）

**Files:**
- Modify: `backend/src/controllers/automation.js`、`middlewares/automation/index.js`、`utils/Validator/automation_Validator.js`
- Create: `tests/test_member_notify.py`
- Modify: `tests/test_validator_sweep.py`、`docs/lock-order.md`（§10 加 auto_setting upsert：單一語句、不開交易）、`backend/src/routes/automation.js`（新增 `GET /regions`）
- Modify: `frontend/src/utils/api.js`、`views/admin/userprofilePage.vue`、`e2e/test_member_center.py`、`e2e/test_member_flow.py`

**Interfaces:**
- Produces（API，路由不變、仍 `authRole('User')`）：
  - `GET /allnotifi-settings`：沒有資料時回預設 `{ notifi_settings_enabled: false, price_tracking: { price_tracking_enabled: false, country: null, region: null, max_price: null } }`，訊息 `查詢成功`；有資料時兩個開關輸出布林。
  - `PATCH /notifi-settings`：`INSERT … ON CONFLICT (user_id) DO UPDATE SET early_notify = EXCLUDED.early_notify, updated_at = now()`，200 `提醒設定已更新`。
  - `PATCH /price-tracking`：同樣 upsert（只更新 `flexible_notify, country, region, price`）；開啟時 `country`／`region` 必須是上架行程的組合，**或**與該會員目前存的 `(country, region)` 完全相同（R2a）；`max_price` 必須是 0 以上的整數，**或**與目前存的值完全相同（F2，seed 的 `1200.5` 保留）（R2：`EXISTS (SELECT 1 FROM tour WHERE status = 1 AND country = $1 AND region = $2)`，與 regions API 共用 `controllers/automation.js` 內的 SQL 常數 `LISTED_REGION_SQL`），否則 400 `「國家」與「地區」不是系統提供的選項`；關閉時三欄寫 NULL。200 `彈性價格提醒狀態已更新`。
  - `GET /regions`（新，`auth`, `authRole('User')`）：`SELECT DISTINCT country, region FROM tour WHERE status = 1 AND country IS NOT NULL AND region IS NOT NULL`，依國家分組回 `dbdata = [{ country, regions: [string] }]`（陣列，不包 `{ data, total }`，F6；國家、地區皆字母序；空清單時 `resStatus` 省略 `data`，前端視為 `[]`）。
  - 驗證訊息全部換成共用約定的中文標籤，經 `userMessage`。
- Produces（`api.js`）：常數 `apiUrl_automation = …/user/automation` 加進 `isMemberApi`（F14）；`get_notify_settings()`、`patch_early_notify(enabled: boolean)`、`patch_price_tracking({ enabled, country, region, maxPrice })`、`get_tracking_regions() -> Promise<Array<{ country, regions }>>`（打 `/user/automation/regions`；不使用 `/web/filter` 的中文表）。
- Produces（「個人偏好設定」分頁）：已存的國家或地區不在 `get_tracking_regions()` 清單時，仍加入選項並維持選取，選項文字為 `<值>（目前沒有上架行程）`（R2a）；勾選框 `出發前提醒`、`價格追蹤`；開啟價格追蹤才顯示下拉 `國家`、`地區` 與數字輸入 `預算上限`；按鈕 `儲存設定` 依序呼叫兩支 PATCH，成功 Swal `設定已儲存`；文字 `目前只儲存設定，尚未寄送通知`。

- [ ] **Step 1: 寫紅燈測試**（`tests/test_member_notify.py`）
  - `test_get_defaults_when_no_row`（新會員 → 預設值，兩個開關 `is False`）；`test_get_returns_booleans`（DB 插 `early_notify = 1` → `True`）。
  - `test_patch_early_upsert_idempotent`（PATCH 兩次 → DB 該會員 1 列、`early_notify = 1`）；`test_patch_price_upsert_keeps_early`（先 early true，再 price-tracking 開啟 `Japan`／`Tokyo`／30000 → 1 列，兩項都在）；`test_patch_concurrent_first_write_one_row`（兩執行緒同時第一次 PATCH → 都 200、1 列；紅燈步驟跑 10 次，F26）。
  - F2：`test_alice_like_row_resave_unchanged_is_200`（GC10 seed 帳號唯讀，PATCH 是寫入，所以不對 alice 本人重存；改以 `make_user` 建會員並以 DB 寫入與 alice 合併後完全相同的一列（`early 0, flexible 1, Japan, Tokyo, 1200.5`），GET 後原樣 PATCH price-tracking → 200，DB 值不變（`price = 1200.5`）；`test_price_tracking_non_integer_new_price_is_400`（改成 `1300.5` → 400 `「預算上限」必須是 0 以上的整數`）。
  - `test_regions_lists_listed_tour_pairs`（`make_tour` 建上架行程並以 DB 設 `country = 'p5land'`、`region = 'p5city'` → 回應含該組；下架行程的組合不出現）；`test_regions_admin_is_403`、`test_regions_without_token_is_401`。
  - `test_price_tracking_invalid_region_is_400`（`Japan`／`Paris`、`日本`／`東京` → 400 `「國家」與「地區」不是系統提供的選項`）；`test_price_tracking_accepts_listed_pair`（`France`／`Paris` → 200）；**R2a** `test_delisted_saved_region_kept_and_resavable`（`make_tour` 建上架行程並設 `country = 'p5land'`、`region = 'p5city'`，會員存這組 → 以 DB 把該行程下架 → `GET` 仍回 `p5land`／`p5city`；原值不變再 PATCH 一次 → 200；改成 `p5land`／`p5other` → 400 `「國家」與「地區」不是系統提供的選項`）；`test_price_tracking_requires_fields`（開啟但缺 `region` → 400 `開啟價格追蹤時「地區」為必填欄位`）；`test_price_tracking_negative_price_is_400`；`test_early_not_boolean_is_400`（`"abc"` → `「旅遊提醒」必須是 true 或 false`）；`test_disable_price_tracking_clears_fields`。
  - `test_notify_without_token_is_401`、`test_notify_admin_is_403`（三支各一次，參數化）。
  - `test_validator_sweep.py`：`SWEEP_JS` 加 `automation.early`、`automation.price`；parametrize 加 `automation`。
  - E2E **R2a** `test_delisted_saved_region_shown_with_note`：同上建立並存好後下架 → 個人偏好設定分頁的國家、地區下拉仍選取原值，文字含 `（目前沒有上架行程）`；直接 `儲存設定` → `設定已儲存`。
  - E2E：`test_notify_settings_persist_after_reload`（勾 `出發前提醒`、`價格追蹤`，選 `Japan`／`Tokyo`、預算 30000 → `儲存設定` → `page.reload()` → 值都在；DB 1 列）。刪除 `test_coming_soon_tabs`，改 `test_no_coming_soon_tabs`（四個分頁都沒有 `即將開放`）。
- [ ] **Step 2: 跑紅燈**（F19 明列檔案）：`uv run pytest tests/test_member_notify.py tests/test_validator_sweep.py e2e/test_member_center.py e2e/test_member_flow.py -v --tb=short`；併發測試另跑 10 次（F26）：`for i in $(seq 10); do uv run pytest tests/test_member_notify.py::test_patch_concurrent_first_write_one_row -q --tb=line; done`，10 次都沒紅就照實寫。存 `task-6-red.txt`，commit 總覽 `test: 通知設定預設值、upsert、地區驗證、布林輸出 🔴`。
- [ ] **Step 3: 實作**：依 Interfaces。
- [ ] **Step 4: 綠燈**：`uv run pytest tests e2e -q`。commit backend `fix: 通知設定讀取預設值、寫入 upsert、地區須為系統選項、開關輸出布林 🟢`；frontend `feat: 個人偏好設定分頁（通知設定）、自動化設定頁導向 🟢`；總覽 `docs: 上鎖順序記錄通知設定 upsert`。

### Task 7: 收藏後端與商品回傳 favorite_id（雙審）

**Files:**
- Modify: `backend/migrations/R__views_functions.sql`：`tour_travel` `:77-115`（`收藏狀態` 在 `:112`）、`tour_tour_detail` 自 `:147`（`:223`）、`tour_hotel` 自 `:247`（`:326`）、`tour_restaurant` 自 `:351`（`:428`）的 `RETURNS TABLE` 與 SELECT
- Modify: `backend/src/controllers/product.js:295,370,461`
- Modify: `backend/src/routes/collection.js:14,17`、`controllers/collection.js:7-114`、`middlewares/collection/index.js`、`utils/Validator/collection_Validator.js`
- Create: `tests/test_member_favorites.py`
- Modify: `tests/test_async_errors.py`、`tests/test_api_smoke.py:365-376`、`tests/db_contract.py:60,76`（及 detail／hotel／restaurant 的欄位清單）、`tests/test_views_a.py:266-274`、`tests/test_validator_sweep.py`
- Modify: `docs/db-contract.md`（4 個 function 的欄位表加 `收藏編號`）、`docs/lock-order.md`（新增 §11 收藏新增）

**Interfaces:**
- Produces（function）：`(SELECT f.favorite_id FROM favorite f WHERE f.user_id = <fn>.使用者編號 AND f.tour_id = tb."旅遊編號") AS "收藏編號"`。
- Produces（API）：
  - `GET /info/all`：只回應一次；**不分頁**（F4／F5）：query 只認 `lang`（預設 `zh-TW`，其他鍵沿用 `stripUnknown` 忽略），`ORDER BY 建立時間 DESC, favorite_id LIMIT 100`，另算 `total`（實際總數）；回 `dbdata = { data, total }`；空列表 200 `查無資料`、`{ data: [], total: 0 }`；每筆保留 view 欄位（含 `上下架狀態`、`favorite_id`）與 `偏好分類`。
  - `POST /info/:tour_id`（加 `authRole('User')`）：Joi `tour_id` UUIDv4；`findListedTour`（`utils/purchase.js`）為 null → 404 `查無此旅遊項目`；`INSERT … ON CONFLICT (user_id, tour_id) DO NOTHING RETURNING favorite_id`，有回傳 → 201 `收藏成功`，否則 `SELECT favorite_id … WHERE user_id = $1 AND tour_id = $2` → 200 `已收藏過此行程`；兩者 `dbdata = { favorite_id }`。移除「查無此人」「已經收藏過」兩段查詢。
  - `DELETE /info/:favorite_id`（加 `authRole('User')`）：`DELETE … WHERE favorite_id = $1 AND user_id = $2 RETURNING favorite_id`；0 列 → 404 `查無此收藏項目`；200 `刪除成功`。
  - 詳情 API 三處 `is_favorited` 旁加 `favorite_id: rows[0].收藏編號 ?? null`。

- [ ] **Step 1: 寫紅燈測試**（`tests/test_member_favorites.py`；`FAV = "/api/v1/user/collection/info"`）
  - `test_favorite_first_time_is_201`（→ 201 `收藏成功`、回 `favorite_id`、DB 1 列）；`test_favorite_duplicate_returns_original_id`（第二次 → 200 `已收藏過此行程`、同一 `favorite_id`、DB 1 列）。
  - **Review Focus 3** `test_concurrent_favorite_same_tour_returns_same_id`（`Barrier(2)` 同時 POST → 狀態集合 `{200, 201}`、兩個 `favorite_id` 相同、DB 1 列；紅燈步驟跑 10 次，F25）。
  - `test_favorite_unlisted_tour_is_404`（`make_tour(status=2)` → 404 `查無此旅遊項目`）；`test_favorite_unknown_tour_is_404`；`test_favorite_bad_uuid_is_400`（`not-a-uuid` → 400 `「行程編號」必須是有效的 UUID 格式`）。
  - `test_delete_other_users_favorite_is_404`（B 刪 A 的 → 404 `查無此收藏項目`，A 的仍在）；`test_delete_own_favorite`（200 `刪除成功`、DB 0 列）；`test_delete_bad_uuid_is_400`（F20：`not-a-uuid` → 400 `「收藏編號」必須是有效的 UUID 格式`）。
  - `test_list_capped_at_100_newest_first`（F4：以 DB 插 101 筆收藏、`created_at` 遞增 → `len(data) == 100`、`total == 101`、第一筆是最新、最舊那筆不在）。
  - **Review Focus 5** `test_refavorite_after_delete_gets_new_id_and_old_id_404`（收藏 → 刪除 → 再收藏得到新 id ≠ 舊 id；DELETE 舊 id → 404；新收藏仍在）。
  - `test_favorite_admin_is_403`（POST、DELETE、GET 參數化）、`test_favorite_without_token_is_401`。
  - `test_list_single_response_and_unlisted_flag`（收藏一個上架、一個之後以 DB 改 `status = 2` 的行程 → 一次回應 2 筆，下架那筆 `上下架狀態 == 2`）；`test_list_empty`（`data == []`）。
  - `test_detail_returns_favorite_id`（收藏後 `GET /user/product/search/:tour_id` → `is_favorited is True`、`favorite_id` 等於 POST 回傳值；未收藏 `favorite_id is None`）；`test_search_returns_favorite_id`（搜尋結果該行程 `收藏編號` 等於 POST 回傳值）。
  - 既有測試：`test_api_smoke.py:365` 移除 `Connection: close` 與註解；`test_async_errors.py` 改用另一個仍在 try 外 reject 的路由（找不到 ⛔ 停下回報，不得刪測試），原路由另寫 `test_collection_bad_uuid_is_400`；`tests/db_contract.py` 4 個 function 的欄位加 `("收藏編號", "uuid")`；`test_views_a.py:274` 的比較同時排除 `收藏編號`；`test_validator_sweep.py`：`SWEEP_JS` 加 `collection.list`（`lang`）、`collection.tourID`、`collection.favoriteID` 三個 target，parametrize 加 `collection`（F11）；`test_api_smoke.py::test_favorite_list` 不再送 `PAGING`。
- [ ] **Step 2: 跑紅燈**：`uv run pytest tests/test_member_favorites.py tests/test_async_errors.py tests/test_api_smoke.py tests/test_db_contract.py tests/test_views_a.py tests/test_validator_sweep.py -v --tb=short`；併發測試另跑 10 次（F25）：`for i in $(seq 10); do uv run pytest tests/test_member_favorites.py::test_concurrent_favorite_same_tour_returns_same_id -q --tb=line; done`，10 次都沒紅就照實寫。存 `task-7-red.txt`，commit 總覽 `test: 收藏唯一、重複回原 id、404、商品回傳 favorite_id 🔴`。
- [ ] **Step 3: 實作**：依 Interfaces。`RETURNS TABLE` 能多一欄，是靠 `R__views_functions.sql:24-29` 開頭的 `DROP FUNCTION IF EXISTS … CASCADE`（簽章只看參數型別，不變），不要改動這段（R7）。
- [ ] **Step 3b: 在既有 volume 上驗證 R__ 重跑（R7）**：**不跑 `down -v`**。先記下 `SELECT count(*) FROM flyway_schema_history WHERE script = 'R__views_functions.sql'` 與 `SELECT proname FROM pg_proc WHERE pronamespace = 'public'::regnamespace` ＋ `SELECT viewname FROM pg_views WHERE schemaname = 'public'` 的清單；`docker compose run --rm flyway` 輸出含 `Migrating schema "public" with repeatable migration views functions`、結束碼 0；之後 history 多一列且 `success = t`，function／view 清單與執行前相同（檔頭註解的 21 個物件都在）。少了任何物件 ⛔ 停下回報。輸出存 `docs/reports/evidence/phase-5/task-7-repeatable-rerun.txt`。
- [ ] **Step 4: 綠燈**：`uv run pytest tests -q`。commit backend `fix: 收藏列表只回應一次、新增驗證 UUID 與 404、重複收藏回原 id、擁有者以 SQL 限定；feat: 商品回傳 favorite_id 🟢`；總覽 `docs: 契約與上鎖順序記錄收藏約束與收藏編號`。

### Task 8: 收藏前端、愛心元件、P5 主線 E2E（雙審）

**Files:**
- Create: `frontend/src/components/FavoriteHeart.vue`、`e2e/test_favorite_flow.py`
- Modify: `frontend/src/utils/api.js`（`apiUrl_collection`、`isMemberApi`）、`views/admin/collectPage.vue`、`views/front/searchPage.vue:170-225`、`views/front/tourPage.vue`、`views/HomeView.vue:159-161`

**Interfaces:**
- Consumes：Task 7 的 API 與鍵（詳情 `favorite_id`；搜尋／首頁 `收藏編號`；列表 `favorite_id`、`上下架狀態`、`旅遊編號`、`旅遊名稱`、`旅遊代表圖 Url`）。
- Produces（`api.js`）：`get_favorites() -> Promise<{ data: Array, total: number }>`（不帶分頁參數，無資料回 `{ data: [], total: 0 }`；F4／F5）、`post_favorite(tourId) -> Promise<{ favorite_id }>`、`delete_favorite(favoriteId) -> Promise<void>`。
- Produces（`FavoriteHeart.vue`）：props `tourId: String`（必填）、`favoriteId: String | null`；emits `update:favoriteId`；點擊 `@click.stop.prevent`；`userStore.isLoggedIn` 為 false → `router.push('/admin/login')`；先切換畫面狀態再呼叫 API，失敗還原（錯誤框由 `tradeRequest` 顯示）；請求進行中忽略點擊；圖示沿用 `assets/img/icon/favorite.svg`／`favorite-line.svg`。
- Produces（`collectPage.vue`，套 `HeaderComponent`／`FooterComponent`）：每張 `data-testid="favorite-card"`；上架卡片點擊進 `{ name: 'tour', params: { tour_id } }`；`上下架狀態 !== 1` → 標籤 `已下架`、卡片不可點、仍有 `取消收藏` 按鈕；空狀態 `還沒有收藏的行程` 與連結 `去逛逛`（→ `/search`）；不做分頁 UI；`total > 100` 時顯示 `只顯示最新 100 筆收藏`（F4）。

- [ ] **Step 1: 寫紅燈測試**（`e2e/test_favorite_flow.py`）
  - `test_p5_main_flow(page, db, make_user, make_tour)`（spec §0）：`make_tour(price=1000, start_date=+10 天, end_date=+12 天)` → UI 登入 → `/search` 以標題關鍵字搜尋 → 卡片的 `favorite-heart` 點擊（`aria-pressed="true"`）→ `#/admin/collect` 有該卡 → 點卡進行程頁 → 加入購物車 → `#/cart` `去結帳` → 填地址電話 → `確認並前往付款` → mock `付款成功` → 結果頁 `付款成功` → `#/admin/userprofile?tab=orders` 該筆 `已付款`、`明細` 含標題 → `?tab=level` 有 `購物回饋`、`+100` → `#/admin/collect` 按 `取消收藏` → `還沒有收藏的行程`；DB favorite 0 列。
  - `test_tour_page_heart_toggles(page, db, make_user, make_tour)`：點兩次 → DB 1 列 → 0 列。
  - `test_guest_heart_goes_to_login(page, make_tour)`：未登入點搜尋卡片愛心 → `**/#/admin/login`。
  - `test_home_heart_does_not_open_tour(page, make_user)`：首頁卡片愛心點擊 → URL 仍是首頁、`aria-pressed="true"`（spec §5 事件冒泡）。
  - `test_heart_reverts_on_failure(page, make_user, make_tour)`：`page.route("**/user/collection/info/*", lambda r: r.fulfill(status=500, body='{"status":"error","message":"伺服器錯誤"}'))` → 點擊後 `aria-pressed="false"`、錯誤框可見。
  - `test_unlisted_favorite_is_marked_and_removable(page, db, make_user, make_tour)`：收藏後以 DB 下架 → 收藏頁 `已下架` 可見；點卡片 URL 不變；`取消收藏` 後卡片消失。
  - `test_collect_page_empty(page, make_user)`：`還沒有收藏的行程`、`去逛逛` → `**/#/search`。
- [ ] **Step 2: 跑紅燈**：`uv run pytest e2e/test_favorite_flow.py -v --tb=short`。存 `task-8-red.txt`，commit 總覽 `test: 收藏頁、愛心元件、P5 主線 E2E 🔴`。
- [ ] **Step 3: 實作**：依 Interfaces；三個頁面用同一個 `FavoriteHeart`（首頁的靜態 `<span class="favorite">` 換成元件）。
- [ ] **Step 4: 綠燈**：`scripts/ci.sh` 全綠（tests＋e2e）。commit frontend `feat: 收藏頁、共用愛心元件（搜尋、行程頁、首頁） 🟢`。

### Task 9: P4 留下的項目（spec §7）（雙審）

**Files:**
- Modify: `backend/src/utils/trade.js:186-212`、`controllers/newebpay.js:159,174,187,193`
- Modify: `tests/test_trade_checkout.py`、`tests/test_trade_payment.py:565-588`
- Modify: `docs/superpowers/specs/2026-11-24-p4-trade-design.md`（§5.5「與程式註解的編號對照」整條與「（程式註解稱此為「第 7 步」。）」刪除）
- Modify: `docs/lock-order.md`（§7 逾時、§1 取消舊單各加 `orders` UPDATE 清折扣欄位，標「例外 A」）

**Interfaces:**
- Produces（`utils/trade.js`）：`clearOrderDiscount(client, orderId: string) -> Promise<void>`：`UPDATE orders SET discount_type = NULL, discount_price = NULL, updated_at = now() WHERE order_id = $1`；`expireIfOverdue` 在 `releaseReservations` 之後、`cancelPendingOrders` 在每張的 `releaseReservations` 之後呼叫。
- Produces（`tests/test_trade_payment.py`）：`_wait_until_blocked_by(db, holder_pid: int, timeout: float = 10.0) -> None`（輪詢 `pg_stat_activity WHERE wait_event_type = 'Lock' AND %s = ANY(pg_blocking_pids(pid))`，逾時 `pytest.fail`；寫法同 `tests/test_product_write.py:134-147`）；`_assert_waits_on_cart_not_cart_item` 以它取代 `future.result(timeout=1.5)`，之後仍斷言 `not future.done()`。
- `controllers/newebpay.js` 註解編號：`:159` 7 → 4、`:174` 4 → 5、`:187` 6 → 6（不變）、`:193` 5 → 7。

- [ ] **Step 1: 寫紅燈測試**（`tests/test_trade_checkout.py`）
  - `test_expire_clears_discount_columns`：券保留後 `created_at` 61 分鐘前 → summary → `discount_type IS NULL`、`discount_price IS NULL`、`user_coupon.status == 0`、`order_id IS NULL`。
  - `test_expire_point_order_clears_discount_columns`：點數 50 → 同上，`減少_確認中` 0 筆。
  - `test_cancel_previous_order_clears_discount_columns`：A 單 preview 用券 → 建 B 單 → A 的兩欄 NULL、券釋放。
  - `test_refund_keeps_discount_columns`（回歸測試，一開始就綠）：退款後 `discount_type` 不變（`computePayable` 已退款分支仍讀它）。
- [ ] **Step 2: 跑紅燈**：`uv run pytest tests/test_trade_checkout.py -k "clears_discount or keeps_discount" -v --tb=short`。存 `task-9-red.txt`，commit 總覽 `test: 逾時與取消清空訂單折扣欄位 🔴`。
- [ ] **Step 3: 實作**：`clearOrderDiscount`；`newebpay.js` 四處註解改號（只改註解）。
- [ ] **Step 4: NOWAIT 測試改輪詢**：改 `_assert_waits_on_cart_not_cart_item`；`uv run pytest tests/test_trade_payment.py -k "locks_cart_before_cart_item" -v` 連跑 3 次皆綠；用 mutation 驗證一次（F23）：先 commit 正式的修改，再把「helper 的 holder 改成不鎖 cart」做成 patch 檔（`git diff > $TMP/mutation.patch` 後 `git checkout -- tests/test_trade_payment.py`，或 `git stash`），套用後三個測試都要失敗，再還原；還原後 `git status --short` 必須沒有輸出（結果與指令寫 ledger）。
- [ ] **Step 5: 綠燈**：`uv run pytest tests -q`。commit backend `fix: 訂單逾時或被取消時清空折扣欄位；notify 註解改用 P4 spec 新編號 🟢`；總覽 `test: 鎖順序測試改為輪詢確認正在等鎖`（回歸測試）；總覽 `docs: P4 spec 刪除註解編號對照、上鎖順序記錄清折扣欄位`。

### Task 10: P5 報告、上鎖順序、契約、README（雙審；非 TDD）

**Files:**
- Create: `docs/reports/phase-5.md`
- Modify: `docs/lock-order.md`、`docs/db-contract.md`、`README.md`

- [ ] **Step 1: 上鎖順序全面核對**：以 backend `phase-5` HEAD 重跑 Task 0 Step 3 的核對，更新頂端核對 commit 與所有 `file:line`；確認「已知問題」多 cart 已標「P5 已解決（V6 `cart_user_id_key`＋`ON CONFLICT`，Task 1）」；「對應的測試」加 `test_first_add_concurrently_creates_one_cart`，「已知缺口」刪除 1.5 秒那句。
- [ ] **Step 2: 契約收尾**：`:1339`（`減少_確認中` → `減少` 已由 `trade.js` `settlePaidOrder` 處理）、`:1537`（P4 結算會寫 `payment_status = 1`）改寫為現況並註明 P5；確認 Task 1、3、7 的契約改動都在。
- [ ] **Step 3: 乾淨環境驗證**：⛔ 請使用者執行 `! docker compose down -v`；之後 `scripts/ci.sh` 連跑兩次（第 2 次保留 volume），記錄 passed／xfailed／skipped、耗時、exit code，原始摘要存 `docs/reports/evidence/phase-5/task-10-clean-ci.txt`。
- [ ] **Step 4: 報告初稿** `docs/reports/phase-5.md`，格式比照 `phase-4.md`：標頭（日期、三個 repo 的起點與分支最後 commit；tag 與 CI run 欄位留「待主對話合併後補」）；§0 摘要表（測試數 798 → 實跑數，GC18）；§1 每個問題：現象 → 根因與行號（P4 tag 的行號）→ 紅燈 evidence → 修正 → 綠燈（越權讀取、收藏兩次回應與 500、V6 與 seed 重複、通知設定、負點數與空券、姓名規則、Google 名字、§7 各項）；§1 另寫「與 spec 的差異」：逐條列出全部裁決 R1–R7、R2a、D1–D9、F1–F26 的內容與處理結果（F22）與 Task 0 查證結果（含 lock-order 行號核對，spec §7.6）；§2 Ruling 與雙審對照；§3 測試分層與數量；§4 操作指南（會員中心四個分頁、收藏、`?tab=`；seed 帳號唯讀）；附錄 A 變更檔案；附錄 B 已知限制（升級規則未實作、通知只存不寄、`/admin/personalOrder` 空頁、R2：價格追蹤以上架行程的英文地區為準，中文 `country`／`region` 表本階段未使用（P3 N5 留 P6）、P4 報告 :191 與 :387／:397 的矛盾以已裁決為準（spec §7.5，P4 報告不改））。**⛔ 停下請使用者審閱。**
- [ ] **Step 5: README**：版本對照表加 `| P5 會員中心 | phase-5 | phase-5 | [phase-5.md](docs/reports/phase-5.md) |`。
- [ ] **Step 6: final whole-branch review**：reviewer-opus＋reviewer-fable 平行審三個 repo 的 `phase-5`，處理 Critical／Important 後依 GC3 修正。
- [ ] **Step 7: Commit**（總覽）：`docs: P5 報告、上鎖順序核對、契約收尾、README 版本對照`。合併、tag、push 不在本計畫內，交回主對話。
