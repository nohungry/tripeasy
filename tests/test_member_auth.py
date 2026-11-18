"""P2 會員：權限與資料清理。後續 Task 的會員測試加在這裡。"""
import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest

from conftest import TEST_PASSWORD, USER_FK_TABLES, auth_header, delete_user
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


@pytest.mark.xfail(strict=True, reason="P3：PATCH /info 部分更新（只給 name）會 500；中介層假設 preference 必有")
def test_patch_profile_info_name_only(api, db, make_user):
    user = make_user()
    r = api.patch(PROFILE_INFO, headers=auth_header(user), json={"name": "新名字"})
    assert r.status_code == 200, r.text
    (name,) = db.execute('SELECT name FROM "user" WHERE user_id = %s', (user["user_id"],)).fetchone()
    assert name == "新名字"


@pytest.mark.xfail(strict=True, reason="P3：PATCH /info 部分更新（只給 preference）會 500；controller 一律寫入 name")
def test_patch_profile_info_preference_only(api, db, make_user):
    user = make_user()
    (before,) = db.execute('SELECT name FROM "user" WHERE user_id = %s', (user["user_id"],)).fetchone()
    r = api.patch(PROFILE_INFO, headers=auth_header(user), json={"preference": ["美食探索", "都市感官", "自然療癒"]})
    assert r.status_code == 200, r.text
    (after,) = db.execute('SELECT name FROM "user" WHERE user_id = %s', (user["user_id"],)).fetchone()
    assert after == before
