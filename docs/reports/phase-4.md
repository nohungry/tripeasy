# Phase 4：交易（購物車、結帳、折扣、藍新付款本機模擬、退款 API）
> 2026-11-25（**定稿**；使用者已審閱初稿並核可） · backend tag `phase-4`（待 Step 5：合併、tag、GitHub Actions；起點 `06ded19`，分支最後一個 commit `237f63b`） · frontend tag `phase-4`（待 Step 5；起點 `ae9b824`，分支最後一個 commit `e075222`） · 總覽 tag `phase-4`（待 Step 5；起點 `5377fe9`＝與 `main` 的 merge-base，分支最後一個 commit 見 `git log phase-4`）
>
> 本報告依 `docs/superpowers/specs/2026-10-15-tripeasy-rebuild-design.md` §5 範本與 `docs/reports/phase-3.md` 的格式撰寫。設計見 `docs/superpowers/specs/2026-11-24-p4-trade-design.md`（以下稱「P4 spec」），計畫見 `docs/superpowers/plans/2026-11-24-p4-trade.md`。引用一律以 commit hash、`檔案:行號`、evidence 檔名為出處；查不到的寫「未查證」。
>
> 行號基準：P4 之前就存在的問題，行號取自修正前的 backend `06ded19`（= tag `phase-3`）與 frontend `ae9b824`，並已用 `git show` 逐一核對；沒有核對到的，標明「P4 spec 讀碼推定」。紅燈 evidence 都在 `docs/reports/evidence/phase-4/`（以下省略目錄），已去除絕對路徑。
>
> 資料來源：P4 的 SDD ledger（逐 Task 的派工、審查、裁決紀錄，存在 `.superpowers/sdd/2026-11-24-p4-trade/`，該目錄被 git 忽略，不在 repo 內；以下以「ledger」稱之）、各 Task 的實作報告、`git log`（總覽 `main..phase-4`、backend `main..phase-4`、frontend `dev..phase-4`）與上述 evidence。

## 0. 摘要

P4 的目標：讓「登入 → 詳情頁加入購物車 → 購物車調整數量 → 結帳填資料 → 套用優惠券或點數 → 前往藍新付款 → 付款結果頁」整條主線能從前端完整操作，並讓付款成功時的結算（扣點、優惠券標已用、回饋點數、清購物車）正確、可驗證，同一個通知重送也不會重複結算。這個階段同時是總 spec §4.2「安全／金流」那一層的主戰場。

| 項目 | 結果 |
|---|---|
| 測試數量 | **505 passed、0 xfailed（P3 結束，`phase-3.md` 附錄 C）→ 798 passed、0 xfailed、0 skipped**（**798** 是最終修正波後、保留 volume 的實跑；**782** 是修正波前 `down -v` 乾淨環境連跑兩次的結果，見 §3.3；基準：總覽 `150b95b`、backend `237f63b`、frontend `e075222`）。淨增 293 個測試 |
| xfail／skip | 皆為 0（P3 已清空，P4 沒有新增） |
| 新增服務 | `mock-newebpay`（`node:22-alpine`、不用 npm 套件，`mock-newebpay/server.js`）：假付款頁、驗簽、伺服器端自簽 notify、交易時限 |
| 後端 | 修正購物車／結帳／折扣／藍新 controller 的既有缺陷（§1.1–§1.8）；新增 migration `V5`（§1.9）；結算與鎖順序集中在 `src/utils/trade.js`、`src/utils/newebpay.js`；新增管理員退款 API（§1.10）；藍新 notify／return 對 CORS 白名單的例外（§1.11）；驗證訊息改中文標籤並以共用函式收斂（§1.12） |
| 前端 | 詳情頁加入購物車、購物車頁、結帳頁（`pay.vue`）、付款結果頁（`payResult.vue`）接 API；付款錯誤顯示後端訊息（§1.13） |
| Seed／契約 | 折抵改以促銷後金額為基底、回饋按實付計算（§1.14）；契約 `docs/db-contract.md` 同步 |
| 審查 | 13 個 Task 中 10 個（Task 2、3、5、6、7、8、9、10、11、12）採 reviewer-opus＋reviewer-fable 雙審，Task 1、4 只派 reviewer-opus；總計 14 個修正輪（Task 1、2、3、5、6、9、11 各 1 輪，Task 8、12 各 2 輪，Task 10 共 3 輪；§2.3）。Task 13 的 whole-branch 最終審查（opus、fable 雙審）皆判「With fixes」，其修正已在單一修正波完成（§1.16） |
| 已知限制 | P4 spec §3.1、§5.5 第 4 步（原第 7 步）、seed #16／#17、ledger 標「P5 以後」的項目，見附錄 B |

**修了幾個 bug**：§1.1–§1.8 與 §1.11 是 P3 結束時已存在、P4 修掉的缺陷（連線洩漏、乘法折扣、notify 500、return 卡住、Amt 來自前端、明文參數、重複建單、擁有者檢查缺漏、`discount_price` 寫 0、購物車與訂單的多項資料只取第一筆、CORS 擋掉閘道回呼）；§1.12 的搜尋日期與驗證訊息是 P3 deferred 項目；另外，審查過程中抓到由 P4 自己新寫程式引入的缺陷（死結、鎖順序反向、金額核對順序、輪詢競態，見 §2）；最終審查又補了五項（建單未重驗購物車、重付時券的畫面金額與送出不一致、負積分顯示、付款進行中同折扣被擋、`/payment` 訊息含參數名，§1.16）。

## 1. 問題與修正

每項格式：現象 → 根因（行號）→ 紅燈 evidence → 修正 → 綠燈。「紅燈 commit」是總覽 repo 的 hash，「修正」是 backend／frontend 的 hash。

**先讀這段：紅燈 evidence 的限制**。逐項核對 evidence 與 ledger 後，有幾處紅燈不是「各自獨立、因該 bug 而失敗」，報告如實記錄，不美化：
- `task-1-red.txt`（3 failed，皆 ReadTimeout）是**連帶失敗**：第一個測試把連線池耗盡後，第二、三個測試在第一次呼叫就逾時，並非各自在第 max+1 次失敗。綠燈時三者各自獨立通過。
- `task-8-red.txt`（32 failed、13 passed）：舊版 `POST /newebpay/payment` 一律 500（見 §1.5），而多數 notify／return 測試要先呼叫 `/payment` 才能取得 `MerchantOrderNo`，所以它們是**經由 `/payment` 的 500 連帶失敗**（evidence 中 28 處 `500`）。notify 500 與 return 卡住這兩個缺陷，是靠讀舊碼與資料表定義確認的根因，紅燈 evidence 沒有單獨證明。另外 `test_payment_amount_from_backend` 的紅燈是測試輔助函式的 `TypeError`（`start_payment() got multiple values for argument 'user'`），不是行為錯誤；輔助函式在綠燈 commit `1d2b75b` 修正（ledger 記為 GC3 偏離，9 行）。
- 數個紅燈 commit 中，部分測試**一開始就是綠的**（回歸守門，不是失敗證明），各 commit 訊息與報告皆有註明：例如 Task 4 的 `test_cart_list_uses_live_promo_price`、Task 5 修正輪的三支逾時測試、Task 6 新增的 7 支、Task 9 修正輪的 H1／H2、Task 10 的 J6／J7、Task 11 修正輪只有 M1 真正是紅燈。
- 紅燈 commit 之後又修改測試的有：`65ce429`（修正自己紅燈測試的 PATCH body）、`c1a6050`（購物車合計改用 `data-testid`、人數於 `change` 送出）、`83bc4c9`（`make_user` 預設名稱不合 2–10 字元規則，改填合法全名）、`5575096`（載入失敗測試先關閉 Swal 再斷言）、`1d2b75b`（測試輔助函式參數）。這些都不是為了讓測試通過而放寬斷言，但屬於 GC3 的偏離，列在這裡供審閱。

### 1.1 連線洩漏：購物車與建立訂單（P4 spec §5.1）

**現象**：重複呼叫購物車／結帳寫入 API 約 10 次後，之後所有需要 DB 的請求都卡住。
**根因**：`backend/src/controllers/cart.js:12`、`:94`、`:144` 與 `controllers/checkout.js:12`、`:129` 的 `pool.connect()` 沒有 `release()`；pg Pool 未設 `max`，預設為 10（Task 1 實測確認，迴圈 15 次）。
**紅燈**：[task-1-red.txt](evidence/phase-4/task-1-red.txt)（總覽 `62328a5`，3 failed，連帶失敗，見上）。evidence 當時漏存，由 `5f69931` 補交（未改寫歷史）。
**修正**：backend `bfc641e`：五個 handler 加 `finally { client?.release(); }`。
**綠燈**：3 passed；全套 438 passed。
**未涵蓋（deferred，P5）**：`catch` 內 `ROLLBACK` 若丟例外則 `next` 不被呼叫；`release` 未帶 error 時可能把壞連線放回 pool（ledger Task 1 minor）。

### 1.2 乘法折扣：折扣被「乘」而不是「減」（P4 spec §5.4；契約 #1）

**現象**：優惠券 `discount` 是金額（例如 100 元），舊程式拿它去乘總價，算出的「折扣後金額」數字毫無意義。
**根因**：`controllers/discounts.js:38` `total_price * couponRepo.rows[0].discount`（試算）與 `controllers/checkout.js:153` 同樣的乘法（`PATCH /checkout/preview` 寫入 `orders.discount_price`）。
**紅燈**：[task-6-red.txt](evidence/phase-4/task-6-red.txt)（總覽 `60b5b0d`，15 failed、10 passed；全為斷言失敗）。新增的 7 支測試一開始就綠（回歸測試）。
**修正**：backend `7308881`：折抵改為「減去折抵金額」；`utils/trade.js` 新增 `evaluateDiscount`、`reserveDiscount`；試算 API 不寫 DB、preview 才寫保留；點數只接受 5 的倍數（回 400）、折抵後至少 1 元。後續 `3118941`（已付款／逾時不得取消折扣、付款進行中不得改折扣，回 409，紅燈 `2e017ca`，[task-6-red-guards.txt](evidence/phase-4/task-6-red-guards.txt) 4 failed）、`5c7a847`（試算與 preview 的金額一律來自 `computePayable`、優惠券歸屬改在 SQL 比較，紅燈 `192e34c`，[task-6-red-round1.txt](evidence/phase-4/task-6-red-round1.txt) 1 failed）。
**綠燈**：`test_trade_checkout.py` 46 passed；全套 500 passed。
**審查發現的連帶決定**：取消折扣 API 對已付款訂單會把 `discount_*` 欄位清掉（Task 6 實作者自己指出），裁決加狀態與逾時檢查（§2.2）。

### 1.3 `order_item.discount_price` 沒有促銷時寫 0，應付金額會算出 0 元（P4 spec §16 第 3 點；契約 :212）

**現象**：沒有促銷的項目 `discount_price` 被寫成 0，與契約「沒有促銷為 NULL」不符；如果應付金額直接取 `discount_price`，這類項目會變 0 元。
**根因**：`controllers/checkout.js:28–32` 的 `case when … then 促銷價錢 else 0 end`。
**紅燈**：[task-5-red.txt](evidence/phase-4/task-5-red.txt)（總覽 `b8a48ab`，13 failed、2 passed）中的 `test_create_order_snapshots_promo_price`、`test_payable_treats_zero_discount_price_as_no_promo`。
**修正**：backend `de9be10`：建單時沒有促銷寫 NULL；`computePayable`（`utils/trade.js`）把 `discount_price = 0` 視同 NULL（`NULLIF`），舊資料也不會算出 0 元。
**綠燈**：468 passed（Task 5 結束時）。

### 1.4 重複建單與只取購物車第一筆（P4 spec §5.3）

**現象**：舊的建單只讀 `cartItemRepo.rows[0]`（`controllers/checkout.js` 建單段，只取第一個項目），且同一位使用者每次結帳都新增訂單、不處理上一張未付款訂單。
**根因**：`controllers/checkout.js:12–`起的建單 handler（`06ded19`）以 `cartItemRepo.rows[0]` 建一筆 `order_item`；沒有任何取消既有 -1／0 訂單的邏輯。
**紅燈**：同 [task-5-red.txt](evidence/phase-4/task-5-red.txt)：`test_create_order_includes_every_cart_item`、`test_create_order_cancels_previous_pending`、`test_create_order_concurrently_leaves_one_pending`、`test_create_order_empty_cart_is_400`。
**修正**：backend `de9be10`：整車建單（一個購物車 → 一張 `orders`、多筆 `order_item`，每筆記原價與促銷價快照）；建單交易開頭先鎖會員列，再 `cancelPendingOrders` 取消舊的 -1／0 訂單並釋放保留。購物車改在付款成功時才清（§1.7）。
**鎖的後續**：`FOR UPDATE` 鎖會員列會與外鍵檢查的 `KEY SHARE` 死結（P4 自己寫的缺陷，不是舊缺陷），改 `FOR NO KEY UPDATE`，見 §2.2 與 backend `890106b`。

### 1.5 `POST /newebpay/payment`：金額來自前端、參數明文、編號超長、表單未跳脫（P4 spec §3、§5.5）

**現象與根因**（行號為 `06ded19` 的 `controllers/newebpay.js`）：
1. **Amt 來自前端**：`:47–59` 從 `req.body` 取 `order_items`，`Amt = order_items.reduce(… item.price …)`；前端想付多少就付多少。沒送 `order_items` 時 `.reduce` 在 `try` 之外丟 `TypeError` → 500（這也是 `tests/test_async_errors.py` 原本拿它當「try 外拋錯」案例的原因，P4 改換路由，P4 spec §16 第 8 點）。
2. **參數明文**：`:115–120` 把 `MerchantOrderNo`、`Amt`、`ItemDesc`、`Email`、`ReturnURL`、`NotifyURL` 當明文 hidden 欄位送出，藍新規格要求放在加密的 TradeInfo 內，且明文欄位可被竄改。
3. **`ItemDesc` 未跳脫**：`${order.ItemDesc}` 直接插進 HTML；`ItemDesc` 來自 DB 的商品標題。
4. **編號超長**：`:96` `MerchantOrderNo: order_id`，`orders.order_id` 是 36 字元 UUID，超過藍新的 30 字元上限；且同一張訂單重新付款時編號不能重複。
**紅燈**：[task-8-red.txt](evidence/phase-4/task-8-red.txt)（總覽 `b2d281d`，32 failed、13 passed）：`test_payment_trade_info_contains_required_fields`、`test_payment_form_never_contains_raw_item_desc`、`test_payment_new_merchant_order_no_each_attempt`、`test_payment_other_users_order_is_404`、`test_payment_requires_order_id` 等。**注意**：這批紅燈是經 `/payment` 先 500 連帶失敗（見本節開頭）；`test_payment_amount_from_backend` 是輔助函式 `TypeError`，其真正的行為紅燈由修正後輔助函式（`1d2b75b`）之後的測試承擔，不是紅燈證明。
**修正**：backend `23e4fe2`：`/payment` 只接受 `order_id`（Joi UUIDv4）；金額一律由後端 `computePayable` 算；`MerchantID`、`RespondType`、`TimeStamp`、`Version`、`MerchantOrderNo`、`Amt`、`ItemDesc`、`Email`、`NotifyURL`、`ReturnURL`、`TradeLimit`、`CREDIT` 全放進加密的 TradeInfo，表單只留 `MerchantID`、`TradeInfo`、`TradeSha`、`Version`（`utils/newebpay.js`）；`ItemDesc` HTML 跳脫；每次付款嘗試產生新的 21 字元 `merchant_order_no` 寫在 `payment` 列上（V5，§1.9）。

### 1.6 `POST /newebpay/notify`：500、不冪等、不核金額、不結算（P4 spec §5.5、§6）

**現象與根因**（`06ded19` 的 `controllers/newebpay.js`）：
1. `:213` 對 `order_item` 執行 `SET payment = 1`，但 `order_item` 沒有 `payment` 欄（V1 的欄位只有 `payment_status`），整個交易 `catch` 後回 500「DB Error」（`:228–229`）。這是讀碼與 V1 欄位表的推定；紅燈 evidence 沒有單獨證明（見本節開頭）。
2. 沒有冪等：每次通知都 `INSERT` 一筆 `payment_status = 1`，重送就多一筆。
3. 沒有金額核對：不看 `Amt`，不核對訂單應付金額。
4. 沒有結算：不扣點、不標優惠券已用、不發回饋、不清購物車、不更新 `order_item.payment_status`（評論資格靠它，P3 N10 指定 P4 必做）。
5. 先解密再驗 `TradeSha`（`:140–:158`）、找不到訂單回 404 而不是 400。
**紅燈**：[task-8-red.txt](evidence/phase-4/task-8-red.txt)：`test_notify_bad_sha_changes_nothing`、`test_notify_amount_mismatch_rejected`、`test_notify_duplicate_settles_once`、`test_notify_concurrent_duplicates_settle_once`、`test_notify_success_settles_coupon_order`、`test_notify_success_settles_point_order`、`test_paid_order_item_enables_review`、`test_reward_floors_non_multiple_of_ten`（皆為連帶失敗，限制見本節開頭）。
**修正**：backend `23e4fe2`、`5157494`、`56146f9`：先驗 `TradeSha`（`timingSafeEqual`）再解密；鎖訂單與 `payment` 列；冪等（該 `payment` 已為 1 直接回 200）；金額核對（只在訂單為 0 時，仍呼叫 `computePayable`）；成功時在同一交易內 `settlePaidOrder`：`payment`／訂單／項目 → 1、優惠券 -1 → 1、`減少_確認中` → `減少` 並扣 `travel_point`、回饋 `floor(實付 × 0.1)`、只清與訂單項目相同（行程、出發日、房型）的購物車項目。訂單不是 0 時的處理見 §2.2（notify 第 4 步，原第 7 步；程式註解仍稱第 7 步）。
**DB 層防線**：V5 的部分唯一索引（§1.9）保證一張訂單最多一筆成功付款，即使 controller 的冪等判斷寫錯也擋得住（`tests/test_migrations.py`）。
**綠燈**：`test_trade_payment.py` 44 passed（Task 8 結束時 628 passed，`scripts/ci.sh`）；併發 notify 測試加 `threading.Barrier`、連跑 3 次穩定。

### 1.7 `POST /newebpay/return` 沒有 handler，請求永遠不回應（P4 spec §5.5）

**現象**：瀏覽器從藍新（或 mock）回到 `ReturnURL` 時，請求卡住。
**根因**：`routes/newebpay.js:22`（`06ded19`）`router.post('/return', controller.get_newebpay_return)`，而 `controllers/newebpay.js:235–237` 的 `get_newebpay_return` 是空函式，不呼叫 `res`、不呼叫 `next`。
**紅燈**：[task-8-red.txt](evidence/phase-4/task-8-red.txt)：`test_return_redirects_to_result_page`、`test_return_bad_sha_redirects_without_order`（兩者在呼叫 `/payment` 時就 500，屬連帶失敗，見本節開頭）。
**修正**：backend `23e4fe2`：`post_newebpay_return` 驗簽後 302 導向前端結果頁（`FRONTEND_PATH` 環境變數）並帶訂單編號；簽章不符則導向不帶訂單編號；**不改任何資料**（只有 notify 能改狀態）。

### 1.8 擁有者檢查缺漏（P4 spec §5.1）

**現象**：購物車項目、訂單、折扣、付款的多支 API 沒有確認資源屬於登入者；知道 id 就能改別人的購物車項目。
**根因**（`06ded19`）：`controllers/cart.js:98–100` `DELETE … WHERE cart_item_id = $1`、`:146–149` `UPDATE cart_item … WHERE cart_item_id = $1` 都沒有 user 條件，`middlewares/cart/index.js:137–139`、`:170–173` 只以 `cart_item_id` 查詢；結帳與折扣的 middleware 同類（Task 5、6 報告）。
**紅燈**：[task-4-red.txt](evidence/phase-4/task-4-red.txt)（總覽 `0ef2a32`，9 failed、4 passed）：`test_cart_patch_other_users_item_is_404`、`test_cart_delete_other_users_item_is_404`；[task-5-red.txt](evidence/phase-4/task-5-red.txt)：`test_other_users_cart_is_404`、`test_other_users_summary_is_404`、`test_other_users_userinfo_is_404`；[task-6-red.txt](evidence/phase-4/task-6-red.txt)：`test_preview_other_users_order_is_404`、`test_trial_discount_other_users_order_is_404`、`test_cancel_discount_other_users_order_is_404`。
**修正**：backend `a81ea11`（購物車）、`de9be10`（結帳）、`7308881`（折扣）：不屬於登入者一律 404（不透露資源存在）：購物車項目回 `查無此購物車項目`，訂單、折扣與付款回 `查無此訂單項目`。購物車另補：只能加入上架行程、出發日不得早於今天、同行程同出發日同房型重複加入合併數量、列表回 `cart_item_id`（`a81ea11`）。
**deferred**：`PATCH` 沒有比對 item（飯店可繞過空房檢查）、首次建立 cart 無唯一約束、合併鍵可能因 PATCH 重複（P5，附錄 B）。

### 1.9 V5 migration 與契約（P4 spec §3）

`backend/migrations/V5__p4_trade.sql`：`payment.merchant_order_no VARCHAR(30) NULL UNIQUE`；部分唯一索引 `payment(order_id) WHERE payment_status = 1`。`point_record.type` 新增 `退款退回`（正）與 `退款收回`（負），`type` 是 VARCHAR，不改 schema，契約補值域與寫入時機。
**紅燈**：[task-2-red.txt](evidence/phase-4/task-2-red.txt)（總覽 `89fa48f`，5 failed、14 passed）：`v1_to_v5`、欄位、唯一（含 NULL 可多筆）、一張訂單一筆成功付款（status 0 可並存）、seed 的 15 筆 `merchant_order_no` 為 NULL。**修正**：backend `b4d33d8`。
**審查**：雙審皆 Needs fixes（§2.3）：退款點數的正負號寫反方向、契約仍引用 `v1_to_v4`、§0.1 第 9 項欄位表缺 `merchant_order_no`，皆於修正輪 `e48a67f` 處理。

### 1.10 新功能：管理員退款 API（P4 spec §7；D6、D7）

`POST /api/v1/admin/orders/:order_id/refund`（`routes/admin.js`、`controllers/admin.js`、`utils/trade.js` 的 `refundOrder`）：只有狀態 1 可退，其餘 409；同一交易內訂單與項目 → 3、使用的點數加回並寫 `退款退回`、回饋點數扣回並寫 `退款收回`、使用的優惠券 → 0 並清 `order_id`；回饋已被用掉時 `travel_point` 允許變負（使用者定 Q2）；不改 `payment`、不呼叫藍新。
**紅燈**：[task-9-red.txt](evidence/phase-4/task-9-red.txt)（總覽 `e32c867`，15 failed）。**修正**：backend `ed6e0a1`。
**修正輪**（opus Approved、fable Approved 但有 2 個 Important）：紅燈 [task-9-fix1-red.txt](evidence/phase-4/task-9-fix1-red.txt)（總覽 `b54a435`，1 failed、61 passed，只有 H3 真的紅，H1／H2 是釘住既有行為）；backend `3ed884b`。H1：加「兩個退款併發只成功一次」測試（`Barrier`；暫時把 `lockOrder` 換成無鎖 `SELECT` 的鑑別力驗證：5 次中 4 次失敗，偶爾通過屬競態時機，已還原未 commit）；H2：已退款訂單的 summary 要顯示實付（§2.2）；H3：`discounts.js` 的 `user_point` 夾限為 0（儲存餘額仍可為負），避免負餘額被當成可用點數。

### 1.11 CORS 白名單擋掉閘道回呼（Task 12 發現；P4 spec 未預見）

**現象**：mock 付款頁（`Origin: http://localhost:8095`）以瀏覽器表單 POST 到 `/api/v1/user/newebpay/return`，被全域 `cors()` 白名單拒絕，使用者回不到結果頁；真實藍新的 origin 同理。
**根因**：`backend/src/server.js` 全域 CORS 白名單對所有路由生效，沒有為閘道回呼例外（Task 12 實作者回報 NEEDS_CONTEXT，ledger 記為真實的正式環境缺陷）。
**紅燈**：[task-12-cors-red.txt](evidence/phase-4/task-12-cors-red.txt)（總覽 `63f7780`，2 failed、1 passed）。
**修正**：backend `574f30c`：只對 `POST` 的 `/api/v1/user/newebpay/notify` 與 `/return` 兩個**確切路徑**略過來源白名單（兩者都靠簽章驗證，return 不改資料）；其他路由行為不變。測試 `tests/test_cors_gateway.py`（3 passed）：return 以外部 Origin 通過、notify 以外部 Origin 仍照常處理（簽章檢查仍在）、一般會員路由與 `/payment` 以不允許的 Origin 仍被拒。
**與裁示的偏離**：裁示要求斷言「不允許的來源」訊息，實作者發現全域錯誤處理對無 status 的錯誤只回通用 500「伺服器錯誤」，改斷言該通用訊息並加白名單內 Origin 的對照；主對話接受（ledger）。

### 1.12 P3 deferred：搜尋與購物車日期、驗證訊息含參數名（P4 spec §10）

**現象**：不存在的日期（`2027-02-30`）在搜尋回 500；400 訊息含 API 參數名（例如「type 為必填欄位」）；Joi 內建英文訊息洩漏給使用者（例如 `"people" cannot be infinity`）。
**修正**：
- backend `a81ea11`、`e66c9d4`：新增 `utils/dateRules.js`（`strictDate`、`strictLocalDateTime`、`todayInTaipei`）；日期只接受真實的 `YYYY-MM-DD`、`end_date` 帶時區偏移的規則與購物車 `start_date` 統一；搜尋訊息改中文標籤（`tests/test_product_read.py`、`e2e/test_product_flow.py` 同步）。
- **共用格式化函式（結構性修正）**：第 1–2 輪逐個欄位補訊息，都沒有收斂（見 §2.2）；第 3 輪改為 `utils/Validator/joiMessage.js` 的 `userMessage()`：取 `details[0].message`，空值、非字串或含 ASCII `"` 就回固定的「輸入的資料格式不正確」（本專案自訂訊息全是中文且用「」；Joi 17 內建預設訊息以 `"label"` 開頭，所以一定含 `"`），不依賴 error code 清單。
**紅燈**：[task-10-red.txt](evidence/phase-4/task-10-red.txt)（總覽 `dd36b5d`，39 failed、21 passed）；第 1 輪 [task-10-fix1-red.txt](evidence/phase-4/task-10-fix1-red.txt)（`594c783`，26 failed、71 passed）；第 2 輪 [task-10-fix2-red.txt](evidence/phase-4/task-10-fix2-red.txt)（`a0ce49e`，27 failed、96 passed）；第 3 輪 [task-10-fix3-red.txt](evidence/phase-4/task-10-fix3-red.txt)（`ca84cd5`，15 failed；掃描前實測 74 筆洩漏）。
**綠燈**：backend `e66c9d4`、`c9e3acb`、`efa991f`、`ad01f5f`；`tests/test_validator_sweep.py`（Task 10 結束時 15 passed；最終修正波後 16 passed）在容器內對 14 個 schema（最終修正波後 15 個，加入 `/payment` 的 schema）送 1477 筆（最終 1510 筆）惡意輸入（null、`[]`、`{}`、`true`、`""`、±1e30、字串、小數、JSON `1e400`…），斷言沒有任何一筆回應含 ASCII 雙引號；`tests/test_validator_messages.py`（80 passed）。
**殘留**：product 的其他 handler 與 purchases／promotion／home 的 validator 仍含參數名（deferred，附錄 B；newebpay 的 `/payment` 已於最終修正波 F5 處理）。`POST /user/collection/info/not-a-uuid` 回 500 是已知的驗證缺陷，`tests/test_async_errors.py` 依賴它（P5）。

### 1.13 前端：購物車、結帳、付款結果頁（P4 spec §8）

**現象**：`views/front/cart.vue` 的總金額寫死 `NT$37,600`（`ae9b824:src/views/front/cart.vue:43`、`:59`），沒有呼叫 API；`pay.vue` 沒有呼叫 API；`utils/api.js` 沒有任何交易函式；詳情頁「加入購物車」停用。
**紅燈**：Task 11 [task-11-red.txt](evidence/phase-4/task-11-red.txt)（總覽 `7f1cee9`，5 failed，皆因功能缺漏）；Task 12 [task-12-red.txt](evidence/phase-4/task-12-red.txt)（`4a87746`，6 failed）。
**修正**：frontend `b301aaa`（詳情頁訂購表單、購物車頁；以 `test_add_to_cart_from_detail` 取代 P3 的 `test_add_to_cart_coming_soon`，屬「行為改變後替換」，不是刪測試）、`27f241d`（`pay.vue`、`payResult.vue`、路由）。
**審查後的修正輪**：
- Task 11 `48a679e`（紅燈 [task-11-fix1-red.txt](evidence/phase-4/task-11-fix1-red.txt)，`a32a070`，1 failed 7 passed，只有 M1 真正是紅燈）：`post_payment` 以 `responseType: text` 取回應，後端錯誤訊息遺失，Swal 顯示「網路錯誤」（雙審同一個 Important）；改在 `tradeRequest` 解析字串錯誤 body。
- Task 12 `e263a6a`（紅燈 [task-12-fix1-red.txt](evidence/phase-4/task-12-fix1-red.txt)，`5758c54`，4 failed）：N1 結帳頁初始資料載入完成前按鈕停用（原本的 e2e 不穩定其根因是預填競態）；N2 選優惠券但沒有券時要重算金額；N3 付款結果頁輪詢遇到任何非 0 狀態即停（3 顯示「訂單已退款」）；N4 折扣試算只採最新結果（latest-wins）。
- Task 12 `89d2570`（紅燈 [task-12-fix2-red.txt](evidence/phase-4/task-12-fix2-red.txt)，`fd46f75`，2 failed）：載入前折扣控制也停用、初始折扣還原也只採最新結果、載入失敗提示。
**時區**：購物車 PATCH 以 ISO 字串 `slice(0,10)` 取日期，依賴後端與 DB 同一時區；compose 的 backend 加 `TZ: UTC`（總覽 `1e4e2b7`），DB 日期斷言為回歸測試（§2.2）。

### 1.14 Seed：折抵改以促銷後金額為基底、回饋按實付（P4 spec §12 Q1-b、§6）

**現象**：契約原規則「折抵以原價 `total_price` 為基底」「回饋 = `total_price × 0.1`」，與使用者 2026-11-24 的決定（促銷後金額為基底、回饋按實付、無條件捨去）不符；seed 中同時有促銷與折抵的只有 #2（北海道）與 #4（馬爾地夫）。
**紅燈**：[task-3-red.txt](evidence/phase-4/task-3-red.txt)（總覽 `f81296a`，4 failed、27 passed）。
**修正**：總覽 `7a25bbd`：改 `db/seed-build/extra_seed.sql`（orders 2 列、payment 2 列、point_record 9 列）並以 `build_seed.py` 重產 `R__seed.sql`（不直接改產物）；`tests/test_seed.py` 同步（另有連帶失敗的 `test_seed_user_coupons_point_to_rebuilt_orders`）。因 `R__seed.sql` 靠 `ON CONFLICT DO NOTHING`，舊 volume 不會更新，必須 `docker compose down -v`（使用者已執行，444 passed）。契約 §9 的表格、折抵基底說明與回饋規則由 `a613091`、`22384fa` 同步。
**seed 的 payment 欄位**：seed 列的 `payment.discount_price` 維持與 `orders.discount_price` 同值（無折扣為 NULL，沿用契約舊規則），不改成實付；P4 新建的 `payment` 寫應付金額（ledger 裁決，契約有註明兩者差異）。

### 1.15 與 spec 不符之處（P4 spec §13「讀碼推定不符就回報」的處理結果）

實作過程中發現計畫或 spec 與實際不符的地方，及其處理（來源：ledger 的 Pre-flight 與各 Task 裁決）：

| 與 spec／計畫不符 | 處理 |
|---|---|
| 應付金額公式兩處不同（有／無 `NULLIF(…,0)`） | 兩處都用「0 視同 NULL」（Pre-flight；§1.3） |
| 計畫的建單鎖 `FOR UPDATE` 會與外鍵檢查死結 | 改 `FOR NO KEY UPDATE`（§2.2） |
| spec §5.5 第 7 步（舊編號；現為第 4 步）原只含成功通知，且排在第 4 步（舊編號；現為第 5 步）金額核對之後；實作與審查顯示順序會讓合法的折扣後通知被判金額不符 | 2026-11-25 兩度修訂 spec：第 7 步擴大為成功與失敗通知皆只記錄，且**先於**金額核對（總覽 `3a3d9fa`、`77658a0`；§2.2） |
| spec §3.1「訂單期限內都可送出付款」語意模糊，計畫的演算法會讓重付無限延長訂單 | `POST /payment` 在訂單自己的期限過後一律 409 `訂單已逾時`（spec 同註記補充，§2.2） |
| 試算 API 先呼叫 `expireIfOverdue`，會寫 DB，與「試算不寫入」衝突 | 逾時轉 4 屬狀態修正、不算折扣寫入（Pre-flight） |
| 取消折扣 API 沒有狀態檢查，會清掉已付款訂單的折扣欄位 | 加 -1／0 狀態與逾時檢查（`3118941`；Task 6 裁決） |
| 付款進行中改折扣會讓 notify 金額不符而無法結算 | preview 與取消折扣在付款進行中回 409 `付款進行中，請稍後再試` |
| spec §9 以為 `USER_FK_TABLES` 要補表 | builder check 與 Task 1 Step 0b 確認已涵蓋，未改 `conftest.py` 的該常數 |
| 已退款訂單的 `computePayable` 無定義（Task 5 實作者提出） | Task 9 裁決（§2.2） |
| 計畫的 `["data"]` 整理與 GC5 衝突 | spec §10 明定納入，視為 GC5 例外（測試整理不需紅燈） |
| 計畫 T13 的「505」無來源 | 505 來自 `phase-3.md` 附錄 C（最終修正波）；本報告 §0 以實跑的 798 為準（修正波前為 782） |
| 總 spec §4 沒有 P7 列 | cloudflared 的待辦改放 §6 的 P7 區塊（總覽 `1b78922`，使用者接受） |
| spec §5.5 第 7 步修訂註記同時保留舊句與新句 | 最終審查後已就地改寫：notify 步驟重新編號與程式順序一致（原第 7 步現為第 4 步），舊句刪除（§1.16 D2） |

### 1.16 最終審查修正波（whole-branch review；Task 13 Step 4）

最終審查（reviewer-opus、reviewer-fable 平行、互不看對方結果）皆判「With fixes」。主對話裁決後，在**單一修正波**完成以下項目。紅燈：[final-fix-red.txt](evidence/phase-4/final-fix-red.txt)（13 個 pytest 失敗、2 個 e2e 失敗；總覽 `5096cfd`）。其中 12 個 pytest 與 2 個 e2e 是斷言失敗；惡意輸入矩陣那一個（`test_hostile_matrix_has_no_joi_default_leaks`）是 `TypeError`（`paymentSchema` 尚未匯出，容器內 `schema` 為 undefined），不是偵測到洩漏，屬「測試輔助尚未存在」的紅燈。紅燈測試曾有一支寫錯欄位名（`point_record_id`，實際是 `point_id`），在紅燈 commit 前以暫存 backend 修正還原後重跑確認為斷言失敗，已就地修正並重存 evidence（紅燈 commit 以 amend 更新，未 push）。

| 項目 | 問題 | 修正 | 覆蓋測試 |
|---|---|---|---|
| F1 | `POST /checkout/order` 把購物車項目 join 到 `tour_base`（含下架行程），不檢查是否上架、出發日是否已過：放過期或下架的項目可以被下單、付款 | backend `237f63b`：建單 SQL 帶 `stale`（`上下架狀態` 不是 1 或 `start_date::date` 早於 `todayInTaipei()`），任何項目 stale 就 409「購物車中有已下架或已過出發日的項目，請移除後再結帳」，整個交易回滾（上一張未付款訂單不被取消） | `test_create_order_rejects_taken_down_tour`、`…_rejects_past_start_date`、`…_stale_item_keeps_previous_pending_order`、`…_valid_cart_still_ok` |
| F2 | 重新付款時，本訂單已保留的券不在可用券清單（清單只含 status 0）：`runTrial` 以「券在清單內」決定、`discountBody` 以「有 couponId」決定，改選旅遊積分再選回優惠卷後，畫面顯示未折抵（1000），送出卻帶券（Amt 900） | frontend `e075222`：兩者共用 `selectedCoupon()`（券必須在選項清單內）；載入時把 summary 的保留券補進選項 | e2e `test_retry_with_reserved_coupon_amount_matches_submit`（畫面金額與 mock 頁金額皆 900） |
| F3 | 退款把餘額扣成負數後，結帳頁「可用積分」顯示負數 | frontend `e075222`：顯示 `Math.max(0, points)` | e2e `test_negative_points_display_as_zero` |
| F4 | 回到結帳頁、什麼都沒改就送出，preview 在付款進行中一律 409 | backend `237f63b`：`utils/trade.js` 新增 `reservationMatches`；付款進行中，要求的折扣與目前保留相同（同類型、同 `coupon_id`／同 `used_point`、或兩邊都沒有）時放行，只更新地址、電話、付款方式，不動保留；不同仍 409「付款進行中，請稍後再試」。只讀、不新增鎖，鎖順序不變（GC14） | `test_preview_same_coupon_while_payment_in_progress_is_ok`、`…_same_points_…`（含「不同點數仍 409、保留不變」）、`…_same_none_…`、`…_other_discount_…_still_409`；既有 `test_preview_while_payment_in_progress_is_409` 維持綠 |
| F5 | `middlewares/newebpay` 的訊息含 `order_id` 且繞過 `userMessage()` | backend `237f63b`：標籤改「訂單編號」、改走 `userMessage(error)`；匯出 `paymentSchema` | `test_payment_bad_body_is_400_without_raw_names`（`[]`、缺、空字串、非 UUID、數字）；原始碼掃描新增 `newebpay`；惡意輸入矩陣新增 `np.payment` |

文件修正（無紅燈）：D1 本報告（§4.3 密碼、促銷 checkbox、附錄 A、§1.8、標頭、§2.3「觀察」標明為實作者觀察、附錄 B）；D2 P4 spec §5.5 notify 步驟就地改寫（順序與程式一致，刪除「以此為準」與舊 `Status = SUCCESS` 句；「契約現行」改為「已改寫」；§3.1 新增付款進行中的同折扣例外）；D3 計畫 GC14 補 `reserveDiscount` 點數路徑的已知例外、GC9 的 `cryptography` 改為 Task 7；D4 前端路由註解「產品細項頁面(假資料)」改為「結帳填寫付款資料頁」（`tests/test_api_smoke.py` 標頭「只做 GET，不寫入資料」已不精確——summary 測試以 fixture 自建訂單——改為註明該例外，併入總覽修正 commit）。

**不在這一波（deferred，見附錄 B）**：訂單折扣欄位在逾時／取消後不重設（P5／P6）、回饋公式在 summary 與 settle 各算一次（兩者同為 `floor(payable × 0.1)`，保留並註記）、`NOWAIT` 固定 1.5 秒等測試穩健性（P5）、Google 登入名稱與 2–10 字元規則（P5）、會員中心的負點數顯示（待使用者決定）。

## 2. Vibe coding 工作流

### 2.1 使用的 skill

SDD（subagent-driven development）流程：主對話只做方向、裁決與審查比對；每個 Task 由 implementer 依計畫逐步實作（紅燈 commit → 實作 → 綠燈 commit）、reviewer-opus 審查，計畫標雙審的 Task 另派 reviewer-fable 平行審查、互不看對方結果，主對話比對差異後裁決；「必須修正」項目退回 implementer，修完再審。每個 Task 的狀態、裁決與 deferred minor 記在 ledger。使用者在 `docker compose down -v`、`.env` 修改、push、合併、tag 前都被詢問（Task 3、Task 7、Task 13 各有一次停下點）。

### 2.2 Ruling 與審查對照

下表只列影響較大的裁決（全部裁決見 ledger）。格式：裁決 — 理由 — 若錯的代價。

| # | 裁決（出處） | 理由與代價 |
|---|---|---|
| R1 | **建單鎖會員列由 `FOR UPDATE` 改 `FOR NO KEY UPDATE`**（Task 5 修正輪，backend `890106b`；紅燈 [task-5-red-deadlock.txt](evidence/phase-4/task-5-red-deadlock.txt)，總覽 `63218f5`） | 雙審共同 Important：`FOR UPDATE` 會與 `INSERT orders`／`point_record` 的外鍵檢查（`KEY SHARE` 鎖會員列）死結。這是主對話在 Pre-flight 自己下的裁決（要求以會員列序列化同使用者建單），計畫照做，屬主對話錯誤。`FOR NO KEY UPDATE` 與 `KEY SHARE` 相容、與自己互斥，序列化效果不變。代價：無。紅燈在舊鎖上重現（建單／preview 併發測試 8 輪，建單 500）。ledger 另記一個 minor：報告寫「第 2 輪」，evidence 是第 0 輪出現，兩者不符 |
| R2 | **notify 第 7 步先於第 4 步金額核對；訂單非 0 時成功與失敗通知皆只記錄**（Task 8 審查輪 1、2，backend `5157494`、`56146f9`；紅燈 [task-8-fix1-red.txt](evidence/phase-4/task-8-fix1-red.txt) 5 failed、[task-8-fix2-red.txt](evidence/phase-4/task-8-fix2-red.txt) 3 failed；spec `3a3d9fa`、`77658a0`） | （以下「第 7 步」「第 4 步」為修訂當時的舊編號，現行編號見 §1.16／spec §5.5：舊第 7 步＝現第 4 步，舊第 4 步＝現第 5 步。）雙審共同 Important：有折扣的訂單逾時／取消後保留已釋放，應付金額回到未折抵的小計，用它核對會把合法的折扣後通知誤判為「金額不符」回 400，而不是「記錄、人工退款」的 200。裁決：金額核對只在訂單為 0 時進行；其餘只寫 `result_info`（含 notify 的 `Amt`）、`result_time`，`payment_status` 維持 0（否則違反 V5 部分唯一索引會回 500）。代價：已死訂單上偽造金額的通知會被「記錄」而非拒絕——簽章仍必驗，風險低 |
| R3 | **標準鎖順序與鎖清單**（Task 8 修正輪 1→2，backend `5157494`、`56146f9`；紅燈 `e01fc43`；清單 ledger 的 lock-inventory） | 鎖順序缺陷第 3 次出現（Task 5 會員列、Task 8 F2 `settlePaidOrder` 與 `cart.js` 反向、F2 修正後又與 `cart.js` 的 patch／delete 反向），**主對話諮詢 advisor 後改為完整盤點**：依 `lock-inventory.md` 列出 12 條路徑，只有 `cart` patch／delete 與 add／settle 反向（I-1…I-4，皆為 cart_item → cart）。定案順序：`user(NO KEY UPDATE，僅 checkout)` → `orders(FOR UPDATE)` → `payment(FOR UPDATE)` → `orders/order_item` → `user_coupon/point_record` → `user_level` → `cart(FOR UPDATE)` → `cart_item`；任何碰 `cart_item` 的交易先鎖所屬 cart 列。範圍擴大到 `controllers/cart.js`，並以 `NOWAIT` 的決定性鎖順序測試取代難以重現的併發測試（寫進 GC14）。代價：改動到非 P4 計畫範圍的檔案；若漏盤點會冒出新的死結類別 |
| R4 | **CORS 白名單對 notify／return 兩個確切路徑例外**（Task 12，backend `574f30c`；§1.11） | 閘道回呼本來就是跨來源；兩者皆由簽章驗證，return 不改資料。代價：兩個靠簽章保護的端點接受任何 origin |
| R5 | **Joi 訊息改共用格式化函式**（Task 10 第 3 輪，backend `ad01f5f`；§1.12） | 逐欄位補訊息 3 輪不收斂（第 1 輪 6 項處理、仍有 1–2 項；第 2 輪 K1／K3 仍開；第 3 輪才出現 74 筆洩漏）。**advisor 建議改結構性修正**：`userMessage()` 固定備援＋容器內惡意輸入掃描＋原始碼掃描；規定第 3 輪是最後一次 resume，第 4、5 輪要換更強的 implementer。代價：通用訊息損失一些具體性 |
| R6 | **backend `TZ=UTC` 固定**（Task 11 修正輪，總覽 `1e4e2b7`） | 前端 PATCH 以 ISO 字串切片取日期，假設後端序列化與寫入同一時區；compose 加 `TZ: UTC` 並加 DB 日期斷言（回歸測試，一開始就綠）。P7 部署必須保持 backend `TZ=UTC`（附錄 B）。代價：環境設定耦合 |
| R7 | **已退款訂單的 `computePayable` 取成功 `payment` 列的 `discount_price`**（Task 9，backend `ed6e0a1`、`3ed884b`） | 退款釋放了優惠券，若即時重算會顯示未折抵的金額；改取實際扣款金額，仍在 `computePayable` 內（符合 GC12「金額只由一個函式算」）。無成功 `payment` 列或為 NULL 時退回原邏輯，seed #19 不受影響。代價：小。（H2 審查發現：原實作只對優惠券單成立，點數單的 summary 要補測） |
| R8 | 金額一律來自 `computePayable`（GC12）；`orders.discount_price` 只寫入、不作為金額來源 | Task 6 修正輪收斂 `summaryOf` 自算與 preview 回應讀 `orders.discount_price`；Task 8 依賴它為單一來源 |
| R9 | `POST /payment` 在**訂單自己的期限**過後 409（Task 8 I3，`5157494`） | 原演算法讓每次重付都能延長訂單；「付款進行中不判逾時」只保護既有那次嘗試。代價：期限邊緣失敗的使用者要等交易時限後重新下單 |
| R10 | reward 為 0 不寫 `新增` 的 `point_record`（Task 8；Task 9 退款同） | spec 沒說；零值帳本列是雜訊；有測試釘住 |
| R11 | 付款進行中 preview／取消折扣回 409（Task 6） | 藍新 `Amt` 已固定，改折扣會讓 notify 金額不符而無法結算；代價：使用者需等交易時限（≤10 分鐘） |
| R12 | `tradeLimitSeconds` 夾限 60–900，mock 同（Task 7→8） | 查證結果見 spec §16 第 2 點；兩側一致，雙側夾限各有測試 |

### 2.3 Fable vs Opus review 對照

| Task | opus | fable | 差異與處理 |
|---|---|---|---|
| 1 連線洩漏 | Needs fixes：evidence 沒存／沒 commit、`add_to_cart` 未放 conftest | 未派 | 兩項都是主對話派工指示錯誤（把紅燈指示存在 `.superpowers`，違反 GC3）；evidence 另開 commit 補交（`5f69931`），不改寫歷史 |
| 2 V5 | Needs fixes | Needs fixes | 共同 Important：退款點數正負號。Opus 認為契約引用 `v1_to_v4` 是 Important、Fable 認為 Minor；**Fable 獨有 Important**：§0.1 第 9 項欄位表缺 `merchant_order_no`（Opus 誤以為不存在）。三項皆送修（`e48a67f`） |
| 3 Seed | Needs fixes | Needs fixes | 共同 Important：契約 :243 舊折抵公式；Fable 另提醒 spec §6 補 `NULLIF` 規則，主對話併入 |
| 4 購物車 | Approved（Minor） | 未派 | Minor 併入 Task 10 |
| 5 建單 | Needs fixes | Needs fixes | 共同 Important：會員列死結（R1）、付款進行中的反例（覆蓋缺口，兩方皆指出）、seed 測試限定 email（兩方皆指出 flaky） |
| 6 折扣 | Approved | Approved | 無 Important；仍開修正輪，因兩方皆指出 GC12 未收斂（`summaryOf` 自算、preview 讀 `orders.discount_price`）、uuid 字串比較、併發測試非決定性。ledger 另記：修正輪的併發測試 mutation 證據證錯對象（只拿掉 `FOR UPDATE` 得 ReadTimeout，沒有驗證「保留鎖、拿掉重評」） |
| 7 mock | Approved | Approved（1 Important，計畫指定：沒有測試證明 notify 真的送出或逾時後不送） | 裁決：計畫已延到 Task 8 的 `test_payment_through_mock_gateway_settles`，Task 8 必須加「逾時後無結算」；時鐘邊際、`TradeLimit` 夾限併入 Task 8 |
| 8 藍新 | Needs fixes（1 Important） | Needs fixes（4 Important） | 共同：notify 順序（R2）。**Fable 獨有**：`settlePaidOrder` 先鎖 cart 的順序（I2，Opus 僅列 minor）、`/payment` 訂單期限（I3）、測試改用 conftest API base（I4）。修正輪 1 結束時 Opus 判通過、Fable 發現 F2 的修正與 `cart.js` 反向（新 Important）→ R3 |
| 9 退款 | Approved | Approved，2 Important | **Fable 獨有**：H1 退款鎖沒有測試（我的派工把「併發」配對錯誤）、H2 已退款 summary 只處理券；H3（負餘額未夾限）一併處理 |
| 10 驗證訊息 | Needs fixes | Needs fixes | 兩方同樣兩項 Important（購物車 type／item／people／options 的英文預設訊息、優惠 object.base／coupon 空值）。`65ce429` 曾改紅燈測試 body 繞過缺陷，審查發現。修正 3 輪才收斂（R5） |
| 11 購物車前端 | Needs fixes | Needs fixes | 同一個 Important（`post_payment` 錯誤訊息遺失）。Fable 審查遇 529 兩次，第三次重試才成功 |
| 12 結帳前端 | Needs fixes（2 Important） | Needs fixes（4 Important） | 兩方皆認可 CORS 例外（精確路徑）。Fable 獨有的兩項（N3 結果頁輪詢遇非 0 即停、N4 試算 latest-wins）；修正輪 1 後 Opus 判通過、Fable 判未通過（初始 summary 折扣還原不是 latest-wins）→ 修正輪 2，只派 Opus 複審（小改動） |
| 13 最終審查（whole-branch） | With fixes（1 Important：建單未重驗購物車；數項 Minor） | With fixes（2 項必修文件、3 項 Important） | 共同：建單未重驗購物車（opus Important、fable M-3）、`/payment` 的訊息繞過 `userMessage()`（兩方 minor）。其餘各自獨有（重付時券的畫面金額與送出不一致、負積分顯示、付款進行中同折扣被擋為 fable 獨有；PKCS7 區塊大小為 opus 獨有）。全部在單一修正波完成（§1.16） |

**實作者自己的觀察（非 reviewer 或使用者的結論）**：Fable 在跨檔推演（鎖順序、spec 一致性、測試是否真的有鑑別力）上抓到較多 Opus 未列為 Important 的問題；Opus 在多數 Task 的複審較快收斂。兩者共同指出的項目幾乎都是真實缺陷；單方獨有的項目中，Fable 的幾乎都成立，Opus 獨有的「契約引用 `v1_to_v4`」與 Fable 的「欄位表缺欄」互補。

### 2.4 AI 出錯／人介入紀錄

1. **主對話派工錯誤（Task 1）**：指示紅燈存 `.superpowers`（git 忽略），違反 GC3 要求存 `docs/reports/evidence/phase-4/` 並 commit；`add_to_cart` 也被指示放錯位置。審查抓到，補 commit。
2. **主對話 Ruling 錯誤（Task 5）**：計畫與主對話裁決的 `SELECT … FOR UPDATE` 鎖會員列與外鍵 `KEY SHARE` 死結（R1）。
3. **鎖順序缺陷三次**（Task 5、Task 8 F2、cart patch／delete）：第三次由主對話諮詢 advisor，改為完整盤點（R3）。
4. **Joi 訊息三輪不收斂**：第三輪起由 advisor 建議改結構性修正（R5）。
5. **紅燈測試被自己改過**：`65ce429`（Task 10 的 PATCH body 不合法，讓測試被 body 驗證先擋下，審查指出）、`83bc4c9`、`5575096`、`c1a6050`（見 §1 開頭）。
6. **紅燈不獨立**：Task 1（連帶失敗）、Task 8（經 `/payment` 500 連帶）、Task 6 修正輪（併發測試 mutation 驗證了錯的對象）、Task 11 修正輪（只有 M1 真正是紅燈）。報告如實記錄，沒有補造證據。
7. **派工訊息的模型名與實際不符**：Task 8 的 Co-Authored-By 依實際執行模型寫 Claude Sonnet 5.5，與派工訊息所寫不同（GC3）。
8. **Task 7 與 Task 13 的使用者介入點**：`.env` 必須由使用者改（Task 7，使用者 2026-11-25 完成並驗證）；`docker compose down -v` 由使用者執行（Task 3、Task 13）。
9. **一次無法重現的 e2e 失敗**（Task 12，首次完整 e2e：2 failed、81 passed，`with_points` 與 `retry` 在 pay 頁後 30 秒未到 mock）：單獨與整檔重跑皆過。事後審查認定根因是載入競態（N1），修正輪加 `loaded` 閘門與專屬測試（page 端以 `page.route` 扣住 userinfo 證明）。
10. **無法重現的環境問題**：Task 11 修正輪 `docker compose up` 後立刻跑 e2e，frontend 容器重啟造成 13 筆失敗，等待就緒後全綠（ledger deferred：直接 `docker compose up` 後單跑 e2e 不會等待 frontend 就緒；`scripts/ci.sh` 本來就有 `wait_for frontend`）。

## 3. 測試方法

### 3.1 測試分層（總 spec §4.2 四層）

下表的數量取自最終修正波後的 `scripts/ci.sh`（`pytest -v`）PASSED 行，依檔案分組（檔內有些測試跨層，以主要目的歸類）：

| 層 | 檔案（passed 數） | 重點 |
|---|---|---|
| API 契約 | `tests/test_trade_cart.py`（13）、`tests/test_trade_checkout.py`（54）、`tests/test_trade_refund.py`（18）、`tests/test_validator_messages.py`（80）、`tests/test_validator_sweep.py`（16） | 每支 API 的正常、驗證錯誤、非自己資源回 404、狀態碼；驗證訊息不洩漏參數名 |
| 安全／金流 | `tests/test_trade_payment.py`（49）、`tests/test_cors_gateway.py`（3）、`tests/test_mock_newebpay.py`（14） | `TradeSha` 錯誤、`Amt` 被竄改、notify 重送與併發只結算一次、前端金額被忽略、`ItemDesc` 的 HTML 跳脫、「backend 沒有跳過簽章或假付款的開關」（`test_no_signature_bypass_switch`，純原始碼掃描，[task-13-no-bypass.txt](evidence/phase-4/task-13-no-bypass.txt)） |
| DB 狀態 | `tests/test_migrations.py`（19）、`tests/test_seed.py`（31）、`tests/test_trade_checkout.py`／`test_trade_payment.py`／`test_trade_refund.py` 內的 DB 斷言 | 付款成功後 `orders`、`order_item`、`payment`、`point_record`、`user_level`、`user_coupon`、購物車的值；取消、逾時、退款後的釋放與歸還；V5 部分唯一索引真的擋得住第二筆成功付款；連線洩漏回歸測試 |
| E2E | `e2e/test_trade_flow.py`（21）；`e2e/test_product_flow.py`（42，含 P3 測試改動） | 主線（登入 → 加入購物車 → 結帳 → 優惠券 → mock 付款 → 結果頁）、付款失敗後重付、用點數付款、載入失敗、最新結果優先 |

### 3.2 值得一看的技巧

1. **簽章工具自簽 notify**（`tests/newebpay.py`，`cryptography==50.0.2` 精確鎖版）：pytest 可以不經 mock 直接簽 notify，做竄改、重送、簽章錯誤；mock 則走真實頁面（`X-Mock-Now` 只影響 mock 自身時間，backend 沒有對應邏輯）。
2. **決定性的併發測試**：兩個退款或兩個 notify 用 `threading.Barrier` 同時發；折扣保留的併發測試由另一條連線鎖 `user_coupon` 列、輪詢 `pg_stat_activity` 確認兩個請求都在等鎖後才放行；鎖順序測試用 `NOWAIT` 取代難以重現的死結。ledger 也記了弱點：`NOWAIT` 測試用固定 1.5 秒等待，慢速 CI 有誤綠的可能（deferred）。
3. **用資料庫時間製造逾時**：直接改 `created_at` 或 `payment.created_at`，不用真的等；`ORDER_PAYMENT_TIMEOUT_MINUTES`、`NEWEBPAY_TRADE_LIMIT_SECONDS` 由環境變數設定。
4. **Mutation 驗證測試鑑別力**：Task 9 H1 把 `lockOrder` 換成無鎖 `SELECT`，5 次中 4 次失敗（證明測試真的在驗鎖）；Task 6 的同類驗證驗錯對象（見 §2.3），列為已知缺口。
5. **容器內的惡意輸入矩陣**（`test_validator_sweep.py`）：對 15 個 schema 送 1510 筆輸入（最終修正波後；原 14 個、1477 筆），斷言回應不含 ASCII 雙引號。
6. **原始碼掃描當護欄**：`test_no_signature_bypass_switch`（正式程式碼不得有跳過簽章的開關）與 `createDecipheriv` 唯一呼叫處掃描（紅燈 evidence 中的 `assert not ['controllers/newebpay.js: createDecipheriv']`）。ledger 的 minor：Joi 的原始碼掃描 regex 可繞過（只要求每個檔案有一個 `userMessage(`）。
7. **seed 帳號唯讀**：對 seed 訂單呼叫 summary、preview、試算／取消折扣、建單、付款都算寫入（§4.2、附錄 B）。

### 3.3 測試數量與 CI 結果

乾淨環境驗證（使用者先執行 `docker compose down -v`，再連跑兩次 `scripts/ci.sh`；第 2 次保留 volume；原始摘要見 [task-13-clean-ci.txt](evidence/phase-4/task-13-clean-ci.txt)）：

| 次數 | passed | xfailed | skipped | pytest 耗時 | 牆鐘 | exit code |
|---|---|---|---|---|---|---|
| 第 1 次（`down -v` 之後，含映像建置） | 782 | 0 | 0 | 218.29s | 251s | 0 |
| 第 2 次（保留 volume） | 782 | 0 | 0 | 203.02s | 210s | 0 |
| 最終修正波後（§1.16；backend `237f63b`、frontend `e075222`；保留 volume） | **798**（+16：F1 4、F4 4、F5 6〔5 個 payment 參數化＋1 個原始碼掃描〕、e2e 2） | 0 | 0 | 199.88s | — | 0 |

測試數量變化：**505 passed、0 xfailed（P3 最終）→ 798 passed、0 xfailed、0 skipped（P4，最終修正波後、保留 volume；乾淨 volume〔`down -v`〕的 782 是修正波前的兩次實跑，798 = 782 + 修正波新增的 16）**。各 Task 結束時 `scripts/ci.sh` 的 passed 數（取自 ledger）：Task 1：438（pytest）、Task 7：578、Task 8：614→624→628、Task 9：643→646、Task 10：683→720→746→761、Task 11：765→768、Task 12：777→781→782。CI（GitHub Actions）的 run 編號待 Step 5 push 後補入。

## 4. 操作指南

### 4.1 切到這個版本並啟動

```bash
git clone https://github.com/nohungry/tripeasy.git && cd tripeasy
git clone -b "$(grep BACKEND_REF refs.env | cut -d= -f2)" https://github.com/nohungry/tripeasy-backend.git backend
git clone -b "$(grep FRONTEND_REF refs.env | cut -d= -f2)" https://github.com/nohungry/tripeasy-frontend.git frontend
scripts/ci.sh        # 啟動全部服務並跑測試
```

目前 `refs.env` 是 `BACKEND_REF=phase-4`、`FRONTEND_REF=phase-4`（在合併前是分支名；Step 5 合併後 `phase-4` 會是 tag，同 `phase-3.md` §4.1 的說明）。`.env` 由 `.env.example` 複製，**這個版本新增三組設定**：藍新金鑰與網址（指向本機 mock，假金鑰）、`ORDER_PAYMENT_TIMEOUT_MINUTES=60`、`NEWEBPAY_TRADE_LIMIT_SECONDS=600`。舊的 `.env` 需要手動同步，或刪掉後讓 `scripts/ci.sh` 重新複製。服務網址：前端 http://localhost:5173、backend http://localhost:3000、mock-newebpay http://localhost:8095（`/health`）、Mailpit http://localhost:8025。

### 4.2 測試帳號

seed 帳號（密碼 `Tripeasy123`）：`alice@example.com`（`User`）、`bob@example.com`（`admin`）、`carol@example.com`（`User`）。

**seed 帳號只能讀，不要拿它們走交易流程**：
- seed 的未付款訂單 #16（alice，-1）與 #17（bob，0）在展示環境第一次被查詢時會轉成逾時（4）並釋放保留（P4 spec §16 第 7 點，屬正常行為）；對 seed 訂單呼叫 summary、preview、試算／取消折扣、建單、付款**都算寫入**。測試靠「seed 帳號唯讀」約束不觸發，`tests/test_api_smoke.py` 的 summary smoke 測試改用自建訂單。
- 不要用 seed 帳號加購物車、建單或付款，也不要對 seed 的已付款訂單呼叫退款 API（會改 `travel_point` 與 `point_record`），否則 `tests/test_seed.py` 的計數與餘額斷言會紅。

### 4.3 手動實測

> **實測於 2026-11-25**：以下步驟已由實作者照字面在 headless Chromium（Playwright）與 curl 實跑一遍，並依實跑結果修正文字（原稿漏了姓名與偏好欄位、註冊後不會自動登入等）。**唯一未實測**：步驟 6 的「付款失敗」分支（以 `e2e/test_trade_flow.py::test_payment_failure_then_retry` 覆蓋）。實測紀錄見 ledger 的 `final-docs-report.md`。

前提：在總覽 repo 根目錄（`login()` 用 `uv run python`）、服務已啟動（`docker compose up -d`），且 `e2e-manual-demo@example.com` 這個 email 符合 `TEST_EMAIL_PREFIXES`（前綴 `e2e-`、結尾 `@example.com`），下次執行 pytest 時 session 開頭會被 purge。

**(1) 用自建帳號走一次 mock 付款**

1. 開 http://localhost:5173/#/admin/register，姓名填「展示用戶」（2–10 字元）、email 填 `e2e-manual-demo@example.com`，**密碼必須填 `Tripeasy123`**（符合註冊規則，且與下方 (2) 的 `login()` 使用的密碼相同；填別的密碼，curl 登入會 401），三個「請選擇」的偏好下拉選單各選一個不同的選項（必填），按「加入會員」，出現「註冊成功」。**註冊不會自動登入**：再開 http://localhost:5173/#/admin/login 用同組 email／密碼登入，出現「登入成功」（停留在登入頁，不會跳轉，直接開下一步的網址即可）。
2. 開首頁或搜尋頁選一個行程進詳情頁（實測用 `#/tour/<tour_id>` 直接開 seed 的旅遊行程「北海道雪景 5 日深度遊」，`tour_id` 為 `c35e011b-ffe4-48ea-8511-9f27ef0d5d69`，單價 NT$40,500），「人數」填 1，「出發日期」選未來日期（過去日期會被後端 400；旅遊類行程不必填結束日期），按「加入購物車」，看到「已加入購物車」。
3. 開 `#/cart`：把人數改成 2 並離開欄位（人數於離開欄位時才送出），總金額應隨之更新（實測 NT$40,500 → NT$81,000，不是寫死的 NT$37,600）；按「去結帳」，網址變為 `#/pay?order=…`。
4. 在結帳頁確認 email 預填、填收件資料（全名 2–10 字元、地址、連絡電話，例如「展示用戶」、「台北市測試路1號」、`0912345678`）；選「優惠卷」或「旅遊積分」（二選一；新帳號沒有券與點數，可略過），確認「應付金額」。
5. 按「確認並前往付款」，瀏覽器被導到 http://localhost:8095/MPG/mpg_gateway 的 mock 付款頁，顯示訂單編號、金額（實測 `金額：81000`）與商品名稱。按「付款成功」。
6. 回到 `#/pay/result?order=…`：顯示「付款成功」、「應付金額 NT$81,000」與「獲得旅遊積分 8100 點」（實付 × 10% 無條件捨去）；結果頁需數秒才會顯示結果（腳本等了 6 秒）；再開 `#/cart`，顯示「購物車是空的」。若改按「付款失敗」，訂單維持待付款，可從結帳頁重新付款（此分支未實測，見上方說明）。

**(2) 退款（curl；token 用 login API 取得，不從 localStorage 拿）**

只對步驟 (1) 建立的自建訂單退款，不要對 seed 訂單操作：

```bash
login() { curl -s -X POST http://localhost:3000/api/v1/auth/userinfo/login/email \
  -H 'Content-Type: application/json' -d "{\"email\":\"$1\",\"password\":\"Tripeasy123\"}" \
  | uv run python -c 'import sys,json; print(json.load(sys.stdin)["data"]["token"])'; }
ORDER=$(docker compose exec -T postgres sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -At' <<'SQL'
select o.order_id from orders o join "user" u using (user_id)
where u.email = 'e2e-manual-demo@example.com' and o.payment_status = 1
order by o.created_at desc limit 1;
SQL
)
# 一般會員打退款 → 403
curl -s -w '\n%{http_code}\n' -X POST "http://localhost:3000/api/v1/admin/orders/$ORDER/refund" \
  -H "Authorization: Bearer $(login e2e-manual-demo@example.com)"
# admin（bob）退款 → 200 退款成功
curl -s -w '\n%{http_code}\n' -X POST "http://localhost:3000/api/v1/admin/orders/$ORDER/refund" \
  -H "Authorization: Bearer $(login bob@example.com)"
# 再退一次 → 409
curl -s -w '\n%{http_code}\n' -X POST "http://localhost:3000/api/v1/admin/orders/$ORDER/refund" \
  -H "Authorization: Bearer $(login bob@example.com)"
```

預期（實測輸出一致）：第一個 403（「您沒有權限進行此操作」），第二個 200（訊息「退款成功」，`data` 含 `payment_status: 3`、`returned_point: 0`、`clawed_back: 8100`），第三個 409（「只有已付款的訂單可以退款」）。之後以自建帳號登入瀏覽器，開 `#/pay/result?order=$ORDER`（`$ORDER` 請換成實際的訂單編號），顯示「訂單已退款」。若自建帳號重複走了多次 (1)，`$ORDER` 只取最新一筆已付款訂單，其餘已付款訂單不受影響，purge 時一併刪除。若看到 401，代表 login 失敗（token 為空字串），檢查帳號密碼；`$ORDER` 為空代表付款尚未成功。

**注意**：自建帳號在被 purge 之前會讓 `user`、`user_level`、`point_record`、`orders`、`order_item`、`payment`、`cart` 等表的計數多出來；若在 pytest 執行途中手動建立，`tests/test_seed.py` 會紅。

## 附錄

### A. 變更檔案清單

統計基準（as of 總覽 `150b95b`、backend `237f63b`、frontend `e075222`；總覽數字以 `git diff --shortstat main..HEAD` 在 `150b95b` 計算，**不含**本次「§4.3 實測修正」文件 commit）：總覽 `main..phase-4`（61 個檔案，+8617／−98，含 evidence 與文件）、backend `main..phase-4`（24 個檔案，+1528／−828）、frontend `dev..phase-4`（6 個檔案，+693／−129）。以下略去 evidence 檔案（`docs/reports/evidence/phase-4/` 28 個，其中 `final-fix-red.txt` 為最終修正波新增， `task-13-clean-ci.txt` 與 `task-13-no-bypass.txt` 為 Task 13 新增）。

**backend**（`github.com/nohungry/tripeasy-backend`，`main..phase-4`）
- 新增：`migrations/V5__p4_trade.sql`、`src/utils/trade.js`（結算、鎖、逾時、退款、`computePayable`）、`src/utils/newebpay.js`（加解密、簽章、跳脫）、`src/utils/dateRules.js`、`src/utils/Validator/joiMessage.js`
- 修改：`src/controllers/{cart,checkout,discounts,newebpay,admin}.js`、`src/middlewares/{cart,checkout,discounts,newebpay,admin,product}/index.js`、`src/routes/{newebpay,admin}.js`、`src/server.js`（CORS 例外）、`src/utils/Validator/{admin_Validator（加退款 schema）,cart_Validator,checkout_Vaildator,discounts_Validatior,product_Validator}.js`

**frontend**（`github.com/nohungry/tripeasy-frontend`，`dev..phase-4`）
- 新增：`src/views/front/payResult.vue`
- 修改：`src/router/index.js`、`src/utils/api.js`、`src/views/front/{cart,pay,tourPage}.vue`

**總覽 repo**（`main..phase-4`）
- 新服務：`mock-newebpay/{Dockerfile,server.js}`、`docker-compose.yml`（`mock-newebpay` 服務、backend `TZ: UTC`）、`scripts/ci.sh`（等待 mock health）、`.env.example`、`refs.env`、`pyproject.toml`／`uv.lock`（`cryptography==50.0.2`）
- 測試新增：`tests/test_trade_cart.py`、`test_trade_checkout.py`、`test_trade_payment.py`、`test_trade_refund.py`、`test_mock_newebpay.py`、`test_cors_gateway.py`、`test_validator_messages.py`、`test_validator_sweep.py`、`tests/newebpay.py`、`e2e/test_trade_flow.py`
- 測試修改：`tests/conftest.py`（交易 helper：`add_to_cart`、`make_coupon`、`checkout`、`preview`、`start_payment`、`notify` 等）、`test_migrations.py`、`test_seed.py`、`test_api_smoke.py`、`test_async_errors.py`、`test_product_read.py`、`e2e/conftest.py`、`e2e/test_product_flow.py`
- Seed／契約：`db/seed-build/extra_seed.sql`、`db/seed/R__seed.sql`、`docs/db-contract.md`
- 文件：`docs/superpowers/specs/2026-11-24-p4-trade-design.md`、`docs/superpowers/plans/2026-11-24-p4-trade.md`、總 spec §2.2／§4／§6、本報告

### B. 已知限制

以下來源：P4 spec §3.1、§5.5 第 4 步（原第 7 步）、spec §16 第 7 點，與 ledger 標「deferred」的項目（P5 以後或 final review 待決）。

**B.1 P4 spec §3.1 已知限制：付款通知延遲超過交易時限**
藍新的通知延遲超過交易時限、而期間又有人查詢訂單，訂單會先轉 4（逾時）。之後的成功通知照 §5.5 第 4 步（原第 7 步）只記錄（`result_info`、`result_time`，`payment_status` 維持 0），訂單不改，回 200；真實情況需要人工退款（P6 後台）。連帶：`cancelPendingOrders` 在使用者建新單時會取消付款進行中的舊單，同樣讓之後的成功通知走第 4 步只記錄（P4 spec §3.1 已接受）。

**B.2 P4 spec §5.5 第 4 步（原第 7 步；2026-11-25 修訂後）**
訂單不是 0 時，成功與失敗通知皆只記錄、回 200、不核對金額；金額核對只在訂單為 0 時進行。副作用：已死訂單上的偽造金額通知會被記錄而不是拒絕（簽章仍必驗）；真實藍新的失敗通知可能缺少 `Result` 欄位（P7 以真實藍新測試商店複核）。spec 已就地改寫，編號與程式一致（§1.16 D2）。

**B.3 seed #16、#17 的處理（P4 spec §16 第 7 點）**
seed 的未付款訂單 #16（alice，-1）、#17（bob，0）在展示環境第一次被查詢時會轉成逾時（4）。接受；測試靠「seed 帳號唯讀」約束不觸發（見 §4.2）。`tests/test_seed.py` 對 seed 的假設因此不得被 P4 之後的 E2E 或手動操作破壞。

**B.4 ledger 標「P5 以後」或 final review 待決的項目**
- **交易與資料**：cart 沒有 `UNIQUE(user_id)`（併發首次加入可能建出兩個 cart）；PATCH 沒有比對 item（飯店可繞過空房檢查）、合併／PATCH 未重查空房、PATCH 後合併鍵可能重複；`catch` 內 `ROLLBACK` 丟例外則 `next` 不被呼叫、`release` 未帶 error（Task 1）；`userinfo.js` 的 Google 登入 `FOR UPDATE` 會員列可能與外鍵 `KEY SHARE` 同類衝突（Task 5，行號取自審查當時的 SHA，未重新核對）；`discounts.js` 的 `user_point` 未扣其他待付款訂單已保留的點數（既有）；`admin.js:273` 的 admin 解除優惠券綁定可刪掉被保留（-1）的券（→ P6）；checkout 讀 `cart_item` 未加鎖；read 路徑（summary、試算、取消折扣）持有 `orders FOR UPDATE` 至 COMMIT。
- **金額與退款**：會員中心的點數顯示在退款後會出現原始的負 `travel_point`（`userinfo.js` 多處；使用者裁決：會員中心一律顯示 0，與結帳頁一致；實作延至 P5）；`payment.discount_price` 在 seed 列沿用舊規則，報表若用它算營收，seed 列要 fallback。
- **驗證訊息**：`product_Validator.js` 的 hidden-share `tour_id` 等、purchases／promotion／home 的 validator 仍含參數名；`test_product_write.py:523` 仍斷言 `「tour_id」`；`cartIDSchema` 的 `cart_id` 訊息（ledger 標 final review）；訊息措辭不一致、無共用標籤常數；`POST /user/collection/info/not-a-uuid` 回 500（`test_async_errors.py` 依賴它）；product 的 `product_Validator.js:555` admin 訊息含 ASCII `"`，在擴大 `userMessage` 之前必須先改。
- **後端其他缺陷**：food 空位檢查讀 `options.start_time`，但 food schema 只允許 `start_date`，所以 `restaurant_booking` 永遠不檢查容量；購物車列表 `ORDER BY cart_id` 順序不穩；超過 50 項時列表與 summary 不符。
- **前端**：結果頁任何錯誤都顯示「查無訂單」且不重試；已付款／已取消的訂單仍可開付款表單；重試時地址與電話沒有預填；點數 0 時仍送 `used_point: 0`；`submit` 只 await 點擊當下進行中的試算；「同意接收促銷訊息」checkbox 已移除（它沒有綁定、後端也沒有對應欄位；frontend `27f241d` 移除，之後未還原；還原延至 P5）；`blur` 與 `change` 事件可能吞掉下一次點擊；人數 2.7 靜默變 2；購物車過期項目 PATCH 400 沒有說明。
- **測試**：`NOWAIT` 鎖順序測試用固定 1.5 秒等待、慢速 CI 可能誤綠（建議改輪詢 `pg_stat_activity`）；`test_trade_limit_seconds_is_clamped` 與 `test_trade_checkout.py:267` 寫死 `docker compose exec backend`；`MOCK_BASE` 定義在兩個測試檔而不在 conftest；`test_submit_disabled_until_loaded` 的 `assert held` 不是等待（理論上可能不穩）；載入失敗測試只涵蓋 userinfo；支付錯誤 E2E 依賴 Vite dev server 的 `/src/utils/api.js`；`e2e` 單跑時不等待 frontend 就緒；`TZ=UTC` 的固定只存在 compose，P7 與其他部署必須保持 backend `TZ=UTC`。
- **P6／P7**：逾時訂單排程、訂單管理畫面（P6）；真實藍新測試商店、cloudflared、`TradeLimit` 以最新版手冊複核（P7）；`FRONTEND_PATH` 未設時 return 的導向為 `undefined`。

**B.4a 最終審查新增的已知限制**
- **PKCS7 區塊大小**：mock 與 backend 的 TradeInfo 加解密都用 Node 內建的 16-byte PKCS7（AES-256-CBC）；藍新官方手冊的填充規則尚未對照，P7 接真實測試商店前必須以官方手冊複核（opus M-7）。
- **折扣欄位不重設**：`orders.discount_type`／`discount_price` 在訂單逾時或被取消後不重設（保留已釋放，欄位仍留舊值；金額一律來自 `computePayable`，不受影響）→ P5／P6。
- **會員中心的負點數顯示**：退款扣回回饋後 `travel_point` 可為負（Q2）；結帳頁已顯示為 0（F3）。使用者裁決：會員中心（`userinfo.js`）也一律顯示 0，與結帳頁一致；實作延至 P5。
- **回饋公式有兩份**：summary 的 `get_point` 與 `settlePaidOrder` 各算一次 `floor(payable × 0.1)`，目前相同；保留。
- **測試穩健性**：`NOWAIT` 測試的固定 1.5 秒等待及其他小項（P5）；Google 登入的名稱未套用 2–10 字元規則（P5）。

**B.5 P4 之前就存在、未處理的項目**
P3 報告附錄 B 的項目（P4 spec §10 之外者）沿用，不在此重列。
