# Phase 5：會員中心（我的訂單、點數與等級、通知設定、收藏、姓名規則、越權讀取）
> 2026-11-26（**定稿**，使用者 2026-11-27 同意合併） · backend tag `phase-5`＝merge `2271138` 到 main（起點 `0e3b192`，程式碼 HEAD `2f19285`） · frontend tag `phase-5`＝merge `56c3a54` 到 dev（起點 `bfd20f0`，程式碼 HEAD `89b2282`） · 總覽 tag `phase-5`＝merge 到 main（見 `git log main`）（起點 `025556b`＝與 `main` 的 merge-base；程式碼 HEAD `31863c7`） · GitHub Actions：`phase-5` 分支 run 45778412244 success（959 passed）
>
> 本報告依 `docs/superpowers/specs/2026-11-26-p5-member-center-design.md`（以下稱「P5 spec」）§0、§10、§12 與 `docs/reports/phase-4.md` 的格式撰寫，計畫見 `docs/superpowers/plans/2026-11-26-p5-member-center.md`（以下稱「計畫」）。引用一律以 commit hash、`檔案:行號`、evidence 檔名為出處；查不到的寫「未查證」。
>
> **起點的說明**：總覽起點是 `025556b`（`git merge-base main HEAD`；本機 `main` 的 HEAD，`phase-5` 從此開出；ledger 的 Task 0 BASE 也是它）。派工文字曾寫成另一個 commit，是**主對話的錯誤**（Ruling T10-1），初稿因此並列兩個候選，現已更正，本報告所有數字都以 `025556b` 為起點。
>
> 行號基準：P5 之前就存在的問題，行號取自修正前的 backend `0e3b192`（＝tag `phase-4`）與 frontend `bfd20f0`，已用 `git show` 逐一核對；沒有核對到的標「未查證」。紅燈 evidence 都在 `docs/reports/evidence/phase-5/`（以下省略目錄），已去除絕對路徑。
>
> 資料來源：P5 的 SDD ledger（逐 Task 的派工、審查、裁決紀錄，存在 `.superpowers/sdd/2026-11-26-p5-member-center/`，該目錄被 git 忽略，不在 repo 內；以下稱「ledger」）、各 Task 的實作報告、`git log`（總覽 `main..phase-5`、backend `main..phase-5`、frontend `dev..phase-5`）與上述 evidence。

## 0. 摘要

P5 的目標：讓會員中心可以從前端完整操作（我的訂單全狀態與明細、繼續付款；點數紀錄與等級；通知設定；收藏頁與各處愛心），同時修掉 P1 以來一直擋在「對外開放」前面的越權讀取（契約 §4.2 (c)），並清掉 P4 留下的項目（P5 spec §7）。

| 項目 | 結果 |
|---|---|
| 測試數量 | **798 passed、0 xfailed、0 skipped（P4 結束，`phase-4.md` §3.3）→ 959 passed、0 xfailed、0 skipped**（`tests/` 844＋`e2e/` 115；截至程式碼 HEAD：總覽 `31863c7`、backend `2f19285`、frontend `89b2282`）。淨增 161 個測試。**乾淨環境（`down -v`）連跑兩次：第 1 次 959 passed、227.80s（牆鐘 235s）；第 2 次（保留 volume）959 passed、224.75s（牆鐘 231s）；皆 0 failed／xfail／skip、exit 0，原始輸出 [clean-run-1.txt](evidence/phase-5/clean-run-1.txt)、[clean-run-2.txt](evidence/phase-5/clean-run-2.txt)**（Ruling T10-2 已執行）。更早的保留 volume 實跑：修正波前 `3d89477` 957 passed、206.73s（fable 重跑 957、213.95s）；修正波後 959 passed、215.04s（[task-10-ci.txt](evidence/phase-5/task-10-ci.txt)） |
| xfail／skip | 皆為 0（P4 已清空，P5 沒有新增） |
| 新增 migration | `V6__p5_member_center.sql`：`favorite_user_tour_key`、`cart_user_id_key`、`auto_setting_user_id_key` 三個唯一約束（§1.3）；`R__views_functions.sql` 的四個 function 多輸出 `收藏編號`（§1.2） |
| 後端 | 新增 `GET /user/orders`、`GET /user/orders/:order_id`、`GET /user/points/records`、`GET /user/automation/regions` 四支唯讀 API；修正已購買明細越權（§1.1）、收藏（§1.2）、通知設定（§1.4）、負點數與空券（§1.5）、姓名規則與 Google 名字（§1.6、§1.7）、P4 留下的項目（§1.8）；新增 `utils/nameRule.js`、`utils/orderStatus.js`、`utils/Validator/paging_Validator.js` |
| 前端 | `userprofilePage.vue` 以 `?tab=` 切換四個分頁（會員資訊、會員等級、個人偏好設定、個人訂單查看）；新增共用元件 `FavoriteHeart.vue`、收藏頁；Header 的死連結接上（§1.9、§1.10） |
| 審查 | 11 個 Task（0–10）依 R5 全部雙審（reviewer-opus＋reviewer-fable 平行、互不看對方結果）；Task 0–9 逐 Task 審過；**整條分支的最終雙審已完成：opus 與 fable 都判定程式可合併（沒有程式面的 Critical／Important），並已完成一輪修正（Ruling FW）**。6 個 Task（3、4、5、7、8、9）各開 1 個修正輪，Task 0、1、2、6 一次通過（§2.3）；fable 另在 `3d89477` 以保留 volume 重跑 `scripts/ci.sh`：957 passed、213.95s |
| 已知限制 | 手動取消訂單、等級升級規則、實際寄送通知留到 P6；其餘見附錄 B |

**修了幾個 bug**：§1.1–§1.7 是 P4 結束時已存在、P5 修掉的缺陷（越權讀取、收藏兩次回應與 500、重複列與多購物車、通知設定的併發與驗證、負點數與全 null 優惠券物件、三套姓名規則、Google 名字過長）；§1.8 是 P4 報告附錄 B 點名的項目。審查另外抓到由 P5 自己新寫的程式或文件引入的缺陷（折扣類型顯示 `none`、`?tab=constructor` 空白頁、負點數 E2E 在 API 回應前就通過、收藏 POST 的重試迴圈沒進鎖順序文件、鎖順序檢查結果少算一處反向，見 §2）。

## 1. 問題與修正

每項格式：現象 → 根因（行號）→ 紅燈 evidence → 修正 → 綠燈。「紅燈 commit」是總覽 repo 的 hash，「修正」是 backend／frontend 的 hash。

**先讀這段：紅燈 evidence 的限制**。逐項核對 evidence 與 ledger 後，有幾處紅燈不是「各自獨立、因該 bug 而失敗」，報告如實記錄，不美化：
- **Task 1 的 `test_alice_auto_settings_merged`**：紅燈 evidence 中這個測試是因為**測試輔助函式解析輸出錯誤**而失敗，不是行為錯誤；綠燈 commit 內修正了解析方式與預期 id（`seed_id` 換算，見下）。兩位審查員都另外驗證過，最終版本確實有鑑別力（ledger Task 1 minor）。
- **Task 7 的併發測試**（[task-7-red-concurrent.txt](evidence/phase-5/task-7-red-concurrent.txt)，10 次全紅）**不是鑑別力證據**：舊程式對重複收藏本來就回 400 且沒有 `favorite_id`，測試不論有沒有撞到競態都會紅。真正的鑑別力證據是修正輪的變異驗證（把 POST 改回先查再寫：新增的決定性測試紅、8 條執行緒測試 10 次中 8 次紅，[task-7-red-mutant.txt](evidence/phase-5/task-7-red-mutant.txt)）。
- **Task 6 的併發首次寫入測試**只有 2 條執行緒，對舊程式 10 次中 6 次紅、4 次綠（[task-6-red-concurrent.txt](evidence/phase-5/task-6-red-concurrent.txt)），鑑別力約 60%；ledger 列為待加強（附錄 B.2）。
- **一開始就綠的回歸測試**（各 commit 訊息與 Task 報告皆有註明，不是失敗證明）：Task 2 的 `test_profile_saves_trimmed_name`、`test_google_long_name_can_checkout`；Task 3 的 `test_own_unpaid_purchase_item_unchanged` 與修正輪新增的 3 支（詳情 401、自己不存在的訂單 404、已退款訂單的 payable）；Task 4 的 `test_coming_soon_tabs` 縮減版與修正輪的分頁 `limit=10`；Task 6 的 11 支（`ffc47b1` 訊息未註明，附錄 B.2）；Task 7 的 401／403、`tour_travel` 欄位比對、`test_async_errors` 新路由；Task 9 的 `test_refund_keeps_discount_columns`、鎖順序輪詢測試（916e266）、`test_paid_order_keeps_discount_columns_after_deadline_and_new_order`。
- **紅燈 commit 之後又修改測試的**：Task 1（`remap_ids` 之後 alice 的 `auto_setting` 最終 id 是 `seed_id` 換算後的 `d47d7d56-46dd-48ff-bf22-afcb3f46d2a9`，不是計畫寫的 `1111aaaa…`，測試預期值在綠燈 commit 調整）；Task 5（紅燈 commit 中 `test_point_records_reasons_and_order` 有 5 筆但預設 `limit` 是 4，永遠不會綠，改為明確傳 `limit=10`，commit `1ce1786`）；Task 3 修正輪（狀態對應斷言改為逐筆）。這些都不是為了讓測試通過而放寬斷言。

### 1.1 越權讀取：已購買明細（契約 §4.2 (c)；P5 spec §4.2）

**現象**：任何登入的 `User` 只要知道 `order_item_id`，就能讀到別人的購買明細（P1 起就標為「對外開放前必修」）。
**根因**（backend `0e3b192`）：`controllers/purchases.js:59` 的 `SELECT * FROM public."user_order_item" where order_item_id = $1` 與 `middlewares/purchases/index.js:31` 的 `SELECT * FROM public."order_item" where order_item_id = $1` 都只用 `order_item_id` 查，沒有 `user_id` 條件；`middlewares/purchases/index.js:34` 的 `if (!dataRepo)` 對 `pool.query` 的結果永遠為真值，404 永遠不會觸發。
**紅燈**：[task-3-red.txt](evidence/phase-5/task-3-red.txt)（總覽 `999146f`，24 failed、18 passed：新 API 404、sweep 找不到新 validator、purchases 越權 200 等）。
**修正**：backend `46c3d2b`：擁有者條件寫在 SQL（middleware 查 `order_item JOIN orders … AND o.user_id = $2`，controller 對 `user_order_item` 加 `AND 使用者編號 = $2`），非本人或不存在回 404 `查無此訂單項目`；本人但未付款維持現狀（200 `查無資料`，F3）。同一個 commit 新增 `GET /user/orders`（分頁）與 `GET /user/orders/:order_id`，兩者的 `total_price`、`promo_subtotal`、`discount_type`、`discount_amount`、`payable` 全部取自 `utils/trade.js::computePayable`（GC12），並回 `can_continue_payment` 與 `is_overdue` 兩個布林（F1），讀取 API 不開交易、不加鎖、不寫入。
**審查後修正輪**（總覽 `d455320`）：計畫的狀態對應斷言只比對集合，沒有鑑別力（§2.4 第 3 點），改為逐筆比對 `{payment_status: status_label}`；補詳情未登入 401、自己不存在的訂單 404、已退款訂單的 `payable` 等於實際付款金額。
**綠燈**：768 passed（修正輪後）；契約 §4.2 (c) 標為已修正（總覽 `03219c5`）。
**這個 Task 順手修的**：`purchases_Validator.querySchema` 的訊息由「lang」改成「語言」（GC14）；`trade.js` 抽出 `paymentInProgressSql`、`orderDeadlineSql`，讓 `pastOrderDeadline` 與會員端列表共用同一段期限 SQL。

### 1.2 收藏：兩次回應、500、重複收藏、非本人（P5 spec §4.5）

**現象**：`GET /user/collection/info/all` 每次送兩次回應（第二次丟 `ERR_HTTP_HEADERS_SENT`）；`POST` 的 `tour_id` 格式錯誤回 500；找不到行程與重複收藏回 400；`DELETE` 非本人回 400；同一行程可被重複收藏；商品 API 不回 `favorite_id`。
**根因**（backend `0e3b192`）：`controllers/collection.js:39`（有資料）與 `:57`（無條件）各呼叫一次 `resStatus`；`:78` `INSERT INTO favorite … VALUES ($1, $2)` 沒有唯一約束可依靠，只靠 `middlewares/collection/index.js:68` 先查再寫；`middlewares/collection/index.js:46` 以 `SELECT * FROM tour WHERE tour_id = $1` 直接查未驗證格式的 `tour_id`；`:102` 的 `DELETE` 查詢同類（D4）。
**紅燈**：[task-7-red.txt](evidence/phase-5/task-7-red.txt)（總覽 `3ca6294`，6 個檔案、151 項，33 failed、118 passed）；併發測試的限制見本章開頭。
**修正**：backend `ab52b9a`：列表不分頁、伺服器端上限 100 筆、新到舊、回 `{ data, total }`（F4／F5）；`POST` 以 `INSERT … ON CONFLICT (user_id, tour_id) DO NOTHING RETURNING favorite_id` 寫入，新增 201 `收藏成功`、已收藏 200 `已收藏過此行程`，皆回 `{ favorite_id }`；行程不存在或下架 404 `查無此旅遊項目`；`DELETE … WHERE favorite_id = $1 AND user_id = $2`，0 列 404 `查無此收藏項目`；UUIDv4 驗證回 400；`tour_travel`、`tour_tour_detail`、`tour_hotel`、`tour_restaurant` 四個 function 多輸出 `收藏編號`（詳情 API 輸出鍵 `favorite_id`，搜尋與首頁原樣輸出 `收藏狀態`／`收藏編號`，D2）。R7：在既有 volume 上重跑 Flyway，`R__views_functions.sql` 的 `DROP FUNCTION … CASCADE` 之後，function 與 view 清單前後完全相同（[task-7-repeatable-rerun.txt](evidence/phase-5/task-7-repeatable-rerun.txt)）。
**審查後修正輪**（總覽 `0198349`、backend `4255bbd`）：`lock-order.md` §11 補上 POST 的重試迴圈（最多 3 輪）；新增決定性測試 `test_favorite_waits_on_uncommitted_insert_then_returns_same_id`；詳情 `favorite_id` 測試涵蓋 travel／hotel／food／spot 四種。
**D6**：`tests/test_async_errors.py` 原本拿收藏路由當「try 外 reject → 500」的案例，收藏修好後回 400，改用 `POST /user/trade/cart/<hotel 行程>`（`options.room_type` 含 NUL 字元，Joi 接受、查詢在 try 外 reject）；原收藏路由另寫 `test_collection_bad_uuid_is_400`。
**綠燈**：945 passed（修正輪後）。

### 1.3 V6 唯一約束、seed 重複、建購物車併發（P5 spec §3、§7.2）

**現象**：`favorite`、`cart`、`auto_setting` 沒有唯一約束，併發請求可以寫入重複列；P4 報告 B.4b 記錄的「兩個 cart 時新增購物車與付款結算可能死結」只能靠機率避開；seed 的 alice 有兩筆 `auto_setting`（`db/seed-build/tripeasy_fakedata.sql:842` 起，`created_at` 相同，Task 0 以 `GROUP BY … HAVING count(*) > 1` 確認）。
**根因**：V1 沒有這三個約束；`controllers/cart.js:26`、`:31` 先查 cart、查不到才 INSERT，沒有唯一約束時併發首次加入會建出兩個 cart。Flyway 先跑 V6 再跑 `R__seed`（rank 6、7），所以 seed 的重複列在乾淨 volume 上會讓 `R__seed` 失敗。
**紅燈**：[task-1-red.txt](evidence/phase-5/task-1-red.txt)（總覽 `6668160`，9 failed、113 passed）、[task-1-red-concurrent.txt](evidence/phase-5/task-1-red-concurrent.txt)（併發首次加入購物車，10 次全紅，cart 2 列）。
**修正**：backend `175b63d`：V6 加三個約束；cart 與 auto_setting 只做預檢（有重複就 `RAISE EXCEPTION`，不自動合併）；`cart.js` 改 `INSERT … ON CONFLICT (user_id) DO NOTHING` 再 `FOR UPDATE`（D3，提前到地基）。總覽 `98e99d8`：`build_seed.py` 新增 `merge_duplicate_auto_settings`（R1 的規則：每欄取 `updated_at` 較新者，相同時取 `auto_setting_id` 較小者），seed 的 `auto_setting` 4 → 3 列。
**注意**：保留列的最終 `auto_setting_id` 是 `d47d7d56-46dd-48ff-bf22-afcb3f46d2a9`（`remap_ids` 換算），不是來源的 `1111aaaa…`；`docs/db-contract.md` :89 已於本次補上說明。
**綠燈**：使用者執行 `docker compose down -v` 後 715 passed；併發測試 10 次全綠。`tests/db_contract.py` 只記 view／function、沒有約束或 seed 筆數，所以沒有改動（F8「若有」）。

### 1.4 通知設定：讀取、寫入、地區驗證與併發（P5 spec §4.4；R2、R2a）

**現象**：前端沒有任何地方呼叫 `/user/automation/*`；後端寫入是先查再寫（V6 之後併發首次寫入會撞約束回 500）；地區沒有驗證；開關欄位輸出 SMALLINT。
**根因**（backend `0e3b192`）：`controllers/automation.js:60`、`:109` 為 `Insert into public."auto_setting" …`，沒有 `ON CONFLICT`。
**紅燈**：[task-6-red.txt](evidence/phase-5/task-6-red.txt)（總覽 `ffc47b1`，20 failed、72 passed）、[task-6-red-concurrent.txt](evidence/phase-5/task-6-red-concurrent.txt)（10 次中 6 次紅）。
**修正**：backend `251249b`：讀取回預設值；寫入改單一 `INSERT … ON CONFLICT (user_id) DO UPDATE`；新增 `GET /user/automation/regions`（上架行程的 distinct `(country, region)`，回陣列，F6）；寫入驗證「值在上架清單中，或與目前存的值相同」（R2a、F2）；開關輸出布林。frontend `bb0349e`：「個人偏好設定」分頁接上；`automaticSetting.vue` 刪除；`isMemberApi` 加 `/user/automation`。
**綠燈**：917 passed；併發測試修正後 10/10 綠。

### 1.5 負點數與全 null 優惠券物件（P5 spec §4.3；R3、R6）

**現象**：退款扣回回饋後 `travel_point` 可為負（P4 Q2），會員中心與登入回應會顯示負點數；沒有可用優惠券的會員，`GET /pointslevel` 的 `coupon` 是 `[{coupon_id: null, code: null, …}]`；註冊與 Google 新會員會寫一筆 `新增 0` 的 `point_record`，列出來會顯示「購物回饋 +0」。
**根因**（backend `0e3b192`）：`controllers/userinfo.js:57`、`:123`、`:249`、`:379` 的 `points` 直接回 `travel_point`；`user_level_point_coupon` 對優惠券用 LEFT JOIN，而 `controllers/userProfile.js` 沒有檢查優惠券欄位是否為 NULL；`controllers/userinfo.js:37`、`:213` 寫 `新增`、`point = 0`。
**紅燈**：[task-5-red.txt](evidence/phase-5/task-5-red.txt)（總覽 `8ac641e`，18 failed、179 passed）。
**修正**：backend `354bfea`：新增 `GET /user/points/records`（SQL 排除 `point = 0` 與 `減少_確認中`，R3；原因文字對應見共用約定）；`pointslevel` 與四處登入回應的 `points` 改 `Math.max(0, …)`（R6，DB 不變）；沒有券時 `coupon` 回 `[]`。frontend `647983e`：會員等級分頁（等級、餘額、優惠券、點數紀錄）。
**審查後修正輪**：負點數 E2E 原本在 `pointslevel` 回應之前就通過（沒有鑑別力），改為 `page.expect_response` 並讓等級卡片在載入後才顯示（frontend `16eb3d5`、總覽 `7e00ffa`）；`docs/db-contract.md` 四處改為「沒有券回 `[]`」。
**綠燈**：888 passed（修正輪後）。
**回饋比例**：前端寫死 10%（F10 偏離 spec，P5 spec §12 第 18 點）。

### 1.6 姓名規則：三處規則統一（P5 spec §6；R4）

**現象**：註冊、會員資料、結帳收件人三處各有不同的姓名規則（2–5、2–5、2–10 個字，且都禁止空白與符號）。
**根因**（backend `0e3b192`）：`utils/Validator/userInfo_Validator.js:4` `/^[a-zA-Z0-9\u4e00-\u9fa5]{2,5}$/`、`userprofile_Validator.js:3` `/^[\u4e00-\u9fa5a-zA-Z0-9]{2,5}$/`、`checkout_Vaildator.js:23` `/^[\u4e00-\u9fa5a-zA-Z0-9]{2,10}$/`。
**紅燈**：[task-2-red.txt](evidence/phase-5/task-2-red.txt)（總覽 `46288ce`，30 failed、198 passed）、[task-2-red-frontend.txt](evidence/phase-5/task-2-red-frontend.txt)（`b603135`，e2e 3 failed、1 passed）。
**修正**：backend `ba08ec7`：新增 `utils/nameRule.js`，三處共用：去頭尾空白後 2–20 個 Unicode 字元（`[...s].length`），不限字元種類，拒絕 `\p{Cc}`；訊息見共用約定。frontend `abf0e47`：註冊、會員資料、結帳表單同步。
**綠燈**：741 passed、e2e 94 passed。`tests/test_member_auth.py:343` 的 `a!b`→400 斷言屬於被取代的舊規則，改為 `"名\u0007"`→400，並釘住 `a!b`→200（T2-a）。

### 1.7 Google 登入名字過長（P5 spec §6；P4 報告附錄 B）

**現象**：Google 名字超過規則上限時，會員存進 DB 後在結帳頁被擋住。
**根因**：`controllers/userinfo.js:202`（INSERT 語句，參數在 `:203`；P5 spec §6 引用 `:142`、`:202`）把 Google 回傳的名字原樣寫進 `"user".name`。
**紅燈與修正**：與 §1.6 同一批（`test_google_emoji_name_truncated_by_code_point` 在 `tests/test_google_login.py`，審查重點 1）。`googleDisplayName(name, email)`：先移除 `\p{Cc}`，去空白後 ≥ 2 字則以 code point 取前 20 字（不留下半個 surrogate），截斷後再去空白；不足 2 字則用 email 的 `@` 前段（同樣移除控制字元、取 20 字、去空白），前段仍 < 2 字則「旅客」＋前段。「截斷後再去空白」與 email 前段的處理是 Ruling T2-c 補的，spec 沒寫。

### 1.8 P4 留下的項目（P5 spec §7）

| spec §7 | 結果 |
|---|---|
| 7.1 折扣欄位清空 | 訂單逾時（`expireIfOverdue`）或被取消（`cancelPendingOrders`）時，在 `releaseReservations` 之後呼叫新的 `clearOrderDiscount`，清空 `orders.discount_type`／`discount_price`；屬 `lock-order.md` 例外 A。紅燈 [task-9-red.txt](evidence/phase-5/task-9-red.txt)（總覽 `f92dfcb`，3 failed、1 passed〔`test_refund_keeps_discount_columns`，回歸〕）；backend `94c9326`。審查補洞：`checkout.js` summary 在本次呼叫轉逾時時，回應的 `discount.type`、`summary.discount_price` 也要是 `null`（紅燈 [task-9-red-summary-expired.txt](evidence/phase-5/task-9-red-summary-expired.txt)，總覽 `a43f69f`，1 failed；backend `d3280ce`）；已付款訂單過期不清折扣欄位（回歸測試）。理由已改變，決定維持（P5 spec §12 第 16 點，F9） |
| 7.2 多購物車死結 | 見 §1.3；`docs/lock-order.md`「已知問題」改為「（已解決）」，補 `test_first_add_concurrently_creates_one_cart` |
| 7.3 `newebpay.js` 註解編號 | backend `94c9326` 把註解 7→4、4→5、5→7 對齊 P4 spec §5.5 新編號；P4 spec 刪除「與程式註解的編號對照」（總覽 `478606a`） |
| 7.4 NOWAIT 固定等 1.5 秒 | 總覽 `916e266`：新增 `_wait_until_blocked_by`，輪詢 `pg_stat_activity` 確認請求在等鎖；F23 mutation（把 holder 的 `FOR UPDATE` 去掉）→ 3 failed（30.55s），還原後 `git status --short` 乾淨 |
| 7.5 P4 報告的矛盾 | 以已裁決為準（負點數會員中心一律顯示 0），P4 報告不改（見附錄 B） |
| 7.6 lock-order 行號核對 | Task 0 Step 3 以 backend `0e3b192` 核對（見 §1.11）；Task 10 重核，見 §1.11 |

### 1.9 前端：會員中心分頁、訂單、等級（P5 spec §5；D1、F1、F13）

**現象**：`HeaderComponent.vue:68-70` 桌機會員選單的「會員等級」「個人偏好設定」「個人訂單查看」是 `router-link to="#"`，手機選單的「購物車」（`:119`）也是；`router/index.js:128-131` 的 `personalOrder` 是空頁；會員中心沒有任何訂單或點數畫面。
**紅燈**：[task-4-red.txt](evidence/phase-5/task-4-red.txt)（總覽 `ec9fcf9`，7 failed、31 passed）；修正輪 [task-4-red-round1.txt](evidence/phase-5/task-4-red-round1.txt)（`0b877a4`，3 failed、6 passed）。
**修正**：frontend `e88bb45`：`?tab=` 切換（未知或缺少 → `info`）、訂單分頁（明細、繼續付款，只讀 `can_continue_payment`／`is_overdue`／`status_label`，不在前端算期限）、Header 連結接上、`isMemberApi` 加 `apiUrl_orders`；呼叫時明確傳 `limit: 10`（F13）。修正輪 `3ed8ed8`：折扣類型為 `none` 時顯示「無」而不是原字串、`?tab=constructor`／`__proto__` 改用 `Object.hasOwn`、明細載入失敗還原 `openDetailId`、Header 以 prettier 排版。
**綠燈**：e2e 103 passed、tests 768 passed。

### 1.10 前端：收藏頁、愛心、P5 主線 E2E（P5 spec §0、§4.5）

**紅燈**：[task-8-red.txt](evidence/phase-5/task-8-red.txt)（總覽 `55ff39f`，7 failed）。
**修正**：frontend `e4ea6d3`：`FavoriteHeart.vue`（`data-testid="favorite-heart"`、`aria-pressed`、`aria-label` 為 `加入收藏`／`取消收藏`）接在搜尋卡片、行程頁（放在價格旁，T8-1）、首頁；收藏頁 `collectPage.vue`。修正輪（總覽 `1326263`、frontend `9460d7a`）：主線 E2E 改走 UI 登入（初版注入 token，與 spec §0 第 1 步「登入」不符）、鎖定失敗訊息「伺服器錯誤」、訪客點愛心斷言沒有送出 POST、已收藏的行程載入即亮、搜尋頁點愛心後 URL 不變、移除未使用的 catch 參數與無效樣式。
**最終修正波（Ruling FW）**：`delete_favorite` 對 404（查無此收藏項目）視為已取消、不顯示錯誤框（紅燈 [task-10-red-heart-404.txt](evidence/phase-5/task-10-red-heart-404.txt)，frontend `89b2282`）。
**綠燈**：952 passed。主線 E2E 與修正輪後 `scripts/ci.sh` 的結果都是 952 passed。

### 1.11 與 spec 的差異（全部裁決 R1–R7、R2a、D1–D9、F1–F26 與處理結果；F22）

起草與開工前掃描讀碼時與 spec 不同、或需要主對話裁決的項目。格式：**決定 — 理由 — 若錯的代價**；ledger 或計畫沒有寫理由或代價的，寫「未記」，不補寫。

**R 系列（起草時待裁決；計畫「Ruling」區塊）**

| # | 決定 | 理由 | 若錯的代價 | 處理結果 |
|---|---|---|---|---|
| R1 | alice 的兩筆 `auto_setting` 在 seed 來源合併成一筆：每欄取 `updated_at` 較新者，相同或沒有時取 id 較小者；刪 `4444dddd…`；`test_seed.py` 4 → 3；V6 對 cart／auto_setting 只預檢、不自動合併；Task 1 後由使用者自己 `down -v` | V6 的唯一約束與 Flyway 順序（V6 先於 `R__seed`）讓重複列無法存在；規則固定、可重現 | alice 的 `early_notify` 從 1 變 0，展示時「出發前提醒」顯示未勾選 | Task 1 完成（§1.3）；使用者已 `down -v` |
| R2 | 價格追蹤的 `country`／`region` 以上架行程（`tour.status = 1`）的 distinct `(country, region)` 為準；新增唯讀 `GET /user/automation/regions` | 選單與驗證同源，與 seed 及搜尋參數一致（P3 搜尋已移除國家下拉，搜尋 API 比對 `tour` 的英文值） | 多一支唯讀 API；中文 `country`／`region` 表本階段不使用 | Task 0 Step 8 重新查證三項皆相符；Task 6 完成（§1.4） |
| R2a | 存著的地區若已無上架行程，表單仍列為選項並標註「（目前沒有上架行程）」；寫入驗證「值在上架清單，或與目前存的值完全相同」就通過 | 會員沒改任何東西卻存不了檔，會以為系統壞了 | 已沒有上架行程的地區可能被長期保留，P6 排程只是比對不到東西 | Task 6 完成 |
| R3 | 點數紀錄 API 在 SQL 排除 `point = 0`，前端不另外過濾；測試含「新註冊會員的點數紀錄是空列表」 | 註冊時寫的 `新增 0` 不是購物回饋，顯示出來會誤導 | 真的 0 點紀錄（目前程式不會產生）也看不到 | Task 5 完成（`test_point_records_hide_signup_zero_row`） |
| R4 | 姓名只檢查長度：去頭尾空白後 2–20 個 Unicode 字元，不限字元種類；另拒絕 `\p{Cc}`；Google 名字先移除 `\p{Cc}` 再套截斷與後備規則 | Google 名字常含空格，限制字元種類會讓截斷後仍過不了結帳；控制字元會破壞顯示與日誌 | 名字可含 emoji、符號，前端版面要能容納 | Task 2 完成（§1.6、§1.7） |
| R5 | 全部 Task（0–10）都雙審 | `~/.claude/CLAUDE.md` 的門檻是「跨多檔，或動到 CI 設定」，Task 0 改 `refs.env`，其餘每個 Task 都跨多檔 | 審查成本加倍 | Task 0–10 與整條分支的最終審查皆已雙審（Task 10 的文件由最終審查一併審；最終審查後完成一輪修正，Ruling FW） |
| R6 | 註冊、Email 登入、Google 登入、`get_user_loginStatus` 回傳的 `points` 改 `Math.max(0, …)`，DB 不變；Email 登入與 loginStatus 寫測試 | spec 反目標「會員中心的任何地方都不顯示負點數」 | 只多 4 處 clamp | Task 5 完成：`controllers/userinfo.js` :58、:124、:250、:380 皆 `Math.max(0, Number(...))` |
| R7 | Task 7 依賴 `R__views_functions.sql` 開頭的 `DROP FUNCTION … CASCADE` 才能改 `RETURNS TABLE`；在既有 volume（不 `down -v`）上重跑 migration，確認 Flyway 重跑 R__ 檔且被 CASCADE 刪掉的物件都重建，否則停下回報 | 未記 | 未記 | Task 7 完成：function 20 個、view 12 個，前後清單 diff 為空，`flyway_schema_history` 中該檔列數 1 → 2、皆 success |

**D 系列（起草時已確認、計畫直接處理，不需裁決）**

| # | 內容 | 處理結果 |
|---|---|---|
| D1 | Header 死連結：桌機會員選單 3 個與手機選單「購物車」是 `router-link to="#"`；沒有收藏頁連結（`HeaderComponent.vue:68-70`、`:119`，已用 `git show bfd20f0` 核對） | Task 4 全部接上；`HeaderReal.vue` 沒有被引用，不動 |
| D2 | spec 說「4 個 view」，實際是 4 個 SQL function，改 `RETURNS TABLE` 靠檔頭 `DROP FUNCTION`；搜尋 API 原樣輸出 function 欄位（鍵是 `收藏狀態`，不是 `is_favorited`） | Task 7；spec §12 第 7 點 |
| D3 | `cart UNIQUE(user_id)` 後，舊的「查不到就 INSERT」併發首次加入會撞約束回 500，所以 `ON CONFLICT` 提前到 Task 1 | Task 1；spec §12 第 8 點 |
| D4 | 收藏 `POST` 找不到行程回 400、重複收藏回 400、`DELETE` 非本人回 400；spec 要 404／200 | Task 7 依 spec 改；spec §12 第 9 點 |
| D5 | 前端沒有任何地方呼叫 `/user/purchases/*` 與 `/user/automation/*`（`grep` frontend `src`） | spec「前端改用新 API」無事可改；SMALLINT → 布林的輸出改動沒有其他呼叫者 |
| D6 | `test_async_errors.py` 的目的是「try 外 reject 要回 500」，收藏修好後必須換路由 | Task 7 換成購物車 POST（§1.2） |
| D7 | 訂單列表的折扣類型與金額改由 `computePayable` 回傳（spec §7.1 的理由說列表「直接顯示」欄位） | Task 3；spec §12 第 16 點；§7.1 的清空照做，但列表不依賴它 |
| D8 | spec 引用的行號起草時逐一讀過與程式一致；`"user".name` 是 `varchar(255)`，20 字不需加寬；`docs/lock-order.md` 全部 `file:line` 與 backend `0e3b192` 一致 | Task 0 Step 3 再核：自動抽出 86 條加簡寫行號，無偏差 |
| D9 | `/admin/personalOrder` 仍是空頁 | 不動，記入附錄 B |

**F 系列（開工前衝突掃描，2026-11-26 主對話裁決；ledger Pre-flight）**

| # | 決定 | 理由 | 若錯的代價 | 處理結果 |
|---|---|---|---|---|
| F1 | 列表與明細多回 `can_continue_payment`（狀態 ∈ {-1,0}、SQL `now() < deadline`、非付款進行中）與 `is_overdue`（狀態 ∈ {-1,0}、`now() >= deadline`、非付款進行中）；前端只讀布林，`deadline` 只顯示 | GC17、spec §4.2 禁止前端算期限 | 多 2 個欄位 | Task 3、4；spec §12 第 11 點。註：`now() >= deadline` 與 `pastOrderDeadline` 的 `deadline < now()` 在 1 微秒邊界不同（ledger Task 3 minor） |
| F2 | R2a「與目前存的值相同就通過」也適用 `max_price`；seed 的 `1200.5` 保留 | 與 R2a 同理 | 非整數的舊資料會一直留著 | Task 6；spec §12 第 12 點 |
| F3 | 舊 `/user/purchases/info*` 維持現狀，只修越權與 `:34`；撤回「本人未付款回 404」；Task 0 查證 `user_order_item` 欄位與篩選 | spec §4.2 的範圍 | 無 | Task 0、3；spec §12 第 13 點 |
| F4／F5 | 收藏列表不分頁，伺服器端上限 100 筆、新到舊，回 `{ data, total }`；前端不做分頁 UI | spec 沒有分頁 | 收藏超過 100 筆的會員看不到較舊的收藏 | Task 7、8；spec §12 第 14 點 |
| F6 | regions 是查找清單，不套用 `{ data, total }` | 未記（共用約定列為例外） | 無 | Task 6；spec §12 第 15 點 |
| F7 | automatic redirect 測試移到 Task 4，只斷言 URL 與 `tab` 參數 | 未記 | 未記 | Task 4 |
| F8 | V6 與 seed 的變動同步 `tests/db_contract.py`（列進 Task 1 Files 與步驟） | 未記 | 未記 | Task 1：`db_contract.py` 只記 view／function，沒有約束或 seed 筆數，未改（實作者偏離 2，審查接受） |
| F9 | spec §12 記錄 §7.1 的理由已被 D7 改變；決定本身維持 | 列表不再依賴那兩欄 | 未記 | Task 9；spec §12 第 16 點 |
| F10 | 補 tie-break 測試與通用合併函式名；回饋比例若有 API 輸出就從 API 讀（Task 0 查證），沒有則前端寫死 10%，並在 spec §12 記為偏離 | 未記 | 未記 | Task 0 查證：沒有任何 API 輸出（Step 9 (h)）；Task 5 前端寫死；spec §12 第 18 點（Task 10 補記，T5-8） |
| F11 | 補 `SWEEP_JS` target，並把 `tests/test_member_auth.py` 列進 Files | 未記 | 未記 | Task 2、3、5、6、7 逐一補 |
| F12 | Task 5 引用 `controllers/userinfo.js` 以函式名為錨點，不用行號 | 未記 | 未記 | Task 5 |
| F13 | 前端 `get_orders`、`get_point_records` 明確傳 `limit: 10`；後端預設 4 不改 | 未記 | 未記 | Task 4、5（Task 4 修正輪補 11 筆訂單的分頁 E2E；點數紀錄的 `limit=10` 沒有 E2E，附錄 B.2） |
| F14／F15／F21 | 掃描列出的查證項目與起草時項目合併為 Task 0 Step 9 (a)–(l)（含 F21＝(d) 首頁 API 是否走 `tour_*` function）；`isMemberApi` 是 `startsWith` 前綴比對，Task 5、6 把新 URL 前綴加進去 | 未記 | 未記 | Task 0 全部相符；orders、points、automation、collection 前綴現在都在 `isMemberApi`（`frontend/src/utils/api.js:46-49`） |
| F16 | 檢查與移除各用一個 regex，檢查用的不加 `g`；補「會員資料存入去頭尾空白後的值」測試 | 避免 `lastIndex` 狀態 | 未記 | Task 2 |
| F17 | E2E 涵蓋輸入 21 字被擋（註冊、會員資料、結帳） | 未記 | 未記 | Task 2（`task-2-red-frontend.txt`） |
| F18 | 註明 `items[].discount_price` 來自 `order_item` | 未記 | 未記 | Task 3 |
| F19 | 紅燈指令明列檔案 | 未記 | 未記 | 各 Task 紅燈 |
| F20 | 補 `test_delete_bad_uuid_is_400` | 未記 | 未記 | Task 7 |
| F22 | 報告大綱列出全部 R、D、F 裁決 | 未記 | 未記 | 本節 |
| F23 | mutation 驗證用 `git stash` 或 patch 檔，還原後 `git status --short` 必須乾淨 | 未記 | 未記 | Task 7（`git -C backend status` 乾淨）、Task 9（只剩既有的 `?? .claude/`） |
| F24 | 負點數情境由退款流程造成（沿用 P4 helper），不直接設 DB | 未記 | 未記 | Task 5（`negative_points_via_refund`） |
| F25／F26 | 紅燈步驟中的併發測試至少跑 10 次；10 次都沒紅就在 evidence 照實記錄 | 未記 | 未記 | Task 1（10/10 紅）、Task 6（6/10 紅）、Task 7（10/10 紅但不是鑑別力證據，見本章開頭） |

**Task 0 查證結果（P5 spec §7.6；evidence [task-0-verify.txt](evidence/phase-5/task-0-verify.txt)）**

| Step | 結果 |
|---|---|
| 1 分支 | 三 repo 皆開 `phase-5`；`refs.env` 改 `phase-5`（總覽 `250dba7`）；相符 |
| 2 V6 版本號 | versioned 最大 5；rank 6 `R__seed`、rank 7 `R__views_functions`；相符（brief 的 `R__views` 是簡稱） |
| 3 lock-order 行號 | backend HEAD `0e3b192`；自動抽出 86 條加簡寫行號逐條核對，無偏差 |
| 4 seed 重複 | favorite 0、cart 0、auto_setting 1（alice）；相符 |
| 5 point_record | `新增` 15 筆、`減少` 3 筆，`order_id` 皆非 NULL；相符 |
| 6 Header 死連結 | 行號與預期完全一致 |
| 7 既有 E2E | 2 passed；**「-1 → 0 → 1」不是都有直接斷言**：`test_checkout_button_creates_order` 只斷言 -1、`test_trade_main_flow` 只斷言最終 1，狀態 0 沒有被直接斷言，只由 `checkout.js:203` 讀碼確認（§2.4 第 2 點） |
| 8 地區來源 | (a) 兩頁無 country／region 下拉；(b) `product.js` 比對 `所屬國家`／`所屬地區`（ILIKE）；(c) seed 的 Japan／Tokyo、France／Paris 都在上架行程；相符 |
| 9 (a)–(l) | 全部相符；(d) 登入所有分支都走 `tour_travel($1)`；(h) 沒有回饋比例（`user_level.benefits` 是 V1 的 `TEXT NULL`，seed 有值，但 backend、frontend `src` 沒有任何程式引用）；(i) 四個 function 皆為 `level.points` |

**Task 0 evidence 的更正**（ledger Task 0 minor，原 evidence 不改，在此註明）：
1. 附錄中 `doc:51` 被誤判成 `utils/trade.js:179/189`；實際是 `checkout.js:175`（`paymentInProgress`）、`:179`（`reservationMatches`）、`:189`（`evaluateDiscount`）。summary 段已寫「人工確認為 checkout.js」，附錄清單沒有同步更正。
2. summary 行寫「無偏差／皆相符」，但 Step 7 的「0 狀態」並未直接斷言（兩位審查員的同一項發現：opus 列 Important、fable 列 Minor；T0-I1 裁決接受）。
3. evidence 內容是摘要，不是原始輸出；第 9 (a) 點寫「711-737 附近」（實際在 :715）；Step 3 的簡寫行號沒有輸出。

**lock-order 行號重核（Task 10，spec §7.6）**：以 backend HEAD `d3280ce`（Task 9 最後一次動行號的 backend commit）重核；最終修正波的 backend `2f19285` 只改 `collection.js` 一行（空列表的 `total`），行號不變。Task 9 修正輪已逐一核對 `checkout`／`discounts`／`newebpay`／`admin`／`userinfo`／`cart`／`collection`／`automation`／`coupon` 的引用，除 `userProfile.js` 改 `:52-58`、`product.js` 改 `:626-630` 外皆正確。Task 10 對 `trade.js` 的 34 個引用行與 `newebpay.js` 8 個引用行、`collection.js:75-79`／`:89-92`、`cart.js:26-33`、`automation.js` 的 `ON CONFLICT` 行抽查，皆與文件相符；`lock-order.md` 檔頭、「已知問題（已解決）」、「已知缺口」（1.5 秒那句已刪）都已是現況，本次補了「對應的測試」四支併發測試與 §10 automation 條目的外鍵 KEY SHARE 說明。

## 2. Vibe coding 工作流

### 2.1 使用的 skill

SDD（subagent-driven development）流程：主對話只做方向、裁決與審查比對；每個 Task 由 implementer（Sonnet）依計畫逐步實作（紅燈 commit → 實作 → 綠燈 commit），reviewer-opus 與 reviewer-fable 平行審查、互不看對方結果（R5：全部 Task 雙審），主對話比對差異後裁決；「必須修正」項目退回 implementer，修完再審。每個 Task 的狀態、裁決與 deferred minor 記在 ledger。使用者在 `docker compose down -v`（Task 1，Task 10 Step 3 待執行）、`.env` 修改、push、合併、tag 前都被詢問。派工前有一次「開工前衝突掃描」（reader 盤點，產出 F1–F26）。

### 2.2 Ruling 與審查對照

下表為每個 Task 執行中的裁決（ledger 以 `Ruling T<N>-…` 開頭的 28 條＋`Ruling T10-1`、`T10-2`，加上 `Ruling GC3`、`Ruling FW`、`Ruling FW-2`，共 33 條）。格式：裁決 — 理由 — 若錯的代價；ledger 沒寫的寫「未記」。

| # | 裁決（出處） | 理由與代價 |
|---|---|---|
| T0-I1 | 接受 Task 0 的偏離：狀態 0 沒有被直接斷言（審查：opus I-1、fable M1） | 前提成立：主線 e2e 能走到 mock 付款，而 `newebpay.js:41-43` 對非 PENDING 回 409，所以訂單必定經過 0；計畫寫的「測試內已斷言」是錯的，**主對話錯誤**。evidence 文字更正延到本報告。代價：無 |
| GC3 | implementer 實際執行的是 Sonnet，所以 implementer 的 commit 署名「Claude Sonnet 5.5」；`250dba7` 帶著 Opus 署名，是主對話派工錯誤，不改寫歷史 | P4 先例：不改寫歷史。代價：`250dba7` 的署名與實際執行的模型不符（§2.4 第 1 點） |
| T2-a | `test_member_auth.py:343` 的 `a!b`→400 特殊字元斷言屬於被取代的舊規則：改為 `"名\u0007"`→400 控制字元，並釘住 `a!b`→200 | R4。代價：符號會被存入（只用於顯示，以文字渲染） |
| T2-b | 錯誤訊息的呈現：`pay.vue`、`userprofilePage.vue` 用 `Swal.fire`，註冊頁沿用 `.error_msg` | 這兩頁沒有現成的 inline 錯誤元件。代價：只影響 UX |
| T2-c | Google 名字：20 字截斷後再去空白；不足 2 字則用 email 前段（移除 Cc、取 20 字、去空白）；補測試 | 計畫沒寫這個情況。代價：無 |
| T2-d | profile schema 拿掉 `.empty('')`；`test_profile_saves_trimmed_name` 標回歸測試；lock-order 行號平移另開 commit | 理由與代價：未記 |
| T2-e | 接受：會員資料頁存檔一定送出姓名，所以 P5 之前建立、姓名不合新規則的會員，要先改姓名才能改偏好設定 | 舊規則是 2–5 字（新規則 2–20 的子集），所以只有 P5 之前的 Google 會員會受影響；乾淨 volume 沒有這種人。代價：舊 Google 會員存偏好時會看到姓名錯誤（附錄 B.1） |
| T3-I1 | 計畫的集合式狀態斷言是計畫缺陷，改為逐筆對應 dict | spec §4.2 的對應必須被釘住；**計畫錯誤，主對話錯誤**（§2.4 第 3 點）。代價：無 |
| T3-fold | 一併補：詳情 401、自己不存在的訂單 404、已退款訂單 payable；`lock-order.md` 檔頭註明 `trade.js` 基準 | 理由與代價：未記 |
| T4-I1 | 折扣類型顯示 `none` 原字串的缺陷必須修（opus、fable 都列 Important） | 兩位審查員共同；代價：未記 |
| T4-I2 | `?tab=constructor`／`__proto__` 造成空白頁，必須修，用 `Object.hasOwn`（fable Important、opus Minor） | 修起來便宜，且違反共用約定「未知 → info」。代價：未記 |
| T4-fold | 11 筆訂單的分頁 E2E 釘住 `limit=10`（F13）；明細載入失敗還原 `openDetailId`；`HeaderComponent.vue:69` prettier | 理由與代價：未記 |
| T4-M2 | 側欄切換用 `router.replace`（不留瀏覽紀錄）是計畫明定的做法，保留 | 計畫規定。代價：返回鍵會直接離開會員中心（附錄 B.1） |
| T5-8 | F10 的 spec §12 偏離記錄（前端寫死 10%）延到 Task 10 | 代價：無 |
| T5-I1 | 負點數 E2E 必須修：`expect_response` 等 `pointslevel`＋等級卡片 `v-if levelLoaded` | 原測試在 API 回應前就通過（opus I、fable I1）。代價：未記 |
| T5-I2 | `db-contract.md` 的 :1304／:1307 現在就修，:1363／:1699 註記「P5 Task 5 已實作」 | fable Important、opus Minor；修起來便宜，符合 GC11 精神。代價：未記 |
| T5-fold | prettier 只重排新加的模板區塊 | 避免整檔雜訊。代價：未記 |
| T6-1 | 搜尋用 `ILIKE` 部分比對、地區驗證用等值比對，這個不一致接受 | 前端從地區下拉選取，使用者不會自己輸入。代價：直接呼叫 API 且傳部分名稱的客戶端會得到 400 |
| T7-1 | 保留收藏 POST 的有限重試（≤3 輪）：`ON CONFLICT DO NOTHING` 後 SELECT 查不到時（剛好被同時刪掉）回到 INSERT；必須寫進 lock-order §11 | 重新 INSERT 是使用者的意圖，且有上限。代價：多一條程式路徑 |
| T7-C1 | §11 寫成「最多 3 輪（首次加 2 次重試）」，與程式的 `attempt < 3` 一致；修 `collection.js:73` 註解；§11 基準 `ab52b9a` | 雙審共同 Critical（文件與程式不一致；fable 另指出重試次數與註解不符）。代價：未記 |
| T7-I1 | 新增決定性測試（另一條連線 INSERT 不提交、輪詢 `pg_stat_activity` 確認 POST 在等鎖、提交後 200 且同一 `favorite_id`），8 條執行緒的測試保留並加 Counter 訊息 | fable Important：原併發測試是機率性的。代價：未記 |
| T7-I2 | 詳情 `favorite_id` 測試參數化涵蓋 travel／hotel／food／spot | fable Important：原本只涵蓋 travel 分支。代價：未記 |
| T7-fold | `db-contract.md` 的 `user_favorite` 一節改為現況（:1440、:1446–1450） | 理由與代價：未記；殘留的舊行號在 Task 10 補（見 §1.11） |
| T8-1 | 行程頁的愛心放在價格旁，不放標題旁 | 固定 header 在捲動時遮住標題，點擊被攔截。代價：只影響版面偏好 |
| T8-I2 | 以 opus 實際執行的探測為準（500 且沒有 CORS 標頭時畫面仍顯示「伺服器錯誤」），fable 的「未執行的推論」不採；但兩位都同意斷言必須釘住文字「伺服器錯誤」 | 實測優先於未跑的推論；fable 事後執行並撤回該主張。代價：無 |
| T8-I1 | 主線 E2E 必須走 UI 登入 | spec §0 第 1 步是「登入」，初版注入 token（fable I-1）。代價：未記 |
| T8-fold | 訪客點愛心斷言沒有送出 POST；已收藏的行程載入即亮（`aria-pressed=true`）；搜尋頁點愛心後 URL 不變；eslint 未用的 catch 變數 3 處；移除未用 import；`api.js:781` 註解；無效 `:disabled` 樣式 | 理由與代價：未記 |
| T9-I | `lock-order.md`「檢查結果」改為四處反向（補例外 A）、「已知缺口」的 NOWAIT 1.5 秒那句改寫、檔頭改成逐檔核對後的基準 | 雙審的 Important：文件寫三處、實際四處（opus、fable）；fable 另指出已知缺口過期與檔頭基準不一致。代價：未記 |
| T9-fold | summary 在本次呼叫轉逾時時，回應的 `discount.type`／`summary.discount_price` 為 null（與 DB 一致）；新增「已付款訂單過期不清折扣欄位」的直接測試 | 一致性；代價：未記 |
| T10-1 | 總覽的 base 是 `025556b`（merge-base），報告只用這一個 hash | 派工文字寫了另一個 commit，是**主對話的錯誤**；`git merge-base` 與 ledger 的 Task 0 BASE 都是 `025556b`。代價：初稿並列兩個候選，增加一輪更正 |
| T10-2 | 計畫 Step 3 的「`down -v` 後連跑兩次」延到合併前執行 | 需要使用者執行 `docker compose down -v`。結果：使用者執行 `down -v` 後，重建並連跑兩次 `scripts/ci.sh`，兩次都是 959 passed、exit 0，pytest 分別 227.80s 與 224.75s（[clean-run-1.txt](evidence/phase-5/clean-run-1.txt)、[clean-run-2.txt](evidence/phase-5/clean-run-2.txt)）。代價：合併前多一輪等待 |
| FW | 單一修正波：通知設定併發測試（8 執行緒、各自 session、Barrier 與 join 帶 timeout，新增 price-tracking 版）、`frontend/src/utils/api.js` 的 `delete_favorite` 把 DELETE 404 視為已取消（`FavoriteHeart.vue` 未改）、折扣「無」的空泛斷言、`test_trade_cart` 加 timeout、smoke 收藏 `total ==`、`collection.js` 空列表 `total`；報告更正（兩方清單的聯集）、spec §12 第 17／18 點去重並補 T9-fold、P4 spec `:193` 補註、lock-order §11 測試清單、`computePayable` 讀取快照的說明 | 最終雙審：兩方都判定程式可合併；fable 要求合併前修 I-1（通知設定併發測試）與 I-2（報告事實錯誤），opus 也要求報告更正並要求 #27 修正或重裁。代價：未記 |
| FW-2 | 其餘 27 條 deferred minor 留到 P6（列在附錄 B）；db-contract 殘留的過期引用留到 P6 | 範圍控制。代價：文件漂移多留一個階段 |

**Task 9 的 mutation 紀錄（F23）**：補丁拿掉 `_assert_waits_on_cart_not_cart_item` 中 holder 的 `FOR UPDATE`（patch 存在 scratchpad `mutation.patch`）；`uv run pytest tests/test_trade_payment.py -k locks_cart_before_cart_item` → 3 failed（30.55s，10 秒輪詢逾時）；還原後 `git status --short` 只剩既有的 `?? .claude/`。

### 2.3 Fable vs Opus review 對照

| Task | opus | fable | 差異與處理 |
|---|---|---|---|
| 0 查證 | Approved（I-1：summary 說全部相符但狀態 0 沒被斷言） | Approved（同一項列 Minor M1） | 同一發現，嚴重度不同；T0-I1 接受 |
| 1 V6 | Approved（0 C／I，7 minor） | Approved（0 C／I，7 minor） | 兩方都同意 5 個實作者偏離；**共同**指出 `automation.js`、`collection.js` 在 T6／T7 之前仍是先查再寫（併發下 23505／500），列為「T6、T7 不得視為已修」 |
| 2 姓名 | Approved（7 minor） | Approved（10 minor） | **共同** minor：sweep 的 collect 略過陣列、Google e2e 的回歸標示不精確、Cf／零寬字元通過（spec 只要求 Cc）。T2-e 為兩方共同提出（⚠️） |
| 3 我的訂單 | Needs fixes（I1：狀態對應測試只比集合） | Needs fixes（同一項，計畫指定） | 共同；修正輪 1 後通過（T3-I1） |
| 4 會員中心分頁 | Needs fixes（I：`none` 原字串；tab 原型鍵為 Minor） | Needs fixes（I-1 tab 原型鍵、I-2 同一個折扣缺陷） | 嚴重度不同的同一組發現；兩方同意 5 個實作者決定；兩方皆指出 Header prettier 新增髒行、F13 未被 E2E 測試 |
| 5 點數與等級 | Needs fixes（I：負點數 E2E 在 API 回應前通過） | Needs fixes（I1 同；**獨有 I2**：db-contract :1304／:1307 過期） | fable 獨有 I2（opus 列 Minor）；修正輪 1 |
| 6 通知設定 | Approved（9 minor） | Approved（10 minor） | **共同** minor：reload 未等 `domcontentloaded`、GET 的 null 往返 PATCH 回 400、連續 PATCH 無回滾（計畫規定）、碼位排序。併發測試只有 2 條執行緒（鑑別力約 60%）列待加強 |
| 7 收藏後端 | Needs fixes（**C**：lock-order §11 缺重試、檔頭基準） | Needs fixes（C1 同＋重試次數與註解不符；**獨有 I1**：併發測試機率性；**獨有 I2**：詳情 `favorite_id` 只測 travel） | 程式本身兩方都判正確；修正輪 1（T7-C1、T7-I1、T7-I2） |
| 8 收藏前端 | Approved（10 minor；實測 500 無 CORS 時仍顯示「伺服器錯誤」） | Needs fixes（**I-1**：主線注入 token；**I-2**：500 路徑未驗，只靠推論） | I-1 成立（T8-I1）；I-2 以 opus 的實測為準，fable 事後執行後撤回 CORS 主張（T8-I2） |
| 9 P4 留下的項目 | Approved（1 Important：lock-order 說 3 處反向、實為 4 處） | spec 符合／Needs fixes（同一項＋**獨有**：已知缺口過期、檔頭基準不一致、cart.js 行號差 1） | fable 的「cart.js 行號差 1」經核對後撤回；其餘併入 T9-I；修正輪 1 |
| 10 文件與報告＋整條分支最終審查（三個 repo 的 `phase-5`） | 程式可合併，0 Critical／Important；報告有事實更正，且 #27（通知設定併發測試，只有 2 條執行緒）要修或重新裁決 | 合併前須修：I-1 通知設定併發測試（擋合併）、I-2 報告的事實錯誤；另在 `3d89477` 以保留 volume 重跑 `scripts/ci.sh`：957 passed、213.95s | 兩方都認為程式可合併；兩方合計 36 條 minor：1 條必修（ledger L109，即通知設定併發測試）、約 8 條已結案、其餘留 P6（Ruling FW-2）。單一修正波（Ruling FW）：通知設定併發測試改 8 執行緒並新增 price-tracking 版、愛心取消 404 視為已取消、折扣「無」斷言改精確比對、`test_trade_cart` 加 timeout、smoke `total ==`、`collection.js` 空列表 `total`，以及報告與文件更正 |

**實作者自己的觀察（非 reviewer 或使用者的結論）**：兩位審查員的共同發現幾乎都是真實缺陷；單方獨有的項目中，fable 的多半成立（T5-I2、T7-I1、T7-I2、T8-I1），但也有一次主張經實測後被撤回（T8-I2，CORS）與一次行號主張被撤回（T9）。opus 在 Task 8 以實際執行的探測推翻 fable 未執行的推論。

### 2.4 AI 出錯／人介入紀錄

1. **主對話的錯誤：派工署名（Task 0）**：派工時叫 implementer 用 Opus 署名，但實際執行的是 Sonnet。`250dba7` 的 `Co-Authored-By` 因此不正確；依 P4 先例不改寫歷史，後續 Task 一律寫實際執行的模型（Ruling GC3）。
2. **主對話的錯誤：計畫 Task 0 Step 7 的不實陳述**：計畫（由主對話撰寫）寫「-1 → 0 → 1（測試內已斷言）」，這句不正確，實際測試沒有直接斷言狀態 0（T0-I1）。
3. **主對話的錯誤：計畫 Task 3 的斷言沒有鑑別力**：計畫（由主對話撰寫）中狀態對應的斷言只做集合比對，換成任何一對一的錯誤對應都會通過；審查抓到，改為逐筆比對（T3-I1）。
4. **紅燈不獨立或不是鑑別力證據**：Task 1 的 `test_alice_auto_settings_merged`（helper 解析錯誤，非行為錯誤）、Task 6（併發測試約 60%）、Task 7（併發測試對舊程式本來就會紅）。報告如實記錄，沒有補造證據。
5. **計畫的行號與預期值過期**：計畫寫 alice 的 `auto_setting` 最終 id 是 `1111aaaa…`，實際被 `remap_ids` 換成 `d47d7d56-…`（Task 1）；計畫 Task 10 Step 2 的 `docs/db-contract.md` `:1339`、`:1537` 是起草基準的行號，後續 Task 已使文件位移，本次以內容定位。
6. **實作者報告與事實不符，由審查或自查更正**：Task 8 初版報告沒有寫「主線 E2E 注入 token」，也誤寫「500 無 CORS 標頭時 axios 看到網路錯誤」（第 1 輪更正）；Task 7 初版報告把「10 次全紅」當成鑑別力證據（同一份報告自行更正為不是鑑別力證據）。
7. **審查員之間的主張衝突**：Task 8 的 CORS 路徑（以實測裁決）、Task 9 的 cart.js 行號（核對後撤回）。
8. **主對話的錯誤：總覽起點寫錯（Ruling T10-1）**：派工文字把總覽的 base 寫成另一個 commit；實際是 `025556b`，初稿因此並列兩個候選，最終審查後更正。
9. **使用者介入點**：Task 1 的 `docker compose down -v`（使用者已執行）；Task 10 Step 3 的 `down -v` 已由使用者執行，連跑兩次的結果見 §3.3（Ruling T10-2）；合併、tag、push 不在計畫內（Step 5）。
10. **無法在環境內執行的檢查**：frontend 的 eslint 在 Task 5、Task 6 因本機未安裝套件而無法執行；Task 8 以 `docker compose exec -T frontend npx --no-install eslint` 對本次檔案執行，沒有新問題，並發現兩個既有錯誤（附錄 B.3）。

## 3. 測試方法

### 3.1 測試分層（總 spec §4.2 四層）

下表的數量取自 `scripts/ci.sh`（`pytest -v`）PASSED 行（[task-10-ci.txt](evidence/phase-5/task-10-ci.txt)），依檔案分組（檔內有些測試跨層，以主要目的歸類）。

| 層 | 檔案（passed 數；P5 新增檔標 ★） | 重點 |
|---|---|---|
| API 契約 | ★`tests/test_member_orders.py`（24）、★`tests/test_member_points.py`（11）、★`tests/test_member_notify.py`（27）、★`tests/test_member_favorites.py`（27）、★`tests/test_name_rule.py`（17）、`tests/test_member_auth.py`（86，含 R6 與 `test_point_records_hide_signup_zero_row`）、`tests/test_google_login.py`（30）、`tests/test_validator_sweep.py`（23；P4 結束時為 16）、`tests/test_validator_messages.py`（80） | 每支 API 的正常、驗證錯誤、非自己資源回 404、狀態碼；驗證訊息不洩漏參數名；姓名規則的 code point 邊界 |
| 安全／越權 | `tests/test_member_orders.py`（非本人 404、未登入 401、admin 403）、`tests/test_member_favorites.py`（非本人刪除 404）、`tests/test_member_points.py::test_point_records_other_user_not_visible`（點數紀錄看不到別人的） | 契約 §4.2 (c) 的紅燈與回歸；擁有者條件寫在 SQL |
| DB 狀態 | `tests/test_migrations.py`（22；P4 為 19）、`tests/test_build_seed.py`（10）、`tests/test_seed.py`（31）、`tests/test_db_contract.py`（45）、`tests/test_views_a／b／c.py`（22／24／13）、`tests/test_trade_cart.py`（14；P4 為 13）、`tests/test_trade_checkout.py`（59；P4 為 54） | V6 三個約束真的擋得住重複；seed 的 `auto_setting` 一人一列；逾時／取消後折扣欄位為 NULL；`tour_*` function 的 `收藏編號` |
| 併發與鎖 | `tests/test_trade_payment.py`（49；notify 併發、鎖順序、簽章）、`test_first_add_concurrently_creates_one_cart`、`test_patch_concurrent_first_write_one_row`、`test_price_tracking_concurrent_first_write_one_row`、`test_concurrent_favorite_same_tour_returns_same_id`、`test_favorite_waits_on_uncommitted_insert_then_returns_same_id`，以及 P4 的鎖順序測試（改為輪詢） | 見 `docs/lock-order.md`「對應的測試」 |
| E2E | ★`e2e/test_member_center.py`（13）、★`e2e/test_favorite_flow.py`（8）、`e2e/test_member_flow.py`（31）、`e2e/test_trade_flow.py`（21）、`e2e/test_product_flow.py`（42）；合計 115 | P5 主線（UI 登入 → 搜尋卡片愛心 → 收藏頁 → 付款 → 我的訂單 → 點數紀錄 → 取消收藏）、`?tab=`、繼續付款、逾時與處理中的訂單、負點數顯示 0、通知設定存檔後重新整理 |

### 3.2 值得一看的技巧

1. **決定性的鎖等待測試**（Task 7、Task 9）：另一條連線先 INSERT 同一組 `(user_id, tour_id)` 但不提交，輪詢 `pg_stat_activity` 確認 POST 真的卡在鎖上，才提交並斷言回 200 與同一個 `favorite_id`；取代「多條執行緒同時打、看運氣」的機率性測試（8 條執行緒的版本保留當補充，對先查再寫的變異版 10 次中 8 次紅）。
2. **用變異版驗證測試的鑑別力**（F23）：Task 7 把 POST 改回先查再寫、Task 9 把 holder 的 `FOR UPDATE` 拿掉，確認對應測試真的會紅，並在還原後以 `git status` 確認工作樹乾淨。
3. **期限與狀態由後端算**：列表與明細回 `can_continue_payment`／`is_overdue` 兩個布林，前端只讀布林；測試用 DB 時間（改 `created_at`）製造逾時，不用真的等。
4. **以 `page.expect_response` 等 API**（GC20）：負點數 E2E 原本在 API 回應前就通過，這是這類 E2E 最容易犯的錯，修正後等級卡片在載入完成前不渲染，測試明確等 `pointslevel` 回應。
5. **容器內的惡意輸入矩陣沿用**：新 validator 加進 `SWEEP_JS` 與原始碼掃描清單（GC14）。
6. **seed 帳號唯讀**：需要寫入的測試一律 `make_user`；本階段新增的 GET 可以對 seed 帳號呼叫。

### 3.3 測試數量與 CI 結果

| 次數 | passed | xfailed | skipped | pytest 耗時 | 牆鐘 | exit code |
|---|---|---|---|---|---|---|
| 乾淨環境第 1 次：使用者執行 `down -v` 刪除 volume 後，`docker compose up -d --build` 重建（映像為快取），Flyway 在新的 pgdata 上套用 V1–V6，接著執行 `scripts/ci.sh`（截至程式碼 HEAD：總覽 `31863c7`、backend `2f19285`、frontend `89b2282`；[clean-run-1.txt](evidence/phase-5/clean-run-1.txt)） | **959**（844＋115） | 0 | 0 | 227.80s | 235s | 0 |
| 乾淨環境第 2 次（保留 volume；[clean-run-2.txt](evidence/phase-5/clean-run-2.txt)） | **959**（844＋115） | 0 | 0 | 224.75s | 231s | 0 |
| 修正波後、`down -v` 前（保留 volume，[task-10-ci.txt](evidence/phase-5/task-10-ci.txt)） | 959（844＋115） | 0 | 0 | 215.04s | 未計 | 0 |
| 修正波前（`3d89477`，保留 volume，[task-10-ci-before-fixwave.txt](evidence/phase-5/task-10-ci-before-fixwave.txt)；fable 重跑 957、213.95s） | 957（843＋114） | 0 | 0 | 206.73s | 3m33s | 0 |
| GitHub Actions `phase-5` 分支 run 45778412244（推送後首次 CI） | **959** | 0 | 0 | 175.46s | — | 0 |

測試數量變化：**798 passed（P4 最終）→ 959 passed**（乾淨環境兩次皆 959），淨增 161 個（修正波新增：通知設定 price-tracking 併發測試 1、愛心取消 404 的 E2E 1）。各 Task 結束時 ledger 記錄的 passed 數：Task 1：715（`tests/`，`down -v` 之後）、Task 2：741＋e2e 94、Task 3：765→768、Task 4：tests 768＋e2e 101→103、Task 5：888、Task 6：917、Task 7：834（tests）／941→945（全套）、Task 8：952、Task 9：842＋114→843＋114（957）、Task 10：957（修正波前）→ 959（修正波後）。

## 4. 操作指南

### 4.1 切到這個版本並啟動

```bash
git clone https://github.com/nohungry/tripeasy.git && cd tripeasy
git clone -b "$(grep BACKEND_REF refs.env | cut -d= -f2)" https://github.com/nohungry/tripeasy-backend.git backend
git clone -b "$(grep FRONTEND_REF refs.env | cut -d= -f2)" https://github.com/nohungry/tripeasy-frontend.git frontend
scripts/ci.sh        # 啟動全部服務並跑測試
```

目前 `refs.env` 是 `BACKEND_REF=phase-5`、`FRONTEND_REF=phase-5`（合併後分支改指向同名 tag，同 `phase-4.md` §4.1 的說明；Step 5 之後確認）。**從舊 volume 升級要小心**：seed 的 `auto_setting` 改了（alice 4 → 3 列），既有 volume 若 alice 仍有兩筆，V6 預檢會失敗，要 `docker compose down -v`。`.env` 沒有新增設定。

### 4.2 測試帳號與 seed 的使用

seed 帳號（密碼 `Tripeasy123`）：`alice@example.com`（`User`）、`bob@example.com`（`admin`）、`carol@example.com`（`User`）。**seed 帳號唯讀**（GC10）：不要用 alice／bob／carol 做收藏 POST／DELETE、通知設定 PATCH、加購物車、建單、付款、summary，否則 `tests/test_seed.py` 的計數與餘額斷言會紅，且 seed 的未付款訂單 #16、#17 會在第一次被查詢時轉成逾時（P4 報告 §4.2）。本階段新增的 `GET /user/orders*`、`GET /user/points/records`、`GET /pointslevel`、`GET /allnotifi-settings`、`GET /collection/info/all` 是唯讀，可以對 seed 帳號呼叫（注意 bob 是 `admin`，會員端點對他回 403）。

### 4.3 手動操作路徑（會員中心）

> **未實測**：本節是依 e2e 測試與程式碼整理的操作說明，**這次沒有手動實跑**（P4 報告 §4.3 有手動實測；P5 初稿未做）。每個步驟列出覆蓋它的 e2e 測試，供審閱時對照。需要手動實跑時，請用自建帳號（email 以 `e2e-` 開頭、`@example.com` 結尾，下次 pytest 開頭會被 purge），不要用 seed 帳號。

1. **登入後的入口**：Header 的會員選單（桌機）與手機選單，桌機會員選單登入後才顯示「會員資訊、會員等級、個人偏好設定、個人訂單查看、收藏」（`e2e/test_member_center.py::test_header_links_open_tabs`）；手機選單的「購物車」連結未登入也看得到，登入後才多出會員連結。**手機選單的連結沒有 e2e 測試**（附錄 B.2）。
2. **會員中心四個分頁**：網址 `#/admin/userprofile?tab=info|level|preference|orders`，對應「會員資訊／會員等級／個人偏好設定／個人訂單查看」；未知或缺少的 `tab` 回到 `info`（含 `constructor`、`__proto__`）。側欄切換用 `router.replace`，不留瀏覽紀錄（計畫明定）。覆蓋：`test_profile_tab_from_query`、`test_admin_automatic_redirects_to_preference_tab`。
3. **會員等級分頁**：顯示等級、點數餘額（負數顯示 0）、可用優惠券、購物回饋比例（前端寫死 10%，見附錄 B）與點數紀錄（購物回饋、點數折抵、退款收回回饋、退款退還折抵；新註冊會員的 `+0` 紀錄不顯示）。覆蓋：`test_level_tab_shows_points_and_records`、`test_level_tab_negative_points_shows_zero`。
4. **個人偏好設定分頁（通知設定）**：「出發前提醒」開關；「價格追蹤」開啟時選國家、地區（下拉來自上架行程）與預算上限；存檔後重新整理設定仍在。覆蓋：`e2e/test_member_center.py::test_notify_settings_persist_after_reload`、`test_delisted_saved_region_shown_with_note`。
5. **個人訂單查看**：列表（每頁 10 筆）顯示全部狀態；點開看明細；待付款且未逾時的訂單有「繼續付款」，導到 P4 的結帳頁；付款處理中的訂單顯示「付款處理中」且沒有「繼續付款」。覆蓋：`test_orders_tab_lists_paid_order_with_detail`、`test_orders_paging_uses_limit_10`、`test_continue_payment_goes_to_pay_page`、`test_overdue_pending_order_has_no_continue_button`、`test_orders_tab_empty`。
6. **收藏**：搜尋結果卡片、行程頁（價格旁）與首頁的愛心可以收藏／取消（訪客點愛心不會送出請求）；`#/admin/collect` 的收藏頁列出收藏（最新 100 筆）、可取消、可點進行程頁，已下架的行程有標籤。覆蓋：`e2e/test_favorite_flow.py::test_p5_main_flow`（走 UI 登入）、`test_tour_page_heart_toggles`、`test_guest_heart_goes_to_login`、`test_unlisted_favorite_is_marked_and_removable`、`test_collect_page_empty`。
7. **姓名**：註冊、會員資料、結帳收件人都是 2–20 個字（去頭尾空白後，允許空白與符號，拒絕控制字元）。覆蓋：`e2e/test_member_flow.py::test_register_name_too_long_shows_message`、`test_profile_name_too_long_shows_message`、`test_pay_name_too_long_blocked`。

## 附錄

### A. 變更檔案清單

統計基準（截至程式碼 HEAD：總覽 `31863c7`、backend `2f19285`、frontend `89b2282`；總覽數字以 `git diff --shortstat 025556b..31863c7` 計算，不再隨報告本身的 commit 更新）：總覽 `025556b..31863c7`（31 個 commit、56 個檔案，+9430／−170，含 21 個 evidence 檔、報告與最終修正波的測試）、backend `main..phase-5`（36 個檔案，+771／−439，10 個 commit）、frontend `dev..phase-5`（12 個檔案，+923／−65，9 個 commit）。以下略去 evidence 檔案（`docs/reports/evidence/phase-5/`）。

**backend**（`github.com/nohungry/tripeasy-backend`，`main..phase-5`）
- 新增：`migrations/V6__p5_member_center.sql`、`src/controllers/{orders,points}.js`、`src/middlewares/{orders,points}/index.js`、`src/routes/{orders,points}.js`、`src/utils/{nameRule,orderStatus}.js`、`src/utils/Validator/{orders_Validator,paging_Validator}.js`
- 修改：`migrations/R__views_functions.sql`（四個 function 加 `收藏編號`）、`src/controllers/{automation,cart,checkout,collection,newebpay,product,purchases,userProfile,userinfo}.js`、`src/middlewares/{automation,collection,purchases,userProfile,userinfo}/index.js`、`src/routes/{automation,collection}.js`、`src/server.js`（掛載 orders、points）、`src/utils/trade.js`（`clearOrderDiscount`、`paymentInProgressSql`、`orderDeadlineSql`）、`src/utils/Validator/{automation,checkout,collection,purchases,userInfo,userprofile}_Validator.js`（含 `checkout_Vaildator.js` 的原拼法）

**frontend**（`github.com/nohungry/tripeasy-frontend`，`dev..phase-5`）
- 新增：`src/components/FavoriteHeart.vue`
- 刪除：`src/views/admin/manage/automaticSetting.vue`（空頁，路由改 redirect）
- 修改：`src/components/HeaderComponent.vue`、`src/router/index.js`、`src/utils/{api,function}.js`、`src/views/HomeView.vue`、`src/views/admin/{collectPage,userprofilePage}.vue`、`src/views/front/{pay,searchPage,tourPage}.vue`

**總覽 repo**（`025556b..31863c7`）
- 測試新增：`tests/test_member_{orders,points,notify,favorites}.py`、`tests/test_name_rule.py`、`e2e/test_member_center.py`、`e2e/test_favorite_flow.py`
- 測試修改：`tests/{conftest,db_contract,test_api_smoke,test_async_errors,test_build_seed,test_google_login,test_member_auth,test_migrations,test_seed,test_trade_cart,test_trade_checkout,test_trade_payment,test_trade_refund,test_validator_messages,test_validator_sweep,test_views_a}.py`、`e2e/{conftest,test_member_flow}.py`
- Seed／設定：`db/seed-build/build_seed.py`（`merge_duplicate_auto_settings`）、`db/seed/R__seed.sql`、`refs.env`
- 文件：`docs/db-contract.md`、`docs/lock-order.md`、`docs/superpowers/specs/2026-11-24-p4-trade-design.md`（刪註解編號對照）、`docs/superpowers/specs/2026-11-26-p5-member-center-design.md`（§12 補第 18 點）、`README.md`（版本對照表）、本報告（計畫檔 `docs/superpowers/plans/2026-11-26-p5-member-center.md` 與 spec §12 的前段在 `025556b` 之前就已在 `main`，不在 `025556b..153f4ba` 的範圍內）

### B. 已知限制與待辦

**B.0 使用者已做的決定與延後項目**
- **會員手動取消訂單**【使用者定】：留到 P6，和後台的訂單管理一起做。
- **會員等級升級規則**【使用者定】：留到 P6 的後台會員管理再決定；P5 只顯示 seed 的等級，**升級規則未實作**。
- **實際寄送通知、站內通知、價格追蹤比對**【使用者定】：屬於 P6 的排程；P5 的通知設定只儲存、不寄送。
- **「同意接收促銷訊息」勾選框**【Claude 定】：不還原（後端沒有對應欄位，勾了也沒有作用），在 P5 結案；若錯，P6 要另外加欄位與 UI。
- **Facebook 登入的空路由**（`routes/userinfo.js:19`）：不動。
- **`/admin/personalOrder` 仍是空頁**（D9；`router/index.js:128-131`）：P5 不動。
- **R2**：價格追蹤以上架行程的英文地區為準；中文 `country`／`region` 表本階段未使用（P3 N5 留 P6）。
- **P4 報告的矛盾（P5 spec §7.5）**：P4 報告 :191 寫負點數「待使用者決定」，:387、:397 寫已裁決；以已裁決為準（會員中心一律顯示 0），P4 報告不改。
- **回饋比例前端寫死 10%**（F10；P5 spec §12 第 18 點）：API 沒有輸出比例；`user_level.benefits`（V1 `TEXT NULL`）雖存在、seed 有值，但 backend 與 frontend 的 `src` 都沒有任何程式引用它。若之後各等級比例不同，要同時改 API 與前端（建議 P6 隨升級規則一併處理）。

**B.1 已知且已接受的行為**
- **Task 2 的 Ruling T2-e**：P5 之前建立、姓名不合新規則的會員，存偏好設定時會被擋下（會員資料頁存檔一定送出姓名，要先改姓名）。舊規則是 2–5 字（新規則 2–20 的子集），所以只有 P5 之前的 Google 會員會受影響；乾淨 volume 沒有這種人。
- **側欄切換用 `router.replace`**（T4-M2）：不會留下瀏覽紀錄，返回鍵會直接離開會員中心；這是計畫明定的做法。
- **eslint 有兩個既有錯誤**，位置在 `frontend/src/utils/api.js:218`（`parseError` 未使用）、`:657`（`no-useless-catch`）；非 P5 新增，未處理（Task 8）。eslint 在 Task 5、6 因本機未安裝套件無法執行。
- **ILIKE 搜尋 vs 等值驗證**（T6-1）：搜尋 `Jap` 能搜到日本，但價格追蹤存 `Jap` 會被 400；前端從下拉選取，不受影響。
- **收藏列表上限 100 筆**（F4）：超過時前端提示只顯示最新 100 筆。
- **前端連續兩支 PATCH 不回滾**：第二支回 400 時第一支已寫入（計畫規定）。
- **`now() >= deadline` 與 `pastOrderDeadline` 的 `deadline < now()` 在 1 微秒邊界不同**（F1 字面）。

**B.2 ledger 的 `minor (deferred)`，依類別整理（建議處理時機標在最後）**

**已結案**：最終審查把兩方的 36 條 minor 整理成清單（已在 Task 10 或最終修正波結案的有下列各項；審查員清單的編號不在報告內重複，直接描述內容），包括：通知設定併發測試補強（L109，唯一必修項）、收藏 DELETE 404 視為已移除（`FavoriteHeart`／`collectPage` 共用的 `delete_favorite`）、訂單折扣「無」斷言改用 testid 精確比對、`test_trade_cart` 的 barrier／join timeout、smoke 收藏 `total ==`、`collection.js` 空列表 `total` 用查到的值、T1 與 T7 的 lock-order 測試清單（`test_first_add_concurrently_creates_one_cart`、§11 的決定性測試）補齊、P4 spec `:193` 補註、spec §12 第 17／18 點去重並補 T9-fold、db-contract 被點名的行號與敘述。以下**其餘 27 條依 Ruling FW-2 全部留到 P6**（db-contract 殘留的過期引用也是；代價：文件漂移多留一個階段）。另補一條：會員端讀取（訂單列表／明細）中，`computePayable(pool, …)` 內的多條 `pool.query` 不在同一個快照裡，結果只用於顯示，不影響寫入路徑，留 P6。

*交易／資料*
- `cart.js:34` 在 INSERT 與 SELECT 之間 cart 被刪的話 `rows[0]` 為 undefined（目前沒有刪除路徑）（T1）→ P6 若加刪除路徑時處理。
- V6 的去重與預檢 SQL 沒有被任何測試執行過（fable 手動模擬過）（T1）→ P6 或下次 migration 前補。
- tie-break 沒有測「兩邊字面相等」與「字面＋`CURRENT_TIMESTAMP` 混合」；`updated_at` 以字串比較；`build_seed.py` 註解 :429 描述錯誤（T1）。
- 合併函式的單元測試兩筆都把贏家放最後（take-last 變異版會通過），應加「較新者在前」案例（T1）。
- 列表的 `COUNT(*)` 與資料／`payments[]` 是不同語句、不同快照；`ORDER BY created_at` 沒有 tie-break；`first_item` 可能為 null（T3、T5、T7）→ P6（後台訂單管理）時一併處理。
- 通知設定：關閉狀態下 null／`''` 欄位會 400；先讀後 upsert 的競態（無害）；`updated_at` 與 trigger 重複；儲存順序可能先送價格（T6）。
- NULL 與 `'none'` 兩種「無折扣」表示法並存（T9）→ P6。
- 取消路徑的點數釋放沒有測試（T9）。
- `userinfo.js` 的 Google 登入 `FOR UPDATE` 會員列、`admin.js:274` 解除優惠券綁定可刪掉被保留的券、checkout 讀 `cart_item` 不加鎖等 P4 B.4 項目沿用，P5 沒有處理（→ P6）。

*測試穩定度與品質*
- 通知設定的併發測試（T6 原本只有 2 條執行緒、鑑別力約 60%）：**已在最終修正波補強**，改為 8 條執行緒、各自 session、Barrier／join 帶 timeout，並新增 price-tracking 端點版；mutation（改回先查再寫）各跑 10 次，早期提醒 9／10 紅、price-tracking 8／10 紅（[task-10-notify-mutant.txt](evidence/phase-5/task-10-notify-mutant.txt)），還原後 10 次全綠。
- `test_trade_cart` 的併發測試 import 在函式內（T1；barrier／join 的 timeout 已在最終修正波補上）。
- 收藏測試：「single response」不是決定性測試、cap 測試只比對頭尾、跨使用者搜尋的 `favorite_id` null 未測、`test_async_errors` 依賴購物車的 NUL 缺口、`lang` 400 只被 sweep 涵蓋、lock-wait 測試的 `pool.shutdown(wait=False)`／`Api` 未關閉／以 `LIKE` 比對 SQL 文字／匯入私有 `_db_params`（T7）。
- 點數紀錄：優惠券列表顯示未測、Api session 沒關（應匯出 `api` fixture）、`points.paging` sweep target 與 `paging` 重複（計畫規定）、`:key=index`、`limit=10` 沒有 E2E、`1ce1786` 訊息缺標示（T5）。
- 訂單：付款期限文字、手機連結、`tab=info` 連結、`first_item` null 文字、orders 401 導回都未測；coupon 明細測試 teardown 沒有還原券狀態（T4）。
- Task 4 的 E2E 從 `test_trade_flow.py` 匯入私有 helper，應移到 conftest；`wait_for_url` 預設等 load（與既有一致）（T4）。
- 通知設定 E2E：reload 只等設定、沒等地區；下架地區重存沒有 DB 斷言；缺「國家上架、地區下架」案例；固定的 `p5land`／`p5city`（T6）。
- Task 2：碼位鑑別力弱（註冊 10／21 emoji 與 Google 長名 E2E 用 BMP 字元，應改 `"😀"*20/25`）；sweep 的 collect 略過整個陣列（應遞迴進元素）且 de66d10 把測試 harness 的改動放在 `docs:` commit；回歸註解不精確；email 前段超過 20 字的截斷未測；1 字下限只在會員資料測；測試耦合（私有 helper、寫死「P0 測試」、sweep 的切片終止字串）；未使用的 import；未去頭尾空白的值在重新載入前仍顯示（T2）。
- Task 3：owner-in-SQL（GC16）無法被測試鑑別、controller 層 AND 使用者編號未測（可考慮原始碼掃描）、欄位值覆蓋不足（`total_price`、`promo_subtotal`、付款結果「處理中／未完成」）、測試寫死 60 分鐘逾時、`computePayable` 的檔頭註解仍寫 client、purchases middleware 沒有 try/catch（既有）。
- Task 0：evidence 是摘要不是原始輸出（見 §1.11 的更正）。
- Task 2：只有 Cf／零寬字元的名字會通過（spec 只要求拒絕 Cc）；頭尾的 `\n` 去掉後通過；截斷可能切開 ZWJ 序列（符合 spec）（T2）。
- Task 6：`ffc47b1` 的 commit 訊息沒有註明那 11 支測試一開始就是綠的（回歸測試，未標示）（T6）。
- Task 9：poll 的過濾沒有比對 query 內容、請求提早完成時仍等滿 10 秒。

*前端*
- 會員中心訂單首次載入失敗時是空白分頁、沒有重試；偏好設定載入失敗同（T4、T6）。
- `TAB_KEYS` 在 data 中未使用、`ordersSeq` 未宣告；在頁內點分頁連結後下拉／導覽沒有關閉（推定）（T4）。
- 收藏：已下架卡片的樣式讓取消按鈕變暗；`<li>` 不能用鍵盤操作；busy 狀態雙擊未測；超過 100 筆的提示未測；已下架行程的 URL 斷言可能立刻通過（T8）。
- 儲存偏好時 null 往返的 PATCH 400；下拉以碼位排序（T6）。
- prettier 對 `api.js`、`userprofilePage.vue` 整檔原本就不合格，P5 只排新增區塊（T5、T6）。
- 前端回饋比例寫死 10%（見 B.0）。

*文件*
- `docs/db-contract.md` 本次只改被點名的位置（`user_level_point_coupon` 欄位表與「列的語意」、`user_favorite` 一節、`:1342`／`:1542`／`:1529` 的過期敘述、`:89`），**同節或他處沒被點名的過期引用沒有改**：`:835`（`userProfile.js:145–147`）、`:1225`（`userProfile.js:156`）、`:1428`（`collection.js:15`）、`:1639`（`userProfile.js:140`）、`:1688`（`userProfile.js:148`）、`:1704`（`collection.js:100`）、`user_level_point_coupon` 一節的 `discounts.js`、`middlewares/*` 行號、「待確認 3」與 §4.1 #39／#40 描述舊行為的 `userProfile.js:153`、`user_favorite` 的 controller 行為 1–3 的歷史行號；`:1304` 的「`SUM`／JSON 字串」推論（P5 Task 5 之後 `userProfile.js:150` 已包 `Number()`）只加註，沒有改寫。契約檔頭 `:11` 宣告的行號基準仍是 backend `phase-1`，只有本次改過的位置標了 backend `d3280ce`。
- `docs/lock-order.md` 的 §10 automation 條目對「UPDATE 分支不做外鍵檢查」是依 Postgres 行為與讀碼推定，沒有另外寫測試。
- P4 報告的矛盾（見 B.0）。

**B.3 建議由 P6 或之後處理的項目（彙整）**
1. P6（後台訂單管理）：手動取消、逾時訂單排程、NULL／`'none'` 兩種「無折扣」表示法統一、列表快照一致性、`admin.js:274` 刪除被保留的券。
2. P6（後台會員管理）：等級升級規則與回饋比例輸出（取代前端寫死 10%）。
3. P6（價格追蹤排程）：通知實際寄送；中英地區對照（P3 N5）；重新評估 ILIKE vs 等值。
4. 下一個有機會動測試的階段：鎖等待測試的 helper 統一（輪詢＋逾時）、E2E private helper 移進 conftest（通知設定併發測試已在最終修正波補強）。
5. P6（使用者已決定的後續）：會員中心側欄切換由 `router.replace` 改為 `router.push`，讓上一頁回到上一個分頁，並補 E2E（目前按上一頁會直接離開會員中心，T4-M2）。
6. P6（修正波複審留下）：通知設定沒有決定性的鎖等待測試（只有 8 執行緒的機率性測試，比照收藏的 `test_favorite_waits_on_uncommitted_insert_then_returns_same_id` 補一支）；`delete_favorite` 把**任何** 404 都視為已取消，路由不存在（例如部署版本不符）時也一樣，應只在回應訊息為「查無此收藏項目」時才視為已取消。
7. P7：保持 backend `TZ=UTC`（P4 R6，沿用）、真實藍新測試商店（P4 B.4a，沿用）。
8. 任何時候都可以做的小項：eslint 兩個既有錯誤（`api.js:218`、`:657`）、前端載入失敗的重試、`first_item` 為 null 的顯示。

**B.4 上鎖順序**
各交易路徑的標準鎖順序、`file:line` 與對應測試見 `docs/lock-order.md`。P5 新增：§9 cart 的 `ON CONFLICT`、§10 通知設定 upsert、§11 收藏新增與刪除（含重試迴圈）、例外 A 的第四處（`clearOrderDiscount`）。
