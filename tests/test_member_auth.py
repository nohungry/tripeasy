"""P2 會員：權限與資料清理。後續 Task 的會員測試加在這裡。"""
import datetime
import os
import re
import time
import uuid
from concurrent.futures import ThreadPoolExecutor

import jwt
import pytest
import requests

from conftest import (
    API_BASE,
    MAILPIT_BASE,
    TEST_PASSWORD,
    USER_FK_TABLES,
    auth_header,
    captcha_cookie,
    current_pwv,
    delete_user,
    login_token,
    reset_token,
)
from dbfactory import insert

ROLES = "/api/v1/admin/members/roles"


def _role_of(db, user_id: str) -> str:
    return db.execute('SELECT role FROM "user" WHERE user_id = %s', (user_id,)).fetchone()[0]


def test_change_role_requires_admin(api, db, make_user):
    a = make_user()
    b = make_user()
    r = api.patch(ROLES, headers=auth_header(a), json={"user_ids": [b["user_id"]], "role": "admin"})
    assert r.status_code == 403, r.text
    assert _role_of(db, b["user_id"]) == "User"


def test_change_role_by_admin(api, db, make_user):
    admin = make_user(role="admin")
    b = make_user()
    r = api.patch(ROLES, headers=auth_header(admin), json={"user_ids": [b["user_id"]], "role": "admin"})
    assert r.status_code == 200, r.text
    assert _role_of(db, b["user_id"]) == "admin"


def test_user_fk_tables_list_is_complete(db):
    """Task 2 之後若有 migration 新增參照 "user" 的表，這裡會抓到 delete_user 漏掉的表。"""
    rows = db.execute(
        "SELECT DISTINCT conrelid::regclass::text FROM pg_constraint "
        "WHERE contype = 'f' AND confrelid = '\"user\"'::regclass"
    ).fetchall()
    actual = {r[0].strip('"') for r in rows}
    assert actual == {t.strip('"') for t in USER_FK_TABLES}


def test_delete_user_clears_all_fk_tables(make_user, tx):
    # 參數順序：tx 要先於 make_user 結束（rollback），make_user teardown 刪 user 才不會卡 row lock。
    # 所有 insert 都在 tx 內，失敗也由 rollback 保證不留資料。
    user = make_user()
    uid = user["user_id"]
    tour = insert(tx, "tour")
    coupon = insert(tx, "coupon")
    insert(tx, "socialLogin", user_id=uid)
    insert(tx, "user_level", user_id=uid)
    cart = insert(tx, "cart", user_id=uid)
    insert(tx, "cart_item", cart_id=cart["cart_id"], tour_id=tour["tour_id"])
    insert(tx, "favorite", user_id=uid, tour_id=tour["tour_id"])
    order = insert(tx, "orders", user_id=uid)
    insert(tx, "order_item", order_id=order["order_id"], tour_id=tour["tour_id"])
    insert(tx, "payment", user_id=uid, order_id=order["order_id"])
    insert(tx, "point_record", user_id=uid)
    insert(tx, "point_record", user_id=uid, order_id=order["order_id"])
    insert(tx, "user_coupon", user_id=uid, coupon_id=coupon["coupon_id"], order_id=order["order_id"])
    insert(tx, "review", user_id=uid, tour_id=tour["tour_id"])
    insert(tx, "hidden_play", user_id=uid, tour_id=tour["tour_id"])
    insert(tx, "auto_setting", user_id=uid)

    delete_user(tx, uid)  # 不得丟 FK 錯誤

    for table in USER_FK_TABLES:
        (n,) = tx.execute(f"SELECT count(*) FROM {table} WHERE user_id = %s", (uid,)).fetchone()
        assert n == 0, table
    (n,) = tx.execute('SELECT count(*) FROM "user" WHERE user_id = %s', (uid,)).fetchone()
    assert n == 0


SIGNUP = "/api/v1/auth/userinfo/signup"
LOGIN = "/api/v1/auth/userinfo/login/email"
FORGET = "/api/v1/auth/userinfo/forgetpw"
PREFS = ["探索冒險", "放鬆療癒", "文化體驗"]


@pytest.fixture
def cleanup_email(db):
    """收集測試註冊用的 email，結束時依 email 查 user_id 並刪除。"""
    emails: list[str] = []
    yield emails.append
    for email in emails:
        for (user_id,) in db.execute(
            'SELECT user_id FROM "user" WHERE lower(email) = lower(%s)', (email,)
        ).fetchall():
            delete_user(db, str(user_id))


def _signup_body(default_email: str, **override) -> dict:
    """override 的值為 None 代表移除該欄位。"""
    body = {"name": "測試員", "email": default_email, "password": TEST_PASSWORD, "preference": PREFS, **override}
    return {k: v for k, v in body.items() if v is not None}


def _count_email(db, email: str) -> int:
    return db.execute(
        'SELECT count(*) FROM "user" WHERE lower(email) = lower(%s)', (email,)
    ).fetchone()[0]


def test_signup_normalizes_email(api, db, cleanup_email):
    email = f"Mixed.{uuid.uuid4().hex[:8]}@Example.COM"
    cleanup_email(email)
    r = api.post(SIGNUP, json=_signup_body(email))
    assert r.status_code == 201, r.text
    rows = db.execute('SELECT email FROM "user" WHERE lower(email) = lower(%s)', (email,)).fetchall()
    assert rows == [(email.lower(),)]


def test_signup_duplicate_differs_by_case_is_409(api, db, cleanup_email):
    email = f"dup.{uuid.uuid4().hex[:8]}@example.com"
    cleanup_email(email)
    assert api.post(SIGNUP, json=_signup_body(email)).status_code == 201
    r = api.post(SIGNUP, json=_signup_body(email.upper()))
    assert r.status_code == 409, r.text
    assert r.json()["message"] == "Email已被使用"
    assert _count_email(db, email) == 1


def test_signup_concurrent_same_email_only_one_succeeds(api, db, cleanup_email):
    email = f"race.{uuid.uuid4().hex[:8]}@example.com"
    cleanup_email(email)
    with ThreadPoolExecutor(max_workers=5) as pool:
        codes = list(pool.map(lambda _: api.post(SIGNUP, json=_signup_body(email)).status_code, range(5)))
    assert sorted(codes) == [201, 409, 409, 409, 409], codes
    assert _count_email(db, email) == 1


def test_login_email_is_case_insensitive(api, make_user):
    user = make_user(email=f"lower.{uuid.uuid4().hex[:8]}@example.com")
    r = api.post(LOGIN, json={"email": user["email"].upper(), "password": TEST_PASSWORD})
    assert r.status_code == 200, r.text


def test_login_lowercase_matches_mixed_case_stored_email(api, make_user):
    user = make_user(email=f"Mixed.{uuid.uuid4().hex[:8]}@Example.COM")
    r = api.post(LOGIN, json={"email": user["email"].lower(), "password": TEST_PASSWORD})
    assert r.status_code == 200, r.text
    assert r.json()["data"]["user"]["id"] == user["user_id"]


def test_forgetpw_matches_mixed_case_stored_email(api, make_user):
    user = make_user(email=f"Mixed.{uuid.uuid4().hex[:8]}@Example.COM")
    r = api.post(FORGET, json={"email": user["email"].lower()})
    assert r.status_code == 200, r.text


def test_signup_lowercase_conflicts_with_mixed_case_stored_email(api, make_user):
    user = make_user(email=f"Mixed.{uuid.uuid4().hex[:8]}@Example.COM")
    r = api.post(SIGNUP, json=_signup_body(user["email"].lower()))
    assert r.status_code == 409, r.text
    assert r.json()["message"] == "Email已被使用"


# 以下為既有行為的回歸測試，一開始就綠。
@pytest.mark.parametrize(
    "override, message",
    [
        ({"email": "not-an-email"}, "Email不符合規則"),
        ({"password": "short"}, "密碼不符合規則"),
        ({"name": "六個字的名字喔"}, "使用者名稱不符合規則"),
        ({"preference": PREFS[:2]}, "個人偏好需選擇 3 項內容"),
        ({"password": None}, "「密碼」為必填欄位"),
    ],
    ids=["bad-email", "bad-password", "name-too-long", "preference-too-few", "missing-password"],
)
def test_signup_validation_errors(api, db, cleanup_email, override, message):
    email = f"val.{uuid.uuid4().hex[:8]}@example.com"
    cleanup_email(email)
    r = api.post(SIGNUP, json=_signup_body(email, **override))
    assert r.status_code == 400, r.text
    assert message in r.json()["message"]
    assert _count_email(db, email) == 0
    if "email" in override:
        assert _count_email(db, override["email"]) == 0


def test_signup_unknown_preference_is_409(api, db, cleanup_email):
    email = f"pref.{uuid.uuid4().hex[:8]}@example.com"
    cleanup_email(email)
    r = api.post(SIGNUP, json=_signup_body(email, preference=["探索冒險", "放鬆療癒", "不存在的偏好"]))
    assert r.status_code == 409, r.text
    assert r.json()["message"] == "包含無效的偏好名稱"
    assert _count_email(db, email) == 0


@pytest.mark.parametrize(
    "body",
    [{"email": "not-an-email", "password": TEST_PASSWORD}, {"email": "a@example.com"}],
    ids=["bad-email", "missing-password"],
)
def test_login_email_validation_errors(api, body):
    assert api.post(LOGIN, json=body).status_code == 400


def test_login_unknown_email_is_404(api):
    r = api.post(LOGIN, json={"email": f"nobody.{uuid.uuid4().hex[:8]}@example.com", "password": TEST_PASSWORD})
    assert r.status_code == 404, r.text


def test_login_wrong_password_is_401(api, make_user):
    user = make_user()
    r = api.post(LOGIN, json={"email": user["email"], "password": "Wrongpass123"})
    assert r.status_code == 401, r.text
    assert "(已錯誤 1 次)" in r.json()["message"]


def test_forgetpw_validation_and_unknown_email(api):
    assert api.post(FORGET, json={"email": "not-an-email"}).status_code == 400
    r = api.post(FORGET, json={"email": f"nobody.{uuid.uuid4().hex[:8]}@example.com"})
    assert r.status_code == 404, r.text


def test_checkout_preview_email_lookup_is_case_insensitive(api, make_user):
    """結帳預覽以 body 的 email 查會員；大寫 email 不得回「查無此使用者」（用不存在的 order_id，預期走到「查無此訂單項目」）。"""
    user = make_user(email=f"co.{uuid.uuid4().hex[:8]}@example.com")
    body = {
        "user": {"name": "測試員", "email": user["email"].upper(), "address": "台北市", "phone_number": "0912345678"},
        "payment_method": "atm",
        "discount": {},
    }
    r = api.patch(
        f"/api/v1/user/checkout/preview/{uuid.uuid4()}", headers=auth_header(user), json=body
    )
    assert r.status_code == 404, r.text
    assert r.json()["message"] == "查無此訂單項目"


# ---- Task 3：沒有密碼的帳號、登入回應頭像 ----

LOGIN = "/api/v1/auth/userinfo/login/email"
LOGIN_STATUS = "/api/v1/auth/userinfo/login/status"
PROFILE_INFO = "/api/v1/user/userinfo/info"
PROFILE_AVATAR = "/api/v1/user/userinfo/avatar"
PROFILE_POINTS = "/api/v1/user/userinfo/pointslevel"
PROFILE_RESET_PW = "/api/v1/auth/userinfo/resetprofilepw"

NULL_PW_LOGIN_MSG = "此帳號使用 Google 登入，請改用 Google 登入，或透過忘記密碼設定密碼。"
NULL_PW_PROFILE_MSG = "此帳號尚未設定密碼，請透過忘記密碼設定。"


def test_login_null_password_is_rejected_without_lock(api, db, make_user):
    user = make_user(password=None)
    for _ in range(4):
        r = api.post(LOGIN, json={"email": user["email"], "password": "Wrongpass123"})
        assert r.status_code == 401, r.text
        assert r.json()["message"] == NULL_PW_LOGIN_MSG
    attempts, locked = db.execute(
        'SELECT login_attempts, locked_datetime FROM "user" WHERE user_id = %s', (user["user_id"],)
    ).fetchone()
    assert not attempts
    assert locked is None


def test_profile_change_password_null_password(api, make_user):
    user = make_user(password=None)
    r = api.patch(
        PROFILE_RESET_PW,
        headers=auth_header(user),
        json={"password": "Wrongpass123", "new_password": "Newpass12345", "confirm_password": "Newpass12345"},
    )
    assert r.status_code == 400, r.text
    assert r.json()["message"] == NULL_PW_PROFILE_MSG


# 既有行為的回歸測試（P2 spec §5）：一開始就綠。
@pytest.mark.parametrize(
    "method, path",
    [
        ("GET", PROFILE_INFO),
        ("PATCH", PROFILE_INFO),
        ("PATCH", PROFILE_AVATAR),
        ("GET", PROFILE_POINTS),
        ("PATCH", PROFILE_RESET_PW),
        ("GET", LOGIN_STATUS),
    ],
)
def test_member_apis_require_login(api, method, path):
    r = api.request(method, path)
    assert r.status_code == 401, r.text


@pytest.mark.parametrize(
    "method, path",
    [("GET", PROFILE_INFO), ("PATCH", PROFILE_INFO), ("PATCH", PROFILE_AVATAR), ("GET", PROFILE_POINTS)],
)
def test_user_only_apis_reject_admin_role(api, make_user, method, path):
    admin = make_user(role="admin")
    r = api.request(method, path, headers=auth_header(admin))
    assert r.status_code == 403, r.text


def test_get_profile_info_ok(api, db, make_user):
    user = make_user()
    r = api.get(PROFILE_INFO, headers=auth_header(user))
    assert r.status_code == 200, r.text
    got = r.json()["data"]["user"]
    (db_name,) = db.execute('SELECT name FROM "user" WHERE user_id = %s', (user["user_id"],)).fetchone()
    assert got["name"] == db_name
    assert got["email"] == user["email"]


def test_patch_profile_info_ok_and_validation(api, db, make_user):
    user = make_user()
    h = auth_header(user)
    prefs = ["探索冒險", "放鬆療癒", "文化體驗"]

    r = api.patch(PROFILE_INFO, headers=h, json={"name": "新名字", "preference": ["美食探索", "都市感官", "自然療癒"]})
    assert r.status_code == 200, r.text
    got = r.json()["data"]["user"]
    assert got["name"] == "新名字"
    assert got["preferences"] == ["美食探索", "都市感官", "自然療癒"]

    def _stored():
        row = db.execute(
            'SELECT name, preference1, preference2, preference3 FROM "user" WHERE user_id = %s', (user["user_id"],)
        ).fetchone()
        return tuple(row)

    assert _stored() == ("新名字", 4, 5, 6)

    r = api.patch(PROFILE_INFO, headers=h, json={})
    assert r.status_code == 400 and "請至少填寫" in r.json()["message"], r.text
    r = api.patch(PROFILE_INFO, headers=h, json={"name": "a!b", "preference": prefs})
    assert r.status_code == 400 and "特殊字元" in r.json()["message"], r.text
    r = api.patch(PROFILE_INFO, headers=h, json={"name": "新名字", "preference": prefs[:2]})
    assert r.status_code == 400 and "需包含 3 個項目" in r.json()["message"], r.text
    r = api.patch(PROFILE_INFO, headers=h, json={"name": "新名字", "preference": ["探索冒險", "放鬆療癒", "不存在"]})
    assert r.status_code == 409 and "包含無效的偏好名稱" in r.json()["message"], r.text
    # 被拒絕的請求不得改到資料
    assert _stored() == ("新名字", 4, 5, 6)


def test_avatar_upload_validation(api, make_user):
    h = auth_header(make_user())
    r = api.patch(PROFILE_AVATAR, headers=h, files={"image": ("a.txt", b"hello", "text/plain")})
    assert r.status_code == 400 and "只允許上傳圖片格式" in r.json()["message"], r.text
    r = api.patch(PROFILE_AVATAR, headers=h)
    assert r.status_code == 400 and "請提供圖片" in r.json()["message"], r.text
    big = b"\x89PNG\r\n\x1a\n" + b"0" * (2 * 1024 * 1024 + 1)
    r = api.patch(PROFILE_AVATAR, headers=h, files={"image": ("big.png", big, "image/png")})
    assert r.status_code == 400 and "圖片太大，請小於 2MB" in r.json()["message"], r.text


def test_profile_change_password_validation(api, make_user):
    user = make_user()
    h = auth_header(user)
    new = "Newpass12345"

    r = api.patch(PROFILE_RESET_PW, headers=h, json={"password": "Wrongpass123", "new_password": new, "confirm_password": new})
    assert r.status_code == 400 and "舊密碼輸入錯誤" in r.json()["message"], r.text
    r = api.patch(PROFILE_RESET_PW, headers=h, json={"password": TEST_PASSWORD, "new_password": TEST_PASSWORD, "confirm_password": TEST_PASSWORD})
    assert r.status_code == 400 and "新密碼與舊密碼相同" in r.json()["message"], r.text
    r = api.patch(PROFILE_RESET_PW, headers=h, json={"password": TEST_PASSWORD, "new_password": new, "confirm_password": "Other12345"})
    assert r.status_code == 400 and "新密碼與驗證密碼不一致" in r.json()["message"], r.text
    # 三個都被拒：原密碼仍能登入，新密碼不能
    r = api.post(LOGIN, json={"email": user["email"], "password": TEST_PASSWORD})
    assert r.status_code == 200, r.text
    r = api.post(LOGIN, json={"email": user["email"], "password": new})
    assert r.status_code == 401, r.text


def test_login_response_has_avatar_url(api, db, make_user):
    user = make_user()
    url = "https://example.com/a.png"
    db.execute('UPDATE "user" SET avatar_url = %s WHERE user_id = %s', (url, user["user_id"]))

    r = api.post(LOGIN, json={"email": user["email"], "password": TEST_PASSWORD})
    assert r.status_code == 200, r.text
    assert r.json()["data"]["user"]["avatar_url"] == url

    r = api.get(LOGIN_STATUS, headers=auth_header(user))
    assert r.status_code == 200, r.text
    assert r.json()["data"]["user"]["avatar_url"] == url


def test_patch_profile_info_name_only(api, db, make_user):
    user = make_user()
    r = api.patch(PROFILE_INFO, headers=auth_header(user), json={"name": "新名字"})
    assert r.status_code == 200, r.text
    (name,) = db.execute('SELECT name FROM "user" WHERE user_id = %s', (user["user_id"],)).fetchone()
    assert name == "新名字"
    prefs = db.execute(
        'SELECT preference1, preference2, preference3 FROM "user" WHERE user_id = %s', (user["user_id"],)
    ).fetchone()
    assert tuple(prefs) == (1, 2, 3)


def test_patch_profile_info_preference_only(api, db, make_user):
    user = make_user()
    (before,) = db.execute('SELECT name FROM "user" WHERE user_id = %s', (user["user_id"],)).fetchone()
    r = api.patch(PROFILE_INFO, headers=auth_header(user), json={"preference": ["美食探索", "都市感官", "自然療癒"]})
    assert r.status_code == 200, r.text
    (after,) = db.execute('SELECT name FROM "user" WHERE user_id = %s', (user["user_id"],)).fetchone()
    assert after == before


def test_patch_profile_info_releases_db_connection(api, make_user):
    """PATCH /info 每次都要把 DB 連線還給 pool（pool 預設 max 10），否則之後的請求會卡住。"""
    user = make_user()
    h = auth_header(user)
    prefs = ["探索冒險", "放鬆療癒", "文化體驗"]
    for i in range(12):  # pool max 10 + 2
        r = api.patch(PROFILE_INFO, headers=h, json={"name": "連線測試", "preference": prefs}, timeout=5)
        assert r.status_code == 200, f"第 {i + 1} 次：{r.text}"
    r = api.get(PROFILE_INFO, headers=h, timeout=5)
    assert r.status_code == 200, r.text


# ---------------------------------------------------------------------------
# Task 4：token 用途分離與密碼指紋（P2 spec §3.1、§3.1a）
# ---------------------------------------------------------------------------
FRONTEND_PATH = os.getenv("FRONTEND_PATH", "http://localhost:5173")
RESETPW = "/api/v1/auth/userinfo/resetpw"
NEW_PW = "Newpass12345"
TOKEN_ERR_MSG = "Token 資料錯誤、無效或過期"
HOME_PRODUCTS = "/api/v1/user/home/search/products"  # 只掛 auth_not_mandatory


def _reset_link(email: str) -> str:
    """打 forgetpw、等 Mailpit 收信，回傳信中的重設連結。"""
    r = requests.post(f"{API_BASE}{FORGET}", json={"email": email}, timeout=10)
    assert r.status_code == 200, r.text
    deadline = time.time() + 10
    messages = []
    while time.time() < deadline:
        messages = requests.get(
            f"{MAILPIT_BASE}/api/v1/search", params={"query": f"to:{email}"}, timeout=10
        ).json()["messages"]
        if messages:
            break
        time.sleep(0.5)
    assert messages, "沒有收到重設信"
    html = requests.get(f"{MAILPIT_BASE}/api/v1/message/{messages[0]['ID']}", timeout=10).json()["HTML"]
    match = re.search(r'href="([^"]*resetpw\?token=[^"]+)"', html)
    assert match, html
    return match.group(1)


def _token_of(link: str) -> str:
    return link.split("resetpw?token=", 1)[1]


def _resetpw(api, token: str, new_password: str = NEW_PW, **override):
    body = {
        "token": token,
        "new_password": new_password,
        "confirm_password": new_password,
        "input": "abcde",
        **override,
    }
    return api.patch(RESETPW, json=body, cookies={"captcha": captcha_cookie("abcde")})


def _stored_password(db, user_id: str):
    return db.execute('SELECT password FROM "user" WHERE user_id = %s', (user_id,)).fetchone()[0]


def _login_token_via_api(api, user: dict) -> str:
    r = api.post(LOGIN, json={"email": user["email"], "password": TEST_PASSWORD})
    assert r.status_code == 200, r.text
    return r.json()["data"]["token"]


def _bearer(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _info_status(api, token: str) -> int:
    """先取出狀態碼再 assert，避免失敗輸出把 JWT 印進 pytest 的斷言說明。"""
    status = api.get(PROFILE_INFO, headers=_bearer(token)).status_code
    return status


@pytest.mark.parametrize("path", [PROFILE_INFO, LOGIN_STATUS, HOME_PRODUCTS])
def test_reset_token_cannot_access_member_api(api, make_user, path):
    user = make_user()
    token = _token_of(_reset_link(user["email"]))
    r = api.get(path, headers=_bearer(token))
    assert r.status_code == 401, r.text


def test_reset_link_shape(make_user):
    user = make_user()
    link = _reset_link(user["email"])
    prefix = link.split("token=", 1)[0] + "token="  # 只比對前綴，避免失敗輸出印出 token
    assert prefix == f"{FRONTEND_PATH}/#/admin/resetpw?token="


def test_login_token_cannot_reset_password(api, db, make_user):
    user = make_user()
    before = _stored_password(db, user["user_id"])
    r = _resetpw(api, auth_header(user)["Authorization"].split(" ")[1])
    assert r.status_code == 400 and r.json()["message"] == TOKEN_ERR_MSG, r.text
    assert _stored_password(db, user["user_id"]) == before


def test_reset_password_old_password_rejected(api, make_user):
    user = make_user()
    token = _token_of(_reset_link(user["email"]))
    assert _resetpw(api, token).status_code == 200
    old = api.post(LOGIN, json={"email": user["email"], "password": TEST_PASSWORD})
    assert old.status_code == 401, old.text
    new = api.post(LOGIN, json={"email": user["email"], "password": NEW_PW})
    assert new.status_code == 200, new.text


def test_reset_token_is_single_use(api, make_user):
    user = make_user()
    token = _token_of(_reset_link(user["email"]))
    r = _resetpw(api, token)
    assert r.status_code == 200, r.text
    r = _resetpw(api, token, "Another12345")
    assert r.status_code == 400 and r.json()["message"] == TOKEN_ERR_MSG, r.text
    # 密碼仍是第一次設定的值
    r = api.post(LOGIN, json={"email": user["email"], "password": NEW_PW})
    assert r.status_code == 200, r.text
    r = api.post(LOGIN, json={"email": user["email"], "password": "Another12345"})
    assert r.status_code == 401, r.text


def test_old_login_token_invalid_after_reset(api, make_user):
    user = make_user()
    old = _login_token_via_api(api, user)
    status = _info_status(api, old)
    assert status == 200

    r = _resetpw(api, _token_of(_reset_link(user["email"])))
    assert r.status_code == 200, r.text

    status = _info_status(api, old)
    assert status == 401
    r = api.post(LOGIN, json={"email": user["email"], "password": NEW_PW})
    assert r.status_code == 200, r.text
    status = _info_status(api, r.json()["data"]["token"])
    assert status == 200


def test_old_login_token_invalid_after_profile_change(api, make_user):
    user = make_user()
    old = _login_token_via_api(api, user)
    r = api.patch(
        PROFILE_RESET_PW,
        headers=_bearer(old),
        json={"password": TEST_PASSWORD, "new_password": NEW_PW, "confirm_password": NEW_PW},
    )
    assert r.status_code == 200, r.text

    status = _info_status(api, old)
    assert status == 401
    r = api.post(LOGIN, json={"email": user["email"], "password": NEW_PW})
    assert r.status_code == 200, r.text
    status = _info_status(api, r.json()["data"]["token"])
    assert status == 200


# 既有行為的回歸測試：一開始就綠。防止新的 verifyLoginToken 把 expired 弄成一律 invalid。
def test_expired_login_token_is_401(api, make_user):
    user = make_user()
    token = login_token(user, exp_delta=datetime.timedelta(seconds=-60))
    r = api.get(PROFILE_INFO, headers=_bearer(token))
    assert r.status_code == 401, r.text
    assert r.json()["message"] == "Token 已過期"


# 既有行為的回歸測試：一開始就綠。
def test_resetpw_validation_and_invalid_token(api, make_user):
    user = make_user()
    token = reset_token(user)
    r = _resetpw(api, token, confirm_password="Other12345")
    assert r.status_code == 400 and r.json()["message"] == "新密碼與驗證密碼不一致", r.text
    r = _resetpw(api, "not-a-jwt")
    assert r.status_code == 400 and r.json()["message"] == "Token 資料錯誤、無效或過期", r.text
    expired = jwt.encode(
        {
            "id": user["user_id"],
            "typ": "reset",
            "pwv": current_pwv(user),
            "exp": datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(seconds=60),
        },
        os.environ["JWT_SECRET"],
        algorithm="HS256",
    )
    r = _resetpw(api, expired)
    assert r.status_code == 400 and r.json()["message"] == "Token 資料錯誤、無效或過期", r.text


def test_forged_token_without_pwv_is_401(api, make_user):
    user = make_user()
    token = jwt.encode({"id": user["user_id"], "role": user["role"]}, os.environ["JWT_SECRET"], algorithm="HS256")
    r = api.get(PROFILE_INFO, headers=_bearer(token))
    assert r.status_code == 401, r.text


def test_token_of_deleted_user_is_401(api, db, make_user):
    user = make_user()
    headers = auth_header(user)
    delete_user(db, user["user_id"])
    r = api.get(PROFILE_INFO, headers=headers)
    assert r.status_code == 401, r.text


def test_null_password_user_can_set_password_via_reset(api, make_user):
    user = make_user(password=None)
    r = _resetpw(api, _token_of(_reset_link(user["email"])))
    assert r.status_code == 200, r.text
    r = api.post(LOGIN, json={"email": user["email"], "password": NEW_PW})
    assert r.status_code == 200, r.text


# 以下為 Task 4 安全測試補強：一開始就綠（既有／新實作已涵蓋的分支）。
def test_auth_not_mandatory_without_header_is_not_401(api):
    # 帶齊 type、item、page、limit、lang（同 test_api_smoke 的 test_home_products_guest）
    params = {"type": "tourgroup", "item": "popular", "page": 1, "limit": 20, "lang": "zh-TW"}
    r = api.get(HOME_PRODUCTS, params=params)
    assert r.status_code == 200, r.text


def _bad_tokens(user: dict) -> dict:
    secret = os.environ["JWT_SECRET"]
    exp = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=10)
    base = {"id": user["user_id"], "role": user["role"], "exp": exp}
    return {
        "reset": reset_token(user),
        "legacy": jwt.encode({"id": user["user_id"], "role": user["role"]}, secret, algorithm="HS256"),
        "wrong_pwv": jwt.encode({**base, "typ": "login", "pwv": "0" * 16}, secret, algorithm="HS256"),
        "missing_pwv": jwt.encode({**base, "typ": "login"}, secret, algorithm="HS256"),
        "alg_none": jwt.encode({**base, "typ": "login", "pwv": current_pwv(user)}, None, algorithm="none"),
    }


@pytest.mark.parametrize("kind", ["reset", "legacy", "wrong_pwv", "missing_pwv", "alg_none"])
@pytest.mark.parametrize("path", [PROFILE_INFO, HOME_PRODUCTS])
def test_invalid_tokens_are_401(api, make_user, kind, path):
    user = make_user()
    token = _bad_tokens(user)[kind]
    r = api.get(path, headers=_bearer(token))
    assert r.status_code == 401, r.text


def test_demoted_admin_old_token_loses_admin(api, db, make_user):
    admin = make_user(role="admin")
    target = make_user()
    headers = auth_header(admin)
    body = {"user_ids": [target["user_id"]], "role": "admin"}
    r = api.patch(ROLES, headers=headers, json=body)
    assert r.status_code == 200, r.text

    db.execute('UPDATE "user" SET role = %s WHERE user_id = %s', ("User", admin["user_id"]))
    r = api.patch(ROLES, headers=headers, json=body)
    assert r.status_code == 403, r.text
    # role 是換成 DB 的值，而不是一律拒絕：同一個舊 token 仍可用會員 API
    status = _info_status(api, headers["Authorization"].split(" ")[1])
    assert status == 200


def test_change_role_to_user_keeps_member_access(api, db, make_user):
    admin = make_user(role="admin")
    b = make_user(role="admin")
    r = api.patch(ROLES, headers=auth_header(admin), json={"user_ids": [b["user_id"]], "role": "user"})
    assert r.status_code == 200, r.text
    assert _role_of(db, b["user_id"]) == "User"
    token = _login_token_via_api(api, b)
    status = _info_status(api, token)
    assert status == 200


# ---------------------------------------------------------------------------
# Task 5：驗證碼 HMAC 簽章 cookie（P2 spec §3.2）與 /resetpw 原子化
# ---------------------------------------------------------------------------
CAPTCHA = "/api/v1/auth/userinfo/captcha"


def _resetpw_with_cookie(api, user, cookie: str, input_: str = "abcde", new_password: str = NEW_PW):
    body = {
        "token": reset_token(user),
        "new_password": new_password,
        "confirm_password": new_password,
        "input": input_,
    }
    return api.patch(RESETPW, json=body, cookies={"captcha": cookie})


def test_captcha_cookie_is_not_plaintext(api):
    r = requests.get(f"{API_BASE}{CAPTCHA}", timeout=10)
    assert r.status_code == 200, r.text
    value = r.cookies.get("captcha")
    assert value and re.fullmatch(r"\d+\.[0-9a-f]{64}", value)


def test_forged_plaintext_captcha_cookie_rejected(api, make_user):
    user = make_user()
    r = _resetpw_with_cookie(api, user, "abcde", "abcde")
    assert r.status_code == 400 and r.json()["message"] == "驗證碼錯誤", r.text


def test_signed_captcha_cookie_accepted(api, make_user):
    user = make_user()
    r = _resetpw_with_cookie(api, user, captcha_cookie("abcde"), "ABCDE")
    assert r.status_code == 200, r.text


def test_expired_captcha_cookie_rejected(api, make_user):
    user = make_user()
    six_min_ago = int((time.time() - 6 * 60) * 1000)
    r = _resetpw_with_cookie(api, user, captcha_cookie("abcde", issued_at=six_min_ago))
    assert r.status_code == 400 and r.json()["message"] == "驗證碼已過期", r.text


def test_captcha_cookie_attributes_from_env():
    r = requests.get(f"{API_BASE}{CAPTCHA}", timeout=10)
    set_cookie = r.headers["Set-Cookie"]
    assert "SameSite=Lax" in set_cookie
    assert "Secure" not in set_cookie
    assert "HttpOnly" in set_cookie


@pytest.mark.parametrize("initial_password", ["default", None], ids=["bcrypt_password", "null_password"])
def test_reset_token_concurrent_use_only_one_succeeds(make_user, initial_password):
    user = make_user() if initial_password == "default" else make_user(password=None)
    token = reset_token(user)
    passwords = [f"Concurrent{i}Pw123" for i in range(4)]

    def hit(pw):
        return requests.patch(
            f"{API_BASE}{RESETPW}",
            json={"token": token, "new_password": pw, "confirm_password": pw, "input": "abcde"},
            cookies={"captcha": captcha_cookie("abcde")},
            timeout=30,
        )

    with ThreadPoolExecutor(max_workers=len(passwords)) as pool:
        results = list(pool.map(hit, passwords))

    statuses = sorted(r.status_code for r in results)
    assert statuses == [200] + [400] * (len(passwords) - 1), [(r.status_code, r.text) for r in results]
    for r in results:
        if r.status_code == 400:
            assert r.json()["message"] == TOKEN_ERR_MSG, r.text

    # DB 的密碼只對得上成功的那一個。先用贏家登入（成功會把失敗次數歸零），
    # 再只驗一個輸家（單次失敗不會觸發帳號鎖定）
    winner_idx = [r.status_code for r in results].index(200)
    loser_idx = (winner_idx + 1) % len(passwords)

    def login_status(pw):
        return requests.post(
            f"{API_BASE}{LOGIN}", json={"email": user["email"], "password": pw}, timeout=10
        ).status_code

    assert login_status(passwords[winner_idx]) == 200
    assert login_status(passwords[loser_idx]) == 401


def test_resetpw_success_clears_captcha_cookie(api, make_user):
    user = make_user()
    r = _resetpw_with_cookie(api, user, captcha_cookie("abcde"), "abcde")
    assert r.status_code == 200, r.text
    set_cookie = r.headers.get("Set-Cookie", "")
    assert set_cookie.startswith("captcha=;"), set_cookie
    assert "Expires=Thu, 01 Jan 1970" in set_cookie or "Max-Age=0" in set_cookie, set_cookie
    assert "Max-Age=300" not in set_cookie, set_cookie


def test_valid_signature_wrong_answer_rejected(api, make_user):
    user = make_user()
    r = _resetpw_with_cookie(api, user, captcha_cookie("abcde"), "zzzzz")
    assert r.status_code == 400 and r.json()["message"] == "驗證碼錯誤", r.text


def test_missing_captcha_cookie_is_expired(api, make_user):
    user = make_user()
    body = {"token": reset_token(user), "new_password": NEW_PW, "confirm_password": NEW_PW, "input": "abcde"}
    r = api.patch(RESETPW, json=body)
    assert r.status_code == 400 and r.json()["message"] == "驗證碼已過期", r.text


def test_tampered_expiry_captcha_cookie_rejected(api, make_user):
    user = make_user()
    old_issue = int((time.time() - 6 * 60) * 1000)  # 已過期的合法 cookie
    expires, sig = captcha_cookie("abcde", issued_at=old_issue).split(".")
    forged = f"{int(expires) + 3_600_000}.{sig}"  # 把到期時間改大、沿用舊簽章
    r = _resetpw_with_cookie(api, user, forged)
    assert r.status_code == 400 and r.json()["message"] == "驗證碼錯誤", r.text


@pytest.mark.parametrize("bad_input", [12345, ["abcde"]], ids=["number", "array"])
def test_non_string_captcha_input_is_400(api, make_user, bad_input):
    user = make_user()
    r = _resetpw_with_cookie(api, user, captcha_cookie("abcde"), bad_input)
    assert r.status_code == 400, r.text
