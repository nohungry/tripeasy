# TripEasy 現況盤點

> 盤點日期：2026-10-13。原始計畫檔（2026-08-30）已遺失，本檔為重新盤點結果，作為重寫計畫的依據。
> 後端 `nohungry/tripeasy-backend`（main，HEAD 2025-07-01 PR #38）
> 前端 `nohungry/tripeasy-frontend`（dev，HEAD 2025-11-13 PR #37）

## 後端

### 技術棧
- Node 22.14.0（`.nvmrc`、Dockerfile；無 `engines`）、Express 4.21（CommonJS）
- PostgreSQL 15，**raw `pg` Pool SQL**（`src/config/database.js`）；typeorm 列在依賴但沒用
- 實際使用：jsonwebtoken、bcrypt、joi、multer、firebase-admin、@sendgrid/mail、axios、svg-captcha、cors、cookie-parser
- 未使用依賴：typeorm、reflect-metadata、pino*、morgan、node-cron、ejs、formidable、dayjs、body-parser
- **沒有 package-lock.json**
- `npm test` 是 placeholder，無任何測試；無 CI

### 結構與啟動
- `src/{server.js, config/, routes/, middlewares/<resource>/ (Joi 驗證), controllers/}`，`models/` 是空的
- `database.js` 讀 `.env.${NODE_ENV}`，缺 `POSTGRES_DB_*` 或 `JWT_SECRET` 就 exit；production 不讀 dotenv
- CORS 只允許 `localhost:5500` + `FRONTEND_PATH`（`server.js:32-48`）→ Vite 的 5173 會被擋
- 環境變數：PORT、NODE_ENV、FRONTEND_PATH、POSTGRES_DB_*、JWT_SECRET、JWT_EXPIRES_DAY、SENDGRID_*、GOOGLE_CLIENT_ID/SECRET/REDIRECT_URI、DEFAULT_OAUTH_PASSWORD*、FIREBASE_SERVICE_ACCOUNT、FIREBASE_STORAGE_BUCKET、藍新 MerchantID/HASHKEY/HASHIV/Version/PayGateWay/NotifyUrl/ReturnUrl/RespondType*（* = `.env.example` 沒列）

### 資料庫
- Flyway SQL migrations：`V1__tripeasy_sql.sql`（25 張表）、`V2__tripeasy_trigger.sql`（updated_at trigger）
- **沒有 seed 資料**
- **程式查詢的 view 沒有任何 migration 建立**：`tour_base`、`tour_travel`、`user_couponList`、`user_favorite`、`user_level_point_coupon`、`user_orders`、`user_order_item`、`user_user_level`、`restaurant_business_parsed` → 全新 DB 上 cart / checkout / product / coupon / profile 都會 SQL 錯誤

### API（前綴 `/api/v1`）
auth/userinfo（signup、login email/google、forgetpw、resetpw、captcha、login/status）、user/userinfo、user/automation、user/collection、user/purchases、user/home/search、user/trade/cart、user/trade/discounts、user/checkout、user/newebpay、admin（members、promotions、coupons）、web/filter、web/scheduler、product（見 P0）

### 路由 bug
- **P0：`src/routes/product.js` 同一個 router 掛在兩個前綴**（`server.js:80` `/user/product/search`、`server.js:101` `/admin/product`）。admin 的 `GET /`（:17）、`GET /:tour_id`（:20）宣告在公開版（:33、:36）之前，`auth` 直接回 401/403 不會 fall through → **訪客與一般使用者永遠查不到商品列表與商品詳情**。admin 路由也同時暴露在 user 前綴下
- `PATCH /:tour_id`（:23）在 `PATCH /status`（:26）之前 → 上架功能打不到
- `admin.js` `PATCH /members/roles` 的 `authRole('admin')` 被註解 → **任何登入者都能改角色（越權）**
- `userinfo.js:19`（login/facebook）、`scheduler.js:6` 沒有 handler
- `newebpay /return` 是空函式 → request 卡住
- Express 4 不接 async reject，多處錯誤會讓 request 卡住（如 `post_newebpay_payment`、`forgetpw`）
- docker-compose healthcheck 打 `/api/health`，實際是 `/api/v1/health`

### 金流（藍新 MPG）
- TradeInfo = AES-256-CBC hex；TradeSha = SHA256(`HashKey=..&TradeInfo&HashIV=..`) 大寫
- notify：先解密再驗 TradeSha，**不檢查 Status / Amt、不冪等**（重送會重複寫 payment）
- **金額取自前端傳的 `order_items[].price`，可被竄改**；HTML 輸出未 escape
- `RespondType` 未定義，但 notify 預期 JSON

### 認證
- JWT Bearer，payload `{id, role}`，role 為 `'User'` / `'admin'`
- bcrypt、登入鎖定；Google OAuth 新用戶預設密碼可能落到寫死的 `'DefaultPassword123!'`
- 重設密碼 token 與登入共用 `JWT_SECRET`，可通過只檢查 `auth` 的路由
- captcha 答案明文存在 cookie

### 今天跑不起來的原因
1. `src/config/firebase.js` 在 require 時就初始化，`FIREBASE_SERVICE_ACCOUNT` 空的就整個 crash
2. 缺 view → 大部分商業 API SQL 錯誤
3. 無 lockfile
4. `.env.example` 的 `POSTGRES_DB_HOST=postgres` 只在 docker 內可解析；compose 寫死 172.18.x IP 可能衝突
5. Dockerfile 跑的是 `npm run dev`（nodemon）

## 前端

### 技術棧
- Vue 3.5、Vite 6、vue-router 4（**hash mode**）、axios、Bootstrap 5.3、sweetalert2、sass、gh-pages
- Pinia 有裝但沒用，實際 store 是 `reactive()`（`src/stores/userStore.js`）
- Node 未指定（CI 用 20）；ESLint 9 + prettier；**無任何測試**
- `.github/workflows/gh-pages.yml` 只有手動觸發，沒設 `VITE_API_BASE`

### 路由（`src/router/index.js`）
- HomeLayout `/`：home、tour、tourfake、pay、tourfakeUSA、search、`/cart`
- `/admin`：login、register、forgotpw、userprofile、resetpw、collect、personalOrder、manage/*
- 問題：route name `search` 重複（:73、:195）；沒有 404 catch-all；userprofile 的 `requireAuth` 被註解；`/admin/manage/*` 沒 guard；`window.location.href='/admin/login'` 等在 hash mode + `/frontend/` base 下會 404；大量 `to="#"` 死連結；prod base `/frontend/` 不符合 fork 名稱 `tripeasy-frontend`
- 第 204–371 行是整份註解掉的舊 router

### API 串接
- base URL 用 `VITE_API_BASE`，**但 `.env.development` / `.env.production` 都沒設** → 全部打到 `undefined/api/v1/...`
- 沒有共用 axios instance / interceptor
- 已串：註冊、登入（email / Google）、忘記 / 重設密碼、captcha、login status、會員資料
- **未串（後端有、前端沒用）**：商品搜尋 / 詳情、首頁商品與評論、購物車、折扣、結帳、藍新付款、收藏、訂單、篩選、頭像、等級點數、所有 admin
- 假資料：HomeView、searchPage（:322 寫死陣列）、tourPageFake、tourFakeUSA、cart、pay；collect / personalOrder / manage 多為 15 行空殼
- `api.js:719` `throw err` 但變數叫 `error` → ReferenceError

### 會在執行時 crash
- tourPage、cart、pay、tourPageFake、tourFakeUSA 的 `data() {}` 沒回傳，且 mounted 呼叫不存在的 `this.fetchUserInfo()` → 一進頁面就 TypeError
- commit 4005818「改成靜態頁面展示版本」關掉了 guard 和登入按鈕，header 永遠顯示已登入（預設名字「阿蘇」）

### 大型元件
HomeView.vue 1551 行（Options API 混一個 setup）、searchPage 607、HeaderComponent / HeaderReal 各 557（HeaderReal 沒被用到）、userprofilePage 546

## Fable 5.1 複核修正（2026-10-13）

> 由 Fable 獨立逐條查核，下列修正已由 Opus 抽查確認。

### 更正
- **缺的 DB 物件是 21 個，不是 9 個 view**，全 repo 沒有任何 `CREATE VIEW/FUNCTION`：
  - 12 個 view：前述 8 個（不含 `tour_travel`）+ `user_orderList`（`controllers/checkout.js:211`）、`user_cartList`（`cart.js:202`）、`user_level_review_forHome`（`home.js:132`）、`user_adminList`（`admin.js:34`）
  - 9 個 SQL 函式：`tour_travel(uuid)`（原誤列為 view）、`tour_travel_popular`、`tour_travel_most_favorited`（`home.js`）、`tour_tour_detail` / `tour_hotel` / `tour_restaurant`（`product.js`）、`hotel_booking`、`restaurant_booking`、`restaurant_isClosed`（`middlewares/cart/index.js`）
  - 這些物件輸出**中文欄位名**（旅遊編號、價錢、評論時間…），欄位契約只能從 controller 用法反推
- `forgetpw` 不會卡住（整段在 try 內，回 500）。真正會卡住的是 `post_newebpay_payment` 與 `checkout.js:122-124`
- CORS：把 `FRONTEND_PATH` 設成 5173 即可，不用改程式
- 5 頁 `fetchUserInfo` TypeError：Vue 3 會攔截生命週期錯誤，**頁面仍會渲染**，只是 console 報錯，不是白屏
- `throw err` bug 在 `api.js:306`（不是 :719）
- header 不是「永遠已登入」，`isLoggedIn` 仍依 localStorage，只是登入鈕被拿掉

### 新發現
- **藍新金流阻斷點**：`MerchantOrderNo` 直接用 `order_id`（UUID，36 字含 `-`，`newebpay.js:96`），藍新限 30 字元英數 → 沙盒會拒絕。`orders` 表要加短訂單編號
- `payment` 表沒有 `unique(order_id)` → 冪等需加約束
- 重設密碼 token（payload 只有 `{id}`）也能打沒有 authRole 的 `PATCH /members/roles`
- **沒有任何建立 admin 帳號的正常入口**：signup 一律寫 `'User'`（`userinfo.js:25`），需 seed admin
- `coupon.discount` 是 FLOAT，語意（折後比率 or 折扣額）需定義；`user` 表沒有 phone/address/birthday
- Google OAuth client_id 寫死在 `loginPage.vue:154`
- 前端需**新寫約 12 個頁面**：`tourPage` 內容空白、6 個 15 行空殼、admin 後台（商品 CRUD + 7 圖上傳、促銷、優惠券、會員 / 角色、異動通知）零 UI
- 前端有、後端無：Facebook 登入、scheduler 自動下架、客服頁
- 藍新 NotifyURL 需外部可達（本機要 tunnel），E2E 需設計「模擬 notify」路徑

### 階段順序的不同意見
Fable 認為「補 DB 物件」應是**獨立且最前面**的一個階段（決定後面一切），而非與 firebase / lockfile 同級的小修補。

## 對重建計畫的意涵
- 前後端目前**只有會員系統真的串起來**；商品 → 購物車 → 結帳 → 付款整條商業流程都還沒接
- 後端要先補：缺的 view migration、seed 資料、firebase lazy init、P0 路由拆分、lockfile、CORS
- 安全問題（越權改角色、金額可竄改、notify 不冪等、captcha 明文）正好是「金流簽章驗證、DB 層驗證、API 契約測試」可以展示的題材：先寫測試證明 bug 存在，再修
