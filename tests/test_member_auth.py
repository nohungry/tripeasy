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
    assert r.status_code != 404, r.text


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
