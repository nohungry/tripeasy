# Task 7 spike：mock-oauth2-server 能否替代 Google

## 結果：B（可行，但有已知的 schema 限制）

- `test_mock_oauth_issues_google_like_claims`：PASS。mock 發出的 userinfo 含 sub=`mock-google-001`、email=`mock.user@example.com`、name=`Mock 使用者`。
- backend 的 token / userinfo 網址改為讀 `GOOGLE_TOKEN_URL` / `GOOGLE_USERINFO_URL`（預設仍是 Google）後，
  backend 在容器內用 `mock-oauth:8080` 換 token、取 userinfo 都成功（沒有 issuer 不符或 401 問題；
  由 401 變成 500 即代表已通過 token 交換與 userinfo）。
- `test_backend_google_login_via_mock`：改前 401（backend 仍打真的 Google），改後 500。log：

```
❌ 系統錯誤: error: value too long for type character varying(255)
    at async post_user_LoginGoogle (/usr/backend/src/controllers/userinfo.js:192:7)
  code: '22001', file: 'varchar.c'
```

原因：mock 的 access token 是 JWT，超過 `socialLogin.provider_token` 的 VARCHAR(255)。
Google 真實的 access token 較短，所以線上沒問題。

## 對 P2 的影響

- P0 不改 schema；該測試以 `xfail(strict=True)` 標記。
- P2 需要 migration 把 `socialLogin.provider_token` 放寬（例如 TEXT），然後移除 xfail。
  strict=True 會在修好之後（XPASS）讓測試失敗，提醒移除標記。
- 修好之後，Google 登入流程就能完全在本機用 mock 跑通，不需要真的 Google client。
