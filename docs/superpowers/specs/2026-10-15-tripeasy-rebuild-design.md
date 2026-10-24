# TripEasy 重建設計（Spec）

> 日期：2026-10-15 · 狀態：待使用者審核（已納入 Fable 5.1 審核意見，Critical 3、Important 4，由 Opus 抽查確認）
> 依據：`docs/inventory.md`（現況盤點，含 Fable 5.1 複核）
> 產出方式：superpowers:brainstorming，2026-10-13 ~ 10-15 逐段確認

## 0. 目標與範圍

### 目標
- **完整實作** TripEasy 旅遊電商網站，作為作品集展示。
- 每個階段產出**教學報告**，向以前同組的成員說明這次 vibe coding 的過程。

### 已定案的原則
- **沿用既有程式碼**：不重寫，也不換技術棧（Express 4 + raw `pg`、Vue 3 + Vite）。
- **重構規則**（2026-10-21 使用者確認）：P1 不改 controller（契約要從它反推）。P2 起允許重構，條件是：先有測試覆蓋相關行為、在計畫裡列成獨立的步驟或 Task（實作者不得自行決定重構）、用獨立的 commit 和修 bug 分開。動到 P1 建立的 view / 函式時，要同時更新 `db-contract.md` 和契約測試。
- 測試技術棧：pytest + requests（API）、psycopg（DB）、Playwright Python（E2E）。**JS 元件測試不做。**
- 刻意展示的測試能力：DB 層驗證、migration / DB 契約測試、金流簽章驗證、API 契約測試。

### 功能範圍
- **要做**：會員（含 Google 登入）、商品（行程、景點、住宿、餐廳）、搜尋、購物車 → 結帳 → 折扣 → 藍新付款、會員中心（收藏、訂單）、admin 後台（商品 CRUD、促銷、優惠券、會員 / 角色），還有以下幾項：
  - 自動下架排程和通知設定
  - 隱藏玩法和評論，包含讀取和新增（只有購買過的會員能新增）
  - 客服：聯絡表單 + 後台回覆
- **不做**：Facebook 登入。從前端移除入口，或標示「未開放」。

### 模型分工
- 實作用 **Sonnet**。
- 卡關時升級 **Opus**，條件是同一個任務連續修兩次還是紅燈，或遇到設計層級的問題。
- Review 由 **Fable 和 Opus** 各自對同一份 diff 做，再比對兩邊的結果。

## 1. 架構與 repo 配置

```
~/project/tripeasy/            ← 新 repo：nohungry/tripeasy（總覽；建立 GitHub repo 前再確認）
├── README.md                  ← 作品集入口：介紹、架構圖、一鍵啟動、階段報告索引、版本對照表
├── docker-compose.yml
├── .env.example
├── docs/
│   ├── inventory.md
│   ├── db-contract.md         ← P1 產出
│   ├── superpowers/specs/     ← 本檔
│   ├── superpowers/plans/
│   └── reports/phase-N.md
├── db/seed/                   ← P1 產出
├── tests/                     ← pytest：API 契約、DB、安全 / 金流
├── e2e/                       ← Playwright Python
├── backend/   (.gitignore)    ← 獨立 repo nohungry/tripeasy-backend（main）
└── frontend/  (.gitignore)    ← 獨立 repo nohungry/tripeasy-frontend（dev）
```

- **版本綁定 `refs.env`**：總覽 repo 用這個檔案記錄 `BACKEND_REF` 和 `FRONTEND_REF`（branch 或 SHA）。CI 和本機腳本都照它 checkout，總覽 repo 的每個 commit 都能重現當時的三個 repo 版本。
- **版本對應**：每個階段完成時，backend 和 frontend 各打一個 `phase-N` tag，`refs.env` 指到這兩個 tag，總覽 README 也記錄兩邊對應的 commit。
- **環境變數只用一個來源**：只保留總覽 repo 根目錄的 `.env.example`，複製成 `.env` 後，compose 用 `env_file` 注入給 backend。backend 內建的 dotenv 不會覆寫已經存在的環境變數，所以不用修改。
- **git 流程**：每個階段在兩個 repo 各開一個 feature branch，完成後 merge 回去並打 tag。**只 push 到使用者的 fork**，不碰 upstream（tripEasyCompany）。

### `docker compose up` 的組成
| 服務 | 用途 |
|---|---|
| `postgres` | PostgreSQL 15 |
| `flyway` | 啟動時跑 migration（V1、V2、新的 V3+），本機額外載入 seed |
| `backend` | Express API，:3000 |
| `frontend` | Vite dev server，:5173 |
| `mailpit` | 攔截寄出的信，在網頁上檢視 |
| `mock-oauth2-server` | 本機模擬 Google OAuth（需要先做可行性測試，見 2.2） |
| 圖片 volume | 本機 storage adapter 使用 |

## 2. P0 地基

### 2.1 後端可以開機
- 用 Node 22.14.0 產生 `package-lock.json`，之後統一用 `npm ci` 安裝。沒用到的套件**先不清**。
- Dockerfile 分成 `dev`（nodemon + bind mount）和 `prod` 兩個 target。
- compose 的 healthcheck 改成 `/api/v1/health`，拿掉寫死的 172.18.x IP。
- `.env.example` 列出全部變數，補上 `DEFAULT_OAUTH_PASSWORD`、`RespondType`。
- **async 錯誤處理**：加一個共用的 async handler wrapper，或用 `express-async-errors`。在 `try` 外面 reject 的錯誤（例如 `newebpay.js:59`、`checkout.js:122-124`）會讓請求一直卡住，測試會逾時，而不是正常失敗。這一項要在所有 API 測試之前完成。

### 2.2 外部服務 adapter（用環境變數切換）
| 服務 | 介面 | 本機（預設） | 部署 |
|---|---|---|---|
| 圖片儲存 | `storage.upload(buffer, path) → url` | `local`：存到 volume，由 Express 提供靜態檔 | `firebase` |
| 寄信 | `mailer.send({to, subject, html})` | `smtp` → Mailpit | `sendgrid` |
| Google OAuth | token 和 userinfo 的網址可設定 | `mock-oauth2-server` | 真的 Google |
| 藍新 | 原本就用環境變數 | 測試環境，notify 由 pytest 模擬 POST | 待 P7 討論 |

- Firebase 改成第一次用到才初始化，不再因為缺金鑰在開機時 crash。
- 前端 `loginPage.vue:154-158`：client_id 和**授權網址**（現在寫死 `accounts.google.com`）都改讀環境變數，`VITE_Redirect_BASE` 也補進 `.env.development`。
- Storage 現在有兩種呼叫方式，adapter 兩種都要涵蓋：`userProfile.js:97-109`（bucket.file 加 download token）和 `utils/firebaseUpload.js:12`。
- **風險**：`navikt/mock-oauth2-server` 還沒在這個專案驗證過。P0 先做可行性測試，行不通就改用免費的 Google 測試 client。測試時要確認：
  - token 裡要帶 `name` 和 `email` 兩個 claim，因為 `user.name` 是 NOT NULL，`userinfo/index.js:170` 也要求 email。
  - issuer 的 hostname 在瀏覽器（localhost）和容器之間（service name）要一致。
- 真正走一次付款流程時，用 cloudflared tunnel 讓藍新的 notify 打得進本機。

### 2.3 測試與 CI 骨架
- `tests/conftest.py` 管理 base_url 和 DB 連線。第一批測試是 `/api/v1/health`，加上一個 CORS 冒煙測試：帶 `Origin: http://localhost:5173` 時，response 要有正確的 `Access-Control-Allow-Origin`。
- 總覽 repo 的 GitHub Actions：照 `refs.env` checkout 三個 repo → `docker compose up` → 跑 pytest。**只有 main 要求全綠**。
- 前端補上 `VITE_API_BASE`。後端 CORS 用 `FRONTEND_PATH=http://localhost:5173`。

### P0 完成標準
`docker compose up` 一行指令就能讓全部服務通過健康檢查。`/health` 和 CORS 測試在 CI 上是綠的。mock OAuth 的可行性有結論（可行，或改用替代方案）。

## 3. P1 DB 契約

### 背景
程式碼查詢了 21 個 DB 物件（12 個 view 加函式，清單見 `inventory.md`「Fable 5.1 複核修正」），但 migration 裡都沒有建立。2026-10-14 查核了使用者手上的 SQL 檔：
- `D:\backend\migrations\V1、V2`：跟 repo 的內容相同，只差 CRLF 換行。
- `Downloads\tripeasy_sql.sql`（2025-04）：是舊版的 V1，**不採用**。
- `Downloads\tripeasy_fakedata.sql`（2025-05）：**符合現在的 schema**。依序跑 V1 → V2 → fakedata 完全沒有錯誤，24 張表都有資料。
- **四份都沒有那 21 個物件，也沒有其他來源**，所以全部從程式碼反推。

### 3.0 路由前置修正（P1 第一步）
`backend/src/routes/product.js` 同一個 router 被掛在兩個前綴上，有兩個路由順序的 bug：
- 管理者用的 `GET /`、`GET /:tour_id`（:17、:20）宣告在公開版（:33、:36）前面，**訪客查商品會拿到 401**。
- `PATCH /:tour_id`（:23）宣告在 `PATCH /status`（:26）前面，**上架 API 永遠走不到**。

不先修好這兩個 bug，P1 的 API 冒煙測試不可能變綠，所以從 P3 / P6 提前到 P1 的第一步。修正方式是把 router 拆成 admin 和 public 兩個，同樣照紅燈 → 綠燈的流程。

### 3.1 反推流程（先寫契約，後寫 SQL）
1. 整理每個物件的使用位置：被哪些 controller 或 middleware 呼叫、傳入什麼參數、用到哪些中文欄位、怎麼排序和篩選。
2. 寫成 `docs/db-contract.md`：每個物件列出參數簽名、輸出欄位（中文名 → 來源表的欄位 → 型別）和語意。
3. **契約由 Fable 和 Opus 各自審過，通過後才寫 SQL。**
   - 語意不明確的地方要列在契約裡，**請使用者確認**。目前已知兩處：
     - 點數的累積和扣抵規則（`checkout.js:159`、`discounts.js:66` 的 `point * 0.8`）
     - `coupon.discount` 是折扣倍率還是折抵金額（`discounts.js:38`）
4. 寫 `backend/migrations/R__views_functions.sql`（repeatable migration；2026-10-23 P1b 計畫改用 repeatable，原寫 `migrations/V3__views_functions.sql`，理由見該計畫 Global Constraints 第 1 條），照程式碼期待的中文欄位名稱，**controller 不改**。

### 3.2 Seed
- 以 `tripeasy_fakedata.sql` 為基礎，改寫成 `db/seed/R__seed.sql`（Flyway 的 repeatable migration），記下來源。
- **只在本機和展示環境載入**：compose 的 Flyway 用 `-locations=filesystem:migrations,filesystem:db/seed`，正式環境只給 `migrations`。
- **可以重複執行**：拿掉檔頭的 `delete`，每個 INSERT 都加 `ON CONFLICT DO NOTHING`。這樣第二次 `docker compose up`（DB volume 還在）不會因為重複的 key 而失敗。
- 要修的地方：
  - 密碼 hash 是假的（29 字元），改成真的 bcrypt，明文寫在 `.env.example` 的註解裡。
  - 補資料量，讓搜尋篩選、分頁、熱門排行有東西可以看。
  - 補 `payment` 的資料。
  - 圖片改用本機的佔位圖。

### 3.3 測試
| 層 | 內容 |
|---|---|
| 契約 | 查 `information_schema` 和 `pg_proc`，確認欄位名稱、型別、函式簽名都符合契約 |
| 行為 | 測試**自己塞資料**，在 transaction 裡跑完就 rollback，不依賴 seed。例如收藏過的商品「是否收藏」要是 true、房間訂滿時不能訂 |
| API 冒煙 | 原本會因為缺物件回 500 的 API，現在都回 200，結構也正確。前提是 3.0 的路由已經修好 |

- 訂單短編號（藍新 30 字元限制）、`payment` 的 unique 約束，這類 schema 修改歸到 P4。

### P1 完成標準
3.0 的兩個路由 bug 都已修正，21 個物件全部建好，契約通過雙模型審核，契約中待確認的語意已經由使用者確認，三層測試在 CI 上全綠，seed 連續 `up` 兩次都不會出錯。

## 4. P2–P6 功能階段

| 階段 | 內容 | 已知要處理的 bug（詳見 inventory） |
|---|---|---|
| P2 會員 | 註冊、登入、驗證碼、忘記密碼、Google 登入、會員資料，恢復前端的登入檢查，修正前端路由 | 驗證碼答案用明文存在 cookie；角色修改 API 少了 admin 檢查；**重設密碼的 token（`userinfo.js:256-257`，payload `{id}`，用同一個 `JWT_SECRET`）能通過所有只檢查 `auth` 的路由**；預設密碼 `'DefaultPassword123!'` 寫死在程式碼裡（`userinfo.js:174`）；前端路由有重複的 `search` name（`router/index.js:75,197`）、沒有 404 catch-all、hash 模式下用 `window.location.href` 跳轉、`api.js:306` 直接 `throw err` |
| P3 商品 | 列表、搜尋、詳情、評論、隱藏玩法（**補上新增功能**：只有購買過的會員能寫評論和分享隱藏玩法） | 路由 bug 已在 P1 修好 |
| P4 交易 | 購物車 → 結帳 → 折扣 / 優惠券 → 藍新付款 | 金額被前端竄改；notify 沒做冪等和金額檢查；訂單編號長度；**`/newebpay/return` 的 handler 是空的，請求會卡住**（`newebpay.js:235-237`）；**付款表單沒有做 HTML 跳脫**（`newebpay.js:103-125`，ItemDesc 直接來自 DB 的商品標題） |
| P5 會員中心 | 收藏、訂單、點數、通知設定 | 點數規則照 P1 契約中確認的語意 |
| P6 後台 | 商品 CRUD、促銷、優惠券、會員 / 角色、自動下架排程、**異動通知**（`routes/admin.js:41-50`）、**客服：會員送出聯絡表單 → admin 在後台檢視和回覆 → 回覆時發站內通知並寄信（Mailpit）** | 排程沒有 handler；客服的後端完全沒有，要新增 1 張表和 API（新的 migration） |

- **權限**：付款、自動設定、點數等級的 API 限定 `authRole('User')`（`routes/newebpay.js:12`、`automation.js:11`、`userProfile.js:32`）。**維持原設計**，admin 不結帳，結帳流程一律用一般會員帳號測試。

### 4.1 單一功能的流程
1. **釐清**：列出這個功能涉及的 API、頁面、DB 物件和已知 bug。
2. **紅燈**：先在總覽 repo 寫測試，證明功能壞掉或還沒做，**單獨 commit**（`test: ... 🔴`）。紅燈的執行輸出保存下來，放進報告。
3. **實作**：Sonnet 在 backend / frontend 的 feature branch 修改，讓測試轉綠，再 commit（`fix/feat: ... 🟢`）。同時更新總覽 repo 的 `refs.env`，指到這個 commit。
   - 紅燈 commit 只存在 feature branch，總覽 repo 的 main 永遠保持全綠。
4. **審查**：Fable 和 Opus 各自 review，比對兩邊的結果，處理確認過的問題。
5. **驗證**：完整跑一次 pytest 和 E2E，CI 全綠。

### 4.2 測試分層
| 層 | 工具 | 範圍 |
|---|---|---|
| API 契約 | pytest + requests + pydantic | 每個 API：正常情況、驗證錯誤、權限（401/403） |
| 安全 / 金流 | pytest | 角色越權、金額竄改、notify 重送的冪等性、藍新簽章 |
| DB 狀態 | psycopg | 打完 API 後查 DB，確認訂單、付款、點數寫入正確 |
| E2E | Playwright Python | 只測主要流程：註冊登入、搜尋 → 詳情 → 購物車 → 結帳、後台上架 |

- 每個測試用 fixture 自己建立需要的資料，不依賴 seed 的狀態。

### 4.3 前端
- 用假資料的頁面改接 API，元件結構盡量維持原樣。
- 範圍外的功能移除入口，或標示「未開放」。
- 驗證碼 / session 的 cookie 屬性（`SameSite`、`Secure`）和 CORS `credentials` **改成環境變數可設定**，先為之後的跨網域部署留彈性。

### 4.4 階段結束
1. merge 回去並打 `phase-N` tag，更新 README 的版本對照表。
2. 寫 `docs/reports/phase-N.md`。
3. **使用者確認報告後，才進入下一個階段。**

### 階段完成標準（P0–P6 共通）
- P2–P6：這個階段的功能可以從前端完整操作，主要流程要有 E2E 測試覆蓋。P0 和 P1 不適用這一條，改用各自的完成標準。
- 新增的測試全綠，舊的測試沒有退化。
- 雙模型 review 沒有還沒處理的 Critical 或 Important 問題。
- 報告已經定稿。

## 5. 階段報告範本

```markdown
# Phase N：<名稱>
> 完成日期 · backend tag phase-N (sha) · frontend tag phase-N (sha)

## 0. 摘要            ← 做了什麼、修了幾個 bug、測試數量的變化
## 1. 問題與修正       ← 每個 bug：現象 → 根因（附原始碼行號）→ 紅燈測試 → 修正 diff → 綠燈
## 2. Vibe coding 工作流 ← 用了哪些 skill、關鍵 prompt、Fable vs Opus review 對照表、AI 出錯 / 人介入紀錄
## 3. 測試方法         ← 新增的測試分層、值得一看的技巧、測試數量和 CI 結果
## 4. 操作指南         ← 怎麼切到這個版本、怎麼啟動、手動試的步驟、測試帳號
## 附錄              ← 變更檔案清單、已知限制
```
- AI 根據 commit 和 review 紀錄產生初稿，使用者修改確認後定稿。範本在 P0 報告時固定下來。

## 6. P7 部署 — 待討論

使用者在 2026-10-15 決定**之後再討論**。目前只確定以下幾點：
- 最終目標是上線，讓作品集有公開的 demo 網址。
- 原本的候選方案是 Neon（DB）、Render 或 Zeabur（後端）、GitHub Pages（前端），**還沒定案**。
- 跨網域需要的 cookie 和 CORS 設定，已在 4.3 先做成可設定的。
- 到 P6 完成前會再開一次 brainstorming 決定 P7。
