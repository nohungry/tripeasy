# P2 會員 設計（Spec）

> 日期：2026-11-12 · 狀態：待使用者審核（已經過 builder check，問題已併入）
> 上位文件：`docs/superpowers/specs/2026-10-15-tripeasy-rebuild-design.md`（以下稱「總 spec」）§4 P2 列、§4.1–4.4
> 產出方式：superpowers:brainstorming，2026-11-12 逐項確認
> 標記：**【使用者定】** = 使用者明確決定；**【Claude 定】** = 討論中由 Claude 決定、使用者未反對，可在審閱時推翻。

## 0. 目的

讓會員功能**從前端能完整操作、而且安全**，並把過程寫成教學報告（總 spec §4.4、§5）。

**P2 的主線**【使用者定】：**註冊 → 登入 → 會員中心** 這段要順。這是 P2 要示範的流程，E2E 以它為主。

「順」的意思：
1. 註冊：填姓名、email、密碼、三個偏好 → 成功。email 重複、格式錯誤時畫面上有清楚訊息。註冊成功後的去向沿用現有前端行為；若現有前端沒有定義，跳到登入頁【Claude 定】。
2. 登入：Email 登入成功進會員中心。密碼錯顯示錯誤次數；錯 3 次鎖 30 分鐘，畫面上看得到（現有後端行為，保留）。已登入者開登入頁會被帶到會員中心（現有 `router.beforeEach` 行為，保留）。
3. 會員中心：未登入直接開會被擋回登入頁；重新整理不會被登出；token 過期回登入頁。

## 1. 範圍

### 要做
- 後端：註冊、Email 登入、驗證碼、忘記密碼 / 重設密碼、會員資料（讀、改、改密碼、頭像上傳）、Google 登入；以及 §3 列的安全修正。
- DB：§2 的兩個 migration，連同 `docs/db-contract.md` 與契約測試的更新。
- 前端：§4 列的路由與登入檢查修正；會員中心依 §4.2 的切法做到可操作。
- 測試：總 spec §4.2 的四層，主線 E2E（§5）。
- P1 遺留待辦（§6）。

### 不做（non-goals）
- 會員中心的「個人偏好設定」「會員等級」「個人訂單查看」三個分頁內容、收藏、點數規則 → P5（見 §4.2）。
- 後台（`/admin/manage/*`）的功能與登入檢查 → P6。
- Facebook 登入（總 spec §0）：前端的 FB 圖示移除或標示「未開放」。
- Email 註冊的信箱驗證信（討論過，未採用；見 §2.3）。
- 「帳號是否存在」的隱藏（見 §3.4）。

### 反目標（做了也算失敗）
- 任何人能不靠該會員的密碼或 Google 帳號登入他的帳號（共用預設密碼、重設 token 當登入 token、預先劫持）。
- 為了修 bug 順手重構，跟修正混在同一個 commit，或沒有先有測試覆蓋（違反總 spec §0 重構規則）。
- main 上出現紅燈（總 spec §4.1：紅燈 commit 只在 feature branch）。

## 2. 資料庫變更

新的 versioned migration 放在 `backend/migrations/`，接在 `V2__tripeasy_trigger.sql` 之後（編號、檔名、拆一個或兩個檔由實作者決定）。兩項都要同步更新 `docs/db-contract.md` 和契約測試（總 spec §0 重構規則最後一句）。

### 2.1 `user.password` 改成可為 NULL【使用者定：方案 A】

**為什麼**：V1 的 `user.password` 是 NOT NULL，所以現行 Google 新註冊（`backend/src/controllers/userinfo.js` 的 `post_user_LoginGoogle`）給每個 Google 會員存同一組 `DEFAULT_OAUTH_PASSWORD`（未設時 `'DefaultPassword123!'`）的 bcrypt。Email 登入不看登入方式，所以知道這組密碼的人能登入任何 Google 會員。`.env.example:26` 已公開這組值。

選 A（NULL）而不選 B（每人隨機密碼）的理由：寫漏時 `bcrypt.compare` 遇 NULL 會丟錯 → 失敗而非放行；「沒有密碼」在 DB 看得見、DB 層測試驗得到。

**行為規則**：
- Google 新註冊：`password` 存 NULL。移除 `DEFAULT_OAUTH_PASSWORD` 的使用（程式與 `.env.example`）。
- Email 登入遇 `password IS NULL`：拒絕，訊息明確說明這個帳號用 Google 登入（可用忘記密碼設定密碼）；**不累計** `login_attempts`、不觸發鎖定【Claude 定】。HTTP 狀態碼由實作者決定，與密碼錯誤一致即可。
- 會員中心改密碼（`patchuserresetprofilePW`，需要舊密碼）遇 NULL：拒絕，訊息引導改走忘記密碼。
- **忘記密碼保留**，對 Google 會員等於「設定密碼」的入口【使用者定】。設好後兩種方式都能登入。
- 任何其他讀 `user.password` 的地方都要處理 NULL（實作者 grep 確認）。

### 2.2 email 不分大小寫唯一【使用者定：方案 ③】

**為什麼**：V1 `user.email` 沒有 UNIQUE，註冊只靠 middleware「先查再新增」，同時送出會產生重複；驗證器不轉小寫，`Alice@` 與 `alice@` 會成為兩個帳號；有重複後 `WHERE email = $1` 取 `rows[0]` 結果不確定。

**做法**：
- migration：`CREATE UNIQUE INDEX ... ON "user" (lower(email))`。不改欄位型別（不用 citext，避免動到 `R__views_functions.sql:621`、`:746` 兩個 view 和契約型別）。
- 驗證器（`backend/src/utils/Validator/userInfo_Validator.js`）的 email 統一轉小寫；Google 回傳的 email 也轉小寫後再查詢 / 寫入。
- 查詢 email 的地方改成能命中大小寫不同的既有資料（`lower(email) = lower($1)` 或等價做法，實作者決定）。
- 寫入撞到 unique（Postgres `23505`）回 **409**，不是 500。保留原本「先查再新增」作為友善訊息，DB 限制是最後防線。
- seed 現有 3 個會員 email 皆為小寫、不重複，migration 不會失敗（P1 已有 seed email 不重複測試）。

### 2.3 Google 登入遇到已存在的 email【使用者定：方案 (a)】

- 自動綁定到既有帳號，並**把該帳號的 `password` 清成 NULL**。**只在第一次綁定時清**（該帳號還沒有 `provider_method='google'` 的 `socialLogin` 列）；已綁定過的會員之後再用 Google 登入不會清密碼，否則會抵銷 §2.1「用忘記密碼設好密碼後兩種方式都能登入」【Claude 定】。要有測試：Google 會員設密碼 → 再用 Google 登入 → Email 登入仍成功。
- 不回填既有資料【Claude 定】：migration 不把現有 Google 會員的密碼改成 NULL。理由：P7 部署從全新的 DB 開始，沒有要搬的舊資料；seed 的 alice（有 google `socialLogin` 列）、bob（`login_method=2`）兩人都有 `SEED_PASSWORD`（`tests/test_seed.py:69`），代表「Google 會員已設好密碼」這個合法狀態，保留。理由：Email 註冊不驗證信箱，攻擊者可先用受害者 email 註冊（預先劫持）；Google 證明了信箱所有權，清掉來路不明的密碼後攻擊者就進不來。
- 代價（已接受）：先 Email 註冊、後改用 Google 的真會員，原密碼失效，需再走忘記密碼。
- Google 回傳的 `email_verified` 不是 true → 一律拒絕登入（新註冊與綁定都適用）。
- `login_method` 的更新沿用現行邏輯。

### 2.4 `socialLogin.provider_token`【Claude 定】

不再存 Google 的 access_token（登入後用不到），寫 NULL，欄位保留不改型別。這同時解掉 P1 留下的 strict xfail（`tests/test_oauth_spike.py:68`，原因是 VARCHAR(255) 放不下 token）：該測試改寫成驗證新行為（例如 provider_token 為 NULL、provider_id 正確），並移除 xfail。

## 3. 後端安全修正

### 3.1 重設密碼 token 不能當登入 token【Claude 定】

**現況**：`post_user_forgetPW` 簽發 payload `{id}`、同一個 `JWT_SECRET`、15 分鐘，能通過所有只檢查 `auth`（`backend/src/middlewares/auth.js`）的路由；`auth_not_mandatory.js` 同理。15 分鐘內可重複使用。

**做法**：
- reset token 帶明確用途標記（例如 `purpose: 'reset'`）；`auth.js` 和 `auth_not_mandatory.js` 拒絕帶用途標記的 token（或只接受登入 token 的形狀，實作者決定判斷方式，但要用測試證明 reset token 打會員 API 回 401）。
- reset 端點只接受 reset token（登入 token 不能拿來重設密碼）。
- reset token 綁定簽發當下的密碼指紋（由當下 `password` 欄位推導，NULL 也有固定指紋）：密碼一改（包括 §2.3 綁 Google 時清成 NULL），舊連結失效 → 實質一次性。不加資料表。

### 3.1a 密碼變動時舊的登入 token 失效【使用者定】

**現況**：登入 token 只有 `{id, role}`、效期 `JWT_EXPIRES_DAY=30d`，無法撤銷。預先劫持的攻擊者在受害者綁 Google 前登入，token 可再用 30 天；一般會員改密碼後舊裝置也維持登入。

**做法**：登入 token（Email 登入、Google 登入、以及其他任何簽發登入 token 的地方）也帶簽發當下的密碼指紋，與 §3.1 同一套算法。`auth.js`、`auth_not_mandatory.js` 驗證 token 時查該會員目前的 `password` 算出指紋比對，不符即視為無效（401）。觸發失效的情況：忘記密碼重設、會員中心改密碼、§2.3 第一次綁 Google 時清成 NULL。代價（已接受）：每個需要登入的請求多一次 DB 查詢。

**測試**：每種觸發情況各一個「舊 token 打會員 API 回 401、新 token 可用」；預先劫持情境要驗證攻擊者先前取得的 token 失效。改密碼的人自己當下的 session 也會失效，前端要能導回登入頁（行為細節由實作者決定，但不能卡在錯誤畫面）。

### 3.2 驗證碼答案不再明文放 cookie【Claude 定】

**現況**：`get_user_captcha` 把答案明文放在 `captcha` cookie，`patchuserresetPW` 拿 cookie 比對 → 使用者可自設 cookie 繞過。

**做法**：cookie 存「答案（不分大小寫正規化後）＋到期時間」的 HMAC 簽章與到期時間，伺服器重算比對，不存明文、不新增資料表。已接受的限制：5 分鐘內同一組題目與答案可重送（驗證碼只用在重設密碼，該步驟本來就要 reset token）。HMAC 金鑰來源由實作者決定（新環境變數或由既有 secret 衍生，要寫進 `.env.example`）。

**cookie 屬性**（總 spec §4.3）：`SameSite`、`Secure` 改成環境變數可設定，CORS `credentials` 一併確認可設定；本機預設要能在 `http://localhost` 運作。

### 3.3 改角色 API 補 admin 檢查

`backend/src/routes/admin.js:26` 被註解的 `authRole('admin')` 打開。測試：一般會員呼叫回 403、admin 成功。（契約 §4.2 記錄的權限提升；P2 前不對外。）

### 3.4 帳號是否存在：不隱藏【Claude 定】

註冊必須回「Email 已被使用」，登入鎖定會回「帳號鎖定中」，所以在忘記密碼或登入隱藏帳號存在與否沒有實際保護效果。現行訊息保留。

### 3.5 Google 登入的其他規則

- 用 compose 既有的 `mock-oauth`（`ghcr.io/navikt/mock-oauth2-server:2.1.10`）代替 Google（P0 已接好，`tests/test_oauth_spike.py`）。mock 的 claims 要補 `email_verified: true`，並準備一組 `email_verified: false` 的情境供測試（mock-oauth2-server 的設定方式由實作者決定）。
- 前端的 Google 按鈕走 `VITE_GOOGLE_AUTH_URL`（`frontend/src/views/admin/loginPage.vue`，已可設定），本機指向 mock。
- 真的 Google 帳號（client id / secret）不在 P2 範圍，留到 P7 部署；`.env.example` 維持 mock 的值。
- **順序**【使用者定】：Google 登入放在 P2 最後實作；Email 的註冊 / 登入 / 忘記密碼不依賴它。

## 4. 前端

### 4.1 路由與登入檢查（`frontend/src/router/index.js`、`frontend/src/utils/api.js`）

- **恢復登入檢查**：檔案內已有 `requireAuth`（呼叫 `api.get_user_status()`），但沒有路由使用。接到會員中心相關路由：`/admin/userprofile`、`/admin/collect`、`/admin/personalOrder`。`/admin/manage/*` 留給 P6。
- **重複的 `search` name**：路由表有兩個 `name: 'search'`（`:75` 在首頁 layout 底下、`:197` 在頂層），保留一個、另一個移除或改名，確保 `/search` 行為不變。
- 檔案中整段註解掉的舊路由表（約 `:203` 起）：刪除與否屬於重構，依 §7 規則處理。
- **404 catch-all**：新增，導到一個簡單的 404 頁（樣式由實作者決定，沿用現有 layout）。
- **`window.location.href` 改成 router 跳轉**：hash 模式下 `window.location.href = '/admin/...'` 會整頁重載並落到首頁，而不是目標頁。`api.js:35`、`:207`（→ `/admin/login`）、`:85`、`:135`（→ `/admin/userprofile`）、`HeaderReal.vue:148`、`HeaderComponent.vue:148`（→ `/`，整頁重載）改成 `router.push`（或等價）。`loginPage.vue:160` 是導向 Google（外部網址），**保留**。
- **hash 模式下的外部回跳網址**【Claude 定】：router 用 `createWebHashHistory`（`router/index.js:24`），維持 hash 模式（P7 前端預計 GitHub Pages）。以下兩個流程目前從瀏覽器走不通，P2 要修好：
  - 重設密碼信的連結是 `${FRONTEND_PATH}/admin/resetpw?token=…`（`controllers/userinfo.js` 的 `post_user_forgetPW`），`resetpwPage.vue:104` 讀 `window.location.search` → 實際落到首頁、拿不到 token。改成能進到 `#/admin/resetpw` 並讀到 token 的網址形狀（例如 `/#/admin/resetpw?token=…` 並從 route query 讀）。
  - Google 回跳 `VITE_Redirect_BASE` / `GOOGLE_REDIRECT_URI` 是 `http://localhost:5173/`，只有 `loginPage.vue:108` 讀 `?code`，但 `/` 不是登入頁。改成回跳後能由登入頁（或專用的回跳頁）讀到 `code`。注意 Google 的 redirect_uri 不能帶 `#`，code 會出現在 `#` 前的 query，前端要從 `window.location.search` 讀並在進入 router 前或登入頁處理。
  - 兩處的網址組法連同 `.env.example`、`frontend/.env.development`、`frontend/.env.example` 一起更新。
- **登入回應的頭像欄位**：`controllers/userinfo.js:113`、`:351` 回 `avatar_url: user.picture`（`user` 表沒有 `picture`），Email 登入後頭像永遠是 null。改成 `user.avatar_url`。
- **`api.js:306` `throw err`**：變數名錯（catch 參數是 `error`），會變成 ReferenceError；改正。實作者順手檢查同檔其他 catch 是否有同類錯誤，有就一起修並列入報告。
- FB 登入圖示（`loginPage.vue:70`）移除或標示「未開放」。

### 4.2 會員中心的切法【使用者定】

`frontend/src/views/admin/userprofilePage.vue` 有四個分頁（`tabs`，約 `:174`），但**只有「會員資訊」有內容**；三個偏好的下拉選單放在這個分頁裡（約 `:56-72`）；頁面沒有上傳頭像的介面，也沒呼叫 `/pointslevel`。

P2 採**縮小版**【使用者定，2026-11-12 選 (b)】：
| 分頁 | P2 要做到 |
|---|---|
| 會員資訊 | 讀取與修改姓名（email 唯讀）、三個偏好**留在原位**讀取與修改、改密碼（§2.1 NULL 情況、§3.1a 改完後的導向）、**新增頭像上傳**（`PATCH /api/v1/user/userinfo/avatar` 已存在），上傳後頁面與 header 顯示新頭像 |
| 個人偏好設定 | 標示「即將開放」，不做內容 |
| 會員等級 | 標示「即將開放」，P5 與點數一起做 |
| 個人訂單查看 | 標示「即將開放」，P5 |

不搬動既有元件結構（避免觸發重構規則）。之後階段再在這些分頁上補內容與測試（使用者原話：「先這樣切，後續在實作測試內容上去就行」）。

## 5. 測試

照總 spec §4.1（紅燈先、單獨 commit，紅燈輸出存起來放報告）與 §4.2 分層。P2 至少要覆蓋：

| 層 | 內容 |
|---|---|
| API 契約 | 每個會員 API 的正常、驗證錯誤、401/403 |
| 安全 | 共用密碼登入 Google 會員失敗；reset token 打會員 API 回 401；密碼變動後舊登入 token 回 401（§3.1a 三種觸發）；reset token 用過（密碼改過）後失效；改 captcha cookie 無法繞過；一般會員改角色回 403；預先劫持情境（攻擊者先註冊 → 受害者 Google 登入 → 攻擊者原密碼失效）；`email_verified: false` 被拒 |
| DB 狀態 | Google 新會員 `password IS NULL`；綁定後既有帳號 `password` 變 NULL；`provider_token` 為 NULL；大小寫不同 email 註冊被擋（409）；同時送出兩個相同 email 的註冊只成功一筆；migration 後的 schema（nullable、unique index）有契約測試 |
| E2E（Playwright Python，放 `e2e/`） | 主線：註冊 → 登入 → 會員中心看到自己的資料、改偏好、改密碼；未登入開會員中心被擋回登入頁；密碼錯 3 次鎖定訊息；忘記密碼 → 從 Mailpit 取信中的連結 → 重設密碼 → 用新密碼登入【Claude 定】。Google 登入的 E2E 經 mock-oauth 走一次（若 mock 的授權頁無法由 Playwright 操作，降為 API 層測試並記入報告）【Claude 定】 |

- 每個測試用 fixture 自建資料，不依賴 seed 狀態（總 spec §4.2）。
- `tests/conftest.py` 的 `delete_user` 目前只清 11 張 FK 表中的 3 張（P1 ruling）；P2 測試若會寫入其他 FK 表，先補齊。
- E2E 要能在 CI 跑（目前 CI 只有 pytest；加 Playwright 的方式由實作者決定，需在計畫中列出）。

## 6. P1 遺留待辦（P2 開工時處理）

1. strict xfail `tests/test_oauth_spike.py:67`（provider_token；decorator 的 reason 寫「P2 以 migration 修正」，實際改由 §2.4 寫 NULL 解掉，不做 migration）。
2. strict xfail `tests/test_api_smoke.py:408`（`GET /admin/product` 500，`backend/src/middlewares/product/index.js:296` 的 `tour_ids`、`:312–315` 的 Promise `.rows`）→ 修好、移除 xfail。雖屬後台，但修法小、測試已在，放 P2。
3. carol 的優惠卷測試在 seed 載入 133 天後會紅 → 加 skip guard 或改成不依賴日期（實作者決定）。
4. `R__views_functions.sql` 寫死 DROP 簽名、`tests/db_contract.py` 不會自動對照契約文字（`docs/reports/phase-1.md` 附錄 B）→ P2 若動到這兩個檔（§2 會動契約）就順手處理；沒動到就留在已知限制，於 P2 報告重申。【Claude 定】

## 7. 流程與約束（沿用總 spec）

- 重構規則（總 spec §0）：先有測試、計畫中列成獨立 Task、獨立 commit。本設計中屬重構的：刪除註解掉的舊路由表、任何非修 bug 必要的程式整理。
- git：backend `main`、frontend `dev` 各開 `phase-2` feature branch；完成後 merge、打 `phase-2` tag、更新 `refs.env` 與 README 版本對照表；**只 push 到 nohungry fork**，每個對外動作先問使用者。
- 模型分工：Sonnet 實作、卡關升 Opus、Fable + Opus 平行 review。
- 報告 `docs/reports/phase-2.md`，照總 spec §5 範本；使用者確認後才進 P3。

## 8. 完成標準

- §0 的主線能從前端完整操作，E2E 覆蓋並在 CI 綠燈。
- §2、§3 每一項都有紅燈 → 綠燈的測試證明。
- P1 的兩個 strict xfail 移除；舊測試不退化。
- `docs/db-contract.md` 與契約測試反映 §2 的 schema 變更。
- 雙模型 review 沒有未處理的 Critical / Important。
- 報告定稿。

## 9. 留給實作者決定

migration 編號與拆分；HTTP 狀態碼細節（在 §2–3 未指定處）；HMAC 金鑰來源；reset token 的判斷方式與密碼指紋算法；mock-oauth 的 `email_verified: false` 情境設定；404 頁樣式；CI 加 Playwright 的方式；Task 切分與順序（Google 必須最後）。
