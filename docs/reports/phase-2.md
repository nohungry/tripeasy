# Phase 2：會員（註冊、登入、會員中心、忘記密碼、Google 登入）
> 2026-11-18（定稿） · backend tag `phase-2`（merge commit `3d835a6`；分支最後一個 commit `124e85c`） · frontend tag `phase-2`（merge commit `71a2171`；分支最後一個 commit `a9a68b5`）
>
> 本報告依 `docs/superpowers/specs/2026-10-15-tripeasy-rebuild-design.md` §5 範本與 `docs/reports/phase-1.md` 的格式撰寫。章節骨架與 P1 相同：§0 摘要、§1 問題與修正、§2 工作流、§3 測試方法、§4 操作指南、附錄（A 變更檔案、B 已知限制）。所有引用以 commit hash、`檔案:行號`、evidence 檔名為出處；查不到的寫「未查證」。
>
> 行號基準：**P2 之前就存在的問題**，行號取自 backend `main`／frontend `dev`（修正前）；**P2 期間才引入或浮現的問題**，行號取自引入它的 commit，並在該處標明。

## 0. 摘要

P2 的目標：讓「註冊 → 登入 → 會員中心」這條主線能從前端完整操作而且安全，並修掉設計（`docs/superpowers/specs/2026-11-12-p2-member-design.md`，以下稱「P2 spec」）列出的帳號接管漏洞。原本的狀態：Google 新會員全部共用同一組預設密碼、`email` 不分大小寫也沒有唯一約束、重設密碼的 token 能當登入 token 用、驗證碼答案明文放在 cookie、任何登入者都能把自己改成 admin、前端的登入檢查根本沒有接到路由上、重設密碼信與 Google 回跳的網址在 hash 路由下都走不通。

| 項目 | 結果 |
|---|---|
| 測試數量 | P1 結束 195 passed + 2 xfailed → P2 結束 **329 passed + 2 xfailed**（本機 `scripts/ci.sh` 連跑兩次：第 1 次在 `docker compose down -v` 之後的乾淨環境、第 2 次保留 volume，見 §3.3） |
| xfail 說明 | **現在的 2 個 xfail 不是 P1 的那兩個。** P1 的兩個（`GET /admin/product` 一律 500、`provider_token` 欄位長度）都已修好並移除（backend `f012cdc`；`provider_token` 改寫 NULL 的 backend `6ce56b3`，測試 xfail 於 overview `cae2c59` 移除）。現在的 2 個是 **PATCH `/info` 部分更新**（只給 name、只給 preference 都回 500）的 `strict=True` xfail：Task 3 決定留到 P3 修，先用 xfail 列管（見 §1.22 與附錄 B）。Task 12 brief 寫的「應無 xfail」已被這個裁決取代（進度帳 Task 3 Ruling） |
| 紅燈 → 綠燈 | 每個修正都有紅燈 commit（`test: … 🔴`）對應綠燈 commit；紅燈輸出存在 `docs/reports/evidence/phase-2/`（23 個檔）。哪些項目的「紅燈」不是乾淨地紅在目標行為上（例如被前置步驟的 500 蓋住），逐項在 §1 誠實標註 |
| 新增物件 | backend：`migrations/V3__p2_user_auth.sql`（3 行）、`src/utils/authToken.js`（81 行）、`src/utils/captcha.js`（44 行）；frontend：`src/oauthRedirect.js`、`src/views/NotFound.vue` |
| 修正項目 | P2 spec §2、§3、§4 列出的項目（§1.1–§1.21）＋ P2 期間發現而計畫原本沒寫的 12 項（§1.22） |
| backend 變更 | 14 檔 +282 −106（`git -C backend diff --stat main..phase-2`）、14 個 commit |
| frontend 變更 | 11 檔 +168 −201（`git -C frontend diff --stat dev..phase-2`）、8 個 commit；`−201` 大多是刪除整段註解掉的舊路由表（`9e264b8`，−173 行） |
| 總覽 repo 變更 | 43 檔 +4751 −81（`git diff --stat main..phase-2`，統計到 `b8141d4`，不含本報告、README 與 `84189ac`）、50 個 commit（同範圍） |
| E2E | 新增 Playwright Python 測試 `e2e/test_member_flow.py`（22 個案例，ci.sh 內執行） |
| CI 結果 | 本機 `scripts/ci.sh` 兩次皆 329 passed, 2 xfailed（第 1 次乾淨、第 2 次保留 volume）；GitHub Actions run：[44323636173](https://github.com/nohungry/tripeasy/actions/runs/44323636173)（綠燈，329 passed, 2 xfailed；`phase-2` tag 當時的 run 是紅燈，原因與處理見 §3.3） |
| 升級 Opus 實作 | 進度帳沒有「升級 Opus 實作」的紀錄；所有 Task 的 fix round 皆為 implementer 完成（未逐一查證） |

Commit 範圍：

- 總覽 repo：`06d86ee`（P2 spec）→ `b8141d4`，共 50 個 commit（`git log main..phase-2`，不含本報告與 `84189ac`）。
- backend：`f012cdc` → `ec2394e`，14 個 commit（初稿之後另補 `124e85c`，backend `.env.example`）。
- frontend：`020842d` → `a9a68b5`，8 個 commit。
- 與 P0／P1 相同：**紅燈在總覽 repo、綠燈在 backend／frontend repo**（測試放總覽 repo）。每個紅燈 commit 只有測試與 evidence。

## 1. 問題與修正

「紅燈」欄指的是對舊實作執行新測試所得的輸出（`docs/reports/evidence/phase-2/*.txt`）。若某個紅燈 commit 的失敗內容不是「目標行為不對」而是被別的錯誤蓋住，會直接寫出。

### 1.1 Google 新會員共用同一組預設密碼（P2 spec §2.1、§2.4 的前半）

**現象**：知道 `DEFAULT_OAUTH_PASSWORD`（未設時 `'DefaultPassword123!'`）的人，能用 Email 登入**任何** Google 新註冊會員。這組值還公開在 `.env.example:26`。

**根因**：
- `migrations/V1__tripeasy_sql.sql:10`：`password VARCHAR(255) NOT NULL`，Google 會員沒有密碼也得塞一個。
- `controllers/userinfo.js:174`：`bcrypt.hash(process.env.DEFAULT_OAUTH_PASSWORD || 'DefaultPassword123!', salt)`；`:176–179` 以此 hash 寫入新會員。
- Email 登入不區分登入方式，只比對 `password`。

**紅燈**（兩段，各自抓到不同東西）：
1. `NULL` 密碼的處理：[task-3-red.txt](evidence/phase-2/task-3-red.txt)（overview `e69343c`，3 failed 37 passed）：`test_member_auth.py` 的兩個 NULL 密碼測試回 **500「伺服器錯誤」**，而不是約定的 401 訊息（登入）與 400 訊息（會員中心改密碼）（`bcrypt.compare` 遇 NULL 丟錯）；另有一個失敗是登入回應沒有 `avatar_url`（見 §1.17）。migration 的 nullable：[task-2-red.txt](evidence/phase-2/task-2-red.txt)（overview `6182c91`，9 failed 17 passed）內的 `test_user_password_is_nullable`。
2. Google 路徑：[task-10-red.txt](evidence/phase-2/task-10-red.txt)（overview `cae2c59`，8 failed 3 passed）。**誠實的說明**：這 8 個失敗全部是 **500「伺服器錯誤」**，原因是舊程式把 Google 的 JWT 寫進 `provider_token`（`VARCHAR(255)`）而溢位（見 §1.4），在還沒走到密碼斷言之前就死了。所以這個紅燈**不能證明**「共用密碼」這件事本身；`test_google_member_cannot_login_with_default_password`、`test_google_new_user_has_null_password` 的分辨力是靠 mutation 證明的（見下）。

**共用密碼的證明方式（brief 指定要寫明）**：共用密碼 `DefaultPassword123!` 通不過 Email 登入的 `passwordPattern`（`utils/Validator/userInfo_Validator.js:7`：`/^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)[A-Za-z\d]{8,16}$/`，只允許英數、8–16 字；共用密碼含 `!` 且 19 字，兩項都不符），Email 登入先回 **400**，而不是 401，所以測試**不可能**用「共用密碼登入成功」當紅燈。證明靠的是兩件事：(a) DB 狀態 `user.password IS NULL`；(b) 任何格式正確的密碼打 Email 登入，都得到 NULL 密碼訊息（401，`tests/test_google_login.py:163-177` 的 `test_google_member_cannot_login_with_default_password`）。**照 evidence 如實寫的差異**：brief 說「紅燈呈現的是訊息與 DB 狀態不同」，但實際存下來的紅燈輸出中，「訊息不同」有證據（task-3-red.txt：500「伺服器錯誤」對比約定的 NULL 密碼訊息），**「DB 狀態不同」沒有出現在紅燈輸出裡**（task-10-red.txt 全是 500，沒走到 `password is None` 斷言）；DB 狀態那條斷言的分辨力由 mutation (c)（新會員 INSERT 改寫 bcrypt 密碼 → `test_google_new_user_has_null_password`、`test_google_member_cannot_login_with_default_password` 轉紅，[task-10-mutation.txt](evidence/phase-2/task-10-mutation.txt)）補上。已列入審閱時要確認的事項。

**修正**：
- backend `6cae20a`（`V3__p2_user_auth.sql`：`password` DROP NOT NULL；詳見 §1.2）。
- backend `ed9840c`：Email 登入遇 NULL 密碼回 401 且**不累計** `login_attempts`；會員中心改密碼遇 NULL 回 400（兩個訊息都是 plan「共用約定」的固定字串）；兩處 `user.picture` 改 `avatar_url`（§1.17）。
- backend `6ce56b3`：Google 新會員 `password` 寫 NULL，移除 `DEFAULT_OAUTH_PASSWORD`（程式）；overview `2cd2087` 從 `.env.example` 與本機 `.env` 移除。

**綠燈**：`tests/test_google_login.py`、`tests/test_member_auth.py` 全綠；mutation (a)–(g) 皆如預期轉紅（[task-10-mutation.txt](evidence/phase-2/task-10-mutation.txt)）。

### 1.2 `email` 不分大小寫唯一（P2 spec §2.2）

**現象**：`Alice@x.com` 與 `alice@x.com` 能註冊成兩個帳號；同時送出兩個相同 email 的註冊會產生重複列；有重複後 `WHERE email = $1` 取 `rows[0]` 結果不確定。

**根因**：`migrations/V1__tripeasy_sql.sql:8`：`email VARCHAR(255) NOT NULL` 沒有 UNIQUE；`utils/Validator/userInfo_Validator.js:16` 的 email 驗證只驗格式、不轉小寫；註冊只靠 middleware「先查再新增」；查詢點是大小寫敏感的 `email = $1`：`middlewares/userinfo/index.js:43,78,219`、`controllers/userinfo.js:80,253`、`middlewares/checkout/index.js:85`、Google 路徑 `controllers/userinfo.js:146`。

**紅燈**：[task-2-red.txt](evidence/phase-2/task-2-red.txt)（overview `6182c91`）：`test_signup_normalizes_email`、`test_signup_duplicate_differs_by_case_is_409`、`test_signup_concurrent_same_email_only_one_succeeds`、`test_login_email_is_case_insensitive`，以及 `test_migrations.py` 的 `test_v3_applied`、`test_user_email_lower_unique_index`、`test_email_case_duplicate_rejected` 等，共 9 failed。checkout 另有紅燈 [task-2-red-checkout.txt](evidence/phase-2/task-2-red-checkout.txt)（overview `feb9a25`）：大寫 email 查不到（回「查無此使用者」，期望 404「查無此訂單項目」）。

**修正**：backend `6cae20a`（`CREATE UNIQUE INDEX user_email_lower_key ON "user" (lower(email))`、validator 轉小寫、5 處查詢改 `lower(email) = lower($1)`、註冊撞 `23505` 且 constraint 為 `user_email_lower_key` 時 ROLLBACK 後回 409）；backend `9e90edf`（checkout 的查詢）。Google 路徑在 `6ce56b3`（轉小寫、`lower(email)` 查詢）與 `da0779d`（新會員撞唯一索引回 409，見 §1.22 i）。

**綠燈**：`test_migrations.py`、`test_member_auth.py` 綠；契約 `docs/db-contract.md` §5 補 P2 表格約束（overview `6eb4de7`、`ce644c1`）。

**過程中的事實**（Task 2 report）：`test_signup_lowercase_conflicts_with_mixed_case_stored_email` 在把 5 處查詢暫時改回 `email = $1` 時仍綠，因為 DB 唯一索引的 `23505` 也回同一個 409「Email已被使用」，只靠 API 區分不出是 middleware 還是 DB 擋的，這是 spec 的「友善訊息＋DB 最後防線」設計造成的；login 與 forgetpw 的反向測試（DB 存 `Mixed.…@Example.COM`）則會轉紅（`96dc90b`）。

### 1.3 Google 登入遇到已存在的 email（預先劫持）與 `email_verified`（P2 spec §2.3、§3.5）

**現象**：Email 註冊不驗證信箱，攻擊者可先用受害者的 email 註冊並取得登入 token；受害者之後用 Google 登入時，舊程式把兩者綁在一起、攻擊者的密碼仍有效、攻擊者先前取得的 token 也繼續有效（30 天）。Google 回傳的 `email_verified` 完全沒檢查。

**根因**：`controllers/userinfo.js:146` 查到既有會員後，`:153–157` 只更新 `avatar_url`、`login_method`，不動 `password`；`:163–167` 的 `ON CONFLICT … DO UPDATE` 每次登入都覆寫 `socialLogin`（含 `provider_token`）；`middlewares/userinfo/index.js` 沒有 `email_verified` 檢查（修正後 `:190`，backend `6ce56b3`）。

**紅燈**：[task-10-red.txt](evidence/phase-2/task-10-red.txt)（overview `cae2c59`，8 failed 3 passed）。**同一個誠實說明**：8 個失敗全是 500（`provider_token` 溢位），所以 `test_google_first_bind_clears_password_and_old_tokens`、`test_google_unverified_email_rejected` 等的關鍵斷言**沒有**在紅燈階段被單獨驗證到（Task 10 report「疑慮」第 2 點）；兩位審查者一致指出「紅燈全卡同一個 500 無分辨力」（進度帳 Task 10 review），於是補了 mutation 證據：[task-10-mutation.txt](evidence/phase-2/task-10-mutation.txt)（overview `0247808`）(a) 首次綁定拿掉 `password = NULL`、(b) 已綁定分支也清密碼、(c) 新會員改寫 bcrypt、(d) `email_verified` 檢查改 `=== false`、(e) 查詢改回 `email = $1`、(f)(g) 其他，皆轉紅。其中 **(e) 一開始沒有任何測試轉紅**，補了 `test_google_binds_existing_mixed_case_stored_email`（DB 存混合大小寫 email）後才轉紅。

**修正**：backend `6ce56b3`：`middlewares` 拒絕 `email_verified !== true`（400）；controller 轉小寫、`lower(email)` 查詢並 `FOR UPDATE` 鎖列；新會員 `password` 為 NULL；**第一次綁定**（該帳號還沒有 `provider_method='google'` 的 `socialLogin` 列）在同一交易內 `password = NULL` ＋ 寫 `socialLogin`；已綁定者之後登入不再清密碼（所以 Google 會員用忘記密碼設好密碼後，兩種方式都能登入）；token 以更新後的列簽發。mock-oauth 改為 `interactiveLogin: true`（`docker-compose.yml`，overview `cae2c59`），測試用 `conftest.mock_google_code(claims)` 向它的登入表單取 code，因此可以自訂 `email_verified`。

**綠燈**：`tests/test_google_login.py` 23 個案例（ci.sh 內）全綠；E2E `test_google_login_via_mock`（§1.20）。

**已接受的代價**（P2 spec §2.3）：先 Email 註冊、後改用 Google 的真會員，原密碼會失效，要再走忘記密碼。

### 1.4 `socialLogin.provider_token` 放不下 Google token（P2 spec §2.4）

**現象**：P1 的 strict xfail `tests/test_oauth_spike.py:68`：Google 登入把 JWT 存進 `provider_token` 時 `VARCHAR(255)` 溢位，回 500。

**根因**：`migrations/V1__tripeasy_sql.sql:29` `provider_token VARCHAR(255)`；`controllers/userinfo.js` 把 `access_token`（`:135` 取得）寫入該欄位（`:167` 既有會員、`:194` 新會員）。

**紅燈**：[task-10-red.txt](evidence/phase-2/task-10-red.txt) 的 `test_backend_google_login_via_mock`（500）。

**修正**：不改欄位型別，改成**不再存 token**，寫 NULL（backend `6ce56b3`）；P1 的 xfail 於 overview `cae2c59` 移除，測試改寫成驗證新行為（`provider_token` 為 NULL、`provider_id` 正確）。註：P1 的 xfail reason 寫「P2 以 migration 修正」，實際改由 P2 spec §2.4 寫 NULL 解掉，沒有 migration（P2 spec §6.1）。

### 1.5 重設密碼 token 能當登入 token、可重複使用（P2 spec §3.1）

**現象**：重設密碼信的 token 通得過所有只檢查 `auth` 的路由；15 分鐘內可重複使用。

**根因**：`controllers/userinfo.js:256–257`：`payload = { id }`，同一個 `JWT_SECRET`、`expiresIn: '15m'`；`middlewares/auth.js:25`、`middlewares/auth_not_mandatory.js:16` 只做 `jwt.verify`，不看用途；重設端點 `middlewares/userinfo/index.js:235 起` 同樣只 `jwt.verify`（`:291` 的 `UPDATE … WHERE user_id = $2` 不檢查舊密碼）。

**紅燈**：[task-4-red.txt](evidence/phase-2/task-4-red.txt)（overview `e6e4cc2`，8 failed 4 passed）：`test_reset_token_cannot_access_member_api`、`test_reset_link_shape`、`test_login_token_cannot_reset_password`、`test_reset_token_is_single_use`。

**修正**：backend `1eff04f`：新增 `src/utils/authToken.js`；reset token payload `{ id, typ: 'reset', pwv }`，`auth.js`／`auth_not_mandatory.js` 只接受 `typ: 'login'`；reset 端點只接受 reset token；`pwv` 為「由當下 `password` 推導的密碼指紋」（`HMAC-SHA256(JWT_SECRET, password ?? '')` 取前 16 hex，NULL 也有固定指紋），密碼一改舊連結失效。重設信連結同時改成 `${FRONTEND_PATH}/#/admin/resetpw?token=…`（§1.16）。

**綠燈**：`test_member_auth.py` 綠。審查後補強（overview `85c16d9`，一開始就綠）：訊息斷言、reset token 打 `/info`、`/login/status`、`/user/home/search/products` 皆 401、alg none／缺 pwv／pwv 錯誤皆 401。

### 1.6 密碼變動時舊的登入 token 不失效（P2 spec §3.1a）

**現象**：登入 token 只有 `{id, role}`、效期 `JWT_EXPIRES_DAY`（30d），無法撤銷：預先劫持的攻擊者在受害者綁 Google 前登入，token 可再用 30 天；改密碼後舊裝置仍維持登入。

**根因**：`controllers/userinfo.js:96`、`:208`（Email 與 Google 登入簽發）的 payload 只有 `{ id, role }`；`middlewares/auth.js:25` 驗完簽章就放行，不查 DB。

**紅燈**：[task-4-red.txt](evidence/phase-2/task-4-red.txt)（overview `e6e4cc2`）：`test_old_login_token_invalid_after_reset`、`test_old_login_token_invalid_after_profile_change`、`test_forged_token_without_pwv_is_401`、`test_token_of_deleted_user_is_401`；第三種觸發（第一次綁 Google 時清成 NULL）由 `test_google_first_bind_clears_password_and_old_tokens`（overview `cae2c59`，見 §1.3 的紅燈說明）覆蓋。

**修正**：backend `1eff04f`：登入 token payload `{ id, role, typ: 'login', pwv }`；`verifyLoginToken` 每次驗證都查 DB（`utils/authToken.js:51` 讀 `password, role`）比對 `pwv`，不符回 401；查不到會員（token 指向已刪除的人）回 401 而非 500。代價（已接受）：每個需要登入的請求多一次 DB 查詢（這件事在 §附錄 B 的 pool 項目有後續影響）。前端的對應（改密碼後導回登入頁、401 統一處理）見 §1.20。

### 1.7 驗證碼答案明文放 cookie，且 cookie 屬性寫死（P2 spec §3.2）

**現象**：使用者可以自設 `captcha` cookie 繞過驗證碼；cookie 的 `secure: true`、`sameSite: 'None'` 寫死在程式裡，無法由環境設定（總 spec §4.3 要求可設定）。

**根因**：`controllers/userinfo.js:313–318` 把 `captcha.text` 明文放進 cookie；`middlewares/userinfo/index.js:268`、`:279` 用 `stored.toLowerCase() !== input.toLowerCase()` 比對。

**紅燈**：[task-5-red.txt](evidence/phase-2/task-5-red.txt)（overview `c9a9a57`，5 failed 3 passed）：`test_captcha_cookie_is_not_plaintext`、`test_forged_plaintext_captcha_cookie_rejected`、`test_signed_captcha_cookie_accepted`、`test_expired_captcha_cookie_rejected`、`test_captcha_cookie_attributes_from_env`。

**修正**：backend `0cb2a15`：新增 `utils/captcha.js`，cookie 值為 `<expiresMs>.<HMAC-SHA256(CAPTCHA_SECRET, lower(answer) + '.' + expiresMs)>`，伺服器重算比對；cookie 的 `SameSite`、`Secure` 與 CORS `credentials` 改讀環境變數；新增 `CAPTCHA_SECRET`、`COOKIE_SAMESITE`、`COOKIE_SECURE`、`CORS_CREDENTIALS`（overview `65cf8f9` 寫進 `.env.example`）。`CAPTCHA_SECRET` 空值 fail closed 與 clearCookie 的修正見 §1.22 e。

**綠燈**：併發與竄改相關測試見 §3.2；已接受的限制：5 分鐘內同一組答案可重送（P2 spec §3.2 允許）。

### 1.8 任何登入者都能把任何人改成 admin（P2 spec §3.3）

**現象**：`PATCH /api/v1/admin/members/roles` 只有 `auth`，任何登入帳號可把任何註冊帳號（含自己）改成 `admin`。

**根因**：`routes/admin.js:26`：`// authRole('admin'),` 被註解掉；`controllers/admin.js:59` 原樣 `UPDATE … SET role = $1`。

**紅燈**：[task-1-red.txt](evidence/phase-2/task-1-red.txt)（overview `69f40de`，2 failed 1 passed 1 error）：`test_change_role_requires_admin` 得 200 而非 403。同一個紅燈的 `test_delete_user_clears_all_fk_tables`（P1 遺留，見 §1.21）因為 `ForeignKeyViolation` 失敗、teardown 也失敗而留下殘留資料（Task 1 report）。

**修正**：backend `f012cdc`：打開 `authRole('admin')`。連帶的兩個後續修正見 §1.22 b、c。

**綠燈**：`test_change_role_by_admin` 在紅燈時就綠（改前本來就沒擋，回歸測試）；一般會員回 403。

### 1.9 帳號是否存在：不隱藏（P2 spec §3.4）

**無程式變更。** 註冊必須回「Email 已被使用」、登入鎖定會回「帳號鎖定中」，所以隱藏沒有實際保護效果；現行訊息保留（P2 spec §3.4，【Claude 定】）。

### 1.10 前端：登入檢查沒有接到路由（P2 spec §4.1 第 1 點）

**現象**：未登入直接開 `#/admin/userprofile`（會員中心）不會被擋回登入頁。
**根因**：`frontend/src/router/index.js:11` 定義了 `requireAuth`，但三條會員中心路由都沒有 `beforeEnter`（`dev:src/router/index.js:125–146` 的 `userprofile`、`collect`、`personalOrder`；`:128` 還有一行被註解掉的 `//beforeEnter: requireAuth`）。
**紅燈**：[task-7-red.txt](evidence/phase-2/task-7-red.txt)（overview `5ef772a`，5 failed 1 passed）：`test_profile_requires_login`。
**修正**：frontend `020842d`，三條路由接 `beforeEnter: requireAuth`（`/admin/manage/*` 留給 P6）。
**綠燈**：同一個測試綠；Task 7 後 e2e 6 passed（Task 7 report）。

### 1.11 前端：重複的 `name: 'search'` 路由（P2 spec §4.1 第 2 點）

**現象**：路由表有兩個 `name: 'search'`，hash 路由下後者覆蓋前者；P2 spec 要求保留一個且 `/search` 行為不變。
**根因**：`dev:src/router/index.js:75`（首頁 layout 底下）與 `:197`（頂層）。
**紅燈**：沒有針對「照 plan 做」之前的紅燈；這一項走了彎路，**照 plan 的做法（刪頂層）反而造成雙 header**，紅燈在修正輪才有：[task-7-red-search.txt](evidence/phase-2/task-7-red-search.txt)（overview `965d6ae`，`test_search_page_single_header` 預期 header 數 1、實際 2；細節見 §1.22 g）。
**修正**：frontend `020842d`（照 plan，刪頂層，錯）→ frontend `fc97780`（保留頂層 `/search`、刪 HomeLayout 下的 search 子路由）。
**綠燈**：`test_search_page_single_header` 綠；搜尋頁 goto 用 `wait_until="domcontentloaded"`，因為頁面載入外部圖片會讓 `load` 事件逾時（Task 7 report）。

### 1.12 前端：舊路由表（P2 spec §4.1 第 3 點）

**現象**：路由檔內有整段註解掉的舊路由表（P2 spec §4.1 記載約 `:203` 起）。
**這是重構**，依總 spec §0 先有測試再獨立 commit：測試即 Task 7 的 E2E；**沒有紅燈**（刪註解掉的程式不會改變行為）。
**修正**：frontend `9e264b8 refactor: 刪除註解掉的舊路由表`（−173 行）。
**綠燈**：e2e 仍 6 passed（Task 7 report）。

### 1.13 前端：沒有 404（P2 spec §4.1 第 4 點）

**現象**：開不存在的網址（例如 `#/no-such-page`）沒有 404 頁。
**根因**：`dev:src/router/index.js` 沒有 catch-all 路由（以 `git show dev:src/router/index.js | grep pathMatch` 驗證無結果）。
**紅燈**：[task-7-red.txt](evidence/phase-2/task-7-red.txt)：`test_unknown_route_shows_404`。
**修正**：frontend `020842d`：新增 catch-all，父路由 `HomeLayout`，子路由 `path: ''`、`name: 'not-found'`（命名放子路由，避免 vue-router 對命名父路由加空路徑子路由的警告），新增 `views/NotFound.vue`（顯示「找不到頁面」與回首頁連結，plan Task 7 Step 3）。
**綠燈**：`test_unknown_route_shows_404` 綠。Task 7 另手動確認 `/#/search` 沒顯示 404 文字（Task 7 report 疑慮：沒有針對該頁的自動化測試）。

### 1.14 前端：`window.location.href` 在 hash 模式會整頁重載（P2 spec §4.1 第 5 點）

**現象**：`window.location.href = '/admin/…'` 在 hash 路由下整頁重載並落到首頁（註冊後、登入後、登出後都去錯地方）。
**根因**：`api.js:35`（註冊後 → `/admin/login`）、`:85`、`:135`（登入 → `/admin/userprofile`）、`:207`（→ `/admin/login`）；`HeaderComponent.vue:148`、`HeaderReal.vue:148`（登出 → `/`）。`loginPage.vue:160` 是導向 Google（外部網址），保留。
**紅燈**：主線 E2E [task-6-red.txt](evidence/phase-2/task-6-red.txt)（overview `75b5274`）：註冊後導航記錄為 `/#/admin/register` → `/admin/login` → `/admin/login#/`，`wait_for_url("**/#/admin/login")` 逾時；[task-7-red.txt](evidence/phase-2/task-7-red.txt)：`test_signup_login_profile_main_flow`、`test_logout_stays_in_spa`。
**修正**：frontend `020842d`：四處改 `router.push`；Header 登出改 `router.push('/')`；因為 SPA 導航不會重載頁面，Swal 彈窗會留在畫面上擋住後續點擊，所以在 `router.push` 前呼叫 `Swal.close()`（彈窗仍顯示 3 秒後才跳轉）。
**綠燈**：主線 E2E 與 `test_logout_stays_in_spa` 綠（Task 7 後 `tests` 282 passed 3 xfailed、e2e 6 passed）。

### 1.15 前端：`throw err` 變數名錯（P2 spec §4.1 第 8 點）

**現象**：`patch_user_Profile` 失敗時應丟出原本的錯誤，卻會變成 ReferenceError。
**根因**：`api.js:306` catch 參數是 `error` 卻 `throw err`（`:278` 的 `throw err` 對應 `catch (err)`，正確）。
**紅燈**：**無專屬紅燈**（該路徑只在網路錯誤時走到，改動隨 Task 7 綠燈；後續 §1.20 的 `test_profile_save_network_error_shows_message` 會走到 `patch_user_Profile`）。
**修正**：frontend `020842d` 改 `throw error`；同檔其他 catch：`:258` 的 `catch (err)` 沒用到 `err`、`:278` 的 `throw err` 對應 `catch (err)`，皆無同類錯誤（Task 7 report）。
**綠燈**：隨 `020842d` 的全套綠燈；§1.20 的網路錯誤 E2E 另外證明該路徑不再丟未處理的 TypeError。

### 1.16 前端：重設密碼信與 Google 回跳在 hash 路由下走不通（P2 spec §4.1 第 6 點）

**(a) 重設密碼連結**
**現象**：從信件點重設連結，落到首頁、拿不到 token。
**根因**：連結是 `${FRONTEND_PATH}/admin/resetpw?token=…`（`controllers/userinfo.js:260`），`resetpwPage.vue:104` 讀 `window.location.search`。
**紅燈**：[task-8-red.txt](evidence/phase-2/task-8-red.txt)（overview `c500f66`；這個 commit 被 amend 過，Task 8 report）：`test_forgot_password_via_mailpit`，重設頁讀不到 token，找不到新密碼欄位而逾時。
**修正**：backend `1eff04f`（連結改 `/#/admin/resetpw?token=`）＋ frontend `2740bfd`（`this.$route.query.token`）。
**綠燈**：`test_forgot_password_via_mailpit` 綠（e2e 9 passed）。**反向驗證**：暫時把 `resetpwPage.vue` 改回讀 `window.location.search`，測試紅在 `expect(heading "修改密碼")`，頁面實際是「Oops! 你來到了一個不存在的地方」，證明 heading 斷言有分辨力。

**(b) Google 回跳 `?code=`**
**現象**：Google 回跳 `http://localhost:5173/?code=…`，不是登入頁，code 沒人處理。
**根因**：`GOOGLE_REDIRECT_URI`／`VITE_Redirect_BASE` 是 `http://localhost:5173/`，只有 `loginPage.vue:108` 讀 `window.location.search`，但 `/` 不是登入頁。
**紅燈**：[task-11-red.txt](evidence/phase-2/task-11-red.txt)（overview `1480975`）：回跳後停在 `http://localhost:5173/?code=...#/`，code 未被處理。
**修正**：frontend `1ae30d6`、`df6842e`：新增 `src/oauthRedirect.js`（只做 `history.replaceState`，把 `?code=` 搬進 hash），為 `main.js` 的**第一個 import**；`loginPage.vue` 改讀 `$route.query.code` 並 `$router.replace` 清掉。**計畫與實測不符**：brief 要求「`main.js` mount 前 `history.replaceState`」，實測無效，因為 `createWebHashHistory()` 在 router 模組載入、建立 history 時就從網址讀走位置，之後只寫 `#…` 相對網址，search 一直殘留；所以改成獨立的 side-effect 模組（進度帳 Task 11 Ruling 與其 Correction：根因不是「讀 search 當 base」）。注意 Google 的 `redirect_uri` 不能帶 `#`。
**綠燈**：`test_google_login_via_mock` 綠；補斷言：回跳後先等 `#/admin/login`、`code=` 不在 URL、`/login/google` POST 恰好 1 次；反向驗證：暫時註解 `router.replace`，測試紅（`wait_for_url` 逾時），已還原。

### 1.17 登入回應的頭像欄位（P2 spec §4.1 第 7 點）

**現象**：Email 登入後頭像永遠是 null。
**根因**：`controllers/userinfo.js:112`、`:351` 寫 `avatar_url: user.picture`，`user` 表沒有 `picture` 欄位。
**紅燈**：[task-3-red.txt](evidence/phase-2/task-3-red.txt)：`test_login_response_has_avatar_url`（`KeyError: 'avatar_url'`）。
**修正**：backend `ed9840c`（實際行號 `:120`、`:359`，brief 寫的行號偏移）。
**綠燈**：`test_login_response_has_avatar_url` 綠（Task 3 後全套 241 passed）。

### 1.18 前端：FB 登入圖示（P2 spec §4.1 第 9 點）

**現象**：登入頁有 FB 登入圖示，但後端沒有 FB 登入（總 spec §0）。
**根因**：`loginPage.vue:70` 的 `<div class="icon-circle fb">`。
**紅燈**：[task-7-red.txt](evidence/phase-2/task-7-red.txt)：`test_facebook_login_not_offered`。
**修正**：frontend `020842d` 移除（Google 不動）。
**綠燈**：`test_facebook_login_not_offered` 綠（審查後補強為 `count == 0` 斷言）。

### 1.19 前端：未登入、token 過期、重新整理（P2 spec §0 的主線第 3 點）

這一項是主線「會員中心」的行為，沒有單獨的程式修正，由 §1.10（未登入被擋）、§1.22 h（無效 token 清登入狀態、網路錯誤不清）、§1.20（過期 token 回登入頁）共同覆蓋；對應的 E2E 見 §3.1（`test_profile_requires_login`、`test_invalid_token_redirects_and_clears_state`、`test_expired_token_redirects_to_login`、`test_require_auth_network_error_keeps_token`）。「重新整理不會被登出」有沒有獨立的 E2E 案例：**未查證**。

### 1.20 會員中心縮小版（P2 spec §4.2【使用者定】）

**範圍**：只有「會員資訊」分頁做到可操作，其他三個分頁標示「即將開放」。原況：`userprofilePage.vue:174`，`tabs` 四個但只有第一個有內容；頁面沒有上傳頭像的介面。

**紅燈**：[task-9-red.txt](evidence/phase-2/task-9-red.txt)（overview `1f58e17`，6 failed 14 passed）：`test_avatar_upload`、`test_change_password_redirects_to_login`、`test_expired_token_redirects_to_login`、`test_profile_save_network_error_shows_message`、`test_coming_soon_tabs`、`test_require_auth_network_error_keeps_token`。**審查退回的更正**：原 task-9-red.txt 記錄 `test_require_auth_network_error_keeps_token` 死在 `wait_for_url`，是錯的；正確的紅燈失敗點是 token 斷言（`assert None is not None`），輸出重存為 [task-9-red-network-token.txt](evidence/phase-2/task-9-red-network-token.txt)（frontend 暫時 checkout `2740bfd` 重跑），原檔不改、以新檔為該測試的更正證據。

**修正**：frontend `44a3c52`：
- 頭像上傳（`patch_user_Avatar`，欄位 `image`，成功後同步 `localStorage.userPicture` 與 store）；
- axios response interceptor：401 時清登入資料並 `router.replace('/admin/login')`，**範圍只限會員 API**（`apiUrl_userprofile` 與 `${apiUrl}/resetprofilepw`），排除 `/login/status`、`/login/email`、`/login/google`，因為 `router.beforeEach` 在 login／register／forgotpw／resetpw 頁會帶著（可能已過期的）token 打 `/login/status`，不排除的話重設密碼信的連結會被導走（plan Task 9 Step 3）；
- `patch_user_Profile` 無 `response`（網路錯誤）時原本 `error.response.data.status` 丟 TypeError，改 `error.response?.data` 並顯示「無法連線到伺服器」；
- 改密碼成功後登出並導回登入頁（P2 spec §3.1a 要求不能卡在錯誤畫面）；
- 其他三個分頁顯示「即將開放」。

### 1.21 P1 遺留待辦（P2 spec §6）

1. **`test_oauth_spike.py:68` 的 strict xfail**：已修（§1.4）。
2. **`test_api_smoke.py:408`（`GET /admin/product` 500）**：已修並移除 xfail。該測試在 P1 就是 strict xfail，所以沒有獨立的紅燈檔；backend `f012cdc` 移除 `middlewares/product/index.js:296` 的 `const { tour_ids } = req.user` 與 `:312–315` 整段「404 查無此項目」檢查（原本從未生效、`tour_ids` 無來源，JWT 只有 id 與 role）。**這是設計判斷**：刪除而不是改寫，兩位審查者皆同意（進度帳 Task 1 Ruling）；空結果回 200、`resStatus` 對空結果不輸出 `data` 欄位。
3. **carol 優惠卷測試 133 天後變紅**：overview `13d086b`：改查 DB 的 `expire_date >= now()`，不成立才 `pytest.skip`；查不到資料則 fail（`f34414d`）。
4. **`R__views_functions.sql` 的 DROP 清單寫死、`tests/db_contract.py` 不比對契約文字**：本階段 `git diff main..phase-2 --stat` 沒有改過 `tests/db_contract.py`；backend 的 `git -C backend diff main..phase-2 --stat` 也沒有改過 `migrations/R__views_functions.sql`（V3 是新檔 `V3__p2_user_auth.sql`，只動 `user`，沒有動 view／function）。所以**依 P2 spec §6.4 與 Task 12 brief，在附錄 B 重申，不處理**。（`docs/db-contract.md` 有改，但 `tests/db_contract.py` 沒有，因為 P2 沒有改 view／function 的欄位或簽章。）
5. **附帶**：`delete_user` 原本只清 11 張直接 FK 表中的 3 張（P1 ruling），Task 1 改成清完整（包含 `cart_item`、`order_item`、`payment`、`point_record`、`user_coupon` 等間接表），並新增 `test_user_fk_tables_list_is_complete` 用 `pg_constraint` 比對所有參照 `"user"` 的表（overview `f34414d`）。

### 1.22 P2 期間發現並修掉、計畫原本沒寫的項目

以下 12 項都不在 P2 spec 的項目裡，是實作或審查中發現的，每一項都由主對話（controller）以 Ruling 決定是否在 P2 內修（見 §2.4 的表）。

| # | 項目 | 現象 → 根因與行號 | 紅燈 | 修正 / 綠燈 |
|---|---|---|---|---|
| a | **PATCH `/info` 連線洩漏** | 每呼叫一次漏一條連線，pool 預設 max 10，約 5 次全套測試後所有後續請求卡住逾時。`controllers/userProfile.js:50` 的 `pool.connect()` 之後整個檔案沒有 `client.release()`，成功與失敗路徑都沒有（`main`） | [task-3-red-leak.txt](evidence/phase-2/task-3-red-leak.txt)，overview `e2cbf7f`：`ReadTimeout`（restart backend 後單跑 `-k releases`，1 failed） | backend `8c540ff`（`finally { if (client) client.release(); }`）；紅綠分 commit；全套連跑 2 次 242 passed 3 xfailed |
| b | **改角色寫入小寫 `user`** | 降級功能壞：`authRole('User')` 比對區分大小寫，API 的驗證接受小寫 `user` 並原樣 `UPDATE`（`controllers/admin.js:56–59`），DB 存成 `user`，被降級的人立即 403。role 以 DB 為準（c）之後立即浮現 | [task-4-red-role-case.txt](evidence/phase-2/task-4-red-role-case.txt)，overview `236acf0`：DB 存成 `user`（期望 `User`） | backend `b34564b`：寫入前把 `user` 正規化為 `User`（`controllers/admin.js:57-58`，P2 後行號）；不改 `authorizeRoles`、Joi |
| c | **role 改由 DB 讀取** | 降級後舊 token 仍帶 `admin`，權限維持到 token 過期（30 天）。`controllers/userinfo.js:96,208` 簽進 token，`authorizeRoles` 讀 `req.user.role`（`middlewares/authorizeRoles.js:5`） | [task-4-red-role.txt](evidence/phase-2/task-4-red-role.txt)，overview `5c82bf8`：降級後仍 200 而非 403 | backend `dea8b01`：`verifyLoginToken` 既然每次都查 DB，就一併讀 `role` 覆蓋 token 內的值（`utils/authToken.js:60-61`）；契約 `db-contract.md` 的「JWT 與 DB 的角色分離」已註明已修 |
| d | **reset 原子化** | 「驗證 token」與「UPDATE 密碼」非原子，同一 reset token 併發可成功多次。引入點：Task 4 的 `1eff04f`（`main` 的重設端點本來就是 `middlewares/userinfo/index.js:291` 的無條件 `UPDATE … WHERE user_id = $2`） | [task-5-red-reset-atomic.txt](evidence/phase-2/task-5-red-reset-atomic.txt)，overview `ff3bd06`：4 個併發請求全 200（`[200, 200, 200, 200]`），10 次執行紅 10 次 | backend `00ed0fc`：`verifyResetToken` 回傳當下 password（同一次 SELECT），`UPDATE … AND password IS NOT DISTINCT FROM $3`，`rowCount` 0 回 400；NULL 密碼參數化；之後併發測試改穩定（`df3e57b`，30/30 全綠） |
| e | **`clearCookie` 帶 `maxAge`／`CAPTCHA_SECRET` 空值 fail closed** | `clearCookie` 帶 `maxAge` 送出 `captcha=; Max-Age=300`，cookie 並沒有被清除。引入點：Task 5 的 `0cb2a15`，`middlewares/userinfo/index.js:320`（`res.clearCookie('captcha', cookieOptions())`）。這是**測試端 workaround 掩蓋後端行為**的實例：implementer 在 `Api.request` 每次 `cookies.clear()`，理由寫錯 | [task-5-red-clearcookie.txt](evidence/phase-2/task-5-red-clearcookie.txt)，overview `9b68763`：`captcha=; Max-Age=300; Path=/; Expires=…2026…`（期望 1970 或 `Max-Age=0`） | backend `dd30027`：`clearCookie` 去 maxAge；`CAPTCHA_SECRET` 空字串 fail closed；overview `fb9449a` 移除 `cookies.clear()`，全套連跑兩次 282 passed 後確認 |
| f | **checkout 的 email 大小寫** | `middlewares/checkout/index.js:85` 的 `WHERE email = $1`，plan Files 漏列；spec §2.2 與 brief「所有查詢」為準 | [task-2-red-checkout.txt](evidence/phase-2/task-2-red-checkout.txt)，overview `feb9a25` | backend `9e90edf`（見 §1.2）；進度帳 Task 2 Ruling：「P4 範圍提前一行」 |
| g | **`/search` 雙 header** | 計畫（plan Task 7 Step 3）要求移除 `:197` 的頂層 `/search`、保留 `:75` 的子路由，前提是錯的：原本 hash 路由下同名覆蓋，**頂層才是生效者**；照計畫刪掉它之後搜尋頁出現兩個 header。引入點：Task 7 第一版（frontend `020842d`），行號 `router/index.js:75`、`:197`（`dev`） | [task-7-red-search.txt](evidence/phase-2/task-7-red-search.txt)，overview `965d6ae`：`test_search_page_single_header` header count 預期 1、實際 2 | frontend `fc97780`：保留頂層 `/search`、刪 HomeLayout 下的 search 子路由；spec §4.1「`/search` 行為不變」優先於 brief 字面（進度帳 Task 7 Ruling）。**只有 reviewer-opus 實測抓到**（見 §2.3） |
| h | **requireAuth 清狀態只在 401 時進行** | 兩段：(1) token 無效時 header 仍顯示已登入：`dev` 的 `router/index.js:11–19`，失敗只 `next('/admin/login')` 不清 `userStore`；(2) 修了 (1) 之後，網路錯誤也會被登出（後端暫時連不上不應把使用者登出） | (1) [task-7-red-search.txt](evidence/phase-2/task-7-red-search.txt) 的 `test_invalid_token_redirects_and_clears_state`（`assert 'garbage-token' is None`）；(2) [task-9-red-network-token.txt](evidence/phase-2/task-9-red-network-token.txt)（overview `1f58e17`） | (1) frontend `fc97780`：失敗分支呼叫 `userStore.logout()`；(2) frontend `44a3c52`：`get_user_status` 的 catch 增加 `unauthorized: err.response?.status === 401`，只有 401 才登出，網路錯誤只導向不清狀態 |
| i | **Google 新會員撞唯一索引回 409** | 併發註冊同一個 Google email 會撞 `user_email_lower_key` 回 500（P2 spec §2.2 明文要求 409）。Task 10 初版（`6ce56b3`）沒處理 | overview `4136c5a`；[task-10-red-review.txt](evidence/phase-2/task-10-red-review.txt)：單跑併發案例 10 次，紅 8 次、綠 2 次（**舊實作並非每次都紅**，是競態） | backend `da0779d`（訊息「Email已被使用」，比照註冊路徑）；新實作連跑 15 次全綠 |
| j | **authPages 縮小** | 前端 `authPages = ['/admin/login','/admin/register','/admin/forgotpw','/admin/resetpw']`（`dev:src/router/index.js:377`），已登入者開忘記密碼／重設密碼頁會被導到會員中心；但 spec §2.1 把忘記密碼定為 Google 會員設密碼的入口、已登入者從信件點重設連結也會被導走 | [final-s1-red.txt](evidence/phase-2/final-s1-red.txt)，overview `49bf3b9`：`test_logged_in_user_can_open_forgotpw_and_resetpw` | frontend `a9a68b5`：`authPages` 只剩 login／register（`router/index.js:213`）；overview `00574ed`：兩個既有回歸案例不再等 `/login/status`（forgotpw／resetpw 不再打該請求，原本會逾時）。已登入開 `#/admin/login` 仍導向會員中心（同一測試內斷言） |
| k | **Google 不覆寫頭像** | 已存在的會員用 Google 登入，`UPDATE … SET avatar_url = $1`（`controllers/userinfo.js:153–157`）會蓋掉使用者自己上傳的頭像 | [final-s2-red.txt](evidence/phase-2/final-s2-red.txt)，overview `49bf3b9`：`test_google_login_keeps_uploaded_avatar`、`test_google_first_bind_keeps_existing_avatar`（2 failed 1 passed） | backend `ec2394e`：兩處 SQL 改 `COALESCE(avatar_url, $1)`，新會員 INSERT 不變。**行為改變**：已有頭像的使用者不再同步 Google 的新頭像（附錄 B） |
| l | **`console.log(res)`** | `requireAuth` 每次導航印出會員資料。`dev:src/router/index.js:13` | 無（刪除一行 log，final-fix-report S5） | frontend `a9a68b5` |

## 2. Vibe coding 工作流

### 2.1 使用的 skill

| 階段 | Skill | 產出 |
|---|---|---|
| 設計 | `superpowers:brainstorming` | `docs/superpowers/specs/2026-11-12-p2-member-design.md`（2026-11-12 逐項確認，2026-11-18 使用者確認；overview `06d86ee`） |
| 計畫 | （是否以 `superpowers:writing-plans` 產生：**未查證**；plan 檔頭只標示執行用 `superpowers:subagent-driven-development`） | `docs/superpowers/plans/2026-11-12-p2-member.md`（12 個 Task；經 reviewer-opus 4 輪審查後定稿，overview `8c27324`） |
| 執行 | `superpowers:subagent-driven-development` | 每個 Task：Sonnet implementer + **Fable 與 Opus 雙 reviewer**；進度帳 `.superpowers/sdd/2026-11-12-p2-member/progress.md` |

流程沿用 P1：controller 產生 brief 檔 → implementer 實作並寫 report → controller 打包 diff → Fable 與 Opus 平行 review → 需要修就派 implementer 修 → 範圍限定的複審。**關鍵 prompt 以各 Task 的 brief 檔為準**：`.superpowers/sdd/2026-11-12-p2-member/task-1-brief.md` 至 `task-12-brief.md`（controller 寫給 implementer 的指令，**不入 git**，`.superpowers/` 不 commit）；本報告沒有逐字引用，審閱時可直接讀那 12 個檔。

P2 新增的做法：

- **每個 Task 都跑雙審**：使用者 2026-11-18 明確選擇，覆蓋全域「雙審只用在跨多檔／共用設定」的門檻（進度帳第一條 Ruling；成本較高）。
- **先補計畫、再開工**：計畫定稿前先經 reviewer-opus 4 輪審查（進度帳 Plan finalized），把審查發現併入計畫（commit 訊息：「補測試覆蓋、相依、helper 與審查修正」，overview `8c27324`）。**審查每一輪各抓到什麼，進度帳沒有逐輪紀錄（未查證）**；已確認併入計畫的項目見 §2.2。
- **Task 之間的相依掃描**：plan 開頭的「共用約定」表（token payload、cookie 格式、訊息字串、env 名稱），避免多個 Task 各寫各的值；「Review Focus」列 5 個特別要審的點。
- **mutation 驗證**：implementer 故意改壞後端確認測試會紅（Task 2、Task 8、Task 10 皆有），Task 10 的 mutation 證據存檔（`task-10-mutation.txt`）。
- **紅燈證據存檔**：[evidence/phase-2/](evidence/phase-2/)，23 個檔。plan Global Constraint 3：存檔前把本機絕對路徑換成相對路徑；Task 3 的紀錄顯示 evidence 曾含截斷 JWT，之後改用 `--tb=short`（進度帳 Task 3 minor）。
- **commit 授權**：使用者下令 commit spec 與 plan（進度帳 `8c27324` 那一行）。

### 2.2 使用者的決定與計畫審查抓到的問題

**使用者在 brainstorming 的決定**（P2 spec 以【使用者定】標記）：

| 決定 | 出處 |
|---|---|
| 主線是「註冊 → 登入 → 會員中心」，E2E 以它為主 | P2 spec §0 |
| `user.password` 改可為 NULL（方案 A，不選每人隨機密碼的 B） | P2 spec §2.1 |
| email 不分大小寫唯一，用 `lower(email)` 唯一索引（方案 ③，不改 citext） | P2 spec §2.2 |
| Google 遇到已存在 email：自動綁定並清密碼（方案 a） | P2 spec §2.3 |
| 密碼變動時舊的登入 token 失效（§3.1a） | P2 spec §3.1a |
| 忘記密碼保留，對 Google 會員等於「設定密碼」入口 | P2 spec §2.1 |
| 會員中心縮小版（只做「會員資訊」，其他三分頁標示「即將開放」，2026-11-12 選 (b)） | P2 spec §4.2 |
| Google 登入放在 P2 最後實作 | P2 spec §3.5 |
| spec 與計畫定案（2026-11-18，AskUserQuestion） | 主對話證實 |
| 每個 Task 都由 Fable 與 Opus 雙審（2026-11-18，AskUserQuestion） | 進度帳第 5 行、主對話證實 |
| 先補計畫再開工（2026-11-18，AskUserQuestion） | 主對話證實 |
| `api.js:302` 沒有 response 時的 TypeError 併入 Task 9（2026-11-18，AskUserQuestion） | 主對話證實 |
| 授權 Task 12 Step 1 的 `docker compose down -v`，並親自執行 | 主對話證實 |
| 使用者下令 commit 計畫（commit `8c27324`） | 進度帳第 10 行 |

**【Claude 定】但使用者未反對、可在審閱時推翻**：reset token 的用途標記與密碼指紋、驗證碼 HMAC cookie、不隱藏帳號是否存在、`provider_token` 寫 NULL、不回填既有資料、hash 路由下的外部回跳網址形狀（P2 spec §2.3、§2.4、§3.1、§3.2、§3.4、§4.1）。

**開工前，使用者透過 AskUserQuestion 親自決定（2026-11-18）**：(1) spec 與計畫定案；(2) 每個 Task 都由 Fable 與 Opus 雙審；(3) 先補計畫再開工；(4) `api.js:302` 沒有 response 時的 TypeError 併入 Task 9。另外：使用者下令 commit 計畫（commit `8c27324`）；使用者授權 Task 12 Step 1 的 `docker compose down -v`，並親自執行。

**P2 spec 本身經過 builder check，問題已併入**（P2 spec 檔頭狀態列）。builder check 抓到什麼：**查不到逐項紀錄**。我比對了 spec 從 `06d86ee` 到 `8c27324` 的差異（`git diff 06d86ee 8c27324 -- docs/superpowers/specs/`），只有 4 處小改：狀態列改「已定案（2026-11-18 使用者確認）」、兩處行號校正（`controllers/userinfo.js:113`→`:112`、`test_oauth_spike.py:67`→`:68`）、模型分工補「每個 Task 由 Fable + Opus 平行 review」；builder check 本身的發現在 `06d86ee` 之前就已併入、不在 git 內，所以**未查證**。

**計畫審查（4 輪 reviewer-opus）併入計畫的問題**，以計畫內容為證（每一項的審查輪次與提出者：進度帳沒有逐輪紀錄）：

| 問題 | 計畫中的處理 | 出處 |
|---|---|---|
| `e2e/__init__.py` 與 conftest 覆蓋：`tests/` 與 `e2e/` 都沒有 `__init__.py` 時，跑全套 `pytest`，後載入的 `e2e/conftest.py` 會蓋掉 `sys.modules["conftest"]`，讓 `tests/` 下所有 `from conftest import …`（例如 `API_BASE`）ImportError | **必須新增空的 `e2e/__init__.py`**；e2e 取用 helper 一律 `from e2e.conftest import …`；共用 fixture 用 importlib 載入、明確匯出，**不可** `from conftest import *` | plan Task 6，約 `:247` |
| interceptor 範圍：若 401 interceptor 不分路由一律處理，login／register／forgotpw／resetpw 頁會帶著過期 token 打 `/login/status`，被導回登入頁，重設密碼信的連結就打不開 | interceptor 只限會員 API，排除 `/login/status`、`/login/email`、`/login/google` | plan Task 9 Step 3，約 `:313` |
| 既有測試自簽的 JWT 在加 `pwv` 檢查後會全部 401 | Task 4 改 `auth_header` 並跑全套 | plan Review Focus 1 |
| 大小寫不同 email 登入既有小寫帳號、token 指向已刪除會員、NULL 密碼走忘記密碼、改完密碼的當下 session | 各自對應一個測試 | plan Review Focus 2–5 |
| helper 放哪裡：搬到 `tests/helpers.py` 屬於重構（違反 GC4） | 只用 importlib 方案 | 進度帳 Ruling（第 8 行） |
| `captcha_cookie()` helper 要放紅燈 commit，否則紅燈只會是 `NameError`；`.env` 既有檔要手動補 `CAPTCHA_SECRET` | 寫入 Task 5 步驟 | plan Task 5，約 `:226–228` |

**執行中才發現的計畫缺陷**（這些就是 §2.4 表內 Ruling 的來源）：Task 7 的 `/search`「保留 `:75`」前提錯（§1.22 g）；Task 11 的「mount 前 `replaceState`」實測無效（§1.16 b）；Task 10 的 mock 對任何 code 都簽發 token（附錄 B）；Task 9 的 interceptor 與 requireAuth 網路錯誤要併入（§1.22 h）；Task 6 的 `ci.sh --with-deps` 在本機需 sudo（§4.5）。「`api.js` bug 併入 Task 9」：plan 把 `throw err` 放 Task 7 Step 3，把 `patch_user_Profile` 無 response 的 TypeError 放 Task 9 Step 3（plan `:274`、`:313`）；**這個分派是使用者在開工前（2026-11-18）透過 AskUserQuestion 親自決定的：`api.js:302` 沒有 response 時的 TypeError 併入 Task 9**。

### 2.3 Fable vs Opus review 對照

來源是進度帳的「Task N review」行。**只有一方抓到的以粗體標示**。

| Task | Fable | Opus | 備註 |
|---|---|---|---|
| 1 | **退回**（清理隔離列為必須） | 通過（清理隔離只列建議） | 分歧在清理隔離的嚴重度。裁決採「必須」：違反 GC9 且已造成殘留資料（Task 1 紅燈殘留，需手動清除） |
| 2 | 退回（`lower(email)` 查詢沒有反向測試） | 退回（`make_user` 沒建 `user_level`，登入成功路徑 500） | **兩邊抓到不同的東西、互補**，兩項都採為必須 |
| 3 | 通過 | 通過 | 兩邊建議收斂：錯誤訊息斷言、拒絕後驗資料未變、PATCH 回應形狀。連線洩漏是 implementer 實測發現（不是 reviewer） |
| 4 | 通過 | 通過 | 建議收斂：`auth_not_mandatory` 測試、single-use 訊息斷言、pwv 分支案例、alg none、role 取自 token；補強後 Opus 複審通過，role 大小寫 bug 修完後 Fable 複審通過 |
| 5 | 退回（只抓到併發測試 flaky） | **退回**（3 項必須：flaky 併發測試、`CAPTCHA_SECRET` 值違反共用約定、`cookies.clear()` 的理由錯且掩蓋 `clearCookie` 帶 maxAge） | **約定值與 clearCookie 只有 Opus 抓到**（Opus 有容器實測），裁決採 Opus |
| 6 | 通過 | 通過 | 共同建議：`combobox` role、`exact=True`、補證據檔。`collection` 雙重回應由 implementer 診斷，不是 reviewer |
| 7 | 通過（未抓到） | **退回**（`/search` 雙 header） | **只有 Opus 抓到**，且有實測；brief 的前提錯（頂層才是生效者）。裁決採 Opus |
| 8 | 通過 | 通過 | 共同建議：`new_page` 開連結、舊密碼失效、cookie domain 由 `API_BASE` 推、heading 斷言、會員中心 email |
| 9 | 退回（另指出兩個 `goto` 間無等待可能 race） | 退回 | 必須修正一致：network_error 測試的紅燈 evidence 原因不符（應死在 token 斷言）。race 只有 Fable 提到；implementer 回報「原死在 `wait_for_url` 的原因未明、競態僅為推測」（Task 9 report） |
| 10 | 退回 | 退回 | **兩邊一致**：紅燈全卡同一個 500 無分辨力（需 mutation 證據）、首次綁定後新 token 可用無測試、既有會員＋未驗證信箱無測試。進度帳記載 Fable 複審通過；**task 指示把 Task 10 列為分歧例子，與進度帳「兩邊一致」不符，以進度帳為準，已列入待確認** |
| 11 | 通過 | 通過 | 建議一致：清 code 無斷言、`replaceState({})` 跳過 router 初始化、註解根因錯、`.env.example` 半套 |
| 最終（整支分支） | 需先修 M1 | 可進 Task 12（修 M1） | M1（`test_invalid_token_redirects_and_clears_state` 的 flake）兩者根因一致且皆重現；最終修正波見 §1.22 j、k 與 §3.3；Opus 複審「全 ADDRESSED」。最終審查的項目為 S1、S2、S3、S5；**S4 是「測試碼品質」**（例如寫死環境值、依賴版面的選擇器），被分到已知限制或可忽略，沒有修（主對話證實） |

觀察：P2 與 P1 一樣，雙審的互補價值明顯：Task 5 的約定值與 `clearCookie`、Task 7 的 `/search` 只有 Opus（有做實機測試）抓到，Fable 都漏掉；Task 1 的嚴重度判斷與 Task 2 的兩個缺口則是兩邊各抓一半。Task 3 的連線洩漏、Task 6 的 `collection` 雙重回應（§3.2、附錄 B）都是 implementer 在實測中發現，不是 reviewer。

### 2.4 主對話的 Ruling

來源：進度帳的 `Ruling:` 行（Task 1 清理隔離那一條是進度帳寫在 review 分歧行內的裁決，沒有 `Ruling:` 前綴，也一併列入）。「錯了的代價」是進度帳記載的「若錯」。

| # | 決定 | 理由 | 錯了的代價 |
|---|---|---|---|
| 1 | 每個 Task 用 reviewer-opus + reviewer-fable 平行雙審 | 使用者 2026-11-18 明確選擇，覆蓋全域門檻 | 成本較高 |
| 2 | 實作派 implementer（sonnet），不另外指定 model | 使用者 CLAUDE.md 規定 | 無 |
| 3 | E2E 共用 helper 只用 importlib 載入 `tests/conftest.py`（方案 b） | 方案 (a) 搬檔違反 GC4 不得順手重構 | e2e conftest 多一段 importlib 樣板 |
| 4 | 接受刪除 `get_tourSearch` 的 404 檢查 | `db-contract.md:1733` 記載從未生效、`tour_ids` 無來源；雙審皆同意 | 補回 404 行為 |
| 5 | Task 1 清理隔離採「必須」 | 違反 GC9 且已造成殘留 | （Task 1 review 分歧裁決，進度帳未記「若錯」） |
| 6 | `make_user` 預設建 `user_level` | 後續 Task 4／7／9 皆假設 `make_user` 可登入 | fixture 多一筆資料 |
| 7 | checkout 的 email 查詢 Task 2 一併改 `lower()` | spec §2.2 與 brief Step 4 寫「所有」為準，plan Files 漏列 | P4 範圍提前一行 |
| 8 | PATCH `/info` 部分更新 500 留到 P3 修，P2 補 strict xfail 列管並寫入報告已知限制 | 屬合法輸入路徑 bug、需設計決定、UI 碰不到 | P2 報告多一條已知限制 |
| 9 | `userProfile.js` 連線洩漏在 Task 3 修，紅綠分 commit | 會讓全套／ci.sh 重跑時 pool 耗盡、測試不穩定，影響 P2 完成標準 | P2 多一個 backend 小修 |
| 10 | 其他 `pool.connect` 疑似漏 release（`cart.js`、`checkout.js`、`product.js:1360`、`newebpay.js` 部分路徑）不在 P2 修，列入 P3（product）／P4（cart／checkout／newebpay） | 屬其他階段範圍，全套與 ci.sh 目前連跑兩次穩定 | 重複呼叫這些 API 會耗盡 pool |
| 11 | `verifyLoginToken` 改由 DB 取 role（紅綠） | 已查 DB 成本極低，補上 Task 1 改角色的另一半（降級後舊 token 仍有 admin 權限 30 天） | 超出 spec 字面範圍一項 |
| 12 | 測試強化在 Task 4 補（test-only） | 安全測試且 Task 5 會重寫 resetpw，先釘住 | 多一個 commit |
| 13 | resetpw 原子化（條件式 UPDATE＋併發測試）併入 Task 5 | Task 5 本就重寫 `patchuserresetPW`，雙審一致 | P2 報告列已知限制 |
| 14 | 改角色 API 寫入小寫 `user` 導致 `authRole(User)` 403，在 P2 修，正規化於寫入點，不改 `authorizeRoles` | 與 Task 1 改角色同一功能、role 以 DB 為準後立即浮現 | 多一個 backend 小修 |
| 15 | `clearCookie` 去 maxAge（紅綠），之後嘗試移除 `cookies.clear`，全套兩次綠則移除、否則保留並更正理由 | 測試 workaround 不應掩蓋後端行為 | 多一輪 |
| 16 | 空字串 `CAPTCHA_SECRET` fail closed 一併修；補竄改負面測試與 NULL 併發參數化 | 雙審一致建議、成本低 | 多數行測試 |
| 17 | `ci.sh` 僅在 `CI=true` 時 `playwright install --with-deps`，本機不帶 deps | 本機 chromium 已可啟動、`--with-deps` 需 sudo 會卡住 Task 7／10／12 的本機 ci.sh | 使用者可改免密碼 sudo 推翻 |
| 18 | 不在 P2 修 `collection` 雙重回應，`test_favorite_list` 改用 `Connection: close` 隔離並註明連結已知 bug | 不讓已知 bug 造成 ci.sh 隨機紅 | 測試層遮蔽一個已列管 bug |
| 19 | 保留頂層 `/search`、刪 HomeLayout 下的 search 子路由 | spec §4.1「`/search` 行為不變」優先於 brief 字面 | 搜尋頁版面需另議 |
| 20 | `requireAuth` 失敗分支呼叫 `userStore.logout()` 清狀態（紅綠） | token 無效時 header 仍顯示已登入，Task 9 interceptor 排除 `/login/status` 不會補到 | 多一行前端 |
| 21 | Task 9 追加：`requireAuth` 僅在 `/login/status` 回 401 時 logout，網路錯誤只導向不清狀態（Task 7 carry-in） | 後端暫時連不上不應把使用者登出 | 多一個前端分支 |
| 22 | 保留亂填 code 測試但改名 `test_google_login_bogus_code_rejected`（斷言 400＋無新增會員），註解與報告寫明 code 驗證由 Google 負責、mock 無法模擬 | 真實行為值得回歸、但不宣稱驗了 code | 測試名與實際驗證範圍有落差 |
| 23 | Google 新會員撞 23505 在 P2 修為 409（紅綠） | spec §2.2 明文，註冊已有現成寫法 | 多數行後端 |
| 24 | sub 不同、email 相同的現行行為用測試釘住並列已知限制（P7 接真 Google 前決定） | （進度帳未寫理由） | （進度帳未寫） |
| 25 | 新增 `frontend/src/oauthRedirect.js`（side-effect 模組，`main.js` 首行 import）；根因更正：history 建立時即從 hash 讀位置，search 永遠殘留 | ES module import 先於 `main.js` 本體執行，brief 的「mount 前 replaceState」實測無效 | 多一個小檔 |
| 26 | （最終審查之後）最終修正波納入 M1 flake（兩處同步點）、S1 authPages 縮為 login／register、S2 Google 登入不覆寫既有頭像、S3 契約過時敘述與行號、刪 `requireAuth` 的 `console.log(res)` | 皆小且影響 P2 主流程或作品集文件正確性 | 多數行前端／後端 |
| 27 | 更正 `oauthRedirect` 的根因：history 建立時即從 hash 讀位置、之後只寫 `#` 相對網址，search 永遠殘留（非「讀 search 當 base」）；註解與說明同步改 | 原說法不符實測，註解會誤導後人 | 註解與根因說明錯誤留在程式碼 |
| 28 | 補 backend `.env.example` 的 `CAPTCHA_SECRET`、`COOKIE_SAMESITE`、`COOKIE_SECURE`、`CORS_CREDENTIALS`（值與註解同總覽 repo；backend `124e85c`，報告初稿之後） | 只 clone backend 時範本缺變數，`CAPTCHA_SECRET` 空值會 fail closed | 只改文件範本；補錯不影響執行 |

### 2.5 AI 出錯 / 人介入紀錄

- **計畫前提錯（Task 7）**：plan 以為移除頂層 `/search` 安全；實際頂層才是生效者，照做會讓搜尋頁出現兩個 header（§1.22 g）。Fable 通過、Opus 實測退回。
- **計畫前提錯（Task 11）**：brief 的「mount 前 `history.replaceState`」實測無效；implementer 停下來回報，主對話同意新增 `oauthRedirect.js`（§1.16 b），後續更正根因說明。
- **implementer 的 workaround 掩蓋後端 bug（Task 5）**：為了讓共用 `Api` session 測試通過，每次 `cookies.clear()` 並寫了錯誤理由；真實原因是 `clearCookie` 帶 `maxAge`（§1.22 e）。
- **紅燈 evidence 錯誤歸因（Task 9）**：`task-9-red.txt` 記錄 network_error 測試死在 `wait_for_url`，是錯的，以 `task-9-red-network-token.txt` 更正；原因未能重現（Task 9 report）。
- **紅燈沒有分辨力（Task 10）**：8 個失敗全是同一個 500，必須補 mutation 證據（§1.3）；mutation (e) 一開始沒有任何測試轉紅，揭露「DB 存混合大小寫 email」的測試缺口。
- **commit 訊息與實際不符**：`c760cf1` 的訊息寫 200，實際斷言 400；後續 commit `38e2770` 修正測試為 200，不改寫歷史（進度帳 Task 4 minor）。
- **紅燈順序刻意調整**：Task 5 的紅燈 commit `ff3bd06` 排在 HMAC 綠燈之後；若先寫，舊後端會因簽章 cookie 全回「驗證碼錯誤」，紅得不是原因（Task 5 report）。
- **一個 commit 混了不同性質的改動**：`df3e57b`（「併發測試改穩定」）同時改了 `.env.example`（進度帳 Task 5 minor）。
- **紅燈 commit 被 amend**：`c500f66`（Task 8）；因為尚未 push，Task 8 report 有註明。
- **測試中斷後殘留資料讓下一次 ci.sh 紅**：Task 1（紅燈失敗殘留 2 組資料，`test_seed` 14 項失敗）、Task 10（指令逾時被中斷，殘留 `e2e-` 會員，`test_seed` 計數 user 4 對 3）、最終修正波（逾時中斷的 e2e 留下 1 個 `p0-` 會員）都發生過；都用 `delete_user` 手動清除後重跑才綠。**操作指南 §4.4 記載了處理方式。**
- **flake**：Task 11 時 `test_invalid_token_redirects_and_clears_state` 在 ci.sh 失敗 1 次（`authToken` 仍為 `garbage-token`），最終審查兩位 reviewer 都重現，根因是兩處同步點（`reload` 與 `goto` 沒有等 `/login/status` 回應）；最終修正波 `c82e801` 修，臨時腳本讓 `/login/status` 延遲 1.5 秒：舊寫法紅、新寫法綠；10 次連跑第一版 12 次中 2 次在 `network_error_keeps_token` 逾時，改用 `wait_for_url` 後連跑 15 次全綠。
- **人工確認節奏**：每個 Task 完成後主對話向使用者回報；使用者在開工前（2026-11-18）透過 AskUserQuestion 親自決定的事項見 §2.2 表。
- **環境**：Task 1 之前，WSL 內沒有 docker 指令，要使用者開啟 Docker Desktop WSL integration（進度帳 Blocker）。

## 3. 測試方法

### 3.1 測試分層

| 層 | 內容 | 檔案 |
|---|---|---|
| API 契約／安全 | 會員 API 的正常、驗證錯誤、401／403；token 用途分離、密碼指紋、`alg: none`、reset 單次使用與併發（20 次連跑全綠，Task 5 複審）、驗證碼 HMAC 竄改、改角色 403／降級後立即失權 | `tests/test_member_auth.py`（本次 ci.sh 內 85 個案例） |
| DB 狀態 | V3 套用、`password` nullable、`user_email_lower_key` 唯一索引、混合大小寫 email 被擋、Google 新會員 `password IS NULL`、`provider_token` 為 NULL | `tests/test_migrations.py`、`tests/test_google_login.py` |
| Google（mock-oauth） | `email_verified` 各種值被拒、首次綁定清密碼＋舊 token 失效、已綁定不清密碼、混合大小寫既有 email、併發撞唯一索引回 409、不覆寫頭像 | `tests/test_google_login.py`（23 個案例）、`tests/test_oauth_spike.py` |
| E2E（Playwright Python） | 主線：註冊 → 登入 → 會員中心看到自己的資料、改偏好、改密碼；未登入開會員中心被擋回登入頁；密碼錯 3 次鎖定訊息；忘記密碼 → 從 Mailpit 取信中連結 → 重設密碼 → 新密碼登入；token 過期／無效／網路錯誤；頭像上傳；Google 登入經 mock-oauth 走一次；404；登出留在 SPA | `e2e/test_member_flow.py`（22 個案例）、`e2e/conftest.py` |

本次 ci.sh 各檔收集數（`PASSED`＋`XFAIL` 行）：`test_member_auth` 85、`test_db_contract` 45、`test_api_smoke` 36、`test_seed` 29、`test_views_b` 24、`test_google_login` 23、`test_views_a` 22、`e2e/test_member_flow` 22、`test_views_c` 13、`test_product_routes` 7、`test_migrations` 7、`test_build_seed` 7、`test_frontend` 5、`test_storage` 3、`test_oauth_spike` 2、`test_mail`／`test_health`／`test_async_errors` 各 1。

### 3.2 值得一看的技巧

- **紅燈要紅在對的原因**：Task 4 為避免 JWT 進 evidence，測試先取 status 變數再 assert、連結只比對前綴；Task 9 的 evidence 因原因歸錯而被更正（§2.5）。
- **mutation 驗證**（Task 10，[task-10-mutation.txt](evidence/phase-2/task-10-mutation.txt)）：(a)(b)(c)(d)(f)(g) 一次轉紅；(e) 一開始沒紅，補了「混合大小寫既有 email」測試才紅。Task 2 也做過（5 處查詢改回 `email = $1` → login 與 forgetpw 反向測試轉紅）。
- **併發測試**：reset 併發（4 個請求、同一 token，期望 `[200, 400, 400, 400]`）；第一版 flaky，改為「先以贏家登入、再只驗一個輸家」並參數化 bcrypt／NULL 密碼，連跑 30 次全綠（Task 5 fix）；Google 新會員併發撞唯一索引（單跑 10 次，舊實作紅 8 次）。
- **注入 cookie 避開 SVG**：伺服器簽、瀏覽器端無法解 SVG 答案，所以 E2E 用 `context.add_cookies` 注入 `captcha_cookie("abcde")`（Task 8 report）。
- **mock-oauth interactive 模式**：`docker-compose.yml` 的 `JSON_CONFIG: '{"interactiveLogin": true}'`，測試以 `mock_google_code(claims)` POST 登入表單（欄位 `username`、`claims` JSON）取得 `code`，這樣才能自訂 `email_verified`；`scripts/ci.sh` 的就緒網址 `/google/.well-known/openid-configuration` 在 interactive 模式下仍回 200（Task 10 report）。
- **E2E 選擇器**：`get_by_role` 與 `exact=True`；按鈕內有 bootstrap-icons 字元進入 accessible name 的案例用子字串比對（Task 9 report）。
- **`collection` 雙重回應隔離**：`GET /user/collection/info/all` 每次送兩次回應（`docs/reports/phase-1.md:323` 已知），第二次寫入觸發 `ERR_HTTP_HEADERS_SENT`，socket destroy，keep-alive 重用連線時有約 1% 機率讓下一個請求 `ConnectionError`；`test_favorite_list` 改用 `Connection: close` 隔離（overview `eb73b31`；證據 `.superpowers/sdd/2026-11-12-p2-member/task-6-connerr-evidence.txt`，不在 git 內）。

### 3.3 測試數量與 CI 結果

| 里程碑（各 Task 回報的數字，來源：進度帳與各 Task report） | passed | xfailed |
|---|---|---|
| P1 結束 | 195 | 2 |
| Task 1 | 199 | 1 |
| Task 2 | 224 | 1 |
| Task 3（含連線洩漏修正） | 242 | 3 |
| Task 4 | 267 | 3 |
| Task 5（修正後） | 282 | 3 |
| Task 6 | 282（另 1 個 E2E 刻意紅燈） | 3 |
| Task 7 | 290 | 未載 |
| Task 8 | 292 | 未載 |
| Task 9 | 303 | 3 |
| Task 10 | 324 | 2 |
| Task 11 | 325 | 2 |
| 最終修正波後 | 329 | 2 |
| **P2 最終（本次兩次 ci.sh）** | **329** | **2** |

（xfail 從 1 變 3：Task 3 補了 PATCH `/info` 的兩個 strict xfail；3 變 2：Task 10 移除 `test_oauth_spike.py` 的 xfail。）

**本機驗證（Task 12 Step 1，使用者先執行 `docker compose down -v`）**：非互動（stdin `/dev/null`），`scripts/ci.sh` 連跑兩次。**第 1 次是乾淨環境；第 2 次沒有再 `down -v`，所以保留 `pgdata` volume**（`docker-compose.yml` 的 postgres 用具名 volume `pgdata`；`ci.sh` 的 `--renew-anon-volumes` 只更新匿名 volume），比照 P1 的寫法。環境：overview `b8141d4`（執行時；其後只新增 `84189ac` 的契約加註與 docstring，沒有改行為）、backend `ec2394e`、frontend `a9a68b5`。

| 次（資料庫狀態） | 結果 | pytest 計時 | 整個 `scripts/ci.sh` 牆鐘（含 `docker compose up --build`、等服務、`uv sync`、`playwright install`） | exit |
|---|---|---|---|---|
| 第 1 次（乾淨，`down -v` 之後） | **329 passed, 2 xfailed** | 74.24 秒（1:14） | 115 秒 | 0 |
| 第 2 次（保留 volume） | **329 passed, 2 xfailed** | 74.12 秒（1:14） | 79 秒 | 0 |

兩次的 xfail 都是 `tests/test_member_auth.py::test_patch_profile_info_name_only`、`::test_patch_profile_info_preference_only`（見 §0 與附錄 B）。第 1 次的 `curl: (52) Empty reply from server` 是 `ci.sh` 的 `wait_for frontend` 在 vite 啟動前的重試輸出，最後 `✅ frontend`。**跑完兩次之後**，只改了 `docs/db-contract.md` 與 `e2e/test_member_flow.py` 的 docstring（`84189ac`）；改完後重跑受影響的 5 個 E2E 案例（`-k "expired_token or logged_in_user_can_open"`）皆通過、`--collect-only` 收集數為 331（329＋2 xfail），與 ci.sh 的總數一致。

**GitHub Actions**：綠燈 run [44323636173](https://github.com/nohungry/tripeasy/actions/runs/44323636173)（`e1901f9`，main）；結果：**329 passed, 2 xfailed**，Using CPython 3.13.18，耗時 74.13 秒。注意本機 `ci.sh` **不跑** `--with-deps`（見 §4.5），所以 CI 上 `CI=true` 才會走的 `playwright install --with-deps chromium` 這條分支，在首次 push 之前沒有被實際驗證過（進度帳 Task 6 minor）。**已解決**：tag 時點的兩個失敗 run 都在 `uv sync` 就失敗，沒跑到這一步；這條分支是在綠燈 run 44323636173 第一次實際跑到並通過。

#### CI 在 tag 時點失敗：runner 映像改版

- **現象**：`phase-2` tag（merge commit `e06ee26`）push 之後，tag 那次的 run 44289947855 與 main 那次的 run 44289947877 都失敗。
- **原因**：GitHub 的 `ubuntu-latest` 換成 ubuntu-26.04 映像，系統 Python 變成 3.14.4；`psycopg-binary` 3.2.3 沒有 cp314 wheel，`uv sync` 因此失敗。
- **修正**：`e1901f9` 新增 `.python-version`（3.13），並把 `runs-on` 固定為 `ubuntu-24.04`。修正後 main 的 run 44323636173 綠燈。
- **決定：`phase-2` tag 不移動**。tag 指向的 commit 仍是 `e06ee26`，所以 tag 那次的 run（44289947855）會一直是紅燈；P2 的程式內容沒有變，CI 結果以上面的綠燈 run 為準。
- **留給 P3 的後續項目**：
  - (a) `requires-python` 加上 `<3.14` 上限，或升級 psycopg 到有 cp314 wheel 的版本。
  - (b) 鎖定 uv 版本；`setup-uv` action 本身固定在 v10.3.3，但沒有指定 `version` input，所以安裝的 uv 是最新版（這次是 0.13.9），同樣會隨時間漂移。

## 4. 操作指南

### 4.1 切到這個版本並啟動

```bash
git clone https://github.com/nohungry/tripeasy.git && cd tripeasy
git clone -b "$(grep BACKEND_REF refs.env | cut -d= -f2)" https://github.com/nohungry/tripeasy-backend.git backend
git clone -b "$(grep FRONTEND_REF refs.env | cut -d= -f2)" https://github.com/nohungry/tripeasy-frontend.git frontend
scripts/ci.sh        # 啟動全部服務並跑測試
```

需要 Docker（含 Compose v2）與 [uv](https://docs.astral.sh/uv/)；服務網址同 `docs/reports/phase-0.md` §4.1。**`refs.env` 是 `BACKEND_REF=phase-2`、`FRONTEND_REF=phase-2`，現在指的是 tag**；三個 repo 的 `phase-2` tag 都已 push（總覽 `e06ee26`、backend `3d835a6`、frontend `71a2171`），README 的 clone 指令現在可以直接使用。

總覽 repo 的 `phase-2` tag 本身沒有 `.python-version`（`e1901f9` 才加入），要重現 P2 的測試結果請用 `main`。

### 4.2 測試帳號

- **seed 帳號**（載入自 `db/seed/R__seed.sql`，明文密碼見 `.env.example` 檔頭）：`alice@example.com`（`User`，有訂單、收藏、購物車、優惠卷）、`bob@example.com`（`admin`）、`carol@example.com`（`User`），密碼都是 `Tripeasy123`。**seed 帳號只能讀，測試不得改它們的密碼或綁定狀態**（plan Global Constraint 9）。
- **自己註冊的帳號**：前端 `http://localhost:5173/#/admin/register`，填姓名、email、密碼（需符合 `passwordPattern`）、三個偏好。
- **Google 會員（沒有密碼）**：用下面 §4.3 登入即可建立；這種帳號用 Email 登入會得到「此帳號使用 Google 登入，請改用 Google 登入，或透過忘記密碼設定密碼。」，不累計錯誤次數。
- **測試自建的帳號**：pytest 與 E2E 用 fixture 建立 `p0-…`、`e2e-…`、`a.…`／`g.…` 等前綴的會員（前綴依最終修正波回報：`e2e-`、`g.`、`p0-`、`a.`），結束時清除。

### 4.3 用 mock-oauth 以 Google 登入（手動）

1. 啟動全部服務（`docker compose up -d`），開 `http://localhost:5173/#/admin/login`。
2. 點登入頁的 **Google 圖示**（`.icon-circle.google`）；瀏覽器會跳到 mock-oauth 的授權頁 `http://localhost:8090/google/authorize?…`（interactive 表單）。
3. 表單有兩個欄位：
   - **`Enter any user/subject`**（HTML placeholder；form 欄位名 `username`）：填一個字串（E2E 與 `mock_google_code` 都填與 claims 的 `sub` 相同的值）。
   - **`Optional claims JSON value`**（欄位名 `claims`）：填 claims JSON，例如：
     ```json
     {"sub":"g-demo-1","email":"demo.google@example.com","email_verified":true,"name":"Google 測試員","picture":"https://example.com/g.png"}
     ```
     測試的做法是 `sub` 與上一欄相同（是否必須一致：未查證）；**一定要有 `email` 與 `email_verified: true`**，否則後端回 400（沒有 email：「Google 帳號資訊異常，無法取得 email」；`email_verified` 不是 `true`：被拒絕）。claims 欄位留空會怎樣：**未查證**。
4. 按 **Sign-in**。瀏覽器回跳到 `http://localhost:5173/?code=…`，`oauthRedirect.js` 把 `code` 搬進 hash，登入頁處理後進會員中心 `#/admin/userprofile`。
5. 試「預先劫持」情境：先用 Email 註冊 `demo.google@example.com`，再用同一 email 走一次 Google 登入，原密碼會被清成 NULL（第一次綁定）；再用「忘記密碼」為它設新密碼後，Email 與 Google 都能登入。
6. mock 不會驗證 code（對亂填的 code 照簽 token），所以不要拿它判斷 code 驗證有沒有生效（附錄 B）。

### 4.4 忘記密碼（手動）與測試中斷後的清理

- 忘記密碼：登入頁點「忘記密碼」→ 輸入 email → 開 Mailpit `http://localhost:8025` 取信 → 連結形狀 `http://localhost:5173/#/admin/resetpw?token=…` → 輸入新密碼與驗證碼圖上的文字（驗證碼是 SVG 路徑圖，要人眼看）。
- **測試中斷後要清掉殘留資料**：測試被逾時或手動中斷時 teardown 不會跑，會留下 `p0-`、`e2e-` 前綴的會員，讓 seed 的 exact count 測試（`test_seed.py`）持續紅（P2 期間發生過三次，§2.5）。處理方式二選一：(1) 用 `tests/conftest.py` 的 `delete_user` 刪掉那個會員（最終修正波的做法）；(2) 使用者自己執行 `docker compose down -v`（agent 不代跑，plan Global Constraint 7）。

### 4.5 本機 `.env` 要補的新變數；為什麼本機 `ci.sh` 不帶 `--with-deps`

- **`scripts/ci.sh` 只在 `.env` 不存在時才從 `.env.example` 複製**，所以**既有的本機 `.env` 要手動補**這四個新變數，然後 `docker compose up -d backend`：
  ```
  CAPTCHA_SECRET=local-captcha-secret-change-me
  COOKIE_SAMESITE=Lax
  COOKIE_SECURE=false
  CORS_CREDENTIALS=true
  ```
  `CAPTCHA_SECRET` 沒設或空字串，後端會 **fail closed**（丟出「CAPTCHA_SECRET 未設定」）；測試端的 `captcha_cookie()` 也直接讀 `os.environ["CAPTCHA_SECRET"]`，缺少會 `KeyError`。`DEFAULT_OAUTH_PASSWORD` 已移除，可從 `.env` 刪掉。部署跨網域時改 `COOKIE_SAMESITE=None`、`COOKIE_SECURE=true`（P7）。
- **backend repo 自己的 `.env.example` 原本也缺這幾個變數，已補**（backend `124e85c chore: .env.example 補 P2 新增的驗證碼與 cookie 變數`，值與註解和總覽 repo 一致；只改文件範本，未跑 ci.sh）。補之前我以 `grep -n "CAPTCHA\|COOKIE\|CORS_CRED\|DEFAULT_OAUTH\|GOOGLE" backend/.env.example` 驗證，只有三個空值的 `GOOGLE_CLIENT_ID`／`GOOGLE_CLIENT_SECRET`／`GOOGLE_REDIRECT_URI`，沒有 `CAPTCHA_SECRET`、`COOKIE_SAMESITE`、`COOKIE_SECURE`、`CORS_CREDENTIALS`。當時 P2 只更新了總覽 repo 的 `.env.example`（overview `65cf8f9`）。
- **前端的 env**：`frontend/.env.example` 已改成本機指向 mock（`VITE_Redirect_BASE=http://localhost:5173/`、`VITE_GOOGLE_CLIENT_ID=tripeasy-local`、`VITE_GOOGLE_AUTH_URL=http://localhost:8090/google/authorize`，frontend `df6842e`）；`frontend/.env.development` 沒有改動（本來就指向 mock）。
- **為什麼本機 `ci.sh` 不帶 `--with-deps`**：`uv run playwright install --with-deps chromium` 要安裝系統套件，需要 sudo 密碼；本機非互動執行會卡在 `sudo`（Task 6 report：`"a terminal is required"`）。本機 chromium 已可啟動，所以 `scripts/ci.sh` 只在 `CI` 環境變數非空時才帶 `--with-deps`（overview `81c94d3`；Ruling 17）。限制：判斷是「非空」，所以 `CI=false` 也會被當作 CI（進度帳 Task 6 minor）。

## 附錄

### A. 變更檔案清單

**總覽 repo**（`git diff --stat main..phase-2`：43 檔 +4751 −81，統計到 `b8141d4`），主要部分：

- 測試：`tests/test_member_auth.py`（新，約 809 行）、`tests/test_google_login.py`（新，321 行）、`tests/conftest.py`（本階段共 125 行變動：`make_user(password=)`、`TEST_PASSWORD(_HASH)`、`delete_user` 清完整、`password_fingerprint`、`login_token`、`reset_token`、`captcha_cookie`、`mock_google_code`）、`tests/test_migrations.py`、`tests/test_api_smoke.py`、`tests/test_oauth_spike.py`、`tests/test_frontend.py`
- E2E：`e2e/__init__.py`、`e2e/conftest.py`、`e2e/test_member_flow.py`、`e2e/fixtures/avatar.png`
- 設定：`pyproject.toml`（`pytest-playwright==0.5.2`、`testpaths`）、`uv.lock`、`scripts/ci.sh`、`docker-compose.yml`（mock-oauth interactive）、`.env.example`、`refs.env`
- 文件：`docs/superpowers/specs/2026-11-12-p2-member-design.md`、`docs/db-contract.md`、`docs/superpowers/plans/2026-11-12-p2-member.md`、`docs/reports/evidence/phase-2/*.txt`
- 之後新增（不在上列統計內）：`docs/reports/phase-2.md`、`README.md`、`84189ac`（契約 §4.2 (b) 加註、E2E docstring）

**backend**（`main..phase-2`：14 檔 +282 −106）：`migrations/V3__p2_user_auth.sql`（新）、`src/utils/authToken.js`（新）、`src/utils/captcha.js`（新）、`src/controllers/userinfo.js`、`src/controllers/admin.js`、`src/controllers/userProfile.js`、`src/middlewares/auth.js`、`src/middlewares/auth_not_mandatory.js`、`src/middlewares/checkout/index.js`、`src/middlewares/product/index.js`、`src/middlewares/userinfo/index.js`、`src/routes/admin.js`、`src/server.js`、`src/utils/Validator/userInfo_Validator.js`。

**frontend**（`dev..phase-2`：11 檔 +168 −201）：`src/router/index.js`、`src/utils/api.js`、`src/main.js`、`src/oauthRedirect.js`（新）、`src/views/NotFound.vue`（新）、`src/views/admin/loginPage.vue`、`src/views/admin/resetpwPage.vue`、`src/views/admin/userprofilePage.vue`、`src/components/HeaderComponent.vue`、`src/components/HeaderReal.vue`、`.env.example`（以上為 `git -C frontend diff --stat dev..phase-2` 的 11 檔）。

### B. 已知限制

以下是 P2 發現、依 Ruling **沒有在 P2 修**的問題。出處皆為進度帳的 `minor (deferred)`、`known limitation`、`carry` 與各 Task report 的「P3 以後」。**進度帳沒有「(b) 類」這個標籤**；task 指示要求「被兩位最終審查分到 (b) 類的項目」，我無法對應，所以這裡以**進度帳所有仍未修的 minor／known limitation／carry 全部列入**為準，並已排除後來已修的項目（契約行號校正 `b8141d4`、resetpw 原子化 `00ed0fc`、`requireAuth` 的 `console.log`、requireAuth 只在 401 清狀態 `44a3c52`、Google 撞 23505 `da0779d`、M1 flake `c82e801`、契約 §4.2(b) 加註 `84189ac`）。已列入審閱時要確認的事項。

#### B.1 需要醒目標示的項目

- **【安全，P7 接真 Google 前必補】OAuth 沒有 `state` 驗證（login CSRF）**：前端的授權網址沒有帶 `state`（`dev:src/views/admin/loginPage.vue:156-159`）、後端也沒有對應的驗證，攻擊者可誘使受害者的瀏覽器以攻擊者的 `code` 完成登入（登入 CSRF）。mock 環境下不會被利用，但接真 Google 之前一定要補（進度帳 Task 11 known limitation）。
- **【穩定性】pool 連線洩漏在 Task 4 之後會放大，波及全站會員 API**：`cart.js:12,94,144`、`checkout.js:12,129`、`product.js:609`（release 在 `:796`）與 `:1360`（整檔僅一個 release，疑似漏）、`newebpay.js:63,161`（只走部分路徑）的 `pool.connect()` 疑似漏 `release`（Task 3 報告；Ruling 10 列入 P3／P4）。**放大的原因（我的推論，已列入待確認）**：Task 4 之後 `auth.js`／`auth_not_mandatory.js` 每個需要登入的請求都用 `pool.query` 查一次 DB（`utils/authToken.js:51`）；pool 預設 max 10，一旦被洩漏耗盡，**所有**帶 token 的會員 API 都會卡住，不再只是洩漏的那支端點受影響。P2 內只修了 `userProfile.js`（§1.22 a）。
- **【驗證範圍】code 驗證在 mock 層測不到**：mock-oauth 對任何 code（含亂填、重複使用）都簽發 token（Task 10 spike）。`test_google_login_bogus_code_rejected` 驗的是「userinfo 缺 email 時拒絕」（400「Google 帳號資訊異常，無法取得 email」，且 `user`／`socialLogin` 筆數不變），**不是** code 本身被拒（進度帳 Task 10 Ruling）。
- **【行為】sub 不同但 email 相同時會覆寫**：已綁定 Google 的會員，若再用「不同 `sub`、相同 email」登入，回 200 且 `socialLogin.provider_id` 被覆寫成新的 `sub`；現在以 email 為身分依據、不比對 `sub`。`tests/test_google_login.py:246` 的 `test_google_rebind_different_sub_same_email_current_behavior` 釘住現行行為，P7 接真 Google 前要決定是否改成 `sub` 不符就拒絕（進度帳 Task 10 Ruling）。
- **【測試缺口】伺服器簽、伺服器驗的驗證碼沒有自動化測試**：我 grep 了 `tests/` 與 `e2e/`：`tests/test_member_auth.py:702` 的 `test_captcha_cookie_is_not_plaintext` 只檢查 `GET /captcha` 回的 cookie **格式**（`\d+\.[0-9a-f]{64}`），沒有拿它去打 `/resetpw`；其餘打 `/resetpw` 的測試與 E2E（`e2e/test_member_flow.py:161-168`）都是用測試端 `captcha_cookie()` 自己算 HMAC 再注入。所以「伺服器簽出的 cookie 能被伺服器驗過」這條完整路徑**沒有任何自動化測試**（進度帳 Task 5 minor 原記「E2E 補」，實際沒有補到）。
- **【測試缺口】`CAPTCHA_SECRET` 的 fail closed 沒有自動化測試**：只在容器內手動執行 `CAPTCHA_SECRET= node -e "...signCaptcha('abcde')..."` 驗證丟出「CAPTCHA_SECRET 未設定」（Task 5 fix report）。
- **PATCH `/info` 部分更新（2 個 strict xfail）**：只給 `name` → `middlewares/userProfile/index.js` 的 `preference.map` 對 `undefined` 丟 TypeError → 500；只給 `preference` → 中介層通過，`controllers/userProfile.js` 一律 `UPDATE name = $1` 帶入 `undefined` → `null value in column "name" violates not-null` → 500。validator 允許二擇一，中介層與 controller 卻假設兩者都有。UI 碰不到；`tests/test_member_auth.py::test_patch_profile_info_name_only`、`::test_patch_profile_info_preference_only`；留到 P3（Ruling 8）。進度帳另記：xfail 可加 `raises=AssertionError`。
- **`collection` 雙重回應，目前用 `Connection: close` 隔離**：`GET /api/v1/user/collection/info/all` 每次送兩次回應（`docs/reports/phase-1.md:323` 已知 bug），第二次寫入觸發 `ERR_HTTP_HEADERS_SENT`、socket destroy，keep-alive 重用連線時約 1% 機率讓下一個請求 `ConnectionError`；`test_favorite_list` 加 `Connection: close` 隔離。**此 workaround 待 bug 修好後移除**（Ruling 18）。
- **`.env.production` 缺 `VITE_Redirect_BASE`**：`frontend/.env.production` 只有 `VITE_BASE_URL` 與 `VITE_GOOGLE_CLIENT_ID`（P7）。另外 `.env.example` 公開預設 secret（`JWT_SECRET`、`CAPTCHA_SECRET` 等）要在 P7 部署前檢查。
- **S2 改了行為**：已有頭像的使用者，Google 登入**不再同步** Google 的新頭像（§1.22 k；`COALESCE(avatar_url, $1)`）。要「同步 Google 頭像」的需求若將來出現，要另外設計（例如只在頭像是 Google 來源時同步）。

#### B.2 其他後端、安全項目

- `COOKIE_SAMESITE` 未驗證值（接受任意字串）。
- 驗證碼 cookie 5 分鐘內可重放（P2 spec §3.2 允許）。
- 沒有密碼的帳號，`pwv` 指紋是全站共用常數（依 spec §2.3「NULL 也有固定指紋」，不回 NULL）。
- 進度帳 Task 4 minor 記「`login_token` 預設 30d 與 `JWT_EXPIRES_DAY` 略異」：`.env.example` 的 `JWT_EXPIRES_DAY=30d`，而程式的缺省值是 `|| '7d'`（`main:src/controllers/userinfo.js:98`；P2 後在 `src/utils/authToken.js:23`），測試端 `conftest.login_token` 預設 30 天。
- `user.role` 沒有 CHECK 約束（P3 migration）。
- 非 uuid 的 `id` 簽出的 token 會讓驗證查詢出 DB 錯誤（只有持有 secret 者能構造）；`auth.js` 與 `auth_not_mandatory.js` 的 `FailedMessageMap` 重複（Task 4 report）。
- `get_tourSearch` 的 404 檢查整段刪除（Ruling 4）：管理者商品列表空結果回 200。
- 後端 `level` undefined 無防呆、controller 的 pool／client 混用（登入交易 BEGIN 在 client、查詢在 pool）；併發測試無法區分 409 是 middleware 還是 DB 擋的（Task 2 minor）。
- `ROLLBACK` 丟錯時請求懸掛（P3，Task 3 minor）。
- 同一個 Google 新會員併發註冊已改回 409，但 `socialLogin` 的併發測試可再加一列（Task 10 minor）。
- 契約 `docs/db-contract.md` 內其他檔案的行號仍可能過期（建議改用函式名）；§3 的 `userinfo.js` 行號已於 `e7f20fe`、`b8141d4` 校正（Task 10 report）。

#### B.3 前端

- `Swal.close()` 在 3 秒內可能關掉別的彈窗（P3：改 timer＋then）；`Header` 用 `import router` 可改 `useRouter`；`HeaderReal.vue` 看起來未被使用、與 `HeaderComponent` 重複。
- 首頁出現兩個 header（既有，P3）；搜尋頁外部圖片連不上導致 `load` 事件逾時；手機選單 visible 判定。
- 401 之後登入頁仍跳後端錯誤 Swal（P3 統一「登入已過期」）；網路錯誤靜默導登入頁無提示。
- 會員中心：圖示缺 `aria-label`；前端無檔案預檢、上傳成功無提示；頭像 `img` 無鍵盤操作；`uploads/` 測試圖未清（既有）。
- 重設密碼頁：點圖換驗證碼 handler 未掛上、過期 token 仍顯示表單到送出才報錯、`mounted` 在檢查 token 前就呼叫 `get_user_captcha`、`HeaderComponent` 顯示寫死的「嗨！阿蘇」。
- 真 Google 的額外參數殘留網址；`?error=access_denied` 回跳時登入頁不顯示取消授權提示；失敗提示為 AxiosError 字串（既有）。
- `api.js` 其他 `error.response.data` 寫法（原 `:41`、`:92`、`:165`、`:213`、`:238`、`:337`）未動，網路錯誤時會 TypeError（Task 7、Task 9 皆記）；`updateUserInfo` 失敗時 rethrow 造成 unhandled rejection；`loginPage` 的 `mounted` 以 `window.location.search` 讀 Google code 與 hash 路由並存。
- 非 `/admin` 以外的 `requireAuth` 失敗跳轉沒有 redirect 回原頁功能。

#### B.4 測試基礎設施

- `base_url` fixture 未被使用；`CI=false` 也算 CI；`81c94d3` 的 commit 訊息前綴（`test:` 但改的是 `scripts/ci.sh`）；CI 分支 `--with-deps` 原本首次 push 才驗證，已於綠燈 run 44323636173 實際跑到並通過（已解決，見 §3.3）。
- **P3 後續（CI）**：`requires-python` 加上 `<3.14` 上限，或升級 psycopg 到有 cp314 wheel 的版本（對應 §3.3 (a)）。
- **P3 後續（CI）**：鎖定 uv 版本，`setup-uv` 補上 `version` input（對應 §3.3 (b)）。
- `delete_user` 中途失敗留半刪狀態（需 docstring）；`conftest.py:86-88` 依 `order_id` 刪除對同會員多餘；`test_delete_user_clears_all_fk_tables` 失敗時 `finally` 內 `delete_user` 同樣失敗而殘留，可改巢狀 try。
- 測試前綴殘留會讓 seed 筆數斷言持續紅（P3 測試基礎設施）；洩漏測試 `range(12)` 與 pool max 耦合。
- mutation (e) 預期文字對齊、各組無 diff；bogus code 範圍筆數比對。
- 總覽 repo 沒有 Task 4 的綠燈 commit（`conftest.py` 隨紅燈 commit，Task 4 report）。
- Mailpit helper 在 E2E 內重複。`checkout` 的大小寫測試 P4 搬到結帳測試檔。
- 紅燈 evidence 曾含截斷 JWT（Task 3；之後用 `--tb=short`）；`non_string input` 測試只斷言 400；`test_admin_product_empty_result` 的空結果斷言可收緊為 `"data" not in`、`resStatus` 對空結果沒有 `data` 欄位（P3 前端留意）。
- carol 優惠卷測試（`tests/test_api_smoke.py:292`）的 `pytest.skip` reason 字串過長。
- `.env` 與 `.env.example` 無同步檢查機制；其他開發機的本機 `.env` 需手動補 `CAPTCHA_SECRET` 等（§4.5）。

#### B.5 P1 遺留、本階段沒有處理（重申，P2 spec §6.4）

- **`R__views_functions.sql` 的 DROP 清單寫死**：簽章若日後改變，要同時保留舊簽章的 `DROP` 行；DROP 用 `CASCADE`；P7 若用原專案 DB 當基礎，手工建立的同名物件這支檔不會清掉（`docs/reports/phase-1.md` 附錄 B）。**本階段沒有改過 `migrations/R__views_functions.sql`**（`git -C backend diff --stat main..phase-2` 沒有此檔）。
- **`tests/db_contract.py` 與 `docs/db-contract.md` 沒有自動比對**：**本階段沒有改過 `tests/db_contract.py`**（`git diff --stat main..phase-2` 沒有此檔）；改 view／function 時要同步兩邊。
- 其他 P1 已知限制（IDOR 於 P5、`IMAGE_BASE` 於 P7、優惠卷金額運算於 P4）不在 P2 範圍，見 `docs/reports/phase-1.md` 附錄 B。（其餘 `pool.connect` 洩漏不是 P1 遺留，是 P2 Task 3 才發現的，列在 B.1。）
- 契約 §4.2 (b)（權限提升）已修，加註見 overview `84189ac`。

**P0／P1 遺留**：`provider_token VARCHAR(255)` 已於 P2 以「寫 NULL」解決（§1.4）；其餘見 `docs/reports/phase-0.md` 附錄與 `docs/reports/phase-1.md` 附錄 B。
