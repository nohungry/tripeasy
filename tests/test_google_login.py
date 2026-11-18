"""P2 Google 登入：信箱驗證、大小寫、首次綁定清密碼、不再使用共用密碼。"""
import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest

from conftest import TEST_PASSWORD, captcha_cookie, delete_user, mock_google_code, reset_token

GOOGLE = "/api/v1/auth/userinfo/login/google"
LOGIN = "/api/v1/auth/userinfo/login/email"
SIGNUP = "/api/v1/auth/userinfo/signup"
INFO = "/api/v1/user/userinfo/info"
RESETPW = "/api/v1/auth/userinfo/resetpw"
PREFS = ["探索冒險", "放鬆療癒", "文化體驗"]
NULL_PW_LOGIN_MSG = "此帳號使用 Google 登入，請改用 Google 登入，或透過忘記密碼設定密碼。"
UNVERIFIED_MSG = "Google 帳號的信箱尚未驗證，無法登入。"
MISSING = object()  # email_verified 欄位不存在
BAD_VERIFIED = [False, MISSING, "true", 1]
BAD_VERIFIED_IDS = ["false", "missing", "string-true", "int-1"]
# 舊版 Google 新會員共用的密碼（本機 .env.example 的值、程式內預設值）；兩者都通不過 passwordPattern
OLD_SHARED_PASSWORDS = ("local-oauth-default-pw", "DefaultPassword123!")


@pytest.fixture
def google(api, db):
    """回傳 (new_claims, login)：產生不重複的 claims；login(claims) 取碼並打 /login/google。結束時刪除相關會員。"""
    emails: list[str] = []
    subs: list[str] = []

    def new_claims(**override) -> dict:
        tag = uuid.uuid4().hex[:8]
        claims = {
            "sub": f"g-{tag}",
            "email": f"g.{tag}@example.com",
            "email_verified": True,
            "name": "Google 測試員",
            "picture": "https://example.com/g.png",
            **override,
        }
        if claims["email_verified"] is MISSING:
            del claims["email_verified"]
        emails.append(claims["email"])
        subs.append(claims["sub"])
        return claims

    def login(claims: dict):
        return api.post(GOOGLE, json={"code": mock_google_code(claims)})

    yield new_claims, login
    for email in emails:
        for (user_id,) in db.execute('SELECT user_id FROM "user" WHERE lower(email) = lower(%s)', (email,)).fetchall():
            delete_user(db, str(user_id))
    for sub in subs:
        for (user_id,) in db.execute('SELECT user_id FROM "socialLogin" WHERE provider_id = %s', (sub,)).fetchall():
            delete_user(db, str(user_id))


def _user_row(db, email: str):
    return db.execute(
        'SELECT user_id, password, login_method, role FROM "user" WHERE lower(email) = lower(%s)', (email,)
    ).fetchall()


def test_google_new_user_has_null_password(api, db, google):
    new_claims, login = google
    claims = new_claims()
    r = login(claims)
    assert r.status_code == 200, r.text
    ((user_id, password, login_method, role),) = _user_row(db, claims["email"])
    assert password is None
    assert login_method == 2
    assert role == "User"
    assert db.execute(
        'SELECT provider_method, provider_id, provider_token FROM "socialLogin" WHERE user_id = %s', (user_id,)
    ).fetchall() == [("google", claims["sub"], None)]


@pytest.mark.parametrize("verified", BAD_VERIFIED, ids=BAD_VERIFIED_IDS)
def test_google_unverified_email_rejected(api, db, google, verified):
    new_claims, login = google
    claims = new_claims(email_verified=verified)
    r = login(claims)
    assert r.status_code == 400, r.text
    assert r.json()["message"] == UNVERIFIED_MSG
    assert _user_row(db, claims["email"]) == []
    assert db.execute('SELECT count(*) FROM "socialLogin" WHERE provider_id = %s', (claims["sub"],)).fetchone()[0] == 0


@pytest.mark.parametrize("verified", BAD_VERIFIED, ids=BAD_VERIFIED_IDS)
def test_google_unverified_email_cannot_bind_existing(api, db, google, make_user, verified):
    new_claims, login = google
    user = make_user()
    before = _user_row(db, user["email"])
    claims = new_claims(email=user["email"], email_verified=verified)
    r = login(claims)
    assert r.status_code == 400, r.text
    assert r.json()["message"] == UNVERIFIED_MSG
    assert _user_row(db, user["email"]) == before  # password 沒變
    assert db.execute('SELECT count(*) FROM "socialLogin" WHERE user_id = %s', (user["user_id"],)).fetchone()[0] == 0
    r = api.post(LOGIN, json={"email": user["email"], "password": TEST_PASSWORD})
    assert r.status_code == 200, r.text


def test_google_email_case_matches_existing(api, db, google, make_user):
    new_claims, login = google
    user = make_user(email=f"a.{uuid.uuid4().hex[:8]}@example.com")
    claims = new_claims(email=user["email"].upper())
    r = login(claims)
    assert r.status_code == 200, r.text
    rows = _user_row(db, user["email"])
    assert [str(row[0]) for row in rows] == [user["user_id"]]
    assert db.execute(
        'SELECT provider_method, provider_id, provider_token FROM "socialLogin" WHERE user_id = %s', (user["user_id"],)
    ).fetchall() == [("google", claims["sub"], None)]


def test_google_binds_existing_mixed_case_stored_email(api, db, google, make_user):
    """DB 存混合大小寫 email 的既有會員（舊資料或其他寫入點可能留下），Google 以全小寫 email 登入要綁到同一位。"""
    new_claims, login = google
    tag = uuid.uuid4().hex[:8]
    user = make_user(email=f"A.{tag}@Example.COM")
    claims = new_claims(email=f"a.{tag}@example.com")
    r = login(claims)
    assert r.status_code == 200, r.text
    rows = _user_row(db, claims["email"])
    assert [str(row[0]) for row in rows] == [user["user_id"]]
    assert db.execute(
        'SELECT provider_method, provider_id, provider_token FROM "socialLogin" WHERE user_id = %s', (user["user_id"],)
    ).fetchall() == [("google", claims["sub"], None)]


def test_google_first_bind_clears_password_and_old_tokens(api, db, google):
    """預先劫持：攻擊者先用受害者 email 註冊並拿到 token，受害者首次 Google 登入後都要失效。"""
    new_claims, login = google
    claims = new_claims()
    r = api.post(
        SIGNUP,
        json={"name": "攻擊者", "email": claims["email"], "password": TEST_PASSWORD, "preference": PREFS},
    )
    assert r.status_code == 201, r.text
    r = api.post(LOGIN, json={"email": claims["email"], "password": TEST_PASSWORD})
    assert r.status_code == 200, r.text
    old_token = r.json()["data"]["token"]
    assert api.get(INFO, headers={"Authorization": f"Bearer {old_token}"}).status_code == 200

    r = login(claims)
    assert r.status_code == 200, r.text
    new_token = r.json()["data"]["token"]

    r = api.post(LOGIN, json={"email": claims["email"], "password": TEST_PASSWORD})
    assert r.status_code == 401, r.text
    assert r.json()["message"] == NULL_PW_LOGIN_MSG
    assert api.get(INFO, headers={"Authorization": f"Bearer {old_token}"}).status_code == 401
    ((user_id, password, _, _),) = _user_row(db, claims["email"])
    assert password is None
    # 受害者 Google 登入拿到的新 token 要能用（pwv 以更新後的 password 計算）
    assert api.get(INFO, headers={"Authorization": f"Bearer {new_token}"}).status_code == 200
    assert db.execute(
        'SELECT provider_method, provider_id, provider_token FROM "socialLogin" WHERE user_id = %s', (user_id,)
    ).fetchall() == [("google", claims["sub"], None)]


def test_google_member_cannot_login_with_default_password(api, db, google):
    """舊版 Google 新會員共用密碼。共用密碼通不過 passwordPattern（Email 登入先 400），
    所以證明靠：DB password 為 NULL，且任何格式正確的密碼都得到 NULL 密碼訊息。"""
    new_claims, login = google
    claims = new_claims()
    assert login(claims).status_code == 200
    ((_, password, _, _),) = _user_row(db, claims["email"])
    assert password is None
    for pw in ("Wrongpass123", "Default12345"):
        r = api.post(LOGIN, json={"email": claims["email"], "password": pw})
        assert r.status_code == 401, r.text
        assert r.json()["message"] == NULL_PW_LOGIN_MSG
    for pw in OLD_SHARED_PASSWORDS:
        r = api.post(LOGIN, json={"email": claims["email"], "password": pw})
        assert r.status_code == 400, r.text


def test_google_rebind_keeps_password(api, db, google):
    new_claims, login = google
    claims = new_claims()
    assert login(claims).status_code == 200
    ((user_id, _, _, role),) = _user_row(db, claims["email"])
    new_pw = "Newpass12345"
    r = api.patch(
        RESETPW,
        json={
            "token": reset_token({"user_id": str(user_id), "role": role}),
            "new_password": new_pw,
            "confirm_password": new_pw,
            "input": "abcde",
        },
        cookies={"captcha": captcha_cookie("abcde")},
    )
    assert r.status_code == 200, r.text

    assert login(claims).status_code == 200

    r = api.post(LOGIN, json={"email": claims["email"], "password": new_pw})
    assert r.status_code == 200, r.text


def test_google_login_response_token_works(api, google):
    new_claims, login = google
    r = login(new_claims())
    assert r.status_code == 200, r.text
    token = r.json()["data"]["token"]
    assert api.get(INFO, headers={"Authorization": f"Bearer {token}"}).status_code == 200


def test_google_login_missing_code_is_400(api):
    r = api.post(GOOGLE, json={})
    assert r.status_code == 400, r.text
    assert r.json()["message"] == "Code 欄位未填寫正確"


def test_google_login_bogus_code_rejected(api, db):
    """驗證 code 是 Google 的責任；mock-oauth2-server 對任何 code 都會簽 token（含亂填、重複使用），
    所以這一層測不到「code 無效」。此測試實際驗的是：userinfo 沒有 email 時後端拒絕（400），
    而且不會建立會員或 socialLogin。mock 對亂填 code 簽出的 sub 是隨機 UUID，這裡改查 mock 的固定 email
    與 sub 以 mock- 開頭的 socialLogin（只看與本次相關的資料，不比對整張表筆數）。"""
    social_sql = "SELECT count(*) FROM \"socialLogin\" WHERE provider_id LIKE 'mock-%%' OR provider_id ~ '^[0-9a-f-]{36}$'"
    social_before = db.execute(social_sql).fetchone()[0]

    r = api.post(GOOGLE, json={"code": "bogus"})

    assert r.status_code == 400, r.text
    assert r.json()["message"] == "Google 帳號資訊異常，無法取得 email"
    assert db.execute('SELECT count(*) FROM "user" WHERE lower(email) = %s', ("mock.user@example.com",)).fetchone()[0] == 0
    assert db.execute(social_sql).fetchone()[0] == social_before


def test_google_new_user_email_stored_lowercase(api, db, google):
    new_claims, login = google
    claims = new_claims()
    claims["email"] = claims["email"].upper()
    assert login(claims).status_code == 200
    ((stored,),) = db.execute(
        'SELECT u.email FROM "user" u JOIN "socialLogin" s ON s.user_id = u.user_id WHERE s.provider_id = %s',
        (claims["sub"],),
    ).fetchall()
    assert stored == claims["email"].lower()


def test_google_rebind_different_sub_same_email_current_behavior(api, db, google):
    """釘住現行行為：已綁定的會員用不同 sub、相同 email 再登入，回 200 且 provider_id 被覆寫。
    已知限制：現在以 email 為身分依據，不比對 sub；P7 接真 Google 前要再決定是否改成 sub 不符就拒絕。"""
    new_claims, login = google
    claims = new_claims()
    assert login(claims).status_code == 200
    other = {**claims, "sub": claims["sub"] + "-other"}
    assert login(other).status_code == 200
    ((user_id,),) = db.execute('SELECT user_id FROM "user" WHERE email = %s', (claims["email"],)).fetchall()
    assert db.execute(
        'SELECT provider_id FROM "socialLogin" WHERE user_id = %s', (user_id,)
    ).fetchall() == [(other["sub"],)]


def test_google_new_user_concurrent_same_email_not_500(api, db, google):
    """同一個 email 同時 Google 首次登入：不可回 500（撞 user_email_lower_key 要回 409），最後只有一位會員。"""
    new_claims, _ = google
    claims = new_claims()
    codes = [mock_google_code({**claims, "sub": f"{claims['sub']}-{i}"}) for i in range(6)]
    with ThreadPoolExecutor(max_workers=6) as pool:
        statuses = list(pool.map(lambda c: api.post(GOOGLE, json={"code": c}).status_code, codes))
    assert set(statuses) <= {200, 409}, statuses
    assert 200 in statuses, statuses
    assert len(_user_row(db, claims["email"])) == 1
