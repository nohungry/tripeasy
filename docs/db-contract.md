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

> B 組共通觀察（各物件裡不再重複解釋）：
>
> - 路徑前綴：購物車 `/api/v1/user/trade/cart`（`routes/cart.js`）、折扣 `/api/v1/user/trade/discounts`（`routes/discounts.js`）、結帳 `/api/v1/user/checkout`（`routes/checkout.js`）、會員積分 `GET /api/v1/user/userinfo/pointslevel`（`routes/userProfile.js:32`）、管理者 `GET /api/v1/admin/members/:user_id/coupons`（`routes/admin.js:53`）。
> - 路徑相對於 `backend/src/`；SQL 原文的縮排已整理，內容未改。
> - 表格「依據」欄的「JS 讀取」指 controller／middleware 取 `row.<欄位>`；「WHERE」「ORDER BY」指 SQL 字串用到。
> - **pg 型別對應 JS 的限制（影響欄位型別選擇）**：`pg` 會把 `smallint`／`integer`／`float8` 回成 JS number，但 `bigint`（`COUNT(...)` 的型別）與 `numeric` 回成字串。凡是 controller 用 `=== 1`、`+`、`<` 直接運算的欄位，下面都標了型別，不能隨意換。
> - **識別字大小寫**：未加雙引號的名稱 PostgreSQL 會轉成小寫。程式碼用 `public."user_cartList"`（有引號）所以 view 要以**帶雙引號的混合大小寫**建立；`restaurant_isClosed(...)` 在程式碼沒有引號，所以 function 要以**小寫 `restaurant_isclosed`**（或不加引號的 `restaurant_isClosed`，兩者等價）建立，若用 `"restaurant_isClosed"`（有引號）建立則呼叫會失敗。
> - 跨組：`tour_base` 見 §1 `tour_base`；`user_user_level`（同樣有 `使用者編號`、`旅遊等級`…）見 §1 `user_user_level`。
> - **UUID 版本檢查（影響 seed 能否走通 API）**：下列驗證器只接受 `uuid({ version: 'uuidv4' })`（第三段開頭必須是 `4`、第四段開頭必須是 `8`／`9`／`a`／`b`）：`utils/Validator/cart_Validator.js:84`（`tour_id`）、`:92`（`cart_item_id`）、`utils/Validator/checkout_Vaildator.js:4`（`cart_id`）、`:12`（`order_id`）、`:71`（`discount.coupon_id`，`type='coupon'` 時）、`utils/Validator/discounts_Validatior.js:29`（`order_id`）、`utils/Validator/purchases_Validator.js:8`（`order_item_id`）。以 seed 逐項核對：`tour`（`db/seed/R__seed.sql:189` 起，10 筆）與 `coupon`（`db/seed/R__seed.sql:137` 起，5 筆）的主鍵全是手寫值，**一筆都不是 v4**；`cart`（6 筆）、`cart_item`（10 筆）、`orders`（5 筆）、`order_item`（10 筆）的主鍵都是 v4。後果：`POST /api/v1/user/trade/cart/:tour_id` 對任何 seed 行程都在驗證階段回 400，不論星期幾或時段；`PATCH /api/v1/user/checkout/preview/:order_id` 帶 seed 的 `coupon_id` 回 400。`PATCH /api/v1/user/trade/cart/:cart_item_id` 的 `tour_id` 取自 `cart_item`（不經驗證），所以對 seed 既有購物車項目仍可走到各 function。**這一點由使用者在 Task 7 決定**：改寫 seed 的 `tour`／`coupon` 主鍵為 v4（連同引用它們的外鍵），或放寬這些驗證器（`utils/Validator`，不是 controller，但仍是 P1a 以外的程式碼修改，需使用者同意）。
> - `orders`／`order_item` 的 `payment_status` 值（V1 `backend/migrations/V1__tripeasy_sql.sql:277`、`:292` 註解）：-1 資料剛建立、0 資料填寫完成未付款、1 已付款、2 已取消、3 已退款、4 付款逾時。`user_coupon.status`（V1 `:414` 註解）只定義 1 使用、0 未使用，但 `checkout.js:149` 另外寫入 -1（見 `user_couponList`）。

### `user_cartList`

- **種類**：view（無參數）
- **使用位置**：
  - `controllers/cart.js:202`（API：`GET /api/v1/user/trade/cart/list?page=&limit=&lang=`）
    ```sql
    select * from public."user_cartList"
          where user_id = $1
          ORDER BY cart_id ASC LIMIT $2 OFFSET $3;
    ```
    參數 `[id, limit, (page - 1) * limit]`，`id` 為 `req.user.id`。
- **輸出欄位**（`controllers/cart.js:208–226` 取 key）：

  | 欄位（中文） | 型別 | 來源（表.欄位 或計算式） | 讀取位置 | 依據 |
  |---|---|---|---|---|
  | user_id（英文） | uuid | `cart.user_id` | `controllers/cart.js:203` | WHERE |
  | cart_id（英文） | uuid | `cart.cart_id` | `controllers/cart.js:204,210` | ORDER BY + response.cart_id |
  | tour_id（英文） | uuid | `cart_item.tour_id` | `controllers/cart.js:211` | JS 讀取 → response.tour_id |
  | 大分類 | varchar | `tour_base.大分類`（即 `tour.type`） | `controllers/cart.js:212` | JS 讀取 → response.type |
  | 小分類 | varchar | `tour_base.小分類`（即 `tour.item`） | `controllers/cart.js:213` | JS 讀取 → response.item |
  | 旅遊名稱 | varchar | `tour_base.旅遊名稱` | `controllers/cart.js:214` | JS 讀取 → response.title |
  | 旅遊代表圖 Url | text | `tour_base."旅遊代表圖 Url"` | `controllers/cart.js:215` | JS 讀取 → response.image_url |
  | 價錢 | integer | `tour_base.價錢`（`tour.price`） | `controllers/cart.js:216` | JS 讀取 → response.price |
  | 促銷價錢 | double precision | `tour_base.促銷價錢`（`notification.promo_price`） | `controllers/cart.js:217` | JS 讀取 → response.promo_price（見待確認 2） |
  | quantity（英文） | integer | `cart_item.quantity` | `controllers/cart.js:219` | JS 讀取 → response.options.people |
  | start_date（英文） | timestamp | `cart_item.start_date` | `controllers/cart.js:220` | JS 讀取 → response.options.start_date |
  | end_date（英文） | timestamp | `cart_item.end_date`（V1 可 NULL） | `controllers/cart.js:221` | JS 讀取 → response.options.end_date |
  | room_type（英文） | varchar | `cart_item.room_type`（V1 可 NULL） | `controllers/cart.js:222` | JS 讀取 `item.room_type \|\| ''`，`NULL` 會被轉成 `''` |
  | singleTotal_Price（英文，混合大小寫，需雙引號） | numeric 或 double precision（推測） | 單一購物車項目的小計（見待確認 1） | `controllers/cart.js:224` | JS 讀取 `Number(item.singleTotal_Price)` → response.total_price，並加總成 summary.total_price（`controllers/cart.js:230`） |

  `cart_item_id` 不在 controller 讀取的 key 內（見邊界第 4 點）。

- **列的語意**：每個購物車項目（`cart_item`）一列，帶入所屬購物車（`cart.user_id`）與行程資料（`tour_base`）。預設排序由 controller 決定（`cart_id ASC`，沒有第二排序鍵）。
- **邊界**：
  - 對 `cart`／`cart_item` 必須是 `INNER JOIN`（`cart_item` 有 `cart_id` NOT NULL，V1 `:254–255`）。對 `tour_base`：若 `tour_base` 不含下架行程（§1 `tour_base` 待確認 1 解讀 B），INNER JOIN 會讓購物車裡已下架的項目消失，LEFT JOIN 則該列的中文欄位為 `NULL`，`Number(NULL)`＝0。
  - 欄位名稱混用英文與中文（`user_id`、`cart_id`、`quantity`、`singleTotal_Price` 是英文；`大分類`、`價錢` 等是中文），必須照程式碼拼字，`singleTotal_Price` 有大寫 T 與 P。
  - **controller 行為 1（分頁不穩定）**：`controllers/cart.js:204` 只 `ORDER BY cart_id ASC`。`post_cartItem` 把同一位使用者的項目都放進同一個 `cart_id`（`controllers/cart.js:46–55`），所以同一使用者所有列的排序鍵相同，`LIMIT/OFFSET` 在這種情況下沒有確定順序，翻頁可能重複或漏列。契約只記錄，不處理。
  - **seed 對照（UUID 版本）**：`GET /list` 本身不經 uuid 驗證，但 seed 行程的 `tour_id` 不是 v4，所以無法再用 `POST /cart/:tour_id` 加入任何 seed 行程（見共通觀察的「UUID 版本檢查」）；seed 既有的 `cart_item` 可由 `GET /list` 讀到。
  - **controller 行為 2（多購物車）**：`controllers/cart.js:15,46` 取使用者的 `cart`（`:15` 查詢，`:46` 讀 `user_cartRepo.rows[0]`），`controllers/cart.js:47–50` 的 `Update public."cart" ... where user_id = $1` 沒有限定 `cart_id`，會更新該使用者的**所有**購物車。V1 的 `cart` 沒有 `user_id` unique 約束，而 seed（`db/seed/R__seed.sql:765–772`）每位使用者有 2 個 `cart`（`a1b2...`、`b2c3...`、`c3d4...` 各 2 筆），所以對 seed 使用者加入購物車會同時改兩個購物車的 `total_price`。這是 controller／seed 的衝突，不是 view 的問題，但 view 會把兩個購物車的項目都列出。
  - **controller 行為 3（總額與小計各自計算）**：`cart.total_price`（`controllers/cart.js:31,49,110–111,164–170`）由 controller 在每次加入／刪除／修改時用「當下的」`price * 人數` 增減，`GET /list` 的 `summary.total_price` 則是各列 `singleTotal_Price` 的加總（`controllers/cart.js:230`），兩者不保證一致（促銷價改變後，刪除項目會用新價格扣舊價格加入的金額）。
  - **controller 行為 4（回傳不含 `cart_item_id`）**：`DELETE`／`PATCH /:cart_item_id` 需要 `cart_item_id`（`routes/cart.js:15,24`），但 `GET /list` 的 response（`controllers/cart.js:209–225`）沒有輸出 `cart_item_id`，即使 view 有這個欄位，前端也拿不到。view 是否提供 `cart_item_id` 無法由程式碼證實（見待確認 3）。
  - `end_date` 為 `NULL` 的項目（V1 允許，`cart_item.end_date` 為 `TIMESTAMP NULL`；seed 有這樣的列：`db/seed/R__seed.sql:776,785`）會直接輸出 `null`。
- **信心**：欄位名稱：確定（全部由 `controllers/cart.js:208–226` 讀取證實）；來源對應：大部分確定（V1 `cart`、`cart_item` 欄位一一對應）；`singleTotal_Price` 的計算與型別：推測。
- **待確認**：
  1. **`singleTotal_Price` 怎麼算？**（程式碼只讀它，沒有計算）
     - 解讀 A：`有效單價 × quantity`，有效單價＝促銷期間內用 `促銷價錢`，否則 `價錢`（與 `controllers/cart.js:19–22` 同一個 CASE）。後果：與 `cart.total_price` 的累計邏輯一致；促銷期間外項目自動回到原價。
     - 解讀 B：`價錢 × quantity`（永遠用原價）。後果：有促銷的項目小計大於實際 `cart.total_price` 所加的金額，`summary.total_price` 與 `cart.total_price` 不一致。
     - 解讀 C：`促銷價錢 × quantity`（`NULL` 時退回 `價錢`），不檢查促銷期間。後果：過期促銷的行程仍用促銷價。
     - 型別：若是 `numeric` 或 `bigint`，pg 回字串，所以 `Number(...)`（`controllers/cart.js:224`）是必要的；若是 `double precision` 則 `Number` 無害。controller 用 `Number()` 暗示型別不一定是 number。
  2. **`促銷價錢` 在沒有促銷或促銷已過期時是什麼？**（`controllers/cart.js:217` 原樣輸出 `promo_price`）
     - 解讀 A：永遠是 `notification.promo_price` 原值（`tour_base` 的 `促銷價錢`）。後果：過期促銷的項目仍會回傳 `promo_price`，前端要自己判斷期間。
     - 解讀 B：只有在促銷期間內才有值，否則 `NULL`。後果：前端以「有值」判斷是否促銷；方向與 §1 `tour_base` 待確認 4 解讀 B 相同（期間外不視為促銷），但 §1 待確認 4 談的是 `通知狀態`，不是 `促銷價錢`。
  3. **view 是否多帶 `cart_item_id` 等未被讀取的欄位？** 程式碼不讀，不影響現有 API。解讀 A：帶（建議，未來讓前端能刪除項目）。解讀 B：不帶。後果：前端目前拿不到 `cart_item_id`（見邊界第 4 點）的狀況不變。
  4. **與 `tour_base` 的 JOIN 方式**：見邊界第 1 點。解讀 A：INNER JOIN（下架行程的購物車項目消失）。解讀 B：LEFT JOIN（項目保留，行程欄位為 `NULL`，小計 0）。

### `hotel_booking`

- **種類**：function（`hotel_booking(房型 varchar, 入住日期 timestamp, 退房日期 timestamp, 旅遊編號 uuid) RETURNS TABLE(booking_count ..., room_count ...)`）。參數名稱為推測（controller 用位置參數）；型別依呼叫端傳入值推測。
- **使用位置**：
  - `middlewares/cart/index.js:52`（API：`POST /api/v1/user/trade/cart/:tour_id`，`item === 'hotel'`）
    ```sql
    select * from public.hotel_booking($1,$2,$3,$4);
    ```
    參數 `[options.room_type, options.start_date, options.end_date, tour_id]`（`middlewares/cart/index.js:53–56`）。
  - `middlewares/cart/index.js:187`（API：`PATCH /api/v1/user/trade/cart/:cart_item_id`，`item === 'hotel'`）
    ```sql
    select * from public.hotel_booking($1,$2,$3,$4);
    ```
    參數 `[options.room_type, options.start_date, options.end_date, tour_id]`（`middlewares/cart/index.js:188–191`），其中 `tour_id` 取自 `cart_item`（`middlewares/cart/index.js:183`）。
- **參數**：

  | 參數 | 型別 | 來源 | 語意 |
  |---|---|---|---|
  | 第 1 個 | varchar | `options.room_type`（`hotelSchema` 必填字串，`utils/Validator/cart_Validator.js:16`） | 房型名稱，對應 `hotel_room.title`（seed 例：`設計雙人房`、`豪華家庭房`，`db/seed/R__seed.sql:537–560`）。推測 |
  | 第 2 個 | timestamp | `options.start_date`（ISO 日期字串，`cart_Validator.js:7`） | 入住日期 |
  | 第 3 個 | timestamp | `options.end_date`（ISO 日期字串，`cart_Validator.js:11`，驗證器要求不早於 `start_date`） | 退房日期 |
  | 第 4 個 | uuid | `req.params.tour_id`（post）／`cart_item.tour_id`（patch） | 飯店所屬行程 |

- **輸出欄位**：

  | 欄位 | 型別 | 來源（表.欄位 或計算式） | 讀取位置 | 依據 |
  |---|---|---|---|---|
  | booking_count（英文） | integer 或 bigint | 該房型在指定日期區間內已被預訂的間數（見待確認 1） | `middlewares/cart/index.js:60,195` | JS 讀取 `rows[0].booking_count`，與 `room_count` 比較 |
  | room_count（英文） | integer | `hotel_room.room_count`（該房型總間數） | `middlewares/cart/index.js:61,196` | JS 讀取 `rows[0].room_count` |

  兩個欄位以 `>=` 比較（`middlewares/cart/index.js:62,197`）。若 `booking_count` 是 `bigint`（`COUNT(*)` 的型別），pg 回字串，JS 的 `>=` 會把字串轉成數字，比較結果仍正確。

- **列的語意**：每次呼叫回 0 或 1 列（controller 只讀 `rows[0]`）。1 列表示找得到該 (行程, 房型)，帶出已預訂數與總房數。
- **邊界**：
  - **0 列時略過檢查**：`middlewares/cart/index.js:59,194` 用 `booking_room.rowCount > 0` 才比較；找不到房型（例如 `room_type` 拼錯）時 function 回 0 列，controller 視為「有空房」，購物車項目仍會建立。function 的行為因此決定拼錯房型是否被擋：0 列＝放行，1 列且 `booking_count = 0, room_count = 0`＝擋下（`0 >= 0`）。見待確認 3。
  - `booking_count >= room_count` 時回「選擇的房間已無空房」（HTTP 400）。
  - 此 function 的 `start_date`／`end_date` 區間重疊的判定（含不含退房當日）程式碼沒有證據，見待確認 2。
  - **seed 對照（UUID 版本）**：`POST /cart/:tour_id` 的 `paramsSchema`（`middlewares/cart/index.js:10`、`cart_Validator.js:84`）要求 `tour_id` 為 uuidv4，seed 的行程都不是 v4，所以 POST 路徑對 seed 行程永遠走不到本 function；只有 PATCH 既有的 seed `cart_item`（`tour_id` 取自 `cart_item`）能呼叫它。見共通觀察。
  - PATCH 時（`middlewares/cart/index.js:187`）呼叫端沒有排除「被修改的這個項目自己」，若 function 把購物車內項目也算進 `booking_count`，使用者修改自己已在購物車的項目時會與自己衝突。見待確認 1。
- **信心**：參數順序與輸出欄位名：確定。`booking_count` 的計算方式、參數名稱與型別：推測。
- **待確認**：
  1. **`booking_count` 數什麼？**（程式碼只讀結果）
     - 解讀 A：數 `order_item` 中同一 (行程, 房型) 且日期區間與參數重疊的列，不看 `payment_status`。後果：連剛建立（-1）、已取消（2）、已退款（3）、付款逾時（4）的訂單都占房間，房間會被放棄的結帳占住。
     - 解讀 B：只數 `payment_status = 1`（已付款）。後果：只有真正付款的才占房；有人下單未付款時，其他人仍可加入購物車（超賣風險）。
     - 解讀 C：數 `payment_status IN (-1, 0, 1)`（排除 2、3、4；各值意義見 B 組共通觀察）。後果：保留未付款的訂單占房，已取消、已退款、逾時的釋放。
     - 解讀 D：數 `payment_status IN (0, 1)`（已填寫完成、已付款）。後果：排除「剛建立、還沒填寫」的訂單。
     - 解讀 E：數 `cart_item`（購物車內項目）而非訂單。後果：占房的是還沒結帳的購物車項目；PATCH 時要自己排除自己，否則修改會與自己衝突。
     - 解讀 F：`order_item` 與 `cart_item` 都數。後果：同一間房可能被同一人重複計算（購物車與已生成訂單各一次）。
  2. **日期區間重疊的判定**：
     - 解讀 A：半開區間 `[start_date, end_date)`，退房日當天可被下一位入住（一般飯店）。後果：同日退房入住不衝突。
     - 解讀 B：閉區間 `[start_date, end_date]`。後果：退房日當天仍算占房，連續住宿無法接續。
     - `order_item.start_date`／`end_date`（V1 `:296–297`）是 `timestamp`，不是 `date`，是否取到日期精度也要定。
  3. **找不到 (行程, 房型) 時回 0 列還是回 0／0？**
     - 解讀 A：回 0 列（`LEFT JOIN`／`WHERE` 沒有符合）。後果：`room_type` 拼錯時 `middlewares/cart/index.js:59` 的檢查被略過，項目被加入。
     - 解讀 B：回 1 列 `booking_count = 0, room_count = 0`（例如 `COALESCE`）。後果：拼錯房型會被「已無空房」擋下，錯誤訊息不準確但不會加入無效房型。
     - 解讀 C：丟例外。後果：API 回 500。

### `restaurant_booking`

- **種類**：function（`restaurant_booking(預約時間 timestamp, 旅遊編號 uuid) RETURNS TABLE(booking_count ..., reservation_limit ...)`）。參數名稱、型別為推測（controller 用位置參數）。
- **使用位置**：
  - `middlewares/cart/index.js:72`（API：`POST /api/v1/user/trade/cart/:tour_id`，`item === 'food'`）
    ```sql
    select * from public.restaurant_booking($1,$2);
    ```
    參數 `[options.start_time, tour_id]`（`middlewares/cart/index.js:73–74`）。
  - `middlewares/cart/index.js:207`（API：`PATCH /api/v1/user/trade/cart/:cart_item_id`，`item === 'food'`）
    ```sql
    select * from public.restaurant_booking($1,$2);
    ```
    參數 `[options.start_time, tour_id]`（`middlewares/cart/index.js:208–209`），`tour_id` 取自 `cart_item`（`middlewares/cart/index.js:183`）。
- **參數**：

  | 參數 | 型別 | 來源 | 語意 |
  |---|---|---|---|
  | 第 1 個 | timestamp（推測） | `options.start_time`（見邊界第 1 點：這個 key 實際上不存在，值恆為 `undefined`，pg 送出 `NULL`） | 預約時間 |
  | 第 2 個 | uuid | `req.params.tour_id`（post）／`cart_item.tour_id`（patch） | 餐廳所屬行程 |

- **輸出欄位**：

  | 欄位 | 型別 | 來源（表.欄位 或計算式） | 讀取位置 | 依據 |
  |---|---|---|---|---|
  | booking_count（英文） | integer 或 bigint | 該餐廳在該預約時間已預約的人數（見待確認 2） | `middlewares/cart/index.js:78,213` | JS 讀取 `rows[0].booking_count` |
  | reservation_limit（英文） | integer | `restaurant.reservation_limit` | `middlewares/cart/index.js:79,214` | JS 讀取 `rows[0].reservation_limit`（controller 內的變數名 `food_count`） |

  兩者以 `>=` 比較（`middlewares/cart/index.js:80,215`），成立時回「預約已額滿」（HTTP 400）。

- **列的語意**：每次呼叫回 0 或 1 列（controller 只讀 `rows[0]`）；1 列表示找得到該行程的餐廳，帶出已預約數與上限。
- **邊界**：
  - **controller 行為 1（呼叫參數 key 錯誤，已證實）**：`middlewares/cart/index.js:73` 與 `:208` 傳 `options.start_time`，但 food 的驗證器 `foodSchema`（`utils/Validator/cart_Validator.js:22–27`）只有 `start_date`，且 Joi object 預設不允許未知 key，帶 `start_time` 會被 `baseSchema.validate`（`middlewares/cart/index.js:9`）擋下回 400。所以透過 API 呼叫此 function 時，第 1 個參數**恆為 `NULL`**。結果：function 若用第 1 個參數比對預約時間（例如 `WHERE start_date = 參數`），永遠比對不到任何預約，`booking_count` 恆為 0（若回 1 列），額滿檢查等於永遠不會觸發。契約只記錄，不處理（controller 不改）。
  - `middlewares/cart/index.js:77,212` 用 `booking_food.rowCount > 0` 才比較，0 列時略過檢查。
  - **seed 對照（UUID 版本）**：`POST` 路徑對 seed 行程在驗證階段就回 400（`cart_Validator.js:84`），走不到本 function；只有 PATCH 既有 seed `cart_item` 能呼叫。見共通觀察。
  - 此 function 不檢查營業時間，營業時間由 `restaurant_business_parsed`（`middlewares/cart/index.js:91`）與 `restaurant_isClosed`（`middlewares/cart/index.js:105`）處理。
  - 加入購物車的 food 項目只存 `start_date`（`controllers/cart.js:40`），`quantity`（人數）也在 `cart_item`；`booking_count` 是否以人數加總見待確認 2。
- **信心**：參數順序與輸出欄位名：確定。參數 1 的實際內容（恆 `NULL`）：確定（驗證器與 controller 的 key 對照）。計算方式、型別：推測。
- **待確認**：
  1. **參數 1 恆為 `NULL` 時，function 要怎麼處理？**
     - 解讀 A：function 忽略參數 1，只以行程計算總預約數 vs. `reservation_limit`。後果：整個行程累計預約人數到上限就額滿，不分時段；與「預約時間」的語意不符，但有作用。
     - 解讀 B：function 以參數 1 比對時段（程式碼原意）。後果：參數恆為 `NULL`，永遠比對不到，額滿檢查形同虛設；要讓它有效必須改 controller 讀 `options.start_date`。
     - 解讀 C：function 在參數為 `NULL` 時回 0 列。後果：略過檢查（`rowCount > 0`），同 B 的結果。
  2. **`booking_count` 數什麼？**
     - 解讀 A：`order_item` 中該行程（`tour.item='food'`）的筆數，不看 `payment_status`。後果：已取消、已退款、逾時的訂單也占名額。
     - 解讀 B：`order_item.quantity` 加總（以人數計），與 `reservation_limit`（`restaurant.reservation_limit`，V1 `:129`，seed 為 50、30）同單位。後果：符合「人數限制」的語意（§1 `tour_restaurant` 把 `reservation_limit` 輸出成 `餐廳人員限制`，`response.feature.about.people`）。
     - 解讀 C：解讀 A 或 B 加上 `payment_status` 篩選（-1、0、1、2、3、4 的選法同 `hotel_booking` 待確認 1 解讀 B、C、D）。後果同該處。
     - 解讀 D：數 `cart_item`。後果：占名額的是尚未結帳的購物車項目。

### `restaurant_isClosed`

- **種類**：function（`restaurant_isclosed(預約時間 timestamp, 旅遊編號 uuid) RETURNS TABLE(isclosed boolean)`）。名稱在程式碼未加引號，PostgreSQL 會折成小寫 `restaurant_isclosed`。
- **使用位置**：
  - `middlewares/cart/index.js:105`（API：`POST /api/v1/user/trade/cart/:tour_id`，`item === 'food'`）
    ```sql
    select * from restaurant_isClosed($1,$2);
    ```
    參數 `[options.start_date, tour_id]`（`middlewares/cart/index.js:106–107`）。
  - `middlewares/cart/index.js:240`（API：`PATCH /api/v1/user/trade/cart/:cart_item_id`，`item === 'food'`）
    ```sql
    select * from restaurant_isClosed($1,$2);
    ```
    參數 `[options.start_date, tour_id]`（`middlewares/cart/index.js:241–242`），`tour_id` 取自 `cart_item`（`middlewares/cart/index.js:183`）。
- **參數**：

  | 參數 | 型別 | 來源 | 語意 |
  |---|---|---|---|
  | 第 1 個 | timestamp | `options.start_date`（ISO 字串，`foodSchema` 必填，`cart_Validator.js:23`） | 預約日期時間。注意參數順序是 (時間, 旅遊編號)，與 `hotel_booking` 的 (房型, 日期, 日期, 旅遊編號)、`restaurant_business_parsed` 的 (`tour_id` 在前) 都不同 |
  | 第 2 個 | uuid | `req.params.tour_id`／`cart_item.tour_id` | 餐廳所屬行程 |

- **輸出欄位**：

  | 欄位 | 型別 | 來源（表.欄位 或計算式） | 讀取位置 | 依據 |
  |---|---|---|---|---|
  | isclosed（英文，**必須全小寫**） | boolean | 該時間點是否休息（見待確認 1） | `middlewares/cart/index.js:110,245` | JS 讀取 `food_closed.rows[0].isclosed === true`，嚴格比較 `true` |

- **列的語意**：每次呼叫**必須回 1 列**。為 `true` 時回「此時段無營業」（HTTP 400，`middlewares/cart/index.js:111–115`）。
- **邊界**：
  - **controller 行為（0 列則 500）**：`middlewares/cart/index.js:110,245` 直接讀 `food_closed.rows[0].isclosed`，沒有 `rowCount` 檢查；function 若回 0 列，`rows[0]` 是 `undefined`，丟 TypeError，API 回 500。所以 function 在任何情況（包含找不到餐廳）都要回 1 列。
  - **欄位名稱大小寫**：pg 以欄位名的實際拼法當 key。程式碼讀 `isclosed`（小寫），function 的 `RETURNS TABLE` 欄位若寫成 `"isClosed"`（有引號）或 `isClosed`（無引號會折成小寫，OK），前者會讓 `rows[0].isclosed` 為 `undefined`，檢查永遠不成立。
  - **seed 對照（UUID 版本）**：`POST` 路徑對 seed 行程在驗證階段就回 400（`cart_Validator.js:84`），走不到本 function；只有 PATCH 既有 seed `cart_item` 能呼叫。見共通觀察。
  - 呼叫順序：同一請求先過 `restaurant_business_parsed`（`middlewares/cart/index.js:90–102`，不在營業時段就回「餐廳已關閉」），通過後才呼叫本 function；所以在營業時段內才可能走到這裡。V1／V2 沒有任何「公休日」「特殊休息日」的表（grep `closed|holiday|休` 在 `backend/migrations/` 沒有結果），本 function 能依據的資料只有 `restaurant_business` 與 `restaurant`。
- **信心**：參數順序、輸出欄位名與型別：確定。「休息」的判定方式：推測（見待確認）。
- **待確認**：
  1. **`isclosed` 依什麼判斷？**（V1 沒有公休日表）
     - 解讀 A：只看 `restaurant_business` 是否有對應星期（`week`）的列；沒有該星期的營業列＝公休。後果：與 `restaurant_business_parsed` 有部分重複（`parsed` 已過濾時段，但 `week` 缺列在 `parsed` 也會得到 0 列而先被擋下），本 function 在實務上永遠回 `false`。
     - 解讀 B：看 `restaurant_business.business_hours` 時段，判斷預約時間是否落在任一時段之外。後果：與 `parsed` 的判斷幾乎重複，通過 `parsed` 的請求必然 `false`。
     - 解讀 C：另外依某個尚未存在的公休日／特殊日資料（需要新增表，超出「V3 只建 view／function」的範圍）。後果：需要另外的 migration；沒有該表之前 function 無法實作。
     - 解讀 D：永遠回 `false`（占位）。後果：「此時段無營業」永遠不會觸發；其餘功能不受影響。
  2. **預約時間為 `NULL` 或餐廳不存在時**：解讀 A：回 1 列 `isclosed = false`（放行）。解讀 B：回 1 列 `isclosed = true`（擋下）。後果：A 讓不存在的 `tour_id` 也可加入購物車（`middlewares/cart/index.js:26` 已先確認 `tour` 存在，但不確認它有 `restaurant` 列）；B 擋下。丟例外則 API 回 500。

### `restaurant_business_parsed`

- **種類**：view（無參數）
- **使用位置**：
  - `middlewares/cart/index.js:91`（API：`POST /api/v1/user/trade/cart/:tour_id`，`item === 'food'`）
    ```sql
    SELECT * FROM restaurant_business_parsed 
           WHERE tour_id = $1 AND $2::timestamp::time BETWEEN start_time AND end_time 
           AND week = TRIM(TO_CHAR($2::timestamp, 'FMDay'));
    ```
    參數 `[tour_id, options.start_date]`（`middlewares/cart/index.js:94`）。
  - `middlewares/cart/index.js:226`（API：`PATCH /api/v1/user/trade/cart/:cart_item_id`，`item === 'food'`）
    ```sql
    SELECT * FROM restaurant_business_parsed 
           WHERE tour_id = $1 AND $2::timestamp::time BETWEEN start_time AND end_time 
           AND week = TRIM(TO_CHAR($2::timestamp, 'FMDay'));
    ```
    參數 `[tour_id, options.start_date]`（`middlewares/cart/index.js:229`）。
- **輸出欄位**（controller 只用 `rowCount`，下列欄位由 SQL 的 WHERE 證實）：

  | 欄位 | 型別 | 來源（表.欄位 或計算式） | 讀取位置 | 依據 |
  |---|---|---|---|---|
  | tour_id（英文） | uuid | `restaurant.tour_id`（經由 `restaurant_business.restaurant_id` → `restaurant.restaurant_id`） | `middlewares/cart/index.js:92,227` | WHERE `tour_id = $1` |
  | week（英文） | varchar | `restaurant_business.week` | `middlewares/cart/index.js:93,228` | WHERE `week = TRIM(TO_CHAR(..., 'FMDay'))`，右邊是英文全名（`Monday`…），seed 的 `week` 即 `Monday`…`Sunday`（`db/seed/R__seed.sql:478–491`） |
  | start_time（英文） | time | 由 `restaurant_business.business_hours` 的一個時段拆出的開始時間 | `middlewares/cart/index.js:92,227` | WHERE `$2::timestamp::time BETWEEN start_time AND end_time`，左邊是 `time` |
  | end_time（英文） | time | 同上的結束時間 | `middlewares/cart/index.js:92,227` | 同上 |

- **列的語意**：**每個 (餐廳, 星期, 營業時段) 一列**。`restaurant_business.business_hours` 是 TEXT，格式範例見 V1 `:145` 註解與 seed：`'11:00~14:00, 17:00~21:00'`（多時段）、`'17:00~23:00'`（單時段）（`db/seed/R__seed.sql:478–491`）。view 要把它拆成每個時段一列、轉成 `time`。controller 只用 `rowCount === 0` 判斷「餐廳已關閉」（`middlewares/cart/index.js:96,231`）。
- **邊界**：
  - 時段分隔用 `, `（逗號加空白），起訖用 `~`，格式來自 seed 與 V1 註解；程式碼本身沒有解析 `business_hours` 的位置。
  - `BETWEEN start_time AND end_time` 是閉區間，且不處理跨午夜。seed 有 `'17:00~00:00'`（`db/seed/R__seed.sql:489,490`，行程 `99999999-cccc-dddd-eeee-999999999999` 的星期五、星期六）。若 `end_time` 解析成 `00:00:00`，則 `start_time > end_time`，`BETWEEN` 永遠不成立，這兩天**所有**時間都會回「餐廳已關閉」。此判斷只在請求通過 uuid 驗證後才會執行；seed 行程用 POST 加入購物車在驗證階段就被擋下（見共通觀察），所以 seed 環境下實際走到本 view 的只有 PATCH 既有 `cart_item`。見待確認 2。
  - `week` 的比對是區分大小寫的字串比對：`TO_CHAR(..., 'FMDay')` 在 `lc_time` 為英文時回 `Monday` 這種首字大寫的英文名（`TRIM` 是因為沒有 `FM` 時會補空白）；若資料庫 `lc_time` 設成中文，會回中文而比對不到 seed 的英文 `week`。這是環境依賴，契約只記錄。
  - `options.start_date` 是帶時區的 ISO 字串時，`$2::timestamp` 會丟掉時區（以字串的牆上時間為準），所以時段以「使用者送出的牆上時間」判斷。
- **信心**：欄位名稱與型別：確定（SQL 字串直接使用）。拆解 `business_hours` 的細節（分隔符、跨午夜）：推測，依據 seed 與 V1 註解。
- **待確認**：
  1. **`business_hours` 無法解析（格式不符）的列怎麼辦？**
     - 解讀 A：view 忽略該列（不輸出）。後果：該餐廳該星期視為「已關閉」。
     - 解讀 B：view 解析失敗時丟例外。後果：整個 view 查詢失敗，所有餐廳的加入購物車都回 500。
  2. **跨午夜時段（seed 的 `17:00~00:00`）**：
     - 解讀 A：`00:00` 視為 `24:00`，轉成 `end_time = 23:59:59`。後果：星期五、星期六 17:00 到 23:59:59 可預約，`00:00` 之後不可。
     - 解讀 B：保持 `00:00:00`（原樣）。後果：這兩天任何預約都回「餐廳已關閉」（seed 的行程 `99999999-...`：PATCH 既有的 seed `cart_item` `c5cefe38-ff77-497c-b3fb-2831bbfb898c` 時，週五六的預約會被擋下；用 POST 加入該行程則不論星期幾都先被 uuidv4 驗證擋下，與本題無關，見共通觀察）。
     - 解讀 C：拆成兩列（`17:00~23:59:59` 與隔日的 `00:00~00:00`）。後果：需要把隔日時段記在下一個 `week`，view 較複雜。
  3. **沒有 `restaurant` 列的行程**：這類行程在 view 內沒有列，`rowCount === 0`，回「餐廳已關閉」（HTTP 400）。INNER JOIN 與 LEFT JOIN（時段為 `NULL`）在這個查詢下結果相同，因為 `NULL` 比不到 `BETWEEN`。契約不要求特別處理，只記錄這個行為。

### `user_couponList`

- **種類**：view（無參數）
- **使用位置**：
  - `controllers/checkout.js:144`（API：`PATCH /api/v1/user/checkout/preview/:order_id`，`discount.type === 'coupon'`）
    ```sql
    SELECT * FROM public."user_couponList" where coupon_id = $1 and user_id = $2
    ```
    參數 `[coupon_id, id]`。
  - `controllers/checkout.js:216`（API：`GET /api/v1/user/checkout/summary/:order_id`）
    ```sql
    select * from public."user_couponList" where user_id = $1 and order_id = $2 and status = -1
    ```
    參數 `[id, order_id]`。
  - `middlewares/discounts/index.js:41`（API：`POST /api/v1/user/trade/discounts/:order_id`，`type === 'coupon'`，驗證階段）
    ```sql
    SELECT * FROM public."user_couponList" where code = $1 and user_id = $2
    ```
    參數 `[req.body.discount.coupon, userId]`。
  - `middlewares/checkout/index.js:112`（API：`PATCH /api/v1/user/checkout/preview/:order_id`，驗證階段）
    ```sql
    SELECT * FROM public."user_couponList" where coupon_id = $1 and user_id = $2
    ```
    參數 `[req.body.discount.coupon_id, userId]`。
  - `controllers/discounts.js:14`（API：`POST /api/v1/user/trade/discounts/:order_id`，`type === 'coupon'`）
    ```sql
    SELECT * FROM public."user_couponList" where code = $1 and user_id = $2
    ```
    參數 `[discount.coupon, userId]`。
  - `controllers/admin.js:239`（API：`GET /api/v1/admin/members/:user_id/coupons`）
    ```sql
    select * from public."user_couponList" where user_id = $1
    ```
    參數 `[user_id]`；`result.rows` **整份原樣**放進 response 的 `dbdata`（`controllers/admin.js:248`），所以 view 的每一個欄位名稱都會成為管理者 API 的輸出 key。
- **輸出欄位**：

  | 欄位 | 型別 | 來源（表.欄位 或計算式） | 讀取位置 | 依據 |
  |---|---|---|---|---|
  | user_id（英文） | uuid | `user_coupon.user_id` | `controllers/checkout.js:144,216`、`middlewares/discounts/index.js:41`、`middlewares/checkout/index.js:112`、`controllers/discounts.js:14`、`controllers/admin.js:239` | WHERE |
  | coupon_id（英文） | uuid | `user_coupon.coupon_id`（等於 `coupon.coupon_id`） | `controllers/checkout.js:144`、`middlewares/checkout/index.js:112`、`controllers/checkout.js:241`、`controllers/discounts.js:29` | WHERE；JS 讀取 → response.discount.coupon_id |
  | code（英文） | varchar | `coupon.code` | `middlewares/discounts/index.js:41`、`controllers/discounts.js:14,31`、`controllers/checkout.js:242` | WHERE；JS 讀取 → response.discount.name／response.discount.coupon |
  | discount（英文） | double precision | `coupon.discount`（V1 `:58`，`FLOAT`） | `controllers/discounts.js:32,38`、`controllers/checkout.js:155` | JS 讀取，**乘上 `orders.total_price`**（見待確認 1） |
  | description（英文） | text | `coupon.description` | `controllers/discounts.js:33` | JS 讀取 → response.discount.description |
  | expire_date（英文） | timestamp | `coupon.expire_date`（V1 `:60`） | `middlewares/discounts/index.js:65`、`middlewares/checkout/index.js:136` | JS 讀取 `new Date(rows[0].expire_date)`，與現在時間比較 |
  | expired_date（英文，**多了 d**） | timestamp | `coupon.expire_date`（同一個值） | `controllers/discounts.js:34` | JS 讀取 → response.discount.date_period（見邊界與待確認 2） |
  | status（英文） | smallint | `user_coupon.status` | `middlewares/discounts/index.js:54`、`middlewares/checkout/index.js:125`、`controllers/checkout.js:216` | JS 讀取 `status === 1`；WHERE `status = -1` |
  | order_id（英文） | uuid | `user_coupon.order_id`（V1 可 NULL） | `controllers/checkout.js:216` | WHERE `order_id = $2` |

  `user_coupon` 沒有被 controller 直接讀的欄位（`user_coupon_id`、`created_at`、`updated_at` 等）是否也在 view 內，只有管理者 API（`controllers/admin.js:239`）會因為 `SELECT *` 而輸出，程式碼無法證實。

- **列的語意**：每個「使用者與優惠卷的綁定」（`user_coupon`）一列，帶入優惠卷內容（`coupon`）。**不過濾** `status`、也不過濾過期：
  - `middlewares/discounts/index.js:54`（回「優惠券已使用」409）與 `:65`（回「優惠券已過期」409）是在**取到列之後**才判斷；若 view 先濾掉已使用或已過期，這兩個分支永遠走不到，使用者只會看到「查無此優惠卷」404。
  - `controllers/checkout.js:216` 要取到 `status = -1` 的列，所以 `status` 為 -1 的也要在 view 內。
- **邊界**：
  - **controller 行為 1（`expired_date` 與 `expire_date` 兩種拼法）**：`middlewares/discounts/index.js:65` 與 `middlewares/checkout/index.js:136` 讀 `expire_date`，但 `controllers/discounts.js:34` 讀 `expired_date`。V1 `coupon` 欄位是 `expire_date`。view 只有 `expire_date` 時，`controllers/discounts.js:34` 取到 `undefined`，`date_period` 欄位在 JSON 裡不會出現（`JSON.stringify` 略過 `undefined`），不會報錯；view 只有 `expired_date` 時，`new Date(undefined)` 是 `Invalid Date`，`now > Invalid Date` 為 `false`，**過期檢查被靜默略過**（過期的優惠卷可以使用）。契約要求至少提供 `expire_date`；是否同時提供 `expired_date` 見待確認 2。
  - **controller 行為 2（-1 被當成「可再使用」）**：`controllers/checkout.js:148–151` 在 PATCH 預覽時把 `user_coupon.status` 設成 -1（V1 `:414` 註解只有 1／0），`middlewares/checkout/index.js:125` 與 `middlewares/discounts/index.js:54` 只擋 `status === 1`。**全 `backend/src` 沒有任何地方把 `status` 設成 1**（grep `user_coupon` 只有 `controllers/checkout.js:149`、`controllers/coupon.js:209`（新增綁定，`status` 寫 0）、`controllers/admin.js:271`（刪除綁定）、`middlewares/coupon/index.js:260,290`、`middlewares/admin/index.js:384`（只讀）），付款成功的 `newebpay.js` 也沒有。所以 seed 以外，status 永遠不會成為 1，-1 的優惠卷可以被重複套用到另一張訂單（`controllers/checkout.js:149` 會把 `order_id` 覆蓋成新訂單）。
  - **controller 行為 3（`code` 不是 unique）**：V1 `coupon.code` 沒有 unique 約束，`middlewares/discounts/index.js:41` 與 `controllers/discounts.js:14` 以 `code` + `user_id` 查詢並取 `rows[0]`；同一使用者綁定兩張 `code` 相同的優惠卷時，取到哪張不固定。
  - **controller 行為 4（驗證器與 seed 的 `code` 不相容）**：`utils/Validator/discounts_Validatior.js:9–13` 要求 `discount.coupon` 符合 `^[A-Z0-9]{6}$`（剛好 6 碼大寫英數），而 seed 的 5 個優惠卷代碼（`db/seed/R__seed.sql:143,152,161,170,179`）只有 `VIP300`（6 碼）符合，`WELCOME100`（10）、`SUMMER50`（8）、`TRAVEL10P`（9）、`SPRING20`（8）都會被 `POST /api/v1/user/trade/discounts/:order_id` 以 400 擋下（`type='coupon'` 路徑）。`PATCH /preview/:order_id` 雖然用 `coupon_id` 而非 `code`，但 `utils/Validator/checkout_Vaildator.js:71` 要求 `discount.coupon_id` 是 `uuid({ version: 'uuidv4' })`，seed 的 5 個 `coupon_id`（`db/seed/R__seed.sql` 的 coupon 區段，手寫值如 `11111111-aaaa-bbbb-cccc-111111111111`）第三段都不是 `4` 開頭，同樣會被 400 擋下（見共通觀察的「UUID 版本檢查」）。
  - **controller 行為 5（`discount` 的運算）**：`controllers/discounts.js:38` 與 `controllers/checkout.js:155` 都是 `orders.total_price * coupon.discount`，結果寫入／輸出為 `discount_price`（見待確認 1）。
  - 狀態以 JS 的 `=== 1` 比較，所以 `status` 必須是 `smallint`／`integer`，不能是 `bigint`／`numeric`／字串（pg 會回字串，嚴格比較失敗，已使用的優惠卷會被當成未使用）。
  - **seed 對照（UUID 版本）**：`PATCH /preview/:order_id` 的 `coupon_id` 要求 uuidv4（`checkout_Vaildator.js:71`），seed 的 5 個 `coupon_id` 都不是 v4，所以 seed 優惠卷走不到 `controllers/checkout.js:144` 與 `middlewares/checkout/index.js:112` 這兩處查詢；`POST /discounts/:order_id` 以 `code` 查詢（`middlewares/discounts/index.js:41`），seed 訂單 `order_id` 是 v4 可通過，但 `code` 受 `^[A-Z0-9]{6}$` 限制（上一點）。
  - 與 `user_level_point_coupon` 的 `優惠卷折扣`（見該物件）是同一個 `coupon.discount`，兩邊語意要一致。
  - `status` 完整可能值（程式碼與 seed 實際出現）：`0` 未使用（`controllers/coupon.js:209`、seed `db/seed/R__seed.sql:918`）、`1` 已使用（seed `:917,919,920`；程式碼只讀不寫）、`-1` 預覽中占用（只由 `controllers/checkout.js:149` 寫入）。
- **信心**：欄位名稱：確定（全部由程式碼讀取證實）；來源對應：確定（V1 `coupon`、`user_coupon` 欄位一一對應）；`expired_date` 是否存在：推測；`status` 篩選：確定（不篩選）。
- **待確認**：
  1. **（spec 3.1 已知問題 2）`coupon.discount` 是折扣倍率還是折抵金額？**
     - **程式碼對它做的運算（所有位置）**：
       - `controllers/discounts.js:38`（`POST /user/trade/discounts/:order_id`，回傳 response）：`discount_price: orderRepo.rows[0].total_price * couponRepo.rows[0].discount`。
       - `controllers/checkout.js:155`（`PATCH /user/checkout/preview/:order_id`，**寫入 `orders.discount_price`**）：`UPDATE public."orders" SET discount_price = $1 ...`，參數 `orderRepo.rows[0].total_price * couponRepo.rows[0].discount`。
       - `controllers/discounts.js:32`、`controllers/userProfile.js:156`：原樣輸出 `discount`（沒有運算）。
       - 沒有任何地方做 `total_price - discount`、`discount / 100` 或 `1 - discount`。
     - **寫入位置（`coupon.discount` 怎麼進來）**：
       - `controllers/coupon.js:6`（解構 `req.body.discount_amount`）、`:10–12`（`INSERT INTO public.coupon (code, discount, description, expire_date) VALUES ($1, $2, $3, $4)`，`$2` ＝ `discount_amount`）：`POST /api/v1/admin/coupons`。
       - `controllers/coupon.js:103`（解構 `req.body.discount_amount`）、`:107–108`（`update coupon set code = $1,discount = $2,description = $3,expire_date = $4 where coupon_id = $5`，`$2` ＝ `discount_amount`）：`PATCH /api/v1/admin/coupons/update/:coupon_id`。
       - 驗證器 `utils/Validator/coupon_Validator.js:45`：`discount_amount: Joi.number().greater(0)`，錯誤訊息是「優惠折扣數」，**沒有上限**（沒有 `.max(...)`）。
       - 管理者端的請求欄位叫 `discount_amount`（字面是「折扣金額」），但訊息文字叫「優惠折扣數」；欄位名與訊息各自偏向不同解讀，不能由此決定。
       - `grep '\.discount'` 在這兩個 controller 的其他命中行都不是對 `coupon.discount` 的運算：`controllers/discounts.js:99`、`controllers/checkout.js:188,265` 只是輸出 `orders.discount_price`；`controllers/checkout.js:124` 是解構 `req.body.discount`；`controllers/checkout.js:240` 讀 `orders.discount_type`。
     - **seed 裡實際的值**（`db/seed/R__seed.sql:137–186`，`coupon.discount` 欄位）：

       | code | `discount` | `description` | 位置 |
       |---|---|---|---|
       | `WELCOME100` | `100.0` | 首次註冊禮，折抵新台幣 100 元 | `db/seed/R__seed.sql:143–145` |
       | `SUMMER50` | `50.0` | 夏日旅遊季，折抵新台幣 50 元 | `db/seed/R__seed.sql:152–154` |
       | `TRAVEL10P` | `10.0` | 旅遊商品 10% 折扣 (最高折抵 500 元) | `db/seed/R__seed.sql:161–163` |
       | `VIP300` | `300.0` | 尊榮會員專屬，折抵新台幣 300 元 | `db/seed/R__seed.sql:170–172` |
       | `SPRING20` | `20.0` | 春季限定，旅遊折抵新台幣 20 元 | `db/seed/R__seed.sql:179–181` |

       五個值都 > 1。以 `total_price * discount` 計算：`total_price` 3576.74、`discount` 100.0 → `discount_price` 357,674。沒有任何一個 seed 值落在 0 到 1 之間。
     - **相關事實**：`orders.discount_price`（V1 `:279`，`FLOAT NULL`）在 `controllers/checkout.js:155`（優惠卷）與 `controllers/checkout.js:165`（點數：`total_price - used_point * 0.8`，見 `user_level_point_coupon` 待確認 1）寫入的都是同一欄；後者的運算形式（`total_price - ...`）算出來的是「折扣後應付金額」。seed 的 `orders.discount_price`（`db/seed/R__seed.sql:790–794`，例如 `total_price` 3576.74 對 `discount_price` 794.83）都小於 `total_price`，看起來像「折掉的金額」，與程式碼寫入的「應付金額」語意不同；`discount_type` 在 seed 是 `'none'`、`'earlybird'`（`:790–794`），程式碼只寫 `'coupon'`／`'point'`，或在 `type` 省略時寫 `NULL`（`checkout_Vaildator.js:64–67` 的 `discount` 與 `type` 都是 `.optional()`；`controllers/checkout.js:133–134`）。這些只是觀察，不能由此決定 `coupon.discount` 的語意。
     - 解讀 A：**折扣倍率**（`discount` 在 0 到 1，例如 `0.9` 表示九折，`discount_price` 為折扣後應付金額）。後果：結帳計算（`discounts.js:38`、`checkout.js:155`）不用改，與 `controllers/checkout.js:165` 的「`discount_price` 是折扣後應付金額」一致；但 admin 寫入端的驗證器（`coupon_Validator.js:45`）只要求 `> 0`、沒有上限，管理者仍可建立 `discount = 100` 的優惠卷，結帳照樣算出數百倍金額，要擋住需另外給驗證器加 `.max(1)`；請求欄位名 `discount_amount` 也與倍率語意不符。另外 seed 的 5 個值（100.0、50.0、10.0、300.0、20.0）全部要改成倍率（例如 `0.9`），`description` 的「折抵新台幣 100 元」也要改；P1b 的 seed 要跟著動。
     - 解讀 B：**折抵金額**（NT$，與 seed 的 `description` 文字一致：100、50、300、20）。後果：seed 不用改，admin 寫入端的 `discount_amount > 0` 且無上限（`coupon_Validator.js:45`）與金額語意相容、欄位名也一致；但 `controllers/discounts.js:38` 與 `controllers/checkout.js:155` 的 `total_price * discount` 算出來是金額的幾百倍（上例 357,674），需要改 controller 為 `total_price - discount`，違反「controller 不改」；若不改，結帳會寫入錯誤的 `orders.discount_price`。`TRAVEL10P` 的 `10.0` 在此解讀下只折抵 10 元，與其 `description`「10% 折扣 (最高折抵 500 元)」矛盾。
     - 解讀 C：**混合**（`TRAVEL10P` 是百分比 `10` ＝ 10%，其餘是金額）。後果：與 seed 的 `description` 全部吻合，但同一欄位兩種語意，程式碼的 `total_price * discount` 兩種都算錯；要靠 `description` 或新增欄位區分類型（V1 沒有類型欄位，需改 migration）；admin 寫入端的驗證器（`coupon_Validator.js:45`）只檢查 `> 0`，無法區分百分比與金額。
     - 解讀 D：**折扣百分比**（`discount` 是 0–100，`10` ＝ 打 9 折）。後果：seed 的 5 個值都需要改成 0–100 以內的百分比（100 以上沒有意義）；程式碼要改成 `total_price * (1 - discount / 100)`；admin 驗證器（`coupon_Validator.js:45`）無上限，需補 `.max(100)`。
  2. **`expired_date`（`controllers/discounts.js:34`）要不要提供？**
     - 解讀 A：只提供 `expire_date`。後果：`POST /user/trade/discounts/:order_id` 的 response 少了 `date_period`，前端若依賴它會顯示空白。
     - 解讀 B：`expire_date` 與 `expired_date` 兩個都提供（同值）。後果：response 有 `date_period`，admin API（`SELECT *`）會多一個重複欄位。
  3. **`status = -1` 的列要不要出現在管理者 API 與其他查詢中？**
     - 解讀 A：全部出現（如目前所推）。後果：管理者看到 -1。
     - 解讀 B：view 把 -1 換算成別的顯示值。後果：`controllers/checkout.js:216` 的 `status = -1` 失效，結帳摘要看不到已套用的優惠卷。
  4. **同一個 (使用者, `code`) 有多筆時**：V1 有 `UNIQUE (user_id, coupon_id)`（V1 `:420`）但 `code` 不 unique。解讀 A：不處理。後果：取 `rows[0]` 不固定。解讀 B：view 只取最新一筆。後果：需另定規則。

### `user_level_point_coupon`

- **種類**：view（無參數）
- **使用位置**：
  - `controllers/userProfile.js:125`（API：`GET /api/v1/user/userinfo/pointslevel`）
    ```sql
    SELECT * FROM public."user_level_point_coupon" where 使用者編號 = $1
    ```
    參數 `[user.id]`；整份 `result.rows` 依 `row['使用者編號']` 分組（`controllers/userProfile.js:130–161`）。
  - `controllers/discounts.js:44`（API：`POST /api/v1/user/trade/discounts/:order_id`，`type === 'point'`）
    ```sql
    SELECT * FROM public."user_level_point_coupon" where 使用者編號 = $1
    ```
    參數 `[userId]`。
  - `middlewares/discounts/index.js:77`（API：同上，驗證階段）
    ```sql
    SELECT * FROM public."user_level_point_coupon" ucl where 使用者編號 = $1
    ```
    參數 `[userId]`。
  - `middlewares/checkout/index.js:148`（API：`PATCH /api/v1/user/checkout/preview/:order_id`，驗證階段）
    ```sql
    SELECT * FROM public."user_level_point_coupon" ucl where 使用者編號 = $1
    ```
    參數 `[userId]`。
- **輸出欄位**：

  | 欄位（中文） | 型別 | 來源（表.欄位 或計算式） | 讀取位置 | 依據 |
  |---|---|---|---|---|
  | 使用者編號 | uuid | `user.user_id` | `controllers/userProfile.js:133,137`、`controllers/discounts.js:44`、`middlewares/discounts/index.js:77`、`middlewares/checkout/index.js:148` | WHERE；分組鍵；response.user_id |
  | 名稱 | varchar | `user.name` | `controllers/userProfile.js:138` | JS 讀取 → response.name |
  | 信箱 | varchar | `user.email` | `controllers/userProfile.js:139` | JS 讀取 → response.email |
  | 角色 | varchar | `user.role` | `controllers/userProfile.js:140` | JS 讀取 → response.role |
  | 個人照片 Url | varchar | `user.avatar_url` | `controllers/userProfile.js:141` | JS 讀取 → response.avatar_url |
  | 個人偏好 1 | smallint | `user.preference1` | `controllers/userProfile.js:142` | JS 讀取 → response.preference1（欄位名有空格） |
  | 個人偏好 2 | smallint | `user.preference2` | `controllers/userProfile.js:143` | 同上 |
  | 個人偏好 3 | smallint | `user.preference3` | `controllers/userProfile.js:144` | 同上 |
  | 旅遊等級 | varchar | `user_level.level` | `controllers/userProfile.js:145` | JS 讀取 → response.level（欄位名稱與 §1 `user_user_level` 一致） |
  | 旅遊等級名稱 | varchar | `user_level.name` | `controllers/userProfile.js:146` | JS 讀取 → response.level_name |
  | 旅遊徽章 Url | varchar | `user_level.badge_url` | `controllers/userProfile.js:147` | JS 讀取 → response.badge_url |
  | 使用者旅遊積分 | integer | 見待確認 1（`user_level.travel_point` 或 `point_record` 加總） | `controllers/userProfile.js:148`、`controllers/discounts.js:60,62`、`middlewares/discounts/index.js:89`、`middlewares/checkout/index.js:160` | JS 讀取，做 `<`、`-` 運算；response.travel_point／user_point |
  | 優惠卷編號 | uuid | `coupon.coupon_id` | `controllers/userProfile.js:154` | JS 讀取 → response.coupon[].coupon_id |
  | 優惠卷代碼 | varchar | `coupon.code` | `controllers/userProfile.js:155` | JS 讀取 → response.coupon[].code |
  | 優惠卷折扣 | double precision | `coupon.discount` | `controllers/userProfile.js:156` | JS 讀取 → response.coupon[].discount（語意見 `user_couponList` 待確認 1） |
  | 優惠卷描述 | text | `coupon.description` | `controllers/userProfile.js:157` | JS 讀取 → response.coupon[].description |
  | 優惠卷期限 | timestamp | `coupon.expire_date` | `controllers/userProfile.js:158` | JS 讀取 → response.coupon[].expire_date |

  `使用者旅遊積分` 在 `middlewares/discounts/index.js:89`、`middlewares/checkout/index.js:160` 以 `<` 與 `used_point`／`point` 比較，在 `controllers/discounts.js:62` 做減法；若是 `bigint`／`numeric`（例如 `SUM(...)` 的結果），pg 回字串，`<` 與 `-` 會自動轉成數字不會出錯，但輸出到 response 時（`controllers/discounts.js:60`、`controllers/userProfile.js:148`）會變成 JSON 字串，與 `integer` 時的數字不同。

- **列的語意**：**每位使用者的每張優惠卷一列**（使用者與會員等級的資料在每一列重複）。依據：`controllers/userProfile.js:133–160` 以 `使用者編號` 分組，第一次出現時建立使用者物件，每一列再 `push` 一張優惠卷。
- **邊界**：
  - **沒有優惠卷的使用者（關鍵）**：
    - 若 view 對優惠卷用 `LEFT JOIN`：使用者得到 1 列，優惠卷欄位全為 `NULL`；`controllers/userProfile.js:153–159` 沒有檢查，會 `push` 一個全為 `null` 的優惠卷物件，response 的 `coupon` 是 `[{coupon_id: null, code: null, ...}]`。
    - 若用 `INNER JOIN`：沒有優惠卷的使用者在 view 內完全沒有列，`GET /pointslevel` 回 `[]`（`controllers/userProfile.js:162`），而且 `middlewares/discounts/index.js:81–89` 與 `middlewares/checkout/index.js:152–160` 的 `pointRepo.rowCount === 0` 會回 409「查無可使用的點數」，**即使使用者有積分也無法使用點數折抵**。
  - 沒有 `user_level` 列的使用者：INNER JOIN 時同樣消失（理由同 §1 `user_user_level` 待確認 1）。
  - controller 在 `controllers/discounts.js:60,62` 與兩個 middleware 都只讀 `pointRepo.rows[0].使用者旅遊積分`，所以每一列的 `使用者旅遊積分` 必須相同（同一個使用者的值不隨優惠卷變動）。
  - 欄位名稱必須照程式碼拼字：`個人偏好 1`（有空格，與 §1 `tour_base` 的 `偏好分類1` 不同）、`個人照片 Url`、`旅遊徽章 Url`；`優惠卷` 用「卷」不是「券」（與 `優惠券已使用` 的訊息用字不同）。
  - 是否包含已使用／已過期的優惠卷：見待確認 3。
- **信心**：欄位名稱：確定（全部由 `controllers/userProfile.js:137–158` 與其他三處的 `使用者編號`、`使用者旅遊積分` 證實）；來源對應：除 `使用者旅遊積分` 外為確定。`使用者旅遊積分` 的來源：推測（見待確認 1）。
- **待確認**：
  1. **（spec 3.1 已知問題 1）點數的累積和扣抵規則，以及 `point * 0.8` 的意義。**

     **a. 點數存在哪個欄位？** V1 有兩個地方：`user_level.travel_point`（INT NULL，V1 `:45`）與 `point_record.point`（INT NOT NULL，V1 `:399`，每筆異動一列，`type` 為 VARCHAR(50) NOT NULL，V1 沒有註解 `type` 可有哪些值）。點數餘額有**兩條讀取路徑**：(1) 本 view 的 `使用者旅遊積分`（`GET /api/v1/user/userinfo/pointslevel`、折抵驗證、折抵 response）；(2) `controllers/userinfo.js:56`（註冊 response）、`:117`（email 登入）、`:228`（Google 登入）、`:356`（`GET /api/v1/auth/userinfo/login/status`）直接輸出 `user_level.travel_point` 為 `level.points`，不經過 view。所以 view 取哪一個欄位，會決定兩條路徑顯示的餘額是否一致：
     - 解讀 A：`user_level.travel_point`。後果：餘額只與 `user_level` 有關，`point_record` 是流水帳但不影響餘額；而**全 `backend/src` 沒有任何 UPDATE `travel_point`**（下表），所以餘額在註冊後永遠是 0（`userinfo.js:30,185` 寫 0），除了 seed 手動設的 1500／3000／800（`db/seed/R__seed.sql:108,119,130`）。與 `userinfo.js` 四處的 `level.points` 一致（同一欄位）。
     - 解讀 B：`SUM(point_record.point)`（全部類型）。後果：`'減少_確認中'`（`controllers/checkout.js:160` 寫入）立即從餘額扣掉，使用者在預覽後馬上看到餘額減少；同一個預覽重複 PATCH 會重複扣（見下表第 5 項）。與 `userinfo.js` 四處的 `level.points`（讀 `travel_point`）**不一致**：預覽後 `pointslevel` 與折抵檢查的餘額減少，登入／登入狀態 response 的 `points` 不變。
     - 解讀 C：`SUM(point_record.point)` 但排除 `'減少_確認中'`。後果：預覽階段不影響餘額；但付款確認後沒有任何程式把 `'減少_確認中'` 轉成 `'減少'`（見下表），所以餘額永遠不會因為使用點數而減少。餘額與 `userinfo.js` 四處的 `level.points` 在 `point_record` 加總不等於 `travel_point` 時（seed 使用者 `c3d4...` 即是）**不一致**。
     - 解讀 D：`user_level.travel_point` 加上 `SUM(point_record.point WHERE type = '減少_確認中')`（即餘額扣掉預扣）。後果：預扣即時生效，但付款完成前沒有人把 `travel_point` 真正扣掉；`pointslevel`／折抵檢查看到的餘額（扣掉預扣）與 `userinfo.js` 四處的 `level.points`（未扣預扣的 `travel_point`）**不一致**。
     - **seed 與兩個來源不一致的實例**：使用者 `c3d4e5f6-7890-abcd-ef12-34567890abcd` 的 `travel_point` 是 800（`db/seed/R__seed.sql:130`），但 `point_record` 有 `'新增' 1610` 與 `'減少' -436`（`db/seed/R__seed.sql:908,909`），加總 1174。`pointslevel` 與折抵檢查：解讀 A 回 800，B／C 回 1174，D 為 800 加上預扣（seed 無 `減少_確認中` 列，所以也是 800）；`userinfo.js` 四處的 `level.points` 一律回 800。因此解讀 B／C 下，同一位使用者登入 response 顯示 800、`pointslevel` 顯示 1174。

     **b. 什麼時候增加或扣除？程式碼中所有寫入點，以及相關的讀取**（grep `point_record`、`travel_point` 於 `backend/src` 與 seed；第 6 列是 SELECT，餘額讀取見上方 a，`userinfo.js:56,117,228,356` 為讀取 `travel_point`）：

     | # | 位置 | 對象 | 內容 | 時機 |
     |---|---|---|---|---|
     | 1 | `controllers/userinfo.js:30` | `user_level.travel_point` | INSERT，值 `0` | 註冊（`POST /api/v1/auth/userinfo/signup`） |
     | 2 | `controllers/userinfo.js:36` | `point_record` | INSERT `(user_id, type='新增', point=0)` | 註冊 |
     | 3 | `controllers/userinfo.js:185` | `user_level.travel_point` | INSERT，值 `0` | Google 首次登入建立使用者（`POST /api/v1/auth/userinfo/login/google`） |
     | 4 | `controllers/userinfo.js:189` | `point_record` | INSERT `(user_id, type='新增', point=0)` | Google 首次登入建立使用者（`POST /api/v1/auth/userinfo/login/google`） |
     | 5 | `controllers/checkout.js:158–161` | `point_record` | INSERT `(user_id, order_id, type='減少_確認中', point = 0 - used_point)` | `PATCH /api/v1/user/checkout/preview/:order_id` 且 `discount.type === 'point'`；沒有檢查是否已有同訂單的 `減少_確認中`，每次 PATCH 都新增一列 |
     | 6 | `controllers/checkout.js:221` | `point_record` | SELECT `type = '減少_確認中'` | `GET /api/v1/user/checkout/summary/:order_id`，取 `rows[0].point` 的絕對值當 `used_point` |
     | 7 | `db/seed/R__seed.sql:108,119,130` | `user_level.travel_point` | seed 值 1500、3000、800 | seed |
     | 8 | `db/seed/R__seed.sql:908,909` | `point_record` | `'新增' 1610`、`'減少' -436`，皆屬訂單 `f4977608-...`（該訂單 `total_price` 1610.73、`discount_price` 436.75，`db/seed/R__seed.sql:792`） | seed |

     結論（皆可由 grep 證實）：
     - **沒有任何程式碼增加點數**（只有註冊時的 0）。付款成功（`controllers/newebpay.js:163–217` 只更新 `payment`、`orders.payment_status`、`order_item`）不會新增點數。
     - **沒有任何程式碼 UPDATE `user_level.travel_point`**。
     - **沒有任何程式碼把 `'減少_確認中'` 轉成 `'減少'`**，也沒有取消／逾時時回補。
     - 唯一與「累積」有關的是 `controllers/checkout.js:225` 的 `get_point = orderRepo.rows[0].total_price * 0.1`，只放進 `GET /summary/:order_id` 的 `summary.get_point`（`controllers/checkout.js:266`）顯示「可得點數」，**沒有寫入任何表**。
     - `GET /api/v1/user/trade/discounts/:order_id`（編號 33，標題「使用者取消優惠卷、累積積分」，`controllers/discounts.js:78–115`）只回傳訂單原本的 `total_price`／`discount_price` 與 `discount: null`，**沒有任何寫入**：不會刪除 `point_record` 的 `'減少_確認中'`、不會把 `user_coupon.status` 從 -1 還原、不會重設 `orders.discount_price`。取消在資料庫層面沒有作用。
     - 兩個 `used_point` 驗證在 `middlewares/checkout/index.js:160`（`使用者旅遊積分 < used_point`）與 `middlewares/discounts/index.js:89`（`< discount.point`）；因為沒有任何地方扣 `travel_point`，在解讀 A 下同一批點數可以無限次折抵。
     - `used_point` 的驗證器（`utils/Validator/checkout_Vaildator.js:78`）是 `Joi.number().min(0)`，**沒有 `.integer()`**，而 `point_record.point` 是 INT；`PATCH` 帶小數（例如 1.5）時 `0 - used_point` 寫入會失敗（`invalid input syntax for type integer`），API 回 500。

     **c. `point * 0.8` 是什麼意思？**（`controllers/discounts.js:66`、`controllers/checkout.js:165`）
     - 程式碼的運算：
       - `controllers/discounts.js:66`：`discount_price: orderRepo.rows[0].total_price - discount.point * 0.8`（回傳 response，不寫入）。
       - `controllers/checkout.js:165`：`UPDATE public."orders" SET discount_price = $1 ...`，參數 `orderRepo.rows[0].total_price - used_point * 0.8`（**寫入** `orders.discount_price`）。
       - 同一個請求在 `point_record` 記下的是 `0 - used_point`（`controllers/checkout.js:160`），也就是**扣的點數是 `used_point`，折掉的金額是 `used_point * 0.8`**。
       - 另一個比率：`controllers/checkout.js:225` 的 `total_price * 0.1`（累積比率，見上）。
       - seed 的觀察：訂單 `f4977608-...` 的 `減少 -436`（`db/seed/R__seed.sql:909`）對應該訂單的 `discount_price` 436.75（`:792`），約 1 點 ＝ 1 元；`新增 1610`（`:908`）對應該訂單的 `total_price` 1610.73，約 100%（與 `* 0.1` 不符）。
     - 解讀 A：**1 點折抵 0.8 元**（兌換率；等同於「用掉 N 點後折 N 的八折」，兩種說法的計算相同）。後果：`discount_price = total_price - used_point * 0.8` 是折扣後應付金額，與程式碼一致，不用改；seed 的 `-436` 與 `436.75` 的關係（約 1:1）不是這個比率；`used_point` 乘 0.8 會產生非整數的金額（例如 7 點 ＝ 5.6 元），`orders.discount_price` 是 FLOAT 可存。
     - 解讀 B：**1 點折抵 1 元，上限（或手續費）是 0.8**，例如「點數最多折抵訂單的 80%」。後果：程式碼沒有任何上限檢查（`min(total * 0.8, used_point)` 之類），實作與這個解讀不符；使用者用大量點數仍可使 `discount_price` 變成負數（`total_price - used_point * 0.8` 沒有下限）。
     - 解讀 C：**原意是 1 點 ＝ 1 元，0.8 是舊值或誤植**（依 seed 的 436:436.75）。後果：兩處 `0.8` 要改成 `1`（違反「controller 不改」）；不改的話使用者每點只折 0.8 元。
     - 另一個獨立的不一致：累積 `0.1`（`controllers/checkout.js:225`，每消費 1 元得 0.1 點）與兌換 `0.8`（每點折 0.8 元）並存，若 A 成立，使用者消費 100 元得 10 點，10 點可折 8 元，等於 8% 回饋；seed 的 `1610`／`1610.73` 約 100% 回饋與此矛盾。是否為設計值需要使用者確認。

  2. **結帳預覽後 `使用者旅遊積分` 要不要即時反映預扣？**（與待確認 1.a 的 B／C／D 重疊）解讀 A：不反映（餘額不變，直到付款確認）。後果：同一批點數在多張訂單同時預覽時可重複使用。解讀 B：反映。後果：使用者取消預覽後點數被占住，而取消沒有回補程式（見 1.b）。
  3. **view 是否只列出可用的優惠卷（`status = 0` 且未過期）？**（`controllers/userProfile.js:153` 把所有列都放進 `coupon[]`，沒有 `status` 欄位可供判斷）
     - 解讀 A：列出全部綁定（包含已使用 `status=1`、占用中 `-1`、已過期）。後果：`GET /pointslevel` 的 `coupon[]` 含已使用的優惠卷，前端無法區分（因為沒有 `status`／已使用的 key）；seed 使用者 `b2c3...`、`a1b2...` 的優惠卷都是 `status = 1`（`db/seed/R__seed.sql:917,919,920`），會全部顯示。
     - 解讀 B：只列出可用的（`status = 0` 且未過期）。後果：`coupon[]` 只含可用優惠卷，符合「使用者會員等級積分」頁面的語意；沒有可用優惠卷的使用者變成「沒有優惠卷」，需決定 JOIN 方式（見邊界）。
     - 解讀 C：排除 `status = 1` 但保留 `-1`（占用中）。後果：占用中的優惠卷仍顯示為可用。
  4. **沒有優惠卷的使用者是否保留一列（LEFT JOIN）**：見邊界。解讀 A：LEFT JOIN。後果：`coupon[]` 含一個全 `null` 物件。解讀 B：INNER JOIN。後果：使用者完全不在 view 內，點數折抵被擋下（409）。

### `user_orderList`

- **種類**：view（無參數）
- **使用位置**：
  - `controllers/checkout.js:211`（API：`GET /api/v1/user/checkout/summary/:order_id`）
    ```sql
    select * from public."user_orderList" where order_id = $1
    ```
    參數 `[order_id]`。這條 SQL 沒有 `user_id` 條件，擁有者檢查只在前面 `orders` 查詢（`controllers/checkout.js:206–209`）。
- **輸出欄位**（`controllers/checkout.js:245–264` 取 key）：

  | 欄位 | 型別 | 來源（表.欄位 或計算式） | 讀取位置 | 依據 |
  |---|---|---|---|---|
  | order_id（英文） | uuid | `order_item.order_id` | `controllers/checkout.js:211,246` | WHERE + response.orders[].order_id |
  | tour_id（英文） | uuid | `order_item.tour_id` | `controllers/checkout.js:247` | JS 讀取 → response.orders[].tour_id |
  | 大分類 | varchar | `tour_base.大分類` | `controllers/checkout.js:248` | JS 讀取 `item.大分類` → type |
  | 小分類 | varchar | `tour_base.小分類` | `controllers/checkout.js:249` | JS 讀取 `item.小分類` → item |
  | 旅遊名稱 | varchar | `tour_base.旅遊名稱` | `controllers/checkout.js:250` | JS 讀取 → title |
  | 旅遊代表圖 Url | text | `tour_base."旅遊代表圖 Url"` | `controllers/checkout.js:251` | JS 讀取 → cover_image |
  | 價錢 | integer | `tour_base.價錢`（或 `order_item` 換算，見待確認 1） | `controllers/checkout.js:252` | JS 讀取 → price |
  | 促銷價錢 | double precision | 見待確認 2 | `controllers/checkout.js:253` | JS 讀取 `item.促銷價錢` → response.orders[].**discount_price** |
  | quantity（英文） | integer | `order_item.quantity` | `controllers/checkout.js:255` | JS 讀取 → options.people |
  | start_date（英文） | timestamp | `order_item.start_date` | `controllers/checkout.js:256` | JS 讀取 → options.start_date |
  | end_date（英文） | timestamp | `order_item.end_date`（可 NULL） | `controllers/checkout.js:257` | JS 讀取 → options.end_date |
  | room_type（英文） | varchar | `order_item.room_type`（可 NULL） | `controllers/checkout.js:258` | JS 讀取 → options.room_type（這裡不像 `cart.js:222` 轉成 `''`，`NULL` 原樣輸出） |
  | singleTotal_Price（英文，混合大小寫） | numeric 或 double precision（推測） | 單一訂單項目小計（見待確認 3） | `controllers/checkout.js:260` | JS 讀取，**沒有 `Number()`** → total_price |
  | total_count（英文） | integer 或 bigint | 該訂單的項目數 | `controllers/checkout.js:263` | JS 讀取 `orderItemRepo.rows[0].total_count` → summary.total_items |

- **列的語意**：每個訂單項目（`order_item`）一列，帶入行程資料（`tour_base`）。`total_count` 是同一訂單所有列共有的項目總數（`rows[0]` 取第一列的值），推測以 `COUNT(*) OVER (PARTITION BY order_id)` 或子查詢計算。沒有排序。
- **邊界**：
  - **controller 行為 1（訂單沒有項目時 500）**：`controllers/checkout.js:263` 讀 `orderItemRepo.rows[0].total_count`，沒有檢查 `rows.length`，`order_item` 沒有任何列時（`rows[0]` 為 `undefined`）丟 TypeError，API 回 500。
  - **controller 行為 2（非擁有者的訂單 500）**：`middlewares/checkout/index.js:190–199` 只確認訂單存在（`SELECT * FROM public."orders" WHERE order_id = $1`，不比對 `user_id`）；`controllers/checkout.js:206–209` 的 `orders` 查詢加了 `user_id`，非擁有者時 `orderRepo.rows[0]` 為 `undefined`，`controllers/checkout.js:225` 的 `orderRepo.rows[0].total_price` 丟 TypeError，API 回 500（而不是 403／404）。與本 view 無關，但本 view 不帶 `user_id`，所以無法在 view 內補這個檢查。
  - **controller 行為 3（只產生一個訂單項目）**：`controllers/checkout.js:20–33,42–56` 取 `cartItemRepo.rows[0]` 建立 `order_item`，購物車有多個項目時只有第一個進入 `order_item`，但 `orders.total_price` 用整個購物車的 `cart.total_price`（`controllers/checkout.js:38`）。因此一張訂單在本 view 只會有 1 列，`total_count` 恆為 1，與 `orders.total_price` 的加總不符。
  - **controller 行為 4（與本 view 相關的 `order_item` 寫入）**：`controllers/newebpay.js:82,213` 更新 `order_item` 時寫 `SET payment = 0／1`（同檔 `:71,206` 對 `orders` 寫的是 `payment_status`），但 V1 `order_item`（V1 `:288–303`）沒有 `payment` 欄位，只有 `payment_status`，這兩段 SQL 在 PostgreSQL 會失敗（`column "payment" does not exist`）。此問題不屬於 B 組 8 個物件，只在此記錄，因為它會讓訂單項目的付款狀態不被更新。
  - **seed 對照（UUID 版本）**：seed 的 `orders` 主鍵都是 v4，`GET /checkout/summary/:order_id` 可通過 `checkout_Vaildator.js:12`；但新訂單只能由 `POST /checkout/order/:cart_id` 產生，前提是購物車有 `cart_item`，而 seed 行程無法經 `POST /cart` 加入（見共通觀察）。
  - `價錢`、`促銷價錢` 在 `controllers/checkout.js:252–253` 被直接輸出，`discount_price: item.促銷價錢` 這個映射是 controller 的命名（response 的 `discount_price` 來自 view 的 `促銷價錢`，不是 `order_item.discount_price`）。
  - 欄位名稱必須照拼字：`item.大分類`（`.` 取法，所以不含空格）、`item['旅遊代表圖 Url']`、`singleTotal_Price`、`total_count`。
  - 對 `tour_base` 的 JOIN：同 `user_cartList` 邊界第 1 點（§1 `tour_base` 待確認 1 的下架行程問題）。
- **信心**：欄位名稱：確定；來源對應：欄位名稱本身確定，`價錢`／`促銷價錢`／`singleTotal_Price` 的計算：推測；`total_count` 的計算與型別：推測。
- **待確認**：
  1. **`價錢` 是目前的行程單價，還是下單當時的單價？**
     - 解讀 A：`tour_base.價錢`（目前的價格）。後果：行程後來調價，歷史訂單的 `price` 跟著變；`singleTotal_Price` 若用 `order_item.total_price` 則兩者可能不一致。
     - 解讀 B：`order_item.total_price / order_item.quantity`（下單時的單價，`controllers/checkout.js:49` 寫入的是 `tour_base.價錢 * quantity`）。後果：歷史訂單固定；`quantity = 0` 時除以零（V1 沒有 `CHECK`，但 `cart_Validator` 要求 `people >= 1`）。
  2. **`促銷價錢` 是什麼？**（controller 把它輸出為 `discount_price`）
     - 解讀 A：`tour_base.促銷價錢`（目前行程的促銷價）。後果：促銷結束後，歷史訂單的 `discount_price` 變成 `NULL` 或舊促銷價，與下單時不同。
     - 解讀 B：`order_item.discount_price / quantity`（下單時的促銷單價；`controllers/checkout.js:50` 寫入的是 `促銷價 * quantity`，非促銷時是 `0 * quantity ＝ 0`）。後果：非促銷時會是 `0` 而不是 `NULL`，前端若用「有值＝促銷」判斷會把非促銷當成促銷。
     - 解讀 C：`order_item.discount_price`（小計，不除以數量）。後果：欄位名稱是「價錢」卻是小計，與 `價錢` 單價不對稱。
  3. **`singleTotal_Price` 是什麼？**
     - 解讀 A：`order_item.total_price`（`controllers/checkout.js:49` 寫入的 `tour_base.價錢 * quantity`，即不含促銷）。後果：`GET /summary` 的 `orders[].total_price` 是原價小計，與 `orders.discount_price`（`discount_price` 是整張訂單折扣後應付金額）不相加。
     - 解讀 B：有效單價 × `quantity`（促銷期間用促銷價）。後果：與 `user_cartList` 待確認 1 解讀 A 一致。
     - 解讀 C：`order_item.discount_price`（非促銷是 0）。後果：非促銷項目小計為 0。
     - 型別：`controllers/checkout.js:260` 沒有 `Number()`（`controllers/cart.js:224` 有）。若是 `numeric`／`bigint`，response 是 JSON 字串；`double precision` 是數字。
  4. **`total_count` 的型別**：解讀 A：`integer`（view 內 `::int`）。後果：`summary.total_items` 是數字。解讀 B：`bigint`（`COUNT(*)` 預設）。後果：`summary.total_items` 是字串（例如 `"1"`）。
  5. **是否依 `payment_status` 篩選？** 程式碼只用 `order_id` 取全部項目。解讀 A：不篩選（所有 `payment_status` 都出現）。解讀 B：只含部分狀態。後果：預覽階段（-1／0）看不到項目，`GET /summary` 的 `rows[0].total_count` 取不到而 500。

## 3. C 組：會員與後台

## 4. 待使用者確認
