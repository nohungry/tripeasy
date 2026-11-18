# P3 商品 設計（Spec）

> 日期：2026-11-19 · 狀態：**草稿**（待使用者審閱；尚未經 builder check）
> 上位文件：`docs/superpowers/specs/2026-10-15-tripeasy-rebuild-design.md`（以下稱「總 spec」）§0「功能範圍」、§4 P3 列、§4.1–4.4、「階段完成標準」
> 前一階段：`docs/reports/phase-2.md`（以下稱「P2 報告」）附錄 B、§2.4、§3.3；`docs/reports/phase-1.md`（「P1 報告」）附錄 B
> 契約：`docs/db-contract.md`（以下稱「契約」）
> 產出方式：依使用者 2026-11-19 同意的範圍直接起草（未另開 brainstorming）
> 標記：**【使用者定】** = 使用者明確決定；**【Claude 定】** = 起草時由 Claude 決定，以 Ruling 格式「決定 — 理由 — 若錯的代價」寫出，可在審閱時推翻。
> 前提標記：**（已實測）** = 起草時在本機 compose（backend `3d835a6`、frontend `71a2171`、seed 載入日 2026-11-18）實際打 API 或用一次性 Playwright 腳本量過；**（讀碼推定）** = 只讀了程式碼，計畫裡對應步驟要先驗證，不符就停下回報。

## 0. 目的

讓**商品功能從前端能完整操作**（列表、搜尋、詳情、評論、隱藏玩法），並補上總 spec §0 要求的新功能：**只有購買過的會員能寫評論、分享隱藏玩法**。過程照 P2 寫成教學報告（總 spec §4.4、§5）。

**P3 的主線**【Claude 定】：**首頁 → 搜尋 → 詳情 → 讀評論與隱藏玩法 → 購買過的會員登入 → 寫評論 → 分享隱藏玩法**。E2E 以它為主（總 spec §4.2 的「搜尋 → 詳情」段落；購物車以後屬 P4）。

「完整操作」的意思：
1. 首頁「購物專區」的清單來自 API，可切換旅行團／背包客與子分類，點商品進詳情。
2. 搜尋頁的清單、篩選、排序、分頁都來自 API；header 的搜尋框可以帶關鍵字進搜尋頁。
3. 詳情頁依行程種類（travel／spot／hotel／food）顯示對應內容；不存在或已下架的行程顯示「查無此行程」。
4. 詳情頁可讀評論（含平均分數）與隱藏玩法，可載入更多；購買過的會員看得到表單並能送出，送出後立刻出現在列表；其他人看到說明文字，不會看到能送出的表單。

## 1. 範圍

### 要做（goals）
- 後端：既有讀取 API 的修正（§5.1）；新增 3 支 API：購買資格查詢、寫評論、分享隱藏玩法（§5.2）。
- DB：一個 versioned migration `V4`（§4），同步更新契約與契約測試（總 spec §0 重構規則最後一句）。
- 前端：首頁清單、搜尋頁、詳情頁接 API；評論與隱藏玩法的讀寫；移除假頁面路由（§6）。
- 測試：總 spec §4.2 的四層，主線 E2E（§7）。
- P1／P2 指派給 P3 的待辦，以及起草時新發現的問題，逐項 Ruling（§8）。

### 不做（non-goals）
- 購物車、結帳、付款 → P4。詳情頁的訂購區塊保留外觀，按鈕顯示「加入購物車（即將開放）」並停用（總 spec §4.3「範圍外的功能…標示未開放」）。
- 收藏（愛心）的新增／刪除 → P5。搜尋卡片上的愛心圖示移除；詳情頁不顯示收藏按鈕。
- 評論與隱藏玩法的**編輯、刪除、檢舉、管理者審核** → 不在任何已排定階段，P6 前再議（§12 不列為問題，記為已知限制）。
- 首頁「好評專區」接 API（網站好評 `review.type='web'`，不是商品評論）→ 延後，見 §8 表 N8。
- 搜尋頁的國家／地區下拉選單 → 移除，見 §8 表 N5。
- 搜尋結果的總筆數／總頁數 → 不改 API，見 §8 表 N4。
- 多語系（`lang` 一律送 `zh-TW`）。

### 反目標（做了也算失敗）
- 沒有買過（或訂單不是已付款）的人能寫入評論或隱藏玩法；或能以別人的訂單取得資格。
- 使用者輸入的內容在任何頁面被當成 HTML 執行（XSS），或 `javascript:` 等非 http(s) 連結能被存進隱藏玩法。
- 帶著過期 token 瀏覽公開頁面時，頁面壞掉或空白（`auth_not_mandatory` 對無效 token 回 401，見 §6.6）。
- 為了修 bug 順手重構，跟修正混在同一個 commit，或沒有先有測試覆蓋（總 spec §0）。
- main 上出現紅燈（總 spec §4.1）。

## 2. 約束

1. **沿用 P2 的流程**【使用者定】：backend 從 `main`、frontend 從 `dev`、總覽 repo 從 `main` 各開 `phase-3` 分支；每個 Task 紅燈與綠燈分開 commit 並留 evidence；最後一個 Task 寫報告、更新 `refs.env` 與 README 階段表、跑 `scripts/ci.sh` 全綠；合併、打 tag、push 每一步先問使用者。
2. **購買數的計算**【使用者定，2026-11-19 同意沿用契約 `docs/db-contract.md:130` 的裁決】：「購買數」＝ 該行程 `order_item.payment_status = 1` 的**列數**，不乘 `quantity`。P3 任何計數（含測試）都照這條。**P1 報告 `docs/reports/phase-1.md:199` 的待決事項（「P3 商品開工前要變成使用者明確決定」）由此結案**；契約 `:557` 與 `:1747` 兩處由計畫 Task 5 改成「使用者 2026-11-19 確認」。P3 的「購買過」用 `EXISTS` 判斷（§4.2），與計數方式無關，但沿用同一個「已付款」定義。
3. **結帳在 P4**【使用者定】：P3 的測試用 fixture 直接寫入 `orders`／`order_item`；seed 帳號（alice／bob／carol）**只能讀**，不能拿來寫評論或改它們的資料（`tests/test_seed.py:16–24` 的 `SEED_COUNTS` 對 `user`＝3、`review`＝13、`hidden_play`＝6 等做精確計數，寫入就會讓它變紅）。手動示範的帳號與步驟寫死在計畫 Task 13 Step 4。
4. **對 P4 的依賴（寫進契約與 P3 報告）**：現行付款流程到不了「已付款」：`controllers/newebpay.js:82,213` 對 `order_item` 寫不存在的 `payment` 欄位而 ROLLBACK（契約 §4.2）；`:203–206` 只更新 `orders.payment_status`。P3 的資格判斷看 `order_item.payment_status`（§4.2），所以 **P4 必須在付款成功時把 `order_item.payment_status` 設成 1**，否則真實買家永遠不能評論。這條列入 §8 延後表（N10），由 P4 的 spec 承接。
5. 重構規則（總 spec §0）：本設計中屬於重構的只有「刪除已不被路由引用的假頁面檔案」（§6.3），計畫中獨立 step、獨立 `refactor:` commit。
6. 不新增 npm 或 Python 套件。
7. 動到 schema 就同步契約與契約測試；`R__views_functions.sql` 本階段**不改**（§3.1 選 A 的理由之一）。

## 3. 做法比較（approaches）

### 3.1 「購買過」的判斷放在哪裡

| 做法 | 內容 | 優點 | 缺點 |
|---|---|---|---|
| **A（選定）** | 後端 `src/utils/purchase.js` 一支 `hasPurchased(userId, tourId)`，一條 `EXISTS` 查詢；寫入 API 的 middleware 與資格查詢 API 共用 | 規則只有一處；錯誤訊息與狀態碼完全由 API 控制；測試用 fixture 改訂單狀態就能驗 | 規則不在 DB 層，若日後有別的寫入路徑要記得呼叫 |
| B | 寫成 DB function 納入契約（`R__views_functions.sql`） | 規則可被 SQL 直接重用 | 要動 `R__views_functions.sql`（DROP 清單寫死的已知限制，P1 報告附錄 B）、契約、`tests/db_contract.py`，以及數 21 個物件的 `test_contract_lists_all_21_objects`；收益只是「可在 SQL 重用」，P3 用不到 |
| C | `review`／`hidden_play` 的 INSERT trigger 檢查購買 | 任何寫入路徑都擋得住 | 錯誤要從 SQLSTATE 轉成 403 與中文訊息；trigger 隱藏在 DB、教學報告難解釋；P1 契約沒有 trigger 的先例 |

**選 A**【Claude 定】— 規則集中在一個小函式、API 層完整掌握 403 的語意，且不碰 P1 的 view／function 契約 — 若錯（日後出現第二條寫入路徑忘了呼叫）：該路徑能繞過資格檢查；以「寫入 API 只有 §5.2 兩支」與 Review Focus 的測試把關。

### 3.2 前端怎麼知道要不要顯示表單

| 做法 | 內容 | 優點 | 缺點 |
|---|---|---|---|
| A | 登入就顯示表單，送出後吃 403／409 | 不加 API | 沒買的人填完才被拒，體驗差；「已評論過」無從得知，表單一直在 |
| **B（選定）** | 新增 `GET …/:tour_id/eligibility`，回 `{ can_write, has_reviewed }` | 與寫入共用 `hasPurchased`，前後一致；E2E 可以穩定斷言三種狀態 | 多一支 API（**超出「兩個寫入 API」的字面範圍**，回報時點名） |
| C | 在詳情回應加 `can_write` 等旗標 | 少一次請求 | 詳情 controller 有三個幾乎相同的回應分支（`controllers/product.js:215` 起），每支都要改；詳情 API 對訪客也開放，混入會員狀態讓回應語意變複雜 |

**選 B**【Claude 定】— 一支只讀的小 API 換來清楚的 UI 狀態與可測性 — 若錯（使用者只要兩個寫入 API）：刪掉這支 API，前端改用做法 A，成本約半個 Task。

### 3.3 重複評論的防線

| 做法 | 內容 | 缺點 |
|---|---|---|
| A | 只在 middleware 先查再寫 | 同時送出會寫入兩則（P2 註冊的同一類問題，P2 報告 §1.2） |
| **B（選定）** | middleware 先查（給友善訊息）＋ DB 部分唯一索引當最後防線，撞到 `23505` 回 409 | 多一個 migration；與 P2 `user_email_lower_key` 同一套寫法 |

**選 B**【Claude 定】— 沿用 P2 驗證過的「友善訊息＋DB 最後防線」 — 若錯（索引條件寫錯）：網站好評（`tour_id IS NULL`）被擋或重複評論漏網；由 §7 的 migration 測試與併發測試把關。

## 4. 資料庫

### 4.1 V4 migration

新檔 `backend/migrations/V4__p3_review_constraints.sql`，接在 `V3__p2_user_auth.sql` 之後：

| # | 變更 | 理由 |
|---|---|---|
| 1 | `CREATE UNIQUE INDEX review_user_tour_key ON review (user_id, tour_id) WHERE tour_id IS NOT NULL` | 一位會員對一個行程只能有一則評論（§3.3）；網站好評 `type='web'` 的 `tour_id` 為 NULL，不受限 |
| 2 | `ALTER TABLE review ADD CONSTRAINT review_rating_range CHECK (rating BETWEEN 1 AND 5)` | V1 `rating INT NOT NULL DEFAULT 1` 沒有範圍；API 驗證之外的最後防線 |

- seed 相容（已實測）：`review` 13 列的 `rating` 介於 3–5；`tour_id` 非 NULL 的評論沒有 (user_id, tour_id) 重複。計畫要在套用前再查一次，不符就停下回報。
- `hidden_play` **不加**唯一約束：同一位會員可以對同一行程分享多則玩法【Claude 定】— 分享是多則、評論是一則，與一般旅遊網站一致 — 若錯（被大量灌文）：P6 再加上限或審核，資料可回頭清。
- 契約新增 `## 6. P3 表格約束（V4）`（格式同 §5）；`tests/test_migrations.py` 加 V4 測試，並更新 `test_flyway_applied_v1_to_v3`（它斷言 history 恰為 1、2、3，加 V4 後會紅，計畫改名為 `test_flyway_applied_v1_to_v4`）。

### 4.2 「購買過」的定義（Ruling）

查過的 schema（`backend/migrations/V1__tripeasy_sql.sql`）：
- `orders`（`:270`）：`user_id`、`payment_status SMALLINT DEFAULT -1`。
- `order_item`（`:288`）：`order_id`、`tour_id`、`payment_status SMALLINT DEFAULT -1`、`quantity`。
- 兩個 `payment_status` 的值（V1 註解、契約 `:571`）：`-1` 資料剛建立、`0` 填寫完成未付款、`1` 已付款、`2` 已取消、`3` 已退款、`4` 付款逾時。
- `payment`（`:308`）另有 `payment_status`（0／1），一張訂單可能多筆。

**Ruling R1**【Claude 定】：會員 U 對行程 T「購買過」⇔
```sql
EXISTS (SELECT 1 FROM order_item oi JOIN orders o ON o.order_id = oi.order_id
        WHERE o.user_id = U AND oi.tour_id = T AND oi.payment_status = 1)
```
— 理由：(1) 只認「已付款」，與契約 #4（購買數只算 `payment_status = 1`）、#6 定案 B（以**項目層級** `order_item.payment_status` 篩選，`user_orders` view 同此）一致，全站對「買了」只有一個定義；(2) 擁有者看 `orders.user_id`（`order_item` 沒有 `user_id`）；(3) 不看 `payment` 表，因為它一單可多筆、且 P4 才會真正寫入 — 若錯的代價：P4 若只更新 `orders` 而沒更新 `order_item`，真實買家永遠不能評論（§2.4，已列 P4 依賴）；若使用者其實要以 `orders.payment_status` 為準，只改這一條 SQL 與對應測試。
- **已退款（3）不算**：退款代表交易撤銷；若錯（退款後仍出遊的人想評論）：把 `3` 加入條件，一行。
- **不要求「行程已結束」**：住宿、餐廳類商品沒有結束日，`order_item.end_date` 可為 NULL；若錯：加 `end_date < now()` 條件，P4 之後再議。
- **一人一行程一則評論**，不是一單一則：重複購買同一行程也只能評論一次（§4.1 #1）；`EXISTS` 不受同一行程多張已付款訂單影響。
- **只有 `User` 角色能寫**：沿用總 spec §4「admin 不結帳」；admin 打寫入 API 回 403（`authRole('User')`）。
- seed 對照（已實測，唯讀）：alice 已購買**且已評論**北海道（#1），所以 alice＋北海道為 `{ can_write: true, has_reviewed: true }`（顯示「你已評論過此行程」，玩法表單仍在）；alice 對義大利只有 `payment_status = -1`（#16），為 `{ can_write: false, has_reviewed: false }`；carol 已購買北海道（#3）且沒有評論，為 `{ can_write: true, has_reviewed: false }`。可寫評論的 seed 組合（已實測）：alice 的沖繩海景度假旅店、馬爾地夫蜜月天堂 6 日、高雄夜市美食攻略；carol 的北海道雪景 5 日深度遊、首爾咖啡文青小旅行——但 seed 帳號只能讀（§2.3），這些組合只用於唯讀的資格查詢，不用於寫入。

## 5. API 契約

路徑前綴：`/api/v1/user/product/search`（`backend/src/routes/product.js`，`server.js:93` 掛載）。回應外框沿用 `utils/resStatus.js`：成功 `{status:'success', message, data?}`；400／401／403／409 `{status:'failed', message}`；404 `{status:'false', message}`。**`resStatus` 只處理 200、201、400、401、403、404、409、500**，新 API 不得使用其他狀態碼。

### 5.1 既有讀取 API 的修正

| API | 現況 | 修正 |
|---|---|---|
| `GET /`（搜尋，`controllers/product.js:98`） | **分頁不穩**（已實測）：`ORDER BY 旅遊開始日期`／`價錢` 沒有次要排序，`limit=10` 時「首爾咖啡文青小旅行」同時出現在第 1、3 頁，另一個行程永遠拿不到；`limit=50` 一次取回則是 22 筆、不重複（已實測），確認根因是分頁時排序不穩 | `ORDER BY ${sortBy} ${order}, "旅遊編號" ASC` |
| 同上 | **`duration` 不生效**（已實測）：`duration=5` 回 10 筆；`buildDynamicTourSQL` 用 `typeof duration === 'number'`，但 query 參數是字串 | 條件改成 `duration !== undefined`，參數 `Number(duration)` |
| `GET /:tour_id`（詳情，`:172`） | **已下架回 500**（已實測：清邁自然旅宿體驗 `status=2`）；行程沒有子表資料時 `:209` 對 `rows[0]` 讀欄位 TypeError → 500（契約 §4.2）。只有 `tour_hotel`（`JOIN hotel`）、`tour_restaurant` 會回 0 列；`tour_tour_detail` 對 `tour_detail` 是 `LEFT JOIN LATERAL`（`R__views_functions.sql` 的 `tour_tour_detail`），travel／spot 沒有 `tour_detail` 時回 200、特色欄位為 null，維持現狀 | `tourRepo.rowCount === 0`（不存在或非上架）→ 404 `查無此旅遊項目`；`tourDetailsRepo.rowCount === 0` → 404，兩個檢查都在計算 `preferences`（`:208`）之前 |
| 同上（food） | `menu[]` 與 `opening[]` 共用 `rows`，各自含 `name: null`／`week: null` 的空項（契約 #34 選 B，「完整修正需改 controller（P3 商品）」） | `menu` 只取 `菜單名稱 IS NOT NULL` 的列，`opening` 只取 `營業星期 IS NOT NULL` 的列 |
| `GET /:tour_id/hidden-shares`（`:540`） | 回應沒有 `title`：`:574` 寫 `row.type`（P1 報告附錄 B） | 改 `row.title` |
| `GET /api/v1/user/home/search/products?item=promotion`（`controllers/home.js:31–46`） | 契約 #7、#9 留給 P3 的兩個缺口：未登入版直接查 `tour_base`，會列出**已下架**行程；兩個版本都沒有促銷**期間**條件 | 兩個查詢都加 `now() BETWEEN 促銷開始日期 AND 促銷結束日期`；未登入版另加 `上下架狀態 = 1`；排序加次要鍵 `旅遊編號 ASC`。**測試自建促銷**（`make_tour()` 加一筆期間為 `now() ± 1 day` 的促銷通知），不依賴 seed 的有效期；seed 的促銷日期在載入時就算好（2026-11-18 載入，最早 11-25、最晚 12-18 全部到期），到期只影響首頁展示，屬已知限制（放寬 seed 期間超出 P3 範圍） |

`GET /:tour_id/reviews`（`:473`）不改。評論與隱藏玩法的讀取對已下架行程仍回 200（已實測），維持現狀【Claude 定】— 前端只從詳情頁進入，下架行程的詳情已是 404，讀不到 — 若錯：多一個 404 判斷。

### 5.2 新增 API

三支都掛在同一個 router，middleware 鏈與**檢查順序固定**如下（每一步失敗即回應，不往下走）：

| 順序 | 檢查 | 失敗 | 適用 |
|---|---|---|---|
| 1 | `auth`：沒有或無效 token | 401（沿用 `middlewares/auth.js` 訊息） | 三支 |
| 2 | `authRole('User')` | 403 `您沒有權限進行此操作` | 三支 |
| 3 | `tour_id` 是 uuid v4（`tourIDSchema`） | 400 | 三支 |
| 4 | body 驗證（§5.3） | 400 | 兩支 POST |
| 5 | 行程存在且 `status = 1` | 404 `查無此旅遊項目` | 三支 |
| 6 | `hasPurchased` | 403（訊息見下） | 兩支 POST |
| 7 | 已評論過（middleware 先查） | 409 `你已評論過此行程` | POST reviews |
| 8 | INSERT 撞 `review_user_tour_key`（`23505`） | 409 `你已評論過此行程` | POST reviews |

下架行程不能寫入【Claude 定】— 前端進不到下架行程的詳情頁，開放寫入只會產生看不到的內容 — 若錯（買過已下架行程的人想評論）：步驟 5 改成「存在即可」，一行。

#### (a) `GET /:tour_id/eligibility` — 購買資格
- 權限：`auth`、`authRole('User')`。
- 200 `查詢成功`，`data: { can_write: boolean, has_reviewed: boolean }`。`can_write` ＝ `hasPurchased`；`has_reviewed` ＝ 該會員對該行程已有評論。
- 錯誤：401、403（admin）、400、404。

#### (b) `POST /:tour_id/reviews` — 寫評論
- 權限：`auth`、`authRole('User')`、購買過。
- body：`{ "rating": 1–5 的整數, "content": "1–500 字" }`。
- 寫入：`review (user_id, tour_id, type, rating, content)`，`type` ＝ 該行程的 `tour.item`（`travel`／`spot`／`hotel`／`food`，V1 `review.type` 註解），`hashtag` 為 NULL。seed 有 5 則 `review.type` 與 `tour.item` 不一致（已實測：馬爾地夫 hotel／travel、大阪 hotel／food、巴黎 food／spot、曼谷設計旅店 food／hotel、義大利 spot／travel，格式為 type／item），屬已知限制（§8.2 N13），P3 不修 seed。
- 201 `評論成功`，`data: { review_id, review_type, rating, content, create_date }`（鍵名對齊 `GET …/reviews` 的單筆項目）。
- 錯誤：401、403 角色、400、404、403 `購買過此行程的會員才能評論`、409 `你已評論過此行程`。

#### (c) `POST /:tour_id/hidden-shares` — 分享隱藏玩法
- 權限：同上。
- body：`{ "title": "1–50 字", "content": "1–1000 字", "url": "選填，http(s) 網址，≤255 字" }`。
- 寫入：`hidden_play (user_id, tour_id, title, content, share_url)`，`url` 沒給時 `share_url` 為 NULL。
- 201 `分享成功`，`data: { shares_id, title, content, url, create_date }`（鍵名對齊 `GET …/hidden-shares`）。
- 錯誤：401、403 角色、400、404、403 `購買過此行程的會員才能分享隱藏玩法`。不檢查重複（§4.1）。

### 5.3 驗證規則（`utils/Validator/product_Validator.js` 新增兩個 schema）

| 欄位 | 規則 | 訊息 |
|---|---|---|
| `rating` | `Joi.number().integer().min(1).max(5).strict().required()`：**只收 JSON 整數**，字串 `"5"`、`4.5` 都 400 | `「rating」必須是 1 到 5 的整數`；缺少 `請輸入「rating」` |
| `content`（評論） | `string().trim().min(1).max(500).required()` | 空白 `「content」不得為空白`；超長 `「content」不可超過 500 字`；缺少 `請輸入「content」` |
| `title` | `string().trim().min(1).max(50).required()` | `「title」不得為空白`、`「title」不可超過 50 字`、`請輸入「title」` |
| `content`（玩法） | `string().trim().min(1).max(1000).required()` | `「content」不得為空白`、`「content」不可超過 1000 字`、`請輸入「content」` |
| `url` | `string().trim().uri({ scheme: ['http', 'https'] }).max(255).optional()`；空字串 400 | `string.empty`、`string.uri`、`string.uriCustomScheme` 都是 `「url」必須是 http 或 https 網址`（已實測 `javascript:`、`data:`、`ftp:` 為 `uriCustomScheme`，`""` 為 `string.empty`）；`string.max` 為 `「url」不可超過 255 字` |
| 未知欄位 | Joi 預設拒絕；訊息模板用 `{#key}`（`{#label}` 會被 Joi 加上雙引號，已實測） | `不支援的欄位「hashtag」`（模板 `不支援的欄位「{#key}」`） |

- 驗證後的值（trim 過）寫回 `req.body`，controller 只讀 `req.body`。
- 字數以 JavaScript 字串長度計（UTF-16 code unit；中文一字算 1，emoji 可能算 2），已知限制。

### 5.4 XSS 與內容安全【Claude 定】
- 後端**原樣保存**（只 trim），不做 HTML 過濾或跳脫 — 跳脫是輸出端的責任，存原文才能在任何輸出環境正確處理 — 若錯（日後有輸出端用 `v-html` 或伺服器端模板）：該輸出端會有 XSS；以下兩條規則與 E2E 把關。
- 前端顯示使用者內容**只用文字插值 `{{ }}`**，禁止 `v-html`。
- `url` 只允許 http／https（擋 `javascript:`、`data:`），前端以 `<a :href rel="noopener noreferrer" target="_blank">` 顯示。

## 6. 前端頁面與流程

### 6.1 已確認的前提
- （已實測）首頁 `#/`：HomeLayout 的 header 與 HomeView 自帶的 `.nav`（`HomeView.vue:5–7`，捲動後才出現的 header）同時存在，`.header` 2 個、`.footer` 2 個（HomeView 自己又放了 `FooterComponent`，`:291`）。這就是 P2 報告附錄 B.3 的「首頁雙 header」。
- （已實測）`#/tour`、`#/tourfake`、`#/tourfakeUSA` 也是 2 個 header、2 個 footer（頁面自帶 Header／Footer，又掛在 HomeLayout 底下）；`#/search` 1 個（P2 已改成頂層路由）。
- （已實測）header 搜尋框（`HeaderComponent.vue:12`、`:104` 的 `@submit.prevent="search"`）輸入後按 Enter 沒有任何反應：script 內沒有定義 `search`。
- （讀碼推定）`tourPage.vue` 是空殼（`data() {}` 回 undefined、呼叫不存在的 `fetchUserInfo`）；`searchPage.vue` 的清單是寫死的 `allItems`，「查看詳情」連到 `/tourfakeUSA`（`:257`）；`HomeView.vue:350` 的 `productList` 寫死 3 筆；`utils/api.js` 沒有任何商品函式。

### 6.2 首頁（`views/HomeView.vue`）
- **雙 header**【Claude 定】：移除 HomeView 自帶的 `.nav` 區塊（`:5–7`）與 `<FooterComponent />`（`:291`）及兩者的 import／註冊，保留 HomeLayout 的 header 與 footer — 全站 header 一致、首頁頂端就有導覽與登入入口（E2E 主線從首頁出發需要）；P2 對 `/search` 是把頁面移出 layout，但首頁若移出 layout，`/` 會與 layout 父路由同路徑，比對規則難以預期 — 若錯（設計上要保留「捲動後才出現」的效果）：還原 `.nav`、改由 HomeLayout 在首頁隱藏自己的 header，約半天。`isSticky`／`handleScroll` 變成沒有作用，但不刪（不順手重構，記入 ledger）。
- **購物專區**：分類分頁「旅行團」→ `type=tourgroup`，子分頁「熱門專區／促銷專區／多人收藏」→ `item=popular／promotion／most_favorited`；「背包客」→ `type=backpacker`，子分頁改顯示「住宿／美食／景點」→ `item=hotel／food／spot`。每頁 4 筆，左右箭頭換頁，顯示目前頁碼（沒有總頁數，見 §8 N4）；點商品進 `#/tour/<旅遊編號>`。卡片：標籤（`偏好分類`）、名稱、出發日（`旅遊開始日期` 的 `YYYY-MM-DD`，NULL 顯示「自由選擇」）、價格（`促銷價錢 ?? 價錢`）、右側大圖（`旅遊代表圖 Url`）。

### 6.3 詳情頁（新路由 `#/tour/:tour_id`）
- 路由：HomeLayout 底下 `path: 'tour/:tour_id'`、`name: 'tour'`、`meta.title: '行程詳情'`。移除 `tour`（無參數）、`tourfake`、`tourfakeUSA` 三條路由（之後開這三個網址會到 404 頁）。`tourPage.vue` 改寫成真的詳情頁，**不自帶 Header／Footer**。
- 重構（獨立 commit）：刪除 `views/front/tourPageFake.vue`、`views/front/tourFakeUSA.vue`，以及只被它們引用的圖檔（以 grep 確認沒有其他引用）。
- 內容：名稱（`h2`）、標語、代表圖與 6 張圖、價格（有促銷時顯示促銷價與劃線原價）、日期區間（NULL 顯示「自由選擇」）、標籤、描述、地點（國家／地區／地址／Google Map 連結）、異動通知（有才顯示）。依 `item` 顯示：
  - `travel`／`spot`：「行程特色」（`feature[]`）、「行程規劃」（`itinerary`）。
  - `hotel`：「房型介紹」（`feature.room[]`）、「客房服務」（`feature.service[]`）。
  - `food`：「餐廳介紹」（`feature.about`）、「菜單」（`feature.menu[]`）、「營業時間」（`feature.opening[]`）。
- 訂購區塊：按鈕「加入購物車（即將開放）」，`disabled`。
- 404／400 → 顯示「查無此行程」與回搜尋頁的連結。

### 6.4 搜尋頁（`views/front/searchPage.vue`，維持頂層路由）
- 清單改呼叫搜尋 API；篩選保留「旅遊天數（不限、1–10 日）、購買金額（最小／最大）、旅遊日期（起／訖）、關鍵字」，**移除國家、地區兩個下拉選單**（§8 N5）；排序「金額排序」：未選 → `sort_by=date&order=asc`、升序 → `price asc`、降序 → `price desc`；每頁筆數 2／4／6（預設 6）。
- 分頁改成「上一頁／第 N 頁／下一頁」：回傳筆數小於每頁筆數時停用「下一頁」（§8 N4）。
- 空結果顯示「查無符合條件的行程」。
- 卡片：名稱、描述、標籤、日期、價格（有促銷時促銷價＋劃線原價，沒有促銷不顯示劃線價）、代表圖；「查看詳情」連到 `#/tour/<旅遊編號>`；愛心圖示移除（P5）。
- 讀 `route.query.keyword` 當初始關鍵字，並在它變動時重新查詢第 1 頁。
- header 搜尋框（`HeaderComponent.vue`）：補上 `search()`，`router.push({ path: '/search', query: { keyword } })`（去頭尾空白）。`HeaderReal.vue` 未被使用（P2 報告附錄 B.3），不改。

### 6.5 評論與隱藏玩法（詳情頁下半部）
- 「旅客評論」：平均分數（`平均 4.3 分`，沒有評論時顯示「目前還沒有評論」）、列表（名稱、等級名稱、評分、內容、日期），每次 5 筆，「載入更多評論」在最後一次回傳滿 5 筆時才顯示。
- 「隱藏玩法」：列表（標題、內容、分享者、日期、有 `url` 時顯示「查看分享連結」），每次 5 筆，「載入更多玩法」同上。
- 表單狀態（依 §5.2 (a)）：

| 狀態 | 評論區 | 隱藏玩法區 |
|---|---|---|
| 未登入 | 「登入後，購買過此行程的會員可以評論與分享隱藏玩法」＋「登入」連結 | 同左 |
| 已登入、`can_write = false`（含 admin 的 403） | 「購買過此行程的會員才能評論與分享隱藏玩法」 | 同左 |
| `can_write = true`、`has_reviewed = false` | 評論表單（評分 1–5、內容、字數計數、「送出評論」） | 玩法表單（標題、內容、分享連結（選填）、「分享玩法」） |
| `can_write = true`、`has_reviewed = true` | 「你已評論過此行程」 | 玩法表單 |

- 送出成功：成功提示（Swal `timer`，§6.6），重新讀第 1 頁與資格；失敗：顯示後端訊息（403／409／400）。

### 6.6 共用：401 與提示框【Claude 定】
- **401 統一處理**（P2 報告附錄 B.3「401 統一『登入已過期』」）：axios interceptor 對「**有帶 `Authorization` 的請求**回 401」一律：`userStore.logout()`、在 error 上標 `sessionExpired = true`、顯示 Swal（`icon: 'warning'`、標題 `登入已過期`、內文 `請重新登入`、`timer: 2000`）。排除 `/login/status`、`/login/email`、`/login/google`（`router.beforeEach` 與 `requireAuth` 自己處理，P2 Ruling 20、21）。**會員 API**（會員資料、改密碼、兩支寫入 API）再 `router.replace('/admin/login')`；**公開讀取**（首頁清單、搜尋、詳情、評論、隱藏玩法）留在原頁，由呼叫端不帶 token 重試一次；**資格查詢**雖需登入，但它在詳情頁載入時自動呼叫，401 時也**不導頁**，只回 `{ can_write: false, has_reviewed: false }`，讓帶過期 token 的訪客留在詳情頁 — 理由：後端 `auth_not_mandatory` 對無效 token 回 401（P2 的安全測試 `test_invalid_tokens_are_401` 釘住此行為，不改後端），不重試的話帶過期 token 的訪客會看到空白頁 — 若錯（使用者要後端把無效 token 當訪客）：改 `auth_not_mandatory.js` 並改寫 P2 那個測試，前端重試可留可刪。
- 會員 API 的呼叫端（`api.js` 的 `patch_user_Profile`、`patch_user_Avatar`、`post_user_resetProfilePW`，以及 P3 新增的兩支寫入）遇到 `sessionExpired` 不再顯示自己的錯誤 Swal（P2 報告附錄 B.3「401 之後登入頁仍跳後端錯誤 Swal」）。
- **成功提示改用 timer**（P2 報告附錄 B.3）：`api.js:53`、`:104`、`:155`、`:228` 的 `setTimeout(() => { Swal.close(); router.push(…) }, 3000)` 改成 `Swal.fire({…, timer: 3000, timerProgressBar: true}).then(() => router.push(…))`。行為差異：使用者按「OK」會立即跳轉（原本仍等滿 3 秒）；不會再誤關別的彈窗。這會動到 P2 的註冊、登入、Google 登入、重設密碼流程，計畫要求該 Task 跑全套 E2E 回歸。P3 新程式一律用這個寫法。

## 7. 測試策略

照總 spec §4.1（紅燈先、單獨 commit、輸出存 evidence）與 §4.2 分層。

| 層 | 內容 |
|---|---|
| API 契約 | 三支新 API 的正常、每個驗證錯誤、401／403；既有讀取 API 的修正（§5.1）；回應鍵名對齊 GET |
| 安全 | 未付款狀態（-1、0、2、3、4）都不能寫；別人的已付款訂單不算；別的行程的訂單不算；admin 403；`javascript:`／`data:`／`ftp:` 網址 400；HTML 內容原樣保存（API）且在頁面以文字顯示、不執行（E2E）；同時送出 5 則評論只成功 1 則、其餘 409、沒有 500 |
| DB 狀態 | 寫入後 `review.type = tour.item`、內容已 trim、`hidden_play.share_url` NULL／有值；V4 的索引與 CHECK（含 `tour_id IS NULL` 的網站好評不受唯一限制）；seed 唯讀冒煙（alice 的資格） |
| E2E（`e2e/test_product_flow.py`，新） | 主線（§0）；首頁單一 header 與清單；搜尋分頁走完每個上架行程恰一次；header 關鍵字搜尋；詳情四種 item；未登入／未購買的提示；XSS 以文字顯示；過期 token 在公開頁與寫入時的行為；假頁面路由變 404 |

- **fixture**（`tests/conftest.py`，`e2e/conftest.py` 明確匯出）：`make_tour`（以 `tests/dbfactory.py::insert` 建立 `p3-` 開頭的行程，可選 `tour_detail`、`status`）、`make_order`（建立 `orders`＋`order_item`，可指定 `payment_status`）。每個測試自建資料、結束清除，不依賴 seed 的可變狀態。
- **殘留清除**：P3 的 fixture 會把資料 commit 進 `tour`、`orders`、`order_item`、`review`、`hidden_play`，而 `tests/test_seed.py` 的 `SEED_COUNTS` 對這些表做 exact count。新增 session 開頭執行一次的清除：刪除 email 符合測試前綴的會員（連同其資料，`delete_user`）與標題 `p3-` 開頭的行程（§8 C9）。
- 測試數量：P2 結束為 329 passed、2 xfailed；P3 結束時**不應有任何 xfail**（PATCH `/info` 的兩個 strict xfail 移除，§8 C1）。

## 8. 待辦：納入與延後

### 8.1 P1／P2 指派給 P3 的項目

| # | 項目 | 決定 — 理由 — 若錯的代價 |
|---|---|---|
| C1 | PATCH `/info` 部分更新回 500（`middlewares/userProfile/index.js:29–30` 對 `undefined` 呼叫 `.map`；`controllers/userProfile.js:54–57` 一律 `SET name = $1`），移除 `tests/test_member_auth.py:397`、`:406` 兩個 strict xfail | **納入** — 修法小（middleware 只在有 `preference` 時轉換；controller 用 `COALESCE`），紅燈測試已存在，移除後 P3 達成「零 xfail」 — 若錯：會員資料 API 回歸，由 P2 的會員測試與 E2E 把關 |
| C2 | `controllers/product.js:1360` `delete_tourProduct` 的 `pool.connect()` 沒有 release | **納入** — 屬後台（P6），但洩漏會耗盡 pool（max 10），而 P2 之後每個帶 token 的請求都要查 DB（P2 報告附錄 B.1），會拖垮 P3 的全部會員 API；修法是 `try/finally release`。紅燈會耗盡 pool，要單獨執行、存證後 `docker compose restart backend`；只能刪 fixture 建的行程 — 若錯：多一個後台小修，無行為風險 |
| C3 | `controllers/product.js:574` 隱藏玩法 `title` 誤用 `row.type` | **納入** — P3 本身的功能 — 若錯：無 |
| C4 | `user.role` 加 CHECK 約束 | **延後到 P6（後台會員／角色）** — 不影響 P3；P2 已在唯一的寫入點正規化（`controllers/admin.js:58`）；V4 只動 `review`，混入無關的 schema 變更會讓 migration 難以追溯 — 若錯：P6 多一個 migration，成本低 |
| C5 | `ROLLBACK` 本身丟錯時請求懸掛（P2 報告附錄 B.2） | **延後，只記錄** — `server.js:3` 已載入 `express-async-errors`，catch 內再丟錯會被導到 error handler 回 500，「懸掛」很可能不成立；黑箱測試也無法讓 ROLLBACK 丟錯，寫不出紅燈。P3 新增的寫入是單一 `INSERT`，不開交易。P4（`cart.js`、`checkout.js`、`newebpay.js`）重寫交易時再以 fault injection 查證 — 若錯（真的會懸掛）：P4 之前在這些路徑上遇到 DB 錯誤的請求會卡到逾時 |
| C6 | 前端：`Swal.close()` 改用 `timer` | **納入**（§6.6）— 小而確定；P3 新增的提示要用同一套寫法 — 若錯：動到 P2 的四個流程，以全套 E2E 回歸把關 |
| C7 | 前端：401 統一顯示「登入已過期」 | **納入**（§6.6）— P3 新增會員 API（資格、兩支寫入），也必須處理公開頁的過期 token — 若錯：見 §6.6 |
| C8 | 前端：首頁雙 header | **納入**（§6.2）— P3 要改首頁清單，且主線從首頁出發 — 若錯：見 §6.2 |
| C9 | 測試：前綴殘留讓 `test_seed.py` 筆數斷言變紅 | **納入** — P3 fixture 會寫入更多 seed 計數的表，殘留機率更高；做法是 session 開頭的清除函式（只刪測試前綴的會員與 `p3-` 行程，**不刪**其他手動建立的帳號），並有測試證明不會刪到 seed 與非測試帳號 — 若錯（前綴清單漏列）：殘留仍會讓 seed 測試紅，照 P2 報告 §4.4 手動清 |
| C10 | 測試：`test_admin_product_empty_result` 的斷言收緊為 `"data" not in r.json()` | **納入** — 一行、test-only（不是行為修正，沒有紅燈，commit 訊息註明） — 若錯：無 |
| C11 | CI：`requires-python` 加 `<3.14` 上限，或升級 psycopg | **選上限 `>=3.10,<3.14`** — 已查 PyPI：`psycopg-binary` 3.2.3 沒有 cp314 wheel、3.2.10 起才有；改上限不動任何測試依賴，並與 CI 綠燈實際使用的 CPython 3.13.18（P2 報告 §3.3）、`.python-version` 一致；升級 psycopg 則等於在 P3 換掉測試用的 DB driver。兩者都要 `uv lock` 並 commit `uv.lock`（`ci.sh` 用 `--frozen`） — 若錯：日後要支援 3.14 時拿掉上限並升級 psycopg（≥3.2.10），連同 lock 一起改 |
| C12 | CI：鎖定 uv 版本 | **用 `setup-uv` 的 `version` input 固定 `0.13.9`**（P2 綠燈 run 44323636173 實際使用的版本；PyPI 目前最新也是 0.13.9）；**不用** `[tool.uv] required-version` — 本機 uv 是 0.11.26，精確的 `required-version` 會讓本機每個 `uv run` 失敗。計畫要以 `gh api` 查證 `0.13.9` 存在、`setup-uv@v10.3.3` 有 `version` input（P1 報告 `:191` 的 `@v10` 教訓）；本機 `ci.sh` 不跑 workflow，這兩項只能靠查證與 push 後的 run 確認 — 若錯（版本或 input 不存在）：CI 在 Set up job 失敗，push 後立即可見，改版本號即可 |
| C13 | P2 報告 §4.1 補一句「總覽 repo 的 `phase-2` tag 本身沒有 `.python-version`，要重現時用 main」 | **納入**，放在最後的報告 Task — 若錯：無 |
| C14 | P1 遺留（`R__views_functions.sql` DROP 清單寫死、`tests/db_contract.py` 不比對契約文字） | **不處理，報告重申** — P3 不改 view／function（§2.7） — 若錯：同 P1／P2 |

### 8.2 起草時新發現或契約指給 P3 的項目（不在派工清單，Claude 加入）

| # | 項目 | 決定 — 理由 — 若錯的代價 |
|---|---|---|
| N1 | 搜尋分頁不穩（§5.1，已實測） | **納入** — 直接影響「列表／搜尋」能否完整瀏覽 — 若錯：無 |
| N2 | 搜尋 `duration` 不生效（§5.1，已實測） | **納入** — 搜尋頁有「旅遊天數」篩選 — 若錯：無 |
| N3 | 詳情：已下架、沒有子表資料時 500（契約 §4.2）；food 的 `menu`／`opening` 空項（契約 #34） | **納入** — 詳情頁是主線 — 若錯：無 |
| N4 | 搜尋與首頁清單 API 沒有總筆數 | **延後（不改 API）** — 改回應形狀會動到 `tests/test_api_smoke.py` 的契約測試；用「回傳筆數小於每頁筆數就沒有下一頁」即可完整瀏覽 — 若錯（要顯示總頁數）：之後加 `X-Total-Count` header，不動 body |
| N5 | 行程的國家／地區是英文（`Japan`），`/web/filter/countries` 回中文（`日本`），下拉選單無法對應 | **延後到 P6（後台商品 CRUD 決定國家欄位的來源）**，P3 移除兩個下拉選單；API 的 `country`／`region` 參數保留 — 若錯：搜尋少兩個篩選條件 |
| N6 | 首頁促銷分頁：未登入露出下架行程（契約 #7）、兩個版本都沒有期間條件（契約 #9） | **納入** — 契約明文留給 P3，首頁清單要接 API — 若錯：無 |
| N7 | 空結果時回應沒有 `data` 欄位（`resStatus` 只在有資料時輸出） | **不改，前端以 `data ?? []` 處理** — 改了會牽動所有清單 API — 若錯：無 |
| N8 | 首頁「好評專區」寫死（網站好評） | **延後（未排定，P6 前再議）** — 是網站好評，不是商品評論；寫入網站好評的功能也不存在 — 若錯：首頁好評仍是假資料，報告列已知限制 |
| N9 | 首頁未帶 `type` 時 500（契約 §4.2） | **延後** — 前端一律帶 `type` 與 `item`，P3 碰不到 — 若錯：直接打 API 的人會看到 500 |
| N10 | 付款成功沒有把 `order_item.payment_status` 設成 1（`newebpay.js:82,213,203–206`） | **延後到 P4，列為 P4 必做**（§2.4） — 結帳屬 P4 — 若錯（P4 沒做）：真實買家無法評論 |
| N12 | seed 本身就有「沒買過的人」寫的評論與隱藏玩法（已實測）：評論 bob→馬爾地夫（無訂單）、carol→紐西蘭（訂單 `payment_status = 2`）、carol→義大利（無訂單）、alice→巴黎（無訂單）；玩法 alice→紐西蘭（`payment_status = 4`）、alice→大阪（無訂單） | **不追溯既有資料，列已知限制** — 規則只約束新寫入；改 seed 會牽動 `SEED_COUNTS` 與契約 §0.1 — 若錯：展示時看得到「沒買過的人的評論」，可在重建 seed 時一併修 |
| N13 | seed 有 5 則 `review.type` 與 `tour.item` 不一致（§5.2 (b)） | **列已知限制，不修** — 只影響 `review_type` 欄位的顯示，P3 頁面不顯示它 — 若錯：重建 seed 時修正 |
| N11 | 其他 `pool.connect` 疑似漏 release（`cart.js`、`checkout.js`、`newebpay.js`）、`product.js:609` 的新增商品 | **延後到 P4／P6** — 不在 P3 會呼叫的路徑上（P2 Ruling 10） — 若錯：重複呼叫這些 API 會耗盡 pool |

## 9. 流程與約束（沿用總 spec 與 P2）

- git：見 §2.1。每次 backend／frontend commit 後，總覽 repo 的 `refs.env` 指到 `phase-3` 分支；最後的 Task 才改成 tag。
- 審查：依使用者 `~/.claude/CLAUDE.md`：每個 Task 由 reviewer-opus 審；跨多檔、動到共用設定或 CI 的 Task 加 reviewer-fable 平行雙審（計畫逐 Task 標明）。見 §12 Q1。
- 報告 `docs/reports/phase-3.md`，照總 spec §5 範本；使用者確認後才進 P4。

## 10. 完成標準

- §0 的主線能從前端完整操作，E2E 覆蓋並在 CI 綠燈。
- §5、§8 每個納入項都有紅燈 → 綠燈的證明（test-only 的 C10、CI 設定 C11／C12 依計畫的例外說明）。
- 全套沒有 xfail；P1、P2 的測試不退化。
- 契約與契約測試反映 V4；契約 `:557`、`:1747` 的購買數裁決改為使用者確認。
- review 沒有未處理的 Critical／Important；報告定稿。

## 11. 留給實作者決定

頁面樣式與版面細節；E2E 的 locator 寫法（以角色與文字為主）；evidence 檔是否拆成多份（命名規則照計畫）。其餘都已在本 spec 或計畫中定死。

## 12. 待使用者確認

1. **Q1 審查方式**：P2 由使用者選擇「每個 Task 都 opus＋fable 雙審」（P2 報告 §2.4 Ruling 1），覆蓋了全域門檻。P3 計畫預設回到 `~/.claude/CLAUDE.md` 的門檻（小改動只派 reviewer-opus；跨多檔、共用設定、CI 才雙審）。是否要像 P2 一樣全部雙審？
