# TripEasy DB 契約（`backend/migrations/R__views_functions.sql`）

> 狀態：定案（2026-10-22 使用者確認）；2026-10-23 final review 補充（§0.1、#11、(a) 範圍） · 依據 spec 3.1 · 從 backend 程式碼反推（四份既有 SQL 都沒有這些物件）

## 0. 說明

- 範圍：程式碼查詢了、但 migration 沒有建立的 21 個物件（12 個 view、9 個 function）。
- 反推方法：見 `docs/superpowers/plans/2026-10-20-p1a-routes-seed-contract.md` 的「反推方法」。
- 原則：view／function 照程式碼期待的中文欄位名建立，**controller 不改**。
- 檔案位置（2026-10-23 P1b 計畫改用 repeatable migration）：21 個物件放在 `backend/migrations/R__views_functions.sql`，不再是 spec 3.1 原寫的 versioned V3 migration。理由：versioned migration 套用後內容不能再改（Flyway validate 會失敗），開發中每次修 SQL 都要 `down -v`；P2 起的重構規則又要求動到 view 時同步更新。repeatable migration 內容一改，下次 `migrate` 就重新套用；檔案開頭先 `DROP ... IF EXISTS ... CASCADE` 全部 21 個物件，再依相依順序 `CREATE`（P1b 計畫 Global Constraints 第 1 條）。文中其餘「V3」指這一批 view／function，不是檔名。
- 行號以 backend `phase-1` 分支、P1a Task 1 完成後的版本為準。

### 識別字對照（`CREATE` 時的寫法）

> 2026-10-23 final review 補充。程式碼的引用方式見各物件的「使用位置」；`public."name"` ＝ 有引號，`public.name` ＝ 無引號（PostgreSQL 折成小寫）。

| # | 物件（本契約的標題） | 種類 | `CREATE` 時的識別字 |
|---|---|---|---|
| 1 | `tour_base` | view | `tour_base`（小寫，不需引號） |
| 2 | `tour_travel` | function | `tour_travel`（小寫） |
| 3 | `tour_travel_popular` | function | `tour_travel_popular`（小寫） |
| 4 | `tour_travel_most_favorited` | function | `tour_travel_most_favorited`（小寫） |
| 5 | `tour_tour_detail` | function | `tour_tour_detail`（小寫） |
| 6 | `tour_hotel` | function | `tour_hotel`（小寫） |
| 7 | `tour_restaurant` | function | `tour_restaurant`（小寫） |
| 8 | `user_user_level` | view | `"user_user_level"`（程式碼加引號，名稱本身全小寫，引號可省） |
| 9 | `user_level_review_forHome` | view | `"user_level_review_forHome"`（**必須加雙引號**，混合大小寫） |
| 10 | `user_cartList` | view | `"user_cartList"`（**必須加雙引號**，混合大小寫） |
| 11 | `hotel_booking` | function | `hotel_booking`（小寫） |
| 12 | `restaurant_booking` | function | `restaurant_booking`（小寫） |
| 13 | `restaurant_isClosed` | function | `restaurant_isclosed`（**不加引號**；程式碼未加引號，PostgreSQL 折成小寫；若用 `"restaurant_isClosed"` 建立，呼叫會失敗） |
| 14 | `restaurant_business_parsed` | view | `restaurant_business_parsed`（小寫） |
| 15 | `user_couponList` | view | `"user_couponList"`（**必須加雙引號**，混合大小寫） |
| 16 | `user_level_point_coupon` | view | `"user_level_point_coupon"`（程式碼加引號，名稱本身全小寫，引號可省） |
| 17 | `user_orderList` | view | `"user_orderList"`（**必須加雙引號**，混合大小寫） |
| 18 | `user_favorite` | view | `"user_favorite"`（程式碼加引號，名稱本身全小寫，引號可省） |
| 19 | `user_orders` | view | `"user_orders"`（程式碼加引號，名稱本身全小寫，引號可省） |
| 20 | `user_order_item` | view | `"user_order_item"`（程式碼加引號，名稱本身全小寫，引號可省） |
| 21 | `user_adminList` | view | `"user_adminList"`（**必須加雙引號**，混合大小寫） |

共 12 個 view、9 個 function，與各物件的「種類」一致。

### 0.1 P1b 開工前待補

> 2026-10-23 final review 補充。下列事項不需要使用者再決定（決定已在 §4），但 P1b 要在寫 view／function 的 SQL 之前或同時釘住，否則 SQL 作者會停住或各自選擇，之後又要依 spec 重構規則一起改 view、契約與契約測試。

1. **seed 目標值要先寫成具體值**（再寫 seed 測試）。具體值已寫在本節最後的小節（標題見該節），以下四點是來源與依據：
   - #9 促銷通知日期（§4.1 #9；來源檔 `notification` 的兩筆 `促銷`）。
   - #43 收藏時間（§4.1 #43；來源檔 `favorite` 的 7 筆，同一個 `CURRENT_TIMESTAMP`）。
   - #4–#6 `payment` 資料與各 `payment_status`（§4.1 #4、#5、#6；現值 來源檔 `orders` 5 筆、`order_item` 10 筆）。
   - #3 點數：使用者 2026-10-23 決定 seed 點數資料調成與「1 點折 0.8 元」「10% 回饋」相符（來源檔 `point_record` 2 筆與相關訂單）。
2. **(a)、(d2)、(d3) 的 seed 重寫**，含 `country` 主鍵與 `region.country_id` 外鍵（§4.2 (a) 2026-10-23 擴大範圍）。
3. **`cart_item.start_date` 早於載入日的資料要移到未來**：來源檔 `cart_item` 的 10 筆中有 6 筆（原值 `2025-05-13` 至 `2025-05-19`，早於基準日 `2025-05-20`）位移後落在載入日之前。
4. **重寫後要把本契約的 seed 引用改成穩定的錨點，不引用 `db/seed/R__seed.sql` 的行號或寫死的 seed id**（2026-10-28 Task 3 已完成）：優惠卷用 `code`、使用者用 `email`、行程用 `title`，其他資料寫「`<錨點>` 的訂單／購物車」。可重用 `.superpowers/sdd/2026-10-20-p1a-routes-seed-contract/task-7-selfcheck.py` 的作法檢查，或改用穩定的錨點（coupon `code`、user `email`、tour `title`）。
5. **既有 volume 的處理（使用者 2026-10-23 決定：不加 migrate guard）**。`R__seed.sql` 靠主鍵 `ON CONFLICT DO NOTHING`；V1 的 `"user".email`、`coupon.code`、`tour` 都沒有 unique。主鍵一改，保留舊 volume 重跑 Flyway 時舊列與新列並存（例如兩筆 `alice@example.com`），migrate 仍會成功，`test_seed_is_rerunnable` 只重跑同一份檔案所以抓不到。因此：
   - 主鍵改寫後，**由使用者自己執行** `docker compose down -v`（agent 不代跑）。
   - 加 seed 測試：關鍵表的筆數用 exact count（各表筆數見下方 seed 目標值小節的第 1 項）、seed email 無重複，讓重複的 volume 直接失敗。
   - 新 id 要**從自然鍵決定性產生**（例如 `tour:<title>`、`user:<email>`、`coupon:<code>`、`country:<name>`，每張表各自的鍵），**不用**現行 `fix_generated_ids` 的位置序號 `seed-row-{i}`（`db/seed-build/build_seed.py:73–82`），日後增刪 seed 列 id 才不會跟著移動。
   - **新舊 id 對照依欄位所屬的表建立，不可對字面值整份取代**。來源檔的手寫主鍵在不同表重複使用同一個字面值：來源檔 `db/seed-build/tripeasy_fakedata.sql` 的手寫主鍵 `11111111-aaaa-…`（Task 3 之前也在 `R__seed.sql`）是至少 6 張表的主鍵（另有 `restaurant_menu`、`hotel`、`notification` 等），其中在 (a) 改寫範圍內的是 `coupon.coupon_id`、`tour.tour_id`、`country.country_id`，三者要換成各自表的新 id；對字面值整份取代會讓三張表拿到同一個新值，或把 `cart_item.tour_id`、`order_item.tour_id` 等外鍵指到錯的表（理由同 P1b 計畫 Global Constraints 第 5 條：外鍵依欄位名稱對應被參照的表）。
   - 新 id 必須是 **v4 形狀**（版本位 `4`、variant 位 `8`／`9`／`a`／`b`）；現行 `fix_generated_ids` 用 `uuid.uuid5` 產生的是 v5，會被 v4 專用驗證器擋下（`admin_Validator.js` 接受 v5，其餘不接受，見 §4.2 (a)）。
6. **seed 測試**：每個被 v4 專用驗證器擋住的主鍵都要是 v4——至少涵蓋 `tour`、`coupon`、`user`、`country`，以及 `cart`、`cart_item`、`orders`、`order_item`。

#### seed 目標值（定案）

> 2026-10-23 P1b Task 1 補。Task 2、3 與 seed 測試只引用本節，不自己決定數值。本節的每個數字都標出依據：§4 題號、程式碼行號，或「來源檔」（`db/seed-build/tripeasy_fakedata.sql`，行號為該檔行號）。
>
> - **載入日**＝seed 載入那天的 `CURRENT_DATE`（`build_seed.py` 的 `DATE_ANCHOR` 平移）。「+N 天」＝載入日加 N 天，「−N 天」＝載入日減 N 天；日期欄位取當日 `00:00:00`，期間的結束日取當日 `23:59:59`（與來源檔的寫法相同）。「載入時間」＝載入當下的 `CURRENT_TIMESTAMP`。seed 測試以 Flyway 記錄的 `min(installed_on)` 當載入時間／載入日，所以 migrate 跨過午夜、或 Flyway 與測試連線的時區不同時，日期類的斷言可能差一天（P1a 起的已知限制）。
> - 資料列以自然鍵稱呼：使用者用 `email`（`alice@example.com`、`bob@example.com`、`carol@example.com`）、優惠卷用 `code`、行程用 `title`；訂單與訂單項目用（使用者 `email`，行程 `title`）——下面 20 筆訂單中這組值不重複。
> - **各表處理方式（P1b 計畫 2026-10-25 controller 裁決：來源金額非 10 的倍數、一張訂單多個項目，無法只改狀態滿足 #3、#4–#6；#3 定案已含「與相關訂單」）**：
>   - **刪除來源檔的列後重建**：`orders`（5 筆）、`order_item`（10 筆）、`point_record`（2 筆）。
>   - **純新增**：`payment`（來源檔沒有資料列）。
>   - **保留來源檔的列、逐列修改，再加新增列**：`favorite`（7 筆保留、改 `created_at`，加 2 筆）、`notification`（促銷日期；加新行程的通知）、`cart_item`（`start_date`；移除被移除購物車底下的項目）、`review`（加 3 則 `web`，並設 5 則 `web` 的 `created_at`）、`user_coupon`（4 列保留，只改指向的訂單）、`coupon`（代碼與一則 `description`）、`tour`（加 13 個行程）。
>   - 新增列的主鍵自然鍵形狀，由 Task 3 實作，形狀同 Global Constraints 第 5 條：`orders`、`order_item`、`favorite`、`payment` 用 `{table}:{email}:{title}`；`point_record` 用 `point_record:{email}:{title}:{type}`（同一張訂單可有 `新增` 與 `減少` 兩筆，一定要含 `type`）；`notification` 沒有使用者欄位，用 `notification:{title}:{type}`（`{type}` 為 `促銷`／`異動`，每個行程至多 1 列通知，所以不重複）。
> - 本節沒有寫到的欄位（行程的國家、地區、圖片、內文，訂單項目的出發日期，新增行程的子表等）由 Task 3 決定，不影響下面任何斷言。

**1. 筆數（Task 3 的 `SEED_COUNTS` 依此）**

| 表 | 筆數 | 說明 |
|---|---|---|
| `"user"`／`user_level` | 3／3 | 不變（來源檔 `:30–:82`、`:116–:152`）；`user_level.travel_point` 不變：alice 1500、bob 3000、carol 800（見第 10 項） |
| `coupon` | 5 | 不變（第 2 項只改代碼與一則 `description`） |
| `tour` | 23 | `status = 1` 共 22、`status = 2` 共 1（第 3 項） |
| `notification` | 9 | `促銷` 7、`異動` 2（第 6 項） |
| `cart`／`cart_item` | 3／6 | 第 7 項 |
| `orders`／`order_item` | 20／20 | 每張訂單恰好 1 個項目（與 `checkout.js:20–33,42–56` 只取購物車第一個項目一致，見 §2 `user_orderList` 邊界）；第 9 項 |
| `payment` | 15 | 每張 `payment_status = 1` 的訂單 1 筆（第 9 項） |
| `point_record` | 18 | `新增` 15、`減少` 3（第 10 項） |
| `favorite` | 9 | 第 8 項 |
| `auto_setting` | 3 | 一位使用者一列（P5 V6 `auto_setting_user_id_key`）：來源檔 alice 有兩列，`build_seed.py::merge_duplicate_auto_settings` 併成一列（每欄取 `updated_at` 較新者，相同時取 `auto_setting_id` 較小者；結果是來源 `1111aaaa-…` 那列的值：early 0、flexible 1、Japan、Tokyo、1200.5） |
| `review` | 13 | 來源檔 10 則加 3 則 `web`；`type = 'web'` 共 5 則（第 11 項） |
| `user_coupon` | 4 | 第 9 項最後一段 |

**2. 優惠卷（(d2)、#1 定案 B）**

| 舊 `code`（來源檔） | 新 `code` | `discount` | `description` |
|---|---|---|---|
| `WELCOME100` | `WEL100` | `100.0` | 不變：`首次註冊禮，折抵新台幣 100 元` |
| `SUMMER50` | `SUM050` | `50.0` | 不變：`夏日旅遊季，折抵新台幣 50 元` |
| `TRAVEL10P` | `TRV010` | `10.0` | **改成 `旅遊商品折抵新台幣 10 元`**（原 `旅遊商品 10% 折扣 (最高折抵 500 元)`，與 #1 定案 B 的折抵金額矛盾；新文字沿用其他代碼「折抵新台幣 N 元」的句型，`10` 與 `discount` 一致） |
| `VIP300` | `VIP300` | `300.0` | 不變：`尊榮會員專屬，折抵新台幣 300 元` |
| `SPRING20` | `SPR020` | `20.0` | 不變：`春季限定，旅遊折抵新台幣 20 元` |

`expire_date` 維持來源檔的平移結果：`SPR020` +11 天、`SUM050` +103 天、`TRV010` +133 天、`WEL100` 與 `VIP300` +225 天（來源檔 `:154–:203` 的 `2025-05-31`、`2025-08-31`、`2025-09-30`、`2025-12-31` 減 `2025-05-20`），載入日當天五張都未過期。

**3. 行程名單（23 個）與首頁區塊**

來源檔 10 個行程全部保留（`status` 不變），另新增 13 個（`status = 1`）。新增行程的 `type`、`item` 與 `title` 如下，其餘欄位（`price` 為正整數、`country`／`region`、圖片、內文等）由 Task 3 決定，唯一例外是 `沖繩海景度假旅店` 的 `price` 固定為 `8800`（第 9 項的訂單用到）。

| 大分類 `type` | 小分類 `item` | `status = 1` 的行程（共 22 個） | `status = 2` |
|---|---|---|---|
| `tourgroup` | `travel`（7） | 北海道雪景 5 日深度遊、馬爾地夫蜜月天堂 6 日、義大利深度文化之旅、紐西蘭壯麗景觀自駕遊；**新增** 冰島極光 8 日探索、瑞士鐵道山岳 7 日、西班牙陽光巡禮 9 日 | — |
| `backpacker` | `food`（5） | 大阪美食自由行、高雄夜市美食攻略；**新增** 台南小吃巡禮、東京拉麵地圖、曼谷街頭美食 | — |
| `backpacker` | `spot`（5） | 巴黎歷史建築巡禮、首爾咖啡文青小旅行；**新增** 京都古寺散步、倫敦博物館漫遊、新加坡花園城市導覽 | — |
| `backpacker` | `hotel`（5） | 曼谷設計旅店探索；**新增** 沖繩海景度假旅店、峇里島別墅旅宿、河內古城精品旅店、釜山海岸旅店 | 清邁自然旅宿體驗（來源檔 `:350` 起，`status = 2`，保留） |

`home.js` 實際用到的每組 (大分類, 小分類) 與條件（`home_Validator.js:47` 的預設 `limit` 是 4，但首頁 middleware 的預設值不會寫回 `req.query`〔`middlewares/home/index.js:7`，見 §4.2 末段〕，所以測試要明確帶 `limit=4`；2 頁需要至少 5 列）：

| 區塊（API 參數） | 未登入／已登入的行號 | (大分類, 小分類) | 額外條件 | 目標列數 |
|---|---|---|---|---|
| `type=tourgroup&item=popular` | `home.js:19`／`:28` | `('tourgroup','travel')` | `tour_travel_popular`（#4、#7：只回 `status = 1`） | 7（2 頁：4＋3） |
| `type=tourgroup&item=promotion` | `home.js:36`／`:44`（SQL 在 `:33–:35`、`:41–:43`） | `('tourgroup','travel')` | `通知狀態 = '促銷'`（`:34`、`:42`）；**本計畫另要求**促銷期間內（#9 定案 A：view 不判斷期間，所以靠 seed 的日期達成）、`status = 1`（#7：`tour_base` 含下架行程，此區塊直接查 `tour_base`，不過濾） | 5（2 頁：4＋1；第 6 項的 5 個期間內促銷） |
| `type=tourgroup&item=most_favorited` | `home.js:53`／`:62` | `('tourgroup','travel')` | `tour_travel_most_favorited`（#7） | 7（2 頁：4＋3） |
| `type=backpacker&item=hotel` | `home.js:72`／`:81`（`item` 取自 query，`home_Validator.js:8`） | `('backpacker','hotel')` | `tour_travel_popular`（#4、#7） | 5（2 頁：4＋1） |
| `type=backpacker&item=food` | 同上 | `('backpacker','food')` | 同上 | 5（2 頁） |
| `type=backpacker&item=spot` | 同上 | `('backpacker','spot')` | 同上 | 5（2 頁） |

**4. 搜尋清單**：`status = 1` 的行程 22 個（`limit` 預設 10，`product_Validator.js:75`，所以 10＋10＋2 共 3 頁，第 2 頁有資料）；`status = 2` 的行程 1 個（清邁自然旅宿體驗）。

**5. 熱門與收藏排行（#4、#7、#23、#24）**

「購買數」＝該行程 `order_item.payment_status = 1` 的**列數**（#4 定案 B 只定「只算 `payment_status = 1`」；計數方式依 §1 `tour_travel_popular` 的 controller 裁決 2026-10-25：一個項目算 1，不乘 `quantity`；本節資料兩種算法名次相同）；「收藏數」＝該行程的 `favorite` 列數。名次欄只列出購買數或收藏數**唯一**的名次；其餘行程的數值都是 0，並列者以 `tour_id` 升冪決定先後（#24），測試不 assert 其順序。購買數與收藏數都以第 8、9 項的資料為準。

| 區塊 | 行程 | 購買數 | 購買排行 | 收藏數 | 收藏排行 |
|---|---|---|---|---|---|
| `tourgroup/travel` | 北海道雪景 5 日深度遊 | 3 | 1 | 2 | 2 |
| | 馬爾地夫蜜月天堂 6 日 | 2 | 2 | 3 | 1 |
| | 紐西蘭壯麗景觀自駕遊 | 1 | 3 | 1 | 3 |
| | 義大利深度文化之旅、冰島極光 8 日探索、瑞士鐵道山岳 7 日、西班牙陽光巡禮 9 日 | 0 | 4–7（並列） | 0 | 4–7（並列） |
| `backpacker/food` | 高雄夜市美食攻略 | 2 | 1 | 0 | 不使用 |
| | 大阪美食自由行 | 1 | 2 | 1 | 不使用 |
| | 台南小吃巡禮、東京拉麵地圖、曼谷街頭美食 | 0 | 3–5（並列） | 0 | 不使用 |
| `backpacker/spot` | 首爾咖啡文青小旅行 | 2 | 1 | 0 | 不使用 |
| | 巴黎歷史建築巡禮 | 1 | 2 | 1 | 不使用 |
| | 京都古寺散步、倫敦博物館漫遊、新加坡花園城市導覽 | 0 | 3–5（並列） | 0 | 不使用 |
| `backpacker/hotel` | 曼谷設計旅店探索 | 2 | 1 | 1 | 不使用 |
| | 沖繩海景度假旅店 | 1 | 2 | 0 | 不使用 |
| | 峇里島別墅旅宿、河內古城精品旅店、釜山海岸旅店 | 0 | 3–5（並列） | 0 | 不使用 |
| `status = 2` | 清邁自然旅宿體驗 | 0 | 不出現（#7） | 0 | 不出現 |

「收藏排行」只用於 `tourgroup/travel`（`home.js:53,62`，見 §1 `tour_travel_most_favorited`）。每個排行區塊都有 3 個以上購買數不同的行程（`tourgroup/travel`：3、2、1、0；其餘三組：2、1、0）；`tourgroup/travel` 的收藏數 3、2、1、0 各不相同，且與購買排行的順序不同（馬爾地夫在收藏排行第 1、在購買排行第 2）。

**6. 促銷（#8、#9、#10）**

`notification` 共 9 列：下表 7 筆 `促銷`，加上來源檔 `:617–:638` 的 2 筆 `異動`（義大利深度文化之旅、紐西蘭壯麗景觀自駕遊，日期、折扣、價格皆 `NULL`，保留不動；它們不是促銷，所以不影響 `tourgroup/promotion` 區塊）。每個行程至多 1 列通知。

| 行程 | 組別 | 開始 | 結束 | 期間狀態 | `discount`／`promo_price` |
|---|---|---|---|---|---|
| 北海道雪景 5 日深度遊 | `tourgroup/travel` | −10 天 | +20 天 | 期間內 | 來源檔 `10.0`／`40500.0`，不變（來源檔日期 `2025-11-01`～`2025-11-30`＝+165～+194 天，載入日不在期間內，所以要改） |
| 馬爾地夫蜜月天堂 6 日 | `tourgroup/travel` | −5 天 | +25 天 | 期間內 | 來源檔 `15.0`／`83300.0`，不變（來源檔日期 `2025-10-01`～`2025-10-31`＝+134～+164 天，同上） |
| 冰島極光 8 日探索（新增） | `tourgroup/travel` | −7 天 | +14 天 | 期間內 | Task 3 決定 |
| 瑞士鐵道山岳 7 日（新增） | `tourgroup/travel` | −3 天 | +30 天 | 期間內 | Task 3 決定 |
| 西班牙陽光巡禮 9 日（新增） | `tourgroup/travel` | −1 天 | +7 天 | 期間內 | Task 3 決定 |
| 台南小吃巡禮（新增） | `backpacker/food` | +10 天 | +40 天 | **未開始** | Task 3 決定 |
| 京都古寺散步（新增） | `backpacker/spot` | −40 天 | −10 天 | **已結束** | Task 3 決定 |

- 新增促銷的 `discount` 與 `promo_price` 必須維持來源檔的關係 `promo_price = 該行程 price × (1 − discount / 100)`（`45000 × 0.9 = 40500`、`98000 × 0.85 = 83300`）。
- 依據：#9 定案 A（view 不判斷期間，`通知狀態` 期間外仍是 `促銷`，所以未開始與已結束的促銷仍出現在管理者促銷清單 `promotion.js:8,42`）；#10 定案 B（`促銷價錢` 只在期間內有值，所以期間內 5 筆的 `促銷價錢` 非 `NULL`，另 2 筆為 `NULL`）。5 個期間內促銷全在 `tourgroup/travel`，達成第 3 項促銷區塊的 5 列；未開始與已結束各一筆放在 `backpacker`，不進首頁促銷區塊。
- `tourgroup/travel` 的 7 個行程 `tour_start_date` 兩兩不同（首頁促銷區塊 `ORDER BY 旅遊開始日期 DESC`，`home.js:35,43`）：北海道 +195 天、馬爾地夫 +174 天、紐西蘭 +169 天、義大利 +148 天（來源檔 `2025-12-01`、`2025-11-10`、`2025-11-05`、`2025-10-15` 平移，不變），新增的冰島 +220 天、瑞士 +100 天、西班牙 +60 天；`tour_end_date` ＝ 開始日加（`days` − 1）天，`days` 分別為 8、7、9。`backpacker` 行程的 `tour_start_date`／`tour_end_date` 為 `NULL`、`days` 為 `0`（與來源檔相同）。

**7. 購物車（(d3)）與 `cart_item.start_date`**

每位使用者保留 1 個 `cart`。規則：保留有 `cart_item` 的；兩個都有時保留 `cart_item` 較多的；筆數相同時保留 `total_price` 較大的。被移除的 `cart` 底下的 `cart_item` 一起移除（`cart_item` 由 10 筆變 6 筆）。保留的 `cart` 的 `total_price` 不變（與項目金額不一致是來源檔既有的，本節不處理）。

| 使用者 | 保留的 `cart` | 移除的 `cart`（連同其 `cart_item`） |
|---|---|---|
| alice | 有 1 項的那個 | 0 項的那個 |
| bob | 有 3 項的那個 | 有 2 項的那個（清邁自然旅宿體驗、曼谷設計旅店探索） |
| carol | 有 2 項、`total_price` 較大的那個 | 有 2 項的另一個（北海道雪景 5 日深度遊、首爾咖啡文青小旅行） |

保留的 6 個 `cart_item` 的 `start_date`（來源檔 `:781–:790`；表中「來源檔日期」為 `2025-05-20` 基準的字面值，載入日 ＝ 0 天），全部晚於載入日；`end_date` 與 `start_date` 的間隔維持來源檔的天數：

| 使用者 | 行程 | 錨點 | 來源檔 `start_date`（相對天數） | **目標 `start_date`** | **目標 `end_date`** |
|---|---|---|---|---|---|
| alice | 大阪美食自由行 | （同使用者、行程） | `2025-05-16`（−4） | **+30 天** | `NULL` |
| bob | 高雄夜市美食攻略 | （同使用者、行程） | `2025-05-18`（−2） | **+14 天** | `NULL` |
| bob | 義大利深度文化之旅 | （同使用者、行程） | `2025-10-15`（+148） | +148 天（不變） | +155 天 |
| bob | 紐西蘭壯麗景觀自駕遊 | （同使用者、行程） | `2025-11-05`（+169） | +169 天（不變） | +179 天 |
| carol | 馬爾地夫蜜月天堂 6 日 | （同使用者、行程） | `2025-11-10`（+174） | +174 天（不變） | +179 天 |
| carol | 巴黎歷史建築巡禮 | （同使用者、行程） | `2025-05-15`（−5） | **+20 天** | **+21 天** |

最小值為 +14 天，載入日當天與之後都在未來。移除的 4 個項目中，清邁（`status = 2`）也一併離開購物車。

**8. 收藏（#43）**

9 筆 `favorite`：來源檔 `:895–:901` 的 7 筆保留，加 2 筆（bob 收藏馬爾地夫、alice 收藏北海道，用來讓 `tourgroup/travel` 的收藏數成為 3、2、1）。`created_at` 為「載入時間減 N 天」，同一使用者兩兩不同（實際上 9 筆全部不同）；`updated_at` 取與 `created_at` 相同的值。

| 使用者 | 行程 | `created_at` 偏移 | 來源 |
|---|---|---|---|
| alice | 紐西蘭壯麗景觀自駕遊 | −10 天 | 來源檔 |
| alice | 馬爾地夫蜜月天堂 6 日 | −7 天 | 來源檔 |
| alice | 大阪美食自由行 | −3 天 | 來源檔 |
| alice | 北海道雪景 5 日深度遊 | −1 天 | 新增 |
| bob | 北海道雪景 5 日深度遊 | −9 天 | 來源檔 |
| bob | 巴黎歷史建築巡禮 | −5 天 | 來源檔 |
| bob | 馬爾地夫蜜月天堂 6 日 | −2 天 | 新增 |
| carol | 馬爾地夫蜜月天堂 6 日 | −8 天 | 來源檔 |
| carol | 曼谷設計旅店探索 | −4 天 | 來源檔 |

`GET /collection/info/all` 對 alice 依 `建立時間 DESC` 的順序是：北海道、大阪、馬爾地夫、紐西蘭。

**9. 訂單、`payment_status` 與 `payment`（#4、#5、#6、#13）**

`order_item.payment_status` 與其所屬 `orders.payment_status` 相同（消除來源檔「訂單與項目付款狀態不一致」，#6 定案 B 以項目層級篩選）。`order_item.total_price` ＝ `orders.total_price` ＝ 行程 `price × quantity`；`order_item.discount_price` 對期間內促銷的行程（北海道、馬爾地夫）＝ `promo_price × quantity`，其餘 `NULL`（#13：`價錢` ＝ `total_price / quantity`，`促銷價錢` ＝ `NULLIF(discount_price, 0) / quantity`）。

各付款狀態的筆數：`1` 15 筆、`-1`／`0`／`2`／`3`／`4` 各 1 筆（共 20）。`orders` 的 `address`／`phone`（`payment_status = -1` 的訂單為 `NULL`，因為 `checkout.js:36–39` 建立時沒有寫）依使用者固定：alice `台北市中山區南京東路3段123號`／`0987654321`（來源檔 `:798`）、bob `高雄市鼓山區美術館路45號`／`0912345678`（`:794`）、carol `台中市西區公益路321巷9號`／`0987654321`（`:795`）。

| # | 使用者 | 行程 | `payment_status` | `quantity` | `total_price` | `order_item.discount_price` | `payment_type` | `discount_type` | `orders.discount_price` |
|---|---|---|---|---|---|---|---|---|---|
| 1 | alice | 北海道雪景 5 日深度遊 | 1 | 1 | 45000 | 40500 | `credit_card` | `none` | `NULL` |
| 2 | bob | 北海道雪景 5 日深度遊 | 1 | 1 | 45000 | 40500 | `credit_card` | `coupon` | 40490（`TRV010`，促銷後 40500 − 10） |
| 3 | carol | 北海道雪景 5 日深度遊 | 1 | 1 | 45000 | 40500 | `credit_card` | `none` | `NULL` |
| 4 | alice | 馬爾地夫蜜月天堂 6 日 | 1 | 1 | 98000 | 83300 | `credit_card` | `coupon` | 83000（`VIP300`，促銷後 83300 − 300） |
| 5 | carol | 馬爾地夫蜜月天堂 6 日 | 1 | 1 | 98000 | 83300 | `atm` | `none` | `NULL` |
| 6 | bob | 紐西蘭壯麗景觀自駕遊 | 1 | 1 | 85000 | `NULL` | `credit_card` | `coupon` | 84700（`VIP300`，85000 − 300） |
| 7 | alice | 高雄夜市美食攻略 | 1 | 2 | 8400 | `NULL` | `credit_card` | `point` | 8200（用 250 點） |
| 8 | bob | 高雄夜市美食攻略 | 1 | 3 | 12600 | `NULL` | `cvs` | `none` | `NULL` |
| 9 | carol | 大阪美食自由行 | 1 | 2 | 30000 | `NULL` | `credit_card` | `point` | 29680（用 400 點） |
| 10 | alice | 首爾咖啡文青小旅行 | 1 | 2 | 19000 | `NULL` | `credit_card` | `none` | `NULL` |
| 11 | carol | 首爾咖啡文青小旅行 | 1 | 1 | 9500 | `NULL` | `credit_card` | `none` | `NULL` |
| 12 | bob | 巴黎歷史建築巡禮 | 1 | 1 | 22000 | `NULL` | `credit_card` | `none` | `NULL` |
| 13 | bob | 曼谷設計旅店探索 | 1 | 2 | 18000 | `NULL` | `credit_card` | `point` | 17600（用 500 點） |
| 14 | carol | 曼谷設計旅店探索 | 1 | 1 | 9000 | `NULL` | `credit_card` | `none` | `NULL` |
| 15 | alice | 沖繩海景度假旅店 | 1 | 2 | 17600 | `NULL` | `credit_card` | `none` | `NULL` |
| 16 | alice | 義大利深度文化之旅 | **-1** | 1 | 72000 | `NULL` | `NULL` | `NULL` | `NULL` |
| 17 | bob | 大阪美食自由行 | **0** | 1 | 15000 | `NULL` | `atm` | `none` | `NULL` |
| 18 | carol | 紐西蘭壯麗景觀自駕遊 | **2** | 1 | 85000 | `NULL` | `credit_card` | `none` | `NULL` |
| 19 | carol | 巴黎歷史建築巡禮 | **3** | 1 | 22000 | `NULL` | `credit_card` | `none` | `NULL` |
| 20 | alice | 紐西蘭壯麗景觀自駕遊 | **4** | 1 | 85000 | `NULL` | `cvs` | `none` | `NULL` |

- 價格依據：行程 `price`（來源檔 `:204–:403` 的 tour 區段）北海道 45000、馬爾地夫 98000、義大利 72000、紐西蘭 85000、大阪 15000、高雄 4200、巴黎 22000、首爾 9500、曼谷 9000，加上第 3 項固定的沖繩 8800；`total_price` 都是整數且為 10 的倍數。
- 篩選結果（#6 定案 B，只含 `order_item.payment_status = 1`）：`user_orders`／`user_order_item` 對 alice 5 筆（#1、#4、#7、#10、#15）、bob 5 筆（#2、#6、#8、#12、#13）、carol 5 筆（#3、#5、#9、#11、#14）。#16、#17 的狀態落在 #5 定案 C（`IN (-1, 0, 1)`）的範圍內，#18、#19、#20 不在；`hotel_booking`／`restaurant_booking` 只數住宿與餐廳類項目，且訂單項目的出發日期由 Task 3 決定，所以這裡不定 `booking_count` 的目標值。
- 折抵的基底（使用者 2026-11-24 定，P4 spec §12 Q1-b）：優惠卷與點數都以促銷後金額為基底（`order_item.discount_price` 不為 NULL 且不為 0 時取它，否則 `total_price`，加總），所以訂單 #2 的 `orders.discount_price` ＝ 40500 − 10 ＝ 40490、#4 ＝ 83300 − 300 ＝ 83000（舊 controller `checkout.js:155,165` 以 `total_price` 為基底，P4 起改掉）。「實付」＝ `orders.discount_price` 不為 NULL 時取它，否則 Σ `COALESCE(NULLIF(order_item.discount_price, 0), order_item.total_price)`。
- 訂單時間：`orders.created_at` 與其 `order_item.created_at` ＝ 載入時間減 N 天，20 筆兩兩不同，讓 `user_orders` 的 `ORDER BY orders.created_at DESC`（#45）可測。帶促銷價的訂單必須落在該促銷期間內（#13：促銷價是下單當時有效的價格）：北海道的 #1、#2、#3 ＝ −9、−8、−7 天（期間 −10～+20 天），馬爾地夫的 #4、#5 ＝ −4、−3 天（期間 −5～+25 天）；其餘 #6～#20 ＝ −（36 − #）天，即 #6 −30 天、#7 −29、#8 −28 … #20 −16 天。alice 已付款訂單由新到舊依序為 #4（−4）、#1（−9）、#15（−21）、#10（−26）、#7（−29）。
- `user_coupon`（4 列，來源檔 `:911` 起）只改 `order_id` 與 `status` 的對應，`status` 不變：bob 的 `TRV010` → 訂單 #2（`status 1`）、bob 的 `VIP300` → 訂單 #6（`1`）、alice 的 `VIP300` → 訂單 #4（`1`）、carol 的 `TRV010` 未使用（`order_id` 為 `NULL`，`0`）。`orders.discount_price` ＝ 促銷後金額 − `coupon.discount`（#1 定案 B：折抵後應付金額；舊 controller `checkout.js:165` 以 `total_price` 為基底，P4 起改為促銷後，使用者 2026-11-24 定 Q1-b）。

`payment`（15 筆，每張 `payment_status = 1` 的訂單 #1～#15 各 1 筆，其餘訂單沒有——#18（已取消）、#19（已退款）刻意不建 `payment`，只滿足「已付款的訂單有 1 筆」；欄位順序與值的寫法照 `controllers/newebpay.js:182–199`，V1 `payment` 表 `V1:308–323`）：

| 欄位 | 值 |
|---|---|
| `payment_id` | 由 `payment:{email}:{title}` 決定性產生的 v4 形狀 id（形狀見本節開頭各表處理方式） |
| `user_id`、`order_id` | 該訂單的 `user_id`、`order_id` |
| `address`、`phone` | 同該訂單的 `orders.address`、`orders.phone` |
| `payment_method` | 同該訂單的 `orders.payment_type`（`newebpay.js:194` 寫 `result.PaymentType`；seed 自定值，非藍新實際格式，真實的 `PaymentType` 是 `CREDIT` 之類的代碼） |
| `payment_status` | `1` |
| `merchant_order_no` | `NULL`（V5 新增，seed 不填） |
| `discount_price` | 同該訂單的 `orders.discount_price`（`NULL` 就寫 `NULL`，`newebpay.js:196`）。seed 的 `payment.discount_price` 沿用舊規則（與 `orders.discount_price` 同值，無折扣為 `NULL`）；P4 起新建的 `payment` 寫入應付金額（P4 spec §6） |
| `return_data` | seed 自定值，非藍新實際格式：JSON 字串 `{"Status":"SUCCESS","Result":{"MerchantOrderNo":"<該訂單的 order_id>","PaymentType":"<payment_method>","Message":"付款成功"}}` |
| `return_time`、`result_time` | 載入時間 |
| `result_info` | `付款成功` |
| `created_at`、`updated_at` | 預設（載入時間） |

**10. 點數（#2、#3）**

`point_record` 共 18 筆，來源檔 `:906–:907` 的 2 筆（`新增 1610`、`減少 -436`，對應一張未付款訂單，與 #3 規則不符）刪除，改為下表。回饋按實付金額 × 10%，無條件捨去（使用者 2026-11-24 定）。

- **`新增`（15 筆）**：每張 `payment_status = 1` 的訂單（#1～#15）各 1 筆，`point` ＝ `floor(實付 × 0.1)`，`order_id` ＝ 該訂單：

  | 訂單 | #1 | #2 | #3 | #4 | #5 | #6 | #7 | #8 | #9 | #10 | #11 | #12 | #13 | #14 | #15 |
  |---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
  | `point` | 4050 | 4049 | 4050 | 8300 | 8330 | 8470 | 820 | 1260 | 2968 | 1900 | 950 | 2200 | 1760 | 900 | 1760 |

- **`減少`（3 筆）**：只有 `discount_type = 'point'` 的訂單，`point` 為負值，`|point| × 0.8 ＝ 促銷後金額 − orders.discount_price`（#7、#9、#13 無促銷，等於 `total_price`）（#3 定案 A，`checkout.js:165`）：

  | 訂單 | 使用者 | `point` | `total_price` | `discount_price` | 驗算 |
  |---|---|---|---|---|---|
  | #7 | alice | −250 | 8400 | 8200 | 250 × 0.8 ＝ 200 ＝ 8400 − 8200 |
  | #9 | carol | −400 | 30000 | 29680 | 400 × 0.8 ＝ 320 ＝ 30000 − 29680 |
  | #13 | bob | −500 | 18000 | 17600 | 500 × 0.8 ＝ 400 ＝ 18000 − 17600 |

- 沒有 `減少_確認中` 的列（結帳預覽才會寫，`checkout.js:158–161`；#2 定案 A 下 seed 與 `tour_travel_popular`、餘額都不依賴它）。未付款與已取消／退款／逾時的訂單（#16～#20）沒有 `point_record`。
- **`user_level.travel_point` 與 `point_record` 的關係（#2 定案 A）**：餘額取 `user_level.travel_point`，**不**加總 `point_record`，所以兩者不需要相等，`travel_point` 維持 alice 1500、bob 3000、carol 800（來源檔 `:116–:152`）；上表每筆 `減少` 的點數都不超過該使用者的 `travel_point`（250 ≤ 1500、400 ≤ 800、500 ≤ 3000），`pointslevel` 與 `userinfo.js` 讀到相同的餘額。

**11. 首頁好評（#48）**

`review.type = 'web'` 共 5 則：來源檔的 2 則（alice「整個網站設計非常友善，喜歡！」、bob「下單流程簡單又快速，推薦。」，來源檔 `:820–:821`）加 3 則新增（依序 carol、alice、bob；`rating` 為 1–5 的整數，內文由 Task 3 決定）。`GET /home/search/reviews` 以 `評論時間 DESC` 排序（`home.js:132`），所以 5 則的 `created_at` 兩兩不同：alice 既有 −5 天、bob 既有 −4 天，新增的三則依序 −3、−2、−1 天（載入時間減 N 天）。其餘 8 則（非 `web`）不變。

**12. 說明：本節沒有定案、由 Task 3 或使用者另行處理的事**

- `cart.total_price` 與購物車內項目的金額不一致（來源檔既有），本節不處理，也不 assert。
- 回饋取整：無條件捨去（使用者 2026-11-24 定）。
- 新增的 13 個行程只定了 `type`、`item`、`title`、`status`、促銷與少數欄位；它們的 `tour_detail`、`hotel`／`hotel_room`、`restaurant` 等子表是否補、補多少，由 Task 3 決定。沒有子表的行程，詳情頁會走到契約已記錄的「function 回 0 列時 `product.js:209` TypeError」（§4.2 末段），不影響本節的任何斷言。

## 1. A 組：商品與首頁

> A 組共通觀察（各物件裡不再重複解釋）：
>
> - 路徑前綴：公開商品 `GET /api/v1/user/product/search...`、首頁 `GET /api/v1/user/home/search/...`、管理者商品 `/api/v1/admin/product`（`routes/product_admin.js`）。
> - 「偏好分類 1/2/3」的數字（1–10）由 controller 用 `preferenceMap` 反查成中文標籤，所以三個欄位必須是 `smallint`，來源為 `tour.preference1/2/3`。
> - SQL 原文的縮排已整理，內容未改。
> - 表格「依據」欄的「JS 讀取」指 controller 取 `row.<欄位>`；「WHERE」「ORDER BY」「SELECT」指 SQL 字串用到。
> - **seed 行程詳情頁的 UUID 版本檢查（2026-10-23 補充）**：公開 `GET /api/v1/user/product/search/:tour_id`、`/:tour_id/reviews`、`/:tour_id/hidden-shares` 都先過 `product_Validator.tourIDSchema`（`utils/Validator/product_Validator.js:156`，只接受 uuidv4；呼叫處 `middlewares/product/index.js:135,165,196`），而來源檔 seed 的 10 個 `tour_id` 都是手寫值、不是 v4，所以**P1b 之前每個 seed 行程的詳情、評論、隱藏玩法都在驗證階段回 400**，`tour_tour_detail`、`tour_hotel`、`tour_restaurant`（`controllers/product.js:194–198`）在 seed 環境下走不到。同理 `GET /api/v1/web/filter/:country_id/region` 的 `other_Validator.js:5` 要求 v4，來源檔 seed 的 `country` 主鍵也都不是 v4。（P1b Task 2 之後 seed 的 `tour`、`country` 等主鍵都是 v4，這些路徑走得通。）處理見 §4.2 (a)（範圍含 `tour`、`coupon`、`user`、`country`）。

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
  | 通知狀態 | varchar | `notification.type`（'促銷' / '異動'），沒有通知時為 `NULL`；【定案 #8、#9】多筆通知時優先序 促銷 高於 異動，view 不判斷促銷期間（期間外仍是 '促銷'） | `home.js:34`、`promotion.js:42`、`admin.js:168`、`cart.js:22` | WHERE `通知狀態 = '促銷'`、CASE 條件 |
  | 旅遊名稱 | varchar | `tour.title` | `promotion.js:28`、`admin.js:168`、`product.js:1067` | SELECT 清單、ILIKE |
  | 旅遊描述 | text | `tour.description` | `admin.js:168`、`product.js:1067` | SELECT 清單、ILIKE |
  | 大分類 | varchar | `tour.type`（tourgroup / backpacker） | `home.js:34` | WHERE |
  | 小分類 | varchar | `tour.item`（travel / hotel / food / spot） | `home.js:34` | WHERE |
  | 所屬國家 | varchar | `tour.country` | `promotion.js`、`admin.js:168`、`product.js:1067` | WHERE、SELECT 清單 |
  | 所屬地區 | varchar | `tour.region` | 同上 | WHERE、SELECT 清單 |
  | 建立時間 | timestamptz | `tour.created_at`（【定案 #29】來自 `tour`） | `admin.js:168`、`product.js:1067`、`promotion.js` | ORDER BY、WHERE（`DATE(建立時間)`） |
  | 更新時間 | timestamptz | `tour.updated_at`（【定案 #29】來自 `tour`） | `promotion.js:44` | ORDER BY |
  | 價錢 | integer | `tour.price` | `cart.js:22`、`checkout.js:49`（`tourRepo.rows[0].價錢`）、`admin.js:168` | CASE 的 else 分支、JS 讀取、SELECT 清單 |
  | 促銷價錢 | double precision | `notification.promo_price`（type='促銷'）；【定案 #10】僅促銷期間內有值，期間外為 `NULL` | `cart.js:22`、`checkout.js:31` | CASE 的 then 分支 |
  | 促銷開始日期 | timestamp | `notification.start_date` | `cart.js:22` | `now() between` |
  | 促銷結束日期 | timestamp | `notification.end_date` | `cart.js:22` | `now() between` |
  | 旅遊開始日期 | timestamp | `tour.tour_start_date` | `home.js:35` | ORDER BY |
  | 旅遊代表圖 Url | text | `tour.cover_image` | `admin.js:168`、`product.js:1067` | SELECT 清單（欄位名含空格，需雙引號） |
  | 偏好分類1 / 偏好分類2 / 偏好分類3 | smallint | `tour.preference1/2/3` | `home.js:90–96`、`promotion.js:52–59` | `SELECT *` 之後 JS 讀 `row['偏好分類1']` 並移除 |

  `SELECT *` 的呼叫端（`home.js`、`promotion.js`）會把每一個欄位原樣放進 response（只拿掉偏好分類 1/2/3、加上「偏好分類」），所以 view 的欄位集合就是 API 輸出欄位集合。本節只列出程式碼可證實需要的欄位。`旅遊標語`、`旅遊結束日期`、`旅遊天數`、`旅遊代表圖` 等是否也在 view，程式碼無法證實，見待確認 3。【定案 #26】`tour_base` 的欄位集合與 `tour_travel` 相同（只差 `收藏狀態`），`旅遊標語`、`旅遊結束日期`、`旅遊天數`、`旅遊代表圖 Url` 也在 `tour_base`；`異動通知內容` 【定案 #26，2026-10-23 controller 裁決】也納入 `tour_base` 與 `tour_travel`（`notification.change_desc`，type='異動'，與 `tour_tour_detail` 同源），兩者同步（依 A）。

- **列的語意**：每個行程（`tour`）一列，欄位來自 `tour` 並帶入該行程的通知（`notification`）資料。推測：管理者查詢 `上下架狀態` 有 1/2 兩種值，表示 view 含上架與下架的行程（是否成立見待確認 1；【定案 #7】`tour_base` 含全部行程，含下架）。沒有預設排序（每個呼叫端自己 ORDER BY）。
- **邊界**：
  - 沒有通知的行程必須仍會出現，通知相關欄位為 `NULL`（依據：admin 商品清單要列出所有行程；`cart.js` 的 CASE 對 `通知狀態` 為 NULL 時走 `else 價錢`）。因此對 `notification` 必須是 LEFT JOIN。
  - 價錢計算 `now() between 促銷開始日期 and 促銷結束日期` 是 controller 自己判斷，所以 view 本身不需要處理促銷是否在期間內（但見待確認 4；【定案 #9】view 仍不判斷促銷期間，由 controller 判斷）。
  - **首頁 API 的 controller 行為（影響 `tour_base`、`tour_travel`、`popular`、`most_favorited` 所有首頁查詢）**：`routes/home.js` 的 `/products` 使用的 middleware（`middlewares/home/index.js:7`）驗證時用 `home_Validator.reviewSchema`，只把 `page`、`limit`、`lang` 設為必填，且 `validate()` 回傳的 value（含 default）沒有寫回 `req.query`。`type` 沒帶時 `home.js:12–84` 一個分支都不進，`tourData` 維持 `''`，`home.js:86` 的 `''.rows.length` 丟 TypeError，API 回 500；`type=tourgroup` 沒帶 `item` 同理。契約只記錄，不處理。
  - `checkout.js:31` 在非促銷時回 `0`，而 `cart.js:22` 回 `價錢`，兩者語意不同，view 只要提供原始欄位即可。
- **信心**：欄位名稱與來源對應：確定（名稱直接出現在 SQL，來源與 V1 欄位一一對應）。是否過濾下架、一行程對多通知的處理：推測，見待確認。
- **待確認**：
  1. **view 是否只含上架（`status = 1`）的行程？** → §4.1 #7（定案：`tour_base` 含全部行程（含下架）；`tour_travel`、`tour_travel_popular`、`tour_travel_most_favorited`、`tour_tour_detail` 只回 `status = 1`）
     - 程式碼矛盾：`admin.js:168`／`product.js:1067` 用 `上下架狀態` 篩選，表示 view 要含下架；但 `home.js:15/33/49/68` 的公開首頁直接查 `tour_base`，沒有任何上架過濾。
     - 解讀 A：view 含全部行程。後果：首頁（未登入）會列出下架行程；`cart.js`／`checkout.js` 查價也能查到下架行程；admin 功能正常。
     - 解讀 B：view 只含 `status = 1`。後果：首頁正常，但 `GET /admin/product?status=2` 永遠空、管理者清單看不到下架行程。上架 API 本身不受影響（`patch_tourStatus`，`product.js:1332–1341`，直接 `UPDATE public."tour"`，不經過 `tour_base`），只是前端清單裡沒有可選的 `tour_id`。
     - 解讀 C：view 含全部，公開端的過濾交給 `popular` 等 function。後果：`promotion`／`backpacker` 以外各路徑需要逐一確認，`home.js:33` 的 promotion 路徑仍會露出下架行程。
  2. **一個行程有多筆通知（例如同時有「促銷」和「異動」）時，一列要怎麼呈現？** → §4.1 #8（定案：每個行程一列；促銷與異動各自成欄（`促銷價錢` 等取自 type='促銷'、`異動通知內容` 取自 type='異動'），`通知狀態` 優先序 促銷 高於 異動，同類型多筆取 `updated_at` 最大者）
     - `notification` 無 unique 約束，一個 `tour_id` 可有多列。
     - 解讀 A：每個行程只取一筆通知（例如最新一筆）。後果：`通知狀態` 只會是其中一個；有「促銷」又有「異動」時，其中一種會看不到（`cart.js` 就會讀不到促銷價）。
     - 解讀 B：促銷與異動各自成欄（`促銷價錢`…來自 type='促銷' 的那筆、`異動通知內容` 來自 type='異動' 的那筆），`通知狀態` 取優先順序較高者。後果：需另定優先順序；`tour_tour_detail` 同時讀 `異動通知內容` 和 `通知狀態`，這個解讀較能同時提供兩者。
     - 解讀 C：不合併，每筆通知一列。後果：同一個行程在首頁、admin 清單重複出現，`cart.js` 的 `priceRepo.rows[0]` 取到哪一列不固定。
  3. **view 是否包含 `旅遊標語`、`旅遊結束日期`、`旅遊天數`、`旅遊代表圖 Url`、`異動通知內容` 等欄位？** → §4.1 #26（定案：`tour_base` 與 `tour_travel` 欄位集合相同（`tour_travel` ＝ `tour_base` ＋ `收藏狀態`），含 `異動通知內容`）
     - `tour_travel(uuid)` 的 WHERE／排序使用這些欄位（見該物件），而 `tour_base` 與它在首頁共用同一個 JS 轉換，前端很可能以相同欄位集合讀取。
     - 解讀 A：`tour_base` 與 `tour_travel` 欄位一致（只差 `收藏狀態`）。後果：登入與未登入首頁 response 結構相同。
     - 解讀 B：`tour_base` 只含上面表格的欄位。後果：未登入與登入的首頁 response 欄位不同，前端要處理兩種形狀。
  4. **促銷是否在 view 內就判斷是否在期間內？** → §4.1 #9（定案：view 不判斷促銷期間，期間外 `通知狀態` 仍是 '促銷'）
     - 解讀 A：view 不判斷，期間外仍顯示 `通知狀態='促銷'`（依 `cart.js` 自己再檢查 `now() between` 推測）。後果：首頁「促銷」分頁會列出已過期的促銷行程，價格欄位卻是原價。
     - 解讀 B：view 內只在期間內才回 '促銷'。後果：`cart.js` 的檢查變成多餘但無害；首頁促銷分頁不會有過期行程。
  5. **`建立時間`／`更新時間` 來自 `tour` 還是 `notification`？** → §4.1 #29（定案：`建立時間`、`更新時間` 都來自 `tour`（`tour.created_at`／`tour.updated_at`））
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
  | 通知狀態 | varchar | `notification.type`（見 `tour_base` 待確認 2；【定案 #8】同 `tour_base`） | `home.js:42` | WHERE |
  | 旅遊開始日期 | timestamp | `tour.tour_start_date` | `home.js:43`、`product.js:68`、`product.js:106–109`（排序） | ORDER BY、WHERE |
  | 旅遊結束日期 | timestamp | `tour.tour_end_date` | `product.js:73` | WHERE |
  | 旅遊天數 | integer | `tour.days` | `product.js:78` | WHERE |
  | 價錢 | integer | `tour.price` | `product.js:58,63,106` | WHERE、ORDER BY |
  | 旅遊名稱 | varchar | `tour.title` | `product.js:83` | WHERE（ILIKE） |
  | 旅遊標語 | varchar | `tour.slogan` | `product.js:83` | WHERE（ILIKE） |
  | 所屬國家 | varchar | `tour.country` | `product.js:48` | WHERE（ILIKE） |
  | 所屬地區 | varchar | `tour.region` | `product.js:53` | WHERE（ILIKE） |
  | 偏好分類1 / 2 / 3 | smallint | `tour.preference1/2/3` | `product.js:42,126–143`、`home.js:90–96` | WHERE（ANY ARRAY）、JS 讀 `row['偏好分類1']` |
  | 收藏狀態 | boolean | `EXISTS (favorite WHERE user_id = 參數 AND tour_id = tour.tour_id)`；【定案 #28】未登入（參數 `NULL`）時為 `false` | 無直接讀取（見推測） | 推測：函式要帶入使用者編號的唯一合理理由；`tour_tour_detail` 的同名欄位 `收藏狀態` 被讀為 `is_favorited` |

  其餘欄位（`旅遊描述`、`旅遊代表圖 Url`、`促銷價錢`、`促銷開始日期`、`促銷結束日期`…）：呼叫端都是 `SELECT *` 且 controller 沒有讀取具體 key，但 response 會原樣輸出，欄位集合是否與 `tour_base` 相同見待確認 2（【定案 #26】相同，只差 `收藏狀態`）。

- **列的語意**：每個行程一列，欄位與 `tour_base` 類似，額外附上傳入使用者是否已收藏。排序由呼叫端決定。【定案 #7、#27】只回 `status = 1` 的行程，不限 `item`（旅行團與背包客的所有種類）。
- **邊界**：
  - 傳入 `NULL`（未登入）時 `product.js:116` 仍會呼叫它，所以 function 必須接受 `NULL` 並回傳全部行程（`收藏狀態` 應為 `false` 或 `NULL`，見待確認 3；【定案 #28】`false`）。
  - 沒有收藏紀錄的行程要保留（相當於 `LEFT JOIN favorite` 或 `EXISTS`），否則商品搜尋會漏行程。
  - 與 `popular`／`most_favorited` 是 `INNER JOIN`，沒出現在後者結果的行程不會出現在首頁。
  - 首頁 API 沒帶 `type` 時整個回 500，見 `tour_base` 邊界（`middlewares/home/index.js:7` 用 `reviewSchema`，default 沒寫回 `req.query`）。
- **信心**：參數與用於過濾／排序的欄位：確定。`收藏狀態` 與是否過濾上架：推測。
- **待確認**：
  1. **function 名稱是 travel，但被用在所有種類（旅行團 travel、背包客 hotel/food/spot）。** → §4.1 #27（定案：回傳所有種類，不限 `item = 'travel'`）
     - 證據：`product.js:116` 的 `whereSQL` 可帶任意 `大分類`／`小分類`（驗證器允許 backpacker 的 hotel/food/spot）；`home.js:77` 在 `type=backpacker` 時也呼叫它。
     - 解讀 A：回傳所有種類。後果：商品搜尋與首頁背包客分頁正常。
     - 解讀 B：只回傳 `item='travel'`。後果：`GET /user/product/search?type=backpacker` 與首頁背包客（已登入）永遠為空，但「未登入」路徑（用 `tour_base`）仍有資料，兩者行為不一致。
  2. **欄位集合是否與 `tour_base` 相同再加 `收藏狀態`。** → §4.1 #26（定案：欄位集合 ＝ `tour_base` 的欄位 ＋ `收藏狀態`，含 `異動通知內容`）
     - 解讀 A：相同（再加 `收藏狀態`）。後果：登入／未登入首頁 response 欄位只差 `收藏狀態`。
     - 解讀 B：欄位較少或較多。後果：首頁登入與未登入兩個 response 形狀不一致；前端若依賴多出的欄位會在其中一種狀態讀到 `undefined`。
  3. **未登入（`NULL` 參數）時 `收藏狀態` 該是 `false` 還是 `NULL`？** → §4.1 #28（定案：`false`）
     - 解讀 A：`false`。後果：前端 `is_favorited` 一律是布林值。
     - 解讀 B：`NULL`。後果：JSON 內是 `null`，前端的布林判斷結果一樣，但嚴格比較（`=== false`）的測試會失敗。
  4. **是否只回傳上架行程？**（同 `tour_base` 待確認 1） → §4.1 #7（定案：只回 `status = 1`）
     - 解讀 A：只回 `status = 1`。後果：商品搜尋看不到下架行程，符合 `get_tourDetails` 對 `status = 1` 的處理；解讀 B：回傳全部。後果：下架行程出現在公開搜尋。

### `tour_travel_popular`

- **種類**：function（`tour_travel_popular(大分類 text, 小分類 text) RETURNS TABLE(tour_id uuid, 購買排行 integer)`）
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
  | 購買排行 | integer（【定案 #25】） | 依 `order_item`（購買數）由多到少的名次，1 為最熱門；【定案 #4】購買數只算 `payment_status = 1`，【定案 #24】`ROW_NUMBER()` 並加次要排序；**購買數是 `order_item` 的列數，不是 `quantity` 加總**（controller 裁決 2026-10-25：#4 只定狀態，未定計數方式；以 seed 資料兩種算法名次相同；**使用者 2026-11-19 確認**（P3 spec §2.2）） | `home.js:18,27,71,80` | ORDER BY ASC，數字小的在前 |

  `SELECT *` 讓 `tour_id` 與 `購買排行` 一起進入 response（`tour_id` 是額外的英文欄位）。

- **列的語意**：符合 (大分類, 小分類) 的行程，各一列，附上購買排行名次。【定案 #4、#7、#23、#24】只計 `payment_status = 1` 的購買；只回 `status = 1` 的行程；沒有購買的行程也出現並排在最後；並列時以 `ROW_NUMBER()` 加次要排序 `tour_id`（升冪；【定案 #24】）。
- **邊界**：
  - 首頁 API 沒帶 `type` 時整個回 500，不會走到本 function，見 `tour_base` 邊界。
  - 欄位名 `tour_id` 是英文，與其他全部欄位的中文命名不同，但程式碼寫死 `tf.tour_id`，必須照做。
  - 因為是 `INNER JOIN`，沒有出現在此 function 結果裡的行程不會出現在首頁熱門分頁。
- **信心**：參數順序與輸出欄位名：確定（值與欄位名稱直接出現在程式碼）。排名計算方式：推測（只由 `購買排行` 一詞推測）；`bigint` 型別是依 window function／COUNT 的回傳型別推測，程式碼不讀它的型別。【定案 #25】型別改為 `integer`（view／function 內 `::int`）。
- **待確認**：
  1. **「購買」怎麼算？** → §4.1 #4（定案：只算 `order_item.payment_status = 1`（已付款））
     - 解讀 A：數 `order_item` 全部列。後果：未付款、已取消的訂單也計入，排行被灌水。
     - 解讀 B：只算 `payment_status = 1`（已付款）。後果：新 DB／seed 若沒有已付款訂單，熱門分頁整個為空；P1b 的 seed 需要包含已付款訂單。
     - `order_item.payment_status` 的值：-1 資料剛建立、0 資料填寫完成未付款、1 已付款、2 已取消、3 已退款、4 付款逾時。`checkout.js:48` 建立 `order_item` 時一律寫入 -1，所以解讀 A 連尚未填寫就放棄的結帳也會計入。
     - 解讀 C：只排除 2（已取消）、3（已退款）、4（付款逾時），保留 -1、0、1。後果：仍計入未付款的訂單。
     - 解讀 D：只算 0 與 1（已填寫完成、已付款）。後果：排除剛建立與所有失敗狀態，介於 A、B 之間。
  2. **沒有任何購買的行程要不要出現？** → §4.1 #23（定案：沒有購買的行程也出現，排在最後（`LEFT JOIN`，計數 0））
     - 解讀 A：出現，排在最後（`LEFT JOIN`，排行用計數 0 排序）。後果：新 DB 熱門分頁仍有資料。
     - 解讀 B：不出現（`INNER JOIN order_item`）。後果：沒有訂單時首頁熱門分頁回 200「查無資料」。
  3. **排名並列時怎麼處理？** → §4.1 #24（定案：`ROW_NUMBER()` 並加次要排序（`tour_id`），分頁穩定）
     - 解讀 A：`RANK()`（並列同名次）。後果：`ORDER BY 購買排行 ASC LIMIT/OFFSET` 在並列時沒有次要排序，分頁可能重複或漏列。
     - 解讀 B：`ROW_NUMBER()` 並加次要排序。後果：分頁穩定，並列者的先後取決於次要排序的選擇。
  4. **是否只回傳上架行程？**（同 `tour_base` 待確認 1） → §4.1 #7（定案：只回 `status = 1`）
     - 解讀 A：過濾上架。後果：未登入路徑（`tour_base`）不會露出下架行程；解讀 B：不過濾。後果：下架行程可能進入熱門排行。

### `tour_travel_most_favorited`

- **種類**：function（`tour_travel_most_favorited(大分類 text, 小分類 text) RETURNS TABLE(tour_id uuid, 收藏排行 integer)`）
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
  | 收藏排行 | integer（【定案 #25】） | 依 `favorite` 筆數由多到少的名次，1 為最多人收藏 | `home.js:52,61` | ORDER BY ASC |

- **列的語意**：符合 (大分類, 小分類) 的行程，各一列，附上被收藏次數的排行。【定案 #7、#23、#24】只回 `status = 1` 的行程；沒有人收藏的行程也出現並排在最後；並列時以 `ROW_NUMBER()` 加次要排序 `tour_id`（升冪；【定案 #24】）。只在 `type=tourgroup&item=most_favorited` 使用，因此程式碼只會用 `('tourgroup','travel')` 呼叫。
- **邊界**：與 `tour_travel_popular` 相同——欄位 `tour_id` 為英文；`INNER JOIN` 決定首頁是否出現。
- **信心**：參數與欄位名：確定。排名計算：推測；`bigint` 型別為推測（依 window function／COUNT 的回傳型別）。【定案 #25】型別改為 `integer`（view／function 內 `::int`）。
- **待確認**：
  1. **沒有任何人收藏的行程要不要出現？** → §4.1 #23（定案：沒有人收藏的行程也出現，排在最後（`LEFT JOIN`，計數 0））
     - 解讀 A：出現，排在最後。後果：新 DB 也有資料。
     - 解讀 B：不出現。後果：沒有 `favorite` 資料時首頁「最多收藏」回「查無資料」，P1b 的 seed 需要包含收藏紀錄。
  2. **並列名次與分頁穩定性**：同 `tour_travel_popular` 待確認 3（`RANK()` 與 `ROW_NUMBER()` 的後果相同）。 → §4.1 #24（定案：`ROW_NUMBER()` 並加次要排序（`tour_id`），分頁穩定）
  3. **是否只回傳上架行程**：同 `tour_base` 待確認 1。 → §4.1 #7（定案：只回 `status = 1`）

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
  | 收藏狀態 | boolean | `EXISTS (favorite WHERE user_id = 參數 AND tour_id = tour.tour_id)`；【定案 #28】未登入時為 `false` | `product.js:356` | response.is_favorited |
  | 異動通知內容 | text | `notification.change_desc`（type='異動'） | `product.js:357` | response.emergency_notice |
  | 促銷價錢 | double precision | `notification.promo_price`（type='促銷'）；【定案 #10】僅促銷期間內有值，期間外為 `NULL` | `product.js:359–360` | response.promotion.is_promoted（真偽）、promo_price |
  | 通知狀態 | varchar | `notification.type`（【定案 #8、#9】促銷優先；期間外仍是 '促銷'） | `product.js:361` | response.promotion.tag |
  | 促銷開始日期 | timestamp | `notification.start_date` | `product.js:362` | response.promotion.start_at |
  | 促銷結束日期 | timestamp | `notification.end_date` | `product.js:363` | response.promotion.end_at |

- **列的語意**：每個行程一列（`travel`、`spot` 都只讀 `rows[0]`），行程資料加上 `tour_detail`、通知資料，以及傳入使用者的收藏狀態。【定案 #7、#8】只回 `status = 1` 的行程；一個行程一列（促銷與異動各自成欄）。
- **邊界**：
  - 欄位命名不一致，必須照程式碼拼字：`偏好設定分類 1`（有空格，與 `tour_base` 的 `偏好分類1` 不同）、`特色圖1 url`（小寫）、`旅遊圖1 Url`（大寫）、`Google Map Url`。
  - `促銷價錢` 為 `NULL` 時 `is_promoted` 為 `false`（`product.js:359`），所以沒有促銷時必須是 `NULL`，不能是 `0`。【定案 #10】促銷期間外也是 `NULL`，所以期間外 `is_promoted` 為 `false`。
  - **找不到行程時的 controller 行為**（`product.js:178–202`）：先查 `tour` 的 `status = 1`；查不到（tour_id 不存在、已下架）或 type/item 不在對照表（例如 tourgroup 但 item 不是 travel）時 `detailTable` 維持 `''`，SQL 變成 `SELECT * FROM ($2) WHERE 旅遊編號 = $1`（`product.js:202`），PostgreSQL 回語法錯誤，API 回 500，永遠回不到「查無此旅遊項目」。`tour_hotel`、`tour_restaurant` 共用這段，同樣適用。
  - 行程存在、但 function 回 0 列時，`product.js:209` 讀 `rows[0]["偏好設定分類 1"]` 會先丟 TypeError（`rowCount > 0` 檢查在 `product.js:215`，在其後），API 一樣回 500。這只會在 `status = 1` 的行程被 function 濾掉（例如 `spot` 沒有 `tour_detail` 列而 `INNER JOIN`）時發生。
  - 以上為 controller 行為，契約不處理，只記錄。
  - 對 `tour_detail` 必須是 `INNER JOIN` 或 `LEFT JOIN`：`spot` 也用此 function 並讀特色圖（`product.js:335`），若 `spot` 行程沒有 `tour_detail` 列，`INNER JOIN` 會使整列消失（500），`LEFT JOIN` 則特色圖為 `NULL`。【定案 #30】採 `LEFT JOIN`。
- **信心**：欄位名稱與來源對應：確定。通知相關欄位的合併方式、`spot` 與 `tour_detail` 的關係：推測。
- **待確認**：
  1. **一個行程有多筆通知時**（同 `tour_base` 待確認 2）：本物件同時讀 `異動通知內容` 與 `促銷價錢`／`通知狀態`，因此兩者要在同一列。 → §4.1 #8（定案：同 `tour_base` 待確認 2 的定案：促銷與異動各自成欄，一行程一列，`通知狀態` 促銷優先）
     - 解讀 A：只取一筆通知。後果：促銷與異動只會顯示其一。
     - 解讀 B：促銷與異動分欄合併成一列。後果：兩者都能顯示；`通知狀態` 需另定規則。
     - 解讀 C：每筆通知一列。後果：`rows[0]` 取哪筆不固定，且 `hotel`／`food` 的 `rows.map` 會重複。
  2. **`spot` 行程是否保證有 `tour_detail` 列？** → §4.1 #30（定案：`LEFT JOIN tour_detail`，沒有 `tour_detail` 時特色圖、行程規劃為 `NULL`）
     - 解讀 A：保證（`INNER JOIN`）。後果：seed 與新增商品流程必須為每個 spot 建 `tour_detail`，否則詳情頁 500。
     - 解讀 B：不保證（`LEFT JOIN`）。後果：沒有 `tour_detail` 時特色圖、行程規劃為 `NULL`，頁面可顯示。
  3. **只回傳上架行程？** 前面 `product.js:178–183` 已先以 `status = 1` 過濾，因此 function 內是否過濾不影響此 API，但影響其他未來呼叫端。解讀 A：過濾；解讀 B：不過濾。 → §4.1 #7（定案：function 內只回 `status = 1`）
  4. **`收藏狀態` 在未登入時是 `false` 還是 `NULL`**：同 `tour_travel` 待確認 3。 → §4.1 #28（定案：`false`）

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
  | 房型描述 | varchar | `hotel_room.image_desc`（推測；【定案 #31】採用 `image_desc`） | `product.js:411` | response.feature.room[].description |
  | 房型容納人數 | integer | `hotel_room.capacity` | `product.js:412` | response.feature.room[].capacity |
  | 房型數量 | integer | `hotel_room.room_count` | `product.js:413` | response.feature.room[].room_count |
  | 房型代表圖 url（小寫 url） | text | `hotel_room.image` | `product.js:414` | response.feature.room[].image_url |
  | 基本設施與服務 | text | `hotel.facility_desc` | `product.js:419` | response.feature.service[0].item |
  | 餐飲相關服務 | text | `hotel.food_desc` | `product.js:423` | response.feature.service[1].item |
  | 客房與設施 | text | `hotel.room_desc` | `product.js:427` | response.feature.service[2].item |
  | 交通與停車 | text | `hotel.traffic_desc` | `product.js:431` | response.feature.service[3].item |
  | 其他便利服務 | text | `hotel.other_desc`（推測，見待確認 2；【定案 #32】採用 `other_desc`，`leisure_desc` 不輸出） | `product.js:435` | response.feature.service[4].item |
  | 所屬國家、所屬地區、地址、Google Map Url、旅遊描述 | 同 `tour_tour_detail` | 同 `tour_tour_detail` | `product.js:440–445` | response.location / description |
  | 偏好設定分類 1 / 2 / 3 | smallint | `tour.preference1/2/3` | `product.js:209–211` | response.tags |
  | 收藏狀態、異動通知內容、促銷價錢、通知狀態、促銷開始日期、促銷結束日期 | 同 `tour_tour_detail` | 同 `tour_tour_detail` | `product.js:447–454` | response.is_favorited / emergency_notice / promotion |

- **列的語意**：**每個房型一列**（`hotel_room` 一列對應一列輸出），行程與飯店層級的欄位在每一列重複。依據：`product.js:409` 用 `tourDetailsRepo.rows.map(...)` 逐列產生 `room[]`；其他欄位只讀 `rows[0]`。
- **邊界**：
  - 沒有房型的飯店：`INNER JOIN hotel_room` 會使整間飯店消失；`LEFT JOIN` 會有一列、房型欄位為 `NULL`，response 的 `room` 會是一個全為 `null` 的物件。【定案 #33】採 `LEFT JOIN`。
  - 房型的先後順序沒有 `ORDER BY` 可供依據。
  - 欄位命名同樣不一致，必須照拼字：`房型代表圖 url`（小寫）。
- **信心**：欄位名稱：確定；來源對應：大部分確定，`房型描述`、`其他便利服務` 為推測。
- **待確認**：
  1. **`房型描述` 沒有明確來源**：`hotel_room` 只有 `image_desc`（圖片描述）。 → §4.1 #31（定案：`房型描述 = hotel_room.image_desc`）
     - 解讀 A：`房型描述 = hotel_room.image_desc`。後果：前端房型描述就是圖片說明文字。
     - 解讀 B：需新增 `hotel_room.description`（要改 migration）。後果：超出「V3 只建 view/function」範圍，需要另外新增欄位。
  2. **`hotel` 有 6 個描述欄位（`facility_desc`、`food_desc`、`room_desc`、`leisure_desc`、`traffic_desc`、`other_desc`），controller 只讀 5 個**： → §4.1 #32（定案：`其他便利服務 = hotel.other_desc`，`leisure_desc` 不輸出）
     - 解讀 A：`其他便利服務 = other_desc`，`leisure_desc` 被忽略。後果：`leisure_desc` 的資料不會在 API 顯示。
     - 解讀 B：`其他便利服務 = leisure_desc`，`other_desc` 被忽略。後果：同樣有一個欄位資料被忽略，但被忽略的是另一個。
     - 解讀 C：兩者串接。後果：兩者都能顯示，但需要定分隔格式。
  3. **沒有房型的飯店是否出現**：解讀 A：`INNER JOIN`，飯店消失；解讀 B：`LEFT JOIN`，出現一列全為 `null` 的房型。 → §4.1 #33（定案：`LEFT JOIN`，沒有房型的飯店出現一列、房型欄位為 `NULL`）
  4. **通知多筆時的處理**：同 `tour_tour_detail` 待確認 1；多筆通知與多房型相乘，若採解讀 C（每筆通知一列），`room[]` 會重複。 → §4.1 #8（定案：一行程一列（促銷與異動各自成欄），`room[]` 不會因通知而重複）

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

- **列的語意**：同一個 function 的一列同時要供 `menu[]` 和 `opening[]` 使用——`product.js:263` 與 `product.js:268` 都是 `tourDetailsRepo.rows.map(...)`，各自讀同一組列的不同欄位。餐廳層級欄位在每列重複。【定案 #34】採 `UNION ALL`／位置對齊：每列各帶一筆菜單或一筆營業時間，另一邊為 `NULL`（陣列內有 `name: null` 或 `week: null` 的空項），不重複。
- **邊界**：
  - 依賴 V1 的 `restaurant_business`／`restaurant_menu`；程式碼另外查詢 `restaurant_business_parsed`（V1／V2 沒有，是 B 組物件，使用於 `middlewares/cart/index.js`），本物件是否使用它無法由 A 組程式碼證實。
  - 欄位命名必須照拼字：`官網 url`（小寫）、`官網介紹`、`餐廳人員限制`。
  - 【定案 #33】沒有菜單或沒有營業時間的餐廳以 `LEFT JOIN` 保留，空項欄位為 `NULL`。
- **信心**：欄位名稱：確定；列的展開方式：推測（見待確認 1）。
- **待確認**：
  1. **`menu[]` 與 `opening[]` 共用 `rows`，列要怎麼展開？** → §4.1 #34（定案：`UNION ALL`／位置對齊：每列各帶一筆菜單或一筆營業時間，另一邊為 `NULL`，沒有重複（3 ＋ 7 ＝ 10 列））
     - 解讀 A：`restaurant_menu` 與 `restaurant_business` 做 CROSS JOIN（菜單數 × 營業日數）。後果：兩個陣列各有大量重複項（例如 3 道菜 × 7 天 = 21 列，`menu[]` 與 `opening[]` 各 21 項）；程式碼不改的話前端會看到重複資料。
     - 解讀 B：用 `UNION ALL`／位置對齊，使每列各帶一筆菜單或一筆營業時間，不足的欄位為 `NULL`。後果：陣列內會有 `name: null` 或 `week: null` 的空項。
     - 解讀 C：每個餐廳一列，菜單與營業時間聚合進欄位（例如 JSON）。後果：`row.菜單名稱` 會是陣列／JSON，與 `rows.map` 的用法不符，controller 不改就無法使用。
  2. **沒有菜單或沒有營業時間的餐廳是否出現**：解讀 A：`INNER JOIN`，餐廳消失（500）；解讀 B：`LEFT JOIN`，空項為 `null`。 → §4.1 #33（定案：`LEFT JOIN`，沒有菜單或營業時間的餐廳仍出現，空項為 `null`）
  3. **通知多筆時的處理**：同 `tour_tour_detail` 待確認 1。 → §4.1 #8（定案：一行程一列（促銷與異動各自成欄，促銷優先））

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

  欄位名稱與 `user_level_point_coupon`（B 組，見 §2；`userProfile.js:145–147` 讀 `旅遊等級`、`旅遊等級名稱`、`旅遊徽章 Url`）一致，型別與來源也相同（Task 7 已核對）。

- **列的語意**：每位使用者一列，包含使用者資料與其會員等級。
- **邊界**：
  - 【定案 #22】`LEFT JOIN`，沒有 `user_level` 列時等級欄位為 `NULL`；有多筆時取最新一筆（`updated_at` 最大），每位使用者最多一列。
  - 是 `INNER JOIN` 還是 `LEFT JOIN` 在 view 內決定：`user_level` 在 V1 有 `user_id`，沒有 unique 約束；`level`、`name`、`badge_url` 在 V1 都是 `NULL` 可以空（註解「正式需要 not null」）。
  - 沒有 `user_level` 列的使用者，如果 view 用 `INNER JOIN`，他的評論與隱藏玩法在上述兩個 API 會被 controller 的 `inner JOIN` 一起濾掉。
  - `旅遊等級`（V1 是 `VARCHAR`）在 `product.js:571` 直接放入 `level.level`，型別為字串。
- **信心**：欄位名稱與來源：確定（V1 `user`／`user_level` 欄位一一對應）。JOIN 方式與重複列：推測。
- **待確認**：
  1. **使用者沒有 `user_level` 列時怎麼辦？** → §4.1 #22（定案：`LEFT JOIN`，沒有 `user_level` 列時等級欄位為 `NULL`）
     - 解讀 A：view 用 `INNER JOIN`（沒有等級資料就不在 view 內）。後果：該使用者的評論、隱藏玩法在商品頁消失；seed 必須為每個使用者建 `user_level`。（註冊流程 `userinfo.js:31,209` 會建立 `user_level`，所以正常註冊的使用者都有。）
     - 解讀 B：view 用 `LEFT JOIN`，等級欄位為 `NULL`。後果：評論仍顯示，`level` 物件內欄位為 `null`。
  2. **一個使用者有多筆 `user_level` 時？**（V1 沒有 unique） → §4.1 #22（定案：取最新一筆（`updated_at` 最大））
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

  controller 沒有讀取其他 key，`SELECT *` 的欄位原樣輸出到 response，因此程式碼本身**無法證實**還需要哪些欄位。以下依名稱與 `user_user_level`（同一組作者）合理推測的欄位，原為推測，2026-10-23 使用者採為定案（見待確認 1；【定案 #11】欄位集合選 A，以下表為準；frontend `phase-0` 沒有讀取此 API）：

  | 欄位（中文） | 型別 | 來源（【定案 #11】） |
  |---|---|---|
  | 評論編號 | uuid | `review.review_id` |
  | 名稱 | varchar | `user.name` |
  | 個人照片 Url | varchar | `user.avatar_url` |
  | 旅遊等級 | varchar | `user_level.level` |
  | 旅遊等級名稱 | varchar | `user_level.name` |
  | 旅遊徽章 Url | varchar | `user_level.badge_url` |
  | 評分 | integer | `review.rating` |
  | 評論內容 | text | `review.content` |

- **列的語意**：（推測，見待確認 2；【定案 #48】只含 `review.type = 'web'`）「網站整體好評」——`review` 中 `type = 'web'` 的評論（V1 註解：`type` 可以是 web / travel / hotel / food / spot；路由註解 `[GET] 編號 27 : 使用者查看此網頁好評內容`）。每則評論一列，附上評論者的名稱與等級。預設排序由 controller 決定（`評論時間 DESC`）。
- **邊界**：
  - `review.tour_id` 在 V1 可為 `NULL`，網站評論（`type='web'`）通常沒有 `tour_id`，所以 view 不能要求 `tour_id` 存在。
  - 評論者需有 `user_level` 才會出現的規則，同 `user_user_level` 待確認 1（【定案 #22】`LEFT JOIN`）。
- **信心**：推測。controller 只證實 `評論時間`；其餘欄位與篩選條件都來自名稱與註解的推測。
- **待確認**：
  1. **欄位集合與欄位中文名稱**：程式碼沒有讀取任何 key，前端（P0 凍結的 `phase-0`）會依實際欄位名稱讀取。 → §4.1 #11（定案 2026-10-23：欄位集合選 A，以上面的欄位表為準；frontend `phase-0` 不讀此 API，日後 P3–P6 接前端時若 key 不符，依 spec 重構規則連同 view、契約、契約測試一起改）
     - 解讀 A：照上面的推測欄位建立。後果：若前端的欄位名稱不同，首頁好評區塊會缺資料，要在 V3 前核對 `frontend`（P1a 不動 frontend）。
     - 解讀 B：先查 frontend 實際讀取的 key 再定。後果：多花一道工，但欄位名稱正確。
  2. **篩選條件**： → §4.1 #48（定案：只含 `review.type = 'web'`）
     - 解讀 A：只含 `review.type = 'web'`。後果：首頁只顯示網站整體好評；若 seed 沒有 web 類評論，首頁好評區塊為空。
     - 解讀 B：含所有 `review`（不限 type）。後果：行程評論（travel／hotel／food／spot）也會顯示在首頁。
     - 解讀 C：只含評分達標（例如 `rating >= 4`）的評論，名稱中的「好評」。後果：需要另定門檻；低分評論不會出現。
  3. **評論者沒有 `user_level` 列時是否出現**：同 `user_user_level` 待確認 1（INNER vs LEFT JOIN）。 → §4.1 #22（定案：`LEFT JOIN`，評論者沒有 `user_level` 列時評論仍出現、等級欄位為 `NULL`；有多筆時取最新一筆）

## 2. B 組：購物車、訂位、折扣、結帳

> B 組共通觀察（各物件裡不再重複解釋）：
>
> - 路徑前綴：購物車 `/api/v1/user/trade/cart`（`routes/cart.js`）、折扣 `/api/v1/user/trade/discounts`（`routes/discounts.js`）、結帳 `/api/v1/user/checkout`（`routes/checkout.js`）、會員積分 `GET /api/v1/user/userinfo/pointslevel`（`routes/userProfile.js:32`）、管理者 `GET /api/v1/admin/members/:user_id/coupons`（`routes/admin.js:53`）。
> - 路徑相對於 `backend/src/`；SQL 原文的縮排已整理，內容未改。
> - 表格「依據」欄的「JS 讀取」指 controller／middleware 取 `row.<欄位>`；「WHERE」「ORDER BY」指 SQL 字串用到。
> - **pg 型別對應 JS 的限制（影響欄位型別選擇）**：`pg` 會把 `smallint`／`integer`／`float8` 回成 JS number，但 `bigint`（`COUNT(...)` 的型別）與 `numeric` 回成字串。凡是 controller 用 `=== 1`、`+`、`<` 直接運算的欄位，下面都標了型別，不能隨意換。
> - **識別字大小寫**：未加雙引號的名稱 PostgreSQL 會轉成小寫。程式碼用 `public."user_cartList"`（有引號）所以 view 要以**帶雙引號的混合大小寫**建立；`restaurant_isClosed(...)` 在程式碼沒有引號，所以 function 要以**小寫 `restaurant_isclosed`**（或不加引號的 `restaurant_isClosed`，兩者等價）建立，若用 `"restaurant_isClosed"`（有引號）建立則呼叫會失敗。
> - 跨組：`tour_base` 見 §1 `tour_base`；`user_user_level`（同樣有 `使用者編號`、`旅遊等級`…）見 §1 `user_user_level`。
> - **UUID 版本檢查（影響 seed 能否走通 API）**：下列驗證器只接受 `uuid({ version: 'uuidv4' })`（第三段開頭必須是 `4`、第四段開頭必須是 `8`／`9`／`a`／`b`）：`utils/Validator/cart_Validator.js:84`（`tour_id`）、`:92`（`cart_item_id`）、`utils/Validator/checkout_Vaildator.js:4`（`cart_id`）、`:12`（`order_id`）、`:71`（`discount.coupon_id`，`type='coupon'` 時）、`utils/Validator/discounts_Validatior.js:29`（`order_id`）、`utils/Validator/purchases_Validator.js:8`（`order_item_id`）。以 P1b 之前的 seed（來源檔）逐項核對：`tour`（10 筆）與 `coupon`（5 筆）的主鍵全是手寫值，**一筆都不是 v4**；`cart`（6 筆）、`cart_item`（10 筆）、`orders`（5 筆）、`order_item`（10 筆）的主鍵都是 v4。P1b Task 2、3 之後 seed 的所有主鍵都是 v4（`tests/test_seed.py::test_seed_primary_keys_are_v4`）。後果：`POST /api/v1/user/trade/cart/:tour_id` 對任何 seed 行程都在驗證階段回 400，不論星期幾或時段；`PATCH /api/v1/user/checkout/preview/:order_id` 帶 seed 的 `coupon_id` 回 400。`PATCH /api/v1/user/trade/cart/:cart_item_id` 的 `tour_id` 取自 `cart_item`（不經驗證），所以對 seed 既有購物車項目仍可走到各 function。**這一點見 §4.2 (a)，由使用者決定**：改寫 seed 的 `tour`／`coupon` 主鍵為 v4（連同引用它們的外鍵），或放寬這些驗證器（`utils/Validator`，不是 controller，但仍是 P1a 以外的程式碼修改，需使用者同意）。使用者 2026-10-22 決定 A（改寫 seed 主鍵），**2026-10-23 擴大範圍並補列驗證器**：上面的清單不完整，另有 `utils/Validator/product_Validator.js:156`（`tourIDSchema`，公開 `GET /user/product/search/:tour_id`、`/:tour_id/reviews`、`/:tour_id/hidden-shares`，`middlewares/product/index.js:135,165,196`，所以 seed 行程詳情頁全部回 400）、`other_Validator.js:5`（`country_id`，`GET /web/filter/:country_id/region`）、`promotion_Validator.js:7,9`（`tour_ids`）、`coupon_Validator.js:6–20,28,57`（`coupon_ids`、`user_ids`、`user_id`、`coupon_id`）也只接受 v4；來源檔的 `country`（37 筆）主鍵全是手寫值，也不是 v4。改寫範圍因此含 `country` 主鍵與 `region.country_id` 外鍵。注意 `admin_Validator` 接受 v5 而其他不接受，新 id 必須是 v4，不是 uuid5。
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
  | 促銷價錢 | double precision | `tour_base.促銷價錢`（`notification.promo_price`） | `controllers/cart.js:217` | JS 讀取 → response.promo_price（見待確認 2；【定案 #10】僅促銷期間內有值，期間外為 `NULL`） |
  | quantity（英文） | integer | `cart_item.quantity` | `controllers/cart.js:219` | JS 讀取 → response.options.people |
  | start_date（英文） | timestamp | `cart_item.start_date` | `controllers/cart.js:220` | JS 讀取 → response.options.start_date |
  | end_date（英文） | timestamp | `cart_item.end_date`（V1 可 NULL） | `controllers/cart.js:221` | JS 讀取 → response.options.end_date |
  | room_type（英文） | varchar | `cart_item.room_type`（V1 可 NULL） | `controllers/cart.js:222` | JS 讀取 `item.room_type \|\| ''`，`NULL` 會被轉成 `''` |
  | singleTotal_Price（英文，混合大小寫，需雙引號） | double precision（【定案 #12】） | 單一購物車項目的小計（見待確認 1；【定案 #12】有效單價 × `quantity`，促銷期間內用促銷價、否則原價，同 `controllers/cart.js:19–22` 的 CASE） | `controllers/cart.js:224` | JS 讀取 `Number(item.singleTotal_Price)` → response.total_price，並加總成 summary.total_price（`controllers/cart.js:230`） |
  | cart_item_id（英文，【定案 #35】多帶） | uuid | `cart_item.cart_item_id`（V1 `:254`） | 無（controller 不讀） | 為 P4 交易保留；現有 API 的 response 不變 |

  `cart_item_id` 不在 controller 讀取的 key 內（見邊界第 4 點）；【定案 #35】view 多帶 `cart_item_id`。

- **列的語意**：每個購物車項目（`cart_item`）一列，帶入所屬購物車（`cart.user_id`）與行程資料（`tour_base`）。預設排序由 controller 決定（`cart_id ASC`，沒有第二排序鍵）。
- **邊界**：
  - 對 `cart`／`cart_item` 必須是 `INNER JOIN`（`cart_item` 有 `cart_id` NOT NULL，V1 `:254–255`）。對 `tour_base`：若 `tour_base` 不含下架行程（§1 `tour_base` 待確認 1 解讀 B），INNER JOIN 會讓購物車裡已下架的項目消失，LEFT JOIN 則該列的中文欄位為 `NULL`，`Number(NULL)`＝0。【定案 #7】`tour_base` 含全部行程，INNER／LEFT JOIN 結果相同。
  - 欄位名稱混用英文與中文（`user_id`、`cart_id`、`quantity`、`singleTotal_Price` 是英文；`大分類`、`價錢` 等是中文），必須照程式碼拼字，`singleTotal_Price` 有大寫 T 與 P。
  - **controller 行為 1（分頁不穩定）**：`controllers/cart.js:204` 只 `ORDER BY cart_id ASC`。`post_cartItem` 把同一位使用者的項目都放進同一個 `cart_id`（`controllers/cart.js:46–55`），所以同一使用者所有列的排序鍵相同，`LIMIT/OFFSET` 在這種情況下沒有確定順序，翻頁可能重複或漏列。契約只記錄，不處理。
  - **seed 對照（UUID 版本）**：`GET /list` 本身不經 uuid 驗證，但來源檔 seed 行程的 `tour_id` 不是 v4，所以 P1b 之前無法用 `POST /cart/:tour_id` 加入任何 seed 行程（見共通觀察的「UUID 版本檢查」）；P1b Task 2 之後 seed 的 `tour_id` 是 v4，可以加入。seed 既有的 `cart_item` 可由 `GET /list` 讀到。
  - **controller 行為 2（多購物車）**：`controllers/cart.js:15,46` 取使用者的 `cart`（`:15` 查詢，`:46` 讀 `user_cartRepo.rows[0]`），`controllers/cart.js:47–50` 的 `Update public."cart" ... where user_id = $1` 沒有限定 `cart_id`，會更新該使用者的**所有**購物車。V1 的 `cart` 沒有 `user_id` unique 約束，而來源檔 seed 每位使用者有 2 個 `cart`（P1b 之後每位使用者只留 1 個，見 §0.1 第 7 項），所以對 seed 使用者加入購物車會同時改兩個購物車的 `total_price`。這是 controller／seed 的衝突，不是 view 的問題，但 view 會把兩個購物車的項目都列出。
  - **controller 行為 3（總額與小計各自計算）**：`cart.total_price`（`controllers/cart.js:31,49,110–111,164–170`）由 controller 在每次加入／刪除／修改時用「當下的」`price * 人數` 增減，`GET /list` 的 `summary.total_price` 則是各列 `singleTotal_Price` 的加總（`controllers/cart.js:230`），兩者不保證一致（促銷價改變後，刪除項目會用新價格扣舊價格加入的金額）。
  - **controller 行為 4（回傳不含 `cart_item_id`）**：`DELETE`／`PATCH /:cart_item_id` 需要 `cart_item_id`（`routes/cart.js:15,24`），但 `GET /list` 的 response（`controllers/cart.js:209–225`）沒有輸出 `cart_item_id`，即使 view 有這個欄位，前端也拿不到。view 是否提供 `cart_item_id` 無法由程式碼證實（見待確認 3；【定案 #35】view 帶 `cart_item_id`）。
  - `end_date` 為 `NULL` 的項目（V1 允許，`cart_item.end_date` 為 `TIMESTAMP NULL`；seed 有這樣的列：alice 的大阪美食自由行、bob 的高雄夜市美食攻略的購物車項目）會直接輸出 `null`。
- **信心**：欄位名稱：確定（全部由 `controllers/cart.js:208–226` 讀取證實）；來源對應：大部分確定（V1 `cart`、`cart_item` 欄位一一對應）；`singleTotal_Price` 的計算與型別：推測。
- **待確認**：
  1. **`singleTotal_Price` 怎麼算？**（程式碼只讀它，沒有計算） → §4.1 #12（定案：`user_cartList` 的 `singleTotal_Price` ＝ 有效單價 × `quantity`（促銷期間內用促銷價，否則原價，同 `cart.js:19–22` 的 CASE），型別 `double precision`）
     - 解讀 A：`有效單價 × quantity`，有效單價＝促銷期間內用 `促銷價錢`，否則 `價錢`（與 `controllers/cart.js:19–22` 同一個 CASE）。後果：與 `cart.total_price` 的累計邏輯一致；促銷期間外項目自動回到原價。
     - 解讀 B：`價錢 × quantity`（永遠用原價）。後果：有促銷的項目小計大於實際 `cart.total_price` 所加的金額，`summary.total_price` 與 `cart.total_price` 不一致。
     - 解讀 C：`促銷價錢 × quantity`（`NULL` 時退回 `價錢`），不檢查促銷期間。後果：過期促銷的行程仍用促銷價。
     - 型別：若是 `numeric` 或 `bigint`，pg 回字串，所以 `Number(...)`（`controllers/cart.js:224`）是必要的；若是 `double precision` 則 `Number` 無害。controller 用 `Number()` 暗示型別不一定是 number。
  2. **`促銷價錢` 在沒有促銷或促銷已過期時是什麼？**（`controllers/cart.js:217` 原樣輸出 `promo_price`） → §4.1 #10（定案：只在促銷期間內才有值，否則 `NULL`（`通知狀態` 照 #9 不判斷期間））
     - 解讀 A：永遠是 `notification.promo_price` 原值（`tour_base` 的 `促銷價錢`）。後果：過期促銷的項目仍會回傳 `promo_price`，前端要自己判斷期間。
     - 解讀 B：只有在促銷期間內才有值，否則 `NULL`。後果：前端以「有值」判斷是否促銷；方向與 §1 `tour_base` 待確認 4 解讀 B 相同（期間外不視為促銷），但 §1 待確認 4 談的是 `通知狀態`，不是 `促銷價錢`。
  3. **view 是否多帶 `cart_item_id` 等未被讀取的欄位？** 程式碼不讀，不影響現有 API。解讀 A：帶（建議，未來讓前端能刪除項目）。解讀 B：不帶。後果：前端目前拿不到 `cart_item_id`（見邊界第 4 點）的狀況不變。 → §4.1 #35（定案：帶 `cart_item_id`）
  4. **與 `tour_base` 的 JOIN 方式**：見邊界第 1 點。解讀 A：INNER JOIN（下架行程的購物車項目消失）。解讀 B：LEFT JOIN（項目保留，行程欄位為 `NULL`，小計 0）。 → §4.1 #7（定案：`tour_base` 含全部行程，INNER／LEFT JOIN 結果相同，不需選擇）

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
  | 第 1 個 | varchar | `options.room_type`（`hotelSchema` 必填字串，`utils/Validator/cart_Validator.js:16`） | 房型名稱，對應 `hotel_room.title`（seed 例：`設計雙人房`、`豪華家庭房`，`hotel_room.title`）。推測 |
  | 第 2 個 | timestamp | `options.start_date`（ISO 日期字串，`cart_Validator.js:7`） | 入住日期 |
  | 第 3 個 | timestamp | `options.end_date`（ISO 日期字串，`cart_Validator.js:11`，驗證器要求不早於 `start_date`） | 退房日期 |
  | 第 4 個 | uuid | `req.params.tour_id`（post）／`cart_item.tour_id`（patch） | 飯店所屬行程 |

- **輸出欄位**：

  | 欄位 | 型別 | 來源（表.欄位 或計算式） | 讀取位置 | 依據 |
  |---|---|---|---|---|
  | booking_count（英文） | integer（【定案 #25】） | 該房型在指定日期區間內已被預訂的間數（見待確認 1；【定案 #5】數 `payment_status IN (-1, 0, 1)`；【定案 #17】日期區間為半開區間） | `middlewares/cart/index.js:60,195` | JS 讀取 `rows[0].booking_count`，與 `room_count` 比較 |
  | room_count（英文） | integer | `hotel_room.room_count`（該房型總間數） | `middlewares/cart/index.js:61,196` | JS 讀取 `rows[0].room_count` |

  兩個欄位以 `>=` 比較（`middlewares/cart/index.js:62,197`）。若 `booking_count` 是 `bigint`（`COUNT(*)` 的型別），pg 回字串，JS 的 `>=` 會把字串轉成數字，比較結果仍正確。【定案 #25】`booking_count` 採 `integer`（`::int`），pg 回數字。

- **列的語意**：每次呼叫回 0 或 1 列（controller 只讀 `rows[0]`）。1 列表示找得到該 (行程, 房型)，帶出已預訂數與總房數。【定案 #18】恆回 1 列，找不到時為 `0`／`0`。
- **邊界**：
  - **0 列時略過檢查**：`middlewares/cart/index.js:59,194` 用 `booking_room.rowCount > 0` 才比較；找不到房型（例如 `room_type` 拼錯）時 function 回 0 列，controller 視為「有空房」，購物車項目仍會建立。function 的行為因此決定拼錯房型是否被擋：0 列＝放行，1 列且 `booking_count = 0, room_count = 0`＝擋下（`0 >= 0`）。見待確認 3。【定案 #18】找不到 (行程, 房型) 時回 1 列 `booking_count = 0, room_count = 0`，擋下無效房型。
  - `booking_count >= room_count` 時回「選擇的房間已無空房」（HTTP 400）。
  - 此 function 的 `start_date`／`end_date` 區間重疊的判定（含不含退房當日）程式碼沒有證據，見待確認 2。【定案 #17】半開區間 `[start_date, end_date)`，退房日當天可被下一位入住。
  - **seed 對照（UUID 版本）**：`POST /cart/:tour_id` 的 `paramsSchema`（`middlewares/cart/index.js:10`、`cart_Validator.js:84`）要求 `tour_id` 為 uuidv4，來源檔 seed 的行程都不是 v4，所以 P1b 之前 POST 路徑對 seed 行程永遠走不到本 function，只有 PATCH 既有的 seed `cart_item`（`tour_id` 取自 `cart_item`）能呼叫它；P1b Task 2 之後 seed 行程是 v4，POST 也走得到。見共通觀察。
  - PATCH 時（`middlewares/cart/index.js:187`）呼叫端沒有排除「被修改的這個項目自己」，若 function 把購物車內項目也算進 `booking_count`，使用者修改自己已在購物車的項目時會與自己衝突。見待確認 1。
- **信心**：參數順序與輸出欄位名：確定。`booking_count` 的計算方式、參數名稱與型別：推測。
- **待確認**：
  1. **`booking_count` 數什麼？**（程式碼只讀結果） → §4.1 #5（定案：數 `order_item.payment_status IN (-1, 0, 1)`）
     - 解讀 A：數 `order_item` 中同一 (行程, 房型) 且日期區間與參數重疊的列，不看 `payment_status`。後果：連剛建立（-1）、已取消（2）、已退款（3）、付款逾時（4）的訂單都占房間，房間會被放棄的結帳占住。
     - 解讀 B：只數 `payment_status = 1`（已付款）。後果：只有真正付款的才占房；有人下單未付款時，其他人仍可加入購物車（超賣風險）。
     - 解讀 C：數 `payment_status IN (-1, 0, 1)`（排除 2、3、4；各值意義見 B 組共通觀察）。後果：保留未付款的訂單占房，已取消、已退款、逾時的釋放。
     - 解讀 D：數 `payment_status IN (0, 1)`（已填寫完成、已付款）。後果：排除「剛建立、還沒填寫」的訂單。
     - 解讀 E：數 `cart_item`（購物車內項目）而非訂單。後果：占房的是還沒結帳的購物車項目；PATCH 時要自己排除自己，否則修改會與自己衝突。
     - 解讀 F：`order_item` 與 `cart_item` 都數。後果：同一間房可能被同一人重複計算（購物車與已生成訂單各一次）。
  2. **日期區間重疊的判定**： → §4.1 #17（定案：半開區間 `[start_date, end_date)`，退房日當天可被下一位入住）
     - 解讀 A：半開區間 `[start_date, end_date)`，退房日當天可被下一位入住（一般飯店）。後果：同日退房入住不衝突。
     - 解讀 B：閉區間 `[start_date, end_date]`。後果：退房日當天仍算占房，連續住宿無法接續。
     - `order_item.start_date`／`end_date`（V1 `:296–297`）是 `timestamp`，不是 `date`，是否取到日期精度也要定。
  3. **找不到 (行程, 房型) 時回 0 列還是回 0／0？** → §4.1 #18（定案：回 1 列 `booking_count = 0, room_count = 0`（例如 `COALESCE`））
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
  | booking_count（英文） | integer（【定案 #25】） | 該餐廳在該預約時間已預約的人數（見待確認 2；【定案 #15】`order_item.quantity` 加總；【定案 #5】數 `payment_status IN (-1, 0, 1)`） | `middlewares/cart/index.js:78,213` | JS 讀取 `rows[0].booking_count` |
  | reservation_limit（英文） | integer | `restaurant.reservation_limit` | `middlewares/cart/index.js:79,214` | JS 讀取 `rows[0].reservation_limit`（controller 內的變數名 `food_count`） |

  兩者以 `>=` 比較（`middlewares/cart/index.js:80,215`），成立時回「預約已額滿」（HTTP 400）。

- **列的語意**：每次呼叫回 0 或 1 列（controller 只讀 `rows[0]`）；1 列表示找得到該行程的餐廳，帶出已預約數與上限。
- **邊界**：
  - **controller 行為 1（呼叫參數 key 錯誤，已證實）**：`middlewares/cart/index.js:73` 與 `:208` 傳 `options.start_time`，但 food 的驗證器 `foodSchema`（`utils/Validator/cart_Validator.js:22–27`）只有 `start_date`，且 Joi object 預設不允許未知 key，帶 `start_time` 會被 `baseSchema.validate`（`middlewares/cart/index.js:9`）擋下回 400。所以透過 API 呼叫此 function 時，第 1 個參數**恆為 `NULL`**。結果：function 若用第 1 個參數比對預約時間（例如 `WHERE start_date = 參數`），永遠比對不到任何預約，`booking_count` 恆為 0（若回 1 列），額滿檢查等於永遠不會觸發。契約只記錄，不處理（controller 不改）。【定案 #16】function 忽略參數 1，只以行程計算總預約數對 `reservation_limit`；簽章保留參數 1。
  - `middlewares/cart/index.js:77,212` 用 `booking_food.rowCount > 0` 才比較，0 列時略過檢查。
  - **seed 對照（UUID 版本）**：`POST` 路徑對來源檔 seed 行程在驗證階段就回 400（`cart_Validator.js:84`），P1b 之前走不到本 function，只有 PATCH 既有 seed `cart_item` 能呼叫；P1b Task 2 之後 seed 行程是 v4，POST 也走得到。見共通觀察。
  - 此 function 不檢查營業時間，營業時間由 `restaurant_business_parsed`（`middlewares/cart/index.js:91`）與 `restaurant_isClosed`（`middlewares/cart/index.js:105`）處理。
  - 加入購物車的 food 項目只存 `start_date`（`controllers/cart.js:40`），`quantity`（人數）也在 `cart_item`；`booking_count` 是否以人數加總見待確認 2（【定案 #15】以人數加總）。
- **信心**：參數順序與輸出欄位名：確定。參數 1 的實際內容（恆 `NULL`）：確定（驗證器與 controller 的 key 對照）。計算方式、型別：推測。
- **待確認**：
  1. **參數 1 恆為 `NULL` 時，function 要怎麼處理？** → §4.1 #16（定案：忽略參數 1，只以行程計算總預約數對 `reservation_limit`；簽章保留參數 1，P4 修好 controller 後再改成時段比對）
     - 解讀 A：function 忽略參數 1，只以行程計算總預約數 vs. `reservation_limit`。後果：整個行程累計預約人數到上限就額滿，不分時段；與「預約時間」的語意不符，但有作用。
     - 解讀 B：function 以參數 1 比對時段（程式碼原意）。後果：參數恆為 `NULL`，永遠比對不到，額滿檢查形同虛設；要讓它有效必須改 controller 讀 `options.start_date`。
     - 解讀 C：function 在參數為 `NULL` 時回 0 列。後果：略過檢查（`rowCount > 0`），同 B 的結果。
  2. **`booking_count` 數什麼？** → §4.1 #5、#15（定案：#5：數 `order_item.payment_status IN (-1, 0, 1)`；#15：`order_item.quantity` 加總（人數））
     - 解讀 A：`order_item` 中該行程（`tour.item='food'`）的筆數，不看 `payment_status`。後果：已取消、已退款、逾時的訂單也占名額。
     - 解讀 B：`order_item.quantity` 加總（以人數計），與 `reservation_limit`（`restaurant.reservation_limit`，V1 `:129`，來源檔 seed 為 50、30；P1b 另加 3 家，各 40）同單位。後果：符合「人數限制」的語意（§1 `tour_restaurant` 把 `reservation_limit` 輸出成 `餐廳人員限制`，`response.feature.about.people`）。
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
  | isclosed（英文，**必須全小寫**） | boolean | 該時間點是否休息（見待確認 1；【定案 #19】只看 `restaurant_business` 有無對應星期的列，預約時間為 `NULL` 或餐廳不存在時為 `false`） | `middlewares/cart/index.js:110,245` | JS 讀取 `food_closed.rows[0].isclosed === true`，嚴格比較 `true` |

- **列的語意**：每次呼叫**必須回 1 列**。為 `true` 時回「此時段無營業」（HTTP 400，`middlewares/cart/index.js:111–115`）。
- **邊界**：
  - **controller 行為（0 列則 500）**：`middlewares/cart/index.js:110,245` 直接讀 `food_closed.rows[0].isclosed`，沒有 `rowCount` 檢查；function 若回 0 列，`rows[0]` 是 `undefined`，丟 TypeError，API 回 500。所以 function 在任何情況（包含找不到餐廳）都要回 1 列。
  - **欄位名稱大小寫**：pg 以欄位名的實際拼法當 key。程式碼讀 `isclosed`（小寫），function 的 `RETURNS TABLE` 欄位若寫成 `"isClosed"`（有引號）或 `isClosed`（無引號會折成小寫，OK），前者會讓 `rows[0].isclosed` 為 `undefined`，檢查永遠不成立。
  - **seed 對照（UUID 版本）**：`POST` 路徑對來源檔 seed 行程在驗證階段就回 400（`cart_Validator.js:84`），P1b 之前走不到本 function，只有 PATCH 既有 seed `cart_item` 能呼叫；P1b Task 2 之後 seed 行程是 v4，POST 也走得到。見共通觀察。
  - 呼叫順序：同一請求先過 `restaurant_business_parsed`（`middlewares/cart/index.js:90–102`，不在營業時段就回「餐廳已關閉」），通過後才呼叫本 function；所以在營業時段內才可能走到這裡。V1／V2 沒有任何「公休日」「特殊休息日」的表（grep `closed|holiday|休` 在 `backend/migrations/` 沒有結果），本 function 能依據的資料只有 `restaurant_business` 與 `restaurant`。
- **信心**：參數順序、輸出欄位名與型別：確定。「休息」的判定方式：推測（見待確認）。
- **待確認**：
  1. **`isclosed` 依什麼判斷？**（V1 沒有公休日表） → §4.1 #19（定案：判斷依據只看 `restaurant_business` 有沒有對應星期的列，沒有＝公休）
     - 解讀 A：只看 `restaurant_business` 是否有對應星期（`week`）的列；沒有該星期的營業列＝公休。後果：與 `restaurant_business_parsed` 有部分重複（`parsed` 已過濾時段，但 `week` 缺列在 `parsed` 也會得到 0 列而先被擋下），本 function 在實務上永遠回 `false`。
     - 解讀 B：看 `restaurant_business.business_hours` 時段，判斷預約時間是否落在任一時段之外。後果：與 `parsed` 的判斷幾乎重複，通過 `parsed` 的請求必然 `false`。
     - 解讀 C：另外依某個尚未存在的公休日／特殊日資料（需要新增表，超出「V3 只建 view／function」的範圍）。後果：需要另外的 migration；沒有該表之前 function 無法實作。
     - 解讀 D：永遠回 `false`（占位）。後果：「此時段無營業」永遠不會觸發；其餘功能不受影響。
  2. **預約時間為 `NULL` 或餐廳不存在時**：解讀 A：回 1 列 `isclosed = false`（放行）。解讀 B：回 1 列 `isclosed = true`（擋下）。後果：A 讓不存在的 `tour_id` 也可加入購物車（`middlewares/cart/index.js:26` 已先確認 `tour` 存在，但不確認它有 `restaurant` 列）；B 擋下。丟例外則 API 回 500。 → §4.1 #19（定案：預約時間為 `NULL` 或餐廳不存在時回 1 列 `isclosed = false`）

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
  | week（英文） | varchar | `restaurant_business.week` | `middlewares/cart/index.js:93,228` | WHERE `week = TRIM(TO_CHAR(..., 'FMDay'))`，右邊是英文全名（`Monday`…），seed 的 `week` 即 `Monday`…`Sunday` |
  | start_time（英文） | time | 由 `restaurant_business.business_hours` 的一個時段拆出的開始時間 | `middlewares/cart/index.js:92,227` | WHERE `$2::timestamp::time BETWEEN start_time AND end_time`，左邊是 `time` |
  | end_time（英文） | time | 同上的結束時間 | `middlewares/cart/index.js:92,227` | 同上 |

- **列的語意**：**每個 (餐廳, 星期, 營業時段) 一列**。`restaurant_business.business_hours` 是 TEXT，格式範例見 V1 `:145` 註解與 seed：`'11:00~14:00, 17:00~21:00'`（多時段）、`'17:00~23:00'`（單時段）（seed 的 `restaurant_business`）。view 要把它拆成每個時段一列、轉成 `time`。controller 只用 `rowCount === 0` 判斷「餐廳已關閉」（`middlewares/cart/index.js:96,231`）。
- **邊界**：
  - 時段分隔用 `, `（逗號加空白），起訖用 `~`，格式來自 seed 與 V1 註解；程式碼本身沒有解析 `business_hours` 的位置。
  - `BETWEEN start_time AND end_time` 是閉區間，且不處理跨午夜。seed 有 `'17:00~00:00'`（行程「高雄夜市美食攻略」的星期五、星期六）。若 `end_time` 解析成 `00:00:00`，則 `start_time > end_time`，`BETWEEN` 永遠不成立，這兩天**所有**時間都會回「餐廳已關閉」。此判斷只在請求通過 uuid 驗證後才會執行；seed 行程用 POST 加入購物車在驗證階段就被擋下（見共通觀察），所以 seed 環境下實際走到本 view 的只有 PATCH 既有 `cart_item`。見待確認 2。【定案 #20】`00:00` 視為 `24:00`，`end_time = 23:59:59`，所以週五、週六 17:00 到 23:59:59 可預約。
  - `week` 的比對是區分大小寫的字串比對：`TO_CHAR(..., 'FMDay')` 回 `Monday` 這種首字大寫的英文名（`FM` 去掉補的空白，`TRIM` 是多餘但無害）。PostgreSQL 只有加 `TM` 前綴（`TMDay`）才會依 `lc_time` 翻譯星期名，`FMDay` 不加 `TM`，不受 `lc_time` 影響，所以這裡沒有環境依賴。
  - `options.start_date` 是帶時區的 ISO 字串時，`$2::timestamp` 會丟掉時區（以字串的牆上時間為準），所以時段以「使用者送出的牆上時間」判斷。
- **信心**：欄位名稱與型別：確定（SQL 字串直接使用）。拆解 `business_hours` 的細節（分隔符、跨午夜）：推測，依據 seed 與 V1 註解。
- **待確認**：
  1. **`business_hours` 無法解析（格式不符）的列怎麼辦？** → §4.1 #21（定案：view 忽略無法解析的列）
     - 解讀 A：view 忽略該列（不輸出）。後果：該餐廳該星期視為「已關閉」。
     - 解讀 B：view 解析失敗時丟例外。後果：整個 view 查詢失敗，所有餐廳的加入購物車都回 500。
  2. **跨午夜時段（seed 的 `17:00~00:00`）**： → §4.1 #20（定案：`00:00` 視為 `24:00`，轉成 `end_time = 23:59:59`）
     - 解讀 A：`00:00` 視為 `24:00`，轉成 `end_time = 23:59:59`。後果：星期五、星期六 17:00 到 23:59:59 可預約，`00:00` 之後不可。
     - 解讀 B：保持 `00:00:00`（原樣）。後果：這兩天任何預約都回「餐廳已關閉」（seed 的「高雄夜市美食攻略」：PATCH bob 購物車裡既有的該項目時，週五六的預約會被擋下；用 POST 加入該行程則不論星期幾都先被 uuidv4 驗證擋下，與本題無關，見共通觀察）。
     - 解讀 C：拆成兩列（`17:00~23:59:59` 與隔日的 `00:00~00:00`）。後果：需要把隔日時段記在下一個 `week`，view 較複雜。
  3. **沒有 `restaurant` 列的行程**：這類行程在 view 內沒有列，`rowCount === 0`，回「餐廳已關閉」（HTTP 400）。INNER JOIN 與 LEFT JOIN（時段為 `NULL`）在這個查詢下結果相同，因為 `NULL` 比不到 `BETWEEN`。契約不要求特別處理，只記錄這個行為。 → §4.1 #21（定案：沒有 `restaurant` 列的行程不需選擇，只記錄；無法解析的列由 view 忽略）

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
  | discount（英文） | double precision | `coupon.discount`（V1 `:58`，`FLOAT`） | `controllers/discounts.js:32,38`、`controllers/checkout.js:155` | JS 讀取，**乘上 `orders.total_price`**（見待確認 1）；【定案 #1】`coupon.discount` ＝ 折抵金額（NT$），view 原值輸出；正確計算是 `total_price - discount`，現行乘法不符（見邊界 controller 行為 5） |
  | description（英文） | text | `coupon.description` | `controllers/discounts.js:33` | JS 讀取 → response.discount.description |
  | expire_date（英文） | timestamp | `coupon.expire_date`（V1 `:60`） | `middlewares/discounts/index.js:65`、`middlewares/checkout/index.js:136` | JS 讀取 `new Date(rows[0].expire_date)`，與現在時間比較 |
  | expired_date（英文，**多了 d**） | timestamp | `coupon.expire_date`（同一個值） | `controllers/discounts.js:34` | JS 讀取 → response.discount.date_period（見邊界與待確認 2；【定案 #36】view 同時提供 `expire_date` 與 `expired_date`，同值） |
  | status（英文） | smallint | `user_coupon.status` | `middlewares/discounts/index.js:54`、`middlewares/checkout/index.js:125`、`controllers/checkout.js:216` | JS 讀取 `status === 1`；WHERE `status = -1` |
  | order_id（英文） | uuid | `user_coupon.order_id`（V1 可 NULL） | `controllers/checkout.js:216` | WHERE `order_id = $2` |

  `user_coupon` 沒有被 controller 直接讀的欄位（`user_coupon_id`、`created_at`、`updated_at` 等）是否也在 view 內，只有管理者 API（`controllers/admin.js:239`）會因為 `SELECT *` 而輸出，程式碼無法證實。

- **列的語意**：每個「使用者與優惠卷的綁定」（`user_coupon`）一列，帶入優惠卷內容（`coupon`）。**不過濾** `status`、也不過濾過期：
  - `middlewares/discounts/index.js:54`（回「優惠券已使用」409）與 `:65`（回「優惠券已過期」409）是在**取到列之後**才判斷；若 view 先濾掉已使用或已過期，這兩個分支永遠走不到，使用者只會看到「查無此優惠卷」404。
  - `controllers/checkout.js:216` 要取到 `status = -1` 的列，所以 `status` 為 -1 的也要在 view 內。【定案 #37】`status` 原樣輸出，包含 -1。
- **邊界**：
  - **controller 行為 1（`expired_date` 與 `expire_date` 兩種拼法）**：`middlewares/discounts/index.js:65` 與 `middlewares/checkout/index.js:136` 讀 `expire_date`，但 `controllers/discounts.js:34` 讀 `expired_date`。V1 `coupon` 欄位是 `expire_date`。view 只有 `expire_date` 時，`controllers/discounts.js:34` 取到 `undefined`，`date_period` 欄位在 JSON 裡不會出現（`JSON.stringify` 略過 `undefined`），不會報錯；view 只有 `expired_date` 時，`new Date(undefined)` 是 `Invalid Date`，`now > Invalid Date` 為 `false`，**過期檢查被靜默略過**（過期的優惠卷可以使用）。契約要求至少提供 `expire_date`；是否同時提供 `expired_date` 見待確認 2。【定案 #36】同時提供，同值。
  - **controller 行為 2（-1 被當成「可再使用」）**：`controllers/checkout.js:148–151` 在 PATCH 預覽時把 `user_coupon.status` 設成 -1（V1 `:414` 註解只有 1／0），`middlewares/checkout/index.js:125` 與 `middlewares/discounts/index.js:54` 只擋 `status === 1`。**全 `backend/src` 沒有任何地方把 `status` 設成 1**（grep `user_coupon` 只有 `controllers/checkout.js:149`、`controllers/coupon.js:209`（新增綁定，`status` 寫 0）、`controllers/admin.js:271`（刪除綁定）、`middlewares/coupon/index.js:260,290`、`middlewares/admin/index.js:384`（只讀）），付款成功的 `newebpay.js` 也沒有。所以 seed 以外，status 永遠不會成為 1，-1 的優惠卷可以被重複套用到另一張訂單（`controllers/checkout.js:149` 會把 `order_id` 覆蓋成新訂單）。
  - **controller 行為 3（`code` 不是 unique）**：V1 `coupon.code` 沒有 unique 約束，`middlewares/discounts/index.js:41` 與 `controllers/discounts.js:14` 以 `code` + `user_id` 查詢並取 `rows[0]`；同一使用者綁定兩張 `code` 相同的優惠卷時，取到哪張不固定。【定案 #38】view 不處理，維持每個 `user_coupon` 一列，根本修正見 §4.2 (d4)。
  - **controller 行為 4（驗證器與 seed 的 `code` 不相容）**：`utils/Validator/discounts_Validatior.js:9–13` 要求 `discount.coupon` 符合 `^[A-Z0-9]{6}$`（剛好 6 碼大寫英數），而來源檔 seed 的 5 個優惠卷代碼只有 `VIP300`（6 碼）符合（P1b 之後 seed 的代碼已改成 `WEL100`、`SUM050`、`TRV010`、`VIP300`、`SPR020`，全部符合），`WELCOME100`（10）、`SUMMER50`（8）、`TRAVEL10P`（9）、`SPRING20`（8）都會被 `POST /api/v1/user/trade/discounts/:order_id` 以 400 擋下（`type='coupon'` 路徑）。`PATCH /preview/:order_id` 雖然用 `coupon_id` 而非 `code`，但 `utils/Validator/checkout_Vaildator.js:71` 要求 `discount.coupon_id` 是 `uuid({ version: 'uuidv4' })`，來源檔 seed 的 5 個 `coupon_id`（手寫值）第三段都不是 `4` 開頭（P1b 之後已改成 v4），同樣會被 400 擋下（見共通觀察的「UUID 版本檢查」）。
  - **controller 行為 5（`discount` 的運算）**：`controllers/discounts.js:38` 與 `controllers/checkout.js:155` 都是 `orders.total_price * coupon.discount`，結果寫入／輸出為 `discount_price`（見待確認 1）。【定案 #1】`coupon.discount` ＝ 折抵金額（NT$），正確計算是 `total_price - discount`，`orders.discount_price` 為折後應付金額（與點數路徑 `checkout.js:165` 同語意）。**現行 controller 不符合定案**：兩處的 `total_price * discount` 在金額語意下會算出數百倍金額（例：`total_price` 3576.74 × `discount` 100.0 → 357,674），要改成 `total_price - discount`，屬 P4 結帳；P4 修好之前優惠卷結帳金額是錯的。V3 view 照金額語意輸出原值，不為了配合乘法而轉換數值。
  - 狀態以 JS 的 `=== 1` 比較，所以 `status` 必須是 `smallint`／`integer`，不能是 `bigint`／`numeric`／字串（pg 會回字串，嚴格比較失敗，已使用的優惠卷會被當成未使用）。
  - **seed 對照（UUID 版本）**：`PATCH /preview/:order_id` 的 `coupon_id` 要求 uuidv4（`checkout_Vaildator.js:71`），來源檔 seed 的 5 個 `coupon_id` 都不是 v4，所以 P1b 之前 seed 優惠卷走不到 `controllers/checkout.js:144` 與 `middlewares/checkout/index.js:112` 這兩處查詢（P1b Task 2 之後 `coupon_id` 是 v4，走得到）；`POST /discounts/:order_id` 以 `code` 查詢（`middlewares/discounts/index.js:41`），seed 訂單 `order_id` 是 v4 可通過，但 `code` 受 `^[A-Z0-9]{6}$` 限制（上一點）。
  - 與 `user_level_point_coupon` 的 `優惠卷折扣`（見該物件）是同一個 `coupon.discount`，兩邊語意要一致。【定案 #1】兩邊都是折抵金額（NT$）。
  - `status` 完整可能值（程式碼與 seed 實際出現）：`0` 未使用（`controllers/coupon.js:209`、seed 的 carol `TRV010` 綁定）、`1` 已使用（seed 的其他 3 筆；程式碼只讀不寫）、`-1` 預覽中占用（只由 `controllers/checkout.js:149` 寫入）。
- **信心**：欄位名稱：確定（全部由程式碼讀取證實）；來源對應：確定（V1 `coupon`、`user_coupon` 欄位一一對應）；`expired_date` 是否存在：推測；`status` 篩選：確定（不篩選）。
- **待確認**：
  1. **（spec 3.1 已知問題 2）`coupon.discount` 是折扣倍率還是折抵金額？** → §4.1 #1（定案：`coupon.discount` ＝ 折抵金額（NT$），`discount_price` ＝ `total_price - discount`（折後應付金額）；view 原值輸出；現行 `total_price * discount` 兩處要改，屬 P4）
     - **程式碼對它做的運算（所有位置）**：
       - `controllers/discounts.js:38`（`POST /user/trade/discounts/:order_id`，回傳 response）：`discount_price: orderRepo.rows[0].total_price * couponRepo.rows[0].discount`。
       - `controllers/checkout.js:155`（`PATCH /user/checkout/preview/:order_id`，**寫入 `orders.discount_price`**）：`UPDATE public."orders" SET discount_price = $1 ...`，參數 `orderRepo.rows[0].total_price * couponRepo.rows[0].discount`。
       - `controllers/discounts.js:32`、`controllers/userProfile.js:156`：原樣輸出 `discount`（沒有運算）。
       - 沒有任何地方做 `total_price - discount`、`discount / 100` 或 `1 - discount`。
     - **寫入位置（`coupon.discount` 怎麼進來）**：
       - `controllers/coupon.js:6`（解構 `req.body.discount_amount`）、`:10–12`（`INSERT INTO public.coupon (code, discount, description, expire_date) VALUES ($1, $2, $3, $4)`，`$2` ＝ `discount_amount`）：`POST /api/v1/admin/coupons`。
       - `controllers/coupon.js:103`（解構 `req.body.discount_amount`）、`:107–108`（`update coupon set code = $1,discount = $2,description = $3,expire_date = $4 where coupon_id = $5`，`$2` ＝ `discount_amount`）：`PATCH /api/v1/admin/coupons/update/:coupon_id`。
       - 驗證器 `utils/Validator/coupon_Validator.js:45`：`discount_amount: Joi.number().greater(0)`，錯誤訊息是「優惠折扣數」，**沒有上限**（沒有 `.max(...)`）。【定案 #1】折抵金額語意下 `> 0` 無上限與金額相容；是否加上限（例如不得超過訂單金額）只是 P4／P6 的觀察，不是決定。
       - 管理者端的請求欄位叫 `discount_amount`（字面是「折扣金額」），但訊息文字叫「優惠折扣數」；欄位名與訊息各自偏向不同解讀，不能由此決定。
       - `grep '\.discount'` 在這兩個 controller 的其他命中行都不是對 `coupon.discount` 的運算：`controllers/discounts.js:99`、`controllers/checkout.js:188,265` 只是輸出 `orders.discount_price`；`controllers/checkout.js:124` 是解構 `req.body.discount`；`controllers/checkout.js:240` 讀 `orders.discount_type`。
     - **seed 裡實際的值**（`coupon.discount` 欄位；下表「舊 `code`」是來源檔的寫法，P1b 之後的代碼見 §0.1 第 2 項）：

       | code | `discount` | `description` | 位置 |
       |---|---|---|---|
       | `WELCOME100` | `100.0` | 首次註冊禮，折抵新台幣 100 元 | 來源檔 |
       | `SUMMER50` | `50.0` | 夏日旅遊季，折抵新台幣 50 元 | 來源檔 |
       | `TRAVEL10P` | `10.0` | 旅遊商品 10% 折扣 (最高折抵 500 元) | 來源檔 |
       | `VIP300` | `300.0` | 尊榮會員專屬，折抵新台幣 300 元 | 來源檔 |
       | `SPRING20` | `20.0` | 春季限定，旅遊折抵新台幣 20 元 | 來源檔 |

       五個值都 > 1。以 `total_price * discount` 計算：`total_price` 3576.74、`discount` 100.0 → `discount_price` 357,674。沒有任何一個 seed 值落在 0 到 1 之間。
     - **【定案 #1 對 seed 的影響】**：`coupon.discount` 的 5 個值（100、50、10、300、20）保留不改；但 `TRAVEL10P` 的 `description`「10% 折扣 (最高折抵 500 元)」與折抵金額語意矛盾（`10.0` 只折 10 元），P1b 要改它的 `description` 讓兩者一致（若改成改數值，要同步更新本契約）。代碼本身依 §4.2 (d2) 本來就要改。
     - **相關事實**：`orders.discount_price`（V1 `:279`，`FLOAT NULL`）在 `controllers/checkout.js:155`（優惠卷）與 `controllers/checkout.js:165`（點數：`total_price - used_point * 0.8`，見 `user_level_point_coupon` 待確認 1）寫入的都是同一欄；後者的運算形式（`total_price - ...`）算出來的是「折扣後應付金額」。來源檔 seed 的 `orders.discount_price`（例如 `total_price` 3576.74 對 `discount_price` 794.83）都小於 `total_price`，看起來像「折掉的金額」，與程式碼寫入的「應付金額」語意不同；`discount_type` 在來源檔 seed 是 `'none'`、`'earlybird'`（P1b 之後只有 `none`、`coupon`、`point` 與 `NULL`），程式碼只寫 `'coupon'`／`'point'`，或在 `type` 省略時寫 `NULL`（`checkout_Vaildator.js:64–67` 的 `discount` 與 `type` 都是 `.optional()`；`controllers/checkout.js:133–134`）。這些只是觀察，不能由此決定 `coupon.discount` 的語意。
     - 解讀 A：**折扣倍率**（`discount` 在 0 到 1，例如 `0.9` 表示九折，`discount_price` 為折扣後應付金額）。後果：結帳計算（`discounts.js:38`、`checkout.js:155`）不用改，與 `controllers/checkout.js:165` 的「`discount_price` 是折扣後應付金額」一致；但 admin 寫入端的驗證器（`coupon_Validator.js:45`）只要求 `> 0`、沒有上限，管理者仍可建立 `discount = 100` 的優惠卷，結帳照樣算出數百倍金額，要擋住需另外給驗證器加 `.max(1)`；請求欄位名 `discount_amount` 也與倍率語意不符。另外 seed 的 5 個值（100.0、50.0、10.0、300.0、20.0）全部要改成倍率（例如 `0.9`），`description` 的「折抵新台幣 100 元」也要改；P1b 的 seed 要跟著動。
     - 解讀 B：**折抵金額**（NT$，與 seed 的 `description` 文字一致：100、50、300、20）。後果：seed 不用改，admin 寫入端的 `discount_amount > 0` 且無上限（`coupon_Validator.js:45`）與金額語意相容、欄位名也一致；但 `controllers/discounts.js:38` 與 `controllers/checkout.js:155` 的 `total_price * discount` 算出來是金額的幾百倍（上例 357,674），需要改 controller 為 `total_price - discount`，違反「controller 不改」；若不改，結帳會寫入錯誤的 `orders.discount_price`。`TRAVEL10P` 的 `10.0` 在此解讀下只折抵 10 元，與其 `description`「10% 折扣 (最高折抵 500 元)」矛盾。
     - 解讀 C：**混合**（`TRAVEL10P` 是百分比 `10` ＝ 10%，其餘是金額）。後果：與 seed 的 `description` 全部吻合，但同一欄位兩種語意，程式碼的 `total_price * discount` 兩種都算錯；要靠 `description` 或新增欄位區分類型（V1 沒有類型欄位，需改 migration）；admin 寫入端的驗證器（`coupon_Validator.js:45`）只檢查 `> 0`，無法區分百分比與金額。
     - 解讀 D：**折扣百分比**（`discount` 是 0–100，`10` ＝ 打 9 折）。後果：seed 的 5 個值都需要改成 0–100 以內的百分比（100 以上沒有意義）；程式碼要改成 `total_price * (1 - discount / 100)`；admin 驗證器（`coupon_Validator.js:45`）無上限，需補 `.max(100)`。
  2. **`expired_date`（`controllers/discounts.js:34`）要不要提供？** → §4.1 #36（定案：兩個都提供（`expire_date` 與 `expired_date`，同值））
     - 解讀 A：只提供 `expire_date`。後果：`POST /user/trade/discounts/:order_id` 的 response 少了 `date_period`，前端若依賴它會顯示空白。
     - 解讀 B：`expire_date` 與 `expired_date` 兩個都提供（同值）。後果：response 有 `date_period`，admin API（`SELECT *`）會多一個重複欄位。
  3. **`status = -1` 的列要不要出現在管理者 API 與其他查詢中？** → §4.1 #37（定案：原樣輸出 `status = -1`）
     - 解讀 A：全部出現（如目前所推）。後果：管理者看到 -1。
     - 解讀 B：view 把 -1 換算成別的顯示值。後果：`controllers/checkout.js:216` 的 `status = -1` 失效，結帳摘要看不到已套用的優惠卷。
  4. **同一個 (使用者, `code`) 有多筆時**：V1 有 `UNIQUE (user_id, coupon_id)`（V1 `:420`）但 `code` 不 unique。解讀 A：不處理。後果：取 `rows[0]` 不固定。解讀 B：view 只取最新一筆。後果：需另定規則。 → §4.1 #38（定案：不處理，view 維持每個 `user_coupon` 一列；重複 `code` 的根源見 §4.2 (d4)）

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
  | 使用者旅遊積分 | integer | 見待確認 1（`user_level.travel_point` 或 `point_record` 加總）；【定案 #2】`user_level.travel_point`，預扣不反映，型別 `integer` | `controllers/userProfile.js:148`、`controllers/discounts.js:60,62`、`middlewares/discounts/index.js:89`、`middlewares/checkout/index.js:160` | JS 讀取，做 `<`、`-` 運算；response.travel_point／user_point |
  | 優惠卷編號 | uuid | `coupon.coupon_id` | `controllers/userProfile.js:154` | JS 讀取 → response.coupon[].coupon_id |
  | 優惠卷代碼 | varchar | `coupon.code` | `controllers/userProfile.js:155` | JS 讀取 → response.coupon[].code |
  | 優惠卷折扣 | double precision | `coupon.discount` | `controllers/userProfile.js:156` | JS 讀取 → response.coupon[].discount（語意見 `user_couponList` 待確認 1；【定案 #1】折抵金額（NT$），view 原值輸出） |
  | 優惠卷描述 | text | `coupon.description` | `controllers/userProfile.js:157` | JS 讀取 → response.coupon[].description |
  | 優惠卷期限 | timestamp | `coupon.expire_date` | `controllers/userProfile.js:158` | JS 讀取 → response.coupon[].expire_date |

  `使用者旅遊積分` 在 `middlewares/discounts/index.js:89`、`middlewares/checkout/index.js:160` 以 `<` 與 `used_point`／`point` 比較，在 `controllers/discounts.js:62` 做減法；若是 `bigint`／`numeric`（例如 `SUM(...)` 的結果），pg 回字串，`<` 與 `-` 會自動轉成數字不會出錯，但輸出到 response 時（`controllers/discounts.js:60`、`controllers/userProfile.js:148`）會變成 JSON 字串，與 `integer` 時的數字不同。【定案 #2、#25】`使用者旅遊積分` ＝ `user_level.travel_point`（`integer`），不經 `SUM`，response 是數字。

- **列的語意**：**每位使用者的每張優惠卷一列**（使用者與會員等級的資料在每一列重複）。依據：`controllers/userProfile.js:133–160` 以 `使用者編號` 分組，第一次出現時建立使用者物件，每一列再 `push` 一張優惠卷。【定案 #39、#40】只列 `status = 0` 且未過期的優惠卷；對優惠卷採 `LEFT JOIN`，沒有可用優惠卷的使用者仍保留 1 列、優惠卷欄位全為 `NULL`。
- **邊界**：
  - **沒有優惠卷的使用者（關鍵；【定案 #40】採 `LEFT JOIN`）**：
    - 若 view 對優惠卷用 `LEFT JOIN`：使用者得到 1 列，優惠卷欄位全為 `NULL`；`controllers/userProfile.js:153–159` 沒有檢查，會 `push` 一個全為 `null` 的優惠卷物件，response 的 `coupon` 是 `[{coupon_id: null, code: null, ...}]`。
    - 若用 `INNER JOIN`：沒有優惠卷的使用者在 view 內完全沒有列，`GET /pointslevel` 回 `[]`（`controllers/userProfile.js:162`），而且 `middlewares/discounts/index.js:81–89` 與 `middlewares/checkout/index.js:152–160` 的 `pointRepo.rowCount === 0` 會回 409「查無可使用的點數」，**即使使用者有積分也無法使用點數折抵**。
  - 沒有 `user_level` 列的使用者：INNER JOIN 時同樣消失（理由同 §1 `user_user_level` 待確認 1）。【定案 #22】對 `user_level` 採 `LEFT JOIN`，有多筆時取最新一筆。
  - controller 在 `controllers/discounts.js:60,62` 與兩個 middleware 都只讀 `pointRepo.rows[0].使用者旅遊積分`，所以每一列的 `使用者旅遊積分` 必須相同（同一個使用者的值不隨優惠卷變動）。【定案 #2】值取自 `user_level.travel_point`，不隨優惠卷列變動。
  - 欄位名稱必須照程式碼拼字：`個人偏好 1`（有空格，與 §1 `tour_base` 的 `偏好分類1` 不同）、`個人照片 Url`、`旅遊徽章 Url`；`優惠卷` 用「卷」不是「券」（與 `優惠券已使用` 的訊息用字不同）。
  - 是否包含已使用／已過期的優惠卷：見待確認 3（【定案 #39】不包含，只列 `status = 0` 且未過期）。
- **信心**：欄位名稱：確定（全部由 `controllers/userProfile.js:137–158` 與其他三處的 `使用者編號`、`使用者旅遊積分` 證實）；來源對應：除 `使用者旅遊積分` 外為確定。`使用者旅遊積分` 的來源：推測（見待確認 1）。
- **待確認**：
  1. **（spec 3.1 已知問題 1）點數的累積和扣抵規則，以及 `point * 0.8` 的意義。** → §4.1 #2、#3（定案：#2：`使用者旅遊積分` ＝ `user_level.travel_point`，預扣不反映，型別 `integer`；#3：1 點折抵 0.8 元，累積 0.1 一併視為設計值）

     **a. 點數存在哪個欄位？** V1 有兩個地方：`user_level.travel_point`（INT NULL，V1 `:45`）與 `point_record.point`（INT NOT NULL，V1 `:399`，每筆異動一列，`type` 為 VARCHAR(50) NOT NULL，V1 沒有註解 `type` 可有哪些值）。點數餘額有**兩條讀取路徑**：(1) 本 view 的 `使用者旅遊積分`（`GET /api/v1/user/userinfo/pointslevel`、折抵驗證、折抵 response）；(2) `controllers/userinfo.js:57`（註冊 response）、`:123`（email 登入）、`:249`（Google 登入）、`:379`（`GET /api/v1/auth/userinfo/login/status`）直接輸出 `user_level.travel_point` 為 `level.points`，不經過 view。所以 view 取哪一個欄位，會決定兩條路徑顯示的餘額是否一致：
     - 解讀 A：`user_level.travel_point`。後果：餘額只與 `user_level` 有關，`point_record` 是流水帳但不影響餘額；而**全 `backend/src` 沒有任何 UPDATE `travel_point`**（下表），所以餘額在註冊後永遠是 0（`userinfo.js:31,209` 寫 0），除了 seed 手動設的 1500／3000／800。與 `userinfo.js` 四處的 `level.points` 一致（同一欄位）。
     - 解讀 B：`SUM(point_record.point)`（全部類型）。後果：`'減少_確認中'`（`controllers/checkout.js:160` 寫入）立即從餘額扣掉，使用者在預覽後馬上看到餘額減少；同一個預覽重複 PATCH 會重複扣（見下表第 5 項）。與 `userinfo.js` 四處的 `level.points`（讀 `travel_point`）**不一致**：預覽後 `pointslevel` 與折抵檢查的餘額減少，登入／登入狀態 response 的 `points` 不變。
     - 解讀 C：`SUM(point_record.point)` 但排除 `'減少_確認中'`。後果：預覽階段不影響餘額；但付款確認後沒有任何程式把 `'減少_確認中'` 轉成 `'減少'`（見下表），所以餘額永遠不會因為使用點數而減少。餘額與 `userinfo.js` 四處的 `level.points` 在 `point_record` 加總不等於 `travel_point` 時（seed 使用者 `c3d4...` 即是）**不一致**。
     - 解讀 D：`user_level.travel_point` 加上 `SUM(point_record.point WHERE type = '減少_確認中')`（即餘額扣掉預扣）。後果：預扣即時生效，但付款完成前沒有人把 `travel_point` 真正扣掉；`pointslevel`／折抵檢查看到的餘額（扣掉預扣）與 `userinfo.js` 四處的 `level.points`（未扣預扣的 `travel_point`）**不一致**。
     - **seed 與兩個來源不一致的實例**：來源檔 seed 的使用者 `carol@example.com` 的 `travel_point` 是 800，但 `point_record` 有 `'新增' 1610` 與 `'減少' -436`，加總 1174（P1b 之後 seed 的 `point_record` 已重建，見 §0.1 第 10 項：`travel_point` 仍是 800，`point_record` 加總是 +10% 與 −折抵點數，兩者不相等，#2 定案 A 不加總）。`pointslevel` 與折抵檢查：解讀 A 回 800，B／C 回 1174，D 為 800 加上預扣（seed 無 `減少_確認中` 列，所以也是 800）；`userinfo.js` 四處的 `level.points` 一律回 800。因此解讀 B／C 下，同一位使用者登入 response 顯示 800、`pointslevel` 顯示 1174。

     **b. 什麼時候增加或扣除？程式碼中所有寫入點，以及相關的讀取**（grep `point_record`、`travel_point` 於 `backend/src` 與 seed；第 6 列是 SELECT，餘額讀取見上方 a，`userinfo.js:57,123,249,379` 為讀取 `travel_point`）：

     | # | 位置 | 對象 | 內容 | 時機 |
     |---|---|---|---|---|
     | 1 | `controllers/userinfo.js:31` | `user_level.travel_point` | INSERT，值 `0` | 註冊（`POST /api/v1/auth/userinfo/signup`） |
     | 2 | `controllers/userinfo.js:37` | `point_record` | INSERT `(user_id, type='新增', point=0)` | 註冊 |
     | 3 | `controllers/userinfo.js:209` | `user_level.travel_point` | INSERT，值 `0` | Google 首次登入建立使用者（`POST /api/v1/auth/userinfo/login/google`） |
     | 4 | `controllers/userinfo.js:213` | `point_record` | INSERT `(user_id, type='新增', point=0)` | Google 首次登入建立使用者（`POST /api/v1/auth/userinfo/login/google`） |
     | 5 | `controllers/checkout.js:158–161` | `point_record` | INSERT `(user_id, order_id, type='減少_確認中', point = 0 - used_point)` | `PATCH /api/v1/user/checkout/preview/:order_id` 且 `discount.type === 'point'`；沒有檢查是否已有同訂單的 `減少_確認中`，每次 PATCH 都新增一列 |
     | 6 | `controllers/checkout.js:221` | `point_record` | SELECT `type = '減少_確認中'` | `GET /api/v1/user/checkout/summary/:order_id`，取 `rows[0].point` 的絕對值當 `used_point` |
     | 7 | seed 的 `user_level` | `user_level.travel_point` | seed 值 1500、3000、800 | seed |
     | 8 | 來源檔的 `point_record`（已由 §0.1 第 10 項取代） | `point_record` | `'新增' 1610`、`'減少' -436`，皆屬 carol 的一張未付款訂單（該訂單 `total_price` 1610.73、`discount_price` 436.75） | 來源檔 |

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
       - seed 的觀察：來源檔 seed 中 carol 一張未付款訂單的 `減少 -436` 對應該訂單的 `discount_price` 436.75，約 1 點 ＝ 1 元；`新增 1610` 對應該訂單的 `total_price` 1610.73，約 100%（與 `* 0.1` 不符；P1b 已依 #3 重建，見 §0.1 第 10 項）。
     - 解讀 A：**1 點折抵 0.8 元**（兌換率；等同於「用掉 N 點後折 N 的八折」，兩種說法的計算相同）。後果：`discount_price = total_price - used_point * 0.8` 是折扣後應付金額，與程式碼一致，不用改；seed 的 `-436` 與 `436.75` 的關係（約 1:1）不是這個比率；`used_point` 乘 0.8 會產生非整數的金額（例如 7 點 ＝ 5.6 元），`orders.discount_price` 是 FLOAT 可存。
     - 解讀 B：**1 點折抵 1 元，上限（或手續費）是 0.8**，例如「點數最多折抵訂單的 80%」。後果：程式碼沒有任何上限檢查（`min(total * 0.8, used_point)` 之類），實作與這個解讀不符；使用者用大量點數仍可使 `discount_price` 變成負數（`total_price - used_point * 0.8` 沒有下限）。
     - 解讀 C：**原意是 1 點 ＝ 1 元，0.8 是舊值或誤植**（依 seed 的 436:436.75）。後果：兩處 `0.8` 要改成 `1`（違反「controller 不改」）；不改的話使用者每點只折 0.8 元。
     - 另一個獨立的不一致：累積 `0.1`（`controllers/checkout.js:225`，每消費 1 元得 0.1 點）與兌換 `0.8`（每點折 0.8 元）並存，若 A 成立，使用者消費 100 元得 10 點，10 點可折 8 元，等於 8% 回饋；seed 的 `1610`／`1610.73` 約 100% 回饋與此矛盾。是否為設計值需要使用者確認。

  2. **結帳預覽後 `使用者旅遊積分` 要不要即時反映預扣？**（與待確認 1.a 的 B／C／D 重疊）解讀 A：不反映（餘額不變，直到付款確認）。後果：同一批點數在多張訂單同時預覽時可重複使用。解讀 B：反映。後果：使用者取消預覽後點數被占住，而取消沒有回補程式（見 1.b）。 → §4.1 #2（定案：不反映預扣（`使用者旅遊積分` ＝ `user_level.travel_point`））
  3. **view 是否只列出可用的優惠卷（`status = 0` 且未過期）？**（`controllers/userProfile.js:153` 把所有列都放進 `coupon[]`，沒有 `status` 欄位可供判斷） → §4.1 #39（定案：只列 `status = 0` 且未過期的優惠卷）
     - 解讀 A：列出全部綁定（包含已使用 `status=1`、占用中 `-1`、已過期）。後果：`GET /pointslevel` 的 `coupon[]` 含已使用的優惠卷，前端無法區分（因為沒有 `status`／已使用的 key）；seed 使用者 bob、alice 的優惠卷都是 `status = 1`，會全部顯示。
     - 解讀 B：只列出可用的（`status = 0` 且未過期）。後果：`coupon[]` 只含可用優惠卷，符合「使用者會員等級積分」頁面的語意；沒有可用優惠卷的使用者變成「沒有優惠卷」，需決定 JOIN 方式（見邊界）。
     - 解讀 C：排除 `status = 1` 但保留 `-1`（占用中）。後果：占用中的優惠卷仍顯示為可用。
  4. **沒有優惠卷的使用者是否保留一列（LEFT JOIN）**：見邊界。解讀 A：LEFT JOIN。後果：`coupon[]` 含一個全 `null` 物件。解讀 B：INNER JOIN。後果：使用者完全不在 view 內，點數折抵被擋下（409）。 → §4.1 #40（定案：`LEFT JOIN`，沒有優惠卷的使用者保留 1 列、優惠卷欄位全為 `NULL`；須與 #39 的 B 一起採用）

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
  | 價錢 | double precision（【定案 #13】解讀 B） | `order_item.total_price / NULLIF(order_item.quantity, 0)`（【定案 #13】下單當時單價；原推測 `tour_base.價錢`，見待確認 1） | `controllers/checkout.js:252` | JS 讀取 → price |
  | 促銷價錢 | double precision | 見待確認 2；【定案 #13】運算式 `NULLIF(order_item.discount_price, 0) / NULLIF(order_item.quantity, 0)`。結果：`discount_price` 為 0（非促銷）→ `NULL`；`discount_price` 為 `NULL`（seed 中非促銷的項目，P1b 之後 20 筆項目裡有 15 筆；只有北海道雪景 5 日深度遊 3 筆、馬爾地夫蜜月天堂 6 日 2 筆有促銷價）→ `NULL`；`quantity` 為 0 → `NULL`；其餘為下單當時的促銷單價 | `controllers/checkout.js:253` | JS 讀取 `item.促銷價錢` → response.orders[].**discount_price** |
  | quantity（英文） | integer | `order_item.quantity` | `controllers/checkout.js:255` | JS 讀取 → options.people |
  | start_date（英文） | timestamp | `order_item.start_date` | `controllers/checkout.js:256` | JS 讀取 → options.start_date |
  | end_date（英文） | timestamp | `order_item.end_date`（可 NULL） | `controllers/checkout.js:257` | JS 讀取 → options.end_date |
  | room_type（英文） | varchar | `order_item.room_type`（可 NULL） | `controllers/checkout.js:258` | JS 讀取 → options.room_type（這裡不像 `cart.js:222` 轉成 `''`，`NULL` 原樣輸出） |
  | singleTotal_Price（英文，混合大小寫） | double precision（【定案 #12】） | 單一訂單項目小計（見待確認 3；【定案 #12】`order_item.total_price`，下單當時固定，不含促銷） | `controllers/checkout.js:260` | JS 讀取，**沒有 `Number()`** → total_price |
  | total_count（英文） | integer（【定案 #25】） | 該訂單的項目數 | `controllers/checkout.js:263` | JS 讀取 `orderItemRepo.rows[0].total_count` → summary.total_items |

- **列的語意**：每個訂單項目（`order_item`）一列，帶入行程資料（`tour_base`）。`total_count` 是同一訂單所有列共有的項目總數（`rows[0]` 取第一列的值），推測以 `COUNT(*) OVER (PARTITION BY order_id)` 或子查詢計算。沒有排序。
- **邊界**：
  - **controller 行為 1（訂單沒有項目時 500）**：`controllers/checkout.js:263` 讀 `orderItemRepo.rows[0].total_count`，沒有檢查 `rows.length`，`order_item` 沒有任何列時（`rows[0]` 為 `undefined`）丟 TypeError，API 回 500。
  - **controller 行為 2（非擁有者的訂單 500）**：`middlewares/checkout/index.js:190–199` 只確認訂單存在（`SELECT * FROM public."orders" WHERE order_id = $1`，不比對 `user_id`）；`controllers/checkout.js:206–209` 的 `orders` 查詢加了 `user_id`，非擁有者時 `orderRepo.rows[0]` 為 `undefined`，`controllers/checkout.js:225` 的 `orderRepo.rows[0].total_price` 丟 TypeError，API 回 500（而不是 403／404）。與本 view 無關，但本 view 不帶 `user_id`，所以無法在 view 內補這個檢查。
  - **controller 行為 3（只產生一個訂單項目）**：`controllers/checkout.js:20–33,42–56` 取 `cartItemRepo.rows[0]` 建立 `order_item`，購物車有多個項目時只有第一個進入 `order_item`，但 `orders.total_price` 用整個購物車的 `cart.total_price`（`controllers/checkout.js:38`）。因此一張訂單在本 view 只會有 1 列，`total_count` 恆為 1，與 `orders.total_price` 的加總不符。
  - **controller 行為 4（與本 view 相關的 `order_item` 寫入）**：`controllers/newebpay.js:82,213` 更新 `order_item` 時寫 `SET payment = 0／1`（同檔 `:71,206` 對 `orders` 寫的是 `payment_status`），但 V1 `order_item`（V1 `:288–303`）沒有 `payment` 欄位，只有 `payment_status`，這兩段 SQL 在 PostgreSQL 會失敗（`column "payment" does not exist`）。此問題不屬於 B 組 8 個物件，只在此記錄，因為它會讓訂單項目的付款狀態不被更新。
  - **seed 對照（UUID 版本）**：seed 的 `orders` 主鍵都是 v4，`GET /checkout/summary/:order_id` 可通過 `checkout_Vaildator.js:12`；但新訂單只能由 `POST /checkout/order/:cart_id` 產生，前提是購物車有 `cart_item`，而來源檔 seed 行程不是 v4，P1b 之前無法經 `POST /cart` 加入（見共通觀察；P1b Task 2 之後可以）。
  - `價錢`、`促銷價錢` 在 `controllers/checkout.js:252–253` 被直接輸出，`discount_price: item.促銷價錢` 這個映射是 controller 的命名（response 的 `discount_price` 來自 view 的 `促銷價錢`，不是 `order_item.discount_price`）。
  - 欄位名稱必須照拼字：`item.大分類`（`.` 取法，所以不含空格）、`item['旅遊代表圖 Url']`、`singleTotal_Price`、`total_count`。
  - 對 `tour_base` 的 JOIN：同 `user_cartList` 邊界第 1 點（§1 `tour_base` 待確認 1 的下架行程問題）。
- **信心**：欄位名稱：確定；來源對應：欄位名稱本身確定，`價錢`／`促銷價錢`／`singleTotal_Price` 的計算：推測；`total_count` 的計算與型別：推測。
- **待確認**：
  1. **`價錢` 是目前的行程單價，還是下單當時的單價？** → §4.1 #13（定案：`價錢` ＝ 下單當時單價（`order_item.total_price / NULLIF(quantity, 0)`），型別 `double precision`）
     - 解讀 A：`tour_base.價錢`（目前的價格）。後果：行程後來調價，歷史訂單的 `price` 跟著變；`singleTotal_Price` 若用 `order_item.total_price` 則兩者可能不一致。
     - 解讀 B：`order_item.total_price / order_item.quantity`（下單時的單價，`controllers/checkout.js:49` 寫入的是 `tour_base.價錢 * quantity`）。後果：歷史訂單固定；`quantity = 0` 時除以零（V1 沒有 `CHECK`，但 `cart_Validator` 要求 `people >= 1`）。
  2. **`促銷價錢` 是什麼？**（controller 把它輸出為 `discount_price`） → §4.1 #13（定案：`促銷價錢` ＝ 下單當時促銷單價，運算式 `NULLIF(order_item.discount_price, 0) / NULLIF(order_item.quantity, 0)`；`discount_price` 為 0 或 `NULL`、或 `quantity` 為 0 時輸出 `NULL`）
     - 解讀 A：`tour_base.促銷價錢`（目前行程的促銷價）。後果：促銷結束後，歷史訂單的 `discount_price` 變成 `NULL` 或舊促銷價，與下單時不同。
     - 解讀 B：`order_item.discount_price / quantity`（下單時的促銷單價；`controllers/checkout.js:50` 寫入的是 `促銷價 * quantity`，非促銷時是 `0 * quantity ＝ 0`）。後果：非促銷時會是 `0` 而不是 `NULL`，前端若用「有值＝促銷」判斷會把非促銷當成促銷。
     - 解讀 C：`order_item.discount_price`（小計，不除以數量）。後果：欄位名稱是「價錢」卻是小計，與 `價錢` 單價不對稱。
  3. **`singleTotal_Price` 是什麼？** → §4.1 #12（定案：`user_orderList` 的 `singleTotal_Price` ＝ `order_item.total_price`，型別 `double precision`）
     - 解讀 A：`order_item.total_price`（`controllers/checkout.js:49` 寫入的 `tour_base.價錢 * quantity`，即不含促銷）。後果：`GET /summary` 的 `orders[].total_price` 是原價小計，與 `orders.discount_price`（`discount_price` 是整張訂單折扣後應付金額）不相加。
     - 解讀 B：有效單價 × `quantity`（促銷期間用促銷價）。後果：與 `user_cartList` 待確認 1 解讀 A 一致。
     - 解讀 C：`order_item.discount_price`（非促銷是 0）。後果：非促銷項目小計為 0。
     - 型別：`controllers/checkout.js:260` 沒有 `Number()`（`controllers/cart.js:224` 有）。若是 `numeric`／`bigint`，response 是 JSON 字串；`double precision` 是數字。
  4. **`total_count` 的型別**：解讀 A：`integer`（view 內 `::int`）。後果：`summary.total_items` 是數字。解讀 B：`bigint`（`COUNT(*)` 預設）。後果：`summary.total_items` 是字串（例如 `"1"`）。 → §4.1 #25（定案：`integer`（view 內 `::int`））
  5. **是否依 `payment_status` 篩選？** 程式碼只用 `order_id` 取全部項目。解讀 A：不篩選（所有 `payment_status` 都出現）。解讀 B：只含部分狀態。後果：預覽階段（-1／0）看不到項目，`GET /summary` 的 `rows[0].total_count` 取不到而 500。 → §4.1 #14（定案：不篩選 `payment_status`）

## 3. C 組：會員與後台

> C 組共通觀察（各物件裡不再重複解釋）：
>
> - 路徑前綴：收藏 `/api/v1/user/collection`（`routes/collection.js`，掛載在 `server.js:87`）、已購買 `/api/v1/user/purchases`（`routes/purchases.js`，`server.js:90`）、管理者 `/api/v1/admin`（`routes/admin.js`，`server.js:111`）。
> - 路徑相對於 `backend/src/`；SQL 原文的縮排已整理，內容未改。表格「依據」欄的「JS 讀取」「WHERE」「ORDER BY」意義同 §1、§2。
> - 三個 `SELECT *` 的呼叫端（`collection.js:15`、`purchases.js:9`、`purchases.js:59`）都會把 view 的每個欄位原樣放進 response，只有偏好分類 1/2/3 被移除後換成文字陣列（`reversePreferenceMap`，定義在 `utils/Validator/userprofile_Validator.js:6–9`，由 `utils/preferenceMap.js` 的 1–10 反查）。所以這幾個 view 的**欄位集合就是 API 輸出欄位集合**，程式碼只能證實被 controller 讀取的 key，其餘欄位都是推測，分別標在各物件。偏好分類三個欄位同 §1 共通觀察：必須是 `smallint`，值 1–10 以外會變成 `undefined`（JSON 序列化成陣列裡的 `null`）。
> - **`role` 的值與大小寫（影響 C 組三個 API 能不能走通）**：`authorizeRoles`（`middlewares/authorizeRoles.js:5,7`）用 `includes` 做區分大小寫的字串比對，角色取自 JWT payload（`middlewares/auth.js` 解出 `req.user`，簽發處 `controllers/userinfo.js:105,232`），不查 DB（P2 已修：P2 Task 1 起 `verifyLoginToken` 每次驗證都查 DB，`utils/authToken.js:51` 讀 `password, role`，`:60-61` 以 DB 的 `role` 覆蓋 token 內的值，降級後舊 token 不再有舊權限；`middlewares/auth.js` 改呼叫 `verifyLoginToken`）。`user.role` 目前的所有值與來源如下：
>
>   | role 值 | 寫入來源 | 通過 `authRole('User')`（收藏 GET、已購買 GET） | 通過 `authRole('admin')`（admin 路由） |
>   |---|---|---|---|
>   | `User` | 註冊 `controllers/userinfo.js:25`、Google 註冊 `controllers/userinfo.js:202`；seed 的 `alice@example.com`、`carol@example.com` | 是 | 否 |
>   | `admin` | seed 的 `bob@example.com`；管理者 PATCH `controllers/admin.js:59` | 否 | 是 |
>   | `user`（小寫） | 只可能由管理者 PATCH 寫入：`utils/Validator/admin_Validator.js:4,67–74` 只接受 `admin`／`user` 兩個值，`controllers/admin.js:59` 原樣 `UPDATE` | **否**（`'user'` 不等於 `'User'`） | 否 |
>
>   後果：被管理者用 `role: 'user'` 降權的帳號，下次登入後 `GET /api/v1/user/collection/info/all`、`GET /api/v1/user/purchases/info`、`GET /api/v1/user/purchases/info/:order_item_id` 都回 403（`routes/collection.js:11`、`routes/purchases.js:11,17`）。降權成 `'User'` 在 validator 層根本無法表達（不在 `supportedRoles` 內）。這是 controller／validator 的問題，契約只記錄，不處理。
> - **安全問題（全系統性）：`PATCH /api/v1/admin/members/roles` 沒有角色檢查**。`routes/admin.js:23–29` 的 `authRole('admin')` 被註解掉（`:26`），只剩 `auth`（路由掛載在 `/api/v1/admin`，`server.js:111`）；`middlewares/admin/index.js:62–104` 只驗證 body，不比對呼叫者；`controllers/admin.js:59` 原樣 `UPDATE public."user" SET role = $1 WHERE user_id = $2`。後果：任何經註冊流程產生的已登入使用者，都可以把自己（或任何人）的 `role` 改成 `admin`，重新登入後 JWT 帶 `admin`（`controllers/userinfo.js:105`），即可通過系統內**所有** `authRole('admin')` 閘門（`routes/admin.js` 其餘路由、`/admin/product`、`/admin/promotions`、`/admin/coupons` 等），整個管理者授權層實質上對所有註冊使用者開放。範圍限制：只有 body 的 `user_ids`（目標）要通過 `admin_Validator.js:8–15` 的 `UUIDField`（v4／v5，`admin_Validator.js:61–66`），呼叫者本身不受這個檢查。所以**被提權的目標**只能是註冊流程建立的帳號（`uuid_generate_v4()`）；seed 的三個帳號版本位不是 v4／v5，作為目標會被擋成 400（見下一條）。但**呼叫者**可以是任何已登入的帳號，包括 seed 的 `User`（例如 Alice），都能把任何註冊帳號改成 `admin`。這是 route 設定問題，契約只記錄，不處理；決定項見 §4.2 (b)。（P2 已修：P2 Task 1 已取消 `routes/admin.js:26` 的註解並加上 `authRole('admin')`，`controllers/admin.js:57-58` 寫入前把 `user` 正規化成 `User`，非 admin 不能再改角色；此條原文保留作歷史紀錄。）
> - **UUID 版本檢查補充（§2 B 組共通觀察「UUID 版本檢查」沒有涵蓋的驗證器）**：`utils/Validator/admin_Validator.js:8–15` 的 `UUIDField` 只接受 `guid({ version: ['uuidv4', 'uuidv5'] })`（第三段開頭必須是 `4` 或 `5`、第四段開頭必須是 `8`／`9`／`a`／`b`），`userDetailinfoSchema`（`:55–58`）、`userPurviewSchema`（`:61–75`，`user_ids` 每一項）、`userSearchSchema`（`:78–80`）的 `user_id` 都用它。來源檔 seed 三位使用者（alice、bob、carol）的主鍵是手寫值（版本位分別是 `7`、`9`、`a`），**三筆都不是 v4／v5**；P1b Task 2 之後已改成 v4。後果：`GET /api/v1/admin/members/:user_id`（讀 `user_adminList`）、`PATCH /api/v1/admin/members/roles`、`GET /api/v1/admin/members/list/:user_id` 對任何 seed 使用者都在驗證階段回 400（`middlewares/admin/index.js:32`、`:66`、`:112`），只有經註冊流程產生的使用者（`uuid_generate_v4()`，V1 `:6`）走得通。其他 C 組驗證器與 seed 的核對：`collection_Validator.js:60–62` 的 `favorite_id`（`UUIDField` 同樣接受 v4／v5）對來源檔 seed 的 `favorite`（7 筆）全部通過，因為它們是 v5（第三段開頭 `5`，第四段開頭 `8`／`b`／`a`／`9`）；`purchases_Validator.js:8` 的 `order_item_id`（只接受 v4）對來源檔 seed 的 `order_item`（10 筆）全部通過；`collection_Validator.js:55–57` 的 `tour_id` 只是 `nonEmptyString`，**不檢查 UUID**，所以 §2 提到的「seed 行程主鍵都不是 v4」不影響收藏 API（seed 行程可以被加入收藏）。**這一點同樣見 §4.2 (a)，由使用者決定**：改寫 seed `user` 的主鍵為 v4（連同引用它們的所有外鍵），或放寬 `admin_Validator.js` 的 `UUIDField`。使用者決定 A，且 2026-10-23 擴大範圍到 `country`（含 `region.country_id`），並補列其他 v4 專用驗證器（`product_Validator.js:156`、`other_Validator.js:5`、`promotion_Validator.js:7,9`、`coupon_Validator.js:6–20,28,57`），見 §2 B 組共通觀察「UUID 版本檢查」與 §4.2 (a)；新 id 必須是 v4，不是 v5。
> - **各表寫入／讀取來源索引**（供改動時找全）：`favorite` 的寫入只有 `controllers/collection.js:78`（INSERT）、`:100`（DELETE）；`orders`／`order_item` 的寫入見 §2 `user_orderList` 與本節 `user_orders`；`user.role` 的寫入見上表。

### `user_favorite`

- **種類**：view（無參數）
- **使用位置**：
  - `controllers/collection.js:14–17`（API：`GET /api/v1/user/collection/info/all?lang=&page=&limit=`，`routes/collection.js:11`，需登入且 `authRole('User')`）
    ```sql
    SELECT * FROM public."user_favorite" WHERE 收藏人員編號 = $1 ORDER BY 建立時間 DESC LIMIT $2 OFFSET $3
    ```
    參數 `[user_id, limit, (page - 1) * limit]`（`collection.js:16`）：`user_id` 為 `req.user.id`（JWT，不經 UUID 驗證）；`limit`、`page` 是 `req.query` 的字串（`middlewares/collection/index.js:9` 驗證了 `lang`／`page`／`limit` 必填且 `page`、`limit` ≥ 1，但 `validate()` 的結果沒有寫回 `req.query`）。`lang` 在 `collection.js:10` 被解構但沒有用在任何查詢。
  - 沒有其他使用位置。`favorite` 資料表的寫入與重複檢查不走這個 view，見邊界。
- **輸出欄位**（`controllers/collection.js:20–36` 取 key）：

  | 欄位（中文） | 型別 | 來源（表.欄位 或計算式） | 讀取位置 | 依據 |
  |---|---|---|---|---|
  | 收藏人員編號 | uuid | `favorite.user_id` | `controllers/collection.js:15` | WHERE |
  | 建立時間 | timestamptz | `favorite.created_at`（見待確認 2；【定案 #43】收藏時間；**不是** `tour_base` 的 `建立時間`） | `controllers/collection.js:15` | ORDER BY |
  | 偏好分類1 | smallint | `tour.preference1`（欄位名稱確定，來源見待確認 3；【定案 #42】行程的偏好） | `controllers/collection.js:23,32` | JS 讀取 `row.偏好分類1` → 轉成文字放入 response `偏好分類[0]`，原欄位設為 `undefined` |
  | 偏好分類2 | smallint | `tour.preference2`（同上；【定案 #42】） | `controllers/collection.js:24,33` | 同上 → `偏好分類[1]` |
  | 偏好分類3 | smallint | `tour.preference3`（同上；【定案 #42】） | `controllers/collection.js:25,34` | 同上 → `偏好分類[2]` |

  controller 沒有讀取其他 key，`...row`（`collection.js:30`）會把其餘欄位原樣放進 response。以下為依 API 用途推測的欄位，**程式碼無法證實**，原為推測，2026-10-23 使用者採為定案（見待確認 1；【定案 #11】欄位集合選 A：`favorite` 加 `tour_base` 的欄位再加 `favorite_id`，命名照下表；frontend `phase-0` 沒有讀取此 API）：

  | 欄位（中文） | 型別 | 來源（【定案 #11】） | 依據（原推測理由） |
  |---|---|---|---|
  | favorite_id（英文） | uuid | `favorite.favorite_id` | 取消收藏 `DELETE /api/v1/user/collection/info/:favorite_id`（`routes/collection.js:17`、`collection.js:97`）要前端帶 `favorite_id`，而列表是前端唯一可能取得它的 API；欄位名稱是否為英文，程式碼沒有證據 |
  | 旅遊編號 | uuid | `favorite.tour_id`（= `tour.tour_id`） | 沿用 `tour_base` 的命名（§1） |
  | 旅遊名稱、旅遊代表圖 Url、價錢、大分類、小分類、所屬國家、所屬地區等（§1 `tour_base` 輸出欄位表的其餘欄位；**不含** `旅遊編號`——上一列已列，整個 view 只出現一次；**不含** `建立時間`、`更新時間`——`建立時間` 一律取自 `favorite.created_at`，不帶入 `tour_base` 的 `建立時間`／`更新時間`；`偏好分類1/2/3` 見上面第一張表） | 同 §1 `tour_base` | 同 §1 `tour_base` | 收藏清單要顯示行程；偏好分類 1/2/3 的命名與 `tour_base` 相同，表示 view 很可能由 `tour_base` 衍生 |

- **列的語意**：每筆 `favorite` 一列，帶入被收藏行程的資料（待確認 1；【定案 #11，2026-10-23】選 A：帶入 `tour_base` 的欄位）。【定案 #41、#43】下架行程的收藏也出現；`建立時間` ＝ `favorite.created_at`。`WHERE 收藏人員編號 = $1` 取出單一使用者的收藏，controller 以 `建立時間 DESC` 排序並分頁（`LIMIT`／`OFFSET`）。
- **邊界**：
  - **controller 行為 1（`get_collection` 每次都送兩次回應）**：`controllers/collection.js:39–46`（有資料）或 `:49–53`（無資料）已經呼叫 `resStatus` → `res.status(200).json(...)`（`utils/resStatus.js:33`），`:57–64` 又無條件再呼叫一次。第二次 `res.json` 會丟 `ERR_HTTP_HEADERS_SENT`，被 `:65` 的 `catch` 接住並 `next(error)`，進入 `server.js:137` 的錯誤處理，那裡又呼叫 `res.status(500).json(...)` 再丟一次。**client 收到的是第一次的回應**（依序執行，第一次 `json()` 已結束回應）；伺服器 log 每次都有錯誤，錯誤處理之後 Express 對連線的處置（推測是 `finalhandler` 因 headers 已送出而關閉 socket）沒有實測。結果：每次呼叫此 API 至少會留下 `❌ 伺服器內部錯誤` 與 `❌ 系統錯誤` 兩筆錯誤 log（Express 的 `finalhandler` 對錯誤處理再丟出的錯誤可能另外輸出第三筆，推測，未實測），與 view 的內容無關。
  - **controller 行為 2（有資料時的 response 形狀）**：`collection.js:43–45` 的 `dbdata` 是 `{ data: transformedRows }`，`resStatus` 再包一層，所以 client 拿到的是 `body.data.data[]`（兩層 `data`）。
  - **controller 行為 3（寫入與重複檢查走 base table，不走 view）**：`POST /api/v1/user/collection/info/:tour_id` 寫 `INSERT INTO favorite (user_id, tour_id) VALUES ($1, $2)`（`collection.js:78`），`DELETE` 寫 `DELETE FROM favorite WHERE user_id = $1 AND favorite_id = $2`（`collection.js:100`）。V1 `favorite`（`V1:382–390`）沒有 `UNIQUE (user_id, tour_id)`，重複收藏只靠 `middlewares/collection/index.js:68–70` 的 `SELECT 1 FROM favorite WHERE user_id = $1 AND tour_id = $2` 先查再寫，並行請求可以寫入重複列；view 若直接 JOIN 就會重複顯示。
  - **controller 行為 4（`POST` 的 `tour_id` 沒有 UUID 驗證）**：`collection_Validator.js:55–57` 只要求非空字串，`middlewares/collection/index.js:46` 直接把它放進 `SELECT * FROM tour WHERE tour_id = $1`；`tour_id` 不是 UUID 格式時 PostgreSQL 回 `22P02`（invalid input syntax for type uuid），經 `express-async-errors`（`server.js:3`）進入 `server.js:137` 回 500，而不是 400。`DELETE` 有 UUID 驗證（`collection_Validator.js:60–62`）。
  - **controller 行為 5（角色檢查不一致）**：只有 `GET` 有 `authRole('User')`（`routes/collection.js:11`），`POST`／`DELETE`（`:14`、`:17`）只需登入。見共通觀察的 `role` 表。
  - **seed 對照**：來源檔 seed 有 7 筆收藏（Alice 3 筆、Bob 2 筆、Carol 2 筆；P1b 之後 9 筆），其中 Bob 的 `role` 是 `admin`，`authRole('User')` 讓他無法呼叫 `GET /collection/info/all`，所以此 API 在 seed 上只有 Alice 與 Carol 能實際操作，來源檔的 `created_at` 都是 `CURRENT_TIMESTAMP`（同一個 INSERT 敘述內的值相同；P1b 之後 9 筆各不相同，見 §0.1 第 8 項），因此 `ORDER BY 建立時間 DESC` 在同一位使用者的多筆收藏之間沒有區分度，`LIMIT`／`OFFSET` 分頁的順序不穩定（若 `建立時間` 取 `tour.created_at`，seed 行程的 `created_at` 是否相同需另查，見待確認 2）。
  - 其他讀取 `favorite` 的物件（不是本 view，列出避免漏看）：`tour_travel_most_favorited`（§1，推測依 `favorite` 筆數排名）、`tour_travel`／`tour_tour_detail` 的 `收藏狀態`（§1，推測）；`middlewares/collection/index.js:69,103` 直接查 `favorite`。
  - `favorite.tour_id` 有外鍵指向 `tour`（`V1:389`），若 view 對 `tour` 做 `INNER JOIN`，收藏列不會因為行程不存在而消失；若改為對 `tour_base` JOIN，則受 §1 `tour_base` 待確認 1 的上下架問題影響（見待確認 4）。【定案 #41、#7】`tour_base` 含全部行程，下架行程的收藏也出現。
- **信心**：`收藏人員編號`、`建立時間`、`偏好分類1/2/3` 的欄位名稱：確定（直接出現在 SQL／JS）。來源對應：`收藏人員編號` 確定；`建立時間`、`偏好分類` 的來源與其餘欄位集合：推測。
- **待確認**：
  1. **欄位集合：view 是否帶入行程資料？** → §4.1 #11（定案 2026-10-23：欄位集合選 A（`favorite` 加 `tour_base` 的欄位，再加 `favorite_id`），以上面的欄位表為準；frontend `phase-0` 不讀此 API，日後 P3–P6 接前端時若 key 不符，依 spec 重構規則連同 view、契約、契約測試一起改）
     - 解讀 A：`favorite` 加上 `tour_base` 的欄位（再加 `favorite_id`）。後果：前端一次拿到收藏清單所需的名稱、圖、價錢；欄位名稱要與 `tour_base` 一致。
     - 解讀 B：只有 `favorite` 自己的欄位（`favorite_id`、`旅遊編號`、`建立時間`）加偏好分類。後果：偏好分類 1/2/3 沒有來源行程以外的合理來源（見待確認 3），前端要另打商品 API 才能顯示收藏卡片。
     - 解讀 C：對齊 `tour_tour_detail`（§1）的欄位集合。後果：欄位過多，包含 `異動通知內容` 等收藏清單用不到的資料。
  2. **`建立時間` 是收藏時間還是行程建立時間？** → §4.1 #43（定案：`favorite.created_at`）
     - 解讀 A：`favorite.created_at`。後果：最近收藏的排在最前面（符合「使用者查看收藏項目」的語意）；來源檔 seed 的 7 筆時間相同，同使用者內順序不穩定（見邊界 seed 對照）；P1b 之後 9 筆各不相同（§0.1 第 8 項）。
     - 解讀 B：`tour.created_at`。後果：排序跟收藏無關，最新上架的行程在最前；取消後重新收藏不會改變位置。
  3. **`偏好分類 1/2/3` 是行程的偏好，還是使用者的偏好？** → §4.1 #42（定案：`tour.preference1/2/3`（行程的偏好））
     - 解讀 A：`tour.preference1/2/3`（與 `tour_base` 的同名欄位一致；使用者的偏好在 §2 `user_level_point_coupon` 叫 `個人偏好 1/2/3`）。後果：每筆收藏顯示該行程自己的三個分類標籤。
     - 解讀 B：`user.preference1/2/3`。後果：同一位使用者所有收藏列的 `偏好分類` 完全相同，對收藏清單沒有意義。
  4. **下架行程（`tour.status = 2`）的收藏要不要出現？** → §4.1 #41（定案：下架行程的收藏也出現（對 `tour` 或含全部的 `tour_base` JOIN））
     - 解讀 A：出現（view 對 `tour` JOIN，不看上下架）。後果：使用者看得到已下架的收藏，點進去的商品詳情行為由 `tour_tour_detail` 決定。
     - 解讀 B：不出現（view 對 `tour_base` JOIN 且 `tour_base` 只含上架，即 §1 `tour_base` 待確認 1 解讀 B）。後果：收藏列仍在 `favorite` 表，但清單看不到，也就無法由列表取消這筆收藏（`DELETE` 需要 `favorite_id`）。

### `user_orders`

- **種類**：view（無參數）
- **使用位置**：
  - `controllers/purchases.js:9–11`（API：`GET /api/v1/user/purchases/info`，`routes/purchases.js:11`，需登入且 `authRole('User')`；沒有 query／params 驗證，`controllers/purchases.js` 前面也沒有 middleware）
    ```sql
    SELECT * FROM public."user_orders" where 使用者編號 = $1
    ```
    參數 `[user.id]`（`purchases.js:8` 的 `req.user`，即 JWT 內的 `id`）。沒有 `ORDER BY`、沒有 `LIMIT`：整份結果一次回傳。
- **輸出欄位**（`controllers/purchases.js:14–30` 取 key）：

  | 欄位（中文） | 型別 | 來源（表.欄位 或計算式） | 讀取位置 | 依據 |
  |---|---|---|---|---|
  | 使用者編號 | uuid | `orders.user_id` | `controllers/purchases.js:9` | WHERE |
  | 偏好分類1 | smallint | `tour.preference1`（名稱確定，來源見待確認 3；【定案 #42】行程的偏好） | `controllers/purchases.js:17,26` | JS 讀取 → 轉成文字放入 `偏好分類[0]`，原欄位設為 `undefined` |
  | 偏好分類2 | smallint | `tour.preference2`（同上；【定案 #42】） | `controllers/purchases.js:18,27` | 同上 → `偏好分類[1]` |
  | 偏好分類3 | smallint | `tour.preference3`（同上；【定案 #42】） | `controllers/purchases.js:19,28` | 同上 → `偏好分類[2]` |

  controller 沒有讀取其他 key，`...row`（`purchases.js:24`）把其餘欄位原樣放進 response。以下為推測的欄位，**程式碼無法證實**（見待確認 1、4）。原為推測，2026-10-23 使用者採為定案（【定案 #11】欄位集合以下表為準；命名選 A：中文為主、`order_item_id` 保持英文；frontend `phase-0` 沒有讀取此 API）：

  | 欄位（中文） | 型別 | 來源（【定案 #11】） | 依據（原推測理由） |
  |---|---|---|---|
  | order_item_id（英文） | uuid | `order_item.order_item_id` | 明細 API `GET /api/v1/user/purchases/info/:order_item_id`（`routes/purchases.js:14–20`）以 `order_item_id` 查 `user_order_item`；列表是前端取得此 id 的唯一合理來源。`user_order_item` 的此欄位是英文（`purchases.js:59`），所以這裡也可能是英文 |
  | 旅遊名稱、旅遊代表圖 Url、大分類、小分類、價錢（即 §1 `tour_base` 輸出欄位表的全部欄位） | 同 §1 `tour_base` | 同 §1 `tour_base` | 「已購買項目清單」要顯示項目；`偏好分類` 命名與 `tour_base` 一致 |
  | 付款狀態、數量、出發日期、小計、促銷小計 | 見 `order_item` | 依序為 `order_item.payment_status`、`quantity`、`start_date`、`total_price`、`discount_price` | 同上，名稱無程式碼證據；`付款狀態`、`數量`、`出發日期`、`小計` 的命名為【定案 #11】採用，`促銷小計` 的名稱於 2026-10-23 final review 修正時補上，非使用者決定 |

- **列的語意**：推測為「每個訂單項目（`order_item`）一列」（見待確認 1），列出該使用者（`orders.user_id`）名下的項目，並帶入行程資料。沒有預設排序。【定案 #44、#6、#45、#41】每個 `order_item` 一列（含 `order_item_id`）；只含 `order_item.payment_status = 1`；view 內含 `ORDER BY`（依 `orders.created_at` 由新到舊，V1:280）；下架行程的購買紀錄也出現。
- **邊界**：
  - **排序（2026-11-01 使用者決定）**：`ORDER BY` 只有 `orders.created_at DESC`，不加第二排序鍵；同一張訂單的多個項目之間沒有穩定順序，P4 若一張訂單可有多個項目再重新檢視。
  - **controller 行為 1（沒有分頁）**：`purchases.js:9` 沒有 `LIMIT`，使用者的所有項目一次回傳。
  - **controller 行為 2（回應形狀）**：有資料時 `dbdata: transformedRows`（陣列，`purchases.js:37`），client 拿到 `body.data[]`；沒有資料時 `message: '查無資料'` 且沒有 `data`（`purchases.js:41–45`，`resStatus` 對空陣列也不放 `data`）。
  - **controller 行為 3（付款狀態實際上寫不到 1）**：能影響這個 view 的 `payment_status` 寫入點：`controllers/checkout.js:36–39`（`orders` 建立，`-1`）、`:43–56`（`order_item` 建立，`-1`）、`:133–139`（`orders` 與 `order_item` 都改成 `0`）、`controllers/newebpay.js:70–72`（`orders` 改 `0`）、`:206`（`orders` 改 `1`）。`newebpay.js:80–84`、`:211–215` 對 `order_item` 寫的是不存在的欄位 `payment`（V1 `order_item`，`V1:288–303`，只有 `payment_status`；詳見 §2 `user_orderList` 邊界 controller 行為 4），SQL 失敗後 `:127`／`:221` 的 `ROLLBACK` 會把同一個交易裡的 `payment_status` 更新（`:71`、`:206`）一起撤銷。因此：**在乾淨的 DB 上，經 API 產生的訂單，`order_item.payment_status` 只會是 `-1` 或 `0`，`orders.payment_status` 也只會是 `-1` 或 `0`；沒有任何程式碼會寫入 `1`、`2`、`3`、`4`**。這四個值只出現在 seed。
  - **controller 行為 4（每張訂單只會有一個 `order_item`）**：見 §2 `user_orderList` 邊界 controller 行為 3（`controllers/checkout.js:20–33,42–56` 只取購物車第一個項目）。
  - **seed 對照**：來源檔 seed 的 `orders`（5 筆）與 `order_item`（10 筆）（P1b 之後重建成 20 張訂單、每張 1 個項目，且訂單與項目的 `payment_status` 一致，見 §0.1 第 9 項）。`orders.payment_status`：`0` 共 4 筆（來源檔的 bob 2 張、carol 1 張、alice 1 張）、`1` 共 1 筆（carol 的一張）。`order_item.payment_status`：`1` 共 6 筆、`2` 共 1 筆、`3` 共 3 筆。**seed 內 `orders` 與 `order_item` 的付款狀態並不一致**（例如 bob 的一張訂單為 `0`，其項目為 `1`），因此「以哪個表的哪個狀態篩選」在 seed 上會得到不同結果（見待確認 2）。注意 Bob 的 `role` 是 `admin`（seed 的 `bob@example.com`），`authRole('User')` 會讓他在 `GET /purchases/info` 與 `GET /collection/info/all` 回 403，所以這兩個 API 在 seed 上只有 Alice 與 Carol 能實際操作；Bob 的數字只在 view 內可見。依擁有者分：來源檔裡 Alice 1 個項目（狀態 `3`）、Bob 5 個項目（狀態 `1`、`1`、`3`、`1`、`1`）、Carol 4 個項目（狀態 `2`、`1`、`3`、`1`）；P1b 之後見 §0.1 第 9 項。
  - **UUID**：`order_item_id` 對 seed 都是 v4，明細 API 可以通過驗證（見共通觀察）。
  - 對 `tour_base` 的 JOIN：若 view 對 `tour_base` JOIN，下架行程的購買紀錄會消失，見 §1 `tour_base` 待確認 1；`order_item.tour_id` 有外鍵指向 `tour`（`V1:302`），對 `tour` JOIN 不會消失。【定案 #41】下架行程的購買紀錄也出現（`tour_base` 含全部行程，#7）。
  - 其他讀取 `orders`／`order_item` 的位置（不是本 view）：`user_orderList`（§2）、`controllers/checkout.js:170,175,207`、`controllers/discounts.js:19,49,85`、`middlewares/checkout/index.js:52,98,190`、`middlewares/discounts/index.js:26,120`、`controllers/newebpay.js:168`、`middlewares/purchases/index.js:31`。
- **信心**：`使用者編號`、`偏好分類1/2/3` 的欄位名稱：確定。列的粒度、篩選條件、其餘欄位：推測。
- **待確認**：
  1. **一列的粒度：每個 `order_item` 一列，還是每張 `orders` 一列？** → §4.1 #44（定案：每個 `order_item` 一列（含 `order_item_id`））
     - 解讀 A：每個 `order_item` 一列（含 `order_item_id`）。後果：每列可以接到明細 API；一張訂單多個項目會是多列。
     - 解讀 B：每張訂單一列（彙總）。後果：沒有 `order_item_id`，前端無法呼叫明細 API（`routes/purchases.js:14–20` 需要 `:order_item_id`）。
  2. **要列出哪些付款狀態？**（`payment_status`：`-1` 資料剛建立、`0` 資料填寫完成未付款、`1` 已付款、`2` 已取消、`3` 已退款、`4` 付款逾時，`V1:277,292`）。下列後果中的 seed 數字依「controller 行為 3」與「seed 對照」的計算。 → §4.1 #6（定案：清單只含 `order_item.payment_status = 1`）
     - 解讀 A：不篩選（`order_item` 全部 `-1`～`4`）。後果：經 API 新建的訂單項目（只有 `-1`、`0`）也出現在「已購買」；來源檔 seed 上 Alice 1 筆、Bob 5 筆、Carol 4 筆，含已取消（`2`）與已退款（`3`）；P1b 之後 alice 7 筆、bob 6 筆、carol 7 筆（共 20，含 `-1`、`0`、`2`、`3`、`4` 各 1 筆）。
     - 解讀 B：只含 `order_item.payment_status = 1`。後果：已取消、已退款、逾時都不顯示；因為 API 寫不到 `1`（controller 行為 3），**經 API 產生的訂單永遠不會出現**，只有 seed 資料；來源檔 seed 上 Alice 0 筆（回「查無資料」）、Bob 4 筆、Carol 2 筆；P1b 之後 alice、bob、carol 各 5 筆。
     - 解讀 C：含 `order_item.payment_status IN (1, 2, 3, 4)`（排除 `-1`、`0`，即尚未完成付款的）。後果：保留取消／退款／逾時的歷史；API 產生的訂單同樣不會出現；來源檔 seed 上與解讀 A 相同（沒有 `-1`、`0`、`4` 的項目）；P1b 之後 alice 6 筆、bob 5 筆、carol 7 筆（排除 `-1`、`0` 各 1 筆）。
     - 解讀 D：依 `orders.payment_status = 1`（訂單層級）篩選。後果：來源檔 seed 上只有 carol 的一張訂單符合，其下兩個項目（項目狀態 `2` 已取消與 `1`）都出現，Alice、Bob 都是「查無資料」；P1b 之後訂單與項目的狀態一致（§0.1 第 9 項），結果與解讀 B 相同：alice、bob、carol 各 5 筆；API 產生的訂單同樣不會出現。
  3. **`偏好分類 1/2/3` 是行程的還是使用者的？** 同 `user_favorite` 待確認 3。解讀 A（行程）：每個項目顯示該行程的分類標籤。解讀 B（使用者）：同一位使用者所有列相同。 → §4.1 #42（定案：`tour.preference1/2/3`（行程的偏好））
  4. **欄位名稱用中文還是英文？** 已知 `使用者編號` 是中文（WHERE）；`user_order_item` 的 `order_item_id`、`preference1/2/3` 是英文（`purchases.js:59,67–69`）；§2 `user_orderList` 是中英混合。解讀 A：中文為主（與 `tour_base`、`使用者編號` 一致，`order_item_id` 保持英文）。後果：前端讀 `旅遊名稱` 等。解讀 B：英文為主（與 `user_order_item` 一致）。後果：前端讀 `title` 一類；兩種解讀的 response key 不同，前端要對應。 → §4.1 #11（定案 2026-10-23：命名選 A，中文為主、`order_item_id` 保持英文，以上面的欄位表為準；frontend `phase-0` 不讀此 API，日後 P3–P6 接前端時若 key 不符，依 spec 重構規則連同 view、契約、契約測試一起改）
  5. **排序**：`purchases.js:9` 沒有 `ORDER BY`。解讀 A：view 內含 `ORDER BY`（依 `orders.created_at` 由新到舊，V1:280）。後果：順序穩定，但 `ORDER BY` 寫在 view 內在 PostgreSQL 不保證被外層保留（單純 `SELECT *` 加 `WHERE` 通常會保留，加了 JOIN 或排序就不一定）。解讀 B：不排序。後果：順序不穩定，重新整理可能不同。 → §4.1 #45（定案：view 內含 `ORDER BY`（依 `orders.created_at` 由新到舊，V1:280））
  6. **下架行程的購買紀錄要不要出現？** 同 `user_favorite` 待確認 4 的兩個解讀：A（出現）；B（對 `tour_base` JOIN 而消失，受 §1 `tour_base` 待確認 1 影響）。 → §4.1 #41（定案：下架行程的購買紀錄也出現（對 `tour` 或含全部的 `tour_base` JOIN））

### `user_order_item`

- **種類**：view（無參數）
- **使用位置**：
  - `controllers/purchases.js:58–61`（API：`GET /api/v1/user/purchases/info/:order_item_id?lang=`，`routes/purchases.js:14–20`，需登入且 `authRole('User')`，經 `middlewares/purchases/index.js:11` 驗證）
    ```sql
    SELECT * FROM public."user_order_item" where order_item_id = $1
    ```
    參數 `[order_item_id]`，來自 `req.validatedParams`（`purchases.js:57`，在 `middlewares/purchases/index.js:43` 寫入）；驗證為 `purchases_Validator.js:8` 的 `uuid({ version: 'uuidv4' })`。`lang` 由 `querySchema`（`purchases_Validator.js:16`）驗證並預設 `zh-TW`，結果寫入 `req.validatedQuery`（`middlewares/purchases/index.js:44`），沒有任何查詢使用。
  - 沒有其他使用位置。`middlewares/purchases/index.js:31` 另外直接查 `public."order_item"`（不是本 view）。
- **輸出欄位**（`controllers/purchases.js:64–80` 取 key）：

  | 欄位 | 型別 | 來源（表.欄位 或計算式） | 讀取位置 | 依據 |
  |---|---|---|---|---|
  | order_item_id（英文） | uuid | `order_item.order_item_id` | `controllers/purchases.js:59` | WHERE |
  | preference1（英文） | smallint | `tour.preference1`（名稱確定，來源見待確認 3；【定案 #42】行程的偏好） | `controllers/purchases.js:67,76` | JS 讀取 → 轉成文字放入 `preference[0]`，原欄位設為 `undefined` |
  | preference2（英文） | smallint | `tour.preference2`（同上；【定案 #42】） | `controllers/purchases.js:68,77` | 同上 → `preference[1]` |
  | preference3（英文） | smallint | `tour.preference3`（同上；【定案 #42】） | `controllers/purchases.js:69,78` | 同上 → `preference[2]` |

  注意這裡讀的是英文 `preference1/2/3`，與 `user_orders`、`user_favorite` 讀的中文 `偏好分類1/2/3` 不同，response 的合併欄位也不同（`preference` 而不是 `偏好分類`）。`...row`（`purchases.js:74`）把其餘欄位原樣放進 response。以下為推測的欄位，**程式碼無法證實**（見待確認 1、4）。原為推測，2026-10-23 使用者採為定案（【定案 #11】其餘欄位命名選 A：全部英文，沿用 `order_item`／`tour`／`orders` 的欄位名；frontend `phase-0` 沒有讀取此 API）：

  | 欄位 | 型別 | 來源（【定案 #11】） | 依據（原推測理由） |
  |---|---|---|---|
  | order_id、tour_id、payment_status、total_price、discount_price、quantity、start_date、end_date、room_type、created_at、updated_at | 同 `order_item` | `order_item.*`（`V1:288–303`；`created_at`／`updated_at` 取 `order_item`，2026-11-01 使用者決定） | 「訂單明細」；`preference1` 與 `order_item_id` 都是 V1 風格的英文欄位名，可能整個 view 沿用英文欄位 |
  | title、cover_image、type、item 等（`tour` 的欄位，英文欄位名） | 同 `tour` | `tour.*`（不含 `created_at`／`updated_at`；`tour_id` 只出現一次） | 明細頁要顯示行程 |
  | address、phone、payment_type、discount_type | 同 `orders` | `orders.*`（`V1:270–283`） | 明細頁要顯示收件／付款資訊。【定案 #47】**不帶入**這些欄位，只多帶 `使用者編號`（`orders.user_id`）；若日後 P3–P6 接前端時發現明細頁需要地址與電話，改採 #47 的 B（依 spec 重構規則，view、契約與契約測試一起改），且要先處理 §4.2 (c) |

  註記：`created_at`／`updated_at` 取 `order_item`（2026-11-01 使用者決定），不取 `tour` 的；`tour` 的其餘欄位照 `tour.*`（`tour_id` 只出現一次）。`address` 是 `tour.address`（行程地點），**不是**收件地址（#47 不帶 `orders.address`）。

- **列的語意**：由 `WHERE order_item_id = $1`（`order_item` 的主鍵，`V1:289`）取單一訂單項目的明細。預期 0 或 1 列（見待確認 2）。controller 一律把結果 `rows.map(...)` 成**陣列**放進 response，所以即使只有一列，`body.data` 也是長度 1 的陣列。【定案 #46】恰好 1 列（只 JOIN 一對一的 `order_item`、`orders`、`tour`）。
- **邊界**：
  - **controller 行為 1（沒有擁有者檢查，任何登入的 `User` 都可以讀任何項目）**：`middlewares/purchases/index.js:31–33` 與 `controllers/purchases.js:59` 都只用 `order_item_id` 查，沒有 `user_id` 條件；view 也拿不到請求者是誰。因此使用者 A 帶使用者 B 的 `order_item_id`（例如從任何管道取得的 seed 項目，如 bob 買北海道雪景 5 日深度遊的 `order_item`）可以讀到 B 的訂單明細，包括 `orders` 的地址與電話（若 view 帶入，見待確認 4）。契約只記錄；若 view 帶入 `orders.user_id`（`使用者編號`），日後可在 controller 補條件，目前不能。【定案 #47】view 多帶 `使用者編號`（`orders.user_id`），明細不帶 `orders` 的地址與電話，擁有者檢查見 §4.2 (c)。
  - **controller 行為 2（404 永遠不會觸發）**：`middlewares/purchases/index.js:34` 的 `if (!dataRepo)`，`dataRepo` 是 `pool.query` 回傳的 result 物件，永遠為真，所以「無此訂單細項編號」的 404 不可能發生；不存在的 `order_item_id` 會一路走到 controller，由 `purchases.js:63` 的 `rowCount > 0` 回 `200`、`message: '查無資料'`、沒有 `data`（`purchases.js:89–95`）。
  - **controller 行為 3（命名不一致時的結果）**：如果 view 提供的是中文 `偏好分類1/2/3`（與另外兩個 view 一致）而不是英文 `preference1/2/3`，`purchases.js:67–69` 讀到 `undefined`，`reversePreferenceMap[undefined]` 也是 `undefined`，response 的 `preference` 會是 `[null, null, null]`，而 `偏好分類1/2/3` 三個數字欄位**不會被移除**（`purchases.js:76–78` 只清英文 key）。
  - **controller 行為 4（`payment_status` 實際值）**：同 `user_orders` 邊界 controller 行為 3：經 API 產生的項目只會是 `-1` 或 `0`；`1`～`4` 只出現在 seed（來源檔的 `order_item`：`1` 6 筆、`2` 1 筆、`3` 3 筆；P1b 之後：`1` 15 筆，`-1`、`0`、`2`、`3`、`4` 各 1 筆，見 §0.1 第 9 項）。
  - **UUID**：seed 的 `order_item_id`（來源檔 10 筆；P1b 之後 20 筆）全是 v4（版本位 `4`，第四段開頭 `8`／`9`／`a`／`b`），通過 `purchases_Validator.js:8`。
  - 對 `tour_base` 的 JOIN：同 `user_orders` 邊界。【定案 #6、#41】只含 `order_item.payment_status = 1`（與 `user_orders` 同一個篩選）；下架行程的項目也出現。
  - 其他讀取 `order_item` 的位置（不是本 view）：見 `user_orders` 邊界。
- **信心**：`order_item_id`、`preference1/2/3` 的欄位名稱：確定。其餘欄位集合、來源、列數：推測。
- **待確認**：
  1. **其餘欄位用中文還是英文？** 已知 `order_item_id`、`preference1/2/3` 是英文。解讀 A：全部英文（沿用 `order_item`／`tour`／`orders` 的欄位名）。後果：response key 是 `total_price`、`title` 之類，與 `user_orders`（中文為主）不同。解讀 B：中英混合（類似 §2 `user_orderList`）。後果：同一個頁面要同時讀兩種風格，前端易錯。 → §4.1 #11（定案 2026-10-23：命名選 A，全部英文（沿用 `order_item`／`tour`／`orders` 欄位名），另加 `使用者編號`（#47），以上面的欄位表為準；frontend `phase-0` 不讀此 API，日後 P3–P6 接前端時若 key 不符，依 spec 重構規則連同 view、契約、契約測試一起改）
  2. **一個 `order_item_id` 會回幾列？** 解讀 A：恰好 1 列（只 JOIN 一對一的 `order_item`、`orders`、`tour`）。後果：`body.data` 是長度 1 的陣列。解讀 B：JOIN 一對多的表（例如 `tour_detail`、`restaurant_menu`、`hotel_room`），一個項目多列。後果：`body.data` 有多個元素，每個元素重複訂單資料。 → §4.1 #46（定案：恰好 1 列（只 JOIN 一對一的 `order_item`、`orders`、`tour`））
  3. **`preference1/2/3` 是行程的還是使用者的？** 同 `user_favorite` 待確認 3（解讀 A：`tour.preference1/2/3`；解讀 B：`user.preference1/2/3`，後果是明細頁顯示的是購買者自己的偏好而不是商品分類）。 → §4.1 #42（定案：`tour.preference1/2/3`（行程的偏好））
  4. **明細帶入哪些訂單資料？** → §4.1 #47（定案：只有 `order_item` ＋ `tour`，並多帶 `使用者編號`（`orders.user_id`）；明細不帶 `orders` 的地址與電話）
     - 解讀 A：只有 `order_item` ＋ `tour` 的欄位。後果：明細頁沒有地址／電話，其他使用者即使讀到別人的 `order_item_id`（controller 行為 1），洩漏的資料較少。
     - 解讀 B：再帶入 `orders`（地址、電話、付款方式、折扣類型、訂單總額）。後果：明細完整，但 controller 行為 1 會把別人的地址與電話暴露。
     - 解讀 C：再帶入 `payment`（付款紀錄，`V1:308–325`）。後果：可顯示付款結果，但 `payment` 一張訂單可能有多列（失敗重試），可能造成待確認 2 解讀 B 的多列情形。
  5. **是否依 `payment_status` 篩選？**（`-1`～`4`，定義見 `user_orders` 待確認 2）解讀 A：不篩選。後果：`user_orders` 無論採用哪個篩選，點進去的明細都有資料，即使是 `-1`、`0`（尚未付款）的項目，也可以從網址直接開啟。解讀 B：與 `user_orders` 使用相同的篩選條件。後果：兩個 view 一致；不在清單的項目回「查無資料」。解讀 C：與 `user_orders` 不同的篩選條件。後果：清單看得到但明細回「查無資料」，或相反。 → §4.1 #6（定案：明細與清單用同一個篩選：只含 `order_item.payment_status = 1`）

### `user_adminList`

- **種類**：view（無參數）
- **使用位置**：
  - `controllers/admin.js:33–36`（API：`GET /api/v1/admin/members/:user_id?lang=`，`routes/admin.js:14–20`，需登入且 `authRole('admin')`，經 `middlewares/admin/index.js:27` 驗證）
    ```sql
    select * from public."user_adminList" WHERE 使用者編號 = $1
    ```
    參數 `[req.params.user_id]`（`controllers/admin.js:35`）：先經 `admin_Validator.js:55–58` 的 `UUIDField`（v4／v5）驗證，再由 `middlewares/admin/index.js:48` 的 `SELECT * FROM public."user" WHERE user_id = $1` 確認使用者存在（不存在回 404）。`lang` 在 `controllers/admin.js:31` 被解構但沒有用在任何查詢。view 名稱含大寫 `A`、`L`，必須以帶雙引號的混合大小寫建立（見 §2 B 組共通觀察「識別字大小寫」）。
  - 沒有其他使用位置。
- **輸出欄位**（`controllers/admin.js:33–45` 沒有讀取任何 key）：

  | 欄位（中文） | 型別 | 來源（表.欄位 或計算式） | 讀取位置 | 依據 |
  |---|---|---|---|---|
  | 使用者編號 | uuid | `user.user_id` | `controllers/admin.js:34` | WHERE（唯一能由程式碼證實的欄位；與 §1 `user_user_level`、§2 `user_level_point_coupon` 同名） |

  controller 把整份 `userRepo.rows` 放進 `dbdata: { data: userRepo.rows }`（`controllers/admin.js:42–44`），完全沒有讀取或轉換任何欄位，所以程式碼**無法證實**還需要哪些欄位。以下為依「管理者查看註冊用戶詳細資料」（路由註解 `routes/admin.js:13`）與同組 view 推測的欄位，原為推測，2026-10-23 使用者採為定案（見待確認 1；【定案 #11】欄位集合選 A：`user` 加 `user_level` 的欄位，不含優惠卷；frontend `phase-0` 沒有讀取此 API）：

  | 欄位（中文） | 型別 | 來源（【定案 #11】） | 依據（原推測理由） |
  |---|---|---|---|
  | 名稱 | varchar | `user.name` | §1 `user_user_level`、§2 `user_level_point_coupon` 同名欄位；`GET /admin/members`（`controllers/admin.js:11`）列表也回 `name` |
  | 信箱 | varchar | `user.email` | 同上（§2 `user_level_point_coupon` 的 `信箱`；`controllers/admin.js:11` 回 `email`） |
  | 角色 | varchar | `user.role` | 管理者頁面要看／改權限（`PATCH /admin/members/roles`，`controllers/admin.js:59`）；§2 `user_level_point_coupon` 有 `角色` |
  | 個人照片 Url | varchar | `user.avatar_url` | 同 §1 `user_user_level` |
  | 個人偏好 1／2／3 | smallint | `user.preference1/2/3` | 同 §2 `user_level_point_coupon`（欄位名含空格）；但見待確認 2（【定案 #49】輸出 `smallint` 數字） |
  | 旅遊等級、旅遊等級名稱、旅遊徽章 Url、使用者旅遊積分 | varchar／varchar／varchar／integer | `user_level.level`／`name`／`badge_url`／`travel_point` | 同 §1 `user_user_level`、§2 `user_level_point_coupon`（【定案 #2】若包含積分，`使用者旅遊積分` ＝ `user_level.travel_point`，`integer`） |

- **列的語意**：推測為「每位使用者一列」，以 `使用者編號` 取出單一使用者（`WHERE` 只有一個等號條件）。實際列數取決於 `user_level` 的 JOIN 方式（見待確認 3、4）；controller 對 0 列也回 `200`（見邊界）。【定案 #22】對 `user_level` 採 `LEFT JOIN`，有多筆時取最新一筆，所以存在的使用者恰好一列。
- **邊界**：
  - **controller 行為 4（`PATCH /admin/members/roles` 沒有角色檢查，最嚴重，詳見 C 組共通觀察「安全問題」）**：`routes/admin.js:26` 註解掉 `authRole('admin')`，任何已登入的註冊使用者都能改 `role`，直接改到本 view 的 `角色` 欄位，並使所有 admin 路由對註冊使用者開放（目標限 v4／v5 的 `user_id`，即註冊流程建立的帳號，seed 帳號作為目標見行為 3；呼叫者不受此限，任何已登入帳號都可以）。另外 `role` 只接受 `admin`／`user`（小寫），降權寫入的 `user` 與其他地方使用的 `User` 大小寫不同，見共通觀察的 `role` 表。
  - **controller 行為 1（view 查不到時仍是 200）**：存在性檢查在 `middlewares/admin/index.js:48`（查 `user` 資料表，不是 view）。若使用者存在但 view 沒有他的列（例如 view 對 `user_level` 做 `INNER JOIN` 而該使用者沒有等級），`controllers/admin.js:38–45` 仍回 `200`、`message: '查詢成功'`、`data: { data: [] }`；`resStatus` 以 `dbdata.length !== 0` 判斷是否放 `data`（`utils/resStatus.js:9`），物件沒有 `length`，所以 `data` 一定存在。
  - **controller 行為 2（response 形狀）**：client 拿到 `body.data.data[]`（兩層 `data`），與 `user_favorite` 相同；`GET /admin/members`（`controllers/admin.js:10–20`）與 `GET /admin/members/list/:user_id`（`controllers/admin.js:85–97`）直接查 `user` 資料表，只回 `user_id`、`name`、`email`（英文 key），不經過本 view。
  - **controller 行為 3（seed 使用者全部通不過驗證）**：見共通觀察「UUID 版本檢查補充」：`admin_Validator.js:55–58` 的 `UUIDField` 拒絕來源檔 seed 的三個 `user_id`，所以 P1b 之前以 seed 資料操作 `GET /admin/members/:user_id` 一律回 400，這個 view 在 seed 環境下**無法經由 API 被讀到**，只有註冊流程建立的使用者可以；P1b Task 2 之後 seed 使用者的 `user_id` 是 v4，讀得到。
  - **契約要求（設計選擇，不是程式碼證實）**：controller 把整列原樣輸出，所以 view 不應包含 `user.password`（`V1:10`，bcrypt 雜湊）、`login_attempts`、`locked_datetime`；否則管理者 API 會直接回傳密碼雜湊。
  - **JWT 與 DB 的角色分離**：`req.user.role` 來自簽發時的 token（`controllers/userinfo.js:105,232`），`PATCH` 只改 DB，所以 view 的 `角色` 立即變，但被改的人在重新登入前仍帶舊角色（P2 已修：此敘述已不成立，`utils/authToken.js:60-61` 每次請求都以 DB 的 `role` 為準，角色變更立即生效，不必重新登入）。
  - 其他寫入／讀取這個 view 底層欄位的位置（不是本 view）：
    - `user` 寫入：`controllers/userinfo.js:25`（註冊，`role = 'User'`）、`controllers/userinfo.js:93`（登入成功後 `login_attempts = 0`、`locked_datetime = null`、`login_method = 1`）、`:172`、`:186`（Google 登入更新 `avatar_url`、`login_method`；首次綁定的 `:172` 同時把 `password` 清成 NULL）、`:202`（Google 註冊，`password` 寫 NULL）、`middlewares/userinfo/index.js:121`（`login_attempts`、`locked_datetime`）、`:315`、`:393`（`password`）、`controllers/userProfile.js:55`（`name`、偏好）、`:99`（`avatar_url`）、`controllers/admin.js:59`（`role`）。
      - P2 新增（Task 10 實作）：Google 帳號綁定到已存在的 email 會員時，把 `password` 清成 NULL（P2 spec §2.3）。
    - `user_level` 寫入：只有 `controllers/userinfo.js:31`（註冊，`'Level 1'`、`'初心旅人'`、`travel_point = 0`）與 `:209`（Google 註冊）；同一交易另插入一筆 `point_record`（`controllers/userinfo.js:37`、`:213`，`type = '新增'`、`point = 0`）；`backend/src` 內沒有任何 `UPDATE user_level`，所以 `travel_point` 註冊後不會再變。
    - `user_level` 讀取：`controllers/userinfo.js:97,226,359`（`SELECT * FROM public."user_level" where user_id = $1`），並直接讀 `level.travel_point`（`:57,123,249,379`，輸出為 `points`）；另有 `user_user_level`、`user_level_point_coupon`（§1、§2）。
    - `user.role` 讀取：`middlewares/authorizeRoles.js:5`（來自 JWT，不查 DB）、`controllers/userProfile.js:140`（經 `user_level_point_coupon`）。
- **信心**：`使用者編號` 的欄位名稱：確定。其餘欄位、列數、JOIN 方式：推測（controller 完全沒有讀取其他 key）。
- **待確認**：
  1. **欄位集合**： → §4.1 #11（定案 2026-10-23：欄位集合選 A（`user` 加 `user_level` 的欄位，鏡射 `user_level_point_coupon` 去掉優惠卷），以上面的欄位表為準；frontend `phase-0` 不讀此 API，日後 P3–P6 接前端時若 key 不符，依 spec 重構規則連同 view、契約、契約測試一起改）
     - 解讀 A：`user` ＋ `user_level` 的欄位（鏡射 §2 `user_level_point_coupon` 去掉優惠卷）。後果：管理者看到基本資料與等級；沒有優惠卷（優惠卷由 `GET /admin/members/:user_id/coupons` 另查，`controllers/admin.js:239`）。
     - 解讀 B：再加上優惠卷欄位（鏡射 `user_level_point_coupon`，一位使用者多列）。後果：`body.data.data[]` 的長度等於優惠卷數，使用者資料在每列重複；沒有優惠卷的使用者是否保留一列取決於 JOIN 方式（同 §2 `user_level_point_coupon` 待確認 4）。
     - 解讀 C：再加上訂單或積分統計。後果：View 需要聚合，欄位名稱完全沒有依據。
  2. **偏好欄位是數字還是文字？** `admin.js` 沒有像 `collection.js`／`purchases.js` 那樣使用 `reversePreferenceMap`。解讀 A：view 輸出 `smallint` 數字（`個人偏好 1/2/3`）。後果：管理者頁面拿到 `1`～`10`，要自己對照文字。解讀 B：view 內已轉成文字。後果：`smallint` 對照表要放進 view（SQL `CASE`），而且與其他 view 的型別不一致。 → §4.1 #49（定案：`smallint` 數字（`個人偏好 1/2/3`））
  3. **使用者沒有 `user_level` 列時**：同 §1 `user_user_level` 待確認 1。解讀 A（`INNER JOIN`）：後果是上述邊界的 `200` 加 `data: []`，管理者頁面看到空資料而不是 404；註冊流程一律會建立 `user_level`（`userinfo.js:31,209`），所以只有手動建立或 seed 缺漏的使用者會遇到。解讀 B（`LEFT JOIN`）：後果是等級欄位為 `null`，其餘資料仍顯示。 → §4.1 #22（定案：`LEFT JOIN`，沒有 `user_level` 列時等級欄位為 `null`）
  4. **使用者有多筆 `user_level` 時**（V1 `user_level`，`V1:39–50`，沒有 unique）：同 §1 `user_user_level` 待確認 2。解讀 A（直接 JOIN）：後果是 `body.data.data[]` 有多列，管理者頁面如果只取第一列會漏掉資料。解讀 B（取最新一筆）：後果是只有一列，需定義「最新」（`updated_at` 最大）。seed 每位使用者各 1 筆。 → §4.1 #22（定案：取最新一筆（`updated_at` 最大））
  5. **若包含積分，`使用者旅遊積分` 的來源**：同 §2 `user_level_point_coupon` 待確認 1.a（該處有 A–D 四個解讀，此處列兩個代表；C 是 `point_record` 加總但排除 `'減少_確認中'`，D 是 `travel_point` 再加上預扣，後果見該處）。解讀 A：`user_level.travel_point`。後果：管理者看到註冊時的初始值（沒有程式會更新它），seed 上 Carol 為 800（`user_level.travel_point`）。解讀 B：`point_record` 加總。後果：來源檔 seed 上 Carol 為 `1610 + (-436) = 1174`（P1b 之後 carol 為 `+4500 +9800 +3000 +950 +900 −400`，與 800 不同），與解讀 A 的 800 不同；沒有 `point_record` 的使用者要決定是 `0` 還是 `NULL`（註冊流程一律會插入一筆 `point_record`，`controllers/userinfo.js:37,213`，所以只有 seed 缺漏或手動建立的使用者會沒有列）。 → §4.1 #2（定案：`user_level.travel_point`（預扣不反映，型別 `integer`））

## 4. 待使用者確認

> 本節彙整 §1–§3 每個物件的「待確認」（共 79 題），加上契約以外、需要使用者決定的事項。「使用者的決定」欄已於 2026-10-22 由使用者確認：全部採用建議，#1 改選 B（折抵金額）。2026-10-23 final review 後另有使用者決定（#11 fallback、#3 調整 seed、§4.2 (a) 擴大到 `country`、既有 volume 規則見 §0.1）與 controller 裁決（#24、#45、#26），已寫入對應的決定欄。
>
> - **§4.1 契約語意**：49 列。同一個底層問題被多個物件問到時合併成一列（例如 `payment_status` 的用法、點數餘額、下架行程），各物件的「待確認」結尾以「→ §4.1 #n（定案：…）」指向這裡並附上定案；物件內的解讀原文保留，供查證。本表的選項字母是本表自己的編號，與物件內的「解讀 A／B」不一定相同。列依影響排序：先是會改變多支 API 或金額計算的（#1–#7），之後大致依影響遞減，最後是單一物件內的語意。
> - **建議的原則**：選讓現有 controller 不用改就能正確運作的選項，並附程式碼依據。沒有任何選項能不改 controller 就完全正確時，建議欄會明說，並選改動最小的。
> - **（低風險，可直接採用建議）** 共 26 列：#14、#17、#19、#20、#21、#22、#23、#24、#25、#26、#27、#28、#29、#30、#31、#33、#35、#36、#37、#41、#42、#43、#44、#45、#46、#49。這些列的建議是顯而易見的或影響很小，可以整批接受。
> - **§4.2 契約以外**：seed 與驗證器的 UUID 版本、兩個權限問題，以及其他需要使用者決定的非語意事項。

### 4.1 契約語意

| # | 物件 | 問題 | 選項與後果 | 建議 | 使用者的決定 |
|---|---|---|---|---|---|
| 1 | `user_couponList`（待確認 1） | `coupon.discount` 是折扣倍率、折抵金額，還是折扣百分比？（spec 3.1 已知問題 2）程式碼只做 `total_price * discount`：`controllers/discounts.js:38`（回傳）、`controllers/checkout.js:155`（寫入 `orders.discount_price`）；沒有任何地方做減法或除以 100。 | **A 倍率**（0 到 1，`0.9` ＝ 九折，`discount_price` ＝ 折後應付金額）。後果：兩處運算不用改，且與 `checkout.js:165`（點數路徑 `total_price - ...`，同樣把折後應付金額寫進 `orders.discount_price`）一致；seed 的 5 個值（100、50、10、300、20，來源檔）與 `description` 都要改（P1b，見 §0.1 第 2 項）；admin 驗證器 `coupon_Validator.js:45` 只要求 `> 0` 沒有上限，管理者仍可建立 `discount = 100`，要擋需補 `.max(1)`；請求欄位名 `discount_amount` 與倍率語意不符。<br>**B 折抵金額**（NT$）。後果：seed 不用改，admin 驗證器與欄位名相容；但兩處運算會算出金額的數百倍（`total_price` 3576.74、`discount` 100.0 → 357,674），要把 controller 改成 `total_price - discount`；`TRAVEL10P` 的 `10.0` 只折 10 元，與其 `description`「10% 折扣 (最高折抵 500 元)」矛盾。<br>**C 混合**（`TRAVEL10P` 是百分比，其餘是金額）。後果：同一欄位兩種語意，`total_price * discount` 兩種都算錯；要靠新增欄位區分（V1 沒有，需改 migration）；admin 驗證器無法區分。<br>**D 百分比**（0–100）。後果：seed 5 個值都要改成百分比；controller 要改成 `total_price * (1 - discount / 100)`；admin 驗證器要補 `.max(100)`。 | （歷史建議，未採用）**A**。理由：只有 A 讓 `discounts.js:38`、`checkout.js:155` 不用改就正確，B／C／D 都要改 controller（違反 P1「controller 不改」）。代價：P1b 改 seed（值與 description）；admin 驗證器的 `.max(1)` 屬 validator 修改，留給 P6 後台（優惠卷 CRUD）。 | **B 折抵金額**（使用者選擇，與建議 A 不同；建議欄的 seed 改值與 `.max(1)` 代價不適用） |
| 2 | `user_level_point_coupon`（待確認 1.a、2）、`user_adminList`（待確認 5） | `使用者旅遊積分`（點數餘額）取哪個來源？結帳預覽的預扣（`point_record` 的 `'減少_確認中'`，`controllers/checkout.js:158–161`）要不要即時反映？餘額有兩條讀取路徑：本 view（`GET /pointslevel`、折抵檢查 `middlewares/discounts/index.js:89`、`middlewares/checkout/index.js:160`），以及 `controllers/userinfo.js:57,123,249,379` 直接讀 `user_level.travel_point`（輸出為 `level.points`）。 | **A `user_level.travel_point`**（預扣不反映）。後果：與 `userinfo.js` 四處是同一個欄位，兩條路徑一致；`backend/src` 沒有任何 UPDATE `travel_point`，餘額永遠是註冊時的 0 或 seed 的 1500／3000／800，使用點數不會扣，同一批點數可重複折抵；多張訂單同時預覽也能重複使用同一批點數。<br>**B `SUM(point_record.point)`**（全部類型，預扣即時反映）。後果：`減少_確認中` 立刻從餘額扣掉；同一預覽重複 PATCH 會重複扣（每次新增一列）；取消預覽沒有回補程式（`discounts.js:78–115` 沒有任何寫入），點數被占住；與 `userinfo.js` 四處不一致（seed 使用者 `c3d4...`：登入 response 顯示 800，`pointslevel` 顯示 1174）。<br>**C `SUM(point_record.point)` 但排除 `減少_確認中`**。後果：預覽不影響餘額，但沒有任何程式把 `減少_確認中` 轉成 `減少`，使用點數永遠不減餘額；同樣與 `userinfo.js` 不一致（`c3d4...` 為 800 對 1174）。<br>**D `travel_point` 加上 `SUM(減少_確認中)`**。後果：預扣即時生效，但付款完成前沒有人真正扣 `travel_point`；`pointslevel` 與登入 response 的餘額不一致；seed 沒有 `減少_確認中` 列，所以 seed 上等於 A。<br>**附帶（`user_adminList` 原待確認 5）**：採 B／C 時，沒有 `point_record` 的使用者餘額是 `0` 還是 `NULL`？後果：`0` 讓管理者頁面一律是數字；`NULL` 表示無紀錄。註冊流程一律會插入一筆 `point_record`（`userinfo.js:37,213`），只有 seed 缺漏或手動建立的使用者會遇到。建議 `0`。 | **A**。理由：只有 A 讓本 view 與 `userinfo.js` 四處讀同一欄位，controller 不用改。「使用點數不會扣」是 controller 缺少寫入，屬點數功能（spec 4 節 P5「點數規則照 P1 契約中確認的語意」）。型別為 `integer`。 | 採用建議（A，型別 `integer`） |
| 3 | `user_level_point_coupon`（待確認 1.c） | `point * 0.8` 是什麼意思？`controllers/discounts.js:66`（回傳）與 `controllers/checkout.js:165`（寫入 `orders.discount_price`）都是 `total_price - used_point * 0.8`，同一請求在 `point_record` 記的是 `0 - used_point`（`checkout.js:160`）。另有 `checkout.js:225` 的 `total_price * 0.1`（累積，只顯示在 `summary.get_point`，沒有寫入任何表）。 | **A 1 點折抵 0.8 元**（兌換率）。後果：`discount_price` ＝ 折後應付金額，與程式碼一致，不用改；`total_price - used_point * 0.8` 沒有下限，點數夠多時 `discount_price` 會變負數（兩條路徑只檢查點數餘額，`middlewares/discounts/index.js:89`、`middlewares/checkout/index.js:160`），B、C 解讀同樣有此問題；7 點折 5.6 元（`orders.discount_price` 是 FLOAT 可存）；與累積 0.1 並存時，消費 100 元得 10 點、10 點折 8 元，等於 8% 回饋。seed 的 `-436` 對 `436.75`（約 1:1）、`新增 1610` 對 `1610.73`（約 100% 回饋）都不是這個比率（來源檔）。<br>**B 1 點折抵 1 元，0.8 是上限**（例如最多折訂單的 80%）。後果：程式碼沒有任何上限檢查，實作與此解讀不符；`total_price - used_point * 0.8` 沒有下限，大量點數可使 `discount_price` 變負數。<br>**C 原意是 1 點 ＝ 1 元，0.8 是舊值或誤植**（依 seed 約 1:1）。後果：兩處 `0.8` 要改成 `1`（違反「controller 不改」）；不改則每點只折 0.8 元。 | **A**（累積 0.1 一併視為設計值）。理由：A 讓 `discounts.js:66`、`checkout.js:165`、`checkout.js:225` 不用改；B 與實作矛盾，C 要改 controller。代價：P1b 的 `point_record`／`orders` seed 資料要調成與 0.8、0.1 相符，或接受 seed 與規則不符（2026-10-23 使用者選前者：調整 seed）。 | 採用建議（A，累積 0.1 一併視為設計值）；**2026-10-23 使用者決定**：P1b 調整 seed 點數資料，使其與「1 點折 0.8 元」「10% 回饋」相符（來源檔的 `point_record` 與相關訂單），不接受 seed 與規則不符 |
| 4 | `tour_travel_popular`（待確認 1） | `tour_travel_popular` 的「購買」計入哪些 `order_item.payment_status`？（值：-1 剛建立、0 填寫完成未付款、1 已付款、2 已取消、3 已退款、4 付款逾時；`checkout.js:48` 建立 `order_item` 一律寫 -1。） | **A 全部**。後果：未付款、已取消的訂單也灌水，連尚未填寫就放棄的結帳都計入。<br>**B 只算 1（已付款）**。後果：來源檔 seed 有 6 筆 `payment_status = 1`（P1b 之後 15 筆）所以有榜單；但經 API 產生的訂單寫不到 1（`newebpay.js:80–84,211–215` 對 `order_item` 寫不存在的 `payment` 欄位，交易 ROLLBACK，見 §3 `user_orders` 邊界 controller 行為 3），所以新訂單不會進榜，直到付款流程修好。<br>**C 排除 2、3、4（保留 -1、0、1）**。後果：仍計入未付款的訂單。<br>**D 只算 0 與 1**。後果：排除剛建立與所有失敗狀態，介於 A、B 之間。 | **B**。理由：controller 只 `ORDER BY 購買排行 ASC`（`home.js:18,27,71,80`），不讀購買數，任何選項都不用改 controller；「熱門」語意為已付款購買，搭配 #23 的 A（無購買的行程排最後）榜單不會因為沒有已付款訂單而變空。 | 採用建議（B） |
| 5 | `hotel_booking`（待確認 1）、`restaurant_booking`（待確認 2）；`restaurant_booking` 另見 #15 | `hotel_booking`、`restaurant_booking` 的 `booking_count`（占房／占名額）計入哪些 `payment_status`？（值的定義同 #4。） | **A 不看 `payment_status`**。後果：-1、2、3、4 都占房，被放棄、已取消、已退款的訂單仍占著。<br>**B 只數 1**。後果：只有付款的占房；有人下單未付款時，別人仍可加入購物車（超賣風險）；且經 API 產生的訂單寫不到 1（見 #4），檢查等於不作用。<br>**C 數 `IN (-1, 0, 1)`**。後果：未付款的訂單占房，取消／退款／逾時的釋放；沒有任何程式寫入 4（逾時），放棄的結帳會一直占房。<br>**D 數 `IN (0, 1)`**。後果：排除「剛建立、還沒填寫」的訂單，其餘同 C。<br>**E 數 `cart_item`**（購物車內項目）。後果：占房的是還沒結帳的項目；PATCH 時（`middlewares/cart/index.js:187,207`）呼叫端沒有排除自己，修改會與自己衝突。<br>**F `order_item` 與 `cart_item` 都數**（僅 `hotel_booking` 列出）。後果：同一人的購物車與訂單各算一次，重複計算。 | **C**。理由：controller 只比較 `booking_count >= room_count`（`middlewares/cart/index.js:62,197`）與 `>= reservation_limit`（`:80,215`），任何選項 controller 都不用改；C 讓經 API 產生的訂單（只會是 -1 或 0，`checkout.js:36–56,133–139`）仍然占房，檢查才有作用，同時釋放 2、3、4。代價：沒有逾時機制，放棄的結帳會占房，屬 P4 交易。 | 採用建議（C） |
| 6 | `user_orders`（待確認 2）、`user_order_item`（待確認 5） | 「已購買」清單與明細要列出哪些 `payment_status`？`user_orders`（清單）與 `user_order_item`（明細）要不要用同一個篩選？ | **A 不篩選（`-1`～`4`）**。後果：經 API 產生的新訂單項目（只有 -1、0）也出現在「已購買」；來源檔 seed 上 Alice 1 筆、Bob 5 筆、Carol 4 筆，含已取消（2）與已退款（3）（Bob 是 `admin`，`authRole('User')` 讓他呼叫 `GET /purchases/info` 回 403，他的數字只在 view 內可見，下同）。<br>**B 只含 `order_item.payment_status = 1`**。後果：已取消、已退款、逾時都不顯示；經 API 產生的訂單不會出現（寫不到 1，見 #4），只有 seed 資料；來源檔 seed 上 Alice 0 筆（回「查無資料」）、Bob 4 筆、Carol 2 筆；P1b 之後 alice、bob、carol 各 5 筆。<br>**C 含 `IN (1, 2, 3, 4)`**。後果：保留取消／退款／逾時的歷史；經 API 產生的訂單同樣不會出現（寫不到 1，見 #4）；來源檔 seed 上與 A 相同（來源檔沒有 -1、0、4；P1b 之後 -1、0、4 各 1 筆，C 比 B 多出狀態 2、3、4 的項目）。<br>**D 依 `orders.payment_status = 1`（訂單層級）**。後果：經 API 產生的訂單同樣不會出現；來源檔 seed 上只有 carol 的一張訂單符合，Alice、Bob 都是「查無資料」，且來源檔 `orders` 與 `order_item` 的付款狀態不一致，結果與項目層級不同；P1b 之後兩者一致（§0.1 第 9 項），D 與 B 的結果相同。<br>明細：**與清單相同篩選**，後果：兩個 view 一致，不在清單的項目回「查無資料」；**不篩選**，後果：任何狀態的項目都可從網址直接開啟；**不同篩選**，後果：清單看得到但明細回「查無資料」，或相反。 | 清單與明細都用 **B**。理由：兩個 controller 都不篩選也不讀付款狀態（`purchases.js:9–11`、`:58–61`），任何選項 controller 都不用改；「已購買」的語意是已付款，理由純粹是語意，不是 controller 的限制。代價：付款流程修好（P4）之前，API 產生的訂單不會出現在這兩支 API。 | 採用建議（清單與明細都用 B） |
| 7 | `tour_base`（待確認 1）、`tour_travel`（待確認 4）、`tour_travel_popular`（待確認 4）、`tour_travel_most_favorited`（待確認 3）、`tour_tour_detail`（待確認 3）、`user_cartList`（待確認 4） | `tour_base` 是否含下架（`status = 2`）行程？以及 `tour_travel`、`tour_travel_popular`、`tour_travel_most_favorited`、`tour_tour_detail` 要不要只回傳上架行程？（程式碼矛盾：`admin.js:168`、`product.js:1067` 用 `上下架狀態` 篩選，要含下架；`home.js:15/33/49/68` 的公開首頁直接查 `tour_base`，沒有上架過濾。） | **tour_base A 含全部**。後果：管理者清單與 `status=2` 篩選正常；未登入首頁促銷分頁（`home.js:33`，直接查 `tour_base`）會列出下架行程；`cart.js`／`checkout.js` 查價也能查到下架行程。<br>**tour_base B 只含上架**。後果：首頁正常，但 `GET /admin/product?status=2` 永遠是空的、管理者清單看不到下架行程；上架 API 本身不受影響（`patch_tourStatus`，`product.js:1332–1341`，直接 UPDATE `tour`），但前端清單裡沒有可選的 `tour_id`。<br>**其餘四個 function 只回 `status = 1`**。後果：未登入的熱門／最多收藏（`INNER JOIN` function）、已登入首頁與商品搜尋都不會露出下架行程。`tour_tour_detail` 在 `product.js:178–183` 已先過濾 `status = 1`，function 內是否過濾不影響該 API。<br>**其餘四個 function 不過濾**。後果：下架行程出現在公開搜尋與首頁熱門。<br>`user_cartList` 對 `tour_base` 的 JOIN：tour_base 採 A 時 INNER／LEFT 結果相同；採 B 時 INNER 會讓購物車裡已下架的項目消失，LEFT 則行程欄位為 `NULL`、小計 0。 | **tour_base 採 A，其餘四個 function 過濾 `status = 1`**。沒有任何一個選項能讓所有 controller 路徑都不改就正確：採 A 時，只剩未登入首頁促銷分頁（`home.js:33`）會露出下架行程，已登入版走 `tour_travel`（`home.js:41`）已濾掉；採 B 則直接讓 `admin.js:168`、`product.js:1067` 的下架篩選失效。A 是改動最小的選項。採 A 後剩下兩個 controller 缺口，留給 P3 商品／P4 交易（`home.js:33` 已於 P3 Task 3 修正：首頁促銷只列上架且期間內；下架行程可加入購物車並結帳仍留給 P4）：`home.js:33` 的未登入促銷分頁露出下架行程；下架行程仍可加入購物車並結帳（`middlewares/cart/index.js:26` 只確認 `tour` 列存在，`cart.js:19–22`、`checkout.js:24` 都從 `tour_base` 取價）。 | 採用建議（`tour_base` 採 A，其餘四個 function 過濾 `status = 1`） |
| 8 | `tour_base`（待確認 2）、`tour_tour_detail`（待確認 1）、`tour_hotel`（待確認 4）、`tour_restaurant`（待確認 3） | 一個行程有多筆通知（例如同時有「促銷」與「異動」）時，一列怎麼呈現？`notification` 沒有 unique 約束，同一個 `tour_id` 可有多列。 | **A 每個行程只取一筆**（例如最新）。後果：`通知狀態` 只會是其中一個，另一種看不到；有促銷又有異動時，`cart.js:22` 可能讀不到促銷價。<br>**B 促銷與異動各自成欄**（`促銷價錢`…取自 type='促銷'、`異動通知內容` 取自 type='異動'，`通知狀態` 依優先順序取一個）。後果：兩者都能顯示；需另定優先順序。<br>**C 每筆通知一列**。後果：同一行程在首頁、admin 清單重複出現；`rows[0]` 取哪筆不固定；`hotel`／`food` 的 `rows.map` 會與房型、菜單相乘而重複。 | **B，`通知狀態` 優先序為 促銷 高於 異動**（同類型有多筆時取 `updated_at` 最大者，此為建議的細節）。理由：`tour_tour_detail` 同時讀 `異動通知內容` 與促銷欄位且只讀 `rows[0]`（`product.js:357–363`），`hotel`／`restaurant` 用 `rows.map`（`product.js:409`、`:263`、`:268`），只有 B 一個行程一列且兩者都在；促銷優先是因為 `home.js:33`（`通知狀態 = '促銷'`）與 `cart.js:22`（CASE）只認 `'促銷'`。 | 採用建議（B，`通知狀態` 優先序 促銷 高於 異動） |
| 9 | `tour_base`（待確認 4） | 促銷期間外，`通知狀態` 要不要在 view 內就不回 `'促銷'`？（原 `tour_base` 待確認 4。）這個決定適用所有從 `notification` 輸出 `通知狀態`／`促銷價錢`／`促銷開始／結束日期` 的物件：`tour_base`、`tour_travel`（欄位集合見 #26）、`tour_tour_detail`、`tour_hotel`、`tour_restaurant`，以及取自 `tour_base` 的 `user_cartList`；`user_orderList` 僅在 #13 採 A（取目前行程價）時才適用，#13 採 B（建議）時它的價格取自 `order_item`，也沒有 `通知狀態` 欄位。與 #10 是兩個獨立的問題。controller 自己再檢查 `now() between`（`cart.js:22`、`checkout.js:31`）。 | **A view 不判斷**，期間外仍是 `通知狀態='促銷'`。後果：首頁促銷分頁（`home.js:33`、`home.js:41`）列出已過期或尚未開始的促銷行程；詳情的 `promotion.tag`（`product.js:361`）期間外仍是 '促銷'；管理者促銷清單（`promotion.js:8` 的 `通知狀態 = '促銷'`，`:42` 查 `tour_base`）仍列出所有促銷（含未開始與已過期），管理功能正常。<br>**B 只在期間內才回 `'促銷'`，否則 `NULL`**。後果：首頁促銷分頁正確；但管理者促銷清單（`promotion.js:8,42`）看不到尚未開始與已過期的促銷，無法管理；管理者商品清單（`admin.js:168` 選取 `通知狀態`）這些行程顯示 `NULL`。seed 的兩筆促銷日期是浮動的（來源檔：起日 ＝ `2025-11-01`／`2025-10-01` 加上載入日與 `2025-05-20` 的天數差），載入後 165 天與 134 天才開始，載入當天都不在期間內，所以 B 之下 seed 的管理者促銷清單與首頁促銷分頁從第一天起都是空的，P1b 要調整 seed 日期。 | **A**（不判斷）。沒有任何選項能讓所有 controller 路徑都不改就正確：A 讓 `home.js:33,41` 在期間外仍列出促銷（controller 缺期間條件，留給 P3 商品；已於 P3 Task 3 修正：首頁促銷只列上架且期間內）；B 則讓管理者促銷清單（`promotion.js:8,42`）失去未開始與已過期的促銷，破壞管理功能。A 是改動最小的選項。`is_promoted` 的問題由 #10 處理，不依賴本題。 | 採用建議（A） |
| 10 | `user_cartList`（待確認 2） | 促銷期間外，`促銷價錢` 要不要在 view 內就是 `NULL`？（原 `user_cartList` 待確認 2；同樣適用 `tour_base`、`tour_tour_detail`、`tour_hotel`、`tour_restaurant` 的 `促銷價錢`；`user_orderList` 僅在 #13 採 A 時適用。）`is_promoted` 在三處以 `促銷價錢` 的真偽判斷：`product.js:284`（restaurant）、`:359`（travel／spot）、`:450`（hotel）。 | **A 永遠是 `notification.promo_price` 原值**。後果：期間外三處 `is_promoted` 仍為 true；`cart` 的 `promo_price`（`cart.js:217`）期間外仍有值，前端要自己判斷期間。<br>**B 只在期間內才有值，否則 `NULL`**（`促銷開始／結束日期` 照常輸出；可與 #9 的 A 或 B 獨立搭配）。後果：三處 `is_promoted` 與 `cart` 的 `promo_price` 都正確；`cart.js:22`、`checkout.js:31` 的 `now() between` 檢查變成多餘但無害；管理者促銷清單仍依 `通知狀態` 找得到所有促銷，但該 API `select * from tour_base` 並以 `...rest` 回傳（`promotion.js:42`、`:59–63`），`促銷價錢` 會在 response 裡：未開始與已過期的促銷顯示 `促銷價錢 = NULL`，以目前的 seed 而言，載入當天起每一筆促銷都是 NULL（管理者看得到促銷但看不到價格）。 | **B**（只 gate `促銷價錢`，`通知狀態` 照 #9 不 gate）。沒有任何選項完全不改 controller 就正確（`home.js:33,41` 的期間條件仍缺，見 #9）；但這個組合讓 `is_promoted`（`product.js:284,359,450`）與 cart 的 `promo_price` 不用改就正確，仍可管理所有促銷（只是期間外的促銷在管理者清單上 `促銷價錢` 為 NULL），回歸比 #9 的 B 小，是改動最小的選擇。代價：seed 的促銷在開始前（載入後 134、165 天內），詳情的 `is_promoted` 是 false。 | 採用建議（B，只 gate `促銷價錢`，`通知狀態` 照 #9 不 gate） |
| 11 | `user_level_review_forHome`（待確認 1）、`user_favorite`（待確認 1）、`user_orders`（待確認 4）、`user_order_item`（待確認 1）、`user_adminList`（待確認 1） | 程式碼沒有讀取、只能推測欄位集合與命名的 view：`user_level_review_forHome`、`user_favorite`、`user_orders`、`user_order_item`、`user_adminList`。controller 都是 `SELECT *` 後整份放進 response，前端（`phase-0`）依實際 key 讀取；這一題決定五支 API 的 response 形狀，並牽動 §4.2 (d1)。 | **整體做法 A 照契約中的推測欄位建立**。後果：若 frontend 讀取的 key 不同，首頁好評、收藏清單、已購買清單、管理者會員詳情會缺資料。**整體做法 B 先核對 frontend 實際讀取的 key 再定**（唯讀，見 §4.2 (d1)）。後果：多花一道工，欄位與命名有證據。<br>**`user_level_review_forHome` 欄位集合**（原待確認 1）：A 照推測欄位（評論編號、名稱、個人照片 Url、旅遊等級、旅遊等級名稱、旅遊徽章 Url、評分、評論內容、評論時間）。後果：前端 key 不同時首頁好評缺資料。B 先查 frontend 再定。後果：多一道工。<br>**`user_favorite` 欄位集合**（原待確認 1）：A `favorite` 加 `tour_base` 的欄位（再加 `favorite_id`）。後果：一次拿到收藏卡片所需的名稱、圖、價錢，欄位要與 `tour_base` 一致。B 只有 `favorite` 自己的欄位（`favorite_id`、`旅遊編號`、`建立時間`）加偏好分類。後果：偏好分類沒有行程以外的合理來源，前端要另打商品 API。C 對齊 `tour_tour_detail` 的欄位集合。後果：欄位過多，含收藏清單用不到的 `異動通知內容` 等。<br>**`user_adminList` 欄位集合**（原待確認 1）：A `user` 加 `user_level` 的欄位（鏡射 `user_level_point_coupon` 去掉優惠卷）。後果：管理者看到基本資料與等級，優惠卷另查（`admin.js:239`）。B 再加優惠卷欄位（一位使用者多列）。後果：`body.data.data[]` 長度等於優惠卷數、使用者資料每列重複，沒有優惠卷的使用者是否保留一列看 #40。C 再加訂單或積分統計。後果：view 需要聚合，欄位名稱沒有依據。<br>**命名，每個 view 各自一題**（`user_orders` 原待確認 4、`user_order_item` 原待確認 1 是兩個獨立的待確認，可分別決定；兩者選不同風格時，已購買清單與明細頁的 key 風格不一致）：中文為主、`order_item_id` 保持英文。後果：前端讀 `旅遊名稱` 等。英文為主（沿用 `order_item`／`tour`／`orders` 欄位名）。後果：前端讀 `title`、`total_price` 一類，與中文風格的 `user_orders` 不同。中英混合（類似 `user_orderList`）。後果：同一頁面要讀兩種風格。 | （歷史建議，d1 無證據後以 fallback 取代）整體做法 **B**，作法與時程見 §4.2 (d1)；各欄位集合與命名在核對 frontend 之前不預選。理由：controller 對這些欄位幾乎一個都不讀（只讀 `使用者編號`、`order_item_id`、偏好分類），任何選項 controller 都不用改，唯一的依據是 frontend。 | 採用建議（B：依 §4.2 (d1) 核對 frontend 後回填）；**2026-10-23 d1 已完成**：frontend `phase-0` 沒有讀取這五支 API，沒有證據可回填。使用者決定 fallback：**採用契約中的推測欄位表為定案**，P3–P6 接前端時若 key 不符，依 spec 重構規則（view、契約、契約測試一起改）處理。各 view 採用的選項（皆為該物件推測表已顯示者）：`user_level_review_forHome` 欄位集合 **A**（評論編號、名稱、個人照片 Url、旅遊等級、旅遊等級名稱、旅遊徽章 Url、評分、評論內容、評論時間）；`user_favorite` 欄位集合 **A**（`favorite` 加 `tour_base` 的欄位，再加 `favorite_id`）；`user_adminList` 欄位集合 **A**（`user` 加 `user_level` 的欄位，不含優惠卷）；`user_orders` 命名 **中文為主、`order_item_id` 保持英文**（一列一個 `order_item`，見 #44）；`user_order_item` 命名 **英文為主**（沿用 `order_item`／`tour`／`orders` 欄位名，加 `使用者編號`，見 #47）。 |
| 12 | `user_cartList`（待確認 1）、`user_orderList`（待確認 3） | `singleTotal_Price` 怎麼算、什麼型別？（`user_cartList`：程式碼只讀；`user_orderList`：`checkout.js:260` 沒有 `Number()`，`cart.js:224` 有。） | **cartList A 有效單價 × `quantity`**（促銷期間內用促銷價，否則原價，同 `cart.js:19–22` 的 CASE）。後果：與 `cart.total_price` 的累計邏輯一致。<br>**cartList B 原價 × `quantity`**。後果：有促銷的項目小計大於 `cart.total_price` 實際加的金額，`summary.total_price` 與 `cart.total_price` 不一致。<br>**cartList C 促銷價 × `quantity`**（NULL 退回原價，不檢查期間）。後果：過期促銷仍用促銷價。<br>**orderList A `order_item.total_price`**（`checkout.js:49` 寫入的 `價錢 * quantity`，不含促銷）。後果：`orders[].total_price` 是原價小計，下單當時固定，與 `orders.discount_price`（整張訂單折後應付金額）不相加；促銷項目的 `orders[].total_price` 會大於 `summary.total_price`（後者是 `orders.total_price`，取自以促銷價計算的 `cart.total_price`，`checkout.js:38,264`）。<br>**orderList B 有效單價 × `quantity`**。後果：與 cartList A 一致，但隨行程目前的促銷變動。<br>**orderList C `order_item.discount_price`**（非促銷是 0）。後果：非促銷項目小計為 0。<br>型別：`numeric`／`bigint` 時 pg 回字串；`cart.js:224` 有 `Number()` 所以任何型別都可；`checkout.js:260` 沒有，只有 `double precision`（或 integer）才是 JSON 數字。 | cartList 採 **A**；orderList 採 **A**；兩者型別都用 **`double precision`**（`order_item.total_price` 在 V1 即 FLOAT，`V1:293`）。理由：cartList A 與 `cart.js:19–22`、`cart.total_price` 累計一致；orderList A 是訂單建立時寫入的值，歷史訂單不隨行程調價改變，與 #13 的建議同方向；`double precision` 讓沒有 `Number()` 的 `checkout.js:260` 不用改。程式碼沒有指定 cartList 與 orderList 的計算方式，這是依一致性的建議。 | 採用建議（cartList A、orderList A、`double precision`） |
| 13 | `user_orderList`（待確認 1、2） | `user_orderList` 的 `價錢` 與 `促銷價錢` 是行程目前的價格，還是下單當時的？（response 把 `促銷價錢` 輸出成 `orders[].discount_price`，`checkout.js:253`。） | **A 目前的行程價**（`tour_base.價錢`、`tour_base.促銷價錢`）。後果：行程後來調價或促銷結束，歷史訂單的 `price`、`discount_price` 跟著變（促銷結束後變 NULL）。<br>**B 下單當時的單價**（`價錢` ＝ `order_item.total_price / quantity`，`促銷價錢` ＝ `order_item.discount_price / quantity`，寫入處 `checkout.js:49–50`）。後果：歷史訂單固定；`價錢` 型別變成 `double precision`；`quantity = 0` 時除以零（V1 無 CHECK，但 `cart_Validator` 要求人數 ≥ 1）；非促銷時 `order_item.discount_price` 是 `0 * quantity ＝ 0`，輸出 `0` 而不是 `NULL`，前端若用「有值＝促銷」判斷會把非促銷當促銷。<br>**C `促銷價錢` ＝ `order_item.discount_price`（小計，不除數量）**。後果：欄位名是「價錢」卻是小計，與單價的 `價錢` 不對稱。 | **B**，非促銷（0）時 `促銷價錢` 輸出 `NULL`，且用 `NULLIF(quantity, 0)` 避免除以零。理由：訂單明細應固定下單當時的價格；`checkout.js:252–253` 原樣輸出，不用改。輸出 `NULL` 與 `user_cartList` 的 `促銷價錢`（非促銷為 NULL）一致。這個細節是建議，不是程式碼已證實的行為。 | 採用建議（B，非促銷（0）時 `促銷價錢` 輸出 `NULL`，用 `NULLIF(quantity, 0)`）；定案運算式：`價錢` ＝ `order_item.total_price / NULLIF(order_item.quantity, 0)`，`促銷價錢` ＝ `NULLIF(order_item.discount_price, 0) / NULLIF(order_item.quantity, 0)`（`discount_price` 為 0 或 `NULL`、或 `quantity` 為 0 時皆為 `NULL`） |
| 14 | `user_orderList`（待確認 5） | `user_orderList` 要不要依 `payment_status` 篩選？（程式碼只用 `order_id` 取全部項目。） | **A 不篩選**。後果：預覽階段（-1／0）的項目也在，`GET /summary` 正常。<br>**B 只含部分狀態**。後果：預覽階段看不到項目，`orderItemRepo.rows[0].total_count`（`checkout.js:263`）取不到而 500。 | （低風險，可直接採用建議）**A**。理由：只有 A 讓 `GET /checkout/summary/:order_id` 在 -1／0 的訂單上不 500（`checkout.js:263`），controller 不用改。 | 採用建議（A） |
| 15 | `restaurant_booking`（待確認 2） | `restaurant_booking` 的 `booking_count` 數什麼？（狀態篩選見 #5。） | **A `order_item` 筆數**（該行程 `tour.item='food'`）。後果：已取消、已退款、逾時的訂單也占名額（若不加狀態篩選）；一筆訂單不論人數都算 1。<br>**B `order_item.quantity` 加總**（人數）。後果：與 `reservation_limit`（`restaurant.reservation_limit`，來源檔 seed 為 50、30；P1b 另加 3 家，各 40）同單位，符合「人數限制」的語意（`tour_restaurant` 輸出為 `餐廳人員限制`，`response.feature.about.people`）。<br>**C A 或 B 加上 `payment_status` 篩選**。後果：同 #5。<br>**D 數 `cart_item`**。後果：占名額的是尚未結帳的購物車項目。 | **B**（狀態篩選照 #5）。理由：controller 只比較數字（`middlewares/cart/index.js:80,215`），不用改；`reservation_limit` 是人數上限，單位要相同。 | 採用建議（B，狀態篩選照 #5） |
| 16 | `restaurant_booking`（待確認 1） | `restaurant_booking` 的第 1 個參數經 API 恆為 `NULL`（`middlewares/cart/index.js:73,208` 傳 `options.start_time`，但 `foodSchema`，`cart_Validator.js:22–27`，只有 `start_date`，帶 `start_time` 會被驗證擋成 400），function 要怎麼處理？ | **A 忽略參數 1**，只以行程計算總預約數對 `reservation_limit`。後果：整個行程累計到上限就額滿，不分時段；與「預約時間」語意不符，但額滿檢查有作用。<br>**B 以參數 1 比對時段**（程式碼原意）。後果：參數恆為 `NULL`，永遠比對不到，額滿檢查形同虛設；要有效必須改 controller 讀 `options.start_date`。<br>**C 參數為 `NULL` 時回 0 列**。後果：`middlewares/cart/index.js:77,212` 的 `rowCount > 0` 不成立而略過檢查，結果同 B。 | **A**。理由：只有 A 在 controller 不改的前提下，額滿檢查仍有作用。保留參數 1（簽章不變），P4 修好 controller 傳 `start_date` 後再改成時段比對（依 spec 重構規則，要同時更新契約與契約測試）。 | 採用建議（A） |
| 17 | `hotel_booking`（待確認 2） | `hotel_booking` 日期區間重疊的判定，含不含退房當日？（`order_item.start_date`／`end_date` 是 `timestamp`，V1 `:296–297`，是否取到日期精度也要定。） | **A 半開區間 `[start_date, end_date)`**。後果：退房日當天可被下一位入住，連續住宿可接續。<br>**B 閉區間 `[start_date, end_date]`**。後果：退房日當天仍算占房，連續住宿無法接續。 | （低風險，可直接採用建議）**A**。理由：一般飯店退房日當天房間可再出租；controller 只比較結果，不用改。 | 採用建議（A） |
| 18 | `hotel_booking`（待確認 3） | `hotel_booking` 找不到 (行程, 房型)（例如 `room_type` 拼錯）時怎麼回？ | **A 回 0 列**。後果：`middlewares/cart/index.js:59,194` 的 `rowCount > 0` 不成立而略過檢查，無效房型的項目被加入購物車。<br>**B 回 1 列 `booking_count = 0, room_count = 0`**（例如 `COALESCE`）。後果：`0 >= 0` 成立，被「選擇的房間已無空房」擋下，訊息不準確但不會加入無效房型。<br>**C 丟例外**。後果：API 回 500。 | **B**。理由：controller 不改的前提下，只有 B 能擋下無效房型且不 500。 | 採用建議（B） |
| 19 | `restaurant_isClosed`（待確認 1、2） | `restaurant_isClosed` 依什麼判斷「休息」？預約時間為 `NULL` 或餐廳不存在時怎麼回？（function 必須永遠回 1 列：`middlewares/cart/index.js:110,245` 沒有 `rowCount` 檢查，0 列會 500。） | 判斷依據：**A** 只看 `restaurant_business` 有沒有對應星期的列，沒有＝公休。後果：與 `restaurant_business_parsed` 重複（先過 `parsed`，無該星期列已在前面被擋），實務上永遠回 `false`。**B** 看 `business_hours` 時段。後果：與 `parsed` 幾乎重複，通過 `parsed` 的請求必然 `false`。**C** 依尚未存在的公休日表。後果：要新增表（超出「V3 只建 view／function」），沒有該表之前無法實作。**D** 永遠回 `false`（占位）。後果：「此時段無營業」永遠不觸發，其餘功能不受影響。<br>NULL／不存在：**A 回 1 列 `isclosed = false`**（放行）。後果：不存在的餐廳不會在此被擋（但 `parsed` 已先回 0 列而擋下）。**B 回 `true`**（擋下）。後果：擋下。**丟例外**：API 回 500。 | （低風險，可直接採用建議）判斷依據 **A**，NULL／不存在回 **`false`**。理由：兩者在 `parsed` 先行把關後不會改變實際行為（`middlewares/cart/index.js:90–102`），A 不需要新表；controller 不用改，且保證回 1 列。 | 採用建議（判斷依據 A，NULL／不存在回 `false`） |
| 20 | `restaurant_business_parsed`（待確認 2） | `restaurant_business_parsed` 遇到跨午夜時段（seed 的 `17:00~00:00`，高雄夜市美食攻略的星期五、六）怎麼處理？`BETWEEN start_time AND end_time` 是閉區間且不處理跨午夜。 | **A `00:00` 視為 `24:00`，轉成 `end_time = 23:59:59`**。後果：週五、週六 17:00 到 23:59:59 可預約，`00:00` 之後不可。<br>**B 保持 `00:00:00`**。後果：`start_time > end_time`，`BETWEEN` 永遠不成立，這兩天任何預約都回「餐廳已關閉」。<br>**C 拆成兩列**（`17:00~23:59:59` 與隔日 `00:00~00:00`）。後果：隔日時段要記在下一個 `week`，view 較複雜。 | （低風險，可直接採用建議）**A**。理由：controller 不改，只有 A（與 C）能讓 seed 的週五、週六營業時段可預約；A 最簡單。 | 採用建議（A） |
| 21 | `restaurant_business_parsed`（待確認 1、3） | `restaurant_business_parsed` 的其他邊界：`business_hours` 無法解析（格式不符）的列怎麼辦？沒有 `restaurant` 列的行程呢？ | 無法解析：**A view 忽略該列**。後果：該餐廳該星期視為「已關閉」。**B 丟例外**。後果：整個 view 查詢失敗，所有餐廳加入購物車都回 500。<br>沒有 `restaurant` 列的行程：view 內沒有列，`rowCount === 0`，回「餐廳已關閉」（400）；INNER JOIN 與 LEFT JOIN 結果相同，不需要選擇，只記錄。 | （低風險，可直接採用建議）無法解析採 **A**。理由：B 會讓一筆壞資料拖垮所有餐廳；controller 不用改。 | 採用建議（無法解析採 A） |
| 22 | `user_user_level`（待確認 1、2）、`user_level_review_forHome`（待確認 3）、`user_adminList`（待確認 3、4） | 使用者沒有 `user_level` 列、或有多筆時，`user_user_level`、`user_level_review_forHome`、`user_adminList`（以及 `user_level_point_coupon` 的邊界）怎麼處理？V1 `user_level` 沒有 unique（`V1:39–50`）。 | 沒有列：**A INNER JOIN**。後果：該使用者的評論、隱藏玩法在商品頁消失（`product.js:495,553` 的 `inner JOIN`）、首頁好評消失；`GET /admin/members/:user_id` 回 200 但 `data: []`；`user_level_point_coupon` 中該使用者消失。**B LEFT JOIN**。後果：評論照常顯示，等級欄位為 `null`。<br>多筆：**A 直接 JOIN**。後果：該使用者每筆評論重複（筆數 ＝ 等級列數）；admin 回多列。**B 取最新一筆**（`updated_at` 最大）。後果：不重複，但要定義「最新」。 | （低風險，可直接採用建議）沒有列採 **LEFT JOIN**，多筆採 **B 取最新一筆**。理由：註冊流程一律會建立 `user_level`（`userinfo.js:31,209`），seed 每位使用者各 1 筆，所以在正常資料上四個物件結果相同；LEFT JOIN＋取一筆能保證每位使用者最多一列，不讓缺漏或重複的資料影響評論與管理者頁面。controller 不用改。 | 採用建議（沒有列採 LEFT JOIN，多筆採 B 取最新一筆） |
| 23 | `tour_travel_popular`（待確認 2）、`tour_travel_most_favorited`（待確認 1） | 沒有任何購買（`tour_travel_popular`）或沒有任何人收藏（`tour_travel_most_favorited`）的行程要不要出現？ | **A 出現，排在最後**（`LEFT JOIN`，排行用計數 0 排序）。後果：新 DB 熱門與最多收藏分頁仍有資料。<br>**B 不出現**（`INNER JOIN`）。後果：沒有訂單或收藏時，首頁對應分頁回 200「查無資料」；P1b 的 seed 需要有已付款訂單與收藏紀錄。 | （低風險，可直接採用建議）**A**。理由：controller 對兩個 function 做 `INNER JOIN` 後 `ORDER BY` 排行（`home.js:15,49`），A 不依賴 seed 資料量就有東西可看。 | 採用建議（A） |
| 24 | `tour_travel_popular`（待確認 3）、`tour_travel_most_favorited`（待確認 2） | 排名並列時怎麼處理？（`home.js` 的 `ORDER BY 購買排行 ASC LIMIT/OFFSET` 與 `ORDER BY 收藏排行 ASC LIMIT/OFFSET` 沒有次要排序。） | **A `RANK()`**（並列同名次）。後果：並列時分頁可能重複或漏列。<br>**B `ROW_NUMBER()` 並加次要排序**（`tour_id`）。後果：分頁穩定，並列者的先後由次要排序決定。 | （低風險，可直接採用建議）**B**。理由：controller 沒有次要排序，只有 B 保證分頁穩定；不用改 controller。 | 採用建議（B；次要排序鍵 `tour_id`，2026-10-23 controller 裁決） |
| 25 | `user_orderList`（待確認 4）；另涉及輸出欄位型別（無獨立待確認）：`hotel_booking`、`restaurant_booking`、`tour_travel_popular`、`tour_travel_most_favorited`、`user_level_point_coupon` | 計數類欄位的型別：`user_orderList.total_count`（原待確認 4）、`hotel_booking`／`restaurant_booking` 的 `booking_count`、`購買排行`／`收藏排行`、`使用者旅遊積分`（若用 `SUM`）。`COUNT`／`SUM` 預設是 `bigint`，pg 回字串（§2 共通觀察）。 | **A `integer`**（view／function 內 `::int`）。後果：JSON 是數字；`summary.total_items`（`checkout.js:263`，沒有 `Number()`）是數字。<br>**B `bigint`**。後果：`summary.total_items` 是字串（如 `"1"`）；`booking_count >= room_count` 的比較仍正確（JS 轉數字），但排行欄位在首頁 response 是字串。 | （低風險，可直接採用建議）**A**。理由：controller 對 `total_count`、`使用者旅遊積分` 沒有 `Number()`（`checkout.js:263`、`discounts.js:60`、`userProfile.js:148`），只有數字型別不用改。若採用，Step 4 要同步更新五處：§1 `tour_travel_popular`、`tour_travel_most_favorited` 簽章的 `bigint`（推測）、§2 `hotel_booking`、`restaurant_booking` 的 `booking_count` 型別格（「integer 或 bigint」）、§2 `user_orderList` 的 `total_count` 型別格（「integer 或 bigint」）。 | 採用建議（A） |
| 26 | `tour_base`（待確認 3）、`tour_travel`（待確認 2） | `tour_base` 與 `tour_travel` 的欄位集合是否相同（只差 `收藏狀態`）？`旅遊標語`、`旅遊結束日期`、`旅遊天數`、`旅遊代表圖 Url`、`異動通知內容` 是否也在 `tour_base`？ | **A 相同**（`tour_travel` ＝ `tour_base` ＋ `收藏狀態`）。後果：登入與未登入首頁 response 結構只差 `收藏狀態`。<br>**B `tour_base` 只含目前表格列的欄位**。後果：登入與未登入首頁 response 欄位不同，前端要處理兩種形狀。 | （低風險，可直接採用建議）**A**。理由：兩條路徑共用同一個 JS 轉換（`home.js:90–96`），A 讓 response 形狀一致，不用改 controller。 | 採用建議（A；`異動通知內容` 納入 `tour_base` 與 `tour_travel`，2026-10-23 controller 裁決） |
| 27 | `tour_travel`（待確認 1） | `tour_travel` 名稱是 travel，但被用在所有種類（旅行團 travel、背包客 hotel／food／spot），要不要只回 `item='travel'`？ | **A 回傳所有種類**。後果：商品搜尋與首頁背包客（已登入）正常。<br>**B 只回 `item='travel'`**。後果：`GET /user/product/search?type=backpacker` 與已登入首頁背包客永遠為空，但未登入路徑（`tour_base`）仍有資料，兩者不一致。 | （低風險，可直接採用建議）**A**。理由：`product.js:116` 沒有小分類限制，`home.js:77` 在 `type=backpacker` 也呼叫它。 | 採用建議（A） |
| 28 | `tour_travel`（待確認 3）、`tour_tour_detail`（待確認 4） | 未登入（`NULL` 參數）時 `收藏狀態` 是 `false` 還是 `NULL`？（`tour_travel`、`tour_tour_detail`、`tour_hotel`、`tour_restaurant` 同。） | **A `false`**。後果：前端 `is_favorited` 一律布林。<br>**B `NULL`**。後果：JSON 內是 `null`，布林判斷結果相同，但嚴格比較（`=== false`）的測試會失敗。 | （低風險，可直接採用建議）**A**。理由：`EXISTS (...)` 自然得到 `false`；`product.js:356` 直接輸出為 `is_favorited`，不用改。 | 採用建議（A） |
| 29 | `tour_base`（待確認 5） | `tour_base` 的 `建立時間`、`更新時間` 來自 `tour` 還是 `notification`？（`promotion.js:44` 用 `ORDER BY 更新時間`、`:23` 用 `DATE(建立時間)`；`admin.js:168`、`product.js:1067` 用 `建立時間`。） | **A 兩者都來自 `tour`**。後果：促銷清單依行程本身的更新時間排序，建立日期篩選是行程建立日。<br>**B 兩者都來自 `notification`**。後果：促銷清單依促銷最近修改排序；但無通知的行程 `建立時間` 為 `NULL`，管理者商品清單的排序與篩選失效。<br>**C `建立時間` 取 `tour.created_at`，`更新時間` 取 `GREATEST(tour.updated_at, notification.updated_at)`**。後果：促銷清單排序反映促銷異動，商品清單不受影響；需確認這是否合理。 | （低風險，可直接採用建議）**A**。理由：B 會破壞管理者清單，A 最單純，controller 不用改；若希望促銷清單依促銷異動排序，再改採 C。 | 採用建議（A） |
| 30 | `tour_tour_detail`（待確認 2） | `tour_tour_detail` 對 `tour_detail` 用 INNER 還是 LEFT JOIN？（`spot` 也用此 function 並讀特色圖，`product.js:335`；`spot` 行程不保證有 `tour_detail` 列。） | **A INNER JOIN**。後果：每個 spot 都必須有 `tour_detail`，否則整列消失，`product.js:209` 讀 `rows[0]` 時 TypeError，詳情頁 500；seed 與新增商品流程要補。<br>**B LEFT JOIN**。後果：沒有 `tour_detail` 時特色圖、行程規劃為 `NULL`，頁面可顯示。 | （低風險，可直接採用建議）**B**。理由：controller 不改的前提下，B 不會 500。 | 採用建議（B） |
| 31 | `tour_hotel`（待確認 1） | `tour_hotel` 的 `房型描述` 沒有明確來源（`hotel_room` 只有 `image_desc`）。 | **A `房型描述 = hotel_room.image_desc`**。後果：房型描述就是圖片說明文字。<br>**B 新增 `hotel_room.description`**。後果：超出「V3 只建 view／function」，要改 migration。 | （低風險，可直接採用建議）**A**。理由：`product.js:411` 讀 `房型描述`，A 不需要 migration，controller 不用改。 | 採用建議（A） |
| 32 | `tour_hotel`（待確認 2） | `hotel` 有 6 個描述欄位（`facility_desc`、`food_desc`、`room_desc`、`leisure_desc`、`traffic_desc`、`other_desc`，`V1:172–177`），controller 只讀 5 個（`product.js:416–436`，最後一個是 `其他便利服務`）。`其他便利服務` 取哪個？ | **A `other_desc`**。後果：`leisure_desc` 的資料不會在 API 顯示。<br>**B `leisure_desc`**。後果：`other_desc` 的資料不會顯示。<br>**C 兩者串接**。後果：兩者都能顯示，但要定分隔格式。 | **A**。理由：controller 的標籤是「其他便利服務」，與 `other_desc` 對應，沒有任何標籤對應「休閒」；controller 不用改。這是依名稱的推測。 | 採用建議（A） |
| 33 | `tour_hotel`（待確認 3）、`tour_restaurant`（待確認 2） | `tour_hotel` 沒有房型、`tour_restaurant` 沒有菜單或沒有營業時間時，行程要不要出現？ | **A INNER JOIN**。後果：飯店或餐廳整個消失，`product.js:209` 讀 `rows[0]` 時 TypeError，詳情頁 500。<br>**B LEFT JOIN**。後果：出現一列，房型／菜單／營業時間欄位為 `NULL`，response 的 `room[]`、`menu[]`、`opening[]` 內是欄位全為 `null` 的物件，頁面不會 500。 | （低風險，可直接採用建議）**B**。理由：controller 不改的前提下，B 不會 500。 | 採用建議（B） |
| 34 | `tour_restaurant`（待確認 1） | `tour_restaurant` 的 `menu[]` 與 `opening[]` 共用 `rows`（`product.js:263`、`:268`），列要怎麼展開？ | **A 菜單與營業時間 CROSS JOIN**。後果：兩個陣列各有大量重複項（3 道菜 × 7 天 ＝ 21 列，`menu[]` 與 `opening[]` 各 21 項）。<br>**B `UNION ALL`／位置對齊**。後果：每列各帶一筆菜單或一筆營業時間，另一邊為 `NULL`，陣列內有 `name: null` 或 `week: null` 的空項，但沒有重複（3 ＋ 7 ＝ 10 列）。<br>**C 每個餐廳一列，菜單與營業時間聚合成 JSON**。後果：`row.菜單名稱` 會是陣列，與 `rows.map` 的用法不符，controller 不改就無法使用。 | **B**。沒有任何選項能不改 controller 就完全正確：A 資料齊全但大量重複，B 沒有重複但有空項，C 需要改 controller。B 的瑕疵最小（空項是欄位為 `null` 的物件，不會丟例外）；完整修正需改 controller（P3 商品；已於 P3 Task 4 修正：餐廳菜單與營業時間去空項）。 | 採用建議（B） |
| 35 | `user_cartList`（待確認 3） | `user_cartList` 要不要多帶 `cart_item_id`？（`DELETE`／`PATCH /:cart_item_id` 需要它，但 `GET /list` 的 response 沒有輸出，`cart.js:209–225`。） | **A 帶**。後果：目前 response 不變（controller 不讀）；日後 controller 加上即可讓前端刪除與修改項目。<br>**B 不帶**。後果：前端目前拿不到 `cart_item_id` 的狀況不變，之後要加得改 view。 | （低風險，可直接採用建議）**A**。理由：對現有 API 沒有影響，且為 P4 交易保留。 | 採用建議（A） |
| 36 | `user_couponList`（待確認 2） | `user_couponList` 要不要同時提供 `expired_date`（多了 d）？`middlewares/discounts/index.js:65`、`middlewares/checkout/index.js:136` 讀 `expire_date`，`controllers/discounts.js:34` 讀 `expired_date`。 | **A 只提供 `expire_date`**。後果：`POST /user/trade/discounts/:order_id` 的 response 少了 `date_period`（`JSON.stringify` 略過 `undefined`），前端若依賴會顯示空白。<br>**B 兩個都提供（同值）**。後果：response 有 `date_period`；admin API（`SELECT *`，`admin.js:239`）多一個重複欄位。<br>（只提供 `expired_date` 不可行：`new Date(undefined)` 讓過期檢查被靜默略過。） | （低風險，可直接採用建議）**B**。理由：只有 B 讓三處讀取都不用改 controller。 | 採用建議（B） |
| 37 | `user_couponList`（待確認 3） | `user_couponList` 的 `status = -1`（預覽中占用，只由 `checkout.js:149` 寫入）要不要原樣輸出？ | **A 原樣輸出**。後果：管理者 API 看到 -1。<br>**B view 把 -1 換算成別的顯示值**。後果：`checkout.js:216` 的 `status = -1` 失效，結帳摘要看不到已套用的優惠卷。 | （低風險，可直接採用建議）**A**。理由：`checkout.js:216` 依賴 -1；controller 不用改。 | 採用建議（A） |
| 38 | `user_couponList`（待確認 4） | 同一個 (使用者, `code`) 有多筆綁定時怎麼辦？V1 有 `UNIQUE (user_id, coupon_id)`（V1 `:420`）但 `coupon.code` 不 unique；`middlewares/discounts/index.js:41`、`controllers/discounts.js:14` 取 `rows[0]`。 | **A 不處理**。後果：取到哪張不固定；view 維持每個 `user_coupon` 一列，管理者 API（`admin.js:239`）列出全部綁定。<br>**B view 只取最新一筆**。後果：結果固定，但管理者 API 看不到其他綁定；要另定「最新」的規則。 | **A**（不屬低風險：兩張 `discount` 不同的優惠卷共用同一 `code` 時，`rows[0]` 決定計價用哪個折扣，影響金額；但需要管理者建立重複代碼才會發生，機率低）。理由：重複 `code` 的根源是建立優惠卷時沒有檢查唯一，在 view 裡藏掉會隱瞞資料；根本修正見 §4.2 (d4)。controller 不用改。 | 採用建議（A） |
| 39 | `user_level_point_coupon`（待確認 3） | `user_level_point_coupon` 只列出可用的優惠卷（`status = 0` 且未過期），還是全部綁定？（`userProfile.js:153` 把每一列都放進 `coupon[]`，view 輸出沒有 `status` 欄位可供判斷。） | **A 列出全部綁定**。後果：`coupon[]` 含已使用（1）與占用中（-1）的優惠卷，前端無法區分；seed 使用者 bob、alice 的優惠卷都是 `status = 1`，會全部顯示。<br>**B 只列 `status = 0` 且未過期**。後果：`coupon[]` 只含可用的優惠卷；沒有可用優惠卷的使用者要靠 LEFT JOIN 才不會消失（見 #40）。<br>**C 排除 `status = 1`，保留 -1**。後果：占用中的優惠卷仍顯示為可用。 | **B**。理由：`coupon[]` 沒有 `status` 欄位，前端無法自行篩選，列出不可用的優惠卷是錯誤顯示；折抵檢查只讀 `rows[0].使用者旅遊積分`（`middlewares/discounts/index.js:77`、`middlewares/checkout/index.js:148`），不受影響。代價：必須同時採 #40 的 LEFT JOIN。 | 採用建議（B） |
| 40 | `user_level_point_coupon`（待確認 4） | `user_level_point_coupon` 對優惠卷用 LEFT 還是 INNER JOIN（沒有優惠卷的使用者是否保留一列）？ | **A LEFT JOIN**。後果：使用者得到 1 列、優惠卷欄位全為 `NULL`；`userProfile.js:153–159` 沒有檢查，`coupon` 會是 `[{coupon_id: null, code: null, ...}]`。<br>**B INNER JOIN**。後果：沒有優惠卷的使用者完全不在 view 內，`GET /pointslevel` 回 `[]`，而且 `middlewares/discounts/index.js:81–89`、`middlewares/checkout/index.js:152–160` 的 `pointRepo.rowCount === 0` 回 409「查無可使用的點數」，即使使用者有積分也無法折抵。 | **A**。理由：B 會讓沒有優惠卷的使用者無法使用點數折抵；A 的瑕疵（`coupon[]` 含全 `null` 物件）只是顯示問題，controller 補 `if` 即可（P5 會員中心）。 | 採用建議（A） |
| 41 | `user_favorite`（待確認 4）、`user_orders`（待確認 6） | 下架行程（`tour.status = 2`）的收藏（`user_favorite`）與購買紀錄（`user_orders`、`user_order_item`）要不要出現？ | **A 出現**（view 對 `tour` 或「含全部」的 `tour_base` JOIN）。後果：使用者看得到已下架的收藏與購買紀錄；點進商品詳情的行為由 `tour_tour_detail` 決定。<br>**B 不出現**（對「只含上架」的 `tour_base` JOIN）。後果：收藏列仍在 `favorite` 表但清單看不到，無法由列表取消這筆收藏（`DELETE` 需要 `favorite_id`，`collection.js:100`）；購買紀錄消失。 | （低風險，可直接採用建議）**A**。理由：B 會讓使用者無法取消收藏、看不到買過的東西；與 #7 的建議（`tour_base` 含全部）一致，controller 不用改。 | 採用建議（A） |
| 42 | `user_favorite`（待確認 3）、`user_orders`（待確認 3）、`user_order_item`（待確認 3） | `user_favorite`、`user_orders`、`user_order_item` 的 `偏好分類 1/2/3`（`user_order_item` 為英文 `preference1/2/3`）是行程的偏好還是使用者的偏好？ | **A `tour.preference1/2/3`**。後果：每筆收藏／購買顯示該行程自己的分類標籤；與 `tour_base` 同名欄位一致。<br>**B `user.preference1/2/3`**。後果：同一位使用者所有列的偏好完全相同，對清單沒有意義。 | （低風險，可直接採用建議）**A**。理由：使用者的偏好在 §2 叫 `個人偏好 1/2/3`，`偏好分類` 的命名與 `tour_base` 相同；controller 只轉換數字，不用改。 | 採用建議（A） |
| 43 | `user_favorite`（待確認 2） | `user_favorite` 的 `建立時間` 是收藏時間還是行程建立時間？（`collection.js:15` 的 `ORDER BY 建立時間 DESC`。） | **A `favorite.created_at`**。後果：最近收藏的排最前面；來源檔 seed 7 筆時間相同（皆 `CURRENT_TIMESTAMP`），同一使用者內順序不穩定；P1b 之後 9 筆時間都不同。<br>**B `tour.created_at`**。後果：排序與收藏無關，取消後重新收藏不會改變位置。 | （低風險，可直接採用建議）**A**。理由：符合「使用者查看收藏項目」的語意；controller 不用改。seed 時間相同的問題由 P1b 調整 seed。 | 採用建議（A） |
| 44 | `user_orders`（待確認 1） | `user_orders` 一列的粒度：每個 `order_item` 一列，還是每張 `orders` 一列？ | **A 每個 `order_item` 一列**（含 `order_item_id`）。後果：每列可接到明細 API；一張訂單多個項目會是多列（但 `checkout.js:20–33,42–56` 目前每張訂單只產生 1 個項目）。<br>**B 每張訂單一列**（彙總）。後果：沒有 `order_item_id`，前端無法呼叫明細 API（`routes/purchases.js:14–20`）。 | （低風險，可直接採用建議）**A**。理由：明細 API 需要 `order_item_id`。 | 採用建議（A） |
| 45 | `user_orders`（待確認 5） | `user_orders` 要不要在 view 內排序？（`purchases.js:9–11` 沒有 `ORDER BY`、沒有 `LIMIT`。） | **A view 內含 `ORDER BY`**（依 `orders.created_at` 由新到舊，V1:280）。後果：順序穩定，但 PostgreSQL 不保證 view 內的 `ORDER BY` 被外層保留（單純 `SELECT *` 加 `WHERE` 通常會保留，加了 JOIN 或排序就不一定）。<br>**B 不排序**。後果：順序不穩定，重新整理可能不同。 | （低風險，可直接採用建議）**A**。理由：controller 沒有排序，A 至少在常見查詢下穩定；controller 不用改。 | 採用建議（A；排序鍵 `orders.created_at DESC`，2026-10-23 controller 裁決） |
| 46 | `user_order_item`（待確認 2） | `user_order_item` 一個 `order_item_id` 回幾列？（controller 一律 `rows.map` 成陣列，`purchases.js:63` 起。） | **A 恰好 1 列**（只 JOIN 一對一的 `order_item`、`orders`、`tour`）。後果：`body.data` 是長度 1 的陣列。<br>**B JOIN 一對多的表**（例如 `tour_detail`、`restaurant_menu`、`hotel_room`）。後果：一個項目多列，每個元素重複訂單資料。 | （低風險，可直接採用建議）**A**。理由：明細是單一項目；controller 不用改。 | 採用建議（A） |
| 47 | `user_order_item`（待確認 4） | `user_order_item` 明細帶入哪些訂單資料？（與 §4.2 (c) 的擁有者檢查有關。） | **A 只有 `order_item` 加 `tour`**。後果：明細頁沒有地址與電話；別人的 `order_item_id` 被讀到時洩漏較少。<br>**B 再帶入 `orders`**（地址、電話、付款方式、折扣類型、訂單總額）。後果：明細完整，但沒有擁有者檢查時（`middlewares/purchases/index.js:31`、`controllers/purchases.js:59`）會把別人的地址與電話暴露。<br>**C 再帶入 `payment`**（`V1:308–325`）。後果：可顯示付款結果，但一張訂單可能有多筆付款紀錄（失敗重試），可能產生多列，與 #46 的 B 相同。 | **A，並多帶 `使用者編號`（`orders.user_id`）**。理由：controller 不讀這些欄位，任何選項都不用改；A 在擁有者檢查補上之前洩漏最少，多帶 `使用者編號` 讓日後可在 controller 補 `WHERE 使用者編號 = $2`。若日後 P3–P6 接前端時發現明細頁需要地址與電話，改採 B（依 spec 重構規則，view、契約與契約測試一起改），且要先處理 §4.2 (c)。 | 採用建議（A，並多帶 `使用者編號`） |
| 48 | `user_level_review_forHome`（待確認 2） | `user_level_review_forHome`（首頁好評）要篩選哪些評論？（V1 `review.type` 可為 web／travel／hotel／food／spot；路由註解「使用者查看此網頁好評內容」。） | **A 只含 `review.type = 'web'`**。後果：首頁只顯示網站整體好評；seed 有 5 則 web 評論（來源檔 2 則，P1b 加 3 則，見 §0.1 第 11 項）。<br>**B 含所有 `review`**。後果：行程評論也出現在首頁。<br>**C 只含評分達標**（例如 `rating >= 4`）。後果：要另定門檻；低分評論不出現。 | **A**。理由：controller 不篩選（`home.js:132`），篩選條件只能寫在 view；A 與路由註解、V1 的 `type` 註解相符。這是依名稱與註解的推測。 | 採用建議（A） |
| 49 | `user_adminList`（待確認 2） | `user_adminList` 的偏好欄位輸出數字還是文字？（`admin.js` 沒有像 `collection.js`／`purchases.js` 使用 `reversePreferenceMap`。） | **A `smallint` 數字**（`個人偏好 1/2/3`）。後果：管理者頁面拿到 1～10，要自己對照文字。<br>**B view 內轉成文字**。後果：對照表要放進 view（SQL `CASE`），且與其他 view 的型別不一致。 | （低風險，可直接採用建議）**A**。理由：與 `user_level_point_coupon` 的 `個人偏好 1/2/3` 一致，controller 不用改。 | 採用建議（A） |

### 4.2 契約以外、需要使用者決定的事項

這些事項是做契約時發現的，不是 view／function 的語意。建議欄的依據同 §4.1：以 controller 不用改為準，並附程式碼。

| # | 事項 | 選項與後果 | 建議 | 使用者的決定 |
|---|---|---|---|---|
| a | **seed 主鍵不是 uuidv4，seed 走不通部分 API。** 來源檔 seed 的 `tour`（10 筆）、`coupon`（5 筆）主鍵，以及 3 位 seed `user`（版本位 7、9、a）都是手寫值，不是 v4。購物車、結帳、折扣、已購買的驗證器只接受 v4（`utils/Validator/cart_Validator.js:84,92`、`checkout_Vaildator.js:4,12,71`、`discounts_Validatior.js:29`、`purchases_Validator.js:8`），`admin_Validator.js:8–15` 只接受 v4／v5。**2026-10-23 final review 補列**其他只接受 v4 的驗證器：`utils/Validator/product_Validator.js:156`（`tourIDSchema`；公開 `GET /user/product/search/:tour_id`、`/:tour_id/reviews`、`/:tour_id/hidden-shares` 經 `middlewares/product/index.js:135,165,196` 使用）、`other_Validator.js:5`（`country_id`；`GET /web/filter/:country_id/region`）、`promotion_Validator.js:7,9`（`tour_ids`；admin 促銷）、`coupon_Validator.js:6–20,28,57`（`coupon_ids`、`user_ids`、`user_id`、`coupon_id`；admin 優惠卷）。來源檔 seed 的 `country` 主鍵（37 筆）也全部不是 v4。後果：`GET /user/product/search/:tour_id`、`/reviews`、`/hidden-shares` 對**每個** seed 行程回 400（所以 seed 行程的詳情頁完全打不開）；`GET /web/filter/:country_id/region` 對每個 seed 國家回 400；`POST /user/trade/cart/:tour_id` 對任何 seed 行程回 400；`PATCH /user/checkout/preview/:order_id` 帶 seed 的 `coupon_id` 回 400；`GET /admin/members/:user_id`、`PATCH /admin/members/roles`、`GET /admin/members/list/:user_id` 對 seed 使用者回 400。詳見 §2 B 組共通觀察「UUID 版本檢查」與 §3 C 組共通觀察「UUID 版本檢查補充」。 | **A 把 seed 的 `tour`、`coupon`、`user`、`country` 主鍵改寫成 v4**（連同所有引用它們的外鍵，含 `region.country_id`，V1:231–234；V1 中只有這一欄引用 `country_id`；P1b）。後果：seed 能走通購物車、結帳、折扣與管理者會員 API；要同時改寫引用這些主鍵的所有資料列，契約內引用的 seed 識別值與行號也要隨之更新（已改用 `code`／`email`／`title` 錨點）。<br>**B 放寬驗證器**（`utils/Validator`，P2 以後）。後果：seed 不用動；但這是 controller 以外的程式碼修改（P1a 不允許），會放寬輸入驗證，原記為要改 5 個驗證器檔案、共 8 處；2026-10-23 補列後為 9 個檔案（另含 `product_Validator.js:156`、`other_Validator.js:5`、`promotion_Validator.js:7,9`、`coupon_Validator.js:6–20,28,57`）。 | **A**。理由：驗證器與 controller 都不用改；seed 本來就是 P1b 要補資料的對象。代價：P1b 的 seed 改寫工作量較大（外鍵多）。 | 採用建議（A）；**2026-10-23 使用者決定擴大範圍**：A 同時改寫 `country` 主鍵與 `region.country_id` 外鍵（以及任何引用 country id 的欄位；V1 中只有 `region.country_id`），驗證器清單以上面的補列為準。新 id 必須是 **v4**（`admin_Validator` 接受 v5，其餘驗證器不接受，所以不能用 uuid5 直出）；產生方式與既有 volume 的處理見 §0.1 |
| b | **權限提升：任何已登入帳號都能把任何註冊帳號改成 admin。** `routes/admin.js:26` 的 `authRole('admin')` 被註解掉，`PATCH /api/v1/admin/members/roles` 只剩 `auth`；`controllers/admin.js:59` 原樣 UPDATE `user.role`。被提權者重新登入後 JWT 帶 `admin`（`controllers/userinfo.js:105`），通過所有 `authRole('admin')` 閘門。詳見 §3 C 組共通觀察「安全問題」。spec 4 節已把它列在 P2 的已知 bug。（P2 已修：P2 Task 1 已取消 `routes/admin.js:26` 的註解並加上 `authRole('admin')`，非 admin 呼叫回 403；`controllers/admin.js:57-58` 寫入前把 `user` 正規化成 `User`；本欄原文與下方「建議」「使用者的決定」兩欄保留作 P1 當時的歷史紀錄。） | **A 在任何公開展示之前先修**（取消 `routes/admin.js:26` 的註解，一行；要走紅燈／綠燈兩個 commit）。後果：漏洞關閉；這是 P1a 計畫之外的檔案修改，需要使用者同意。<br>**B 照 P2 計畫處理**。後果：在 P2 完成前，任何能連到服務的註冊帳號都能取得 admin 權限；計畫規定 seed 會在本機與展示環境載入（計畫 Global Constraints），所以只有在 P2 前不對外開放時才安全。 | **B，但加一條規則：P2 完成前不對外開放**。理由：spec 已把它排進 P2，P1 不改 route 以外的行為；若 P2 前就要公開展示，改採 A。 | 採用建議（B，P2 完成前不對外開放） |
| c | **已購買明細的擁有者檢查（IDOR）：任何登入的 `User` 都能讀任何 `order_item`。** 只有明細端點受影響：`GET /api/v1/user/purchases/info/:order_item_id` 的 `middlewares/purchases/index.js:31` 與 `controllers/purchases.js:59` 都只用 `order_item_id` 查，沒有 `user_id` 條件（清單端點 `GET /purchases/info` 以 `使用者編號 = req.user.id` 限定，`controllers/purchases.js:9–11`，不受影響）。另一個保護的缺口：`middlewares/purchases/index.js:34` 的 404 永遠不會觸發。後果：若明細 view 帶入 `orders` 的地址與電話（#47），別人的資料會被讀到。spec 4 節的 P2 已知 bug 清單沒有這一項。 | **A 在任何公開展示之前先修**（兩處查詢加 `user_id` 條件，`user_order_item` view 要提供 `使用者編號`，見 #47）。後果：漏洞關閉；這是 controller 修改（P1 不允許），要有紅燈測試。<br>**B 排進 P5 會員中心**（訂單功能）。後果：P5 完成前，知道或猜到 `order_item_id` 的登入使用者可讀到他人訂單明細；`order_item_id` 是 uuid，不易猜，但 seed 的識別值公開在契約與 seed 裡。 | **B，P5 要列為獨立 Task 並先寫紅燈測試；P5 完成前不對外開放**。理由：同 (b)，P1 不改 controller；同時依 #47 的建議讓 view 帶 `使用者編號`，P5 修起來不必動 view。若 P5 前要公開展示，改採 A。 | 採用建議（B，P5 列為獨立 Task 並先寫紅燈測試；P5 完成前不對外開放）<br>**已修正（P5 Task 3，backend `46c3d2b`）**：擁有者條件寫在 SQL（middleware 查 `order_item JOIN orders ... AND o.user_id = $2`，controller 對 `user_order_item` 加 `AND 使用者編號 = $2`），非本人或不存在回 404 `查無此訂單項目`，`:34` 的 404 改判 `rowCount === 0`；本人未付款維持 200 `查無資料`。 |
| d1 | **frontend 欄位核對（前面延後的檢查）。** #11 列出的 view 沒有 controller 證據，要靠 frontend `phase-0` 實際讀取的 key 才能確定欄位與命名。P1a 不動 frontend，但讀取不受限。 | **A 在 P1b 寫 V3 SQL 之前，唯讀地 grep frontend `phase-0` 讀取的 key**，回填契約。後果：多一個小步驟；欄位與命名有證據，不必事後重做 view 與契約測試（spec 重構規則要求動到 view 時同步更新契約與契約測試）。<br>**B 不核對，照契約推測建**，等 P3–P6 各功能做到時再修。後果：每個推測錯誤都要改 view、契約與契約測試。 | **A**。理由：唯讀、成本小，且是 #11 的前置。 | 採用建議（A）；**2026-10-23 已完成，結果是沒有證據可回填**：frontend `phase-0`（`e3ad994`）只呼叫 `/auth/userinfo` 與 `/user/userinfo`（`frontend/src/utils/api.js:7,9`），`frontend/src/views/HomeView.vue:410` 的 `reviews` 是寫死的陣列，沒有任何程式讀取 `/user/collection`、`/user/purchases`、`/admin/members`、`/user/home/search/reviews`（以 `git -C frontend show phase-0:src/utils/api.js`、`git -C frontend show phase-0:src/views/HomeView.vue`、`git -C frontend grep phase-0 -- src` 驗證）。依 #11 的使用者決定改採 fallback（採用契約推測欄位表為定案） |
| d2 | **seed 的優惠卷代碼不符合驗證器。** `utils/Validator/discounts_Validatior.js:9–13` 要求 `discount.coupon` 為 `^[A-Z0-9]{6}$`；來源檔 seed 的 5 個 `code` 只有 `VIP300` 符合，`WELCOME100`、`SUMMER50`、`TRAVEL10P`、`SPRING20` 會被 `POST /user/trade/discounts/:order_id` 以 400 擋下。 | **A 把 seed 代碼改成 6 碼大寫英數**（P1b）。後果：seed 全部可用；`description` 與代碼需一起檢查。<br>**B 放寬驗證器的 regex**。後果：seed 不用動，但要改 `utils/Validator`（P1a 不允許）。 | **A**。理由：不用動驗證器與 controller，並與 (a) 的 seed 重寫一起做。 | 採用建議（A） |
| d3 | **seed 每位使用者有 2 個購物車，與 controller 衝突。** `controllers/cart.js:47–50` 的 `UPDATE public."cart" ... WHERE user_id = $1` 沒有限定 `cart_id`，會更新該使用者的所有購物車；來源檔 seed 每人 2 個（P1b 之後每人 1 個），加入購物車會同時改兩個購物車的 `total_price`（見 §2 `user_cartList` 邊界 controller 行為 2）。V1 `cart` 沒有 `user_id` unique。 | **A seed 改成每位使用者 1 個購物車**（P1b）。後果：controller 不用改就一致；`cart` 的 seed 筆數與引用它的 `cart_item` 要調整。<br>**B 保留 2 個**。後果：對 seed 使用者加入購物車會同時改兩個購物車的 `total_price`，結果依 `rows[0]` 與全部更新而不一致；日後 P4 修 controller 才會好。 | **A**。理由：controller 不用改，只動 seed。 | 採用建議（A） |
| d4 | **是否補唯一約束。** 多題待確認的根源是 V1 缺少 unique：`notification`（一個行程多筆通知，#8）、`user_level`（一位使用者多筆，#22）、`favorite`（重複收藏，`V1:382–390` 沒有 `UNIQUE (user_id, tour_id)`，只靠 `middlewares/collection/index.js:68–70` 先查再寫）、`coupon.code`（#38）。 | **A 不補（V3 只建 view／function）**。後果：重複資料由 view 的規則處理（#8、#22），並行收藏仍可能寫入重複列。<br>**B 補唯一約束**（新增 migration）。後果：從根源消除重複，但動到 V1 的表結構，既有重複資料要先清理，範圍超出 P1a 與「V3 只建 view／function」。 | **A**。理由：controller 與現有流程都不需要約束就能運作，約束屬功能階段（P5 收藏、P6 優惠卷）的設計；P1b 不擴大範圍。 | 採用建議（A）<br>**P5 已加（V6）**：`favorite (user_id, tour_id)`。原因：重複收藏要回原 id，並行收藏只留一筆，由 DB 擋住而不是靠先查再寫。其餘 d4 項目（`coupon.code` 等）未動。 |
| e | **`tour_hotel`、`tour_restaurant` 也只回 `status = 1`，#7 沒有涵蓋這兩個。** #7 只點名 `tour_travel`、`tour_travel_popular`、`tour_travel_most_favorited`、`tour_tour_detail`；Task 4 的 SQL 讓這兩個 function 也過濾 `status = 1`（與 `tour_tour_detail` 一致）。 | **A 過濾**（現狀）：API 行為與不過濾相同，因為 `product.js:178–183` 已先以 `status = 1` 過濾。**B 不過濾**：未來呼叫端可取得下架行程資料。 | **A**。API 行為相同，與其餘詳情 function 一致。 | 採用建議（A）（2026-11-01 使用者決定） |
| f | **`tour_hotel`、`tour_restaurant` 對 `hotel`／`restaurant` 用 INNER JOIN，且 `tour_id` 沒有 unique 約束。** 契約只定了房型、菜單、營業時間的 LEFT JOIN（#33）。`item = 'hotel'`／`'food'` 的行程若沒有對應的 `hotel`／`restaurant` 列，function 回 0 列，`product.js:209` 丟 TypeError 回 500；若同一 `tour_id` 有多列，`room[]`／`menu[]` 會重複。seed 目前兩者都沒有這種情況。**補充（Task 5 review）**：`restaurant_booking` 也有同樣的問題——同一行程有 N 家餐廳時回 N 列，而 controller 只讀 `rows[0]`；處理方式併入本列的 A／C。 | **A 維持 INNER JOIN，視為已接受的風險**（P1 不改）。**B 改 LEFT JOIN**：行程欄位仍可顯示、飯店／餐廳欄位為 NULL；**C 補 `UNIQUE (tour_id)`**（同 d4，需改 migration）。 | **A**，記錄為已接受風險；是否補 unique 併入 d4。 | 採用建議（A）（2026-11-01 使用者決定） |
| g | **促銷期間用 `now()` 比對沒有時區的 `timestamp`。** DB session 是 `Etc/UTC`，seed 的促銷 `end_date` 是 `23:59:59` 的 naive 值，原意應是台北時間，所以促銷在台北時間隔天 07:59:59 才結束。view 與 `cart.js:22`、`checkout.js:31` 用同一個 `now() between` 運算式，彼此一致。**補充（Task 5 review）**：`user_level_point_coupon` 的 `coupon.expire_date >= now()`（#39「未過期」）有同樣的 session 時區依賴：`expire_date` 是 naive `timestamp`，與 UTC 的 `now()` 比較。 | **A 維持現狀**（view 與 controller 一致）。**B 把 DB／連線時區設成 `Asia/Taipei`**，或改用 `timestamptz` 欄位（需新增 migration 改欄位型別）。 | **A**，P1 不處理；要精確到小時再於 P4 交易階段一併決定。 | 採用建議（A）（2026-11-01 使用者決定） |
| h | **B 組 function／view 中契約沒有明說、Task 5 照現狀實作的四項，加上日期精度。** (1) `hotel_booking.booking_count` 數 `order_item` 列數，不加總 `quantity`（#5 只說「數」；#15 只對餐廳定了人數加總，hotel 的 `quantity` 是人數）。(2) `order_item.end_date` 為 `NULL` 的列不計入（V1 允許 NULL；半開區間比較結果為 NULL）。(3) 同一行程同房型名稱有多個 `hotel_room` 時，`room_count` 是各列加總。(4) `user_level_point_coupon` 的 `expire_date = now()` 仍算未過期（controller 以 `now > expire_date` 判斷過期）。(5) `hotel_booking` 的區間以 timestamp 精度比較；#17 提到「是否取到日期精度也要定」，未明確回答。 | **A 維持現狀**（列數；NULL `end_date` 不計；`room_count` 加總；到期時刻本身未過期；timestamp 精度）。**B** 分別改成 `SUM(quantity)`；NULL `end_date` 視為占一晚（或入住當日）；只取一列 `hotel_room`；`expire_date > now()`；比較前轉 `::date`（同日退房入住的判斷不受時分影響）。 | **A**，與 controller 現行比較方式一致；若 P4 訂單寫入 hotel 的 `quantity` 改為間數，(1) 要改成 B。 | 採用建議（A，(1)–(5) 全部維持現狀）（2026-11-01 使用者決定）；P4 若讓 hotel 的 `quantity` 改存間數，(1) 要改成 `SUM(quantity)` |
| i | **`restaurant_business_parsed` 不接受 `24:00`，也不處理「跨午夜但不是 00:00 結束」的時段。** #20 只定了 `00:00` 視為 `24:00`（→ `23:59:59`）。目前 `24:00` 不符合解析格式而被忽略（#21），`18:00~02:00` 解析成 `start_time > end_time`，`BETWEEN` 永遠不成立。 | **A 維持現狀**：這類時段實質上等於當天不營業；seed 沒有這種資料。**B** 把 `24:00` 也轉成 `23:59:59`。**C** 跨午夜時段拆成當天 `start~23:59:59` 與隔天 `00:00~end` 兩列（隔天記在下一個 `week`，同 #20 解讀 C）。 | **A**，P1 不處理；要支援再與 #20 一併決定。 | 採用建議（A）（2026-11-01 使用者決定） |

#### 契約已記錄、不需決定的問題（供 P2 以後排程）

下列問題屬 controller／validator／route，P1 不改，各物件已詳述，這裡只彙整；是否排入哪個階段由計畫決定，不是本表的決定項。

- 首頁沒帶 `type`（或 `type=tourgroup` 沒帶 `item`）時整個回 500：`middlewares/home/index.js:7` 的 default 沒寫回 `req.query`，`home.js:86` 對 `''` 讀 `.rows`（§1 `tour_base` 邊界）。
- 詳情頁找不到行程、已下架或 type／item 不在對照表時回 500，不是 404（`product.js:178–202`）；function 回 0 列時 `product.js:209` 先 TypeError（§1 `tour_tour_detail` 邊界）。（P3 已修：P3 Task 4 起找不到或已下架回 404 `查無此旅遊項目`；本條原文保留作歷史紀錄。）
- 隱藏玩法 `GET /api/v1/user/product/search/:tour_id/hidden-shares` 的回應永遠沒有 `title`（P1b Task 7 冒煙測試發現）：`controllers/product.js:574` 寫 `title: row.type`，但 `hidden_play` 的欄位是 `title`（V1 沒有 `type` 欄），`undefined` 在 JSON 序列化時被丟掉。view `user_user_level` 不受影響。P3 商品負責處理（改成 `row.title`）；`tests/test_api_smoke.py::test_tour_hidden_shares_use_user_level` 暫不斷言 `title`。（P3 已修：P3 Task 4 已改成 `row.title`，回應帶 `title`；本條原文保留作歷史紀錄。）
- 管理者商品清單 `GET /api/v1/admin/product` 一律回 500（P1b Task 7 冒煙測試發現）：兩個獨立 bug，都要修。(1) `middlewares/product/index.js:296` 從 `req.user` 解構 `tour_ids`，但登入簽發的 JWT 只有 `{ id, role }`（`controllers/userinfo.js:105,232`），`:312` 的 `tour_ids.map` 對 `undefined` 丟 TypeError；(2) 即使有 `tour_ids`，`:312–315` 把 `map` 回傳的 Promise 陣列當查詢結果讀 `.rows`（`userResult.rows` 為 `undefined`，`.length` 再丟 TypeError），那段「查無此項目 404」檢查本身也從未生效。後果：管理者看不到商品清單（`tour_base` 的 admin 使用位置 `controllers/product.js:1067` 因此在 API 層走不到）。P2 管理者商品負責處理；`tests/test_api_smoke.py::test_admin_product_list` 以 `xfail(strict=True)` 記錄，修好後會 XPASS 失敗，提醒移除 xfail。（P2 已修：P2 Task 1 已修好 `GET /admin/product`，`test_admin_product_list` 的 xfail 已移除，現為一般通過的測試。）
- 餐廳額滿檢查的第 1 個參數恆為 `NULL`：`middlewares/cart/index.js:73,208` 傳 `options.start_time`，驗證器只有 `start_date`（§2 `restaurant_booking`）。
- 購物車：`cart.js:47–50` 更新使用者所有購物車；`cart.total_price` 與 `GET /list` 的 `summary.total_price` 各自計算（`cart.js:230`）；list 不輸出 `cart_item_id`（`cart.js:209–225`）；分頁排序鍵相同（`cart.js:204`）（§2 `user_cartList`）。
- 結帳：只有購物車第一個項目進入 `order_item`（`checkout.js:20–33,42–56`）；訂單沒有項目或非擁有者時 `GET /summary` 500（`checkout.js:263`、`:225`）（§2 `user_orderList`）。
- 付款：`newebpay.js:82,213` 對 `order_item` 寫不存在的 `payment` 欄位，交易 ROLLBACK，`payment_status` 到不了 1（§2 `user_orderList`、§3 `user_orders`）。
- 優惠卷與點數：沒有任何程式把 `user_coupon.status` 設成 1（只有 `checkout.js:149` 寫 -1）；`GET /user/trade/discounts/:order_id`（`discounts.js:78–115`）取消折抵沒有任何寫入；`discounts.js:34` 讀 `expired_date`；沒有任何程式增加點數、UPDATE `travel_point` 或把 `減少_確認中` 轉成 `減少`；`used_point` 驗證器沒有 `.integer()`（`checkout_Vaildator.js:78`）（§2 `user_couponList`、`user_level_point_coupon`）。
- 角色大小寫：管理者 PATCH 只接受 `admin`／`user`（`admin_Validator.js:4,67–74`），降權成 `user` 後通不過 `authRole('User')`（`routes/collection.js:11`、`routes/purchases.js:11,17`）；seed 的 Bob 是 `admin`，無法呼叫收藏與已購買的 GET（§3 C 組共通觀察）。
- 收藏：`GET /collection/info/all` 每次送兩次回應（`collection.js:39–64`）；`POST` 的 `tour_id` 不驗 UUID，格式錯誤時 500（`middlewares/collection/index.js:46`）（§3 `user_favorite`）。
- 已購買：`middlewares/purchases/index.js:34` 的 404 永遠不會觸發（§3 `user_order_item`）。
- 優惠卷代碼格式前後台不一致：後台新增與修改（`coupon_Validator.js:34` 的 `coupon` 只是 `Joi.string()`；`controllers/coupon.js:10` 新增、`:107` 修改）不限格式，消費者使用時（`discounts_Validatior.js:9–13`）只接受 `^[A-Z0-9]{6}$`，所以後台建立的非 6 碼代碼消費者永遠用不了。修法是兩邊用同一條規則，統一成哪一條由 P6（後台優惠卷 CRUD）決定，不是本表的決定項。seed 依 (d2) 改成 6 碼，不受影響。
- 優惠卷 `discount` 的運算（§4.1 #1 定案 B ＝ 折抵金額）：`controllers/discounts.js:38`、`controllers/checkout.js:155` 做 `total_price * discount`，在金額語意下會算出數百倍金額（例：`total_price` 3576.74 × `discount` 100.0 → 357,674）；要改成 `total_price - discount`（`orders.discount_price` 為折後應付金額，與點數路徑 `checkout.js:165` 同語意），屬 P4 結帳。P4 修好之前優惠卷結帳金額是錯的。V3 view 照金額語意輸出原值，不為了配合乘法而轉換數值。`coupon_Validator.js:45` 的 `> 0` 無上限與金額語意相容；是否加上限（例如不得超過訂單金額）只是 P4／P6 的觀察，不是決定。
- 依 §4.1 與 §4.2 的決定，P1b 的 seed 需要調整：優惠卷只修 `TRAVEL10P` 的 `description`，讓它與折抵金額語意一致（`discount` 的 5 個值 100、50、10、300、20 保留不改，#1 定案 B）、促銷通知日期（#9）、`point_record` 與訂單的點數資料（#2、#3；#3 於 2026-10-23 決定調成與 1 點折 0.8 元、10% 回饋相符，來源檔的 `point_record` 與相關訂單）、`payment` 資料與各 `payment_status`（#4、#5、#6）、主鍵與代碼（(a)，2026-10-23 起含 `country` 主鍵與 `region.country_id`；(d2)）、購物車數量（(d3)）、收藏時間（#43）。
- 展示環境（P7）：seed 管理者 `bob@example.com`（角色 `admin`）的密碼 `Tripeasy123` 公開在 `.env.example:1–3`，而計畫規定 seed 會在本機與展示環境載入。任何公開展示之前，要改成由環境變數注入展示管理者密碼，或展示環境不載入 seed 管理者；與 seed 圖片網址寫死的 `IMAGE_BASE`（`db/seed-build/build_seed.py:90`）併為同一個 P7 項目。
- **已由使用者確認（P3）**：`tour_travel_popular` 的「購買數」＝`order_item` 列數、不乘 `quantity`，是 P1b Task 1 的 controller 裁決（§4.1 #4 只定「只算 `payment_status = 1`」，沒定計數方式；見 §1 `tour_travel_popular`），**使用者 2026-11-19 確認**（P3 spec §2.2）。兩種算法在 seed 的名次相同，所以 P1 沒有影響；P3 商品開工前已變成使用者的明確決定。
- P1b 開工前待補的清單見 §0.1。

## 5. P2 表格約束（V3）

`backend/migrations/V3__p2_user_auth.sql` 對 `"user"` 做兩項變更。不改欄位型別、不回填資料（P2 spec §2.3），所以 `R__views_functions.sql` 的 view 與 §1–§3 的契約型別都不受影響。

| # | 變更 | 理由（P2 spec） | 對應測試 |
|---|---|---|---|
| 1 | `"user".password` 改為可為 NULL（`ALTER COLUMN password DROP NOT NULL`） | §2.1：Google 新註冊不再共用預設密碼；NULL 讓寫漏時 `bcrypt.compare` 失敗而非放行，且 DB 層看得見「沒有密碼」。 | `tests/test_migrations.py::test_user_password_is_nullable` |
| 2 | 唯一索引 `user_email_lower_key ON "user" (lower(email))` | §2.2：email 不分大小寫唯一，擋掉大小寫不同的重複帳號與併發註冊；撞到時（`23505`）回 409。 | `test_migrations.py::test_user_email_lower_unique_index`、`test_email_case_duplicate_rejected`；`test_member_auth.py::test_signup_normalizes_email`、`test_signup_duplicate_differs_by_case_is_409`、`test_signup_concurrent_same_email_only_one_succeeds`、`test_login_email_is_case_insensitive`、`test_login_lowercase_matches_mixed_case_stored_email`、`test_forgetpw_matches_mixed_case_stored_email`、`test_signup_lowercase_conflicts_with_mixed_case_stored_email`、`test_checkout_preview_email_lookup_is_case_insensitive`（結帳預覽，backend `middlewares/checkout/index.js`） |

V3 套用狀態由 `test_migrations.py::test_v3_applied` 與 `test_flyway_applied_v1_to_v6` 檢查。V3 沒有新增或改動參照 `"user"` 的外鍵，`tests/conftest.py` 的 `USER_FK_TABLES` 不變（`test_user_fk_tables_list_is_complete` 把關）。

## 6. P3 表格約束（V4）

`backend/migrations/V4__p3_review_constraints.sql` 對 `review` 做兩項變更。不改欄位型別、不回填資料（seed 的 `rating` 範圍 3–5、`(user_id, tour_id)` 無重複，已預檢相容），所以 `R__views_functions.sql` 的 view 與 §1–§3 的契約型別都不受影響。

| # | 變更 | 理由（P3 spec） | 對應測試 |
|---|---|---|---|
| 1 | 部分唯一索引 `review_user_tour_key ON review (user_id, tour_id) WHERE tour_id IS NOT NULL` | §3.3、§4.1：每位會員對每個行程只能有一則評論，併發下由 DB 擋住（撞到時 `23505` 回 409，P3 Task 6 實作）；`tour_id` 為 NULL 的 `web` 評論不受限。 | `tests/test_migrations.py::test_review_user_tour_unique_index`、`test_review_duplicate_user_tour_rejected`、`test_web_reviews_not_limited_by_unique_index`（對照組） |
| 2 | CHECK `review_rating_range CHECK (rating BETWEEN 1 AND 5)` | §4.1：評分只能是 1–5（V1 只有 `DEFAULT 1`，沒有範圍限制）。 | `test_migrations.py::test_review_rating_check`（0、6 被拒；1、5 通過） |

V4 套用狀態由 `test_migrations.py::test_v4_applied` 與 `test_flyway_applied_v1_to_v6` 檢查。V4 沒有新增或改動參照 `"user"` 的外鍵，`tests/conftest.py` 的 `USER_FK_TABLES` 不變。

V5 套用狀態由 `test_migrations.py::test_flyway_applied_v1_to_v6` 檢查。

### P4 表格約束（V5）

`backend/migrations/V5__p4_trade.sql`（P4 spec §3）對 `payment` 新增一欄與兩項約束。不回填資料（seed 的 15 筆 `payment` 的 `merchant_order_no` 皆為 NULL），不改 view，所以 `R__views_functions.sql` 與 §1–§3 的契約型別都不受影響。

| # | 變更 | 理由（P4 spec §3） | 對應測試 |
|---|---|---|---|
| 1 | 欄位 `payment.merchant_order_no VARCHAR(30) NULL` ＋ UNIQUE 約束 `payment_merchant_order_no_key (merchant_order_no)` | 付款編號（藍新 `MerchantOrderNo`）一對一對應一筆付款；NULL 不受唯一限制（seed 與舊資料為 NULL）。 | `test_migrations.py::test_payment_merchant_order_no_column`、`test_payment_merchant_order_no_unique`、`test_seed_payments_have_null_merchant_order_no` |
| 2 | 部分唯一索引 `payment_order_paid_key ON payment (order_id) WHERE payment_status = 1` | 每張訂單最多一筆成功付款，併發重複通知由 DB 擋住；`payment_status = 0` 的列可並存。 | `test_migrations.py::test_payment_one_paid_per_order` |

`payment` 欄位新增：`merchant_order_no`（`character varying(30)`，可為 NULL）。

seed 的 `payment`（§0.1 第 9 項）與 `point_record`（§0.1 第 10 項）不受 V5 影響：`merchant_order_no` 一律 NULL，且 seed 沒有 `退款退回`／`退款收回` 的列。

`point_record.type` 值域新增兩個值（P4 spec §3 第 3 點；不是 DB 約束，`type` 仍是 VARCHAR(50) NOT NULL）：`退款退回`：`point` 為正數，退還使用的點數；`退款收回`：`point` 為負數，收回回饋點數。既有值為 `新增`、`減少`、`減少_確認中`。

**寫入時機**（`backend/src/utils/trade.js::refundOrder`，管理員退款 `POST /api/v1/admin/orders/:order_id/refund`，P4 spec §7）：只在訂單由 1 轉 3 的同一個交易內寫入，每張訂單最多各一筆（只有狀態 1 的訂單可退款，退款不會重複）。
- `退款退回`（`point` 為正）：該訂單 `減少` 列的點數絕對值加總 > 0 才寫，同時加回 `user_level.travel_point`。
- `退款收回`（`point` 為負）：該訂單 `新增`（回饋）列的點數加總 > 0 才寫，同時從 `travel_point` 扣除；回饋已被花掉時餘額允許為負（P4 spec Q2，`travel_point` 無 CHECK 約束）。
- 原本的 `減少`、`新增` 列保留不動（流水帳）；`user_coupon` 同時還原為 `status = 0`、`order_id = NULL`；`payment` 列不改。
- 已退款訂單的 `computePayable` 取該單成功付款（`payment_status = 1`）的 `discount_price` 作為應付金額（券已釋放，不能再從保留紀錄推算）。
- 備援：已退款但沒有成功付款列（`payment_status = 1`，或其 `discount_price` 為 NULL；例如 seed 的已退款訂單 #19）時，`computePayable` 走原本的計算（不折抵）。
- `travel_point` 為負時，折抵流程回報的可用點數（`user_point`、`remaining_point`）視為 0；儲存的餘額維持負數（P4 spec Q2）。

### 購買資格（非 DB 物件）

- **定義**（P3 spec §4.2 R1）：會員「購買過」某行程，是指存在該會員本人的 `orders`，其 `order_item` 屬於該行程且 `order_item.payment_status = 1`（已付款）。未付款、已取消、已退款、逾時、別人的訂單、別的行程的訂單都不算。
- **實作位置**：`backend/src/utils/purchase.js`（`hasPurchased`，P3 Task 6 建立），是唯一實作；評論、隱藏玩法與資格查詢 API 都呼叫它，不得另寫 SQL。
- **對 P4 的依賴**：付款成功時，P4 必須把 `order_item.payment_status` 設成 `1`；否則會員永遠沒有評論與分享隱藏玩法的資格（現況 `newebpay.js` 的寫入失敗，見 §4.2「契約已記錄」的付款項）。

## 7. P5 表格約束（V6）

`backend/migrations/V6__p5_member_center.sql`（P5 spec §3）。不改欄位、不改 view，所以 `R__views_functions.sql` 與 §1–§3 的契約型別都不受影響。

| # | 變更 | 理由 | 對應測試 |
|---|---|---|---|
| 1 | `favorite_user_tour_key UNIQUE (user_id, tour_id)`；加約束前先刪重複，同組保留 `(created_at, favorite_id)` 最小者 | 重複收藏回原 id、並行收藏只留一筆（見 §4.2 d4） | `tests/test_migrations.py::test_favorite_user_tour_unique` |
| 2 | `cart_user_id_key UNIQUE (user_id)`；預檢有重複就 `RAISE EXCEPTION`，不自動合併 | 一位會員一個購物車；`controllers/cart.js` 改 `ON CONFLICT (user_id) DO NOTHING` 再 `FOR UPDATE` | `test_migrations.py::test_cart_user_unique`、`test_trade_cart.py::test_first_add_concurrently_creates_one_cart` |
| 3 | `auto_setting_user_id_key UNIQUE (user_id)`；預檢有重複就 `RAISE EXCEPTION`，不自動合併 | 一位會員一組通知設定；seed 改為 3 列（§0.1 第 1 項） | `test_migrations.py::test_auto_setting_user_unique`、`test_build_seed.py::test_alice_auto_settings_merged` 等 |

V6 套用狀態由 `test_migrations.py::test_flyway_applied_v1_to_v6` 檢查。V6 沒有新增或改動參照 `"user"` 的外鍵，`USER_FK_TABLES` 不變。既有 volume 若 alice 仍有兩筆 `auto_setting`，V6 預檢會失敗，要 `docker compose down -v` 重建。
