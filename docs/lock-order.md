# TripEasy 交易上鎖順序

核對基準：行號以 backend `d3280ce` 為準（`git -C backend rev-parse --short HEAD`；P5 Task 9 最後一次動 backend，`utils/trade.js` 與其他引用的檔案行號都已對照該 commit 逐一核對）。下列 `file:line` 皆為該 commit 的行號，路徑相對於 `backend/src/`。

## 規範順序（P4 計畫 GC14，具約束力）

`user (FOR NO KEY UPDATE, checkout only)` → `orders (FOR UPDATE)` → `payment (FOR UPDATE)` → `orders/order_item` → `user_coupon` / `point_record` → `user_level` → `cart (FOR UPDATE)` → `cart_item`

任何碰 `cart_item` 的交易必須先 `FOR UPDATE` 鎖其所屬 `cart`。

### 已知例外

**例外 A**：本交易已 `FOR UPDATE` 的那張 `orders` 列，以及該訂單的 `order_item`，寫入時機不受上述順序限制（即使前面已鎖了 `user_coupon`／`point_record`／`user_level`）。無環的理由：`orders` 列已被本交易鎖住，再 UPDATE 不會等鎖；`order_item` 的寫入者（取消、逾時、結算、退款、preview）都會先對該訂單的 `orders` 取 `FOR UPDATE`（取消舊單是走 `cancelPendingOrders`，`utils/trade.js:225-231`，不是 `lockOrder`），所以持有本訂單鎖的交易不可能被別人擋在 `order_item` 上。

例外 A 實際出現的位置：
- `controllers/checkout.js:199`（`orders` UPDATE）、`:203`（`setOrderStatus`，`orders`／`order_item`）：前面可能已經過 `reserveDiscount` 的 `user_coupon`／`user_level` 鎖
- `utils/trade.js:342`：`reserveDiscount` 結尾 `orders` UPDATE，前面已鎖 `user_coupon`（coupon 路徑，`:303`）或 `user_level`（point 路徑，`:314`）
- `controllers/discounts.js:127`：取消折扣先 `releaseReservations`（`:126`，`point_record`／`user_coupon`）再 UPDATE `orders`
- `utils/trade.js:219`（`expireIfOverdue`）、`:235`（`cancelPendingOrders`）：`releaseReservations` 之後呼叫 `clearOrderDiscount`（`:119-124`），UPDATE 本交易已 `FOR UPDATE` 的那張 `orders`（清空 `discount_type`／`discount_price`）；前面已動 `point_record`／`user_coupon`

**例外 B（GC14 原有）**：`reserveDiscount` 的點數路徑先鎖 `user_level`，再碰本訂單的 `point_record`／`user_coupon`。因子資料都限定在已鎖住的那張訂單，不構成循環。

### 共同前提

所有會改訂單狀態、保留或點數的路徑，都先 `lockOrder`（`utils/trade.js:21-30`，`SELECT ... FROM orders WHERE order_id = $1 FOR UPDATE`）。一張訂單的子列（`order_item`、該訂單的 `user_coupon`／`point_record`）因此只會被持有該訂單鎖的交易修改。下列各節的「無環」判斷都建立在這個前提上。以「誰會取得鎖」為準，前提有兩條例外：
1. 訂單 B 的 preview 會對「被訂單 A 保留的券」取 `FOR UPDATE`（`utils/trade.js:303`），隨後在 `utils/trade.js:266-268` 回 409 並 rollback。B 取得的是 A 的子列鎖。無環：B 持有的只有 B 自己的 `orders` 與這張券，A 的任何路徑在持有 A 的 `orders` 之後取的是自己的券，不會等 B 的列；B 也在拿到券之後就結束。
2. `controllers/admin.js:274` 直接 `DELETE user_coupon`，不鎖 `orders`。無環：它是單一語句、只取一個鎖、取得後不再等其他鎖，不可能形成等待環（代價是可刪掉被保留的券，已知限制）。

## 各路徑

### 1. checkout 建單：`POST /checkout/order/:cart_id`

`controllers/checkout.js:19-106`

| 順序 | 表 | 鎖 | 位置 |
|---|---|---|---|
| 1 | `user` | `FOR NO KEY UPDATE` | `controllers/checkout.js:29` |
| 2 | `cart`、`cart_item` | 無（一般讀取，不加鎖；見下方註） | `controllers/checkout.js:31`、`:37-48` |
| 3 | `orders`（該會員所有 -1／0 訂單，`ORDER BY created_at`） | `FOR UPDATE` | `utils/trade.js:229`（`cancelPendingOrders`，呼叫處 `controllers/checkout.js:55`） |
| 4 | `orders`／`order_item` | UPDATE（取消） | `utils/trade.js:233` → `setOrderStatus` `:126-135` |
| 5 | `point_record`、`user_coupon` | DELETE／UPDATE（釋放保留） | `utils/trade.js:234` → `releaseReservations` `:106-116` |
| 5a | `orders` | UPDATE（清空 `discount_type`／`discount_price`；例外 A，該列已在步驟 3 鎖住） | `utils/trade.js:235` → `clearOrderDiscount` `:119-124` |
| 6 | `orders`、`order_item` | INSERT（新單） | `controllers/checkout.js:58`、`:66` |

註：步驟 2 對 `cart_item` 只做不加鎖的讀取（MVCC），不持有任何列鎖，所以不會參與死結；它不遵守「碰 `cart_item` 先鎖 `cart`」的字面規則，但也不會造成順序反向。建單快照可能與併發的購物車編輯有落差，已列為已知限制。

### 2. preview：`PATCH /checkout/preview/:order_id`

`controllers/checkout.js:151-231`（含 `reserveDiscount`，見第 4 節）

1. `orders` `FOR UPDATE`：`controllers/checkout.js:164` → `utils/trade.js:21-30`
2. `expireIfOverdue`（見第 7 節）：`controllers/checkout.js:166`
3. 無鎖讀取：`paymentInProgress`（`:175`，`utils/trade.js:175-182`）、`reservationMatches`（`:179`，`utils/trade.js:186-207`，讀 `user_coupon`／`point_record`，付款進行中放行「同折扣」用）、`evaluateDiscount`（`:189`，`utils/trade.js:242-293`）
4. 非付款進行中時：`reserveDiscount`（`controllers/checkout.js:196`）
5. `orders` UPDATE：`controllers/checkout.js:199`；`orders`／`order_item` UPDATE：`setOrderStatus` `controllers/checkout.js:203`

### 3. 試算折扣、取消折扣、結帳摘要

三者都只持有 `orders` 鎖，且鎖到 COMMIT（即使不寫入，也會與 notify、付款互相序列化）。

**試算折扣** `POST /trade/discounts/:order_id`：`controllers/discounts.js:25-101`
- `orders` `FOR UPDATE`：`controllers/discounts.js:36`
- `expireIfOverdue`：`:38`
- `evaluateDiscount` 與 `user_level` 餘額讀取皆無鎖：`:47`、`:69`；不寫保留

**取消折扣** `GET /trade/discounts/:order_id`：`controllers/discounts.js:104-154`
- `orders` `FOR UPDATE`：`controllers/discounts.js:113`
- `expireIfOverdue`：`:115`；`paymentInProgress`：`:122`（付款進行中回 409）
- `releaseReservations`（`point_record` → `user_coupon`）：`:126`
- `orders` UPDATE：`:127`

**結帳摘要** `GET /checkout/order/:order_id`：`controllers/checkout.js:234-326`
- `orders` `FOR UPDATE`：`controllers/checkout.js:244`，持有到 `:266` COMMIT
- `expireIfOverdue`：`:246`；其餘皆為讀取

### 4. reserveDiscount

`utils/trade.js:297-346`，呼叫端必須已 `lockOrder`。

- coupon 路徑：`user_coupon` `FOR UPDATE`（`:303`）→ 重新 `evaluateDiscount`（`:306`）→ `releaseReservations`（`:325`；`point_record` DELETE `:108`、`user_coupon` UPDATE `:111`）→ `user_coupon` UPDATE（`:328`）→ `orders` UPDATE（`:342`）
- point 路徑（例外 B）：`user_level` `FOR UPDATE`，`ORDER BY level_id` 鎖該會員所有列（`:314`）→ 重新 `evaluateDiscount`（`:317`）→ `releaseReservations`（`:325`）→ `point_record` INSERT（`:335`）→ `orders` UPDATE（`:342`）
- 為什麼無環：point 路徑持有 `user_level` 時，除了本訂單的子列（只有持有本訂單 `orders` 鎖的交易能動），唯一可能等的是 `point_record` INSERT（`:335`）的外鍵檢查對 `user` 取的 KEY SHARE，它可能在等 Google 登入（`controllers/userinfo.js:156`）；Google 登入之後不會再取任何交易表的鎖，所以不成環。另一張訂單的 `settlePaidOrder`／`refundOrder` 持有的是它自己訂單的子列，等的是 `user_level`，不會反過來等本訂單的子列。多列 `user_level` 鎖定一律 `ORDER BY level_id`，兩個 point 路徑之間順序一致。

### 5. 發起付款：`POST /newebpay/payment`

`controllers/newebpay.js:25-110`

1. `orders` `FOR UPDATE`：`controllers/newebpay.js:34`
2. `expireIfOverdue`：`:36`；`pastOrderDeadline`：`:45`
3. 無鎖讀取：`computePayable`（`:49`）、`order_item`／`tour` 標題（`:50`）、`user` email（`:58`）
4. `payment` INSERT：`:61`（新列，不需先鎖）

### 6. notify

`controllers/newebpay.js:113-213`（驗簽、解密在 `:117-128`，尚未開交易）

共同開頭：
1. `payment` 以 `merchant_order_no` 查 `order_id`：`controllers/newebpay.js:136`（不加鎖，只為了知道要鎖哪張訂單）
2. `orders` `FOR UPDATE`：`:147`
3. `payment` `FOR UPDATE`：`:150`
4. `payment_status = 1` 已處理：COMMIT 回 200（`:154`）

分支：
- 訂單不是 0（逾時、取消等）：只 UPDATE `payment`（`:166`），COMMIT
- 金額不符：只 UPDATE `payment`（`:177`），COMMIT 回 400
- **失敗通知**（訂單為 0、金額相符）：只 UPDATE `payment`（`:188`），訂單維持原狀
- **成功通知**（訂單為 0、金額相符）：UPDATE `payment`（`:194`）→ `settlePaidOrder`（`:201`，`utils/trade.js:350-402`）：
  1. `orders`／`order_item` UPDATE（`setOrderStatus`，`utils/trade.js:355`）
  2. `user_coupon` UPDATE（`:357`）
  3. `point_record` UPDATE（`:362`）、INSERT（`:371`）
  4. `user_level` UPDATE（`:376`；`travel_point` 在 `user_level`，不在 `user`；`point_record` INSERT 對 `user` 只取 FK 的 KEY SHARE，與 checkout 的 `NO KEY UPDATE` 相容，但會被 Google 登入的 `FOR UPDATE`（`controllers/userinfo.js:156`）擋住，見第 10 節）
  5. `cart` `FOR UPDATE`，該會員所有列 `ORDER BY cart_id`（`:384`）
  6. `cart_item` DELETE（`:385-393`）
  7. `cart` UPDATE（重算總額，`:394-399`）

### 7. 逾時轉換：expireIfOverdue

`utils/trade.js:210-221`。目前沒有排程，逾時只在請求碰到訂單時順手轉換（排程屬 P6）。（P5 Task 3：`paymentInProgress` 與 `pastOrderDeadline` 抽出 `paymentInProgressSql`、`orderDeadlineSql`、`orderTimeoutMinutes`，SQL 文字與參數不變，只讓會員端 `GET /user/orders*` 共用；該兩支讀取 API 不開交易、不加鎖、不寫入，不在本文件的上鎖路徑內；`trade.js` 因此在 `paymentInProgress` 之後的行號整體 +16。P5 Task 9：逾時（本節）與取消舊單（第 1 節步驟 5a）都會在 `releaseReservations` 之後清空訂單折扣欄位；因為已持有該訂單的 `orders` 鎖，屬例外 A，不新增鎖順序。）

呼叫端：preview（`controllers/checkout.js:166`）、結帳摘要（`:246`）、試算折扣（`controllers/discounts.js:38`）、取消折扣（`:115`）、發起付款（`controllers/newebpay.js:36`）。notify 不呼叫它。

呼叫前一律已 `lockOrder`。內部依序：`pastOrderDeadline`（讀，`:214`）→ `paymentInProgress`（讀，`:215`）→ `setOrderStatus` 轉 4（`orders`／`order_item` UPDATE，`:217`）→ `releaseReservations`（`point_record` DELETE、`user_coupon` UPDATE，`:218`）→ `clearOrderDiscount`（`orders` UPDATE 清空 `discount_type`／`discount_price`，`:219`，例外 A：本訂單的 `orders` 列已被 `lockOrder` 鎖住）。轉換後各呼叫端必須 COMMIT，否則會被回滾。

### 8. 退款 refundOrder

HTTP 入口 `controllers/admin.js:299-323`（BEGIN `:304`、COMMIT `:306`）；邏輯 `utils/trade.js:406-448`。

1. `orders` `FOR UPDATE`：`utils/trade.js:407`
2. `orders`／`order_item` UPDATE 轉 3：`:413`
3. `user_coupon` UPDATE（歸還券）：`:415`
4. `point_record` 讀取加總（`:420`）、INSERT 退款退回（`:429`）、INSERT 退款收回（`:435`）
5. `user_level` UPDATE：`:441`

退款不鎖 `payment`、不碰 `cart`／`cart_item`。與 notify 的順序（`orders` → ... → `user_level`）一致，所以退款與重複 notify 併發時，後到者在 `orders` 上等待。

### 9. 購物車

`controllers/cart.js`。三條寫入路徑都遵守「先鎖 `cart`，再碰 `cart_item`」，最後 `recalcCartTotal`（`:5-12`）UPDATE `cart`（已持有鎖）。

**新增** `POST`（`:15-83`）
1. INSERT `cart` `ON CONFLICT (user_id) DO NOTHING`（P5 V6 之後 `cart` 有 `UNIQUE(user_id)`）：`:26-29`；再 `cart` `FOR UPDATE`，以 `user_id` 找（一個會員至多一列，不需 `ORDER BY`）：`:30-33`
2. `cart_item` `FOR UPDATE`，以合併鍵（同 `tour_id`、`start_date`、`room_type`）找：`:37-43`
3. `cart_item` UPDATE 數量（`:47`）或 INSERT（`:52`）
4. `recalcCartTotal`：`:58`

**修改** `PATCH`（`:136-188`）
1. `cart` `FOR UPDATE OF c`，以 `cart_item_id` 連回所屬 cart：`:146-150`
2. `cart_item` `FOR UPDATE`：`:152-155`
3. `cart_item` UPDATE：`:156`
4. `recalcCartTotal`：`:162`

**刪除** `DELETE`（`:86-133`）
1. `cart` `FOR UPDATE OF c`，同上：`:95-99`
2. `cart_item` DELETE：`:101`
3. `recalcCartTotal`：`:107`

**列表** `GET`：不開交易、不加鎖。

註：P5 V6 起 `cart` 有 `UNIQUE(user_id)`，併發首次加入由 `ON CONFLICT DO NOTHING` 收斂成同一列（後到者在唯一索引上等待先到者提交），兩個請求再鎖同一個 cart，不會建出第二個。`settlePaidOrder` 仍以 `ORDER BY cart_id` 鎖該會員的 cart 列，現在至多一列，與新增路徑同列同序，無環。

### 10. 不在交易主線上、但碰到相關表的路徑

- `controllers/userinfo.js:156`：Google 登入 `user` `FOR UPDATE`（以 email）。不碰交易表，但會擋住交易路徑因外鍵檢查（`point_record`、`payment`、`user_coupon`、`orders` 的 INSERT）對 `user` 取的 KEY SHARE。Google 登入取得 `user` 鎖後不會再取交易相關表的鎖，所以只是排隊、不成環。
- `controllers/userinfo.js:32`、`:38`、`:210`、`:214`：新會員建立時 INSERT `user_level`／`point_record`，是新列，不與交易競爭。（P5 Task 2：新會員 INSERT `user` 的 name 改為 `googleDisplayName(name, email)`，只換參數值，不新增鎖或查詢；`controllers/userinfo.js` 頂端多一行 require，行號整體 +1。）
- `controllers/userinfo.js:88`：`BEGIN` 開在 `client` 上，但後面的查詢都走 `pool.query`，各自自動提交，不碰交易表。其中 `:93-96` UPDATE `user`，取 `NO KEY UPDATE`，會與 checkout 的 `user` 鎖短暫排隊，不成環。
- `controllers/userProfile.js:52-58`（BEGIN `:52`，UPDATE `:54-57`）：UPDATE `user`，取 `NO KEY UPDATE`，會與 checkout 建單的 `user` 鎖互相排隊，但後續不取其他鎖，不成環。
- `controllers/product.js:626-630`（BEGIN `:630`）：交易只寫 tour 相關表，不碰交易表。
- `controllers/admin.js:274`：解除優惠券綁定，單一 `DELETE user_coupon`、不開交易、不鎖 `orders`，可刪掉被保留（-1）的券（已知限制）。
- `controllers/coupon.js:209`（`post_admin_assigncoupon`）：管理員批次綁定券，INSERT `user_coupon ... ON CONFLICT DO NOTHING`，不開交易。
- `controllers/automation.js:74-78`（`patch_early_notifiSettings`）、`:126-139`（`patch_price_notifiSettings`）：通知設定寫入 `auto_setting`，是單一 `INSERT … ON CONFLICT (user_id) DO UPDATE` 語句、不開交易（P5 Task 6；V6 `auto_setting_user_id_key`）。只鎖該會員自己的那一列，併發首次寫入由唯一索引收斂成一列（後到者等先到者提交後走 UPDATE），不碰交易表、不再取其他鎖，所以不成環。price-tracking 在寫入前另有兩個不加鎖的讀取（`auto_setting` 目前值、`tour` 上架地區），各自獨立自動提交。

### 11. 收藏新增與刪除

`controllers/collection.js`（P5 Task 7；V6 `favorite_user_tour_key UNIQUE (user_id, tour_id)`）。不開交易，每條語句各自自動提交。

**新增** `POST /info/:tour_id`
1. `findListedTour`（`utils/purchase.js`）：不加鎖的 `SELECT … FROM tour`，只讀：`controllers/collection.js:68`
2. `INSERT INTO favorite … ON CONFLICT (user_id, tour_id) DO NOTHING RETURNING favorite_id`：`controllers/collection.js:75-79`。單一語句，只取該會員這一組 `(user_id, tour_id)` 的唯一索引鍵鎖。
3. 若 DO NOTHING（沒有回傳列），不加鎖 `SELECT favorite_id … WHERE user_id = $1 AND tour_id = $2`：`controllers/collection.js:89-92`，回 200 並附原本的 `favorite_id`。SELECT 也查不到（代表那筆剛好被同時刪掉）時回到第 2 步，**最多 3 輪（首次加 2 次重試）**（`:74` 的 `attempt < 3` 迴圈），3 輪都查不到就丟錯，回 500。每一輪的 INSERT、SELECT 都是獨立、自動提交的語句，不會跨輪持有鎖，所以重試不會成環。

**刪除** `DELETE /info/:favorite_id`：單一 `DELETE … WHERE favorite_id = $1 AND user_id = $2 RETURNING favorite_id`（`controllers/collection.js:115-118`）。

**列表** `GET /info/all`：不開交易、不加鎖。

無環的理由：這幾條語句各只碰 `favorite` 一張表、取得鎖後不再等其他鎖；`favorite` 不在規範順序的表裡，其他交易路徑也不會持有 `favorite` 的鎖再去等 `tour`／`user`。併發兩個請求同時新增同一行程時，後到者在唯一索引上等待先到者提交，提交後 DO NOTHING 並走第 3 步查出同一筆，不會撞約束回 500。INSERT 的外鍵檢查對 `user`／`tour` 取 KEY SHARE，只會被 `FOR UPDATE` 擋住（§10 的 Google 登入 `user` 鎖），checkout 的 `FOR NO KEY UPDATE` 不衝突；取得後不再等其他鎖，所以不成環。測試：`tests/test_member_favorites.py::test_concurrent_favorite_same_tour_returns_same_id`（8 條執行緒，各自 session，只有 1 個 201、其餘 200、同一個 `favorite_id`、DB 1 列）。

## 已知問題（已解決）

**多個 cart 時，新增購物車與付款結算可能死結。** 已於 P5 解決：V6 補 `cart UNIQUE(user_id)`，每位會員至多一個 cart，新增購物車改 `INSERT … ON CONFLICT (user_id) DO NOTHING` 後再 `FOR UPDATE`；兩條路徑鎖的是同一列，不再有「各鎖一個、互等」的可能。

## 檢查結果

以字面順序檢查，有四處「後取較前順位的鎖」，分屬上方「已知例外」A 或 B，無環：
1. `reserveDiscount` coupon 路徑（`utils/trade.js:303` → `:342`）與 point 路徑（`:314` → `:342`、`controllers/checkout.js:199`、`:203`）：先鎖 `user_coupon`／`user_level`，之後寫本訂單的 `orders`／`order_item`。（例外 A）
2. 取消折扣（`controllers/discounts.js:126` → `:127`）：先動 `point_record`／`user_coupon`，再 UPDATE `orders`。（例外 A）
3. point 路徑先鎖 `user_level` 再碰本訂單的 `point_record`／`user_coupon`。（例外 B）
4. `expireIfOverdue`（`utils/trade.js:218` → `:219`）與 `cancelPendingOrders`（`:234` → `:235`）：先動 `point_record`／`user_coupon`（`releaseReservations`），再 UPDATE `orders`（`clearOrderDiscount`）。（例外 A：該 `orders` 列已被本交易 `FOR UPDATE`）

除上述之外沒有鎖順序反向。其他觀察：
- checkout 建單（第 1 節步驟 2）以不加鎖讀取碰 `cart_item`，不持任何列鎖，不能構成死結。
- 多 cart 的死結風險已由 V6 `UNIQUE(user_id)` 消除，見「已知問題（已解決）」。

## 對應的測試

總覽 repo `tests/`（以下皆已 grep 確認存在）。

鎖順序的決定性檢查（測試連線先鎖住 `cart`，請求必須卡在 `cart` 上，另一條連線 `NOWAIT` 鎖 `cart_item` 要成功；共用 helper `_assert_waits_on_cart_not_cart_item`）：
- `tests/test_trade_payment.py::test_cart_patch_locks_cart_before_cart_item`
- `tests/test_trade_payment.py::test_cart_delete_locks_cart_before_cart_item`
- `tests/test_trade_payment.py::test_settlement_locks_cart_before_cart_item`

併發與序列化：
- `tests/test_trade_payment.py::test_notify_concurrent_duplicates_settle_once`：重複 notify 併發，只結算一次
- `tests/test_trade_refund.py::test_concurrent_refunds_settle_once`：兩個退款併發，一個 200、一個 409
- `tests/test_trade_refund.py::test_refund_and_duplicate_notify_concurrently`：退款與重複 notify 併發，不 500、點數一致
- `tests/test_trade_checkout.py::test_create_order_concurrently_leaves_one_pending`：併發建單，只留一張未付款訂單（`user` 列鎖）
- `tests/test_trade_checkout.py::test_create_order_and_preview_points_concurrently_no_500`：建單與點數 preview 併發 8 輪，不死結
- `tests/test_trade_checkout.py::test_preview_same_coupon_concurrently_reserves_once`：先鎖住 `user_coupon` 列，兩張訂單的 preview 都卡在鎖上，放行後只有一個保留成功

已知缺口：`NOWAIT` 測試原本等待固定 1.5 秒，P5 Task 9 已改為輪詢 `pg_stat_activity` 確認請求正在等鎖（`_wait_until_blocked_by`）。`user_level` 路徑（point 例外）只有上面的 8 輪併發測試間接覆蓋，沒有決定性的鎖順序測試。

## 維護方式

- 行號會隨程式變動。每個 phase 的計畫第一步，用 `git -C backend rev-parse --short HEAD` 取得 backend 現況，逐條核對本文件的 `file:line`，並更新頂端的核對 commit。
- 新增或修改任何開交易並碰到上述表的路徑時，必須在本文件補上（或更新）一節：依序列出鎖哪些表、用什麼鎖、`file:line`，並確認符合規範順序；有例外就寫進「已知例外」並說明為什麼無環。
- 新增碰 `cart_item` 的交易，先鎖所屬 `cart`，並比照 `_assert_waits_on_cart_not_cart_item` 補一個決定性測試。
