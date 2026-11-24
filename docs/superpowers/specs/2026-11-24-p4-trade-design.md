# P4 交易 設計（Spec）

> 日期：2026-11-24 · 狀態：**已核准**（2026-11-24 使用者核准；已經 builder check）
> 上位文件：`docs/superpowers/specs/2026-10-15-tripeasy-rebuild-design.md`（以下稱「總 spec」）§0、§2.2、§4 P4 列、§4.1–4.4、「階段完成標準」
> 前一階段：`docs/reports/phase-3.md`（以下稱「P3 報告」）N10 與 P3 ledger 的 deferred 項目
> 契約：`docs/db-contract.md`（以下稱「契約」）
> 標記：**【使用者定】** = 使用者在 2026-11-22～24 brainstorming 中明確決定；**【Claude 定】** = 起草時由 Claude 決定，格式為「決定 — 理由 — 若錯的代價」，審閱時可推翻。
> 前提標記：**（讀碼推定）** = 只讀了程式碼、沒有實測；計畫裡對應步驟要先驗證，不符就停下來回報。本文件的現況描述都屬於這一類，來源是 2026-11-22 與 2026-11-24 的 reader 盤點。

## 0. 目的

讓**交易流程從前端能完整操作**：購物車 → 結帳填資料 → 選優惠券或點數 → 藍新付款（本機模擬）→ 付款結果，並讓付款成功時的結算（扣點、優惠券標記已用、回饋點數）正確、可驗證、重送也不會重複結算。過程照 P2/P3 寫成教學報告。

這個階段也是總 spec §4.2「安全／金流」那一層的主戰場：**金額竄改、notify 重送的冪等性、藍新簽章**。這些是作品集要展示、但 `auto-regression` 沒有的東西。

**P4 主線（E2E）**：登入 → 詳情頁加入購物車 → 購物車調整數量 → 結帳填收件資料 → 套用優惠券 → 前往付款 → 模擬藍新頁按「付款成功」→ 結果頁顯示已付款，購物車已清空。

## 1. 範圍

### 要做（goals）
- 修正購物車、結帳、折扣、藍新 controller 的既有 bug（§5）。
- 新增 `mock-newebpay` compose 服務（§4）。
- 一個 versioned migration `V5`（§3），同步更新契約與契約測試。
- 付款成功的結算全部在 P4（§6）。
- 管理員退款 **API**（不含畫面，§7）。
- 前端：購物車頁、結帳／付款頁、付款結果頁接 API（§8）。
- 測試：總 spec §4.2 四層（§9）。
- P3 deferred 給 P4 的項目（§10）。
- 修改總 spec 的兩處（§11）。

### 不做（non-goals）
- 後台訂單管理畫面（訂單列表、詳情、退款按鈕）→ **P6**【使用者定：甲】。
- 串接藍新真正的退款或取消授權 API【使用者定：R2】。
- 接真的藍新測試商店、cloudflared → P7。
- 會員中心的「我的訂單」頁 → P5（`views/admin/personalOrder.vue` 是會員中心的佔位頁，維持原樣）。
- 逾時訂單的**排程**自動轉狀態 → P6，與自動下架排程一起做【Claude 建議，使用者未反對】。
- 優惠券與點數疊加使用。
- 多語系、ATM／超商等非信用卡付款方式。

### 反目標（做了也算失敗）
- 付款金額由前端決定，或 notify 不核對金額就把訂單設成已付款。
- 同一個 notify 送兩次，結算做了兩次（點數扣兩次、回饋發兩次）。
- 正式程式碼裡出現「跳過簽章」「假付款」之類的開關。
- 為了 P4 新增 backend npm 套件【使用者定：沿用不新增】。

## 2. 已定案的決策

| # | 決策 | 來源 |
|---|---|---|
| D1 | 付款通知採本機模擬藍新：測試金鑰自簽 notify ＋本機假付款頁 | 使用者 A |
| D2 | 模擬藍新做成獨立的 compose 服務 `mock-newebpay`，backend 透過既有的 `PayGateWay` 環境變數指向它（方案一） | 使用者 |
| D3 | 一個購物車結成一張訂單（`orders` 一筆、`order_item` 多筆） | 使用者 1-A |
| D4 | 優惠券與點數二選一 | 使用者 2A |
| D5 | 結算（扣點、優惠券標已用、10% 回饋、未付款時釋放保留）全部在 P4，於 notify 成功時執行 | 使用者 2B |
| D6 | 退款採 R2：管理員手動標記，歸還點數與優惠券、收回回饋點數，不呼叫藍新 | 使用者 R2 |
| D7 | P4 只做退款 API 與測試；後台訂單管理畫面放 P6，並在總 spec P6 補上 | 使用者 甲 |
| D8 | backend 不新增 npm 套件 | 使用者 |
| D9 | 逾時只在「查詢或結帳時順便判斷」；排程放 P6 | Claude 建議，使用者未反對 |

## 2.1 做法比較（approaches）

**付款通知怎麼收**（選 A）
| 選項 | 取捨 |
|---|---|
| **A 本機模擬藍新** | 不需要對外網路與真帳號，CI 可以跑；缺點是要自己寫模擬服務 |
| B cloudflared ＋真藍新測試商店 | 最真實；但 CI 跑不了、要申請帳號、通道網址每次不同 |
| C 兩者都做 | 最完整；P4 範圍加倍。B 延到 P7 |

**模擬藍新放哪裡**（選方案一）
| 選項 | 取捨 |
|---|---|
| **方案一：獨立 compose 服務** | backend 金流程式和正式版同一套，P7 只換環境變數；E2E 能走真實頁面跳轉；多一個服務要寫 |
| 方案二：放在 backend，只在開發環境開放 | 少一個服務；但正式程式碼混進假金流，漏擋就是偽造付款漏洞 |
| （未列入）不做假付款頁，只由 pytest 直接打 notify | 前端付款流程無法從畫面操作，不符合 P2–P6 完成標準 |

**退款**（選 R2，P4 只做 API）
| 選項 | 取捨 |
|---|---|
| R1 不做 | 範圍最小；狀態流程缺一段 |
| **R2 後台手動標記** | 完整展示點數與優惠券的歸還；不會真的退錢給刷卡的人 |
| R3 串藍新退款 API | 最真實；本機也要模擬退款 API，工作量最大 |

退款畫面放 P4（乙）或全部放 P6（丙）都被排除：乙讓 P4 範圍膨脹、P6 後台被拆兩次做；丙讓 P4 結束時狀態流程缺退款。

## 3. 資料庫（V5 migration）

現況（讀碼推定，`backend/migrations/V1__tripeasy_sql.sql`）：`orders.order_id` 是 UUID（36 字元），`controllers/newebpay.js:96` 直接拿它當藍新的 `MerchantOrderNo`，超過藍新的 30 字元上限；`payment` 沒有任何唯一約束；`order_item` 沒有 `payment` 欄，但 `newebpay.js:82,213` 會更新它。

`V5__p4_trade.sql`：
1. `payment.merchant_order_no VARCHAR(30) NULL UNIQUE`：每一次「前往付款」產生一個新編號，記在 `payment` 上，不放在 `orders` 上。
   【Claude 定】— 理由：付款失敗後要能用同一張訂單重新付款，而藍新的同一個商店訂單編號不能重複使用；編號放在每次付款嘗試上就不會撞號。— 若錯的代價：如果改成放在 `orders`，只需要搬一個欄位，影響小。
   seed 的 15 筆 `payment` 維持 NULL（UNIQUE 允許多個 NULL）。
2. 部分唯一索引：`payment(order_id) WHERE payment_status = 1`。這是資料庫層的最後一道防線，保證一張訂單最多一筆成功付款，即使 controller 的冪等判斷寫錯也擋得住。
3. `point_record.type` 新增兩種值：`退款退回`（正數，退還使用的點數）、`退款收回`（負數，收回回饋）。type 欄是 VARCHAR，不需要改 schema，但契約要補上。
4. 不改金額欄位的型別（維持 FLOAT），以整數新台幣計算並在寫入前取整。【Claude 定】— 理由：改成 NUMERIC 會動到 view 與契約型別，超出 P4。— 若錯的代價：浮點誤差；因為全部是整數，實際上不會出現。

契約與 `tests/test_db_contract.py`、`tests/test_migrations.py` 要同步更新。

### 3.1 付款狀態（沿用 V1 的定義，不新增值）

| 值 | 意義 | P4 何時進入 |
|---|---|---|
| -1 | 資料剛建立 | 從購物車建立訂單 |
| 0 | 資料填寫完成，未付款 | 填完收件資料與付款方式 |
| 1 | 已付款 | notify 成功且金額相符 |
| 2 | 已取消 | 同一位使用者建立新訂單時，自動取消前一張未付款訂單（P4 不提供使用者手動取消的 API【Claude 定】— 理由：沒有會員訂單頁就沒有地方按取消，放 P5 會員中心再議） |
| 3 | 已退款 | 管理員退款 API |
| 4 | 付款逾時 | 查詢或結帳時發現超過期限 |

`order_item.payment_status` 永遠跟所屬 `orders.payment_status` 一起更新（契約既有規則；P3 N10 指定 P4 必做，評論資格靠它）。

**付款失敗**沒有對應的狀態值：notify 回報失敗時，只寫一筆 `payment`（`payment_status = 0`，`result_info` 存回傳內容），訂單維持 0，可以重新付款，點數與優惠券維持保留。【Claude 定】— 理由：沿用既有狀態值，不新增；信用卡失敗多半是暫時性的。— 若錯的代價：如果你希望失敗就結束，改成轉 2 並釋放即可。

**逾時期限**：訂單建立後 60 分鐘，用環境變數 `ORDER_PAYMENT_TIMEOUT_MINUTES` 設定。【Claude 定】— 理由：測試可以直接改 `created_at` 製造逾時，不用真的等待。

**哪些 API 會順便判斷逾時**：`GET /checkout/summary`、`PATCH /checkout/preview`、`POST /trade/discounts`、`POST /newebpay/payment`。發現逾時就把訂單與項目轉成 4、釋放保留，然後回 409（summary 回 200 並顯示逾時狀態）。notify 不判斷（§5.5）。

**付款進行中不判逾時（使用者定 8-d）**：
- `POST /newebpay/payment` 在 TradeInfo 帶藍新的交易時限參數（`TradeLimit`，600 秒；2026-11-24 以 MPG 技術串接手冊 1.1.1 副本與多個 SDK 查證：整數、60–900 秒、0 或不帶＝不限制、倒數到 0 交易失敗；P7 以最新版官方手冊複核），並把這次付款嘗試的截止時間（`payment.created_at` ＋ 時限）作為判斷依據，不新增欄位。
- 逾時判斷 ＝ 已超過訂單期限 **且** 沒有「截止時間還沒到」的付款嘗試。有進行中的付款時，不轉 4。
- **付款進行中**的定義：`payment.payment_status = 0 AND result_time IS NULL AND created_at + TradeLimit 秒 > now()`。已收到失敗通知（`result_time` 已寫）的嘗試視為已結束，不算進行中。【主對話 2026-11-24 同意】
- 訂單期限內都可以送出付款；付款時限可以跨過訂單期限（最多多出一個交易時限），這段期間靠「付款進行中不判逾時」保護。【Claude 定，2026-11-24 修訂：原本「剩餘期限 ≥ 交易時限才接受」的規則會讓本條永遠用不到，已移除】
- mock-newebpay 要實作交易時限：超過時限才按付款，就顯示「交易逾時」，不送成功的 notify。
- 已知限制：藍新的通知延遲超過交易時限、而期間又有人查詢訂單，訂單會先轉 4；之後的成功通知照 §5.5 第 7 步只記錄，需人工退款（P6 後台）。

## 4. mock-newebpay 服務

- 位置：總覽 repo 根目錄 `mock-newebpay/`，在 `docker-compose.yml` 加一個服務（做法比照 `mock-oauth`，但這個要自己寫，因為沒有現成 image）。
- 技術：Node 22 內建的 `http` 與 `crypto`，**不用任何 npm 套件**，image 用 `node:22-alpine`。【Claude 定】— 理由：藍新的加解密在 backend 已經用 Node `crypto` 寫好，mock 用同一套演算法最容易對照；不需要 `package.json`。— 若錯的代價：如果改用 Python，就要另外維持一份加解密實作。
- 金鑰：mock 與 backend 讀同一組**假的**測試金鑰（`.env.example` 填 32 字元的 HashKey、16 字元的 HashIV，明確標示不是真的金鑰）。
- 行為：
  1. `POST /MPG/mpg_gateway`：接收 `MerchantID`、`TradeInfo`、`TradeSha`、`Version`。驗證 TradeSha，簽章不對就回錯誤頁。解密後顯示一個付款頁，內容有商店訂單編號、金額、商品說明（**要做 HTML 跳脫**）、「付款成功」「付款失敗」兩個按鈕。
  2. 按下按鈕後：mock **在伺服器端**照藍新的格式（`Status`、`MerchantID`、`TradeInfo`、`TradeSha`、`Version`，Result 含 `MerchantOrderNo`、`Amt`、`TradeNo`、`PaymentType`、`PayTime`）簽好 notify，POST 到 TradeInfo 裡的 `NotifyURL`；接著讓瀏覽器自動 POST 相同內容到 `ReturnURL`。
  3. `GET /health`：給 `scripts/ci.sh` 等待服務就緒用。
- 網址：`NotifyURL` 是容器之間的網址（例如 `http://backend:<port>/api/v1/user/newebpay/notify`），`ReturnURL` 是瀏覽器用的網址（localhost）；`PayGateWay` 也是瀏覽器用的網址（`http://localhost:<port>/MPG/mpg_gateway`）。
- 安全邊界：mock 只是另一個「藍新」，backend 不知道它是假的，也沒有任何跳過簽章的分支。切換到真的藍新時，只改環境變數（P7）。
- 測試也可以不經過 mock，直接用 `tests/` 裡的 Python 簽章工具自簽 notify，用來做竄改、重送、簽章錯誤等案例（§9）。

## 5. 後端修正與 API

路由前綴沿用 `backend/src/server.js:90–108`（讀碼推定）。

### 5.1 共通
- **連線洩漏**：`controllers/cart.js:12/94/144`、`controllers/checkout.js:12/129` 取得連線後沒有釋放，大約 10 次寫入後卡死。改成 `try/finally` 釋放。**P4 第一件事**，先寫紅燈測試（連續寫入超過連線池上限仍正常回應）。
- **擁有者檢查**：購物車項目、訂單、折扣、付款的每個 API，都要確認資源屬於登入的使用者；不屬於就回 404（不透露資源存在）。【Claude 定】— 理由：和 P3「查無此行程」的處理一致。
- **金額一律後端算**：前端送來的任何金額欄位都忽略。
- **鎖定**：會改訂單狀態或點數的地方（套用折扣、notify、取消、退款）用 `SELECT ... FOR UPDATE` 鎖訂單那一列，避免同時發生的請求重複結算。

### 5.2 購物車（`/api/v1/user/trade/cart`）
- 加入：行程要存在且上架，`start_date` 不能是過去的日期；同一位使用者、同一行程、同一出發日、同一房型重複加入時，合併數量。【Claude 定】— 理由：避免購物車出現兩列一模一樣的項目。
- 修改、刪除：檢查擁有者。
- 查看：每一項的單價**在查看當下即時計算**（促銷期間內用促銷價，否則用原價），總額由後端加總；`cart_item` 不新增價格欄。建立訂單時才把價格快照寫進 `order_item`，之後一律以快照為準。【Claude 定】— 理由：不動 schema；購物車本來就不是承諾價格。— 若錯的代價：使用者看購物車與下單之間促銷剛好結束時，結帳金額會和購物車不同，summary 會顯示實際金額。

### 5.3 結帳（`/api/v1/user/checkout`）
- `POST /order/:cart_id`：把**整車**轉成一張訂單（D3），每個 `order_item` 記下當下的原價與促銷價快照。購物車是空的回 400。**同一位使用者已有未付款訂單（-1 或 0）時，先把舊的轉成 2 並釋放保留**，再建立新的。【Claude 定】— 理由：修掉「重複建單」的 bug，同時不需要會員訂單頁就能讓使用者回到結帳流程。— 若錯的代價：使用者在兩個分頁同時結帳時，前一個分頁的付款會因為訂單已取消而被拒；可以接受。
- **購物車在付款成功時才清**，而且只刪掉和這張訂單項目相同（行程、出發日、房型）的購物車項目。【Claude 定】— 理由：付款失敗或放棄時，購物車還在。
- `GET /userinfo/:order_id`、`PATCH /preview/:order_id`（地址、電話、付款方式、**折扣**；完成後 -1 → 0。沿用既有的 request 格式，折扣的保留也在這裡寫入，見 §5.4）、`GET /summary/:order_id`（回傳原價、促銷後金額、折抵、**應付金額**）。summary 時順便判斷逾時。

### 5.4 折扣（`/api/v1/user/trade/discounts` 與 `PATCH /checkout/preview`）

沿用既有的分工【Claude 定 — 理由：不破壞既有 API 契約與契約 #37 的 `user_coupon.status = -1`。— 若錯的代價：之後要改成由 discounts 寫入，只需搬動寫入位置】：
- `POST /trade/discounts/:order_id`：**只試算**，回傳套用後的金額給前端看，不寫 DB（現況如此，checkout 前的預覽）。修正 `discounts.js:38` 的乘法。
- `PATCH /checkout/preview/:order_id`：**真正寫入保留**（現況 `checkout.js:142–166`）。修正 `checkout.js:153` 的乘法，改成**減去折抵金額**（契約 #1 定案 B）。
- 兩者共用同一套驗證與計算，二選一（D4）：
  - 優惠券：要屬於該使用者、未使用（`user_coupon.status = 0`）、未過期、`order_id` 為 NULL（沒有被其他未付款訂單保留）。保留時 `status` → -1、`order_id` → 這張訂單（沿用現況與契約 #37）。
  - 點數：1 點折 0.8 元（契約 #3），**只接受 5 的倍數**（不符合回 400，前端輸入框以 5 為單位），折抵金額因此一定是整數【使用者定 Q3】。可用點數為 `user_level.travel_point` 減去其他未付款訂單的 `減少_確認中`。保留時寫一筆 `point_record`（`type = '減少_確認中'`）。折抵後應付金額至少 1 元。
  - 重送 preview 改變折扣時，先釋放舊的保留再寫新的。
- `GET /trade/discounts/:order_id`：取消折扣（沿用既有路由與方法），釋放保留。
- **使用者可用的優惠券清單**：~~新增一支使用者用的清單 API~~ 沿用既有的 `GET /api/v1/user/userinfo/pointslevel`（見 §16）。

### 5.5 藍新（`/api/v1/user/newebpay`）
- `POST /payment`：只接受 `order_id`。**`MerchantOrderNo`、`Amt`、`ItemDesc`、`NotifyURL`、`ReturnURL` 全部放進加密的 TradeInfo**（現況 `newebpay.js:91–97,115–120` 把它們當明文 hidden 欄位送出，藍新規格要求放在 TradeInfo 內，而且明文欄位可被竄改）。訂單要屬於使用者、狀態為 0、沒有逾時。由後端算出 `Amt`，產生新的 `merchant_order_no`（≤30 字元，例如 `T` ＋ 日期時間 ＋ 亂數），寫一筆 `payment`（status 0），回傳自動送出的付款表單。**表單內容要做 HTML 跳脫**（總 spec P4 列：`ItemDesc` 直接來自 DB 的商品標題）。
- `POST /notify`（不需要登入）：
  1. 驗證 `TradeSha`，不符回 400，什麼都不改。
  2. 解密後用 `MerchantOrderNo` 找到 `payment` 與訂單，找不到回 400。
  3. 鎖住訂單。**冪等**：這筆 `payment` 已經處理過（status 1）就直接回 200，不做任何事。
  4. **金額核對**：`Amt` 不等於訂單的應付金額時，記錄到 `payment.result_info`，訂單不改，回 400。
  5. `Status = SUCCESS` 且訂單狀態為 0：`payment` → 1，訂單與所有項目 → 1，執行結算（§6），清購物車。整段在同一個交易內。
  6. `Status` 不是 SUCCESS：只記錄（§3.1 付款失敗）。
  - notify **不做逾時判斷**：只要訂單仍是 0 就照常結算；搭配 §3.1「付款進行中不判逾時」，期限內付款的訂單不會先被轉成 4。
  7. 訂單已經不是 0 卻收到成功通知（例如已被查詢時轉成逾時、已取消，或**同一張訂單的另一次付款嘗試已經成功**）：這筆 `payment` **只寫 `result_info`、`result_time`，`payment_status` 維持 0**（否則會違反 V5 的部分唯一索引而回 500），訂單不改，回 200。列為已知限制（真實情況需要人工退款，屬 P6 後台）。要有對應測試：同一張訂單兩次付款嘗試都回報成功，只結算一次、第二筆 payment 仍是 0、回 200。
- `POST /return`：補上 handler。不改任何資料（只有 notify 能改狀態），302 導向前端的付款結果頁並帶上訂單編號。前端網址用環境變數設定。
- 金鑰、藍新網址、NotifyURL、ReturnURL 繼續用既有的環境變數（`newebpay.js:8–11`）。

## 6. 結算規則（notify 成功時，同一個交易內）

- **折抵以促銷後金額為基底**【使用者定 Q1-b】，取代契約現行的「以原價 `total_price` 為基底」（契約 :241）。
- **應付金額只由一個後端函式計算**，summary、`POST /payment` 的 `Amt`、notify 的金額核對都呼叫它，不從任何欄位直接讀：
  - 促銷後小計 ＝ Σ 每個 `order_item` 的（`discount_price` 不為 NULL 時取 `discount_price`，否則取 `total_price`）。這兩欄是建立訂單時的快照，語意沿用契約 :212（`order_item.discount_price` ＝ 促銷價 × 數量，沒有促銷為 NULL）。
  - 應付金額 ＝ 促銷後小計 − 折抵（優惠券的 `discount`，或點數 × 0.8）。
- 欄位寫法沿用契約現況：有折扣時 `orders.discount_price` ＝ 應付金額；沒有折扣時 `orders.discount_price` 為 NULL、`discount_type = 'none'`（契約 :218）。`payment.discount_price` 寫應付金額（與 seed 的 `payment` 列一致）。
- 不論優惠券或點數，折抵後應付金額至少 1 元，否則回 400（例如 `VIP300` 套在 300 元以下的訂單）。
- 優惠券：`user_coupon.status` -1 → 1（保留時已經設了 `order_id`）。
- 點數：`減少_確認中` → `減少`，`user_level.travel_point` 扣掉使用的點數。
- 回饋：新增一筆 `point_record`（`type = '新增'`），點數 ＝ floor(**應付金額（實付）** × 0.1)，並加到 `travel_point`【使用者定：按實付金額、無條件捨去】。取代契約現行的「`total_price × 0.1`」（契約 :264）。
- 未付款時的釋放（取消、逾時、建立新訂單時取消舊單）：刪除 `減少_確認中` 那筆紀錄；`user_coupon.status` -1 → 0、`order_id` → NULL。

## 7. 退款 API（D6、D7）

- `POST /api/v1/admin/orders/:order_id/refund`，需要 admin 角色（沿用 `authRole('admin')`）。
- 只有狀態 1 的訂單可以退款，其他狀態回 409。
- 同一個交易內：訂單與項目 → 3；使用的點數加回 `travel_point`，寫一筆 `退款退回`；回饋的點數從 `travel_point` 扣回，寫一筆 `退款收回`；使用的優惠券 `status` → 0、`order_id` → NULL。
- 回饋點數已經被用掉、餘額不夠扣時：**照常退款，`travel_point` 允許變成負數**，之後獲得的點數先抵掉負數【使用者定 Q2】。`travel_point` 沒有 CHECK 約束（V1:45），不改 schema；可用點數為負時，折抵視為 0 點可用。
- 不呼叫藍新、不改 `payment` 那筆紀錄（保留付款事實）。

## 8. 前端

現況（讀碼推定）：`views/front/cart.vue` 的總金額寫死 NT$37,600，有 import api 但沒有呼叫；`views/front/pay.vue` 沒有呼叫 api；`utils/api.js` 沒有任何交易相關的函式。

- `utils/api.js` 新增購物車、結帳、折扣、付款的函式，寫法沿用現有的函式。
- 詳情頁：P3 停用的「加入購物車（即將開放）」按鈕改為可用；未登入時導向登入頁。
- `cart.vue`：清單、修改數量、刪除、總額都來自 API；「去結帳」建立訂單後進入 `pay.vue`。
- `pay.vue`：收件資料（預填會員資料）→ 選優惠券或輸入點數 → 確認金額 → 「前往付款」送出後端回傳的表單。元件結構盡量維持原樣（總 spec §4.3）。
- 新增付款結果頁（例如 `#/pay/result?order=...`）：顯示訂單狀態。因為 notify 和 return 不保證誰先到，結果頁要輪詢 summary 幾秒，直到狀態不再是 0。【Claude 定】

## 9. 測試（總 spec §4.2 四層）

P1 的 ruling「`delete_user` 只清 3/11 張外鍵表」：builder check 發現 `tests/conftest.py:89–108` 的 `USER_FK_TABLES` 已列出全部 11 張表，計畫第一步只需確認它涵蓋 P4 會寫入的表（含 V5 之後的 `payment`）。

| 層 | 重點案例 |
|---|---|
| API 契約 | 每支 API 的正常、驗證錯誤、401/403、不是自己的資源回 404 |
| 安全／金流 | TradeSha 錯誤 → 400 且不改資料；Amt 被竄改 → 拒絕；同一個 notify 送兩次只結算一次；前端送的金額被忽略；ItemDesc 含 `<script>` 時付款表單有跳脫；一般會員打退款 API → 403 |
| DB 狀態 | 付款成功後訂單、項目、payment、point_record、user_level、user_coupon、購物車的值；取消、逾時、退款後的釋放與歸還；V5 的部分唯一索引真的擋得住第二筆成功付款；連線洩漏回歸測試 |
| E2E | 主線（§0）；付款失敗後重新付款成功；用點數付款 |

- notify 的簽章工具放在 `tests/`（Python 標準函式庫加上專案已有的加解密套件；若沒有 AES 套件，新增測試端套件不受 D8 限制）。
- E2E 走 mock-newebpay 的真實頁面。
- `scripts/ci.sh` 多等一個 `mock-newebpay` 的 health。
- 紅燈 → 綠燈流程照總 spec §4.1。

## 10. P3 deferred 給 P4 的項目

| 項目 | 處理 |
|---|---|
| 不存在的日期（如 2027-02-30）回 500 | 納入，改回 400 |
| 400 訊息含 API 參數名 | 納入 |
| `end_date` 帶時區偏移時，validator 用伺服器時區、PG `::date` 取字面日期，兩者不一致 | 納入，統一規則；購物車的 `start_date` 也套用同一規則 |
| `test_product_read.py` 其餘 `["data"]` 直接取值 | 納入，順手整理 |

## 11. 總 spec 修改

- §2.2 藍新列：本機改成「`mock-newebpay` 模擬藍新（假付款頁＋自簽 notify），pytest 另外直接自簽 notify」；部署改成「P7 接真的藍新測試商店」；刪掉「真正走一次付款流程時用 cloudflared」那一行，移到 P7 待辦。
- §4 P6 列：加上「訂單管理（列表、詳情、退款按鈕，呼叫 P4 的退款 API）」與「逾時訂單排程」。

## 12. 使用者 2026-11-24 的決定與連帶變更

- **Q1-b**：折抵以促銷後金額為基底，seed 一起修正。連帶：修改契約 :241 的規則；seed 中「促銷期間內的行程且使用優惠券」的訂單（契約 :219 #2 北海道、:221 #4 馬爾地夫）的 `orders.discount_price` 改為「促銷後金額 − 折抵」（#2：40500 − 10 = 40490；#4：83300 − 300 = 83000），同步更新以下位置（2026-11-24 grep `44990`／`97700` 的結果）：
  - `db/seed-build/extra_seed.sql:107,109`（orders）、`:153,155`（payment 的金額）——**修改要從 seed-build 來源改，再用 `build_seed.py` 重產**，不要直接改產物。
  - `db/seed/R__seed.sql:344,346`（orders）、`:392,394`（payment）——由 `build_seed.py` 重產。
  - `docs/db-contract.md:219,221`（§9 表格）與 `:241`（折抵基底的規則說明）。
  - `tests/test_seed.py:275,277` 的斷言。
  - `R__seed.sql` 靠 `ON CONFLICT DO NOTHING`，舊 volume 不會更新既有列，所以改完要 `docker compose down -v` 重建再跑測試。
  - **回饋改按實付計算的 seed 連帶**：契約 §9 第 10 項的 `新增` 表（契約 :264–:268）有 9 筆要改，其餘 6 筆實付等於原價不變：
    | 訂單 | #1 | #2 | #3 | #4 | #5 | #6 | #7 | #9 | #13 |
    |---|---|---|---|---|---|---|---|---|---|
    | 實付 | 40500 | 40490 | 40500 | 83000 | 83300 | 84700 | 8200 | 29680 | 17600 |
    | 回饋（舊 → 新） | 4500 → 4050 | 4500 → 4049 | 4500 → 4050 | 9800 → 8300 | 9800 → 8330 | 8500 → 8470 | 840 → 820 | 3000 → 2968 | 1800 → 1760 |
    `user_level.travel_point` 不變（契約 #2 定案 A：餘額不從 `point_record` 加總）。計畫要先核對契約 :268 的現值與上表的「舊」一致，並找出 seed-build 與 `tests/test_seed.py` 中對應的位置。seed 中只有 #2、#4 同時有促銷與折抵（契約 §9 表格；#6 有優惠券但無促銷，#7、#9、#13 用點數但無促銷）。
- **Q2**：退款時 `travel_point` 允許變成負數（§7）。
- **Q3**：點數只接受 5 的倍數（§5.4）。
- **回饋**：按實付金額 × 10%，無條件捨去（§6）。
- **逾時與付款競爭**：選 d，付款進行中不判逾時＋藍新交易時限（§3.1）。
- **其他審閱結果**：付款失敗維持 0 可重付、建立新單自動取消舊單（手動取消 P5 再議）、付款成功才清購物車、逾時 60 分鐘、編號記在 payment、非本人資源回 404、購物車即時計價、折扣沿用現有 API 分工、折抵後至少 1 元——使用者 2026-11-24 確認維持。

## 13. 流程與約束

- 沿用總 spec §4.1：紅燈 commit → 實作 → 雙審 → 全部測試與 CI 綠燈。
- 總覽 repo 開 `phase-4` 分支；backend、frontend 也開 `phase-4` 分支。
- 每個對外動作（push、合併、打 tag）先問使用者。
- 實作中遇到「讀碼推定」不符的情況，停下來回報。

## 14. 完成標準

- §0 主線可以從前端完整操作，並有 E2E 覆蓋。
- §9 四層測試全綠，舊測試沒有退化，CI 綠燈。
- 雙審沒有未處理的 Critical 或 Important 問題。
- `docs/reports/phase-4.md` 定稿。

## 15. 留給實作者決定

- `merchant_order_no` 的確切格式（只要 ≤30 字元、不重複）。
- mock-newebpay 付款頁的樣式。
- 付款結果頁的輪詢間隔與次數。
- 使用者優惠券清單 API 的路徑（若需要新增）。

## 16. 計畫階段修訂（2026-11-24）

寫實作計畫（`docs/superpowers/plans/2026-11-24-p4-trade.md`）時讀碼與主對話裁決的結果，取代上文對應處：

1. **使用者可用優惠券清單沿用 `GET /api/v1/user/userinfo/pointslevel`**（`backend/src/routes/userProfile.js:32`，回傳點數餘額與 `status = 0` 且未過期的券，保留中的 -1 自動排除），不新增 API；取代 §5.4 最後一點。理由：沿用既有程式碼。
2. **`TradeLimit` 已查證**：MPG 技術串接手冊 1.1.1 副本與多個 SDK——整數、60–900 秒、0 或不帶＝不限制、倒數到 0 交易失敗；本專案用 600。P7 以最新版官方手冊複核。
3. **沒有促銷的項目 `order_item.discount_price` 寫 NULL**（現況 `checkout.js:28–32` 寫 0，與契約 :212 不符）。應付金額計算時 `discount_price = 0` 視同 NULL，避免舊資料算出 0 元。
4. **TradeInfo 補齊藍新 MPG 必要欄位**：除 §5.5 列出的 5 個欄位外，`MerchantID`、`RespondType`、`TimeStamp`、`Version`、`Email`、`TradeLimit`、`CREDIT` 也放進 TradeInfo；表單只留 `MerchantID`、`TradeInfo`、`TradeSha`、`Version`。
5. **移除「剩餘期限 ≥ 交易時限才接受付款」的規則**（§3.1 已修訂）：訂單期限內都可送出付款，靠「付款進行中不判逾時」保護。
6. **付款進行中**的定義含 `result_time IS NULL`（§3.1）。
7. **seed 的未付款訂單（#16 alice -1、#17 bob 0）在展示環境第一次被查詢時會轉成逾時（4）**：屬本 spec 正常行為，接受；測試靠「seed 帳號唯讀」約束不觸發（對 seed 訂單呼叫 summary、preview、試算／取消折扣、建單、付款都算寫入）。`tests/test_api_smoke.py` 的 summary smoke 測試改用自建訂單。報告附錄 B 記錄。
8. **`tests/test_async_errors.py` 換路由**：它原本用 `POST /newebpay/payment` 空 body 當「try 外拋錯回 500」的案例，P4 修好後會回 400，需改用其他仍在 try 外拋錯的 handler。
9. **P3 測試斷言的錯誤訊息隨 §10 修改**：搜尋 400 訊息改成中文標籤（不含 API 參數名）時，同步更新 `tests/test_product_read.py` 與 `e2e/test_product_flow.py` 的斷言。

