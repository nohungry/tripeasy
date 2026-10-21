# TripEasy DB 契約（V3 views / functions）

> 狀態：草稿 · 依據 spec 3.1 · 從 backend 程式碼反推（四份既有 SQL 都沒有這些物件）

## 0. 說明

- 範圍：程式碼查詢了、但 migration 沒有建立的 21 個物件（12 個 view、9 個 function）。
- 反推方法：見 `docs/superpowers/plans/2026-10-20-p1a-routes-seed-contract.md` 的「反推方法」。
- 原則：V3 照程式碼期待的中文欄位名建立，**controller 不改**。
- 行號以 backend `phase-1` 分支、P1a Task 1 完成後的版本為準。

## 1. A 組：商品與首頁

> A 組共通觀察（各物件裡不再重複解釋）：
>
> - 路徑前綴：公開商品 `GET /api/v1/user/product/search...`、首頁 `GET /api/v1/user/home/search/...`、管理者商品 `/api/v1/admin/product`（`routes/product_admin.js`）。
> - 「偏好分類 1/2/3」的數字（1–10）由 controller 用 `preferenceMap` 反查成中文標籤，所以三個欄位必須是 `smallint`，來源為 `tour.preference1/2/3`。
> - SQL 原文的縮排已整理，內容未改。
> - 表格「依據」欄的「JS 讀取」指 controller 取 `row.<欄位>`；「WHERE」「ORDER BY」「SELECT」指 SQL 字串用到。

### `tour_base`

- **種類**：view（無參數）
- **使用位置**：
  - `controllers/home.js:15`（API：`GET /api/v1/user/home/search/products?type=tourgroup&item=popular`，未登入）
    ```sql
    select * from public.tour_base tb
    inner join public.tour_travel_popular($1,$2) as tf
    on tb.旅遊編號 = tf.tour_id
    ORDER BY 購買排行 ASC LIMIT $3 OFFSET $4;
    ```
  - `controllers/home.js:33`（API：同上，`item=promotion`，未登入）
    ```sql
    SELECT * FROM public."tour_base"
    WHERE 大分類 = $1 and 小分類 = $2 and 通知狀態 = $3
    ORDER BY 旅遊開始日期 DESC LIMIT $4 OFFSET $5;
    ```
  - `controllers/home.js:49`（API：同上，`item=most_favorited`，未登入）
    ```sql
    select * from public.tour_base tb
    inner join public.tour_travel_most_favorited($1,$2) as tf
    on tb.旅遊編號 = tf.tour_id
    ORDER BY 收藏排行 ASC LIMIT $3 OFFSET $4;
    ```
  - `controllers/home.js:68`（API：同上，`type=backpacker`，未登入）
    ```sql
    select * from public.tour_base tb
    inner join public.tour_travel_popular($1,$2) as tf
    on tb.旅遊編號 = tf.tour_id
    ORDER BY 購買排行 ASC LIMIT $3 OFFSET $4;
    ```
  - `controllers/promotion.js:42`（API：`GET /api/v1/admin/promotions`）
    ```sql
    select * from public.tour_base
    ${whereClause}   -- 固定有 通知狀態 = '促銷'；可再加 所屬國家 = $n、所屬地區 = $n、DATE(建立時間) = $n、旅遊名稱 ILIKE $n
    ORDER BY 更新時間 DESC
    LIMIT $${paramIndex++} OFFSET $${paramIndex}
    ```
  - `controllers/admin.js:168`（API：`GET /api/v1/admin/change-info`）
    ```sql
    SELECT 旅遊編號, 上下架狀態, 通知狀態, 旅遊名稱, 旅遊描述, 所屬國家, 所屬地區, 建立時間, 價錢, "旅遊代表圖 Url"
    FROM public."tour_base"
    ${whereSQL}   -- 可加 "上下架狀態" = $n、"所屬國家" = $n、"所屬地區" = $n、"建立時間" = $n、("旅遊名稱" ILIKE $n OR "旅遊描述" ILIKE $n)
    ORDER BY "建立時間" DESC
    LIMIT $${index++}
    OFFSET $${index}
    ```
  - `controllers/product.js:1067`（API：`GET /api/v1/admin/product`）
    ```sql
    SELECT 旅遊編號, 上下架狀態, 旅遊名稱, 旅遊描述, 所屬國家, 所屬地區, 建立時間, 價錢, "旅遊代表圖 Url"
    FROM public."tour_base"
    ${whereSQL}   -- 條件同上
    ORDER BY "建立時間" DESC
    LIMIT $${index++}
    OFFSET $${index}
    ```
  - `controllers/cart.js:22`（API：`POST /api/v1/user/trade/cart/:tour_id`）
    ```sql
    select
      case when 通知狀態 = '促銷' and now() between 促銷開始日期 and 促銷結束日期 then 促銷價錢
      else 價錢 end as price from tour_base tb  WHERE 旅遊編號 = $1
    ```
  - `controllers/cart.js:105`（API：`DELETE /api/v1/user/trade/cart/:cart_item_id`），參數是被刪除項目的 `tour_id`（`deleteRepo.rows[0].tour_id`）：
    ```sql
    select
      case when 通知狀態 = '促銷' and now() between 促銷開始日期 and 促銷結束日期 then 促銷價錢
      else 價錢 end as price from tour_base tb  WHERE 旅遊編號 = $1
    ```
  - `controllers/cart.js:159`（API：`PATCH /api/v1/user/trade/cart/:cart_item_id`），參數是被更新項目的 `tour_id`（`updateRepo.rows[0].tour_id`）：
    ```sql
    select
      case when 通知狀態 = '促銷' and now() between 促銷開始日期 and 促銷結束日期 then 促銷價錢
      else 價錢 end as price from tour_base tb  WHERE 旅遊編號 = $1
    ```
  - `controllers/checkout.js:24`（API：`POST /api/v1/user/checkout/order/:cart_id`）
    ```sql
    SELECT * FROM public."tour_base" WHERE 旅遊編號 = $1
    ```
  - `controllers/checkout.js:31`（API：同上）
    ```sql
    select
      case when 通知狀態 = '促銷' and now() between 促銷開始日期 and 促銷結束日期 then 促銷價錢
      else 0 end as price from tour_base tb  WHERE 旅遊編號 = $1
    ```
- **輸出欄位**：

  | 欄位（中文） | 型別 | 來源（表.欄位 或計算式） | 讀取位置 | 依據 |
  |---|---|---|---|---|
  | 旅遊編號 | uuid | `tour.tour_id` | `home.js:17`、`cart.js:22`、`checkout.js:24`、`admin.js:168`、`product.js:1067` | JOIN 條件、WHERE、SELECT 清單 |
  | 上下架狀態 | smallint | `tour.status`（1 上架、2 下架） | `admin.js:168`、`product.js:1067` | SELECT 清單 + WHERE `"上下架狀態" = $n`（值來自 `req.query.status`） |
  | 通知狀態 | varchar | `notification.type`（'促銷' / '異動'），沒有通知時為 `NULL` | `home.js:34`、`promotion.js:42`、`admin.js:168`、`cart.js:22` | WHERE `通知狀態 = '促銷'`、CASE 條件 |
  | 旅遊名稱 | varchar | `tour.title` | `promotion.js:28`、`admin.js:168`、`product.js:1067` | SELECT 清單、ILIKE |
  | 旅遊描述 | text | `tour.description` | `admin.js:168`、`product.js:1067` | SELECT 清單、ILIKE |
  | 大分類 | varchar | `tour.type`（tourgroup / backpacker） | `home.js:34` | WHERE |
  | 小分類 | varchar | `tour.item`（travel / hotel / food / spot） | `home.js:34` | WHERE |
  | 所屬國家 | varchar | `tour.country` | `promotion.js`、`admin.js:168`、`product.js:1067` | WHERE、SELECT 清單 |
  | 所屬地區 | varchar | `tour.region` | 同上 | WHERE、SELECT 清單 |
  | 建立時間 | timestamptz | `tour.created_at` | `admin.js:168`、`product.js:1067`、`promotion.js` | ORDER BY、WHERE（`DATE(建立時間)`） |
  | 更新時間 | timestamptz | `tour.updated_at` | `promotion.js:44` | ORDER BY |
  | 價錢 | integer | `tour.price` | `cart.js:22`、`checkout.js:49`（`tourRepo.rows[0].價錢`）、`admin.js:168` | CASE 的 else 分支、JS 讀取、SELECT 清單 |
  | 促銷價錢 | double precision | `notification.promo_price`（type='促銷'） | `cart.js:22`、`checkout.js:31` | CASE 的 then 分支 |
  | 促銷開始日期 | timestamp | `notification.start_date` | `cart.js:22` | `now() between` |
  | 促銷結束日期 | timestamp | `notification.end_date` | `cart.js:22` | `now() between` |
  | 旅遊開始日期 | timestamp | `tour.tour_start_date` | `home.js:35` | ORDER BY |
  | 旅遊代表圖 Url | text | `tour.cover_image` | `admin.js:168`、`product.js:1067` | SELECT 清單（欄位名含空格，需雙引號） |
  | 偏好分類1 / 偏好分類2 / 偏好分類3 | smallint | `tour.preference1/2/3` | `home.js:90–96`、`promotion.js:52–59` | `SELECT *` 之後 JS 讀 `row['偏好分類1']` 並移除 |

  `SELECT *` 的呼叫端（`home.js`、`promotion.js`）會把每一個欄位原樣放進 response（只拿掉偏好分類 1/2/3、加上「偏好分類」），所以 view 的欄位集合就是 API 輸出欄位集合。本節只列出程式碼可證實需要的欄位。`旅遊標語`、`旅遊結束日期`、`旅遊天數`、`旅遊代表圖` 等是否也在 view，程式碼無法證實，見待確認 3。

- **列的語意**：每個行程（`tour`）一列，欄位來自 `tour` 並帶入該行程的通知（`notification`）資料。推測：管理者查詢 `上下架狀態` 有 1/2 兩種值，表示 view 含上架與下架的行程（是否成立見待確認 1）。沒有預設排序（每個呼叫端自己 ORDER BY）。
- **邊界**：
  - 沒有通知的行程必須仍會出現，通知相關欄位為 `NULL`（依據：admin 商品清單要列出所有行程；`cart.js` 的 CASE 對 `通知狀態` 為 NULL 時走 `else 價錢`）。因此對 `notification` 必須是 LEFT JOIN。
  - 價錢計算 `now() between 促銷開始日期 and 促銷結束日期` 是 controller 自己判斷，所以 view 本身不需要處理促銷是否在期間內（但見待確認 2）。
  - **首頁 API 的 controller 行為（影響 `tour_base`、`tour_travel`、`popular`、`most_favorited` 所有首頁查詢）**：`routes/home.js` 的 `/products` 使用的 middleware（`middlewares/home/index.js:7`）驗證時用 `home_Validator.reviewSchema`，只把 `page`、`limit`、`lang` 設為必填，且 `validate()` 回傳的 value（含 default）沒有寫回 `req.query`。`type` 沒帶時 `home.js:12–84` 一個分支都不進，`tourData` 維持 `''`，`home.js:86` 的 `''.rows.length` 丟 TypeError，API 回 500；`type=tourgroup` 沒帶 `item` 同理。契約只記錄，不處理。
  - `checkout.js:31` 在非促銷時回 `0`，而 `cart.js:22` 回 `價錢`，兩者語意不同，view 只要提供原始欄位即可。
- **信心**：欄位名稱與來源對應：確定（名稱直接出現在 SQL，來源與 V1 欄位一一對應）。是否過濾下架、一行程對多通知的處理：推測，見待確認。
- **待確認**：
  1. **view 是否只含上架（`status = 1`）的行程？**
     - 程式碼矛盾：`admin.js:168`／`product.js:1067` 用 `上下架狀態` 篩選，表示 view 要含下架；但 `home.js:15/33/49/68` 的公開首頁直接查 `tour_base`，沒有任何上架過濾。
     - 解讀 A：view 含全部行程。後果：首頁（未登入）會列出下架行程；`cart.js`／`checkout.js` 查價也能查到下架行程；admin 功能正常。
     - 解讀 B：view 只含 `status = 1`。後果：首頁正常，但 `GET /admin/product?status=2` 永遠空、管理者清單看不到下架行程。上架 API 本身不受影響（`patch_tourStatus`，`product.js:1332–1341`，直接 `UPDATE public."tour"`，不經過 `tour_base`），只是前端清單裡沒有可選的 `tour_id`。
     - 解讀 C：view 含全部，公開端的過濾交給 `popular` 等 function。後果：`promotion`／`backpacker` 以外各路徑需要逐一確認，`home.js:33` 的 promotion 路徑仍會露出下架行程。
  2. **一個行程有多筆通知（例如同時有「促銷」和「異動」）時，一列要怎麼呈現？**
     - `notification` 無 unique 約束，一個 `tour_id` 可有多列。
     - 解讀 A：每個行程只取一筆通知（例如最新一筆）。後果：`通知狀態` 只會是其中一個；有「促銷」又有「異動」時，其中一種會看不到（`cart.js` 就會讀不到促銷價）。
     - 解讀 B：促銷與異動各自成欄（`促銷價錢`…來自 type='促銷' 的那筆、`異動通知內容` 來自 type='異動' 的那筆），`通知狀態` 取優先順序較高者。後果：需另定優先順序；`tour_tour_detail` 同時讀 `異動通知內容` 和 `通知狀態`，這個解讀較能同時提供兩者。
     - 解讀 C：不合併，每筆通知一列。後果：同一個行程在首頁、admin 清單重複出現，`cart.js` 的 `priceRepo.rows[0]` 取到哪一列不固定。
  3. **view 是否包含 `旅遊標語`、`旅遊結束日期`、`旅遊天數`、`旅遊代表圖 Url`、`異動通知內容` 等欄位？**
     - `tour_travel(uuid)` 的 WHERE／排序使用這些欄位（見該物件），而 `tour_base` 與它在首頁共用同一個 JS 轉換，前端很可能以相同欄位集合讀取。
     - 解讀 A：`tour_base` 與 `tour_travel` 欄位一致（只差 `收藏狀態`）。後果：登入與未登入首頁 response 結構相同。
     - 解讀 B：`tour_base` 只含上面表格的欄位。後果：未登入與登入的首頁 response 欄位不同，前端要處理兩種形狀。
  4. **促銷是否在 view 內就判斷是否在期間內？**
     - 解讀 A：view 不判斷，期間外仍顯示 `通知狀態='促銷'`（依 `cart.js` 自己再檢查 `now() between` 推測）。後果：首頁「促銷」分頁會列出已過期的促銷行程，價格欄位卻是原價。
     - 解讀 B：view 內只在期間內才回 '促銷'。後果：`cart.js` 的檢查變成多餘但無害；首頁促銷分頁不會有過期行程。
  5. **`建立時間`／`更新時間` 來自 `tour` 還是 `notification`？**
     - `promotion.js:44/23` 對「促銷清單」用 `ORDER BY 更新時間 DESC`、`DATE(建立時間) = $n`；`admin.js:168`／`product.js:1067` 的商品清單用 `ORDER BY "建立時間" DESC`。
     - 解讀 A：兩者都是 `tour.created_at`／`tour.updated_at`。後果：促銷清單依行程本身的更新時間排序；建立日期篩選是行程建立日。
     - 解讀 B：兩者來自 `notification.created_at`／`updated_at`。後果：促銷清單依促銷（通知）最近修改排序，建立日期是促銷建立日；但商品清單（無通知的行程）的 `建立時間` 會是 `NULL`，排序與篩選失效。
     - 解讀 C：`建立時間` 取 `tour.created_at`，`更新時間` 取 `GREATEST(tour.updated_at, notification.updated_at)`。後果：促銷清單排序反映促銷異動，商品清單不受影響；需另外確認是否合理。

### `tour_travel`

- **種類**：function（`tour_travel(使用者編號 uuid) RETURNS TABLE(...)`）
- **使用位置**：
  - `controllers/home.js:24`（API：`GET /api/v1/user/home/search/products?type=tourgroup&item=popular`，已登入）
    ```sql
    select * from public.tour_travel($1) tb
    inner join public.tour_travel_popular($2,$3) as tf
    on tb.旅遊編號 = tf.tour_id
    ORDER BY 購買排行 ASC LIMIT $4 OFFSET $5;
    ```
  - `controllers/home.js:41`（API：同上，`item=promotion`，已登入）
    ```sql
    SELECT * FROM public.tour_travel($1)
    WHERE 大分類 = $2 and 小分類 = $3 and 通知狀態 = $4
    ORDER BY 旅遊開始日期 DESC LIMIT $5 OFFSET $6;
    ```
  - `controllers/home.js:58`（API：同上，`item=most_favorited`，已登入）
    ```sql
    select * from public.tour_travel($1) tb
    inner join public.tour_travel_most_favorited($2,$3) as tf
    on tb.旅遊編號 = tf.tour_id
    ORDER BY 收藏排行 ASC LIMIT $4 OFFSET $5;
    ```
  - `controllers/home.js:77`（API：同上，`type=backpacker`，已登入）
    ```sql
    select * from public.tour_travel($1) tb
    inner join public.tour_travel_popular($2,$3) as tf
    on tb.旅遊編號 = tf.tour_id
    ORDER BY 購買排行 ASC LIMIT $4 OFFSET $5;
    ```
  - `controllers/product.js:116`（API：`GET /api/v1/user/product/search`，登入或未登入皆可）
    ```sql
    SELECT *
    FROM (
      SELECT * FROM public."tour_travel"($1::uuid)
    ) AS sub
    ${whereSQL}
    ORDER BY ${sortBy} ${order}
    LIMIT $${params.length + 2} OFFSET $${params.length + 3}
    ```
    `whereSQL` 由 `buildDynamicTourSQL`（`product.js:8–95`）動態組成，可能出現的條件：`"大分類" = $n`、`"小分類" = $n`、`$n = ANY (ARRAY["偏好分類1","偏好分類2","偏好分類3"])`、`"所屬國家" ILIKE $n`、`"所屬地區" ILIKE $n`、`"價錢" >= $n`、`"價錢" <= $n`、`"旅遊開始日期" >= $n`、`"旅遊結束日期" <= $n`、`"旅遊天數" = $n`、`("旅遊名稱" ILIKE $n OR "旅遊標語" ILIKE $n)`。`sortBy` 只會是 `"價錢"` 或 `"旅遊開始日期"`。
- **參數**（function 才有）：

  | 參數 | 型別 | 來源 | 語意 |
  |---|---|---|---|
  | 使用者編號 | uuid | `req.user.id`（`auth_not_mandatory` 之後；未登入時 `id` 為 `undefined`，`pg` 送出 `NULL`） | 用來計算「這位使用者是否已收藏」；`product.js:116` 明確寫 `$1::uuid`，表示未登入時會以 `NULL` 呼叫 |

- **輸出欄位**：

  | 欄位（中文） | 型別 | 來源（表.欄位 或計算式） | 讀取位置 | 依據 |
  |---|---|---|---|---|
  | 旅遊編號 | uuid | `tour.tour_id` | `home.js:26,60,79` | JOIN `tb.旅遊編號 = tf.tour_id` |
  | 大分類 | varchar | `tour.type` | `home.js:42`、`product.js:30` | WHERE |
  | 小分類 | varchar | `tour.item` | `home.js:42`、`product.js:35` | WHERE |
  | 通知狀態 | varchar | `notification.type`（見 `tour_base` 待確認 2） | `home.js:42` | WHERE |
  | 旅遊開始日期 | timestamp | `tour.tour_start_date` | `home.js:43`、`product.js:68`、`product.js:106–109`（排序） | ORDER BY、WHERE |
  | 旅遊結束日期 | timestamp | `tour.tour_end_date` | `product.js:73` | WHERE |
  | 旅遊天數 | integer | `tour.days` | `product.js:78` | WHERE |
  | 價錢 | integer | `tour.price` | `product.js:58,63,106` | WHERE、ORDER BY |
  | 旅遊名稱 | varchar | `tour.title` | `product.js:83` | WHERE（ILIKE） |
  | 旅遊標語 | varchar | `tour.slogan` | `product.js:83` | WHERE（ILIKE） |
  | 所屬國家 | varchar | `tour.country` | `product.js:48` | WHERE（ILIKE） |
  | 所屬地區 | varchar | `tour.region` | `product.js:53` | WHERE（ILIKE） |
  | 偏好分類1 / 2 / 3 | smallint | `tour.preference1/2/3` | `product.js:42,126–143`、`home.js:90–96` | WHERE（ANY ARRAY）、JS 讀 `row['偏好分類1']` |
  | 收藏狀態 | boolean | `EXISTS (favorite WHERE user_id = 參數 AND tour_id = tour.tour_id)` | 無直接讀取（見推測） | 推測：函式要帶入使用者編號的唯一合理理由；`tour_tour_detail` 的同名欄位 `收藏狀態` 被讀為 `is_favorited` |

  其餘欄位（`旅遊描述`、`旅遊代表圖 Url`、`促銷價錢`、`促銷開始日期`、`促銷結束日期`…）：呼叫端都是 `SELECT *` 且 controller 沒有讀取具體 key，但 response 會原樣輸出，欄位集合是否與 `tour_base` 相同見待確認 2。

- **列的語意**：每個行程一列，欄位與 `tour_base` 類似，額外附上傳入使用者是否已收藏。排序由呼叫端決定。
- **邊界**：
  - 傳入 `NULL`（未登入）時 `product.js:116` 仍會呼叫它，所以 function 必須接受 `NULL` 並回傳全部行程（`收藏狀態` 應為 `false` 或 `NULL`，見待確認 3）。
  - 沒有收藏紀錄的行程要保留（相當於 `LEFT JOIN favorite` 或 `EXISTS`），否則商品搜尋會漏行程。
  - 與 `popular`／`most_favorited` 是 `INNER JOIN`，沒出現在後者結果的行程不會出現在首頁。
  - 首頁 API 沒帶 `type` 時整個回 500，見 `tour_base` 邊界（`middlewares/home/index.js:7` 用 `reviewSchema`，default 沒寫回 `req.query`）。
- **信心**：參數與用於過濾／排序的欄位：確定。`收藏狀態` 與是否過濾上架：推測。
- **待確認**：
  1. **function 名稱是 travel，但被用在所有種類（旅行團 travel、背包客 hotel/food/spot）。**
     - 證據：`product.js:116` 的 `whereSQL` 可帶任意 `大分類`／`小分類`（驗證器允許 backpacker 的 hotel/food/spot）；`home.js:77` 在 `type=backpacker` 時也呼叫它。
     - 解讀 A：回傳所有種類。後果：商品搜尋與首頁背包客分頁正常。
     - 解讀 B：只回傳 `item='travel'`。後果：`GET /user/product/search?type=backpacker` 與首頁背包客（已登入）永遠為空，但「未登入」路徑（用 `tour_base`）仍有資料，兩者行為不一致。
  2. **欄位集合是否與 `tour_base` 相同再加 `收藏狀態`。**
     - 解讀 A：相同（再加 `收藏狀態`）。後果：登入／未登入首頁 response 欄位只差 `收藏狀態`。
     - 解讀 B：欄位較少或較多。後果：首頁登入與未登入兩個 response 形狀不一致；前端若依賴多出的欄位會在其中一種狀態讀到 `undefined`。
  3. **未登入（`NULL` 參數）時 `收藏狀態` 該是 `false` 還是 `NULL`？**
     - 解讀 A：`false`。後果：前端 `is_favorited` 一律是布林值。
     - 解讀 B：`NULL`。後果：JSON 內是 `null`，前端的布林判斷結果一樣，但嚴格比較（`=== false`）的測試會失敗。
  4. **是否只回傳上架行程？**（同 `tour_base` 待確認 1）
     - 解讀 A：只回 `status = 1`。後果：商品搜尋看不到下架行程，符合 `get_tourDetails` 對 `status = 1` 的處理；解讀 B：回傳全部。後果：下架行程出現在公開搜尋。

### `tour_travel_popular`

- **種類**：function（`tour_travel_popular(大分類 text, 小分類 text) RETURNS TABLE(tour_id uuid, 購買排行 bigint)`）
- **使用位置**：
  - `controllers/home.js:16`（API：`GET /api/v1/user/home/search/products?type=tourgroup&item=popular`，未登入）：完整 SQL 見 `tour_base` 的 `home.js:15`；參數 `['tourgroup','travel']`。
  - `controllers/home.js:25`（API：同上，已登入）：完整 SQL 見 `tour_travel` 的 `home.js:24`；參數 `$2,$3 = 'tourgroup','travel'`。
  - `controllers/home.js:69`（API：`...products?type=backpacker&item=hotel|food|spot`，未登入）：完整 SQL 見 `tour_base` 的 `home.js:68`；參數 `[type, item]`。
  - `controllers/home.js:78`（API：同上，已登入）：完整 SQL 見 `tour_travel` 的 `home.js:77`；參數 `$2,$3 = type, item`。
  - 四處的呼叫片段都是：
    ```sql
    inner join public.tour_travel_popular($1,$2) as tf on tb.旅遊編號 = tf.tour_id
    ...
    ORDER BY 購買排行 ASC LIMIT ... OFFSET ...
    ```
- **參數**（function 才有）：

  | 參數 | 型別 | 來源 | 語意 |
  |---|---|---|---|
  | 第 1 個 | text | `home.js:19` 寫死 `'tourgroup'`；`home.js:72` 為 `req.query.type`（`backpacker`） | 推測為「大分類」（`tour.type`） |
  | 第 2 個 | text | `home.js:19` 寫死 `'travel'`；`home.js:72` 為 `req.query.item`（`hotel`／`food`／`spot`） | 推測為「小分類」（`tour.item`） |

- **輸出欄位**：

  | 欄位（中文） | 型別 | 來源（表.欄位 或計算式） | 讀取位置 | 依據 |
  |---|---|---|---|---|
  | tour_id（英文，不是中文） | uuid | `tour.tour_id` | `home.js:17,26,70,79`（`tf.tour_id`） | JOIN 條件 |
  | 購買排行 | bigint | 依 `order_item`（購買數）由多到少的名次，1 為最熱門 | `home.js:18,27,71,80` | ORDER BY ASC，數字小的在前 |

  `SELECT *` 讓 `tour_id` 與 `購買排行` 一起進入 response（`tour_id` 是額外的英文欄位）。

- **列的語意**：符合 (大分類, 小分類) 的行程，各一列，附上購買排行名次。
- **邊界**：
  - 首頁 API 沒帶 `type` 時整個回 500，不會走到本 function，見 `tour_base` 邊界。
  - 欄位名 `tour_id` 是英文，與其他全部欄位的中文命名不同，但程式碼寫死 `tf.tour_id`，必須照做。
  - 因為是 `INNER JOIN`，沒有出現在此 function 結果裡的行程不會出現在首頁熱門分頁。
- **信心**：參數順序與輸出欄位名：確定（值與欄位名稱直接出現在程式碼）。排名計算方式：推測（只由 `購買排行` 一詞推測）；`bigint` 型別是依 window function／COUNT 的回傳型別推測，程式碼不讀它的型別。
- **待確認**：
  1. **「購買」怎麼算？**
     - 解讀 A：數 `order_item` 全部列。後果：未付款、已取消的訂單也計入，排行被灌水。
     - 解讀 B：只算 `payment_status = 1`（已付款）。後果：新 DB／seed 若沒有已付款訂單，熱門分頁整個為空；P1b 的 seed 需要包含已付款訂單。
     - `order_item.payment_status` 的值：-1 資料剛建立、0 資料填寫完成未付款、1 已付款、2 已取消、3 已退款、4 付款逾時。`checkout.js:48` 建立 `order_item` 時一律寫入 -1，所以解讀 A 連尚未填寫就放棄的結帳也會計入。
     - 解讀 C：只排除 2（已取消）、3（已退款）、4（付款逾時），保留 -1、0、1。後果：仍計入未付款的訂單。
     - 解讀 D：只算 0 與 1（已填寫完成、已付款）。後果：排除剛建立與所有失敗狀態，介於 A、B 之間。
  2. **沒有任何購買的行程要不要出現？**
     - 解讀 A：出現，排在最後（`LEFT JOIN`，排行用計數 0 排序）。後果：新 DB 熱門分頁仍有資料。
     - 解讀 B：不出現（`INNER JOIN order_item`）。後果：沒有訂單時首頁熱門分頁回 200「查無資料」。
  3. **排名並列時怎麼處理？**
     - 解讀 A：`RANK()`（並列同名次）。後果：`ORDER BY 購買排行 ASC LIMIT/OFFSET` 在並列時沒有次要排序，分頁可能重複或漏列。
     - 解讀 B：`ROW_NUMBER()` 並加次要排序。後果：分頁穩定，並列者的先後取決於次要排序的選擇。
  4. **是否只回傳上架行程？**（同 `tour_base` 待確認 1）
     - 解讀 A：過濾上架。後果：未登入路徑（`tour_base`）不會露出下架行程；解讀 B：不過濾。後果：下架行程可能進入熱門排行。

### `tour_travel_most_favorited`

- **種類**：function（`tour_travel_most_favorited(大分類 text, 小分類 text) RETURNS TABLE(tour_id uuid, 收藏排行 bigint)`）
- **使用位置**：
  - `controllers/home.js:50`（API：`GET /api/v1/user/home/search/products?type=tourgroup&item=most_favorited`，未登入）：完整 SQL 見 `tour_base` 的 `home.js:49`；參數 `['tourgroup','travel']`。
  - `controllers/home.js:59`（API：同上，已登入）：完整 SQL 見 `tour_travel` 的 `home.js:58`；參數 `$2,$3 = 'tourgroup','travel'`。
  - 呼叫片段：
    ```sql
    inner join public.tour_travel_most_favorited($1,$2) as tf on tb.旅遊編號 = tf.tour_id
    ...
    ORDER BY 收藏排行 ASC LIMIT ... OFFSET ...
    ```
- **參數**（function 才有）：

  | 參數 | 型別 | 來源 | 語意 |
  |---|---|---|---|
  | 第 1 個 | text | `home.js:53,62` 寫死 `'tourgroup'` | 推測為「大分類」 |
  | 第 2 個 | text | `home.js:53,62` 寫死 `'travel'` | 推測為「小分類」 |

- **輸出欄位**：

  | 欄位（中文） | 型別 | 來源（表.欄位 或計算式） | 讀取位置 | 依據 |
  |---|---|---|---|---|
  | tour_id（英文） | uuid | `tour.tour_id` | `home.js:51,60` | JOIN 條件 |
  | 收藏排行 | bigint | 依 `favorite` 筆數由多到少的名次，1 為最多人收藏 | `home.js:52,61` | ORDER BY ASC |

- **列的語意**：符合 (大分類, 小分類) 的行程，各一列，附上被收藏次數的排行。只在 `type=tourgroup&item=most_favorited` 使用，因此程式碼只會用 `('tourgroup','travel')` 呼叫。
- **邊界**：與 `tour_travel_popular` 相同——欄位 `tour_id` 為英文；`INNER JOIN` 決定首頁是否出現。
- **信心**：參數與欄位名：確定。排名計算：推測；`bigint` 型別為推測（依 window function／COUNT 的回傳型別）。
- **待確認**：
  1. **沒有任何人收藏的行程要不要出現？**
     - 解讀 A：出現，排在最後。後果：新 DB 也有資料。
     - 解讀 B：不出現。後果：沒有 `favorite` 資料時首頁「最多收藏」回「查無資料」，P1b 的 seed 需要包含收藏紀錄。
  2. **並列名次與分頁穩定性**：同 `tour_travel_popular` 待確認 3（`RANK()` 與 `ROW_NUMBER()` 的後果相同）。
  3. **是否只回傳上架行程**：同 `tour_base` 待確認 1。

### `tour_tour_detail`

- **種類**：function（`tour_tour_detail(使用者編號 uuid) RETURNS TABLE(...)`）。證據：`product.js:202` 寫成 `${detailTable}($2) WHERE 旅遊編號 = $1`，被當函式呼叫（`$2` 是使用者編號，可為 `NULL`）。
- **使用位置**：
  - `controllers/product.js:194,196`（API：`GET /api/v1/user/product/search/:tour_id`；`tourgroup/travel` 與 `backpacker/spot` 共用此 function）。表名在 `product.js:194–198` 決定，執行在 `product.js:202`：
    ```sql
    SELECT * FROM public.tour_tour_detail($2) WHERE 旅遊編號 = $1
    ```
    參數 `[tour_id, id]`，`tour_id` 為 URL 參數，`id` 為 `req.user?.id`。
- **參數**（function 才有）：

  | 參數 | 型別 | 來源 | 語意 |
  |---|---|---|---|
  | 使用者編號 | uuid | `req.user.id`，未登入時 `NULL` | 計算 `收藏狀態` |

- **輸出欄位**（`旅遊編號` 是 `WHERE` 條件；其餘由 `product.js:296–366` 的 `travel`／`spot` 分支讀取）：

  | 欄位（中文） | 型別 | 來源（表.欄位 或計算式） | 讀取位置 | 依據 |
  |---|---|---|---|---|
  | 旅遊編號 | uuid | `tour.tour_id` | `product.js:202,298` | WHERE + response.tour_id |
  | 旅遊名稱 | varchar | `tour.title` | `product.js:299` | response.title |
  | 旅遊標語 | varchar | `tour.slogan` | `product.js:300` | response.title_slogan |
  | 大分類 | varchar | `tour.type` | `product.js:301` | response.type |
  | 小分類 | varchar | `tour.item` | `product.js:302` | response.item |
  | 旅遊代表圖 Url | text | `tour.cover_image` | `product.js:303` | response.image_url |
  | 旅遊圖1 描述 … 旅遊圖6 描述 | varchar | `tour.img1_desc … img6_desc` | `product.js:306–328` | response.image_spot[].description |
  | 旅遊圖1 Url … 旅遊圖6 Url | text | `tour.img1 … img6` | `product.js:306–328` | response.image_spot[].image_url |
  | 價錢 | integer | `tour.price` | `product.js:330` | response.price |
  | 旅遊開始日期 | timestamp | `tour.tour_start_date` | `product.js:331` | response.date_start |
  | 旅遊結束日期 | timestamp | `tour.tour_end_date` | `product.js:332` | response.date_end |
  | 特色圖1 描述 … 特色圖3 描述 | varchar | `tour_detail.feature_desc1…3` | `product.js:335–345` | response.feature[].description |
  | 特色圖1 url … 特色圖3 url | text | `tour_detail.feature_img1…3` | `product.js:335–345` | response.feature[].image_url（注意是小寫 `url`） |
  | 行程規劃 | text | `tour_detail.itinerary` | `product.js:347` | response.itinerary |
  | 所屬國家 | varchar | `tour.country` | `product.js:349` | response.location.country |
  | 所屬地區 | varchar | `tour.region` | `product.js:350` | response.location.region |
  | 地址 | text | `tour.address` | `product.js:351` | response.location.address |
  | Google Map Url | varchar | `tour.google_map_url` | `product.js:352` | response.location.google_map |
  | 旅遊描述 | text | `tour.description` | `product.js:354` | response.description |
  | 偏好設定分類 1 / 2 / 3（中間有空格） | smallint | `tour.preference1/2/3` | `product.js:209–211` | 反查中文標籤 → response.tags |
  | 收藏狀態 | boolean | `EXISTS (favorite WHERE user_id = 參數 AND tour_id = tour.tour_id)` | `product.js:356` | response.is_favorited |
  | 異動通知內容 | text | `notification.change_desc`（type='異動'） | `product.js:357` | response.emergency_notice |
  | 促銷價錢 | double precision | `notification.promo_price`（type='促銷'） | `product.js:359–360` | response.promotion.is_promoted（真偽）、promo_price |
  | 通知狀態 | varchar | `notification.type` | `product.js:361` | response.promotion.tag |
  | 促銷開始日期 | timestamp | `notification.start_date` | `product.js:362` | response.promotion.start_at |
  | 促銷結束日期 | timestamp | `notification.end_date` | `product.js:363` | response.promotion.end_at |

- **列的語意**：每個行程一列（`travel`、`spot` 都只讀 `rows[0]`），行程資料加上 `tour_detail`、通知資料，以及傳入使用者的收藏狀態。
- **邊界**：
  - 欄位命名不一致，必須照程式碼拼字：`偏好設定分類 1`（有空格，與 `tour_base` 的 `偏好分類1` 不同）、`特色圖1 url`（小寫）、`旅遊圖1 Url`（大寫）、`Google Map Url`。
  - `促銷價錢` 為 `NULL` 時 `is_promoted` 為 `false`（`product.js:359`），所以沒有促銷時必須是 `NULL`，不能是 `0`。
  - **找不到行程時的 controller 行為**（`product.js:178–202`）：先查 `tour` 的 `status = 1`；查不到（tour_id 不存在、已下架）或 type/item 不在對照表（例如 tourgroup 但 item 不是 travel）時 `detailTable` 維持 `''`，SQL 變成 `SELECT * FROM ($2) WHERE 旅遊編號 = $1`（`product.js:202`），PostgreSQL 回語法錯誤，API 回 500，永遠回不到「查無此旅遊項目」。`tour_hotel`、`tour_restaurant` 共用這段，同樣適用。
  - 行程存在、但 function 回 0 列時，`product.js:209` 讀 `rows[0]["偏好設定分類 1"]` 會先丟 TypeError（`rowCount > 0` 檢查在 `product.js:215`，在其後），API 一樣回 500。這只會在 `status = 1` 的行程被 function 濾掉（例如 `spot` 沒有 `tour_detail` 列而 `INNER JOIN`）時發生。
  - 以上為 controller 行為，契約不處理，只記錄。
  - 對 `tour_detail` 必須是 `INNER JOIN` 或 `LEFT JOIN`：`spot` 也用此 function 並讀特色圖（`product.js:335`），若 `spot` 行程沒有 `tour_detail` 列，`INNER JOIN` 會使整列消失（500），`LEFT JOIN` 則特色圖為 `NULL`。
- **信心**：欄位名稱與來源對應：確定。通知相關欄位的合併方式、`spot` 與 `tour_detail` 的關係：推測。
- **待確認**：
  1. **一個行程有多筆通知時**（同 `tour_base` 待確認 2）：本物件同時讀 `異動通知內容` 與 `促銷價錢`／`通知狀態`，因此兩者要在同一列。
     - 解讀 A：只取一筆通知。後果：促銷與異動只會顯示其一。
     - 解讀 B：促銷與異動分欄合併成一列。後果：兩者都能顯示；`通知狀態` 需另定規則。
     - 解讀 C：每筆通知一列。後果：`rows[0]` 取哪筆不固定，且 `hotel`／`food` 的 `rows.map` 會重複。
  2. **`spot` 行程是否保證有 `tour_detail` 列？**
     - 解讀 A：保證（`INNER JOIN`）。後果：seed 與新增商品流程必須為每個 spot 建 `tour_detail`，否則詳情頁 500。
     - 解讀 B：不保證（`LEFT JOIN`）。後果：沒有 `tour_detail` 時特色圖、行程規劃為 `NULL`，頁面可顯示。
  3. **只回傳上架行程？** 前面 `product.js:178–183` 已先以 `status = 1` 過濾，因此 function 內是否過濾不影響此 API，但影響其他未來呼叫端。解讀 A：過濾；解讀 B：不過濾。
  4. **`收藏狀態` 在未登入時是 `false` 還是 `NULL`**：同 `tour_travel` 待確認 3。

### `tour_hotel`

- **種類**：function（`tour_hotel(使用者編號 uuid) RETURNS TABLE(...)`）
- **使用位置**：
  - `controllers/product.js:197`（API：`GET /api/v1/user/product/search/:tour_id`，當行程 `type='backpacker'` 且 `item='hotel'`）。執行在 `product.js:202`：
    ```sql
    SELECT * FROM public.tour_hotel($2) WHERE 旅遊編號 = $1
    ```
    參數 `[tour_id, id]`。
- **參數**（function 才有）：

  | 參數 | 型別 | 來源 | 語意 |
  |---|---|---|---|
  | 使用者編號 | uuid | `req.user.id`，未登入時 `NULL` | 計算 `收藏狀態` |

- **輸出欄位**（`product.js:372–456`）：

  | 欄位（中文） | 型別 | 來源（表.欄位 或計算式） | 讀取位置 | 依據 |
  |---|---|---|---|---|
  | 旅遊編號 | uuid | `tour.tour_id` | `product.js:202,373` | WHERE + response.tour_id |
  | 旅遊名稱、旅遊標語、大分類、小分類、旅遊代表圖 Url | 同 `tour_tour_detail` | 同 `tour_tour_detail` | `product.js:374–378` | response.title / title_slogan / type / item / image_url |
  | 旅遊圖1–6 描述、旅遊圖1–6 Url | 同 `tour_tour_detail` | 同 `tour_tour_detail` | `product.js:381–403` | response.image_spot[] |
  | 價錢、旅遊開始日期、旅遊結束日期 | 同 `tour_tour_detail` | 同 `tour_tour_detail` | `product.js:405–407` | response.price / date_start / date_end |
  | 房型名稱 | varchar | `hotel_room.title` | `product.js:410` | response.feature.room[].name（逐列） |
  | 房型描述 | varchar | `hotel_room.image_desc`（推測） | `product.js:411` | response.feature.room[].description |
  | 房型容納人數 | integer | `hotel_room.capacity` | `product.js:412` | response.feature.room[].capacity |
  | 房型數量 | integer | `hotel_room.room_count` | `product.js:413` | response.feature.room[].room_count |
  | 房型代表圖 url（小寫 url） | text | `hotel_room.image` | `product.js:414` | response.feature.room[].image_url |
  | 基本設施與服務 | text | `hotel.facility_desc` | `product.js:419` | response.feature.service[0].item |
  | 餐飲相關服務 | text | `hotel.food_desc` | `product.js:423` | response.feature.service[1].item |
  | 客房與設施 | text | `hotel.room_desc` | `product.js:427` | response.feature.service[2].item |
  | 交通與停車 | text | `hotel.traffic_desc` | `product.js:431` | response.feature.service[3].item |
  | 其他便利服務 | text | `hotel.other_desc`（推測，見待確認 1） | `product.js:435` | response.feature.service[4].item |
  | 所屬國家、所屬地區、地址、Google Map Url、旅遊描述 | 同 `tour_tour_detail` | 同 `tour_tour_detail` | `product.js:440–445` | response.location / description |
  | 偏好設定分類 1 / 2 / 3 | smallint | `tour.preference1/2/3` | `product.js:209–211` | response.tags |
  | 收藏狀態、異動通知內容、促銷價錢、通知狀態、促銷開始日期、促銷結束日期 | 同 `tour_tour_detail` | 同 `tour_tour_detail` | `product.js:447–454` | response.is_favorited / emergency_notice / promotion |

- **列的語意**：**每個房型一列**（`hotel_room` 一列對應一列輸出），行程與飯店層級的欄位在每一列重複。依據：`product.js:409` 用 `tourDetailsRepo.rows.map(...)` 逐列產生 `room[]`；其他欄位只讀 `rows[0]`。
- **邊界**：
  - 沒有房型的飯店：`INNER JOIN hotel_room` 會使整間飯店消失；`LEFT JOIN` 會有一列、房型欄位為 `NULL`，response 的 `room` 會是一個全為 `null` 的物件。
  - 房型的先後順序沒有 `ORDER BY` 可供依據。
  - 欄位命名同樣不一致，必須照拼字：`房型代表圖 url`（小寫）。
- **信心**：欄位名稱：確定；來源對應：大部分確定，`房型描述`、`其他便利服務` 為推測。
- **待確認**：
  1. **`房型描述` 沒有明確來源**：`hotel_room` 只有 `image_desc`（圖片描述）。
     - 解讀 A：`房型描述 = hotel_room.image_desc`。後果：前端房型描述就是圖片說明文字。
     - 解讀 B：需新增 `hotel_room.description`（要改 migration）。後果：超出「V3 只建 view/function」範圍，需要另外新增欄位。
  2. **`hotel` 有 6 個描述欄位（`facility_desc`、`food_desc`、`room_desc`、`leisure_desc`、`traffic_desc`、`other_desc`），controller 只讀 5 個**：
     - 解讀 A：`其他便利服務 = other_desc`，`leisure_desc` 被忽略。後果：`leisure_desc` 的資料不會在 API 顯示。
     - 解讀 B：`其他便利服務 = leisure_desc`，`other_desc` 被忽略。後果：同樣有一個欄位資料被忽略，但被忽略的是另一個。
     - 解讀 C：兩者串接。後果：兩者都能顯示，但需要定分隔格式。
  3. **沒有房型的飯店是否出現**：解讀 A：`INNER JOIN`，飯店消失；解讀 B：`LEFT JOIN`，出現一列全為 `null` 的房型。
  4. **通知多筆時的處理**：同 `tour_tour_detail` 待確認 1；多筆通知與多房型相乘，若採解讀 C（每筆通知一列），`room[]` 會重複。

### `tour_restaurant`

- **種類**：function（`tour_restaurant(使用者編號 uuid) RETURNS TABLE(...)`）
- **使用位置**：
  - `controllers/product.js:198`（API：`GET /api/v1/user/product/search/:tour_id`，當 `type='backpacker'` 且 `item='food'`）。執行在 `product.js:202`：
    ```sql
    SELECT * FROM public.tour_restaurant($2) WHERE 旅遊編號 = $1
    ```
    參數 `[tour_id, id]`。
- **參數**（function 才有）：

  | 參數 | 型別 | 來源 | 語意 |
  |---|---|---|---|
  | 使用者編號 | uuid | `req.user.id`，未登入時 `NULL` | 計算 `收藏狀態` |

- **輸出欄位**（`product.js:222–290`）：

  | 欄位（中文） | 型別 | 來源（表.欄位 或計算式） | 讀取位置 | 依據 |
  |---|---|---|---|---|
  | 旅遊編號 | uuid | `tour.tour_id` | `product.js:202,222` | WHERE + response.tour_id |
  | 旅遊名稱、旅遊標語、大分類、小分類、旅遊代表圖 Url | 同 `tour_tour_detail` | 同 `tour_tour_detail` | `product.js:223–227` | response.title 等 |
  | 旅遊圖1–6 描述、旅遊圖1–6 Url | 同 `tour_tour_detail` | 同 `tour_tour_detail` | `product.js:230–252` | response.image_spot[] |
  | 價錢、旅遊開始日期、旅遊結束日期 | 同 `tour_tour_detail` | 同 `tour_tour_detail` | `product.js:254–256` | response.price / date_start / date_end |
  | 餐廳人員限制 | integer | `restaurant.reservation_limit` | `product.js:259` | response.feature.about.people |
  | 官網介紹 | text | `restaurant.website_info` | `product.js:260` | response.feature.about.description |
  | 官網 url（小寫 url） | varchar | `restaurant.website_url` | `product.js:261` | response.feature.about.web_url |
  | 菜單名稱 | varchar | `restaurant_menu.name` | `product.js:264` | response.feature.menu[].name（逐列） |
  | 菜單描述 | text | `restaurant_menu.description` | `product.js:265` | response.feature.menu[].description |
  | 菜單價錢 | double precision | `restaurant_menu.price` | `product.js:266` | response.feature.menu[].price |
  | 營業星期 | varchar | `restaurant_business.week` | `product.js:269` | response.feature.opening[].week（逐列） |
  | 營業時間 | text | `restaurant_business.business_hours` | `product.js:270` | response.feature.opening[].time |
  | 所屬國家、所屬地區、地址、Google Map Url、旅遊描述 | 同 `tour_tour_detail` | 同 `tour_tour_detail` | `product.js:274–279` | response.location / description |
  | 偏好設定分類 1 / 2 / 3 | smallint | `tour.preference1/2/3` | `product.js:209–211` | response.tags |
  | 收藏狀態、異動通知內容、促銷價錢、通知狀態、促銷開始日期、促銷結束日期 | 同 `tour_tour_detail` | 同 `tour_tour_detail` | `product.js:281–288` | response.is_favorited / emergency_notice / promotion |

- **列的語意**：同一個 function 的一列同時要供 `menu[]` 和 `opening[]` 使用——`product.js:263` 與 `product.js:268` 都是 `tourDetailsRepo.rows.map(...)`，各自讀同一組列的不同欄位。餐廳層級欄位在每列重複。
- **邊界**：
  - 依賴 V1 的 `restaurant_business`／`restaurant_menu`；程式碼另外查詢 `restaurant_business_parsed`（V1／V2 沒有，是 B 組物件，使用於 `middlewares/cart/index.js`），本物件是否使用它無法由 A 組程式碼證實。
  - 欄位命名必須照拼字：`官網 url`（小寫）、`官網介紹`、`餐廳人員限制`。
- **信心**：欄位名稱：確定；列的展開方式：推測（見待確認 1）。
- **待確認**：
  1. **`menu[]` 與 `opening[]` 共用 `rows`，列要怎麼展開？**
     - 解讀 A：`restaurant_menu` 與 `restaurant_business` 做 CROSS JOIN（菜單數 × 營業日數）。後果：兩個陣列各有大量重複項（例如 3 道菜 × 7 天 = 21 列，`menu[]` 與 `opening[]` 各 21 項）；程式碼不改的話前端會看到重複資料。
     - 解讀 B：用 `UNION ALL`／位置對齊，使每列各帶一筆菜單或一筆營業時間，不足的欄位為 `NULL`。後果：陣列內會有 `name: null` 或 `week: null` 的空項。
     - 解讀 C：每個餐廳一列，菜單與營業時間聚合進欄位（例如 JSON）。後果：`row.菜單名稱` 會是陣列／JSON，與 `rows.map` 的用法不符，controller 不改就無法使用。
  2. **沒有菜單或沒有營業時間的餐廳是否出現**：解讀 A：`INNER JOIN`，餐廳消失（500）；解讀 B：`LEFT JOIN`，空項為 `null`。
  3. **通知多筆時的處理**：同 `tour_tour_detail` 待確認 1。

### `user_user_level`

- **種類**：view（無參數）
- **使用位置**：
  - `controllers/product.js:495`（API：`GET /api/v1/user/product/search/:tour_id/reviews`）
    ```sql
    SELECT r.*,
           u.名稱,
           u."個人照片 Url",
           u.旅遊等級,
           u.旅遊等級名稱,
           u."旅遊徽章 Url"
    FROM public."review" r
    inner JOIN public."user_user_level" u ON r.user_id = u.使用者編號
    WHERE r.tour_id = $1
    ORDER BY r.created_at DESC
    LIMIT $2 OFFSET $3
    ```
  - `controllers/product.js:553`（API：`GET /api/v1/user/product/search/:tour_id/hidden-shares`）
    ```sql
    SELECT r.*,
           u.名稱,
           u."個人照片 Url",
           u.旅遊等級,
           u.旅遊等級名稱,
           u."旅遊徽章 Url"
    FROM public."hidden_play" r
    inner JOIN public."user_user_level" u ON r.user_id = u.使用者編號
    WHERE r.tour_id = $1
    ORDER BY r.created_at DESC
    LIMIT $2 OFFSET $3
    ```
- **輸出欄位**：

  | 欄位（中文） | 型別 | 來源（表.欄位 或計算式） | 讀取位置 | 依據 |
  |---|---|---|---|---|
  | 使用者編號 | uuid | `user.user_id` | `product.js:495,553` | JOIN `r.user_id = u.使用者編號` |
  | 名稱 | varchar | `user.name` | `product.js:511,567` | SELECT + response.name |
  | 個人照片 Url | varchar | `user.avatar_url` | `product.js:512,568` | SELECT + response.avatar |
  | 旅遊等級 | varchar | `user_level.level` | `product.js:515,571` | SELECT + response.level.level |
  | 旅遊等級名稱 | varchar | `user_level.name` | `product.js:514,570` | SELECT + response.level.name |
  | 旅遊徽章 Url | varchar | `user_level.badge_url` | `product.js:516,572` | SELECT + response.level.badge_icon |

  欄位名稱與 `user_level_point_coupon`（C 組，`userProfile.js:145–147` 讀 `旅遊等級`、`旅遊等級名稱`、`旅遊徽章 Url`）一致，跨組一致性在 Task 7 檢查。

- **列的語意**：每位使用者一列，包含使用者資料與其會員等級。
- **邊界**：
  - 是 `INNER JOIN` 還是 `LEFT JOIN` 在 view 內決定：`user_level` 在 V1 有 `user_id`，沒有 unique 約束；`level`、`name`、`badge_url` 在 V1 都是 `NULL` 可以空（註解「正式需要 not null」）。
  - 沒有 `user_level` 列的使用者，如果 view 用 `INNER JOIN`，他的評論與隱藏玩法在上述兩個 API 會被 controller 的 `inner JOIN` 一起濾掉。
  - `旅遊等級`（V1 是 `VARCHAR`）在 `product.js:571` 直接放入 `level.level`，型別為字串。
- **信心**：欄位名稱與來源：確定（V1 `user`／`user_level` 欄位一一對應）。JOIN 方式與重複列：推測。
- **待確認**：
  1. **使用者沒有 `user_level` 列時怎麼辦？**
     - 解讀 A：view 用 `INNER JOIN`（沒有等級資料就不在 view 內）。後果：該使用者的評論、隱藏玩法在商品頁消失；seed 必須為每個使用者建 `user_level`。（註冊流程 `userinfo.js:30,185` 會建立 `user_level`，所以正常註冊的使用者都有。）
     - 解讀 B：view 用 `LEFT JOIN`，等級欄位為 `NULL`。後果：評論仍顯示，`level` 物件內欄位為 `null`。
  2. **一個使用者有多筆 `user_level` 時？**（V1 沒有 unique）
     - 解讀 A：view 直接 JOIN，不處理。後果：該使用者的每筆評論重複出現（筆數 = 等級列數）。
     - 解讀 B：view 取最新一筆（`updated_at` 最大）。後果：評論不重複，但需要定義「最新」。

### `user_level_review_forHome`

- **種類**：view（無參數）
- **使用位置**：
  - `controllers/home.js:132`（API：`GET /api/v1/user/home/search/reviews`）
    ```sql
    select * from public."user_level_review_forHome" ORDER BY 評論時間 DESC LIMIT $1 OFFSET $2;
    ```
    參數 `[limit, (page - 1) * limit]`；整份 `reviewData.rows` 原樣放進 response（`home.js:141`）。
- **輸出欄位**：

  | 欄位（中文） | 型別 | 來源（表.欄位 或計算式） | 讀取位置 | 依據 |
  |---|---|---|---|---|
  | 評論時間 | timestamptz | `review.created_at` | `home.js:132` | ORDER BY（唯一在程式碼裡確定的欄位） |

  controller 沒有讀取其他 key，`SELECT *` 的欄位原樣輸出到 response，因此程式碼本身**無法證實**還需要哪些欄位。以下為依名稱與 `user_user_level`（同一組作者）合理推測的欄位，需要使用者確認（見待確認 1）：

  | 欄位（中文） | 型別 | 來源（推測） |
  |---|---|---|
  | 評論編號 | uuid | `review.review_id` |
  | 名稱 | varchar | `user.name` |
  | 個人照片 Url | varchar | `user.avatar_url` |
  | 旅遊等級 | varchar | `user_level.level` |
  | 旅遊等級名稱 | varchar | `user_level.name` |
  | 旅遊徽章 Url | varchar | `user_level.badge_url` |
  | 評分 | integer | `review.rating` |
  | 評論內容 | text | `review.content` |

- **列的語意**：（推測，見待確認 2）「網站整體好評」——`review` 中 `type = 'web'` 的評論（V1 註解：`type` 可以是 web / travel / hotel / food / spot；路由註解 `[GET] 編號 27 : 使用者查看此網頁好評內容`）。每則評論一列，附上評論者的名稱與等級。預設排序由 controller 決定（`評論時間 DESC`）。
- **邊界**：
  - `review.tour_id` 在 V1 可為 `NULL`，網站評論（`type='web'`）通常沒有 `tour_id`，所以 view 不能要求 `tour_id` 存在。
  - 評論者需有 `user_level` 才會出現的規則，同 `user_user_level` 待確認 1。
- **信心**：推測。controller 只證實 `評論時間`；其餘欄位與篩選條件都來自名稱與註解的推測。
- **待確認**：
  1. **欄位集合與欄位中文名稱**：程式碼沒有讀取任何 key，前端（P0 凍結的 `phase-0`）會依實際欄位名稱讀取。
     - 解讀 A：照上面的推測欄位建立。後果：若前端的欄位名稱不同，首頁好評區塊會缺資料，要在 V3 前核對 `frontend`（P1a 不動 frontend）。
     - 解讀 B：先查 frontend 實際讀取的 key 再定。後果：多花一道工，但欄位名稱正確。
  2. **篩選條件**：
     - 解讀 A：只含 `review.type = 'web'`。後果：首頁只顯示網站整體好評；若 seed 沒有 web 類評論，首頁好評區塊為空。
     - 解讀 B：含所有 `review`（不限 type）。後果：行程評論（travel／hotel／food／spot）也會顯示在首頁。
     - 解讀 C：只含評分達標（例如 `rating >= 4`）的評論，名稱中的「好評」。後果：需要另定門檻；低分評論不會出現。
  3. **評論者沒有 `user_level` 列時是否出現**：同 `user_user_level` 待確認 1（INNER vs LEFT JOIN）。

## 2. B 組：購物車、訂位、折扣、結帳

## 3. C 組：會員與後台

## 4. 待使用者確認
