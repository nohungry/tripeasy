"""共用 fixture：API session、DB 連線、測試使用者、JWT。"""
import datetime
import hashlib
import hmac
import importlib.util
import json
import os
import time
import uuid
from pathlib import Path

import jwt
import psycopg
import pytest
import requests
from dotenv import load_dotenv

import newebpay as nb
from dbfactory import insert

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

API_BASE = os.getenv("TEST_API_BASE", "http://localhost:3000")
FRONTEND_BASE = os.getenv("TEST_FRONTEND_BASE", "http://localhost:5173")
MAILPIT_BASE = os.getenv("TEST_MAILPIT_BASE", "http://localhost:8025")
MOCK_OAUTH_BASE = os.getenv("TEST_MOCK_OAUTH_BASE", "http://localhost:8090")
DEFAULT_TIMEOUT = 10
BUILD_SCRIPT = ROOT / "db" / "seed-build" / "build_seed.py"


def load_build_seed():
    """seed 產生腳本不在 package 裡，用路徑載入。"""
    spec = importlib.util.spec_from_file_location("build_seed", BUILD_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Api(requests.Session):
    """路徑以 / 開頭時自動接上 base，並一律帶 timeout（避免卡住的請求讓測試無限等待）。"""

    def __init__(self, base: str):
        super().__init__()
        self.base = base

    def request(self, method, url, *args, **kwargs):
        kwargs.setdefault("timeout", DEFAULT_TIMEOUT)
        if url.startswith("/"):
            url = self.base + url
        return super().request(method, url, *args, **kwargs)


@pytest.fixture(scope="session")
def api():
    session = Api(API_BASE)
    yield session
    session.close()


def _db_params() -> dict:
    return dict(
        host=os.getenv("TEST_DB_HOST", "localhost"),
        port=int(os.getenv("TEST_DB_PORT", "5432")),
        user=os.environ["POSTGRES_DB_USER"],
        password=os.environ["POSTGRES_DB_PASSWORD"],
        dbname=os.environ["POSTGRES_DB_NAME"],
    )


@pytest.fixture(scope="session")
def db():
    conn = psycopg.connect(**_db_params(), autocommit=True)
    yield conn
    conn.close()


@pytest.fixture
def tx():
    """不自動 commit 的連線。測試結束一律 rollback，不留下任何資料。"""
    conn = psycopg.connect(**_db_params())
    try:
        yield conn
    finally:
        conn.rollback()
        conn.close()


# 直接參照 "user" 的表（V1 全部），順序即刪除順序（orders、cart 放最後）；test_member_auth 會比對 pg_constraint
USER_FK_TABLES = (
    '"socialLogin"', "user_level", "point_record", "user_coupon", "payment", "review",
    "hidden_play", "auto_setting", "favorite", "orders", "cart",
)  # fmt: skip


def delete_user(db, user_id: str) -> None:
    """依 FK 順序刪除使用者和它的附屬資料（涵蓋 V1 所有參照 "user" 的表，含 orders / cart 底下的間接相依）。"""
    # 先清掉依附在「該會員的 orders / cart」底下的子表
    order_ids = "SELECT order_id FROM orders WHERE user_id = %s"
    cart_ids = "SELECT cart_id FROM cart WHERE user_id = %s"
    db.execute(f"DELETE FROM order_item WHERE order_id IN ({order_ids})", (user_id,))
    db.execute(f"DELETE FROM payment WHERE order_id IN ({order_ids})", (user_id,))
    db.execute(f"DELETE FROM point_record WHERE order_id IN ({order_ids})", (user_id,))
    db.execute(f"DELETE FROM user_coupon WHERE order_id IN ({order_ids})", (user_id,))
    db.execute(f"DELETE FROM cart_item WHERE cart_id IN ({cart_ids})", (user_id,))
    # 再清直接參照 "user" 的表（orders、cart 放最後）
    for table in USER_FK_TABLES:
        db.execute(f"DELETE FROM {table} WHERE user_id = %s", (user_id,))
    db.execute('DELETE FROM "user" WHERE user_id = %s', (user_id,))


TEST_PASSWORD = "Tripeasy123"
# TEST_PASSWORD 的 bcrypt（cost 10，用 backend 容器的 bcrypt 產生；測試環境沒有 Python bcrypt 套件）
TEST_PASSWORD_HASH = "$2b$10$Gv8aWHvXWoOcP9b.gyVTl.vEznO/bXW1hLig..ZaTtEgRMmJGuIlG"
_DEFAULT = object()


def _cleanup_all(items, delete) -> None:
    """逐筆清除；單筆失敗不影響其餘，全部試完後才拋出第一個錯誤。"""
    first_error = None
    for item in items:
        try:
            delete(item)
        except Exception as exc:  # noqa: BLE001
            first_error = first_error or exc
    if first_error is not None:
        raise first_error


@pytest.fixture
def make_user(db):
    created: list[str] = []

    def _make(role: str = "User", email: str | None = None, password=_DEFAULT) -> dict:
        """password 預設存 TEST_PASSWORD 的 bcrypt；傳 None 存 NULL。"""
        if password is _DEFAULT:
            password = TEST_PASSWORD_HASH
        email = email or f"p0-{uuid.uuid4().hex[:8]}@example.com"
        (user_id,) = db.execute(
            'INSERT INTO "user" (name, email, role, password, preference1, preference2, preference3) '
            "VALUES (%s, %s, %s, %s, 1, 2, 3) RETURNING user_id",
            ("P0 測試", email, role, password),
        ).fetchone()
        created.append(str(user_id))
        # 同 Email 註冊交易（controllers/userinfo.js）：登入成功路徑會讀 user_level
        db.execute(
            "INSERT INTO user_level (user_id, level, name, badge_url, travel_point) "
            "VALUES (%s, 'Level 1', '初心旅人', 'https://example.com/badges/level1.png', 0)",
            (user_id,),
        )
        return {"user_id": str(user_id), "email": email, "role": role}

    yield _make
    _cleanup_all(created, lambda user_id: delete_user(db, user_id))


def password_fingerprint(password) -> str:
    """共用約定的 pwv：HMAC-SHA256(key = JWT_SECRET, msg = password ?? '') 的 hex 前 16 字元。"""
    key = os.environ["JWT_SECRET"].encode()
    return hmac.new(key, (password or "").encode(), hashlib.sha256).hexdigest()[:16]


def current_pwv(user: dict) -> str:
    """用新連線查該會員目前的 password 算 pwv（不沿用測試的 db fixture，避免交易可見性問題）。"""
    with psycopg.connect(**_db_params(), autocommit=True) as conn:
        row = conn.execute('SELECT password FROM "user" WHERE user_id = %s', (user["user_id"],)).fetchone()
    return password_fingerprint(row[0] if row else None)


def login_token(user: dict, exp_delta: datetime.timedelta | None = None) -> str:
    """登入 token：{id, role, typ: 'login', pwv}；exp_delta 給定時 exp = 現在 + exp_delta（負值即已過期）。"""
    payload = {"id": user["user_id"], "role": user["role"], "typ": "login", "pwv": current_pwv(user)}
    payload["exp"] = datetime.datetime.now(datetime.timezone.utc) + (exp_delta or datetime.timedelta(days=30))
    return jwt.encode(payload, os.environ["JWT_SECRET"], algorithm="HS256")


def reset_token(user: dict) -> str:
    """重設 token：{id, typ: 'reset', pwv}，效期 15 分鐘。"""
    payload = {
        "id": user["user_id"],
        "typ": "reset",
        "pwv": current_pwv(user),
        "exp": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=15),
    }
    return jwt.encode(payload, os.environ["JWT_SECRET"], algorithm="HS256")


def auth_header(user: dict) -> dict:
    """跟 backend 登入時簽發的登入 token 一樣（帶 pwv）。"""
    return {"Authorization": f"Bearer {login_token(user)}"}


CART_API = "/api/v1/user/trade/cart"


def add_to_cart(api, user, tour, people=1, start_date=None, end_date=None):
    """POST 加入購物車。tour 是 make_tour 回傳的 dict（取其 tour_id、type、item），不是 tour_id 字串。
    start_date／end_date 為 YYYY-MM-DD，預設明天、後天；回傳 requests.Response。"""
    today = datetime.date.today()
    start_date = start_date or (today + datetime.timedelta(days=1)).isoformat()
    end_date = end_date or (today + datetime.timedelta(days=2)).isoformat()
    body = {
        "type": tour["type"],
        "item": tour["item"],
        "people": people,
        "options": {"start_date": start_date, "end_date": end_date},
    }
    return api.post(f"{CART_API}/{tour['tour_id']}", json=body, headers=auth_header(user), timeout=5)


CHECKOUT_API = "/api/v1/user/checkout"


def checkout(api, user, tours: list[dict]) -> str:
    """依序把每個行程（make_tour 回傳的 dict）加入購物車，再用該會員的購物車建單；回傳 order_id。"""
    for tour in tours:
        r = add_to_cart(api, user, tour)
        assert r.status_code == 201, r.text
    with psycopg.connect(**_db_params(), autocommit=True) as conn:
        (cart_id,) = conn.execute("SELECT cart_id FROM cart WHERE user_id = %s", (user["user_id"],)).fetchone()
    r = api.post(f"{CHECKOUT_API}/order/{cart_id}", headers=auth_header(user), timeout=5)
    assert r.status_code == 200, r.text
    return r.json()["data"]["order_id"]


DISCOUNT_API = "/api/v1/user/trade/discounts"


def preview(api, user, order_id, discount: dict | None = None):
    """PATCH 結帳預覽（固定地址、電話、信用卡）；discount 為 None 時不帶該欄位。回傳 requests.Response。"""
    body = {
        "user": {"name": "測試用戶", "email": user["email"], "address": "台北市測試路1號", "phone_number": "0912345678"},
        "payment_method": "credit_card",
    }
    if discount is not None:
        body["discount"] = discount
    return api.patch(f"{CHECKOUT_API}/preview/{order_id}", json=body, headers=auth_header(user), timeout=10)


def trial_discount(api, user, order_id, body: dict):
    """POST 折扣試算（不寫入）。"""
    return api.post(f"{DISCOUNT_API}/{order_id}", json=body, headers=auth_header(user), timeout=10)


def cancel_discount(api, user, order_id):
    """GET 取消折扣（釋放保留）。"""
    return api.get(f"{DISCOUNT_API}/{order_id}", headers=auth_header(user), timeout=10)


CAPTCHA_TTL_MS = 5 * 60 * 1000


def captcha_cookie(answer: str = "abcde", issued_at: int | None = None) -> str:
    """合法的驗證碼 cookie 值：'<expiresMs>.<hex64>'。

    issued_at 為簽發時間（epoch 毫秒，預設現在），expiresMs = issued_at + 5 分鐘；
    簽章 = HMAC-SHA256(key = CAPTCHA_SECRET, msg = f"{answer.lower()}.{expiresMs}")。
    金鑰在呼叫時才讀，缺少就 KeyError（不設預設值，避免與後端悄悄不一致）。
    """
    if issued_at is None:
        issued_at = int(time.time() * 1000)
    expires_ms = issued_at + CAPTCHA_TTL_MS
    key = os.environ["CAPTCHA_SECRET"].encode()
    sig = hmac.new(key, f"{answer.lower()}.{expires_ms}".encode(), hashlib.sha256).hexdigest()
    return f"{expires_ms}.{sig}"


def mock_google_code(claims: dict) -> str:
    """向 mock-oauth（interactiveLogin: true）取一個授權碼；該碼換到的 userinfo 等於 claims。

    作法：POST 它的登入表單（欄位 username 與 claims JSON），取 302 Location 的 code。
    注意：mock 對任何 code（含亂填、重複使用）都會簽發 token，驗證 code 是 Google 的責任，這一層測不到。
    """
    from urllib.parse import parse_qs, urlparse

    r = requests.post(
        f"{MOCK_OAUTH_BASE}/google/authorize",
        params={
            "client_id": os.environ["GOOGLE_CLIENT_ID"],
            "redirect_uri": os.environ["GOOGLE_REDIRECT_URI"],
            "response_type": "code",
            "scope": "openid email profile",
            "state": "p2",
        },
        data={"username": str(claims["sub"]), "claims": json.dumps(claims)},
        allow_redirects=False,
        timeout=DEFAULT_TIMEOUT,
    )
    assert r.status_code == 302, r.text
    return parse_qs(urlparse(r.headers["Location"]).query)["code"][0]


# ------------------------------------------------------------------ P3：測試行程、訂單與殘留清除

# 全小寫；比對用 lower(email)，且 email 必須以 @example.com 結尾
TEST_EMAIL_PREFIXES: tuple[str, ...] = (
    "p0-", "e2e-", "factory-", "a.", "g.", "mixed.", "nobody.", "val.", "race.", "pref.", "lower.", "dup.", "co.", "mock.",
)  # fmt: skip
TEST_TOUR_PREFIX = "p3-"
TEST_COUPON_PREFIX = "P4"


def delete_tour(db, tour_id: str) -> None:
    """依 FK 順序刪除行程與其附屬資料。"""
    p = (tour_id,)
    for table in ("review", "hidden_play", "favorite", "cart_item", "notification", "order_item", "tour_detail"):
        db.execute(f"DELETE FROM {table} WHERE tour_id = %s", p)
    restaurants = "SELECT restaurant_id FROM restaurant WHERE tour_id = %s"
    db.execute(f"DELETE FROM restaurant_business WHERE restaurant_id IN ({restaurants})", p)
    db.execute(f"DELETE FROM restaurant_menu WHERE restaurant_id IN ({restaurants})", p)
    db.execute("DELETE FROM restaurant WHERE tour_id = %s", p)
    db.execute("DELETE FROM hotel_room WHERE hotel_id IN (SELECT hotel_id FROM hotel WHERE tour_id = %s)", p)
    db.execute("DELETE FROM hotel WHERE tour_id = %s", p)
    db.execute("DELETE FROM tour WHERE tour_id = %s", p)


def delete_coupon(db, coupon_id: str) -> None:
    """先刪 user_coupon 再刪 coupon。"""
    db.execute("DELETE FROM user_coupon WHERE coupon_id = %s", (coupon_id,))
    db.execute("DELETE FROM coupon WHERE coupon_id = %s", (coupon_id,))


def purge_leftover_test_data(db) -> dict:
    """刪除前次測試殘留的測試會員、測試行程與測試優惠券（先會員、行程，最後優惠券）。"""
    user_ids = [
        str(user_id)
        for user_id, email in db.execute('SELECT user_id, lower(email) FROM "user"').fetchall()
        if email.endswith("@example.com") and email.startswith(TEST_EMAIL_PREFIXES)
    ]
    for user_id in user_ids:
        delete_user(db, user_id)
    tour_ids = [
        str(r[0])
        for r in db.execute(
            "SELECT tour_id FROM tour WHERE starts_with(title, %s)", (TEST_TOUR_PREFIX,)
        ).fetchall()
    ]
    for tour_id in tour_ids:
        delete_tour(db, tour_id)
    coupon_ids = [
        str(r[0])
        for r in db.execute(
            "SELECT coupon_id FROM coupon WHERE starts_with(code, %s)", (TEST_COUPON_PREFIX,)
        ).fetchall()
    ]
    for coupon_id in coupon_ids:
        delete_coupon(db, coupon_id)
    return {"users": len(user_ids), "tours": len(tour_ids), "coupons": len(coupon_ids)}


@pytest.fixture(scope="session", autouse=True)
def purge_leftovers(db):
    purge_leftover_test_data(db)


@pytest.fixture
def make_tour(db):
    created: list[str] = []

    def _make(
        item: str = "travel",
        status: int = 1,
        with_detail: bool = True,
        title: str | None = None,
        *,
        price: int | None = None,
        start_date: datetime.date | None = None,
        end_date: datetime.date | None = None,
    ) -> dict:
        if with_detail and item not in ("travel", "spot"):
            raise ValueError(f"item={item!r} 不能建立 tour_detail（只允許 travel／spot）")
        title = title or f"{TEST_TOUR_PREFIX}{uuid.uuid4().hex[:8]}"
        assert title.startswith(TEST_TOUR_PREFIX), title
        tour_type = "tourgroup" if item == "travel" else "backpacker"
        # price／tour_start_date／tour_end_date 預設不傳（price 用 dbfactory 預設、日期保持 NULL）
        extra = {}
        if price is not None:
            extra["price"] = price
        if start_date is not None:
            extra["tour_start_date"] = start_date
        if end_date is not None:
            extra["tour_end_date"] = end_date
        row = insert(db, "tour", type=tour_type, item=item, status=status, title=title, **extra)
        tour_id = str(row["tour_id"])
        created.append(tour_id)
        if with_detail:
            insert(db, "tour_detail", tour_id=tour_id)
        return {"tour_id": tour_id, "title": title, "type": tour_type, "item": item, "status": status}

    yield _make
    _cleanup_all(created, lambda tour_id: delete_tour(db, tour_id))


def live_promotion(db, make_tour) -> dict:
    """建立一個上架行程，並寫一筆有效的促銷（now() ± 1 day、discount 10、promo_price 900）；回傳該行程。"""
    t = make_tour()
    db.execute(
        "INSERT INTO notification (tour_id, type, start_date, end_date, discount, promo_price) "
        "VALUES (%s, '促銷', now() - interval '1 day', now() + interval '1 day', 10, 900)",
        (t["tour_id"],),
    )  # notification 由 make_tour teardown 的 delete_tour 清除
    return t


@pytest.fixture
def make_coupon(db):
    created: list[str] = []

    def _make(user: dict | None = None, discount: int = 100, expire_in_days: int = 30, status: int = 0) -> dict:
        """建立 coupon（code = P4 + 4 碼大寫十六進位）；user 不為 None 時一併綁定 user_coupon（status、order_id NULL）。"""
        code = TEST_COUPON_PREFIX + uuid.uuid4().hex[:4].upper()
        (coupon_id,) = db.execute(
            "INSERT INTO coupon (code, discount, description, expire_date) "
            "VALUES (%s, %s, %s, now() + make_interval(days => %s)) RETURNING coupon_id",
            (code, discount, "P4 測試優惠券", expire_in_days),
        ).fetchone()
        created.append(str(coupon_id))
        if user is not None:
            db.execute(
                "INSERT INTO user_coupon (user_id, coupon_id, status) VALUES (%s, %s, %s)",
                (user["user_id"], coupon_id, status),
            )
        return {"coupon_id": str(coupon_id), "code": code, "discount": discount}

    yield _make
    _cleanup_all(created, lambda coupon_id: delete_coupon(db, coupon_id))


@pytest.fixture
def make_order(db):
    created: list[tuple[str, str]] = []

    def _make(
        user: dict, tour_id: str, payment_status: int = 1, quantity: int = 1, order_payment_status: int | None = None
    ) -> dict:
        """payment_status 是 order_item 的；order_payment_status 是 orders 的（預設與 payment_status 相同）。"""
        total = 1000 * quantity
        order_status = payment_status if order_payment_status is None else order_payment_status
        order = insert(db, "orders", user_id=user["user_id"], payment_status=order_status, total_price=total)
        order_id = str(order["order_id"])
        item = insert(
            db, "order_item", order_id=order_id, tour_id=tour_id, payment_status=payment_status,
            total_price=total, quantity=quantity, start_date=datetime.datetime.now(),
        )  # fmt: skip
        item_id = str(item["order_item_id"])
        created.append((order_id, item_id))
        return {"order_id": order_id, "order_item_id": item_id}

    yield _make

    def _delete(pair):
        order_id, item_id = pair
        db.execute("DELETE FROM point_record WHERE order_id = %s", (order_id,))
        db.execute("DELETE FROM order_item WHERE order_item_id = %s", (item_id,))
        db.execute("DELETE FROM orders WHERE order_id = %s", (order_id,))

    _cleanup_all(created, _delete)


# ---- P4 付款輔助（Task 8 起；多個測試檔共用）

PAYMENT_API = "/api/v1/user/newebpay/payment"
NOTIFY_API = "/api/v1/user/newebpay/notify"
SUMMARY_API = "/api/v1/user/checkout/summary"


def ready_order(api, db, make_user, make_tour, discount=None, *, price=1000, people=1, user=None, tour=None):
    """建單並 preview（訂單進入 0）；回傳 (user, order_id)。"""
    user = user or make_user()
    tour = tour or make_tour(price=price)
    assert add_to_cart(api, user, tour, people=people).status_code == 201
    order_id = checkout(api, user, [])
    r = preview(api, user, order_id, discount)
    assert r.status_code == 200, r.text
    return user, order_id


def start_payment(api, user, order_id, noise=None):
    """POST /payment；回傳 (merchant_order_no, amt, 表單欄位)。"""
    r = api.post(PAYMENT_API, headers=auth_header(user), json={"order_id": order_id, **(noise or {})}, timeout=10)
    assert r.status_code == 200, r.text
    _, fields = nb.parse_payment_form(r.text)
    trade = nb.decode_trade_info(fields)
    return trade["MerchantOrderNo"], int(trade["Amt"]), fields


def notify(api, fields):
    return api.post(NOTIFY_API, data=fields, timeout=10)


def success_notify(mon, amt, **kw):
    return nb.build_notify(mon, amt, **kw)


def order_status(db, order_id):
    order = db.execute("SELECT payment_status FROM orders WHERE order_id = %s", (order_id,)).fetchone()[0]
    items = {r[0] for r in db.execute("SELECT payment_status FROM order_item WHERE order_id = %s", (order_id,))}
    return order, items


def travel_point(db, user):
    return db.execute("SELECT travel_point FROM user_level WHERE user_id = %s", (user["user_id"],)).fetchone()[0]


def summary(api, user, order_id):
    r = api.get(f"{SUMMARY_API}/{order_id}", headers=auth_header(user), timeout=10)
    assert r.status_code == 200, r.text
    return r.json()["data"]["summary"]


def refund_url(order_id):
    return f"/api/v1/admin/orders/{order_id}/refund"


def refund(api, admin, order_id):
    return api.post(refund_url(order_id), headers=auth_header(admin), timeout=10)


def negative_points_via_refund(api, db, make_user, make_tour) -> dict:
    """F24：不直接改 DB，用退款流程造出負點數（-8）。

    付清 A 單（1000，回饋 100）→ 用 100 點付 B 單（應付 920，回饋 92）→ admin 退款 A（收回 100）。
    餘額 100 - 100 + 92 - 100 = -8。回傳該會員。
    """
    admin = make_user(role="admin")
    user, order_a = ready_order(api, db, make_user, make_tour, price=1000)
    mon, amt, _ = start_payment(api, user, order_a)
    assert notify(api, success_notify(mon, amt)).status_code == 200
    assert travel_point(db, user) == 100
    user, order_b = ready_order(api, db, make_user, make_tour, {"type": "point", "used_point": 100}, user=user, price=1000)
    mon, amt, _ = start_payment(api, user, order_b)
    assert amt == 920
    assert notify(api, success_notify(mon, amt)).status_code == 200
    assert travel_point(db, user) == 92
    r = refund(api, admin, order_a)
    assert r.status_code == 200, r.text
    assert travel_point(db, user) == -8
    return user
