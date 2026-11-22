# Phase 3：商品（列表、搜尋、詳情、評論與隱藏玩法）
> **初稿，待使用者審閱**（2026-11-19 起草） · backend tag `phase-3`（分支最後 commit `adffa31`；已合併至 `main`，合併 commit `06ded19`，tag `phase-3` 指向合併 commit） · frontend tag `phase-3`（分支最後 commit `9940fa1`；已合併至 `dev`，合併 commit `ae9b824`，tag `phase-3` 指向合併 commit） · 總覽 repo 分支 `phase-3`（起草時 `d73a78d`，起點 `ac8cbdc`；之後的修正與最後 commit 見附錄 C 與 `git log`）；總覽 repo 已合併至 `main`，合併 commit `34d2a7c`（README 版本對照表加 P3 為 `433ac28`），tag `phase-3` 指向合併 commit。三個 repo 的主分支與 tag 已於 2026-11-22 push
>
> 本報告依 `docs/superpowers/specs/2026-10-15-tripeasy-rebuild-design.md` §5 範本與 `docs/reports/phase-2.md` 的格式撰寫。設計見 `docs/superpowers/specs/2026-11-19-p3-product-design.md`（以下稱「P3 spec」），計畫見 `docs/superpowers/plans/2026-11-19-p3-product.md`。引用一律以 commit hash、`檔案:行號`、evidence 檔名為出處；查不到的寫「未查證」。
>
> 行號基準：P3 之前就存在的問題，行號取自 backend `main`（`3d835a6`）／frontend `dev`（`71a2171`）修正前，多數沿用 P3 spec 的實測行號。
>
> **本稿尚缺**：(1) §2.1 使用的 skill 與關鍵 prompt（ledger 沒有紀錄，仍標「未查證」，需使用者補）。

## 0. 摘要

P3 的目標：讓「首頁 → 搜尋 → 詳情 → 讀評論與隱藏玩法 → 購買過的會員登入 → 寫評論 → 分享隱藏玩法」這條主線能從前端完整操作，並補上總 spec §0 的新規則：**只有購買過（`order_item.payment_status = 1`）的 `User` 角色會員能寫評論、分享隱藏玩法**。

| 項目 | 結果 |
|---|---|
| 測試數量 | **329 passed、2 xfailed（P2 結束）→ 499 passed、0 xfailed**（`scripts/ci.sh` 連跑兩次，見 §3.3；最終修正波後 **505 passed、0 xfailed**，見附錄 C）。收集數 331 → 499，淨增 168 個測試；2 個 strict xfail 移除後轉為一般通過 |
| xfail | **2 → 0**：PATCH `/info` 部分更新的兩個 strict xfail（`tests/test_member_auth.py:397`、`:406`）因修好而移除（§1.1） |
| 後端 | 既有讀取 API 修 5 類問題（搜尋分頁不穩、`duration` 不生效、詳情 500、food 空項、隱藏玩法 `title`）；首頁促銷修 2 個契約缺口；新增 3 支 API（資格查詢、寫評論、分享隱藏玩法）；新增 migration `V4`（一人一行程一則評論、評分 1–5） |
| 前端 | 首頁清單、搜尋頁、詳情頁接 API；詳情頁評論與隱藏玩法讀寫；401 統一提示、成功提示改 `timer`；首頁雙 header 修掉；刪除假行程頁與其圖檔 |
| 測試／CI 基礎 | session 開頭殘留清除、`make_tour`／`make_order` fixture；`requires-python` 加上限；CI 鎖 uv 版本；job 加 `timeout-minutes` |
| 購買數 | 「購買數」＝ `order_item.payment_status = 1` 的列數，不乘 `quantity`，**已由使用者 2026-11-19 確認，`phase-1.md:199` 的待決事項結案**（§1.14） |
| P3 spec 的 §8 項目 | 納入 C1、C2、C3、C6–C13、N1–N3、N6；延後或不處理 C4、C5、C14、N4、N5、N7–N13（附錄 B） |

## 1. 問題與修正

每項格式：現象 → 根因（行號）→ 紅燈 evidence → 修正 → 綠燈。紅燈 evidence 都在 `docs/reports/evidence/phase-3/`（以下省略目錄）；「紅燈 commit」是總覽 repo 的 hash，「修正」是 backend／frontend 的 hash。evidence 內的 token 已遮蔽。

### 1.1 PATCH `/info` 部分更新回 500（P3 spec §8.1 C1）

**現象**：只送一個欄位（只送 `name`、或只送 `preference`）的 PATCH 回 500「伺服器錯誤」。
**根因**：`middlewares/userProfile/index.js:29–30` 對 `undefined` 的 `preference` 呼叫 `.map`；`controllers/userProfile.js:54–57` 一律 `SET name = $1`，沒送 `name` 時也會被寫入。
**紅燈**：[task-2-red-patch-info.txt](evidence/phase-3/task-2-red-patch-info.txt)（總覽 `930d7f4`，2 failed 81 deselected）：即 P2 留下的兩個 strict xfail 改成一般測試後轉紅。
**修正**：backend `9faa9c8`：middleware 只在有 `preference` 時轉換；controller 用 `COALESCE` 只更新有送的欄位。
**綠燈**：兩個測試通過；xfail 標記在紅燈 commit `930d7f4`（`tests/test_member_auth.py`）就已移除，使測試以一般失敗呈現；全套 0 xfailed（§3.3）。

### 1.2 `delete_tourProduct` 沒有 release 連線（P3 spec §8.1 C2）

**現象**：重複呼叫後台刪除商品會耗盡 pool（max 10），之後所有需要 DB 的請求（P2 之後每個帶 token 的請求都要查 DB）都會卡住。
**根因**：`controllers/product.js:1360` `pool.connect()` 沒有對應的 `release()`。
**紅燈**：[task-2-red-delete-release.txt](evidence/phase-3/task-2-red-delete-release.txt)（總覽 `930d7f4`，1 failed 7 deselected）。這個紅燈會耗盡 pool，依計畫單獨執行、存證後 `docker compose restart backend`；只刪 fixture 建的行程。
**修正**：backend `9faa9c8`：`try/finally release`。
**綠燈**：測試通過。（屬後台 P6 的功能，但因會拖垮 P3 的全部會員 API 而提前修，見 P3 spec §8.1 C2。）

### 1.3 搜尋分頁不穩（P3 spec §5.1、§8.2 N1）

**現象**（已實測）：`limit=10` 時「首爾咖啡文青小旅行」同時出現在第 1、3 頁，另一個行程永遠拿不到；`limit=50` 一次取回則是 22 筆、不重複。
**根因**：`controllers/product.js:98` 起的搜尋 `ORDER BY 旅遊開始日期`／`價錢` 沒有次要排序鍵；seed 有 16 筆日期為 NULL、同值，PostgreSQL 對同值列的順序不保證穩定。
**紅燈**：[task-3-red.txt](evidence/phase-3/task-3-red.txt)（總覽 `aace4c2`，3 failed 8 passed）；審查後強化分辨力（同值資料、違規一次列出）見 [task-3-red-fix1.txt](evidence/phase-3/task-3-red-fix1.txt)（總覽 `2d375e9`，4 failed 7 passed）。
**修正**：backend `1edf1b7`：`ORDER BY ${sortBy} ${order}, "旅遊編號" ASC`。
**綠燈**：搜尋分頁走完每個上架行程恰一次（API 層與 `e2e/test_product_flow.py` 的搜尋頁）。

### 1.4 搜尋 `duration` 不生效（P3 spec §5.1、§8.2 N2）

**現象**（已實測）：`duration=5` 回 10 筆（沒有過濾）。
**根因**：`buildDynamicTourSQL` 用 `typeof duration === 'number'`，但 query 參數是字串。
**紅燈**：同 §1.3 的 `task-3-red.txt`（總覽 `aace4c2`）；`duration` 測試改走 `_all_pages` 以避免空轉。
**修正**：backend `1edf1b7`：條件改為 `duration !== undefined && duration !== ''`，參數 `Number(duration)`。
**綠燈**：搜尋結果的天數集合與 DB 相符。

### 1.5 首頁促銷：露出已下架行程、沒有期間條件（P3 spec §5.1、§8.2 N6；契約 #7、#9）

**現象**：`GET /api/v1/user/home/search/products?item=promotion`：未登入版直接查 `tour_base`，會列出已下架行程；兩個版本都沒有「促銷期間內」條件。
**根因**：`controllers/home.js:31–46`。
**紅燈**：[task-3-red.txt](evidence/phase-3/task-3-red.txt)（總覽 `aace4c2`）；測試自建促銷（`now() ± 1 day`），不依賴 seed 的有效期。未單獨證明「會員路徑」的紅燈，列入附錄 B（ledger：Task 3 minor）。
**修正**：backend `1edf1b7`：兩個查詢都加 `now() BETWEEN 促銷開始日期 AND 促銷結束日期`；未登入版加 `上下架狀態 = 1`；排序加次要鍵 `旅遊編號 ASC`。
**綠燈**：促銷只列上架且期間內的行程。首頁 E2E（§1.10）證明畫面與 API 一致。

### 1.6 詳情：已下架與無子表資料回 500、food 空項、隱藏玩法沒有 `title`（P3 spec §5.1、§8.1 C3、§8.2 N3；契約 §4.2、#34）

**現象**（已實測）：
1. 已下架行程（清邁自然旅宿體驗 `status=2`）的詳情回 500；只有 `tour_hotel`／`tour_restaurant` 沒有資料的行程也回 500。
2. food 詳情的 `menu[]` 與 `opening[]` 共用 `rows`，各自含 `name: null`／`week: null` 的空項。
3. `GET /:tour_id/hidden-shares` 的回應沒有 `title`。

**根因**：(1) `controllers/product.js:209` 對 `rows[0]` 讀欄位時 `rows` 為空，TypeError。(2) 契約 #34 選 B，「完整修正需改 controller」。(3) `:574` 寫 `row.type`。
**紅燈**：[task-4-red.txt](evidence/phase-3/task-4-red.txt)（總覽 `1676cb4`，5 failed 11 passed）；審查後 food 測試改自建資料並補空餐廳、spot 無明細案例，[task-4-red-fix1.txt](evidence/phase-3/task-4-red-fix1.txt)（總覽 `19a2fc7`，2 failed 3 passed）。
**修正**：backend `1c077a4`：`tourRepo.rowCount === 0`（不存在或非上架）→ 404 `查無此旅遊項目`；`tourDetailsRepo.rowCount === 0` → 404，兩者都在計算 `preferences`（`:208`）之前；`menu` 只取 `菜單名稱 IS NOT NULL`、`opening` 只取 `營業星期 IS NOT NULL`；`row.type` 改 `row.title`。
**綠燈**：四種 item 的詳情、下架、空餐廳、隱藏玩法 `title` 都通過。

### 1.7 V4 migration：一人一行程一則評論、評分 1–5（P3 spec §3.3、§4.1）

**現象**：`review` 沒有任何約束：同一會員可對同一行程寫多則；`rating INT NOT NULL DEFAULT 1` 沒有範圍。
**根因**：V1 的設計（`review` 表）；P2 的 `user_email_lower_key` 是同一類問題（middleware 先查不夠，併發會寫入兩則）。
**紅燈**：[task-5-red.txt](evidence/phase-3/task-5-red.txt)（總覽 `1fe431b`，6 failed 9 passed；計畫寫 5 個，實際 6 個，依 PF1 以實跑為準）。
**修正**：backend `9b710cd`：`migrations/V4__p3_review_constraints.sql`（部分唯一索引 `review_user_tour_key ON review (user_id, tour_id) WHERE tour_id IS NOT NULL`、`CHECK review_rating_range`）；契約 `docs/db-contract.md` 新增 §6「P3 表格約束（V4）」（總覽 `7dc6ef1`）。
**綠燈**：`tests/test_migrations.py`（`test_flyway_applied_v1_to_v4` 等）通過；網站好評（`tour_id IS NULL`）不受唯一限制；審查後補強約束名稱與對照組（總覽 `c6bd5af`）。
**seed 相容（套用前已查）**：`review` 13 列 `rating` 介於 3–5，且沒有重複的 (user_id, tour_id)。

### 1.8 新功能：購買資格查詢與寫評論（P3 spec §5.2 (a)(b)）

**現象**：總 spec §0 要求「只有購買過的會員能評論」，原本任何登入者都沒有寫入評論的 API。
**實作**：`GET /:tour_id/eligibility` → `{ can_write, has_reviewed }`；`POST /:tour_id/reviews`。檢查順序固定（auth 401 → `authRole('User')` 403 → `tour_id` 400 → body 400 → 行程不存在或下架 404 → 未購買 403 → 已評論 409 → INSERT 撞 `review_user_tour_key`（`23505`）409）。購買判斷集中在 `src/utils/purchase.js` 的 `hasPurchased`（一條 `EXISTS`，Ruling R1，§2.4）。
**紅燈**：[task-6-red.txt](evidence/phase-3/task-6-red.txt)（總覽 `a984860`，38 failed）；審查後補 23505 確定性測試、`orders`／`order_item` 狀態分離、eligibility 的 400／404，[task-6-red-fix1.txt](evidence/phase-3/task-6-red-fix1.txt)（總覽 `bd527c6`，3 failed 42 deselected）。
**修正**：backend `8295f91`（`routes/product.js`、`middlewares/product/index.js`、`controllers/product.js`、`utils/Validator/product_Validator.js`、`utils/purchase.js`）。
**綠燈**：未付款狀態（-1、0、2、3、4）都不能寫；別人的已付款訂單、別的行程的訂單不算；admin 403；同時送出 5 則評論只成功 1 則、其餘 409、沒有 500。

### 1.9 新功能：分享隱藏玩法（P3 spec §5.2 (c)）

**現象**：同 §1.8，隱藏玩法沒有寫入 API；且 `url` 若不限制，`javascript:` 之類連結會被存下並在前端變成 XSS 入口。
**實作**：`POST /:tour_id/hidden-shares`；`url` 只收 http／https、`≤255` 字、先 `trim` 再驗證；不檢查重複（P3 spec §4.1，玩法可多則）。
**紅燈**：[task-7-red.txt](evidence/phase-3/task-7-red.txt)（總覽 `8cf7ea1`，36 failed）；審查指出 `url` 缺 `.trim()`（計畫 `:326` 漏寫，spec §5.3 有寫），[task-7-red-trim.txt](evidence/phase-3/task-7-red-trim.txt)（總覽 `4db5784`，1 failed 81 deselected）。
**修正**：backend `fa7fca1`；`url` trim `fe21a62`；`05562d3` 撤回 `fe21a62` 範圍外放寬管理端驗證的 3 處 trim（只保留隱藏玩法的一行）。
**綠燈**：`javascript:`／`data:`／`ftp:`／空字串 400；HTML 原樣保存；`share_url` NULL／有值。

### 1.10 前端：401 統一提示與成功提示改 `timer`（P3 spec §6.6、§8.1 C6、C7）

**現象**：帶過期 token 的請求回 401 後，各頁各自處理（或白屏）；成功提示用 `setTimeout(() => { Swal.close(); router.push(…) }, 3000)`，可能誤關別的彈窗。
**根因**：`utils/api.js:53、:104、:155、:228`（`setTimeout`）；無統一 401 處理。
**紅燈**：[task-8-red.txt](evidence/phase-3/task-8-red.txt)（總覽 `0a8e6f9`，3 failed 22 deselected）；審查後參數化三個入口並移除時間競爭，[task-8-red-fix1.txt](evidence/phase-3/task-8-red-fix1.txt)（總覽 `eedd361`，1 failed 2 passed 24 deselected；第 2 輪 `3fa688a` 以舊實作 3/3 紅、新實作 3/3 綠驗證）。
**修正**：frontend `7eb1dcd`：axios interceptor 對「有帶 `Authorization` 的 401」一律 `logout()`、標 `sessionExpired`、顯示「登入已過期／請重新登入」（`timer: 2000`）；會員 API 另導 `/admin/login`；公開讀取不導頁，由呼叫端不帶 token 重試；資格查詢 401 不導頁。成功提示改 `Swal.fire({ timer }).then(() => router.push(…))`。
**綠燈**：P2 的註冊、登入、Google 登入、重設密碼流程以全套 E2E 回歸；`e2e/test_member_flow.py` 綠。

### 1.11 前端：詳情頁、移除假行程路由（P3 spec §6.3）

**現象**：`tourPage.vue` 是空殼（`data() {}` 回 undefined、呼叫不存在的 `fetchUserInfo`）；`#/tour`、`#/tourfake`、`#/tourfakeUSA` 是假頁；`searchPage.vue:257` 連到 `/tourfakeUSA`。
**紅燈**：[task-9-red.txt](evidence/phase-3/task-9-red.txt)（總覽 `b1f7165`，13 failed）；審查指出 `load()` 把 500／網路錯誤也顯示「查無此行程」，[task-9-red-fix1.txt](evidence/phase-3/task-9-red-fix1.txt)（總覽 `19f433c`，1 failed 13 deselected）。
**修正**：frontend `afd98a5`：新路由 `#/tour/:tour_id`，依 `item` 顯示對應內容；訂購按鈕「加入購物車（即將開放）」停用；404／400 顯示「查無此行程」。`22053e1`（`refactor:`，獨立 commit，無紅燈，以全套 E2E 綠燈為證）：刪除 `tourPageFake.vue`、`tourFakeUSA.vue` 與只被它們引用的 10 張圖。`d4f5568`：非 400／404 顯示載入失敗。
**綠燈**：詳情四種 item、下架行程、過期 token 重試、單一 header 的 E2E 通過。

### 1.12 前端：首頁雙 header、購物專區接 API（P3 spec §6.2、§8.1 C8、§8.2 N6）

**現象**（已實測）：首頁 `.header` 2 個、`.footer` 2 個（HomeView 自帶的 `.nav` 與 `<FooterComponent />`）；`HomeView.vue:350` 的 `productList` 寫死 3 筆。
**紅燈**：[task-10-red.txt](evidence/phase-3/task-10-red.txt)（總覽 `7da7141`，5 failed 15 deselected）。
**修正**：frontend `f9ac92a`：移除 HomeView 自帶的 `.nav` 與 footer；購物專區依 `type`／`item` 呼叫 API，每頁 4 筆；點商品進 `#/tour/<旅遊編號>`。`isSticky`／`handleScroll` 成為無作用程式碼，依 spec 不動（不順手重構）。
**綠燈**：首頁單一 header、清單與 API 一致、分頁、進詳情、過期 token。

### 1.13 前端：搜尋頁接 API、header 搜尋框（P3 spec §6.4）

**現象**（已實測）：搜尋頁的清單是寫死的 `allItems`；header 搜尋框按 Enter 沒有反應（`HeaderComponent.vue:12`、`:104` 的 `@submit.prevent="search"` 沒有對應的 `search`）。
**紅燈**：[task-11-red.txt](evidence/phase-3/task-11-red.txt)（總覽 `4f9f787`，7 failed 20 deselected）；審查指出 `_api_titles` 對空回應（總數為 6 的倍數時沒有 `data` 鍵）會 KeyError，[task-11-red-fix1.txt](evidence/phase-3/task-11-red-fix1.txt)（總覽 `474b6d5`，1 failed 1 passed 26 deselected）。
**修正**：frontend `84e36a9`：清單、篩選（天數、金額、日期、關鍵字）、排序、「上一頁／第 N 頁／下一頁」都走 API；移除國家、地區下拉（§附錄 B：N5）；補 `HeaderComponent.vue` 的 `search()`；卡片連 `#/tour/<旅遊編號>`。
**綠燈**：搜尋頁 E2E 通過（API 清單一致、分頁不重複、header 關鍵字、金額篩選排序、查無結果、卡片連詳情）。

### 1.14 評論與隱藏玩法的前端、購買數裁決與對 P4 的依賴（P3 spec §6.5、§2.2、§2.4）

**評論與隱藏玩法前端**
**紅燈**：[task-12-red.txt](evidence/phase-3/task-12-red.txt)（總覽 `79df5e4`，8 failed）；審查指出資格查回前就渲染預設 `can_write:false`（閃爍，且測試無分辨力），[task-12-red-fix1.txt](evidence/phase-3/task-12-red-fix1.txt)（總覽 `9222e0f`，3 failed 1 passed）；之後 `fada827` 穩定資格延遲測試並補「載入更多停用」的回歸測試（既有行為，一開始即綠）。
**修正**：frontend `179eb58`（評論與隱藏玩法的列表、載入更多、表單與四種狀態）、`a443460`（資格載入完成才顯示購買提示與表單、空白連結不送、409 重讀資格、載入更多進行中停用）。
**綠燈**：主線 E2E（購買過的會員寫評論、分享玩法，送出後立刻出現）；未登入／未購買／admin 的提示；XSS 以文字顯示、不執行；409 切換為「已評論過」。

**購買數裁決已由使用者確認、`phase-1.md:199` 結案**：使用者於 2026-11-19 同意「購買數」＝ 該行程 `order_item.payment_status = 1` 的**列數**，不乘 `quantity`（沿用契約 `docs/db-contract.md:130` 的裁決）。P1 報告 `docs/reports/phase-1.md:199` 的待決事項（「P3 商品開工前要變成使用者明確決定」）由此結案；契約 `:557`、`:1747` 兩處改為「使用者 2026-11-19 確認」（總覽 `7dc6ef1`）。

**對 P4 的依賴（`order_item.payment_status`）**：現行付款流程到不了「已付款」：`controllers/newebpay.js:82,213` 對 `order_item` 寫不存在的 `payment` 欄位而 ROLLBACK（契約 §4.2）；`:203–206` 只更新 `orders.payment_status`。P3 的資格判斷看 `order_item.payment_status = 1`，所以 **P4 必須在付款成功時把 `order_item.payment_status` 設成 1**，否則真實買家永遠不能評論（P3 spec §2.4、§8.2 N10）。

### 1.15 測試、CI 與文件項目（P3 spec §8.1 C9–C14）

| 項目 | 處理 | commit | evidence |
|---|---|---|---|
| C9 殘留清除：測試前綴的會員與 `p3-` 行程殘留讓 `test_seed.py` 變紅 | session 開頭 `purge_leftovers`；只刪測試前綴會員與 `p3-` 行程，有測試證明不會刪到 seed 與非測試帳號；`TEST_EMAIL_PREFIXES` 另加 `mock.`（ledger Ruling T1-I1） | 紅燈 `2d2afe9`、綠燈 `9049f8a`；回歸 `78db6ac`、`99af32c`、`3e12b2d` | [task-1-red.txt](evidence/phase-3/task-1-red.txt)（4 failed 1 passed 3 errors） |
| C10 `test_admin_product_empty_result` 斷言收緊為 `"data" not in r.json()` | test-only，沒有紅燈 | 總覽 `0adc76b` | — |
| C11 `requires-python` 加上限 | `>=3.10,<3.14`；`uv lock` 並 commit `uv.lock`（`ci.sh` 用 `--frozen`）；`psycopg-binary` 3.2.3 沒有 cp314 wheel | 總覽 `63af557` | 設定類，以 CI 綠燈為證（ledger：CI run `44448611062` rerun green，CPython 3.13.18） |
| C12 鎖定 uv 版本 | `setup-uv@v10.3.3` 的 `version: "0.13.9"`；不用 `[tool.uv] required-version`（本機 uv 0.11.26 會讓每個 `uv run` 失敗） | 總覽 `63af557` | 同上：uv 0.13.9、341 passed 2 xfailed（Task 1 當時） |
| C13 P2 報告補句 | §4.1 末尾補「總覽 repo 的 `phase-2` tag 本身沒有 `.python-version`（`e1901f9` 才加入），要重現 P2 的測試結果請用 `main`。」 | 總覽 `76a7f82` | — |
| C14 P1 遺留（`R__views_functions.sql` DROP 清單寫死、`tests/db_contract.py` 不比對契約文字） | **不處理，重申**：P3 沒有改這兩個檔案，見附錄 B 的指令與輸出 | — | 附錄 B.2 |
| （計畫外）CI job 加 `timeout-minutes: 30` | 見 §3.3 | 總覽 `d73a78d` | — |

## 2. Vibe coding 工作流

### 2.1 使用的 skill

**使用的 skill 與關鍵 prompt：未查證**（ledger 沒有逐項紀錄，請使用者在審閱時補）。以下流程可由 ledger 與 git log 確認的流程：P3 spec 經三輪 reviewer-opus 審查（commits `baf5f9b` → `9cd37b7` → `5480908` → `ac8cbdc`）；計畫完成後先做 pre-flight scan（掃描 540 行計畫對照 spec，找出 9 項 Findings，裁決成 Ruling PF1–PF9）；之後逐 Task 派 implementer 實作、reviewer 審查，結果記在 `.superpowers/sdd/2026-11-19-p3-product/progress.md`（以下稱 ledger）。

### 2.2 使用者的決定

- 2026-11-19：確認開工；審查照 `~/.claude/CLAUDE.md` 的門檻：**Task 1、5、6、8、13 雙審（reviewer-opus＋reviewer-fable 平行），其餘單審 reviewer-opus**（P2 是使用者選擇每個 Task 都雙審，P3 spec §12 Q1 回到門檻）。
- 2026-11-19：「購買數」＝ `order_item` 列數，不乘 `quantity`（Task 5 雙審時以 AskUserQuestion 確認）。
- 2026-11-19：Task 1 完成後經同意 push 總覽 `phase-3` 跑 CI（覆蓋計畫 Constraint 2「Task 13 前不 push」，Ruling PF4）。
- 2026-11-19：Task 13 Step 1 前由使用者自己執行 `docker compose down -v`（乾淨 volume）。

### 2.3 Fable vs Opus review 對照

雙審的 Task（1、5、6、8）兩個 reviewer 平行派出、互不看結果，由主對話比對：

| Task | reviewer-opus | reviewer-fable | 比對 |
|---|---|---|---|
| 1 fixture／殘留清除／CI 鎖版 | ✅，無 Critical／Important | ✅，Important I1–I3 | opus Minor 4 ≈ fable I2（purge 對照組）；兩者都建議以 `pythonpath` 取代 `sys.path` hack。fable 另抓出 `mock.` 前綴（test_oauth_spike 的 `mock.user@example.com`）會殘留（I1） |
| 5 V4 與契約 | ❌ C1（措辭）＋ M1–M4 | ❌ C1 ＋ I1–I3 | 一致：C1（「購買數」裁決的措辭）；約束名稱與對照組的分辨力，fable 列 Important、opus 列 Minor。C1 由使用者確認購買數而解決 |
| 6 資格與寫評論 API | spec ✅、安全無漏洞、無 Critical | spec ✅、安全無漏洞、無 Critical | 共同 Important：23505 確定性測試、`payment_status` 兩表分辨；fable 另列 I3（eligibility 缺 400／下架 404），opus 列 Minor |
| 8 前端 401／timer | spec ✅、無 Critical | spec ✅、無 Critical | fable I1–I3（guard 覆蓋、401 提示內容、時間競爭）≈ opus Minor 1–3 |
| 13／整支分支（最終審查） | 0 Critical、2 Important（I1 搜尋日期與天數互斥且 400 顯示「載入失敗」、I2 refs `phase-3` 分支／tag 歧義）、8 Minor | 0 Critical、2 Important（I1 過期 token E2E 斷言順序、I2 報告誤稱有 admin E2E）、12 Minor | 四個 Important 互不重疊，全數處理（I1 經使用者裁決改後端為「天數 ≤ 區間涵蓋天數」並讓前端顯示 400 訊息；I2 已合併並打 tag；三個 repo 的 `phase-3` 分支尚未刪除，刪除為下一步，遠端刪除逐次詢問）。opus M2（詳情頁不 watch `tour_id`）被 fable 以 `App.vue` 的 `:key="$route.fullPath"` 反證，不修。之後共 3 輪修正與複審：第 1 輪複審 opus 新增 1 個 Important（`end_date` 以 00:00 比對，seed 行程結束於 23:59:59，剛好塞滿區間查不到；opus 以 curl 實測成立，fable 未查 seed）、fable 0 Important，使用者裁決 `end_date` 改含當天；第 2 輪複審 opus 1 項必修（本節仍寫待補）、fable 3 個 Important（寬區間缺區間內斷言、本稿尚缺與本節矛盾、`wait_for_timeout` 無鑑別力）；第 3 輪（只改測試與文件）複審只派 reviewer-opus（見附錄 C）。詳見 ledger `progress.md` 的 Final review、Fix re-review、Fix2 re-review 各行 |

單審的 Task（2、3、4、7、9、10、11、12）共抓出的 Important：Task 3 價格排序測試無分辨力；Task 7 `url` 缺 `.trim()`（spec ✅ 但計畫漏寫）；Task 9 `load()` 把 500 也顯示查無；Task 11 `_api_titles` 空回應 KeyError；Task 12 資格載入前就渲染預設狀態。皆已在 fix round 修好（詳見 ledger）。

### 2.4 Ruling 表

| # | Ruling | 出處 |
|---|---|---|
| R1 | 「購買過」＝ `EXISTS (order_item JOIN orders WHERE o.user_id=U AND oi.tour_id=T AND oi.payment_status=1)`；不看 `payment` 表；已退款（3）不算；不要求行程已結束；一人一行程一則評論；只有 `User` 角色能寫 | P3 spec §4.2 |
| S1 | 「購買過」判斷放在後端 `utils/purchase.js`（選 A），不放 DB function（B）、不用 trigger（C） | P3 spec §3.1 |
| S2 | 前端用 `GET …/eligibility`（選 B），而非登入即顯示表單或在詳情回應加旗標 | P3 spec §3.2 |
| S3 | 重複評論：middleware 先查（友善訊息）＋部分唯一索引當最後防線（`23505` → 409） | P3 spec §3.3 |
| S4 | `hidden_play` 不加唯一約束；後端原樣保存內容、前端只用文字插值、`url` 限 http(s) | P3 spec §4.1、§5.4 |
| S5 | 下架行程不能寫入；評論與玩法讀取對下架行程維持 200 | P3 spec §5.2、§5.1 |
| S6 | 401 統一處理：會員 API 導登入頁、公開讀取不帶 token 重試、資格查詢不導頁 | P3 spec §6.6 |
| S7 | 首頁雙 header：移除 HomeView 自帶 `.nav` 與 footer，保留 layout 的 | P3 spec §6.2 |
| PF1 | Task 5 紅燈數以實跑為準（計畫寫 5，實際 6） | ledger |
| PF2 | Task 12 驗紅用明確的新測試 node id，不用 `-k expired_token`（會選到已綠的測試） | ledger |
| PF3 | Task 3 允許修改 `tests/test_api_smoke.py`（Step 1 明文要求，Files 漏列） | ledger |
| PF4 | Constraint 2「Task 13 前不 push」被使用者決定覆蓋 | ledger |
| PF5 | 同一 Task 多段紅燈用 `task-N-red-<主題>.txt` | ledger |
| PF6 | 自建促銷 helper 只寫一份（`tests/conftest.py`／`dbfactory`）；`EXPIRED` 重用既有定義 | ledger |
| PF7 | 弱斷言一律補非空前置斷言；Task 9 紅燈分辨力由實際失敗訊息證明 | ledger |
| PF8 | `duration` 以 spec 為準；Task 2 DELETE 帶 admin header；Task 9 刪假頁面為 refactor、不需紅燈 | ledger |
| T1-I1 | `TEST_EMAIL_PREFIXES` 加 `mock.`（覆蓋 brief 的「值不得更改」） | ledger（fable I1） |
| T4-I1 | food 詳情測試自建資料，不讀 seed 第一個 food | ledger |
| T6 | 允許 Task 6 修改 `make_order`（加可選參數分開 `orders`／`order_item` 狀態） | ledger |
| T7-I1 | `url` 依 spec 補 `.trim()`，計畫 `:326` 不改（spec 為權威） | ledger |
| T8-PF6 | 三處一行 guard 接受，不抽函式 | ledger |
| 複審簡化 | Task 1 第 2 輪只派提出該項的 reviewer-fable；Task 7 第 2 輪（純撤回）、Task 8 第 2 輪、Task 11 修正由主對話核對 diff 代替 reviewer | ledger |
| CI-timeout | CI 加 `timeout-minutes: 30`（§3.3） | ledger；本 Task |

### 2.5 AI 出錯／人介入紀錄

- 計畫與 spec 不一致（pre-flight 抓出 9 項 Findings，裁決成 PF1–PF9）：例如 Task 3 漏列要改的檔案、Task 2 兩段紅燈共用一個 evidence 檔名、Task 12 的 `-k` 選到兩個已綠的測試。
- 計畫漏寫 `url` `.trim()`（spec §5.3 有寫）：Task 7 審查抓到；而 implementer 修正時又在 `fe21a62` 範圍外放寬了管理端驗證的 3 處 trim，第 2 輪審查抓到並撤回（`05562d3`）。
- 主對話誤取消 CI：run `44448611062` 被誤判為卡死而取消（實際是 apt 鏡像下載只有約 84.8 kB/s、拖了約 6 分鐘），rerun 後綠燈；教訓是加上 `timeout-minutes`（§3.3）。
- 測試自己會空轉：多個審查抓到「空結果時斷言空轉」「紅燈期沒有分辨力」的測試，修正方式是補非空前置斷言、以舊實作驗證紅燈（Ruling PF7，Task 3、8、10、11、12）。

## 3. 測試方法

### 3.1 測試分層

照總 spec §4.2 的四層，P3 的新增與重點：

| 層 | 內容 | 主要檔案 |
|---|---|---|
| API 契約 | 三支新 API 的正常、每個驗證錯誤、401／403；既有讀取 API 的修正；回應鍵名對齊 GET | `tests/test_product_write.py`（82）、`tests/test_product_read.py`（23）、`tests/test_api_smoke.py`（36）、`tests/test_product_routes.py`（8） |
| 安全 | 未付款狀態（-1、0、2、3、4）不能寫；別人的、別行程的已付款訂單不算；admin 403；非 http(s) 網址 400；HTML 原樣保存（API）且在頁面以文字顯示不執行（E2E）；併發 5 則評論只成功 1 則 | `tests/test_product_write.py`、`e2e/test_product_flow.py` |
| DB 狀態 | `review.type = tour.item`、內容已 trim、`share_url` NULL／有值；V4 索引與 CHECK（含網站好評不受限）；seed 唯讀冒煙 | `tests/test_migrations.py`（15）、`tests/test_db_contract.py`（45）、`tests/test_product_write.py` |
| E2E | 首頁單一 header 與清單；搜尋分頁走完每個上架行程恰一次；header 關鍵字；詳情四種 item；未登入／未購買／admin 提示；XSS；過期 token；假頁面路由 404；主線 | `e2e/test_product_flow.py`（43）、`e2e/test_member_flow.py`（27） |
| 測試基礎 | `make_tour`、`make_order`、`purge_leftovers`、`_cleanup_all` | `tests/conftest.py`、`tests/test_infra.py`（12）、`e2e/conftest.py` |

### 3.2 值得一看的技巧

- **每個測試自建資料、結束清除**：`make_tour`（`p3-` 前綴行程）、`make_order`（可分開指定 `orders`／`order_item` 的 `payment_status`），不依賴 seed 的可變狀態；seed 帳號只能讀。
- **session 開頭的殘留清除**：`tests/test_seed.py` 的 `SEED_COUNTS` 做 exact count，測試前綴殘留會讓它變紅；清除函式只刪測試前綴會員與 `p3-` 行程，並有對照組測試證明不會刪到 seed。
- **23505 確定性測試**：不靠真的併發，而是讓 middleware 的先查被繞過、直接撞索引，證明 DB 最後防線有效；另有 5 個併發請求的測試。
- **紅燈分辨力**：先以舊實作驗證測試會紅（Task 8 以舊實作 3/3 紅、新實作 3/3 綠），並補非空前置斷言避免空轉。
- **E2E 的時間競爭**：過期 token 的 2 秒提示在斷言前可能已消失，所以先斷言提示再斷言標題（`ddf119f`）。

### 3.3 測試數量與 CI 結果

**本機 `scripts/ci.sh`，兩次都在 `phase-3` 分支（總覽 `d73a78d`、backend `05562d3`、frontend `a443460`）、docker compose 服務由 `ci.sh` 自己啟動**：

| 次數 | volume | exit code | pytest 結果 | pytest 計時 | `ci.sh` 全程 |
|---|---|---|---|---|---|
| 1 | 乾淨（使用者先執行 `docker compose down -v`） | 0 | **499 passed**，xfailed 0、failed 0、error 0 | 127.92s（0:02:07） | 164s |
| 2 | 保留（沒有清 volume） | 0 | **499 passed**，xfailed 0、failed 0、error 0 | 128.06s（0:02:08） | 132s |

- 兩次輸出以 `grep -ci xfail` 檢查，xfail 字樣為 0。
- 329 passed、2 xfailed（P2）→ 499 passed、0 xfailed。
- 每個檔案的通過數（第 2 次）：`tests/` 下 `test_member_auth.py` 83、`test_product_write.py` 82、`test_db_contract.py` 45、`test_api_smoke.py` 36、`test_seed.py` 29、`test_views_b.py` 24、`test_google_login.py` 23、`test_views_a.py` 22、`test_product_read.py` 19（第 2 輪修正後 23）、`test_migrations.py` 15、`test_views_c.py` 13、`test_infra.py` 12、`test_product_routes.py` 8、`test_build_seed.py` 7、`test_frontend.py` 5、`test_storage.py` 3、`test_oauth_spike.py` 2、`test_async_errors.py`／`test_health.py`／`test_mail.py` 各 1；`e2e/` 下 `test_product_flow.py` 41、`test_member_flow.py` 27。
- **GitHub Actions**：Task 1 當時的 run `44448611062`（rerun）為綠燈，341 passed 2 xfailed，uv 0.13.9、CPython 3.13.18。
- **`phase-3` 分支的 GitHub Actions run `44496092927`**：綠燈，505 passed（pytest 115.99s），整個 run 從 09:24:17Z 到 09:33:27Z，約 9m10s（含 `docker compose up --build`、`playwright install --with-deps`）。
- **合併後的 GitHub Actions run**（2026-11-22 push 主分支與 tag 後觸發，皆綠燈、505 passed）：`main` 的 run `45008564851`（總耗時 3m34s，pytest 114.82s）；`phase-3` tag 的 run `45008564712`（總耗時 3m38s）。
- **`timeout-minutes: 30` 的理由**：job 預設逾時是 360 分鐘，真卡死時會空轉 6 小時。實測佐證：本機 `ci.sh` 全程約 2–3 分鐘；GitHub runner 上 run `44496092927` 總耗時約 9m10s（apt 鏡像慢時 `playwright install` 還會多出數分鐘）。30 分鐘約是實測耗時的 3 倍多，能容納鏡像變慢，又能擋住真卡死。若之後正常耗時逼近 20 分鐘，應改值而不是單純拉高。

## 4. 操作指南

### 4.1 切到這個版本並啟動

```bash
git clone https://github.com/nohungry/tripeasy.git && cd tripeasy
git clone -b "$(grep BACKEND_REF refs.env | cut -d= -f2)" https://github.com/nohungry/tripeasy-backend.git backend
git clone -b "$(grep FRONTEND_REF refs.env | cut -d= -f2)" https://github.com/nohungry/tripeasy-frontend.git frontend
scripts/ci.sh        # 啟動全部服務並跑測試
```

需要 Docker（含 Compose v2）與 [uv](https://docs.astral.sh/uv/)；服務網址同 `docs/reports/phase-0.md` §4.1。目前 `refs.env` 是 `BACKEND_REF=phase-3`、`FRONTEND_REF=phase-3`；**合併與打 tag 之後（Step 6）它指的才是 tag**，目前指的是分支。一次只能跑一個 pytest／`ci.sh`：session 開頭會 purge 測試資料，並行會互刪。

### 4.2 測試帳號

seed 帳號（密碼 `Tripeasy123`）：`alice@example.com`（`User`）、`bob@example.com`（`admin`）、`carol@example.com`（`User`）。**seed 帳號只能讀，不要用它們送出評論或玩法**，否則 `tests/test_seed.py` 的 `SEED_COUNTS`（`review` 13、`hidden_play` 6）會紅。

### 4.3 手動實測

> **未實測說明**：使用者於 2026-11-22 選擇略過本節手動實測、直接合併；先前未實跑的 seed 帳號 POST 403 curl 因此仍未實測。

前提：以下指令都在總覽 repo 根目錄（`/home/nohungry/project/tripeasy`，`docker-compose.yml` 與 `pyproject.toml` 所在處）執行，服務已啟動（`docker compose up -d`）。

**唯讀示範（不按送出）**

1. alice 開「義大利深度文化之旅」：她只有一筆 `payment_status = -1` 的訂單，資格查詢 `GET …/eligibility` 回 **200** `{ can_write: false, has_reviewed: false }`，畫面顯示「購買過此行程的會員才能評論與分享隱藏玩法」，沒有表單（**未購買**的 403 只會出現在 POST，見下方 curl）。
2. alice 開「北海道雪景 5 日深度遊」：顯示「你已評論過此行程」，玩法表單仍出現，但不要送出。
3. bob（admin）登入後開任一詳情：資格查詢回 403，前端照樣顯示 (1) 的提示（有 E2E `test_admin_sees_purchase_hint_without_forms` 涵蓋：403、無表單、不導頁、無 `pageerror`）。
4. **搜尋的日期與天數**（日期會隨載入日平移，先用下面的 SQL 查出北海道 5 日的起訖日，不要照抄範例）：

```bash
docker compose exec -T postgres sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -At' <<'SQL'
select tour_start_date::date, tour_end_date::date, days from tour where title = '北海道雪景 5 日深度遊';
SQL
```

開 `#/search`，「旅遊日期」填查到的起日與訖日（含當天，訖日 23:59:59 結束的行程也算），「旅遊天數」選 5日，按「搜尋」：清單要有「北海道雪景 5 日深度遊」。把訖日改成前一天（區間只剩 4 天）再搜：畫面顯示後端訊息「「duration」不可大於「start_date」到「end_date」涵蓋的天數（目前區間共 4 天）」，**不是**「載入失敗，請稍後再試」。起日填得比訖日晚：顯示「「start_date」不可大於「end_date」」。先把日期改回原區間，再把最小金額填得比最大金額大：顯示「「min_price」不可大於「max_price」」。（以上訊息已以 curl 對照 API 實測，狀態碼 400。）

**403 的 curl 示範**（token 一律用 login API 取得，不從 localStorage 拿；這兩個請求都在驗證或資格階段被擋，**不會新增任何列**（login 只會重設 `login_attempts`／`locked_datetime`／`login_method`），`review` 仍是 13 筆）：

```bash
TOUR=$(docker compose exec -T postgres sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -At' <<'SQL'
select tour_id from tour where title = '義大利深度文化之旅';
SQL
)
login() { curl -s -X POST http://localhost:3000/api/v1/auth/userinfo/login/email \
  -H 'Content-Type: application/json' -d "{\"email\":\"$1\",\"password\":\"Tripeasy123\"}" \
  | uv run python -c 'import sys,json; print(json.load(sys.stdin)["data"]["token"])'; }
# (a) alice 沒買過義大利 → 403 購買過此行程的會員才能評論
curl -s -w '\n%{http_code}\n' -X POST "http://localhost:3000/api/v1/user/product/search/$TOUR/reviews" \
  -H "Authorization: Bearer $(login alice@example.com)" -H 'Content-Type: application/json' \
  -d '{"rating":5,"content":"手動示範"}'
# (b) bob 是 admin → 403 您沒有權限進行此操作
curl -s -w '\n%{http_code}\n' -X POST "http://localhost:3000/api/v1/user/product/search/$TOUR/reviews" \
  -H "Authorization: Bearer $(login bob@example.com)" -H 'Content-Type: application/json' \
  -d '{"rating":5,"content":"手動示範"}'
```

預期 (a) 輸出 `{"status":"failed","message":"購買過此行程的會員才能評論"}` 與 `403`；(b) 輸出 `{"status":"failed","message":"您沒有權限進行此操作"}` 與 `403`。若看到 `401`，代表 login 失敗（token 是空字串），檢查帳號密碼。

**示範 201**：在 `#/admin/register` 註冊 **`e2e-manual-demo@example.com`**（一律用這個 email，SQL 才能原樣貼上；符合 `TEST_EMAIL_PREFIXES`，下次執行 pytest 時 session 開頭會被 purge），然後原樣執行：

```bash
docker compose exec -T postgres sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"' <<'SQL'
WITH u AS (SELECT user_id FROM "user" WHERE email = 'e2e-manual-demo@example.com'),
     t AS (SELECT tour_id FROM tour WHERE title = '北海道雪景 5 日深度遊'),
     o AS (INSERT INTO orders (user_id, payment_status, total_price)
           SELECT user_id, 1, 45000 FROM u RETURNING order_id)
INSERT INTO order_item (order_id, tour_id, payment_status, total_price, quantity, start_date)
SELECT o.order_id, t.tour_id, 1, 45000, 1, now() FROM o, t;
SQL
```

預期輸出 `INSERT 0 1`；若是 `INSERT 0 0`，代表帳號還沒註冊或 email 打錯，停下來檢查，不要重跑到成功為止。之後以該帳號登入、開北海道詳情 → 評論表單與玩法表單都出現，送出得 201。

**注意**：自建帳號在被 purge 之前會讓 `user`、`user_level`、`point_record`（註冊時寫入，`controllers/userinfo.js:37`）、`orders`、`order_item`、`review`、`hidden_play` 的計數多出來；若在 pytest 執行途中手動建立，`test_seed.py` 會紅。

## 附錄

### A. 變更檔案清單

**backend**（`main..phase-3`，9 個檔案，+321／−24）

| 檔案 | 變更 |
|---|---|
| `migrations/V4__p3_review_constraints.sql` | 新增（部分唯一索引、rating CHECK） |
| `src/utils/purchase.js` | 新增（`hasPurchased`） |
| `src/controllers/product.js` | 搜尋排序／`duration`、詳情 404／food 空項、`title`、`delete_tourProduct` release、新增 3 個 controller |
| `src/controllers/home.js` | 首頁促銷期間與上架條件 |
| `src/controllers/userProfile.js`、`src/middlewares/userProfile/index.js` | PATCH `/info` 部分更新 |
| `src/middlewares/product/index.js`、`src/routes/product.js`、`src/utils/Validator/product_Validator.js` | 三支新 API 的 middleware、路由、驗證 |

**frontend**（`dev..phase-3`，18 個檔案）：`src/utils/api.js`、`src/router/index.js`、`src/components/HeaderComponent.vue`、`src/views/HomeView.vue`、`src/views/front/searchPage.vue`、`src/views/front/tourPage.vue`；刪除 `src/views/front/tourPageFake.vue`、`src/views/front/tourFakeUSA.vue` 與 `src/assets/img/tour/` 下 10 張圖。

**總覽**（`main..phase-3`，不含 evidence）

| 檔案 | 變更 |
|---|---|
| `tests/conftest.py`、`tests/test_infra.py`（新） | fixture、殘留清除與其測試 |
| `tests/test_product_read.py`（新）、`tests/test_product_write.py`（新）、`tests/test_product_routes.py`、`tests/test_api_smoke.py` | 商品 API 測試 |
| `tests/test_migrations.py`、`tests/test_member_auth.py` | V4 測試、移除 2 個 xfail |
| `e2e/test_product_flow.py`（新）、`e2e/test_member_flow.py`、`e2e/conftest.py` | 商品 E2E、401／timer 回歸 |
| `docs/db-contract.md` | §6 V4、購買數裁決 |
| `docs/reports/phase-2.md`、`docs/reports/phase-3.md`（本檔）、`docs/reports/evidence/phase-3/` | 報告與 evidence |
| `.github/workflows/ci.yml`、`pyproject.toml`、`uv.lock`、`refs.env` | CI 鎖版與 timeout、Python 上限、分支指向 |

### B. 已知限制

**B.1 P1 遺留第 4 項（P3 spec §8 C14）重申：P3 沒有改 `R__views_functions.sql` 與 `tests/db_contract.py`。**

```
$ git -C backend diff --stat main..phase-3 -- migrations/R__views_functions.sql
（無輸出）
$ git diff --stat main..phase-3 -- tests/db_contract.py
（無輸出）
$ git -C backend diff --name-only main..phase-3 | grep -c 'R__'
0
$ git diff --name-only main..HEAD | grep -c 'db_contract.py'
0
```

（`git diff --stat main..phase-3` 的完整檔案清單見附錄 A；`docs/db-contract.md`（契約文字）有改，`tests/db_contract.py`（契約測試輔助）沒有。）所以 P1 遺留的兩項限制仍然成立：`R__views_functions.sql` 的 DROP 清單寫死；`tests/db_contract.py` 不比對契約文字。

**B.2 P3 spec §8 的延後項**

| # | 項目 | 狀態 |
|---|---|---|
| C4 | `user.role` 加 CHECK 約束 | 延後到 P6（後台會員／角色）；P2 已在唯一寫入點正規化（`controllers/admin.js:58`） |
| C5 | `ROLLBACK` 本身丟錯時請求懸掛 | 只記錄；`server.js:3` 已載入 `express-async-errors`，「懸掛」很可能不成立，黑箱測試也寫不出紅燈；P4 重寫交易時以 fault injection 查證 |
| N4 | 搜尋與首頁清單 API 沒有總筆數 | 不改 API；前端用「回傳筆數小於每頁筆數就沒有下一頁」；日後可加 `X-Total-Count` header |
| N5 | 行程國家／地區是英文，`/web/filter/countries` 回中文，下拉無法對應 | 延後到 P6；P3 移除兩個下拉，API 的 `country`／`region` 參數保留 |
| N7 | 空結果時回應沒有 `data` 欄位（`resStatus` 只在有資料時輸出） | 不改，前端以 `data ?? []` 處理 |
| N8 | 首頁「好評專區」寫死（網站好評，不是商品評論） | 延後，未排定（P6 前再議）；首頁好評仍是假資料 |
| N9 | 首頁未帶 `type` 時 500（契約 §4.2） | 延後；前端一律帶 `type` 與 `item` |
| N10 | 付款成功沒有把 `order_item.payment_status` 設成 1（`newebpay.js:82,213,203–206`） | 延後到 P4，**P4 必做**（§1.14）；否則真實買家無法評論 |
| N11 | 其他 `pool.connect` 疑似漏 release（`cart.js`、`checkout.js`、`newebpay.js`）、`product.js:609` 新增商品 | 延後到 P4／P6 |
| N12 | seed 既有的「沒買過的人」的評論與玩法，規則不追溯 | 見下方 |
| N13 | 5 則 `review.type` 與 `tour.item` 不一致 | 見下方 |
| 其他 | 首頁促銷分頁的 seed 日期（backpacker 的京都古寺散步 11-08 已到期、台南小吃巡禮 11-28 才開始）只影響首頁展示 | 已知限制，放寬 seed 期間超出 P3 範圍 |
| 其他 | 評論與隱藏玩法的編輯、刪除、檢舉、管理者審核；多語系 | 不在任何已排定階段，P6 前再議 |
| 其他 | 字數以 JavaScript 字串長度計（UTF-16 code unit；emoji 可能算 2） | 已知限制（P3 spec §5.3） |

**N12**（seed 既有的「沒買過的人」的評論與玩法，規則不追溯）：評論 bob→馬爾地夫（無訂單）、carol→紐西蘭（2）（訂單 `payment_status = 2`）、carol→義大利（無訂單）、alice→巴黎（無訂單）；玩法 alice→紐西蘭（4）（訂單 `payment_status = 4`）、alice→大阪（無訂單）；另有 admin bob 寫的評論→曼谷設計旅店探索、玩法→北海道、巴黎（他有已付款訂單，但角色是 admin，`authRole('User')` 下不能寫）。若錯：展示時看得到「沒買過的人的評論」，可在重建 seed 時一併修。

**N13**：seed 有 5 則 `review.type` 與 `tour.item` 不一致（格式為 type／item）：馬爾地夫 hotel／travel、大阪 hotel／food、巴黎 food／spot、曼谷設計旅店 food／hotel、義大利 spot／travel。只影響 `review_type` 欄位的顯示，P3 頁面不顯示它，不修 seed。

**B.2a 最終修正波後的已知限制（ledger 記為 deferred）**

- 搜尋的 `start_date`／`end_date` 帶不存在的日期（例如 `2027-02-30`）會回 500，不是 400。
- 搜尋 400 的訊息直接顯示 API 參數名（`duration`、`start_date`、`min_price` 等），沒有轉成使用者用語。
- `end_date`／`start_date` 帶時區偏移時，validator 以伺服器時區（UTC）計算區間天數，而 SQL 的 `::date` 取字面日期，兩者可能差一天；前端 `type=date` 只送 `YYYY-MM-DD`，實際影響小。
- `tests/test_product_read.py` 的 `:164`、`:178`、`:199`、`:219`、`:227` 仍直接取 `["data"]`（空回應沒有 `data` 鍵時會 KeyError，而不是清楚的斷言失敗）。
- admin E2E 的 `pageerror` 斷言只抓得到 `expect` 完成之前發生的錯誤；之後才冒出的未處理 rejection 不會被發現。

**B.3 ledger 的「P4 以後」與 deferred minor**（逐項來自 `.superpowers/sdd/2026-11-19-p3-product/progress.md`，不重寫細節）

- Task 1：並行 pytest 會互刪（purge 在全套跑兩次，tests／e2e 各一份 fixture）；任何 pytest 都需 DB（autouse purge）；`ci.sh` 的 `uv run` 未加 `--frozen`；前綴掃描只抓 f-string；`test_google_login.py:230` 寫死 mock email；`_cleanup_all` 測試未驗「第一個」錯誤。
- Task 2：偏好寫入 DB 未斷言；`name:""` 與 `preference` 同送時靜默忽略（既有驗證設計）。
- Task 3：`home_promotion` 會員路徑的紅燈未單獨證明；price desc 無分頁回歸。
- Task 4：結尾 `else` 分支不可達（回 200＋查無，錯誤狀態碼），P4 以後連同外層 `if` 移除；UUID 不存在無直接測試；空餐廳 `opening` 斷言紅燈未獨立證明；spot 回歸只驗 200。
- Task 6：陣列 body 回英文訊息；部分斷言只驗狀態碼；body 400 先於 404 無測試；NUL 字元 500；格式錯誤的 JSON 先於 auth（既有）；`make_order` 同訂單第二品項清理依賴 fixture 順序。
- Task 7：大寫 scheme（`HTTPS://`）被擋（Joi scheme 分大小寫）；401 只測「請先登入」；`create_date` 未驗。
- Task 8：`Bearer null` 也算帶 `Authorization`；`updateUserInfo` 無 try/catch（既有）；`serviceSetting.vue:77` 既有 `v-html`（P6 範圍）；否定斷言在提示框關閉後空過的殘留小時間窗。
- Task 9：日期 `slice(0,10)` 依賴 backend UTC（部署換時區會少一天）（評論／玩法建立日期已於最終修正波修正，只剩行程日期）；`safeUrl` 擋 `javascript:` 無 E2E；無促銷時不出現 `<del>` 無反向驗證；`formatPrice(null)` 為 `NT$0`。
- Task 10：tab 缺 `role=presentation`、無 tabpanel／方向鍵；首頁 API 失敗無提示；卡片 `li` click 無鍵盤可及；收藏圖示 P5 需 `@click.stop`；`isSticky`／`handleScroll` 成為無作用程式碼。
- Task 11：搜尋測試依賴 seed 內容；`min>max` 等 400 顯示「載入失敗」誤導（已於最終修正波修正）；同關鍵字重複導航不重查；「自由選擇」文案為新增；ILIKE 萬用字元（既有後端）。
- Task 12：列表讀取失敗顯示「目前還沒有評論」誤導；共用 `submitting` 旗標；XSS 只驗評論未驗玩法 `title`／`content`；409 後重讀資格失敗成為未處理 rejection（只在 console）；（admin 詳情頁 E2E 已於最終修正波補上）。


### 附錄 C 最終審查修正波（2026-11-19）

| 項目 | 修正 | commit |
|---|---|---|
| F1 | 搜尋日期區間與 `duration`：controller 的語意是「開始日 ≥ start_date、結束日 ≤ end_date（第 2 輪改為含當天）、天數 = duration」，所以行程要落在區間內，只需 `duration ≤ 區間涵蓋天數`，涵蓋天數 = end_date − start_date + 1（含頭尾）。舊驗證要求 `duration` 等於天數差，寬區間永遠 400。超過時回 400「「duration」不可大於「start_date」到「end_date」涵蓋的天數（目前區間共 N 天）」。前端搜尋頁 400 時顯示後端 message，其他錯誤維持「載入失敗，請稍後再試」。例：seed 北海道 5 日行程（2027-06-02～2027-06-06，日期隨載入日平移）以 6/2～6/6 + `duration=5` 查詢，涵蓋 5 天、合法。第 2 輪另把 `end_date` 改為含當天（見下）。紅燈 [final-fix-red.txt](evidence/phase-3/final-fix-red.txt)（3 failed 19 deselected） | 總覽 `fb339da`（紅）；backend `a956697`；frontend `9940fa1` |
| F2 | `test_review_submit_with_expired_token` 先斷言「登入已過期」再等導頁 | 總覽 `44b2e9a` |
| F3 | 補 admin 詳情頁 E2E（`test_admin_sees_purchase_hint_without_forms`）：顯示未購買提示、無評論／玩法表單、不導頁 | 總覽 `44b2e9a` |
| F4–F7 | §1.4 條件措辭；`EXPIRED` 移到 `e2e/conftest.py` 共用；促銷測試改用 `live_promotion`（語意相符：有效促銷、價 900）；`["data"]` 改 `.get("data", [])`；刪 `_home_titles` | 總覽 `44b2e9a` |
| F8、F9 | `tourPage.vue` 新增 `createdText`（評論／玩法建立時間以 Asia/Taipei 換算），`dateText`（行程日期）不動；分享連結輸入框加 `autocapitalize/autocorrect/spellcheck` | frontend `9940fa1` |

第 1 輪 `scripts/ci.sh`：504 passed、0 xfailed（133.25s）。

**第 2 輪**：`end_date` 含當天。複審發現 controller 以 `旅遊結束日期 <= end_date`（當天 00:00）比對，而 seed 行程結束於 23:59:59，6/2～6/6 + `duration=5` 查不到北海道。改為 `旅遊結束日期 < (end_date::date + 1)`（backend `adffa31`）。紅燈 [final-fix2-red.txt](evidence/phase-3/final-fix2-red.txt)（總覽 `0377e20`，1 failed 22 passed）；測試從 DB 讀北海道日期（seed 日期浮動）。admin E2E 另斷言 `/eligibility` 回 403 且沒有 `pageerror`。前端 400 訊息 E2E 沒有先留紅燈證據（舊模板固定顯示「載入失敗」，新斷言在舊碼必紅）。第 2 輪 `scripts/ci.sh`：**505 passed、0 xfailed、0 failed**（138.06s）。

**第 3 輪**（只改總覽 repo 的測試與報告）：寬區間測試補「每列落在區間內」斷言——結果與 DB 以同條件（上架、5 天、開始日 ≥ 區間起日、結束日 < 區間迄日隔天）做集合相等，並另建區間內與兩個越界行程（seed 只有一個 5 日行程，單靠它分辨不出日期條件有沒有作用）；暫時停用 controller 的 `start_date`／`end_date` 條件，該測試轉紅，還原後轉綠（暫改動未 commit，backend 維持 `adffa31`）。另刪 `wait_for_timeout(300)`、`_login_and_open` 回傳 `/eligibility` response。§2.3 補上最終審查結果、§2.1 維持「未查證」。`scripts/ci.sh`：**505 passed、0 xfailed、0 failed**（136.57s）。
