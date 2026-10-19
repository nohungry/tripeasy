# Phase 0：地基
> 2026-10-19（定稿） · backend tag `phase-0`（merge commit `9005a06`；分支最後一個 commit `6e182fb`） · frontend tag `phase-0`（merge commit `e3ad994`；分支最後一個 commit `32cfb59`）
>
> tag 打在 `main` / `dev` 的 `--no-ff` merge commit 上；括號內為 `phase-0` 分支最後一個 commit。

## 0. 摘要

P0 的目標：一行 `docker compose up` 起得來整套服務（postgres、flyway、backend、frontend、mailpit、mock-oauth），外部服務（Firebase、SendGrid、Google OAuth）都有本機替身，pytest 與 `ci.sh` 是綠燈（GitHub Actions 待 push 後驗證）。

另外，Task 1–2 是前置工程：Task 1 建立總覽 repo 骨架與 `refs.env`；Task 2（backend `94240dd`）加入 lockfile、Dockerfile 拆成 dev / prod multi-stage、修正 compose healthcheck、移除固定 IP。

| 項目 | 結果 |
|---|---|
| 測試數量 | P0 前 0 → 現在 **13 passed + 1 xfailed**（共 14 個，xfail 為 `strict=True`，Task 7 結論 B） |
| 紅燈 → 綠燈 | 7 個紅燈 commit（Task 3、4、4 修正輪、5、6、7、8）→ 6 個綠燈 commit（5 個修正 + 1 個為 spike 而做的 URL 設定化 `6e182fb`；Task 3 與 Task 4 共用 `aa21bf8`） |
| CI 結果 | `scripts/ci.sh` 從乾淨狀態（`down -v`）和保留 volume 兩種情況都是 13 passed, 1 xfailed；第二次 Flyway 回報 `Schema "public" is up to date. No migration necessary.` |
| backend 變更 | 17 檔（含 8207 行 lockfile），原始碼只動 10 個檔案 |
| frontend 變更 | 4 檔，+15 −7 |
| 升級 Opus 實作 | 無 |

Commit 範圍（皆已以 `--no-ff` 合併進 backend `main`、frontend `dev`、總覽 `main`，尚未 push）：

- 總覽 repo（`main..phase-0`）：`0f2fd6a` → `6edc729`，共 10 個 commit
  - `0f2fd6a` test 🔴 compose 骨架 + health（Task 3）
  - `0b457ef` test 🔴 本機 storage 上傳（Task 4）
  - `d32978b` test 🔴 `/uploads` 缺安全 header（Task 4 修正輪）
  - `c644d28` test 🔴 忘記密碼信（Task 5）
  - `6ad8078` test 🔴 async rejection crash（Task 6）
  - `41d4367` test 🔴 Google 登入改走 mock（Task 7）、`175ee19` / `59c36a9` spike 結論文件
  - `fdb8cb6` test 🔴 前端 `VITE_API_BASE`（Task 8）
  - `6edc729` ci：本機與 GitHub Actions 共用的 `ci.sh`（Task 9）
- backend（`main..phase-0`）：`94240dd` build、`aa21bf8` storage、`47926b1` /uploads 安全、`47870c8` mailer、`972e469` async、`6e182fb` OAuth URL，共 6 個
- frontend（`dev..phase-0`）：`32cfb59` 1 個（frontend 的基底分支是 `dev`，不是 `main`）

一個誠實的說明：Task 3 的 health 紅燈與 Task 4 的 storage 紅燈**同一個根因**（Firebase 金鑰缺失導致 backend 載入時 crash），Task 3 的測試是在 Task 4 的修正 commit `aa21bf8` 才轉綠。

## 1. 問題與修正

行號皆為修正前（`main` / `dev`）的原始碼。紅燈輸出存在 `evidence/phase-0/`。

### 1.1 Task 3：沒有 Firebase 金鑰，backend 一載入就 crash（health 紅燈）

**現象**：`docker compose up` 後 backend 反覆重啟，`GET /api/v1/health` 連線被關閉。

**根因**：`backend/src/config/firebase.js:4-6` 在模組載入時就檢查 `FIREBASE_SERVICE_ACCOUNT`，沒設就 `throw`；`:19` 也在載入時呼叫 `admin.storage().bucket()`。而 `controllers/userProfile.js:3` 在 server 啟動時 `require('../config/firebase')`，於是少一把金鑰整個 process 掛掉，連跟圖片無關的 health 都打不開。

**紅燈輸出**（[task3-health-red.txt](evidence/phase-0/task3-health-red.txt)）：

```
tests/test_health.py::test_health_ok FAILED
E   requests.exceptions.ConnectionError: ('Connection aborted.', RemoteDisconnected('Remote end closed connection without response'))
```

backend log（取自執行當下，未存入 evidence）：`Error: Missing FIREBASE_SERVICE_ACCOUNT environment variable` at `src/config/firebase.js:5`，接著 `[nodemon] app crashed`。

**修正**：見 1.2（同一個修正 `aa21bf8` 讓它轉綠）。Task 3 的 commit 只有測試與 compose 骨架（`0f2fd6a`，紅燈）。

**綠燈**：Task 4 修正後 `test_health_ok` PASSED；兩個 Flyway migration 測試在 Task 3 當下就已通過（2 passed），證明 V1（25 張表）、V2 有套用。

### 1.2 Task 4：Firebase 改成延遲初始化 + 本機 storage adapter

**現象**：同 1.1；另外本機沒有 Firebase 就無法測任何上傳。

**根因**：同 1.1，加上 `userProfile.js` 的頭像上傳直接綁死 Firebase bucket（`patch_userProfile_Photo`，建立 blob、寫入、組 `firebasestorage.googleapis.com` 網址）。

**紅燈輸出**（[task4-storage-red.txt](evidence/phase-0/task4-storage-red.txt)，2 個測試）：

```
tests/test_storage.py::test_avatar_upload_stored_locally FAILED
tests/test_storage.py::test_upload_filename_cannot_escape_upload_dir FAILED
============================== 2 failed in 0.29s ==============================
```

**修正**（backend `aa21bf8`，7 檔 +138 −93）：

```
 src/config/firebase.js         | 29 ++++++++++++-------
 src/controllers/userProfile.js | 43 ++++++++++------------------
 src/server.js                  |  1 +
 src/utils/firebaseUpload.js    | 65 +++++++-----------------------------------
 src/utils/storage/firebase.js  | 31 ++++++++++++++++++++
 src/utils/storage/index.js     | 17 +++++++++++
 src/utils/storage/local.js     | 45 +++++++++++++++++++++++++++++
```

關鍵片段：`firebase.js` 由「載入時檢查」改成「第一次用才初始化」，模組改為匯出 `getBucket()`：

```js
-if (!process.env.FIREBASE_SERVICE_ACCOUNT) {
-  throw new Error('Missing FIREBASE_SERVICE_ACCOUNT environment variable');
-}
+function getBucket() {
+  if (bucket) return bucket;
+  if (!process.env.FIREBASE_SERVICE_ACCOUNT) {
+    throw new Error('Missing FIREBASE_SERVICE_ACCOUNT environment variable');
+  }
```

`utils/storage/index.js` 依 `STORAGE_DRIVER`（預設 `firebase`，維持原本行為；本機 `.env.example` 設 `local`）選 adapter；`local.js` 把檔案寫進 `UPLOAD_DIR`，`server.js` 以 `/uploads` 提供。`safeKey()` 對路徑每段只保留安全字元、移除 `.` 與 `..`，`resolveInside()` 再檢查結果仍在 `UPLOAD_DIR` 內。

**綠燈**：health、兩個 storage 測試通過（3 passed）；全套 5 passed。Review Focus #2 驗證：`STORAGE_DRIVER=firebase` 且沒有金鑰時 backend 正常開機，只有在真的上傳時才 reject：`rejected: Missing FIREBASE_SERVICE_ACCOUNT environment variable`。

#### 1.2.1 修正輪 1：`/uploads` 的 stored XSS（雙模型 review 只有 Fable 抓到）

**現象**：上傳檔名 `x.html`、內容 `<script>…</script>` 後，從 API 網域直接打開該 URL，瀏覽器會把它當網頁執行。

**根因**：上一個修正新增的 `app.use('/uploads', express.static(...))`（`server.js`）依副檔名決定 `Content-Type`，而副檔名來自使用者的檔名；`.html` / `.svg` 因此成為 API 同源的可執行內容。

**紅燈輸出**（[task4-uploads-xss-red.txt](evidence/phase-0/task4-uploads-xss-red.txt)，overview `d32978b`）：

```
>       assert got.headers["X-Content-Type-Options"] == "nosniff"
E       KeyError: 'x-content-type-options'
========================= 1 failed, 2 passed in 0.14s ==========================
```

**修正**（backend `47926b1`，`server.js` +10 −1）：

```js
express.static(require('./utils/storage/local').UPLOAD_DIR, {
  setHeaders: (res) => {
    res.set('X-Content-Type-Options', 'nosniff');
    res.set('Content-Security-Policy', "default-src 'none'; sandbox");
  },
})
```

**綠燈**：`test_uploaded_file_cannot_run_as_page` 通過。這是計畫沒寫、由 review 發現後加碼的修正，已記錄在 ledger 裁定中。

### 1.3 Task 5：忘記密碼信寫死 SendGrid

**現象**：本機沒有 SendGrid 金鑰，`POST /api/v1/auth/userinfo/forgetpw` 回 500。

**根因**：`controllers/userinfo.js:3` 直接 `require('@sendgrid/mail')`，`:260` `sgMail.setApiKey(process.env.SENDGRID_API_KEY)`、`:264` `await sgMail.send(...)`，沒有任何可替換的出口。金鑰是空字串，SendGrid 丟錯，被外層 catch 轉成 500。

**紅燈輸出**（[task5-mail-red.txt](evidence/phase-0/task5-mail-red.txt)）：

```
>       assert r.status_code == 200, r.text
E       AssertionError: {"status":"error","message":"伺服器錯誤"}
E       assert 500 == 200
```

**修正**（backend `47870c8`：`utils/mailer.js` 新增 32 行，`userinfo.js` +2 −5，`package.json` 加 `nodemailer`）：

```js
// utils/mailer.js
const driver = process.env.MAIL_DRIVER || 'sendgrid';   // 預設維持原本行為
if (driver === 'smtp') { /* nodemailer → SMTP_HOST:SMTP_PORT（本機是 Mailpit） */ }
```

`userinfo.js` 改成 `await mailer.send({ to, subject, html })`，`from` 與 API key 由 adapter 處理。

**綠燈**：`test_forget_password_sends_reset_mail` 通過：Mailpit 收到恰好 1 封、主旨 `TripEasy 密碼重設連結`、內文含 `resetpw?token=`。

### 1.4 Task 6：try 外面的 async rejection 會讓整個 server 掛掉

**現象**：`POST /api/v1/user/newebpay/payment` 帶空 body，整個 backend process 結束，後續所有請求都連不上。

**根因**：Express 4 不會接住 async handler 的 rejection。`controllers/newebpay.js:59`（`order_items.reduce(...)`，`order_items` 為 undefined）在 `try` 之前執行，拋出 `TypeError: Cannot read properties of undefined (reading 'reduce')`，變成 unhandled rejection，Node 預設直接終止 process。Fable 在 review 時逐一稽核了 30 處 `next(err)`，都在 catch 內，目前沒有發現第二處；但這種寫法新程式很容易再踩，所以改成全域處理。

**紅燈輸出**（[task6-async-red.txt](evidence/phase-0/task6-async-red.txt)）：

```
tests/test_async_errors.py::test_rejection_outside_try_returns_500_and_server_survives FAILED
E   requests.exceptions.ConnectionError: ('Connection aborted.', RemoteDisconnected(...))
```

backend log（取自執行當下，未存入 evidence）：`TypeError: Cannot read properties of undefined (reading 'reduce')` at `newebpay.js:59`，`[nodemon] app crashed`。

**修正**（backend `972e469`，`server.js` +2、`package.json` 加 `express-async-errors`）：

```js
const express = require('express');
// Express 4 不會接住 async handler 的 rejection；這個套件把它導到既有的 error handler
require('express-async-errors');
```

**綠燈**：測試要求「回 500、`status == "error"`、且之後 `/health` 仍 200」，通過；backend 維持 `Up (healthy)`，log 顯示 TypeError 經過 `express-async-errors` 後被既有 error handler 處理。全套 8 passed。

### 1.5 Task 7：mock-oauth2-server 能不能取代 Google（spike，結論 B）

**現象 / 目的**：本機沒有 Google client，登入流程無法測。這是個「可行性調查」而非 bug 修正。

**根因（為何 backend 打不到 mock）**：`middlewares/userinfo/index.js:146` 與 `:163` 把 `https://oauth2.googleapis.com/token`、`https://www.googleapis.com/oauth2/v3/userinfo` 寫死。

**紅燈輸出**（[task7-oauth-red.txt](evidence/phase-0/task7-oauth-red.txt)）：

```
>       assert r.status_code == 200, r.text
E       AssertionError: {"status":"failed","message":"Google 驗證失敗，請檢查您的授權碼或後端憑證設定。"}
E       assert 401 == 200
========================= 1 failed, 1 passed in 0.59s =========================
```

（同檔另一個測試 `test_mock_oauth_issues_google_like_claims` 直接驗證 mock 發出的 claims，一開始就通過。）

**修正**（backend `6e182fb`，`middlewares/userinfo/index.js` +2 −2）：

```js
-      'https://oauth2.googleapis.com/token',
+      process.env.GOOGLE_TOKEN_URL || 'https://oauth2.googleapis.com/token',
...
-    const userInfoRes = await axios.get('https://www.googleapis.com/oauth2/v3/userinfo', {
+    const userInfoRes = await axios.get(process.env.GOOGLE_USERINFO_URL || 'https://www.googleapis.com/oauth2/v3/userinfo', {
```

**結果：B（可行，但有已知 schema 限制）**。token 交換和 userinfo 都成功（401 → 500，代表通過了這兩步）；之後寫入 `socialLogin` 時失敗：

```
error: value too long for type character varying(255)
    at async post_user_LoginGoogle (/usr/backend/src/controllers/userinfo.js:192:7)
```

mock 的 access token 是 740 字元的 JWT，超過 `socialLogin.provider_token VARCHAR(255)`。依計畫，P0 不改 schema，該測試標 `xfail(strict=True)`：P2 把欄位改成 TEXT 後會 XPASS 並讓測試失敗，提醒移除標記。完整結論見 [task7-oauth-spike.md](evidence/phase-0/task7-oauth-spike.md)。

**綠燈**：`9 passed, 1 xfailed`（Task 8 加入前端測試後為 13 passed, 1 xfailed），xfail 原因 `socialLogin.provider_token 為 VARCHAR(255)，放不下 JWT access token；P2 以 migration 修正`。

### 1.6 Task 8：前端 `VITE_API_BASE` 沒有任何預設值（含寫死的 Google client id）

**現象**：本機起前端後，所有 API 請求打到 `undefined/api/v1/...`。

**根因**：`frontend/src/utils/api.js:5` 讀 `import.meta.env.VITE_API_BASE`，但 repo 裡 `.env.development` 只有 `VITE_BASE_URL=/`；`.env.example` 的值是 placeholder。同時 `views/admin/loginPage.vue:154` 把 Google client id 寫死在原始碼、`:158` 把授權網址寫死，無法導向 mock。

**紅燈輸出**（[task8-frontend-red.txt](evidence/phase-0/task8-frontend-red.txt)）：

```
>       assert "http://localhost:3000" in r.text
E       assert 'http://localhost:3000' in 'import.meta.env = {"BASE_URL": "/", "DEV": true, ..., "VITE_BASE_URL": "/"};...
        const baseUrl = import.meta.env.VITE_API_BASE;
========================= 1 failed, 3 passed in 0.06s =========================
```

另外 3 個測試（dev server 可存取、CORS 放行前端 origin、CORS 拒絕未知 origin）一開始就是綠燈，作為回歸基準。

**修正**（frontend `32cfb59`，4 檔 +15 −7）：

```
 .env.development              | 6 +++++-
 .env.example                  | 4 +++-
 .env.production               | 3 ++-
 src/views/admin/loginPage.vue | 9 +++++----
```

`.env.development` 加上 `VITE_API_BASE=http://localhost:3000`、`VITE_Redirect_BASE`、`VITE_GOOGLE_CLIENT_ID=tripeasy-local`、`VITE_GOOGLE_AUTH_URL=http://localhost:8090/google/authorize`；`loginPage.vue` 改為：

```js
const googleClientId = import.meta.env.VITE_GOOGLE_CLIENT_ID;
const authUrl = import.meta.env.VITE_GOOGLE_AUTH_URL || 'https://accounts.google.com/o/oauth2/v2/auth';
// 節錄；組網址時 client_id 與 redirect_uri 另外套 encodeURIComponent
```

（`.env.production` 保留原本的 client id 作為正式環境值，不再寫死在原始碼。）

**綠燈**：重啟 frontend 後 `13 passed, 1 xfailed`。Review Focus #5 的 `test_cors_rejects_unknown_origin` 通過，但它只斷言「回應不帶 `Access-Control-Allow-Origin`、server 還活著」；實際上未知 Origin 仍回 500（已知問題，見附錄）。

## 2. Vibe coding 工作流

### 2.1 使用的 skill

| 階段 | Skill | 產出 |
|---|---|---|
| 設計 | `superpowers:brainstorming` | `docs/superpowers/specs/2026-10-15-tripeasy-rebuild-design.md` |
| 計畫 | `superpowers:writing-plans` | `docs/superpowers/plans/2026-10-16-p0-foundation.md`（10 個 Task） |
| 執行 | `superpowers:subagent-driven-development` | 每個 Task 一個 implementer + 雙 reviewer |

### 2.2 每個 Task 的流程與 prompt 設計

1. controller 把計畫中該 Task 的原文加上 Global Constraints 抽成 **brief 檔**；
2. **Sonnet implementer** 讀 brief 實作、commit、寫 report 檔；
3. controller 打包兩個 repo 的 diff 成 review package；
4. **Fable 與 Opus 平行 review**（spec compliance + code quality，findings 分 Critical / Important / Minor，並標註是「計畫要求」還是「implementer 偏離」）；
5. 需要修就 resume 同一個 implementer，修完由 Opus 做範圍限定的 re-review。

關鍵 prompt 設計：

- brief 是唯一的需求來源，exact values 只放在 brief；dispatch 訊息只帶「前面 Task 產出、brief 不知道的介面」。
- implementer 禁止自己再開 subagent 或 reviewer。
- report 一律寫檔，回覆限 15 行。
- reviewer 被要求「報告太薄就自己重跑驗證」。

### 2.3 Fable vs Opus review 對照

| Task | Fable | Opus | 兩邊共同 | 備註 |
|---|---|---|---|---|
| 1 | Approved；建議以 `.git/info/exclude` 排除 `.claude/` | Approved；誤報「全域 git identity 可能被改」 | 都誤報 README 的 backend / frontend 連結會失效（其實是既有 fork） | controller 查證後駁回兩個誤報 |
| 2 | Approved；`.dockerignore` 沒排除 Dockerfile / compose、healthcheck 依賴 curl | Approved；prod image 以 root 執行 | 舊 backend compose 沒指定 build target | |
| 3 | Approved | Approved；evidence 檔含本機絕對路徑 | `delete_user` 只清 11 張關聯表中的 3 張（Important，計畫要求，延到 P2 前修） | |
| 4 | **Changes requested**：`/uploads` 以副檔名提供使用者上傳檔，`.svg` / `.html` 可在 API 網域執行 script（stored XSS） | Approved | 路徑穿越測試其實被 busboy 擋掉、沒測到 `safeKey`；中文檔名被 multer 以 latin1 解碼成亂碼 | XSS 只有 Fable 抓到 → 修正輪 1（nosniff + CSP sandbox）；Opus re-review 誤報 `backend/.claude` 存在 |
| 5 | Approved；實際查 Mailpit 收件匣確認重設信 | Approved | `MAIL_FROM` 覆蓋 SendGrid 寄件人，切 sendgrid 時要注意（P7） | |
| 6 | Approved；逐一稽核 30 處 `next(err)` 都在 catch 內、手動打 API 驗證；Express 5 時移除套件 | Approved；error handler 沒檢查 `res.headersSent` | `err.status` 存在時會把 `err.message` 回給前端；測試只驗 status 沒驗 message | |
| 7 | Approved；實測 mock JWT 長 740 字元；`provider_token` 從未被讀回 | Approved；**指出結論文件「Google token 較短所以線上沒問題」沒有根據** | mock-oauth 綁 0.0.0.0；正式環境若沿用 `.env.example` 的 `GOOGLE_*_URL` 會變成任意登入 | controller 依 Opus 意見改了那一行（`59c36a9`） |
| 8 | Approved；驗 Vite `allowedHosts` / `fs.deny`；OAuth redirect 落在首頁 | Approved | 前端正式 build 從未在 repo 設 `VITE_API_BASE`；`VITE_GAS_URL` 無定義 | 兩邊都用組出的網址打 mock-oauth 拿到 302 |
| 9 | Approved；沒有 `.python-version`（psycopg-binary 只有 cp310–313 wheel）；curl 沒 `--max-time` | Approved；`ci.yml` 沒 `timeout-minutes` / `permissions` | **Important：push 順序必須 backend → frontend → 總覽**（計畫 Task 10 已涵蓋） | 兩邊都確認 fork 是 public、CI 不缺 gitignored 檔 |

觀察：Fable 傾向做 live 驗證，抓到唯一一個 Important 級的安全問題（Task 4）；Opus 抓到文件中未經驗證的斷言（Task 7）。兩邊各有誤報，由 controller 查證後駁回，所以雙 review 的價值在於互補，而不是任一邊單獨可靠。

### 2.4 升級 Opus 實作的紀錄

無。沒有任何 Task 連續修兩次仍紅燈。唯一的 fix round 是 Task 4 的 `/uploads` 修正（1 輪即通過）。

### 2.5 AI 出錯 / 人介入紀錄

- **git 身分**：WSL 沒有全域 git 身分，controller 先設 repo-local；使用者指出應該有全域設定，查明只存在 Windows 端，依使用者指示改設 WSL 全域。
- **Task 2**：計畫 Step 6 的 `docker compose config -q` 因舊 compose 的 profile 問題失敗（既有問題）；controller 裁定用 `--profile tools` 驗證、不改 profile，列入已知問題。
- **Task 4**：計畫的 `git add src/utils/storage` 會被 `backend/.gitignore` 的 `*local.js` 靜默略過 `local.js`，pre-flight 掃描就抓到，改用 `git add -f`，不動 `.gitignore`。
- **Reviewer 誤報 3 次**（見對照表 Task 1 兩次、Task 4 一次），皆由 controller 查證駁回。
- **Task 7**：implementer 在結論文件寫了未驗證的斷言，經 Opus 指出後 controller 修正。implementer 的 report 缺 GREEN 輸出與 self-review，兩位 reviewer 自行重跑驗證補足；Task 8 起 dispatch 明確要求附上。
- **人工確認節奏**：使用者全程逐 Task 確認（「繼續 TaskN」）才往下。

## 3. 測試方法

### 3.1 分層與數量

| 檔案 | 層級 | 測試數 | 對應 |
|---|---|---|---|
| `test_migrations.py` | DB 直連 | 2 | Flyway 套用 V1、V2，25 張表齊全 |
| `test_health.py` | API | 1 | Task 3 |
| `test_storage.py` | API + HTTP | 3 | Task 4 + 修正輪 |
| `test_mail.py` | API + Mailpit API | 1 | Task 5 |
| `test_async_errors.py` | API | 1 | Task 6 |
| `test_oauth_spike.py` | API + mock | 2（1 passed、1 xfail） | Task 7 |
| `test_frontend.py` | HTTP | 4 | Task 8 |

全部測試都是 Python 從外部打 HTTP 和 DB，不 import backend 程式碼，所以同一份測試日後可以對重寫後的 backend 繼續使用。

### 3.2 `conftest.py` 設計

- **`Api` 預設 timeout**：`requests.Session` 子類別，`request()` 一律 `setdefault("timeout", 10)`，路徑以 `/` 開頭時自動接上 base。為了避免 backend 卡住時測試無限等待（Task 6 的 crash 場景就是這種情況），也讓測試碼可以只寫 `api.get("/api/v1/health")`。
- **`make_user` 的清理**：fixture 直接 `INSERT` 一個 `p0-<uuid>@example.com` 的使用者（不經過註冊 API，避免依賴被測功能本身），把 id 記在 list 裡，teardown 時用 `delete_user()` 依 FK 順序先刪 `socialLogin` / `point_record` / `user_level` 再刪 `user`。email 帶 uuid，所以並行或重跑都不會互相污染，Mailpit 的 `to:` 搜尋也能精準對到。
  已知限制：`delete_user` 只清 3 張子表（見附錄）。
- **`auth_header`**：用 `JWT_SECRET` 自己簽一個跟 backend 登入時相同 payload（`{id, role}`）的 HS256 token，需要登入的 API 測試不必每次跑登入流程。
- 所有 base URL（`TEST_API_BASE` 等）與 DB 連線都可由環境變數覆寫，預設值對應 compose 的 port mapping。

### 3.3 紅燈 / 綠燈分開 commit

每個修 bug 的 Task（3–8）先 commit 一個 `test: … 🔴`，再 commit `fix:/feat: … 🟢`（Task 3 與 4 共用 `aa21bf8`）。紅燈 commit 含測試、紅燈證據，以及該 Task 需要的 compose / env 設定；修正程式碼一律在 backend / frontend repo 的 🟢 commit。紅燈輸出存成 `docs/reports/evidence/phase-0/<task>-red.txt`，讓讀者不必重現就能看到「修之前真的是壞的」。合併後，`main` 的 first-parent 線上每個 commit 都是全綠，紅燈 commit 只出現在 `--no-ff` 合併進來的 `phase-0` 側線上。

### 3.4 `ci.sh` 本機與 CI 共用

`scripts/ci.sh`：`docker compose up -d --build --renew-anon-volumes` → 對 backend / frontend / mailpit / mock-oauth 各做最多 90 次輪詢 → `uv sync --frozen` → `uv run pytest -v`；任一 `wait_for` 逾時才印出 `docker compose ps -a` 與 log；pytest 失敗時則由 `ci.yml` 收集 compose logs 上傳。`.github/workflows/ci.yml` 只負責依 `refs.env` checkout 三個 repo 再呼叫同一支腳本，所以「我機器上是綠的」與 CI 的環境差異最小。

驗證結果（Task 9）：

- 乾淨狀態（`down -v`）：4 個服務 ✅，13 passed, 1 xfailed，exit 0
- 保留 volume（`down`）：同上；Flyway 回報 `Schema "public" is up to date. No migration necessary.`（Review Focus #1）
- 尚未驗證：GitHub Actions 上的實際執行（要等 Task 10 Step 5 push 後才跑得到）

## 4. 操作指南

### 4.1 切到這個版本並啟動

```bash
git clone https://github.com/nohungry/tripeasy.git && cd tripeasy
git clone -b "$(grep BACKEND_REF refs.env | cut -d= -f2)" https://github.com/nohungry/tripeasy-backend.git backend
git clone -b "$(grep FRONTEND_REF refs.env | cut -d= -f2)" https://github.com/nohungry/tripeasy-frontend.git frontend
scripts/ci.sh        # 啟動全部服務並跑測試
```

（上述 clone 指令需等 P0 push 到 GitHub 之後才能使用；目前僅存在本機。）

需要 Docker（含 Compose v2）和 [uv](https://docs.astral.sh/uv/)。`refs.env` 目前是 `BACKEND_REF=phase-0`、`FRONTEND_REF=phase-0`，合併後這兩個名字會解析成同名 tag。`ci.sh` 第一次會把 `.env.example` 複製成 `.env`。

| 服務 | 網址 |
|---|---|
| 前端 | http://localhost:5173 |
| API | http://localhost:3000/api/v1/health |
| Mailpit（收信） | http://localhost:8025 |
| mock Google OAuth | http://localhost:8090/google/.well-known/openid-configuration |

只想看畫面、不跑測試：`docker compose up -d`，需要 `.env`（`cp .env.example .env`）。

### 4.2 手動體驗

以下指令都已在 phase-0 的執行環境實際跑過。先設定共用變數：

```bash
B=http://localhost:3000/api/v1
EMAIL=demo@example.com
PW=Passw0rd123     # 規則：英文大小寫 + 數字，8–16 字，不可有特殊字元
# name 欄位規則：2–5 個字母、數字或中文；preference 必須剛好 3 個
```

**(a) 在 Mailpit 看到忘記密碼信**

```bash
# 1. 註冊一個帳號（preference 為偏好名稱，必須剛好 3 個，Joi `.length(3)`）
curl -s -X POST $B/auth/userinfo/signup -H 'Content-Type: application/json' \
  -d "{\"name\":\"Demo\",\"email\":\"$EMAIL\",\"password\":\"$PW\",\"preference\":[\"探索冒險\",\"放鬆療癒\",\"文化體驗\"]}"

# 2. 觸發忘記密碼
curl -s -X POST $B/auth/userinfo/forgetpw -H 'Content-Type: application/json' \
  -d "{\"email\":\"$EMAIL\"}"
# → {"status":"success","message":"連結寄送成功"}
```

打開 http://localhost:8025 ，收件匣會有一封主旨 `TripEasy 密碼重設連結` 的信，內文有 `…/admin/resetpw?token=…`。注意：信中連結目前不能直接用，因為前端是 hash 路由（已知問題，見附錄）。對不存在的 email，middleware 會先回 404「帳號不存在。」。

**(b) 看到上傳後經由 `/uploads` 提供的圖片**

```bash
# 3. 登入取得 token
TOKEN=$(curl -s -X POST $B/auth/userinfo/login/email -H 'Content-Type: application/json' \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PW\"}" | python3 -c 'import sys,json;print(json.load(sys.stdin)["data"]["token"])')

# 4. 上傳頭像（換成你自己的 PNG/JPG）
curl -s -X PATCH $B/user/userinfo/avatar -H "Authorization: Bearer $TOKEN" \
  -F "image=@./your.png;type=image/png"
# → {"status":"success","message":"更新成功","data":{"avatar_url":"http://localhost:3000/uploads/userProfile/<時間>-your.png"}}
```

把回傳的 `avatar_url` 貼進瀏覽器就能看到圖片。檔案實際存在 compose 的 `uploads` volume（容器內 `/usr/backend/uploads`）。用 `curl -I` 看該 URL 會看到 `X-Content-Type-Options: nosniff` 與 `Content-Security-Policy: default-src 'none'; sandbox`。自動化版本見 `tests/test_storage.py`。檔名中的中文經 multer latin1 解碼成亂碼後才被替換成 `_`（見附錄 D）。

**(c) 看 mock-oauth 的 discovery 文件**

```bash
curl -s http://localhost:8090/google/.well-known/openid-configuration
```

或直接用瀏覽器開同一個網址。回傳的 `issuer` 是 `http://localhost:8090/google`，並列出 `authorization_endpoint`、`token_endpoint`、`userinfo_endpoint`、`jwks_uri`。mock 對任何授權碼都簽發固定身分：`sub=mock-google-001`、`email=mock.user@example.com`、`name=Mock 使用者`。

清理上面建立的示範帳號（可選）：測試帳號由 pytest 自己建立並清除，手動建立的 `demo@example.com` 可依 child-first 順序清除（帳號與資料庫名稱取自 `.env.example`）：

```bash
docker compose exec -T postgres psql -U tripeasy_admin001 -d tripeasy_db001 -c "
DELETE FROM point_record WHERE user_id IN (SELECT user_id FROM \"user\" WHERE email='demo@example.com');
DELETE FROM user_level  WHERE user_id IN (SELECT user_id FROM \"user\" WHERE email='demo@example.com');
DELETE FROM \"user\" WHERE email='demo@example.com';"
curl -s -X DELETE "http://localhost:8025/api/v1/search?query=to:demo@example.com"   # 清掉 Mailpit 的信
```

上傳的頭像檔會留在 `uploads` volume，直到 `docker compose down -v`。

### 4.3 測試帳號

P0 沒有 seed 資料。pytest 的 `make_user` 每次建立 `p0-<8碼>@example.com` 並在結束時刪除；手動體驗請用上面的 `signup` 註冊。seed 資料與固定測試帳號屬於 P1。

---

## 附錄

### A. 變更檔案清單

`git diff --stat` 摘要。

**總覽 repo**（`main..phase-0`，22 檔 +3118，另外修改 `README.md`、新增 `docs/reports/phase-0.md`、`refs.env` 內容不變）

```
.env.example                          docker-compose.yml          pyproject.toml / uv.lock
.github/workflows/ci.yml              scripts/ci.sh
tests/conftest.py  test_async_errors.py  test_frontend.py  test_health.py
tests/test_mail.py  test_migrations.py   test_oauth_spike.py  test_storage.py
docs/reports/evidence/phase-0/  task3-health-red.txt  task4-storage-red.txt  task4-uploads-xss-red.txt
                                task5-mail-red.txt    task6-async-red.txt    task7-oauth-red.txt
                                task7-oauth-spike.md  task8-frontend-red.txt
```

**backend**（`main..phase-0`，17 檔 +8420 −136，其中 `package-lock.json` 佔 8207 行）

```
 .dockerignore                     |    7 +
 .gitignore                        |    1 -
 Dockerfile                        |   36 +-
 docker-compose.dev.yml            |    4 +-
 docker-compose.yml                |   14 +-
 package-lock.json                 | 8207 +++
 package.json                      |    2 +
 src/config/firebase.js            |   29 +-
 src/controllers/userProfile.js    |   43 +-
 src/controllers/userinfo.js       |    7 +-
 src/middlewares/userinfo/index.js |    4 +-
 src/server.js                     |   12 +
 src/utils/firebaseUpload.js       |   65 +-
 src/utils/mailer.js               |   32 +
 src/utils/storage/firebase.js     |   31 +
 src/utils/storage/index.js        |   17 +
 src/utils/storage/local.js        |   45 +
```

**frontend**（`dev..phase-0`，4 檔 +15 −7）

```
 .env.development              | 6 +++++-
 .env.example                  | 4 +++-
 .env.production               | 3 ++-
 src/views/admin/loginPage.vue | 9 +++++----
```

### B. 計畫中「不在 P0 修的已知問題」

遇到時只記錄，不在 P0 修。

| 問題 | 歸屬 |
|---|---|
| `forgetpw` 收到不存在的 email 會回 500（`userinfo.js:253`，`user` 是 undefined）（P0 查證：不成立。middleware `postuserforgetPW`（`middlewares/userinfo/index.js:219-221`）先查 user、不存在回 404；controller `userinfo.js:253` 是查詢、`:256` 的 `user.user_id` 走不到。P2 可移除重複查詢。） | P2 |
| 重設密碼信的連結 `${FRONTEND_PATH}/admin/resetpw` 沒有考慮前端是 hash 路由 | P2 |
| `socialLogin.provider_token` 是 VARCHAR(255)，可能放不下 mock 或真實的 JWT access token | P2（見 Task 7） |
| Google 的 redirect 回到首頁，`loginPage.vue:108` 讀取 `location.search` 的流程在 hash 路由下走不到 | P2 |
| fakedata 的角色是 `user` / `admin`，但程式用 `authRole('User')`，大小寫不一致 | P1 seed |
| 不在白名單的 Origin 會讓 CORS callback 丟出 Error，最後回 500 | P2 |

### C. Task 7 spike 結論

完整文件：[task7-oauth-spike.md](evidence/phase-0/task7-oauth-spike.md)。

- 結果 B：mock 的 token 交換與 userinfo 可用，backend 只要讓兩個網址可由環境變數設定就能接上。
- 唯一阻礙是 `socialLogin.provider_token VARCHAR(255)` 放不下 740 字元的 JWT access token；P2 改成 `TEXT` 後，預期 backend 的 Google 登入 API 可在本機用 mock 跑通（尚未驗證）；前端 redirect 流程另有附錄 B 的 hash 路由問題。屆時移除 `xfail(strict=True)`。

### D. 額外的已知限制與延後項目

#### 不要誤解的限制（P0 就該寫明）

- **中文檔名不會保留**：multer 把 multipart 檔名以 latin1 解碼，中文變成亂碼，再被 `safeKey()` 換成 `_`。上傳功能能用，但不能宣稱支援中文檔名。
- **路徑穿越測試沒有測到 `safeKey`**：`test_upload_filename_cannot_escape_upload_dir` 送出 `../../../evil 圖.png`，但 busboy 在更前面就把路徑去掉，`safeKey` 的過濾邏輯沒被觸發。目前能證明的是「結果沒逃出 `UPLOAD_DIR`」，不是「`safeKey` 擋掉了」。
- **`xfail` 沒有失敗原因的特異性**：若 Task 7 退化成別種失敗（例如 outcome C）也同樣顯示 XFAIL；P2 修好欄位時改成明確斷言 varchar 錯誤。
- **舊的 `backend/docker-compose.yml`** 需加 `--profile tools` 才能 `config`（`api` 依賴 profile 內的 `migrate`），P0 不改；根目錄的 compose 不使用它。
- **`delete_user` 只清 3/11 張子表**（`socialLogin`、`point_record`、`user_level`）。P0 沒有測試寫到 cart / orders / payment / review / hidden_play / auto_setting / favorite / user_coupon，所以不會出錯，但 P2 寫第一個會碰這些表的測試之前必須先擴充（child-first）。
- **GitHub Actions 尚未實際執行過**（等 push 後才能驗證）；frontend 在乾淨 runner 上冷啟動 `npm ci` 的 180 秒等待視窗未實測。

#### 延後項目（依目標階段分組）

**P1（seed / 測試資料）**
- fakedata 角色大小寫不一致（見 B）。
- `make_user` teardown 遇到第一個刪除失敗就中止（沒有逐一 try/except）。

**push 前處理**
- `evidence/phase-0/*.txt` 原本含本機絕對路徑，已在 push 前改為相對路徑（`db47539`）。

**P2（auth、金流、上傳）**
- 見 B 表中標 P2 的 5 項（第 1 項 forgetpw 經查證不成立，實際為 4 項，另加移除重複查詢）。
- error handler：`err.status` 存在時會把 `err.message` 回給前端（axios 1.x 會設 `.status`，現在所有 async rejection 都可能走到）；沒有 `res.headersSent` 防護；log 不含 method / url；測試只驗 `status == "error"`，沒驗 message。
- 決定是否還要儲存 `provider_token`（目前從未被讀回）。
- OAuth 登入後 redirect 落在首頁，但 `?code` 的處理在 `admin/loginPage` 的 `mounted()`（與 B 表 Google redirect 一項相關）。
- storage：未知的 `STORAGE_DRIVER` 會同步 throw；`firebase` 初始化在 `bucket()` 失敗後可能卡在半初始化狀態；`local.remove` 的 `decodeURIComponent` 在 try 外；`uploadImageToFirebase` 的檔名組合在 try 外。
- mailer：SMTP transporter 在模組層級快取；`test_mail` 的 `len == 1` 仰賴 email 唯一；Mailpit 映像檔自帶 healthcheck（`compose ps` 顯示 healthy），但 backend 的 `depends_on` 用的是 `service_started` 而非 `service_healthy`。
- Express 5 升級時移除 `express-async-errors`。

**P7（部署）**
- 正式環境**不可**帶 `.env.example` 的 `GOOGLE_TOKEN_URL` / `GOOGLE_USERINFO_URL`，否則 mock 會變成任意登入；考慮加 `NODE_ENV=production` 啟動檢查。
- mock-oauth 綁 `0.0.0.0:8090`，frontend 5173 也綁所有介面（含 Vue DevTools），可改 `127.0.0.1`。
- `MAIL_FROM` 優先於 `SENDGRID_FROM_EMAIL`：切到 `MAIL_DRIVER=sendgrid` 時若沿用 `.env.example` 會用到未驗證的 `no-reply@tripeasy.local`。
- 正式前端 build 從未在 repo 裡設 `VITE_API_BASE` / `VITE_Redirect_BASE`，靠部署者的 gitignored `frontend/.env`；`gh-pages.yml` 沒有注入 env；`HomeView.vue:653` 的 `VITE_GAS_URL` 沒有任何定義（既有問題）。
- Docker：prod image 以 root 執行；`.dockerignore` 沒排除 Dockerfile / compose / `.vscode`；healthcheck 依賴完整 node image 內的 curl；舊 compose 的 `api.build` 沒有 `target`。
- CI：沒有 `.python-version`（`psycopg-binary` 只有 cp310–313 wheel，uv 若抓到 3.14 會讓 `uv sync --frozen` 失敗）；`ci.yml` 沒有 `timeout-minutes` / `permissions`；push 與 pull_request 會重複觸發；action 版本為 Node 20 時代的 major；`ci.sh` 的 curl 沒有 `--max-time`；`up -d` 遇到 unhealthy backend 會直接失敗而略過 `wait_for` 的診斷輸出。
- **push 順序必須是 backend → frontend → 總覽**，且總覽 `refs.env` 解析的 tag 要先存在遠端，否則第一次 CI 會是紅燈。
